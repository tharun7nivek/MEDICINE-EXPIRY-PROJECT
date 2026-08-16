"""
speech_route.py
---------------
POST /speech/expiry-summary — Edge neural TTS MP3 for Listen.
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response

from src.api.core.services.speech_service import (
    SpeechService,
    TtsRateLimited,
    TtsUpstreamError,
)
from src.api.schemas.speech import SpeechExpirySummaryRequest

router = APIRouter(tags=["Speech"])
_service = SpeechService()


@router.post("/speech/expiry-summary")
async def expiry_summary_speech(
    body: SpeechExpirySummaryRequest,
    request: Request,
) -> Response:
    client_ip = request.client.host if request.client else "unknown"
    try:
        audio = await _service.synthesize_expiry_summary(
            lang=body.lang,
            expiry_status=body.expiry_status,
            mfg_display=body.mfg_display,
            exp_display=body.exp_display,
            needs_human_review=body.needs_human_review,
            client_ip=client_ip,
        )
    except TtsRateLimited as exc:
        raise HTTPException(status_code=429, detail=str(exc)) from exc
    except TtsUpstreamError as exc:
        raise HTTPException(status_code=502, detail="Speech synthesis failed.") from exc
    return Response(content=audio, media_type="audio/mpeg")
