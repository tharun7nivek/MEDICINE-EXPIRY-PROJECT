"""
expiry_assessment.py
--------------------
Request/response models for deterministic expiry assessment.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

ExpiryStatus = Literal["valid", "expired", "unknown"]
DatePrecision = Literal["day", "month"]
PipelineStatus = Literal["accepted", "human_review"]


class ExpiryAssessment(BaseModel):
    """
    Deterministic client-facing verdict computed on the backend.

    ``expiry_status`` is derived only from the EXP date string vs today.
    ``needs_human_review`` is independent and comes from pipeline status
    (and is forced True when EXP cannot be parsed).
    """

    expiry_status: ExpiryStatus
    is_expired: Optional[bool] = Field(
        default=None,
        description="True if expired, False if not expired, null if unknown.",
    )
    needs_human_review: bool
    mfg_parsed: bool = False
    exp_parsed: bool = False
    mfg_iso: Optional[str] = None
    exp_iso: Optional[str] = None
    exp_valid_through: Optional[str] = Field(
        default=None,
        description="ISO date of the last day the pack is considered valid.",
    )
    exp_precision: Optional[DatePrecision] = None


class AssessRequest(BaseModel):
    """Body for ``POST /api/v1/assess``."""

    final_mfg: Optional[str] = None
    final_exp: Optional[str] = None
    status: PipelineStatus = "accepted"


class AssessResponse(BaseModel):
    """Response body for ``POST /api/v1/assess``."""

    final_mfg: Optional[str] = None
    final_exp: Optional[str] = None
    status: PipelineStatus
    assessment: ExpiryAssessment
