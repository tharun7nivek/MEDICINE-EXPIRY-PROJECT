"""
consensus_check_node.py
-----------------------
Node 4 of the Approach B LangGraph pipeline.

Type   : Deterministic — no LLM call.
Purpose: Normalise both readers' raw date strings and compare them.  Routes
         to `reflection` when readings disagree OR when either model reported
         low confidence (even if both agree on the value).

A low-confidence agreement still routes to reflection — design doc §2.4:
  "a low-confidence agreement can still be two models making the same mistake."

Implementation follows design doc §2.4 exactly.
"""

import re

from src.api.schemas.date_detection_state import DateDetectionState

# ---------------------------------------------------------------------------
# Regex: a minimal date value contains at least two consecutive digits.
# Label prefixes like 'MFG. D', 'EXP.', 'MFD' contain no digit runs.
# ---------------------------------------------------------------------------
_HAS_DIGITS = re.compile(r"\d{2}")


def _normalize(raw: str | None) -> str | None:
    """
    Normalise a raw date string for comparison:
      - Strip leading/trailing whitespace
      - Uppercase
      - Collapse spaces
      - Collapse double dashes to single dash
    Returns None for null / empty input.
    """
    if not raw:
        return None
    return raw.strip().upper().replace(" ", "").replace("--", "-")


def _looks_like_label_only(raw: str | None) -> bool:
    """
    Return True when *raw* looks like a label prefix fragment rather than an
    actual date value.  A value is considered label-only when it contains no
    run of at least 2 consecutive digits (e.g. 'MFG. D', 'EXP.', 'MFD').
    Numeric dates always contain at least two digits ('06/2023', 'APR2024',
    'MAR. 2027', '05 2025').
    """
    if not raw:
        return False  # null is not a label fragment — treat as missing
    return not bool(_HAS_DIGITS.search(raw))


def consensus_check_node(state: DateDetectionState) -> DateDetectionState:
    """
    LangGraph node — consensus_check (deterministic, no LLM).

    Compares the two independent readings and sets state["consensus_status"]:
      "match"          → both readers agree AND neither field is "low" confidence
      "low_confidence" → both readers agree BUT at least one field is "low"
      "mismatch"       → the readers disagree on at least one field

    Label-prefix guard:
      If second_read returns a label fragment (e.g. 'MFG. D') with no digit content
      while first_read returns a numeric date, the numeric reading is anchored as the
      "match" result without calling Reflection. This prevents Reflection from
      wrongly discarding a valid numeric date in favour of a label header fragment.

    On "match", also sets state["final_mfg"] and state["final_exp"] from the
    normalised values of first_result (reader A), ready for the validate node.

    Returns the mutated state dict.
    """
    a: dict = state["first_result"]
    b: dict = state["second_result"]

    a_mfg_raw = a.get("mfg_date_raw")
    a_exp_raw = a.get("exp_date_raw")
    b_mfg_raw = b.get("mfg_date_raw")
    b_exp_raw = b.get("exp_date_raw")

    # ---------------------------------------------------------------------------
    # Label-prefix guard: if second_read returned only a label fragment (no digits)
    # while first_read has a numeric date, use first_read's reading directly.
    # This prevents Reflection from trusting 'MFG. D' over '06/2023'.
    # ---------------------------------------------------------------------------
    b_mfg_is_label = _looks_like_label_only(b_mfg_raw)
    b_exp_is_label = _looks_like_label_only(b_exp_raw)
    a_mfg_is_label = _looks_like_label_only(a_mfg_raw)
    a_exp_is_label = _looks_like_label_only(a_exp_raw)

    # If second_read produced label fragments but first_read has numeric dates: anchor A
    if (b_mfg_is_label or b_exp_is_label) and not (a_mfg_is_label and a_exp_is_label):
        state["consensus_status"] = "match"
        state["final_mfg"] = _normalize(a_mfg_raw) if not a_mfg_is_label else None
        state["final_exp"] = _normalize(a_exp_raw) if not a_exp_is_label else None
        return state

    mfg_match = _normalize(a_mfg_raw) == _normalize(b_mfg_raw)
    exp_match = _normalize(a_exp_raw) == _normalize(b_exp_raw)

    any_low = "low" in (
        a.get("mfg_confidence"),
        a.get("exp_confidence"),
        b.get("mfg_confidence"),
        b.get("exp_confidence"),
    )

    if mfg_match and exp_match and not any_low:
        state["consensus_status"] = "match"
        state["final_mfg"] = _normalize(a_mfg_raw)
        state["final_exp"] = _normalize(a_exp_raw)
    elif mfg_match and exp_match:
        # Agreement with low confidence → send to reflection for a closer look
        state["consensus_status"] = "low_confidence"
    else:
        state["consensus_status"] = "mismatch"

    return state
