"""Gemini collector — Google AI Studio with Google Search grounding enabled.

Reads GEMINI_API_KEY and GEMINI_MODEL from .env. One fresh call per query.
"""

from __future__ import annotations

from .config import ENGINES, get_key, get_model

SPEC = ENGINES["gemini"]


class GeminiCollector:
    display = SPEC.display
    search_enabled = True

    def __init__(self) -> None:
        from google import genai  # lazy import
        from google.genai import types

        key = get_key(SPEC)
        if not key:
            raise RuntimeError(f"{SPEC.key_var} is not set in .env")
        self.model = get_model(SPEC)
        if not self.model:
            raise RuntimeError(f"{SPEC.model_var} is not set in .env")
        self._client = genai.Client(api_key=key)
        self._config = types.GenerateContentConfig(
            tools=[types.Tool(google_search=types.GoogleSearch())]
        )

    def query(self, prompt_text: str) -> str:
        resp = self._client.models.generate_content(
            model=self.model,
            contents=prompt_text,
            config=self._config,
        )
        return resp.text or ""
