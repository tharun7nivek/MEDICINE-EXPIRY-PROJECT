"""
detect_storage_repository.py
-----------------------------
Temp file storage for the Approach B detect pipeline.

Persists multipart / byte uploads under ``storage/uploads/{request_id}/``,
tracks crop paths produced by crop_zoom (written beside the upload), and
cleans them up after the response unless RETAIN_DETECT_TEMPS is set.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
from pathlib import Path
from uuid import uuid4

from src.api.config.settings import RETAIN_DETECT_TEMPS, STORAGE_DIR

logger = logging.getLogger(__name__)

_SAFE_NAME = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_filename(filename: str) -> str:
    """Return a filesystem-safe basename with a default extension if needed."""
    name = os.path.basename(filename or "").strip() or "upload.jpg"
    name = _SAFE_NAME.sub("_", name)
    if not os.path.splitext(name)[1]:
        name = f"{name}.jpg"
    return name


class DetectStorageRepository:
    """
    Thin local-disk repository for detect uploads and intermediate crops.

    Layout::

        {storage_dir}/
          uploads/
            {request_id}/
              {filename}
              {stem}_crop{ext}   # written by crop_zoom next to the upload
    """

    def __init__(
        self,
        storage_dir: str | None = None,
        retain: bool | None = None,
    ) -> None:
        self.storage_dir = os.path.abspath(storage_dir or STORAGE_DIR)
        self.uploads_dir = os.path.join(self.storage_dir, "uploads")
        self.retain = RETAIN_DETECT_TEMPS if retain is None else retain
        os.makedirs(self.uploads_dir, exist_ok=True)

    def new_request_id(self) -> str:
        return uuid4().hex

    def request_dir(self, request_id: str) -> str:
        return os.path.join(self.uploads_dir, request_id)

    def save_upload_bytes(
        self,
        data: bytes,
        filename: str = "upload.jpg",
        request_id: str | None = None,
    ) -> tuple[str, str]:
        """
        Write *data* under ``storage/uploads/{request_id}/``.

        Returns ``(request_id, absolute_image_path)``.
        """
        if not data:
            raise ValueError("DetectStorageRepository: empty upload bytes")

        rid = request_id or self.new_request_id()
        dest_dir = self.request_dir(rid)
        os.makedirs(dest_dir, exist_ok=True)

        safe_name = _sanitize_filename(filename)
        image_path = os.path.join(dest_dir, safe_name)
        with open(image_path, "wb") as fh:
            fh.write(data)

        logger.debug(
            "DetectStorageRepository: saved upload %s (%d bytes)",
            image_path,
            len(data),
        )
        return rid, image_path

    async def asave_upload_bytes(
        self,
        data: bytes,
        filename: str = "upload.jpg",
        request_id: str | None = None,
    ) -> tuple[str, str]:
        return await asyncio.to_thread(
            self.save_upload_bytes, data, filename, request_id
        )

    def crop_path_for(self, image_path: str) -> str:
        """Return the crop path crop_zoom writes beside *image_path*."""
        base, ext = os.path.splitext(image_path)
        return f"{base}_crop{ext}"

    def cleanup_paths(self, *paths: str) -> None:
        """Delete the given files when retain is False."""
        if self.retain:
            return
        for path in paths:
            if not path:
                continue
            try:
                if os.path.isfile(path):
                    os.remove(path)
                    logger.debug("DetectStorageRepository: removed %s", path)
            except OSError as exc:
                logger.warning(
                    "DetectStorageRepository: failed to remove '%s': %s", path, exc
                )

    def cleanup_request(self, request_id: str, *extra_paths: str) -> None:
        """
        Remove upload/crop files for *request_id* and drop the request directory.

        Extra paths outside the request dir (if any) are also deleted.
        """
        if self.retain:
            return

        req_dir = self.request_dir(request_id)
        for extra in extra_paths:
            if extra and not self._is_under(extra, req_dir):
                self.cleanup_paths(extra)

        if os.path.isdir(req_dir):
            try:
                shutil.rmtree(req_dir)
                logger.debug(
                    "DetectStorageRepository: removed request dir %s", req_dir
                )
            except OSError as exc:
                logger.warning(
                    "DetectStorageRepository: failed to remove dir '%s': %s",
                    req_dir,
                    exc,
                )

    async def acleanup_request(self, request_id: str, *extra_paths: str) -> None:
        await asyncio.to_thread(self.cleanup_request, request_id, *extra_paths)

    @staticmethod
    def _is_under(path: str, parent: str) -> bool:
        try:
            Path(path).resolve().relative_to(Path(parent).resolve())
            return True
        except ValueError:
            return False
