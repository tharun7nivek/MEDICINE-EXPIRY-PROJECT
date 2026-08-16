"""
detect_api.py
-------------
Pydantic request/response models for the public Date Detection API (v1).
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

from src.api.schemas.expiry_assessment import ExpiryAssessment


class ModelsUsed(BaseModel):
    """Model ids used for each pipeline stage (null when stage did not run)."""

    first: Optional[str] = None
    second: Optional[str] = None
    reflection: Optional[str] = None


class DetectResponse(BaseModel):
    """
    Response body for ``POST /api/v1/detect``.

    Mirrors the service DTO produced after ``compiled_graph.ainvoke``,
    plus a deterministic ``assessment`` block for UI/TTS.
    """

    status: Literal["accepted", "human_review"]
    final_mfg: Optional[str] = None
    final_exp: Optional[str] = None
    consensus_status: Optional[
        Literal["match", "mismatch", "low_confidence"]
    ] = None
    validation: dict[str, Any] = Field(default_factory=dict)
    assessment: ExpiryAssessment
    bbox_2d: Optional[list[int]] = None
    crop_source: Optional[Literal["yolo", "full_image_fallback"]] = None
    crop_path: str = ""
    models_used: ModelsUsed = Field(default_factory=ModelsUsed)
    first_result: dict[str, Any] = Field(default_factory=dict)
    second_result: dict[str, Any] = Field(default_factory=dict)
    reflection_result: Optional[dict[str, Any]] = None
    request_id: str
    elapsed_ms: int
    model_pipeline: str = "approach_b_yolo_first"


class HealthResponse(BaseModel):
    """Response body for ``GET /api/v1/health``."""

    status: Literal["ok", "degraded"]
    version: str
    yolo_loaded: bool
    openrouter_keys: int
    groq_keys: int
    storage_dir: str
    tts_configured: bool = False


class ApiRootResponse(BaseModel):
    """Response body for ``GET /api/v1/``."""

    name: str
    version: str
    endpoints: dict[str, str]
