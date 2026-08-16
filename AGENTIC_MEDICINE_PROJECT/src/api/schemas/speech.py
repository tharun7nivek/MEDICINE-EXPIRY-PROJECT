"""
speech.py
---------
Request body for server-side expiry-summary TTS.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

from src.api.schemas.expiry_assessment import ExpiryStatus


class SpeechExpirySummaryRequest(BaseModel):
    """Body for ``POST /api/v1/speech/expiry-summary``."""

    lang: str = Field(default="en", max_length=16)
    expiry_status: ExpiryStatus
    mfg_display: Optional[str] = Field(default=None, max_length=120)
    exp_display: Optional[str] = Field(default=None, max_length=120)
    needs_human_review: bool = False
