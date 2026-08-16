"""Unit tests for paper-parity dewarp + morphological preprocess."""

from __future__ import annotations

import numpy as np

from src.api.utils.image_preprocess import (
    dewarp_and_sharpen,
    morphological_preprocess,
    trapezoid_dewarp,
)


def test_trapezoid_dewarp_keeps_shape():
    img = np.full((80, 160, 3), 180, dtype=np.uint8)
    out = trapezoid_dewarp(img)
    assert out.shape == img.shape


def test_dewarp_and_sharpen_keeps_shape():
    img = np.full((64, 64, 3), 100, dtype=np.uint8)
    out = dewarp_and_sharpen(img)
    assert out.shape == img.shape


def test_morph_output_is_gray_same_hw():
    img = np.zeros((40, 50, 3), dtype=np.uint8)
    img[10:30, 15:35] = 255
    out = morphological_preprocess(img)
    assert out.ndim == 2
    assert out.shape == (40, 50)
    assert set(np.unique(out)).issubset({0, 255})
