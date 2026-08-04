"""
date_detection_state.py
-----------------------
State schema for the Approach B LangGraph date detection pipeline
(YOLO-first localization → dual crop readers → optional reflection).
"""

from typing import Optional, Literal, TypedDict


class DateDetectionState(TypedDict):
    # -----------------------------------------------------------------------
    # Input
    # -----------------------------------------------------------------------
    image_path: str
    """Absolute path to the original raw medicine package image."""

    image_b64: str
    """Base64-encoded data URL of the full original image (data:image/...;base64,...)."""

    attempt: int
    """Graph execution attempt counter (starts at 0, reserved for future retry logic)."""

    # -----------------------------------------------------------------------
    # Node 1 — crop_zoom (YOLO) outputs
    # -----------------------------------------------------------------------
    bbox_2d: Optional[list[int]]
    """
    Bounding box [x1, y1, x2, y2] of the date region in original image coords,
    set from the YOLO union rect (or the full image on fallback).
    """

    crop_path: str
    """Absolute path to the saved cropped+upscaled date-region image."""

    crop_source: Literal["yolo", "full_image_fallback"]
    """
    How the crop was produced:
      "yolo"                 — YOLO detected a date region
      "full_image_fallback"  — no detection; crop is the full original image
    """

    # -----------------------------------------------------------------------
    # Node 2 — first_read output
    # -----------------------------------------------------------------------
    first_result: dict
    """
    Raw JSON dict returned by the first_read (crop OCR) node, containing:
      mfg_date_raw, exp_date_raw, mfg_confidence, exp_confidence,
      ambiguous_characters
    """

    # -----------------------------------------------------------------------
    # Node 3 — second_read output
    # -----------------------------------------------------------------------
    second_result: dict
    """
    Raw JSON dict returned by the second_read (crop OCR) node, containing:
      mfg_date_raw, exp_date_raw, mfg_confidence, exp_confidence
    """

    # -----------------------------------------------------------------------
    # Node 4 — consensus_check output
    # -----------------------------------------------------------------------
    consensus_status: Literal["match", "mismatch", "low_confidence"]
    """
    Outcome of the deterministic string comparison:
      "match"          — both readings agree and neither reported low confidence
      "mismatch"       — readings disagree on at least one field
      "low_confidence" — readings agree but at least one field was rated "low"
    """

    # -----------------------------------------------------------------------
    # Intermediate resolved values (set on match path, or by reflection)
    # -----------------------------------------------------------------------
    final_mfg: Optional[str]
    """Normalized manufacturing date string chosen as the final answer, or None."""

    final_exp: Optional[str]
    """Normalized expiration date string chosen as the final answer, or None."""

    # -----------------------------------------------------------------------
    # Node 5 — reflection output (only populated on mismatch / low_confidence)
    # -----------------------------------------------------------------------
    reflection_result: Optional[dict]
    """
    Raw JSON dict returned by the reflection node (or None if not invoked):
      resolution, mfg_date_raw, exp_date_raw, evidence_note
    """

    # -----------------------------------------------------------------------
    # Node 6 — validate output
    # -----------------------------------------------------------------------
    validation: dict
    """
    Dict of boolean validation checks produced by the deterministic validate node:
      mfg_parsed, exp_parsed, exp_after_mfg, exp_in_future, reflection_unresolved
    """

    status: Literal["accepted", "human_review"]
    """
    Final pipeline outcome:
      "accepted"     — dates passed all structural and calendar checks
      "human_review" — validation failed or reflection could not resolve disagreement
    """
