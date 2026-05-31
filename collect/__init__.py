"""Data-collection package — API collection pipeline.

For each of 4 API engines (OpenAI/ChatGPT, Anthropic/Claude, Google Gemini,
Perplexity) plus Google AI Overviews (via SerpApi), loop all 100 prompts × 3
passes and append verbatim responses to data/capture_log.csv. Web search /
grounding is enabled wherever the provider supports it. API keys AND pinned
model strings are read from .env (see config.py); nothing is hardcoded.

Entry points:
    python -m collect.test_connection   # pre-flight: keys + pinned models
    python -m collect.run_collection    # the 1,500-run matrix

Collection never scores — scoring is a separate stage (score.py).
"""

from .config import ALL_ENGINE_KEYS, API_ENGINE_KEYS, ENGINES, TOTAL_RUNS

__all__ = ["ENGINES", "API_ENGINE_KEYS", "ALL_ENGINE_KEYS", "TOTAL_RUNS"]
