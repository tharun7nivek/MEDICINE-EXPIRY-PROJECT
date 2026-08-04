"""
expiry_assessment_service.py
----------------------------
Service layer: deterministic expired / not-expired + human-review flags.
"""

from __future__ import annotations

from datetime import date
from typing import Literal, Optional

from src.api.schemas.expiry_assessment import (
    AssessRequest,
    AssessResponse,
    ExpiryAssessment,
)
from src.api.utils.pack_date_parser import is_expired, parse_pack_date

PipelineStatus = Literal["accepted", "human_review"]


class ExpiryAssessmentService:
    """
    Pure deterministic assessment — no LLM calls.

    Used by:
      - DetectService (embedded in DetectResponse.assessment)
      - POST /api/v1/assess
    """

    def assess(
        self,
        final_mfg: str | None,
        final_exp: str | None,
        *,
        status: PipelineStatus = "accepted",
        today: date | None = None,
    ) -> ExpiryAssessment:
        ref = today or date.today()
        mfg = parse_pack_date(final_mfg)
        exp = parse_pack_date(final_exp)

        if exp is None:
            expiry_status: Literal["valid", "expired", "unknown"] = "unknown"
            expired: Optional[bool] = None
        elif is_expired(exp, today=ref):
            expiry_status = "expired"
            expired = True
        else:
            expiry_status = "valid"
            expired = False

        # Human review: pipeline flag, or unreadable EXP.
        needs_review = status == "human_review" or exp is None

        return ExpiryAssessment(
            expiry_status=expiry_status,
            is_expired=expired,
            needs_human_review=needs_review,
            mfg_parsed=mfg is not None,
            exp_parsed=exp is not None,
            mfg_iso=mfg.as_date.isoformat() if mfg else None,
            exp_iso=exp.as_date.isoformat() if exp else None,
            exp_valid_through=exp.valid_through().isoformat() if exp else None,
            exp_precision=exp.precision if exp else None,
        )

    def assess_request(
        self,
        body: AssessRequest,
        *,
        today: date | None = None,
    ) -> AssessResponse:
        assessment = self.assess(
            body.final_mfg,
            body.final_exp,
            status=body.status,
            today=today,
        )
        return AssessResponse(
            final_mfg=body.final_mfg,
            final_exp=body.final_exp,
            status=body.status,
            assessment=assessment,
        )
