"""
date_detection_graph.py
-----------------------
Assembles and compiles the Approach B LangGraph date detection pipeline.

Graph structure (YOLO-first):

    START → crop_zoom → first_read → second_read → consensus_check
                                                          │
                             ┌──────────────────────────┐ │
                             │ "match"                   ↓ │
                             └─────────────── validate ←───┘
                                                   │ ↑
                             "mismatch"/"low_confidence"│ │
                                         ↓             │ │
                                     reflection ───────┘ │
                                                          ↓
                                                         END

Key rotation is initialised here so it runs once at import time.
"""

from __future__ import annotations

import asyncio

from langgraph.graph import StateGraph, END

from src.api.schemas.date_detection_state import DateDetectionState
from src.api.config.settings import OPENROUTER_KEYS, GROQ_KEYS
from src.api.http_clients.key_pool import KeyPool, init_provider_config

from src.api.control.agents.approach_b.crop_zoom_node import crop_zoom_node
from src.api.control.agents.approach_b.first_read_node import first_read_node
from src.api.control.agents.approach_b.second_read_node import second_read_node
from src.api.control.agents.approach_b.consensus_check_node import consensus_check_node
from src.api.control.agents.approach_b.reflection_node import reflection_node
from src.api.control.agents.approach_b.validate_node import validate_node

# ---------------------------------------------------------------------------
# One-time initialisation of key pools
# ---------------------------------------------------------------------------
_openrouter_pool = KeyPool(OPENROUTER_KEYS)
_groq_pool = KeyPool(GROQ_KEYS)

init_provider_config(openrouter_pool=_openrouter_pool, groq_pool=_groq_pool)

# ---------------------------------------------------------------------------
# Graph definition — YOLO entry, dual crop readers, optional reflection
# ---------------------------------------------------------------------------
_graph = StateGraph(DateDetectionState)

_graph.add_node("crop_zoom", crop_zoom_node)
_graph.add_node("first_read", first_read_node)
_graph.add_node("second_read", second_read_node)
_graph.add_node("consensus_check", consensus_check_node)
_graph.add_node("reflection", reflection_node)
_graph.add_node("validate", validate_node)

_graph.set_entry_point("crop_zoom")

_graph.add_edge("crop_zoom", "first_read")
_graph.add_edge("first_read", "second_read")
_graph.add_edge("second_read", "consensus_check")

_graph.add_conditional_edges(
    "consensus_check",
    lambda s: s["consensus_status"],
    {
        "match": "validate",
        "mismatch": "reflection",
        "low_confidence": "reflection",
    },
)

_graph.add_edge("reflection", "validate")

_graph.add_conditional_edges(
    "validate",
    lambda s: s["status"],
    {
        "accepted": END,
        "human_review": END,
    },
)

# Compiled graph — imported by detect services (use ainvoke / arun_date_detection)
compiled_graph = _graph.compile()


# ---------------------------------------------------------------------------
# Convenience runners
# ---------------------------------------------------------------------------
async def arun_date_detection(image_path: str) -> DateDetectionState:
    """
    Async runner for the complete date detection pipeline.

    crop_zoom is async (YOLO/OpenCV via asyncio.to_thread); VLM nodes use
    acall_vlm_with_rotation. Prefer this from async FastAPI handlers.
    """
    initial_state: DateDetectionState = {
        "image_path": image_path,
        "image_b64": "",
        "attempt": 0,
        "bbox_2d": None,
        "crop_path": "",
        "crop_source": "yolo",
        "first_result": {},
        "second_result": {},
        "consensus_status": "mismatch",
        "reflection_result": None,
        "final_mfg": None,
        "final_exp": None,
        "validation": {},
        "status": "human_review",
    }

    result = await compiled_graph.ainvoke(initial_state)
    return result  # type: ignore[return-value]


def run_date_detection(image_path: str) -> DateDetectionState:
    """
    Synchronous convenience wrapper around :func:`arun_date_detection`.

    Returns the final DateDetectionState after the graph has completed.
    """
    return asyncio.run(arun_date_detection(image_path))
