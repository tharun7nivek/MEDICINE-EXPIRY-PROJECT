"""
crop_zoom_node.py
-----------------
Entry node of the Approach B LangGraph pipeline.

Type   : Deterministic — no LLM call.
Purpose: Produce a semantically precise crop of the medicine-label date area using
         the fine-tuned YOLO segmentation model (best.pt) as the sole locator.
         On YOLO miss, fall back to a full-image crop (no VLM bbox).

YOLO strategy:
  Run best.pt on the full image.  best.pt is a segmentation model fine-tuned on
  medicine packaging images.  It detects two classes:
    • 0: 'MFD_DATE'  — manufacturing date region
    • 1: 'mfddatexp' — combined MFG + EXP date region
  All masks with confidence ≥ YOLO_CONF_THRESHOLD are collected, their
  contour bounding rectangles are computed, and the UNION rectangle of all of
  them is used as the crop boundary.  A 15% safety padding is applied.

  If YOLO finds no valid mask, the full original image is used as the crop
  (crop_source = "full_image_fallback") and bbox_2d spans the full image.

Model loading:
  best.pt / ultralytics are required at startup.  Import fails hard if either
  is missing so the API cannot start without localization.

OpenCV and YOLO inference run via asyncio.to_thread so they do not block the
event loop when the graph is invoked asynchronously.
"""

from __future__ import annotations

import asyncio
import logging
import os
from pathlib import Path

import cv2
import numpy as np
from ultralytics import YOLO

from src.api.schemas.date_detection_state import DateDetectionState

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YOLO_WEIGHTS_PATH = str(
    Path(__file__).resolve().parents[3] / "utils" / "yolo" / "best.pt"
)

# Confidence threshold: masks below this value are ignored.
YOLO_CONF_THRESHOLD = 0.25

# Safety padding applied around the YOLO union bounding box (15% of each side).
YOLO_PAD_RATIO = 0.15

# Any crop narrower than this is upscaled with cubic interpolation so crop
# readers can distinguish individual characters comfortably.
MIN_CROP_WIDTH = 500

# ---------------------------------------------------------------------------
# YOLO model — required at import time
# ---------------------------------------------------------------------------
if not os.path.isfile(YOLO_WEIGHTS_PATH):
    raise FileNotFoundError(
        f"crop_zoom_node: YOLO weights not found at '{YOLO_WEIGHTS_PATH}'. "
        "best.pt is required for date localization."
    )

try:
    _yolo_model = YOLO(YOLO_WEIGHTS_PATH)
    logger.info("crop_zoom_node: YOLO model loaded from '%s'.", YOLO_WEIGHTS_PATH)
except Exception as _err:
    raise RuntimeError(
        f"crop_zoom_node: failed to load YOLO model from '{YOLO_WEIGHTS_PATH}': {_err}"
    ) from _err


def is_yolo_loaded() -> bool:
    """Return True when the process-global YOLO model is available."""
    return _yolo_model is not None


# ---------------------------------------------------------------------------
# Helpers (sync — executed via asyncio.to_thread)
# ---------------------------------------------------------------------------

