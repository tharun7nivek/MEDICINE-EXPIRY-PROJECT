"""Unit tests for Edge TTS speech service (mocked synthesizer)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from src.api.core.services.speech_service import SpeechService, TtsRateLimited
from src.api.rest.routes import speech_route
from src.api.schemas.speech import SpeechExpirySummaryRequest

_FAKE_MP3 = b"ID3fake-audio"


async def _fake_synth(_text: str, _voice: str) -> bytes:
    return _FAKE_MP3


@pytest.mark.asyncio
async def test_cache_hit_skips_upstream(tmp_path) -> None:
    calls = {"n": 0}

    async def counting_synth(text: str, voice: str) -> bytes:
        calls["n"] += 1
        return _FAKE_MP3

    svc = SpeechService(cache_dir=tmp_path, synthesizer=counting_synth)
    kwargs = dict(
        lang="en",
        expiry_status="valid",
        mfg_display="April 2024",
        exp_display="March 2027",
        needs_human_review=False,
        client_ip="10.0.0.1",
    )
    first = await svc.synthesize_expiry_summary(**kwargs)
    second = await svc.synthesize_expiry_summary(**kwargs)
    assert first == _FAKE_MP3
    assert second == _FAKE_MP3
    assert calls["n"] == 1


@pytest.mark.asyncio
async def test_rate_limit(tmp_path) -> None:
    svc = SpeechService(
        cache_dir=tmp_path,
        rate_limit_per_minute=1,
        synthesizer=_fake_synth,
    )
    await svc.synthesize_expiry_summary(
        lang="en",
        expiry_status="valid",
        mfg_display="A",
        exp_display="B",
        needs_human_review=False,
        client_ip="192.0.2.1",
    )
    with pytest.raises(TtsRateLimited):
        await svc.synthesize_expiry_summary(
            lang="en",
            expiry_status="expired",
            mfg_display="A",
            exp_display="C",
            needs_human_review=False,
            client_ip="192.0.2.1",
        )


def test_oversized_display_rejected() -> None:
    with pytest.raises(ValidationError):
        SpeechExpirySummaryRequest(
            lang="en",
            expiry_status="valid",
            mfg_display="x" * 200,
            exp_display="March 2027",
            needs_human_review=False,
        )


def test_speech_route_returns_mp3(tmp_path, monkeypatch) -> None:
    svc = SpeechService(cache_dir=tmp_path, synthesizer=_fake_synth)
    monkeypatch.setattr(speech_route, "_service", svc)
    app = FastAPI()
    app.include_router(speech_route.router)
    client = TestClient(app)
    response = client.post(
        "/speech/expiry-summary",
        json={
            "lang": "ta",
            "expiry_status": "valid",
            "mfg_display": "ஏப்ரல் 2024",
            "exp_display": "மார்ச் 2027",
            "needs_human_review": False,
        },
    )
    assert response.status_code == 200
    assert response.content == _FAKE_MP3
    assert "audio/mpeg" in response.headers["content-type"]
