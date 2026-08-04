"""
second_read_node.py
-------------------
Node 3 of the Approach B LangGraph pipeline.

Model (provider auto-routed via key_pool.MODEL_SPECS):
  - qwen/qwen3.6-27b  (Groq)

Purpose: Produce an **independent** second reading of the MFG/EXP dates from
         the cropped date-field image.

Critical design point:
  This call must NOT see first_read's answer.  It receives only the cropped image.
  That is what makes it a genuine second opinion rather than an anchored
  re-confirmation of the first model's result.
"""

import base64
import json
import logging

from src.api.schemas.date_detection_state import DateDetectionState
from src.api.http_clients.key_pool import QWEN36_GROQ, acall_vlm_with_rotation

# Production pin: Reader B = qwen on Groq (same model family as Reader A,
# independent call). MODEL_SPECS fallbacks are emergency-only inside the pool.
SECOND_READ_MODELS = [QWEN36_GROQ]

# ---------------------------------------------------------------------------
# Prompt — JSON schema in system (Groq JSON Object Mode requirement)
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = (
    "You are a pharmaceutical date-field transcription API.\n"
    "Respond ONLY with a single valid JSON object. No markdown, no code fences, "
    "no reasoning text, no explanation.\n"
    "JSON schema (example values — replace with what you read):\n"
    "{\n"
    '  "mfg_date_raw": "06/2023",\n'
    '  "exp_date_raw": "05/2025",\n'
    '  "mfg_confidence": "high",\n'
    '  "exp_confidence": "high"\n'
    "}\n"
    "Rules: extract only date values (not label prefixes like MFG/EXP); "
    "use null when a date is missing or illegible; confidence is high, medium, low, or null."
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
    "3. Preserve the original date format exactly as printed.\n"
    "4. If a character is smudged or cut off, set confidence to low.\n\n"
    "Return JSON only."
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


async def second_read_node(state: DateDetectionState) -> DateDetectionState:
    """
    LangGraph node — second_read.

    Sends only the crop image (not first_read's answer) to an independent
    vision-language model for a second MFG/EXP reading.

    Mutates and returns state with:
      - second_result: raw parsed JSON from the model
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
        model=SECOND_READ_MODELS,
        messages=messages,
        response_format={"type": "json_object"},
    )

    raw_text: str = response.choices[0].message.content or "{}"

    try:
        result: dict = _extract_json(raw_text)
    except (json.JSONDecodeError, ValueError) as exc:
        result = {
            "mfg_date_raw": None,
            "exp_date_raw": None,
            "mfg_confidence": "low",
            "exp_confidence": "low",
            "parse_error": str(exc),
        }

    model_used = getattr(response, "_model_used", "unknown")
    result["model_used"] = model_used
    logging.getLogger(__name__).info("second_read_node executed using model: %s", model_used)

    state["second_result"] = result
    return state