def _get_yolo_crop_rect(img: np.ndarray) -> tuple[int, int, int, int] | None:
    """
    Run YOLO inference on *img* and return the union bounding rectangle
    [x1, y1, x2, y2] of all detected date-field masks with confidence
    ≥ YOLO_CONF_THRESHOLD.

    Returns ``None`` when no valid mask is found.
    """
    h, w = img.shape[:2]

    try:
        results = _yolo_model(img, verbose=False)
    except Exception as exc:
        logger.warning("crop_zoom_node: YOLO inference failed (%s).", exc)
        return None

    union_x1 = w
    union_y1 = h
    union_x2 = 0
    union_y2 = 0
    found_any = False

    for result in results:
        if result.masks is None:
            continue

        masks_data = result.masks.data  # shape: (N, H_mask, W_mask)
        confidences = result.boxes.conf.cpu().numpy()

        for mask_tensor, conf in zip(masks_data, confidences):
            if float(conf) < YOLO_CONF_THRESHOLD:
                continue

            mask_np = (mask_tensor.cpu().numpy() * 255).astype(np.uint8)
            mask_np = cv2.resize(mask_np, (w, h), interpolation=cv2.INTER_NEAREST)

            contours, _ = cv2.findContours(
                mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )

            for contour in contours:
                bx, by, bw, bh = cv2.boundingRect(contour)
                union_x1 = min(union_x1, bx)
                union_y1 = min(union_y1, by)
                union_x2 = max(union_x2, bx + bw)
                union_y2 = max(union_y2, by + bh)
                found_any = True

    if not found_any:
        return None

    if union_x2 <= union_x1 or union_y2 <= union_y1:
        return None

    return union_x1, union_y1, union_x2, union_y2


def _prepare_crop(
    img: np.ndarray,
    yolo_rect: tuple[int, int, int, int] | None,
) -> tuple[np.ndarray, list[int], str]:
    """
    Build the crop ndarray, bbox_2d, and crop_source from YOLO (or full image).

    Returns (crop, bbox_2d, crop_source).
    """
    h, w = img.shape[:2]

    if yolo_rect is not None:
        x1, y1, x2, y2 = yolo_rect
        box_w = x2 - x1
        box_h = y2 - y1

        pad_x = int(box_w * YOLO_PAD_RATIO)
        pad_y = int(box_h * YOLO_PAD_RATIO)

        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)

        crop = img[y1:y2, x1:x2]
        crop_source = "yolo"
        bbox_2d = [x1, y1, x2, y2]
    else:
        logger.info("crop_zoom_node: no YOLO mask found. Using full-image fallback.")
        crop = img
        crop_source = "full_image_fallback"
        bbox_2d = [0, 0, w, h]

    if crop.size == 0:
        logger.warning(
            "crop_zoom_node: degenerate crop from %s, falling back to full image.",
            crop_source,
        )
        crop = img
        crop_source = "full_image_fallback"
        bbox_2d = [0, 0, w, h]

    if crop.shape[1] < MIN_CROP_WIDTH:
        scale = MIN_CROP_WIDTH / crop.shape[1]
        crop = cv2.resize(
            crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC
        )

    return crop, bbox_2d, crop_source


def _write_crop(image_path: str, crop: np.ndarray) -> str:
    """Write *crop* next to *image_path* and return the crop path."""
    base, ext = os.path.splitext(image_path)
    crop_path = f"{base}_crop{ext}"
    cv2.imwrite(crop_path, crop)
    return crop_path


def _run_crop_pipeline(image_path: str) -> tuple[str, list[int], str]:
    """
    Synchronous OpenCV + YOLO pipeline (imread → detect → crop → imwrite).

    Returns (crop_path, bbox_2d, crop_source).
    """
    img = cv2.imread(image_path)
    if img is None:
        raise FileNotFoundError(
            f"crop_zoom_node: cannot open image at '{image_path}'"
        )

    yolo_rect = _get_yolo_crop_rect(img)
    crop, bbox_2d, crop_source = _prepare_crop(img, yolo_rect)
    crop_path = _write_crop(image_path, crop)
    return crop_path, bbox_2d, crop_source


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------

async def crop_zoom_node(state: DateDetectionState) -> DateDetectionState:
    """
    LangGraph node — crop_zoom (deterministic, no LLM).

    YOLO-only localization.  On miss, uses the full image as the crop.
    Sets crop_path, bbox_2d, and crop_source ("yolo" | "full_image_fallback").
    """
    image_path: str = state["image_path"]
    crop_path, bbox_2d, crop_source = await asyncio.to_thread(
        _run_crop_pipeline, image_path
    )

    state["crop_path"] = crop_path
    state["bbox_2d"] = bbox_2d
    state["crop_source"] = crop_source  # type: ignore[typeddict-item]
    return state
