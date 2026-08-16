"""Unit tests for consensus_check_node (deterministic)."""

from __future__ import annotations

from src.api.control.agents.approach_b.consensus_check_node import consensus_check_node


def _base_state(**overrides):
    state = {
        "image_path": "",
        "image_b64": "",
        "attempt": 0,
        "bbox_2d": None,
        "crop_path": "",
        "dewarped_crop_path": "",
        "morph_crop_path": "",
        "crop_source": "yolo",
        "first_result": {
            "mfg_date_raw": "06/2023",
            "exp_date_raw": "05/2026",
            "mfg_confidence": "high",
            "exp_confidence": "high",
        },
        "second_result": {
            "mfg_date_raw": "06/2023",
            "exp_date_raw": "05/2026",
            "mfg_confidence": "high",
            "exp_confidence": "high",
        },
        "consensus_status": "mismatch",
        "reflection_result": None,
        "final_mfg": None,
        "final_exp": None,
        "validation": {},
        "status": "human_review",
    }
    state.update(overrides)
    return state


def test_consensus_match_sets_finals():
    out = consensus_check_node(_base_state())
    assert out["consensus_status"] == "match"
    assert out["final_mfg"] == "06/2023"
    assert out["final_exp"] == "05/2026"


def test_consensus_mismatch_on_disagree():
    out = consensus_check_node(
        _base_state(
            second_result={
                "mfg_date_raw": "07/2023",
                "exp_date_raw": "05/2026",
                "mfg_confidence": "high",
                "exp_confidence": "high",
            }
        )
    )
    assert out["consensus_status"] == "mismatch"
    assert out.get("final_mfg") is None


def test_consensus_low_confidence_on_agree_with_low():
    out = consensus_check_node(
        _base_state(
            first_result={
                "mfg_date_raw": "06/2023",
                "exp_date_raw": "05/2026",
                "mfg_confidence": "low",
                "exp_confidence": "high",
            }
        )
    )
    assert out["consensus_status"] == "low_confidence"


def test_label_prefix_guard_anchors_first_read():
    out = consensus_check_node(
        _base_state(
            second_result={
                "mfg_date_raw": "MFG. D",
                "exp_date_raw": "EXP.",
                "mfg_confidence": "high",
                "exp_confidence": "high",
            }
        )
    )
    assert out["consensus_status"] == "match"
    assert out["final_mfg"] == "06/2023"
    assert out["final_exp"] == "05/2026"
