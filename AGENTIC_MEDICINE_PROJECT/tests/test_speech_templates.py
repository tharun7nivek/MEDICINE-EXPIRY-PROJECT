"""Unit tests for spoken expiry-summary templates."""

from __future__ import annotations

import pytest

from src.api.core.services.speech_templates import render_expiry_summary
from src.api.utils.date_display import SUPPORTED_DISPLAY_LANGS


@pytest.mark.parametrize("lang", SUPPORTED_DISPLAY_LANGS)
def test_all_langs_render_nonempty_summary(lang: str) -> None:
    code, text = render_expiry_summary(
        lang,
        "valid",
        "April 2024",
        "March 2027",
        False,
    )
    assert code == lang
    assert text.strip()
    assert "April 2024" in text
    assert "March 2027" in text


def test_english_ascii_status() -> None:
    _, text = render_expiry_summary("en", "expired", None, None, True)
    assert "has expired" in text
    assert "not found" in text
    assert "human review" in text.lower()
    assert text.isascii()


def test_hindi_and_tamil_native_script() -> None:
    _, hi = render_expiry_summary("hi", "valid", "अप्रैल 2024", None, False)
    assert "दवा" in hi
    assert "अप्रैल 2024" in hi

    _, ta = render_expiry_summary("ta-IN", "expired", None, "மார்ச் 2027", True)
    assert "காலாவதி" in ta
    assert "மார்ச் 2027" in ta
    assert "மனித" in ta
