"""
first_read_node.py
------------------
Node 2 of the Approach B LangGraph pipeline (after crop_zoom).

Model (provider auto-routed via key_pool.MODEL_SPECS):
  - qwen/qwen3.6-27b  (Groq)

Purpose: Produce the first independent MFG/EXP reading from the YOLO (or
         full-image-fallback) crop.  Crop-only OCR — no bbox grounding.
"""

import base64
import json
import logging

import cv2

from src.api.schemas.date_detection_state import DateDetectionState
from src.api.http_clients.key_pool import QWEN36_GROQ, acall_vlm_with_rotation

# Production pin: Reader A = qwen on Groq. MODEL_SPECS fallbacks are for
# emergency retry inside acall_vlm_with_rotation only.
FIRST_READ_MODELS = [QWEN36_GROQ]

# ---------------------------------------------------------------------------
# Prompt — JSON schema in system (Groq JSON Object Mode requirement)
# No bbox_2d: localization is handled exclusively by crop_zoom (YOLO).
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a pharmaceutical date-field transcription API.\n"
    "Respond ONLY with a single valid JSON object. No markdown, no code fences, "
    "no reasoning text, no explanation.\n"
    "JSON schema (example values — replace with what you read):\n"
    "{\n"
    '  "mfg_date_raw": "APR.2024",\n'
    '  "exp_date_raw": "MAR.2027",\n'
    '  "mfg_confidence": "high",\n'
    '  "exp_confidence": "high",\n'
    '  "ambiguous_characters": ""\n'
    "}\n"
    "Rules: extract only date values (not label prefixes like MFG/EXP); "
    "use null when a date is missing or illegible; "
    "mfg_confidence/exp_confidence must be high, medium, low, or null; "
    "list any unclear characters in ambiguous_characters (empty string if none)."
)

USER_PROMPT = (
    "IMPORTANT: This image is a CROPPED CLOSE-UP extracted from a medicine package label.\n"
    "The crop was taken around the area where manufacturing and expiration dates are printed.\n\n"
    "Transcribe the ACTUAL DATE VALUES only — NOT label prefixes.\n"
    "The image may contain:\n"
    "  Label prefixes: 'MFG', 'MFG.', 'MFD', 'MFG. DATE:', 'EXP', 'EXP.', 'EXP. DATE:', 'BB', 'USE BY'\n"
    "  Date values: '06/2023', 'APR 2024', '2025-05', 'MAR. 2027'\n\n"
    "Rules:\n"
    "1. Extract ONLY the date values. Ignore label prefix text.\n"
    "2. If you only see a label prefix with no date digits, return null for that field.\n"
    "3. Preserve the original date format exactly as printed "
    "(do not reformat, do not convert month names, do not add separators that are not printed).\n"
    "4. If a character is smudged or cut off, set confidence to low and note it in "
    "ambiguous_characters.\n"
    "5. Do not guess. Return JSON only."
)


def _encode_image(image_path: str, max_dim: int = 1024) -> str:
    """Return a base64 JPEG data URL for *image_path*, resizing large images to max_dim."""
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


async def first_read_node(state: DateDetectionState) -> DateDetectionState:
    """
    LangGraph node — first_read (crop OCR).

    Sends only the crop image to qwen for the first independent MFG/EXP reading.
    Does not perform grounding; bbox_2d is already set by crop_zoom.

    Mutates and returns state with:
      - first_result: raw parsed JSON from the model
    """
    crop_path: str = state["crop_path"]
    crop_b64 = _encode_image(crop_path)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": USER_PROMPT},
                {
                    "type": "image_url",
                    "image_url": {"url": crop_b64, "detail": "high"},
                },
            ],
        },
    ]

    response = await acall_vlm_with_rotation(
        model=FIRST_READ_MODELS,
        messages=messages,
        response_format={"type": "json_object"},
    )

    raw_text: str = response.choices[0].message.content or "{}"
    model_used = getattr(response, "_model_used", "unknown")

    try:
        result: dict = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        result = {
            "mfg_date_raw": None,
            "exp_date_raw": None,
            "mfg_confidence": "low",
            "exp_confidence": "low",
            "ambiguous_characters": f"JSON parse error: {exc}",
        }

    result["model_used"] = model_used
    logging.getLogger(__name__).info(
        "first_read_node executed using model: %s", model_used
    )

    state["first_result"] = result
    return state
