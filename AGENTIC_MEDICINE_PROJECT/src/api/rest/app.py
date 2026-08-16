"""
app.py
------
FastAPI application entry for the Date Detection API (v1).

Lifespan initialises API key pools and verifies YOLO weights are loaded.
All public routes live under ``/api/v1``.
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.config.settings import (
    CORS_ORIGINS,
    GROQ_KEYS,
    OPENROUTER_KEYS,
    STORAGE_DIR,
)

logger = logging.getLogger(__name__)

APP_VERSION = "1.0.0"


def _init_runtime() -> dict:
    """
    Load key pools + YOLO and ensure storage exists.

    Importing the graph / crop_zoom modules performs the actual load;
    this helper records readiness for the health endpoint.
    """
    os.makedirs(STORAGE_DIR, exist_ok=True)

    # Key pools are initialised as a side effect of importing the graph module.
    from src.api.core.services import date_detection_graph as graph_mod  # noqa: F401

    # YOLO is required at crop_zoom import time.
    from src.api.control.agents.approach_b.crop_zoom_node import (
        YOLO_WEIGHTS_PATH,
        is_yolo_loaded,
    )

    yolo_loaded = is_yolo_loaded()
    if not yolo_loaded:
        raise RuntimeError(
            f"YOLO model failed to load from '{YOLO_WEIGHTS_PATH}'."
        )

    runtime = {
        "yolo_loaded": yolo_loaded,
        "yolo_weights": YOLO_WEIGHTS_PATH,
        "openrouter_keys": len(OPENROUTER_KEYS),
        "groq_keys": len(GROQ_KEYS),
        "storage_dir": STORAGE_DIR,
        "tts_configured": True,
    }
    logger.info(
        "Runtime ready: YOLO=%s openrouter_keys=%d groq_keys=%d storage=%s",
        yolo_loaded,
        runtime["openrouter_keys"],
        runtime["groq_keys"],
        STORAGE_DIR,
    )
    return runtime


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.runtime = _init_runtime()
    yield


app = FastAPI(
    title="Agentic Medicine — Date Detection API",
    description=(
        "Medicine package MFG/EXP date detection. "
        "YOLO-first localization → dual qwen crop readers → optional omni reflection."
    ),
    version=APP_VERSION,
    lifespan=lifespan,
)

# Starlette will not send ACAO for allow_origins=["*"] + credentials=True.
_allow_all = CORS_ORIGINS == ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=not _allow_all,
    allow_methods=["*"],
    allow_headers=["*"],
)

from src.api.rest.routes.detect_route import router as detect_router  # noqa: E402
from src.api.rest.routes.speech_route import router as speech_router  # noqa: E402

app.include_router(detect_router, prefix="/api/v1")
app.include_router(speech_router, prefix="/api/v1")
