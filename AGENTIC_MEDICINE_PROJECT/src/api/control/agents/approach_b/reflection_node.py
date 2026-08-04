"""
reflection_node.py
------------------
Node 5 of the Approach B LangGraph pipeline.

Model (provider auto-routed via key_pool.MODEL_SPECS):
  - nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free  (OpenRouter)

Purpose: Adjudication on disagreement or low confidence between the two
         independent crop readers (first_read and second_read).

This node only fires when consensus_check routes "mismatch" or "low_confidence",
which should be a minority of images — most should exit through the cheap
direct match→validate path.

If resolution == "unresolved", final_mfg and final_exp stay None and validate
will route straight to HUMAN_REVIEW regardless of format checks.
"""

import base64
import json
import logging
import re

from src.api.schemas.date_detection_state import DateDetectionState
from src.api.http_clients.key_pool import OMNI30B, acall_vlm_with_rotation

# Production pin: Reflection = omni on OpenRouter.
# MODEL_SPECS fallbacks are emergency-only inside the pool.
REFLECTION_MODELS = [OMNI30B]

# ---------------------------------------------------------------------------
# Prompts — JSON schema in system (Groq JSON Object Mode rules kept for
# providers that honor response_format; omni may strip it via key_pool).
# Both readers are crop OCR — neither saw the full package for grounding.
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are an adjudication API that resolves disagreements between two "
    "medicine-label date readings.\n"
    "Respond ONLY with a single valid JSON object. No markdown, no code fences, "
    "no reasoning text, no explanation.\n"
    "JSON schema (example values):\n"
    "{\n"
    '  "resolution": "resolved",\n'
    '  "mfg_date_raw": "06/2023",\n'
    '  "exp_date_raw": "05/2025",\n'
    '  "evidence_note": "Digit 6 is clear on the crop; B misread label prefix."\n'
    "}\n"
    "resolution must be resolved or unresolved. Use null dates only when unresolved.\n\n"
    "CONTEXT ABOUT THE TWO READERS:\n"
    "- Reading A (first_read): crop OCR of the date region — independent transcription.\n"
    "- Reading B (second_read): crop OCR of the same date region — independent second opinion.\n"
    "Both readers saw only the cropped date field (YOLO or full-image fallback), "
    "not a separate grounding pass.\n"
    "Rules:\n"
    "- Prefer the reading whose characters are clearly visible on the crop.\n"
    "- If one reading is a label prefix (e.g. 'MFG. D' / 'EXP. D') and the other "
    "has a numeric/month date, prefer the date reading.\n"
    "- Mark unresolved when the crop is too ambiguous to choose confidently."
)

USER_PROMPT_TEMPLATE = (
    "Two independent crop readings of a medicine label's date field disagreed:\n\n"
    'Reading A (crop OCR): mfg="{mfg_a}", exp="{exp_a}"\n'
    'Reading B (crop OCR): mfg="{mfg_b}", exp="{exp_b}"\n\n'
    "Look at the attached CROP IMAGE closely at the position(s) where A and B disagree.\n"
    "Decide resolved vs unresolved and return JSON only."
)


def _encode_image(image_path: str, max_dim: int = 1024) -> str:
    """Return a base64 JPEG data URL for *image_path*, resizing large images to max_dim."""
    import cv2
    img = cv2.imread(image_path)
    if img is None:
        with open(image_path, "rb") as fh:
            raw = base64.b64encode(fh.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{raw}"

    h, w = img.shape[:2]
    if max(h, w) > max_dim:
        scale = max_dim / float(max(h, w))
        img = cv2.resize(img, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    success, buffer = cv2.imencode(".jpg", img, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    if not success:
        with open(image_path, "rb") as fh:
            raw = base64.b64encode(fh.read()).decode("utf-8")
        return f"data:image/jpeg;base64,{raw}"

    raw = base64.b64encode(buffer).decode("utf-8")
    return f"data:image/jpeg;base64,{raw}"


def _extract_json(text: str) -> dict:
    """Strip markdown wrappers and parse JSON object safely."""
    if not text:
        return {}
    start_idx = text.find("{")
    end_idx = text.rfind("}")
    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        text = text[start_idx : end_idx + 1]
    return json.loads(text)


def _normalize(raw: str | None) -> str | None:
    """Match the normalisation used in consensus_check for display in the prompt."""
    if not raw:
        return None
    return raw.strip().upper().replace(" ", "").replace("--", "-")


_RE_MM_YYYY = re.compile(r"^(0[1-9]|1[0-2])(\d{4})$")
_RE_YYYY_MM = re.compile(r"^(\d{4})(0[1-9]|1[0-2])$")


def _repair_separator(raw: str | None) -> str | None:
    """
    Restore a date separator that was stripped by normalisation.

    Detects 6-digit MMYYYY / YYYYMM patterns and reinserts '/' or '-':
      '052025' → '05/2025'   (MM/YYYY)
      '202505' → '2025-05'   (YYYY-MM)
    """
    if not raw:
        return raw
    normalized = raw.strip().upper().replace(" ", "").replace("-", "").replace("/", "")
    m = _RE_MM_YYYY.match(normalized)
    if m:
        return f"{m.group(1)}/{m.group(2)}"
    m = _RE_YYYY_MM.match(normalized)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return raw


async def reflection_node(state: DateDetectionState) -> DateDetectionState:
    """
    LangGraph node — reflection (adjudication).

    Shown both candidate crop readings and the crop; required to cite visual
    evidence at the disputed character position before adjudicating.

    Mutates and returns state with:
      - reflection_result: raw parsed JSON from the model
      - final_mfg / final_exp: set if resolution == "resolved"
        (left as None if "unresolved", causing validate to route to HUMAN_REVIEW)
    """
    a: dict = state["first_result"]
    b: dict = state["second_result"]
    crop_path: str = state["crop_path"]

    crop_b64 = _encode_image(crop_path)

    user_content = USER_PROMPT_TEMPLATE.format(
        mfg_a=a.get("mfg_date_raw") or "null",
        exp_a=a.get("exp_date_raw") or "null",
        mfg_b=b.get("mfg_date_raw") or "null",
        exp_b=b.get("exp_date_raw") or "null",
    )

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_content},
                {
                    "type": "image_url",
                    "image_url": {"url": crop_b64, "detail": "high"},
                },
            ],
        },
    ]

    response = await acall_vlm_with_rotation(
        model=REFLECTION_MODELS,
        messages=messages,
        response_format={"type": "json_object"},
    )

    raw_text: str = response.choices[0].message.content or "{}"

    try:
        result: dict = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        result = {
            "resolution": "unresolved",
            "mfg_date_raw": None,
            "exp_date_raw": None,
            "evidence_note": f"JSON parse error in reflection response: {exc}",
        }

    model_used = getattr(response, "_model_used", "unknown")
    result["model_used"] = model_used
    logging.getLogger(__name__).info("reflection_node executed using model: %s", model_used)

    state["reflection_result"] = result

    if result.get("resolution") == "resolved":
        state["final_mfg"] = _normalize(_repair_separator(result.get("mfg_date_raw")))
        state["final_exp"] = _normalize(_repair_separator(result.get("exp_date_raw")))
    else:
        state["final_mfg"] = None
        state["final_exp"] = None

    return state
