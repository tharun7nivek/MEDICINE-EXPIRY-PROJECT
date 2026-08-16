"""
speech_service.py
-----------------
Microsoft Edge neural TTS (edge-tts) for localized expiry summaries.
No API key. Disk cache + in-process per-IP rate limiting.
"""

from __future__ import annotations

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from collections.abc import Awaitable, Callable
from pathlib import Path

from src.api.config.settings import SPEECH_CACHE_DIR, TTS_RATE_LIMIT_PER_MINUTE
from src.api.core.services.speech_templates import TEMPLATE_VERSION, render_expiry_summary
from src.api.schemas.expiry_assessment import ExpiryStatus

logger = logging.getLogger(__name__)

SynthesizeFn = Callable[[str, str], Awaitable[bytes]]

# Pinned female (or standard) neural voices for India locales.
_EDGE_VOICES: dict[str, str] = {
    "en": "en-IN-NeerjaNeural",
    "hi": "hi-IN-SwaraNeural",
    "ta": "ta-IN-PallaviNeural",
    "te": "te-IN-ShrutiNeural",
    "mr": "mr-IN-AarohiNeural",
    "bn": "bn-IN-TanishaaNeural",
    "gu": "gu-IN-DhwaniNeural",
    "kn": "kn-IN-SapnaNeural",
    "ml": "ml-IN-SobhanaNeural",
    "pa": "pa-IN-GaganNeural",
}


class TtsRateLimited(Exception):
    """Caller exceeded the per-minute Listen budget."""


class TtsUpstreamError(Exception):
    """Edge TTS request failed."""


class _RateLimiter:
    def __init__(self, per_minute: int) -> None:
        self._per_minute = max(1, per_minute)
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        window = 60.0
        with self._lock:
            bucket = self._hits[key]
            while bucket and now - bucket[0] > window:
                bucket.popleft()
            if len(bucket) >= self._per_minute:
                return False
            bucket.append(now)
            return True


async def _edge_synthesize(text: str, voice: str) -> bytes:
    import edge_tts

    chunks: list[bytes] = []
    communicate = edge_tts.Communicate(text, voice)
    async for message in communicate.stream():
        if message["type"] == "audio":
            chunks.append(message["data"])
    audio = b"".join(chunks)
    if not audio:
        raise TtsUpstreamError("Empty TTS audio")
    return audio


class SpeechService:
    def __init__(
        self,
        *,
        cache_dir: str | Path | None = None,
        rate_limit_per_minute: int | None = None,
        synthesizer: SynthesizeFn | None = None,
    ) -> None:
        self._cache_dir = Path(cache_dir or SPEECH_CACHE_DIR)
        self._limiter = _RateLimiter(
            rate_limit_per_minute
            if rate_limit_per_minute is not None
            else TTS_RATE_LIMIT_PER_MINUTE
        )
        self._synthesizer = synthesizer or _edge_synthesize

    @property
    def configured(self) -> bool:
        return True

    def _cache_path(
        self,
        lang: str,
        expiry_status: ExpiryStatus,
        mfg_display: str | None,
        exp_display: str | None,
        needs_human_review: bool,
        voice_name: str,
    ) -> Path:
        payload = "|".join(
            [
                TEMPLATE_VERSION,
                lang,
                expiry_status,
                mfg_display or "",
                exp_display or "",
                "1" if needs_human_review else "0",
                voice_name,
            ]
        )
        digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        return self._cache_dir / f"{digest}.mp3"

    async def synthesize_expiry_summary(
        self,
        *,
        lang: str,
        expiry_status: ExpiryStatus,
        mfg_display: str | None,
        exp_display: str | None,
        needs_human_review: bool,
        client_ip: str,
    ) -> bytes:
        if not self._limiter.allow(client_ip or "unknown"):
            raise TtsRateLimited("Too many speech requests.")

        code, text = render_expiry_summary(
            lang, expiry_status, mfg_display, exp_display, needs_human_review
        )
        voice = _EDGE_VOICES[code]
        cache_path = self._cache_path(
            code,
            expiry_status,
            mfg_display,
            exp_display,
            needs_human_review,
            voice,
        )
        if cache_path.is_file():
            return cache_path.read_bytes()

        try:
            audio = await self._synthesizer(text, voice)
        except TtsUpstreamError:
            raise
        except Exception as exc:
            logger.warning("Edge TTS failed: %s", exc)
            raise TtsUpstreamError("TTS failed") from exc

        if not audio:
            raise TtsUpstreamError("Empty TTS audio")

        self._cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = cache_path.with_suffix(".tmp")
        tmp.write_bytes(audio)
        tmp.replace(cache_path)
        return audio
