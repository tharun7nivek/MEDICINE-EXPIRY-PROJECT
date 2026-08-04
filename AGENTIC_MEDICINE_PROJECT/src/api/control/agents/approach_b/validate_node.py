"""
validate_node.py
----------------
Node 6 (final) of the Approach B LangGraph pipeline.

Type   : Deterministic — no LLM call.
Purpose: Validate the final MFG/EXP dates against known pharmaceutical
         date formats and basic calendar rules.  The LLM is never the
         last word on whether a date is valid.

Parsing is delegated to ``pack_date_parser`` so pack formats such as
``APR.2024`` / ``MAR.2027`` are accepted consistently with the assessment API.
"""

from __future__ import annotations

from datetime import date

from src.api.schemas.date_detection_state import DateDetectionState
from src.api.utils.pack_date_parser import is_expired, parse_date, parse_pack_date

# Re-export for existing tests / callers.
__all__ = ["parse_date", "validate_node"]


def validate_node(state: DateDetectionState) -> DateDetectionState:
    """
    LangGraph node — validate (deterministic, no LLM).

    Runs structural and calendar validity checks on final_mfg and final_exp.
    Sets state["validation"] (dict of named boolean checks) and
    state["status"] ("accepted" | "human_review").
    """
    today = date.today()
    mfg = parse_pack_date(state.get("final_mfg"))
    exp = parse_pack_date(state.get("final_exp"))

    reflection_unresolved: bool = bool(
        state.get("reflection_result")
        and state["reflection_result"].get("resolution") == "unresolved"
    )

    exp_in_future = bool(exp and not is_expired(exp, today=today))
    exp_after_mfg = bool(
        mfg and exp and exp.valid_through() >= mfg.as_date
    )

    checks: dict = {
        "mfg_parsed": mfg is not None,
        "exp_parsed": exp is not None,
        "exp_after_mfg": exp_after_mfg,
        "exp_in_future": exp_in_future,
        "reflection_unresolved": reflection_unresolved,
    }

    passed: bool = (
        checks["exp_parsed"]
        and checks["exp_in_future"]
        and (not mfg or checks["exp_after_mfg"])
        and not reflection_unresolved
    )

    state["validation"] = checks
    state["status"] = "accepted" if passed else "human_review"
    return state
