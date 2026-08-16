"""
key_pool.py
-----------
Round-robin key rotation across multiple API providers.

Rotate call-by-call so load spreads across keys before any single one
approaches its daily cap. Rate-limit (429) errors retry on the next key;
other errors propagate so callers can handle them.

Model routing:
  Each known VLM maps to a provider + call defaults (max_tokens, extra_body).
  acall_vlm_with_rotation auto-selects the provider from the model id.

Production VLM nodes use acall_vlm_with_rotation (AsyncOpenAI + asyncio.sleep)
so LangGraph ainvoke does not block the event loop on HTTP.
"""

from __future__ import annotations

import asyncio
import itertools
from typing import Any

from openai import AsyncOpenAI


class KeyPool:
    """Cycles through a list of API keys in round-robin order."""

    def __init__(self, keys: list[str]) -> None:
        if not keys:
            raise ValueError("KeyPool requires at least one key.")
        self._cycle = itertools.cycle(keys)
        self._n = len(keys)

    def next_key(self) -> str:
        return next(self._cycle)

    def __len__(self) -> int:
        return self._n


# ---------------------------------------------------------------------------
# Known VLMs used by Approach B nodes
#
# Production assignment (YOLO-first dual crop readers):
#   first_read  / second_read  → QWEN36_GROQ  (Groq)
#   reflection                 → OMNI30B      (OpenRouter)
# Nodes pin these explicitly (FIRST_READ_MODELS / SECOND_READ_MODELS /
# REFLECTION_MODELS).  MODEL_SPECS entries below are call defaults and
# emergency retry fallbacks only — not primary routing.
# ---------------------------------------------------------------------------
OMNI30B = "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free"
QWEN36_GROQ = "qwen/qwen3.6-27b"

# Call defaults:
# - omni30b: reasoning burns max_tokens → empty content unless budget is high;
#            disable thinking for OCR / adjudication when possible.
# - qwen36: JSON date OCR is small; Groq TPM counts prompt + max_tokens.
#   4096 output budget with two crop images exceeded the 8k TPM cap.
MODEL_SPECS: dict[str, dict[str, Any]] = {
    OMNI30B: {
        "provider": "openrouter",
        "max_tokens": 4096,
        "extra_body": {"chat_template_kwargs": {"enable_thinking": False}},
    },
    QWEN36_GROQ: {
        "provider": "groq",
        "max_tokens": 1024,
        # Groq: thinking-on + json_object often → json_validate_failed.
        # Use reasoning_effort=none (Groq-supported; chat_template_kwargs is not).
        "extra_body": {"reasoning_effort": "none"},
        "temperature": 0,
    },
}


def _is_rate_limited_or_not_found(exc: Exception) -> tuple[bool, bool]:
    """
    Returns (is_rate_limited, is_not_found_or_unavailable) for *exc*.
    """
    status = getattr(exc, "status_code", None)
    err_str = str(exc).lower()
    is_429 = (
        status == 429
        or "429" in err_str
        or ("rate_limit" in err_str and "request too large" not in err_str)
    )
    is_404 = status == 404 or "404" in err_str or "unavailable" in err_str or "not found" in err_str
    return is_429, is_404


def _is_empty_content(exc: Exception) -> bool:
    err = str(exc).lower()
    return "empty" in err or "null content" in err


PROVIDER_CONFIG: dict[str, dict[str, Any]] = {}


def init_provider_config(openrouter_pool: KeyPool, groq_pool: KeyPool) -> None:
    """Register provider endpoints and key pools once at application startup."""
    PROVIDER_CONFIG["openrouter"] = {
        "base_url": "https://openrouter.ai/api/v1",
        "pool": openrouter_pool,
    }
    PROVIDER_CONFIG["groq"] = {
        "base_url": "https://api.groq.com/openai/v1",
        "pool": groq_pool,
    }


def resolve_model_spec(model: str) -> dict[str, Any]:
    """Return provider + call defaults for a model id (with safe fallbacks)."""
    if model in MODEL_SPECS:
        return dict(MODEL_SPECS[model])
    # Heuristic fallback
    if model.startswith("qwen/") or "groq" in model.lower():
        return {"provider": "groq", "max_tokens": 1024, "extra_body": None}
    return {"provider": "openrouter", "max_tokens": 4096, "extra_body": None}


def _response_has_content(resp: Any) -> bool:
    return bool(
        resp
        and getattr(resp, "choices", None)
        and len(resp.choices) > 0
        and resp.choices[0].message.content is not None
        and str(resp.choices[0].message.content).strip()
    )


async def acall_vlm_with_rotation(
    model: str | list[str],
    messages: list[dict],
    provider: str | None = None,
    max_retries: int = 4,
    response_format: dict | None = None,
    max_tokens: int | None = None,
    extra_body: dict | None = None,
) -> Any:
    """
    Call a chat-completion endpoint using the next key from the round-robin
    pool. Supports model candidate lists with per-model provider routing.

    Uses ``AsyncOpenAI`` and ``asyncio.sleep`` so callers can await from
    LangGraph async nodes without blocking the event loop.
    """
    models = [model] if isinstance(model, str) else list(model)
    last_err: Exception | None = None

    for current_model in models:
        spec = resolve_model_spec(current_model)
        current_provider = provider or spec["provider"]
        current_max_tokens = max_tokens if max_tokens is not None else spec.get("max_tokens")
        current_extra = extra_body if extra_body is not None else spec.get("extra_body")
        current_temperature = spec.get("temperature")

        if current_provider not in PROVIDER_CONFIG:
            last_err = KeyError(
                f"Provider '{current_provider}' is not configured for model "
                f"'{current_model}'. Available: {list(PROVIDER_CONFIG.keys())}"
            )
            continue

        cfg = PROVIDER_CONFIG[current_provider]
        pool: KeyPool = cfg["pool"]
        base_url: str = cfg["base_url"]

        for attempt in range(max_retries):
            key = pool.next_key()
            client = AsyncOpenAI(api_key=key, base_url=base_url)
            try:
                kwargs: dict[str, Any] = {
                    "model": current_model,
                    "messages": messages,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                if current_max_tokens is not None:
                    kwargs["max_tokens"] = current_max_tokens
                if current_temperature is not None:
                    kwargs["temperature"] = current_temperature
                if current_extra:
                    kwargs["extra_body"] = current_extra

                try:
                    resp = await client.chat.completions.create(**kwargs)
                    if _response_has_content(resp):
                        setattr(resp, "_model_used", current_model)
                        setattr(resp, "_provider_used", current_provider)
                        return resp
                    raise ValueError(
                        f"Model '{current_model}' returned empty choices or null content"
                    )
                except Exception as inner_exc:
                    err_l = str(inner_exc).lower()
                    if response_format is not None and (
                        "not supported" in err_l
                        or "response_format" in err_l
                        or "failed to validate json" in err_l
                        or "json_validate_failed" in err_l
                    ):
                        kwargs_no_fmt = {
                            k: v for k, v in kwargs.items() if k != "response_format"
                        }
                        resp = await client.chat.completions.create(**kwargs_no_fmt)
                        if _response_has_content(resp):
                            setattr(resp, "_model_used", current_model)
                            setattr(resp, "_provider_used", current_provider)
                            return resp
                    raise inner_exc

            except Exception as exc:
                last_err = exc
                is_429, is_404 = _is_rate_limited_or_not_found(exc)

                if is_404:
                    break

                if is_429 or _is_empty_content(exc):
                    await asyncio.sleep(0.5 * (attempt + 1))
                    continue

                break

    raise last_err  # type: ignore[misc]
