"""
Paper-parity trapezoid dewarp + sharpen, and morphological binarize.

Geometry matches the published dates.py heuristic (not camera undistort):
  offset = min(50, width // 8)
  dest bottom corners pinch inward by offset
  3x3 high-boost sharpen after warp
  morph: gray → adaptive mean INV (11, 10) → 2x2 close → invert
"""

from __future__ import annotations

import logging
import os

import cv2
import numpy as np

logger = logging.getLogger(__name__)

SHARPEN_KERNEL = np.array(
    [[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]],
    dtype=np.float32,
)


def trapezoid_dewarp(
    image: np.ndarray,
    offset: int | None = None,
    interpolation: int = cv2.INTER_CUBIC,
) -> np.ndarray:
    """Fixed bottom-inward trapezoid warp. Same output size as *image*."""
    h, w = image.shape[:2]
    if offset is None:
        offset = min(50, w // 8)
    src = np.float32([[0, 0], [w - 1, 0], [0, h - 1], [w - 1, h - 1]])
    dst = np.float32(
        [[0, 0], [w - 1, 0], [offset, h - 1], [w - offset, h - 1]]
    )
    matrix = cv2.getPerspectiveTransform(src, dst)
    return cv2.warpPerspective(
        image,
        matrix,
        (w, h),
        flags=interpolation,
        borderMode=cv2.BORDER_REPLICATE,
    )


def sharpen(image: np.ndarray) -> np.ndarray:
    """3x3 high-boost / unsharp-style Laplacian (center 9)."""
    return cv2.filter2D(image, -1, SHARPEN_KERNEL)


def dewarp_and_sharpen(image: np.ndarray) -> np.ndarray:
    """Published pair: trapezoid dewarp then sharpen. On failure, return *image*."""
    try:
        return sharpen(trapezoid_dewarp(image))
    except Exception as exc:
        logger.warning("dewarp_and_sharpen failed (%s); returning original.", exc)
        return image


def morphological_preprocess(image: np.ndarray) -> np.ndarray:
    """
    Adaptive-threshold + morph close + invert → black text on white (uint8 gray).
    """
    if len(image.shape) == 3:
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    else:
        gray = image
    thresh = cv2.adaptiveThreshold(
        gray,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY_INV,
        11,
        10,
    )
    kernel = np.ones((2, 2), np.uint8)
    morph = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
    return cv2.bitwise_not(morph)


def write_morph_crop(crop_path: str) -> str:
    """
    Read *crop_path*, write ``{stem}_crop_morph.png`` beside it, return that path.
    """
    img = cv2.imread(crop_path)
    if img is None:
        raise FileNotFoundError(f"morphological_preprocess: cannot open '{crop_path}'")
    morph = morphological_preprocess(img)
    base, _ext = os.path.splitext(crop_path)
    if base.endswith("_crop"):
        morph_path = f"{base}_morph.png"
    else:
        morph_path = f"{base}_crop_morph.png"
    cv2.imwrite(morph_path, morph)
    return morph_path
