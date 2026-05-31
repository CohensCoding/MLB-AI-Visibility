"""Central configuration for the collection pipeline.

Loads .env (via python-dotenv) and exposes the engine registry. API keys AND
pinned model strings are read from the environment — never hardcoded (so a refresh
run is reproducible from the recorded model_version alone).
"""

from __future__ import annotations

import os
from dataclasses import dataclass

try:
    from dotenv import load_dotenv

    # override=True: .env is this project's source of truth for keys + model pins.
    # Without it, an inherited shell var (e.g. an empty exported ANTHROPIC_API_KEY)
    # silently shadows the real value in .env. .env must win.
    load_dotenv(override=True)
except ImportError:  # python-dotenv not installed; rely on real env vars
    pass


# Per-call request timeout (seconds). Bounds each provider call so a stale socket
# (e.g. after the machine sleeps mid-request) errors instead of hanging forever.
# Generous enough for web-search / grounding calls; timeouts are retried.
REQUEST_TIMEOUT = 180

# The full run matrix.
PROMPT_COUNT = 100
PASSES = 3        # passes per prompt for the 4 API engines
AIO_PASSES = 1    # Google AI Overviews: 1 pass — Google serves one cached Overview
                  # per repeated query, so p2/p3 would be byte-identical (no signal).
API_ENGINE_KEYS = ["openai", "anthropic", "gemini", "perplexity"]
ALL_ENGINE_KEYS = API_ENGINE_KEYS + ["gaio"]
# 4 API engines × 100 × 3 (1,200) + AIO × 100 × 1 (100) = 1,300
TOTAL_RUNS = len(API_ENGINE_KEYS) * PROMPT_COUNT * PASSES + PROMPT_COUNT * AIO_PASSES


def passes_for(engine_key: str) -> int:
    """Number of passes for an engine: AIO = 1, all others = PASSES."""
    return AIO_PASSES if engine_key == "gaio" else PASSES


@dataclass(frozen=True)
class EngineSpec:
    key: str            # internal slug, used in query_id
    display: str        # engine label written to capture_log.csv
    key_var: str        # .env var holding the API key
    model_var: str | None  # .env var holding the pinned model string (None for AIO)


ENGINES: dict[str, EngineSpec] = {
    "openai": EngineSpec("chatgpt", "ChatGPT", "OPENAI_API_KEY", "OPENAI_MODEL"),
    "anthropic": EngineSpec("claude", "Claude", "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL"),
    "gemini": EngineSpec("gemini", "Gemini", "GEMINI_API_KEY", "GEMINI_MODEL"),
    "perplexity": EngineSpec("perplexity", "Perplexity", "PERPLEXITY_API_KEY", "PERPLEXITY_MODEL"),
    "gaio": EngineSpec("gaio", "Google AI Overviews", "SERPAPI_API_KEY", None),
}


def get_key(spec: EngineSpec) -> str | None:
    return os.environ.get(spec.key_var) or None


def get_model(spec: EngineSpec) -> str | None:
    if spec.model_var is None:
        return None
    return os.environ.get(spec.model_var) or None
