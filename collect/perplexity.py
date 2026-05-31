"""Perplexity collector — Sonar API (OpenAI-compatible endpoint).

Reads PERPLEXITY_API_KEY and PERPLEXITY_MODEL from .env. Sonar models search the
web natively, so web search is inherently on. One fresh call per query.
"""

from __future__ import annotations

from .config import ENGINES, get_key, get_model

SPEC = ENGINES["perplexity"]
BASE_URL = "https://api.perplexity.ai"


class PerplexityCollector:
    display = SPEC.display
    search_enabled = True  # Sonar searches the web by default

    def __init__(self) -> None:
        from openai import OpenAI  # Perplexity exposes an OpenAI-compatible API

        key = get_key(SPEC)
        if not key:
            raise RuntimeError(f"{SPEC.key_var} is not set in .env")
        self.model = get_model(SPEC)
        if not self.model:
            raise RuntimeError(f"{SPEC.model_var} is not set in .env")
        self._client = OpenAI(api_key=key, base_url=BASE_URL)

    def query(self, prompt_text: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt_text}],
        )
        return resp.choices[0].message.content or ""
