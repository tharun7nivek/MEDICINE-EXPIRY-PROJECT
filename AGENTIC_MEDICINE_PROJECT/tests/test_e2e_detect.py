"""
Optional async e2e against POST /api/v1/detect.

Skipped when OpenRouter / Groq keys are missing so CI/unit runs stay offline.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "images"
    / "output_0.png"
)


def _has_api_keys() -> bool:
    return bool(os.getenv("OPENROUTER_API_KEY") and os.getenv("GROQ_API_KEY"))


pytestmark = pytest.mark.skipif(
    not _has_api_keys(),
    reason="OPENROUTER_API_KEY and GROQ_API_KEY required for e2e detect",
)


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_health_ok():
    from src.api.rest.app import app

    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/v1/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["yolo_loaded"] is True
    assert body["status"] in ("ok", "degraded")
    assert body["version"] == "1.0.0"


@pytest.mark.asyncio
async def test_detect_sample_image():
    assert FIXTURE.is_file(), f"missing fixture: {FIXTURE}"

    from src.api.rest.app import app

    transport = ASGITransport(app=app, lifespan="on")
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        with FIXTURE.open("rb") as fh:
            resp = await client.post(
                "/api/v1/detect",
                files={"file": ("output_0.png", fh, "image/png")},
            )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] in ("accepted", "human_review")
    assert body["crop_source"] in ("yolo", "full_image_fallback")
    assert body["model_pipeline"] == "approach_b_yolo_first"
    assert "models_used" in body
    assert body["request_id"]
    assert isinstance(body["elapsed_ms"], int)
