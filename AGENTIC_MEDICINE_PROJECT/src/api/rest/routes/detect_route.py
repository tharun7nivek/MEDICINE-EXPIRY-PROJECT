"""
detect_route.py
---------------
Public v1 REST routes for medicine package date detection.

Endpoints (mounted under ``/api/v1``):
  GET  /           — API welcome / discovery
  GET  /health     — readiness (keys + YOLO)
  POST /detect     — multipart image upload → DetectResponse (+ assessment)
  POST /assess     — deterministic expiry assessment from MFG/EXP strings
"""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile, Request

from src.api.core.services.detect_service import DetectService
from src.api.core.services.expiry_assessment_service import ExpiryAssessmentService
from src.api.schemas.detect_api import (
    ApiRootResponse,
    DetectResponse,
    HealthResponse,
)
from src.api.schemas.expiry_assessment import AssessRequest, AssessResponse

router = APIRouter(tags=["Date Detection"])

_service = DetectService()
_assessment_service = ExpiryAssessmentService()

_ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/bmp",
    "application/octet-stream",  # some clients omit a proper image type
}


@router.get("/", response_model=ApiRootResponse)
def api_root() -> ApiRootResponse:
    """API discovery for the v1 surface."""
    return ApiRootResponse(
        name="Agentic Medicine — Date Detection API",
        version="1.0.0",
        endpoints={
            "health": "GET /api/v1/health",
            "detect": "POST /api/v1/detect",
            "assess": "POST /api/v1/assess",
        },
    )


@router.get("/health", response_model=HealthResponse)
def health_check(request: Request) -> HealthResponse:
    """
    Report process readiness: YOLO weights loaded and API key pools present.
    """
    runtime = getattr(request.app.state, "runtime", {})
    yolo_loaded = bool(runtime.get("yolo_loaded", False))
    openrouter_keys = int(runtime.get("openrouter_keys", 0))
    groq_keys = int(runtime.get("groq_keys", 0))
    storage_dir = str(runtime.get("storage_dir", ""))

    status = "ok" if yolo_loaded and openrouter_keys > 0 else "degraded"
    return HealthResponse(
        status=status,
        version="1.0.0",
        yolo_loaded=yolo_loaded,
        openrouter_keys=openrouter_keys,
        groq_keys=groq_keys,
        storage_dir=storage_dir,
    )


@router.post("/detect", response_model=DetectResponse)
async def detect(file: UploadFile = File(...)) -> DetectResponse:
    """
    Run the YOLO-first LangGraph date detection pipeline on an uploaded image.

    Multipart form field: ``file`` (JPEG/PNG/WebP/BMP).
    Response includes ``assessment`` (expired / not expired + human review).
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="Upload must include a filename.")

    content_type = (file.content_type or "").lower()
    if content_type and content_type not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported content type: {content_type}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    # Re-wrap as a simple object so the service can read bytes again.
    class _Upload:
        filename = file.filename

        async def read(self) -> bytes:
            return data

    try:
        return await _service.detect_upload(_Upload())
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Pipeline error: {exc}",
        ) from exc


@router.post("/assess", response_model=AssessResponse)
def assess_dates(body: AssessRequest) -> AssessResponse:
    """
    Deterministically assess whether a pack is expired and whether human
    review is needed. Accepts many printed MFG/EXP date formats.
    """
    return _assessment_service.assess_request(body)
