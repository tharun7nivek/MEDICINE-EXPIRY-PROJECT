"""
detect_service.py
-----------------
Service layer for the Approach B YOLO-first date detection pipeline.

Orchestrates: save upload → graph.ainvoke → cleanup → DetectResponse.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Protocol

from src.api.core.services.date_detection_graph import arun_date_detection
from src.api.core.services.expiry_assessment_service import ExpiryAssessmentService
from src.api.data.repositories.detect_storage_repository import DetectStorageRepository
from src.api.schemas.date_detection_state import DateDetectionState
from src.api.schemas.detect_api import DetectResponse, ModelsUsed

logger = logging.getLogger(__name__)


class UploadFileLike(Protocol):
    """Minimal duck-type for FastAPI UploadFile (and tests)."""

    filename: str | None

    async def read(self) -> bytes: ...


class DetectService:
    """
    Async service for the LangGraph date detection pipeline (Approach B).

    Primary entry points for the API layer:
      - detect_upload — multipart UploadFile
      - detect_bytes  — raw image bytes
    """

    def __init__(
        self,
        storage: DetectStorageRepository | None = None,
        assessment: ExpiryAssessmentService | None = None,
    ) -> None:
        self.storage = storage or DetectStorageRepository()
        self.assessment = assessment or ExpiryAssessmentService()

    async def detect_upload(
        self, file: UploadFileLike, lang: str | None = "en"
    ) -> DetectResponse:
        """Run detection on a multipart upload."""
        data = await file.read()
        filename = file.filename or "upload.jpg"
        return await self.detect_bytes(data, filename=filename, lang=lang)

    async def detect_bytes(
        self,
        data: bytes,
        filename: str = "upload.jpg",
        lang: str | None = "en",
    ) -> DetectResponse:
        """
        Persist *data*, run ``compiled_graph.ainvoke``, clean up temps, return DTO.
        """
        request_id, image_path = await self.storage.asave_upload_bytes(
            data, filename=filename
        )
        crop_path = self.storage.crop_path_for(image_path)
        started = time.perf_counter()

        try:
            final_state: DateDetectionState = await arun_date_detection(image_path)
            crop_path = final_state.get("crop_path") or crop_path
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return self._to_response(
                final_state,
                request_id=request_id,
                elapsed_ms=elapsed_ms,
                lang=lang,
            )
        finally:
            await self.storage.acleanup_request(request_id, crop_path)

    async def detect_path(self, image_path: str) -> DetectResponse:
        """
        Convenience for path-based callers: read the file and run detect_bytes.

        Raises FileNotFoundError if *image_path* does not exist.
        """
        if not os.path.isfile(image_path):
            raise FileNotFoundError(
                f"DetectService: image not found at '{image_path}'"
            )
        with open(image_path, "rb") as fh:
            data = fh.read()
        return await self.detect_bytes(data, filename=os.path.basename(image_path))

    def _to_response(
        self,
        final_state: DateDetectionState,
        *,
        request_id: str,
        elapsed_ms: int,
        lang: str | None = "en",
    ) -> DetectResponse:
        first = final_state.get("first_result") or {}
        second = final_state.get("second_result") or {}
        reflection = final_state.get("reflection_result")
        status = final_state.get("status") or "human_review"
        final_mfg = final_state.get("final_mfg")
        final_exp = final_state.get("final_exp")

        return DetectResponse(
            status=status,
            final_mfg=final_mfg,
            final_exp=final_exp,
            validation=final_state.get("validation") or {},
            assessment=self.assessment.assess(
                final_mfg,
                final_exp,
                status=status,
                lang=lang,
            ),
            consensus_status=final_state.get("consensus_status"),
            first_result=first,
            second_result=second,
            reflection_result=reflection,
            crop_path=final_state.get("crop_path") or "",
            crop_source=final_state.get("crop_source"),
            bbox_2d=final_state.get("bbox_2d"),
            models_used=ModelsUsed(
                first=first.get("model_used"),
                second=second.get("model_used"),
                reflection=(reflection or {}).get("model_used") if reflection else None,
            ),
            request_id=request_id,
            elapsed_ms=elapsed_ms,
            model_pipeline="approach_b_yolo_first",
        )
