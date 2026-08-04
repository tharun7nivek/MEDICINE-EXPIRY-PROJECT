"""Unit tests for validate_node (deterministic)."""

from __future__ import annotations

from datetime import datetime

from src.api.control.agents.approach_b.validate_node import parse_date, validate_node


def _base_state(**overrides):
    # EXP far in the future so exp_in_future stays stable across years.
    future_year = datetime.today().year + 3
    state = {
        "image_path": "",
        "image_b64": "",
        "attempt": 0,
        "bbox_2d": None,
        "crop_path": "",
        "crop_source": "yolo",
        "first_result": {},
        "second_result": {},
        "consensus_status": "match",
        "reflection_result": None,
        "final_mfg": "06/2023",
        "final_exp": f"05/{future_year}",
        "validation": {},
        "status": "human_review",
    }
    state.update(overrides)
    return state


def test_parse_date_known_formats():
    assert parse_date("2024-08") is not None
    assert parse_date("08/2024") is not None
    assert parse_date("AUG2024") is not None
    assert parse_date("15-08-2024") is not None
    assert parse_date("not-a-date") is None
    assert parse_date(None) is None


def test_validate_accepted_when_exp_valid_and_after_mfg():
    out = validate_node(_base_state())
    assert out["status"] == "accepted"
    assert out["validation"]["exp_parsed"] is True
    assert out["validation"]["exp_in_future"] is True
    assert out["validation"]["exp_after_mfg"] is True


def test_validate_human_review_when_exp_unparsed():
    out = validate_node(_base_state(final_exp="N/A"))
    assert out["status"] == "human_review"
    assert out["validation"]["exp_parsed"] is False


def test_validate_human_review_when_reflection_unresolved():
    out = validate_node(
        _base_state(reflection_result={"resolution": "unresolved"})
    )
    assert out["status"] == "human_review"
    assert out["validation"]["reflection_unresolved"] is True
