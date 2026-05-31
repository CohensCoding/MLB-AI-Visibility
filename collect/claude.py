"""Claude collector — Anthropic Messages API with the web_search tool enabled.

Reads ANTHROPIC_API_KEY and ANTHROPIC_MODEL from .env. One fresh call per query.
"""

from __future__ import annotations

from .config import ENGINES, REQUEST_TIMEOUT, get_key, get_model

SPEC = ENGINES["anthropic"]


class ClaudeCollector:
    display = SPEC.display
    search_enabled = True

    def __init__(self) -> None:
        import anthropic  # lazy import

        key = get_key(SPEC)
        if not key:
            raise RuntimeError(f"{SPEC.key_var} is not set in .env")
        self.model = get_model(SPEC)
        if not self.model:
            raise RuntimeError(f"{SPEC.model_var} is not set in .env")
        self._client = anthropic.Anthropic(api_key=key, timeout=REQUEST_TIMEOUT)

    def query(self, prompt_text: str) -> str:
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt_text}],
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
        )
        # Concatenate all text blocks (tool-use/result blocks are skipped).
        parts = [b.text for b in resp.content if getattr(b, "type", None) == "text"]
        return "".join(parts)
