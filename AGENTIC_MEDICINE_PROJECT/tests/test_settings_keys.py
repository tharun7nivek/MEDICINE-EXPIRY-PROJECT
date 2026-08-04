"""Unit tests for portable, N-key API key discovery."""

from __future__ import annotations

from src.api.config.settings import load_numbered_api_keys


def test_loads_unsuffixed_and_numbered_keys_any_count():
    env = {
        "GROQ_API_KEY": "g1",
        "GROQ_API_KEY_2": "g2",
        "GROQ_API_KEY_3": "g3",
        "GROQ_API_KEY_4": "g4",
        "GROQ_API_KEY_11": "g11",  # gaps / >10 must work
        "UNRELATED": "nope",
    }
    assert load_numbered_api_keys("GROQ_API_KEY", env) == [
        "g1",
        "g2",
        "g3",
        "g4",
        "g11",
    ]


def test_csv_form_and_dedupe():
    env = {
        "OPENROUTER_API_KEYS": "a, b; c",
        "OPENROUTER_API_KEY": "a",  # duplicate of first CSV entry
        "OPENROUTER_API_KEY_2": "d",
    }
    assert load_numbered_api_keys("OPENROUTER_API_KEY", env) == ["a", "b", "c", "d"]


def test_strips_quotes_and_skips_empty():
    env = {
        "GROQ_API_KEY": '  "quoted"  ',
        "GROQ_API_KEY_2": "",
        "GROQ_API_KEY_3": "   ",
        "GROQ_API_KEY_4": "real",
    }
    assert load_numbered_api_keys("GROQ_API_KEY", env) == ["quoted", "real"]


def test_four_and_four_machine_shape():
    """Other devices may only have 4+4 keys — still a valid pool."""
    env = {
        "OPENROUTER_API_KEY": "o1",
        "OPENROUTER_API_KEY_2": "o2",
        "OPENROUTER_API_KEY_3": "o3",
        "OPENROUTER_API_KEY_4": "o4",
        "GROQ_API_KEY": "g1",
        "GROQ_API_KEY_2": "g2",
        "GROQ_API_KEY_3": "g3",
        "GROQ_API_KEY_4": "g4",
    }
    assert len(load_numbered_api_keys("OPENROUTER_API_KEY", env)) == 4
    assert len(load_numbered_api_keys("GROQ_API_KEY", env)) == 4
