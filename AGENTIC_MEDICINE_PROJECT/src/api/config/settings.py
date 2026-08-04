"""
settings.py
-----------
Portable runtime configuration.

- Loads ``.env`` from the backend package root (not the process cwd), so the
  API works no matter which directory you launch uvicorn from.
- Discovers any number of OpenRouter / Groq keys for round-robin rotation.
- Resolves storage paths relative to the package root unless overridden.
"""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from pathlib import Path

from dotenv import load_dotenv

# src/api/config/settings.py → parents[3] = AGENTIC_MEDICINE_PROJECT/
_REPO_ROOT = Path(__file__).resolve().parents[3]

# Prefer the package-root .env so clones on other machines work without
# depending on the shell's current working directory.
load_dotenv(_REPO_ROOT / ".env")
# Optional cwd .env (does not override vars already set).
load_dotenv()


def _clean_key(value: str | None) -> str | None:
    """Strip whitespace and surrounding quotes from env key values."""
    if not value:
        return None
    cleaned = value.strip().strip('"').strip("'").strip()
    return cleaned or None


def load_numbered_api_keys(
    prefix: str,
    environ: Mapping[str, str] | None = None,
) -> list[str]:
    """
    Collect API keys for *prefix* from the environment.

    Accepted forms (any mix; order preserved; duplicates dropped):

    - ``PREFIX``                  → first key
    - ``PREFIX_1`` … ``PREFIX_N`` → any positive integer suffix
    - ``PREFIXS`` / ``PREFIXES``  → comma- or whitespace-separated list
      (e.g. ``GROQ_API_KEYS=k1,k2,k3``)

    Examples that all work:

    - 1 key:  ``GROQ_API_KEY=...``
    - 4 keys: ``GROQ_API_KEY`` + ``_2`` … ``_4``
    - 10 keys or 100 keys: keep numbering; nothing is hard-capped
    """
    env = environ if environ is not None else os.environ
    keys: list[str] = []
    seen: set[str] = set()

    def add(raw: str | None) -> None:
        cleaned = _clean_key(raw)
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            keys.append(cleaned)

    # CSV / multi-value forms
    for plural in (f"{prefix}S", f"{prefix}ES"):
        blob = env.get(plural)
        if not blob:
            continue
        for part in re.split(r"[\s,;]+", blob):
            add(part)

    # Unsuffixed primary key
    add(env.get(prefix))

    # Numbered suffixes: PREFIX_1, PREFIX_2, … PREFIX_N (any N)
    numbered_re = re.compile(rf"^{re.escape(prefix)}_(\d+)$")
    numbered: list[tuple[int, str]] = []
    for name, value in env.items():
        match = numbered_re.match(name)
        if match:
            numbered.append((int(match.group(1)), value))
    for _, value in sorted(numbered, key=lambda item: item[0]):
        add(value)

    return keys


# ---------------------------------------------------------------------------
# API key pools — size is whatever the host machine provides
# ---------------------------------------------------------------------------
OPENROUTER_KEYS: list[str] = load_numbered_api_keys("OPENROUTER_API_KEY")
GROQ_KEYS: list[str] = load_numbered_api_keys("GROQ_API_KEY")

if not OPENROUTER_KEYS:
    raise EnvironmentError(
        "No OpenRouter API keys found. Set OPENROUTER_API_KEY and/or "
        "OPENROUTER_API_KEY_2…N (any count), or OPENROUTER_API_KEYS=k1,k2,… "
        f"in '{_REPO_ROOT / '.env'}'."
    )

if not GROQ_KEYS:
    raise EnvironmentError(
        "No Groq API keys found. Set GROQ_API_KEY and/or "
        "GROQ_API_KEY_2…N (any count), or GROQ_API_KEYS=k1,k2,… "
        f"in '{_REPO_ROOT / '.env'}'. Crop readers require at least one Groq key."
    )

# ---------------------------------------------------------------------------
# Storage — always under the package unless STORAGE_DIR is set
# ---------------------------------------------------------------------------
_storage_override = _clean_key(os.getenv("STORAGE_DIR"))
STORAGE_DIR: str = str(
    Path(_storage_override).expanduser().resolve()
    if _storage_override
    else (_REPO_ROOT / "storage").resolve()
)
RETAIN_DETECT_TEMPS: bool = (
    os.getenv("RETAIN_DETECT_TEMPS", "false").lower() == "true"
)

# ---------------------------------------------------------------------------
# CORS — comma-separated origins; default "*" for local development
# ---------------------------------------------------------------------------
_cors_raw = os.getenv("CORS_ORIGINS", "*").strip()
CORS_ORIGINS: list[str] = (
    ["*"]
    if _cors_raw == "*"
    else [origin.strip() for origin in _cors_raw.split(",") if origin.strip()]
)
