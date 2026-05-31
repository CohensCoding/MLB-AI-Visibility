"""ChatGPT collector — OpenAI Responses API with the web_search tool enabled.

Reads OPENAI_API_KEY and OPENAI_MODEL from .env. One fresh call per query; no
conversation state is carried between calls.
"""

from __future__ import annotations

from .config import ENGINES, get_key, get_model

SPEC = ENGINES["openai"]


class ChatGPTCollector:
    display = SPEC.display
    search_enabled = True

    def __init__(self) -> None:
        from openai import OpenAI  # lazy import

        key = get_key(SPEC)
        if not key:
            raise RuntimeError(f"{SPEC.key_var} is not set in .env")
        self.model = get_model(SPEC)
        if not self.model:
            raise RuntimeError(f"{SPEC.model_var} is not set in .env")
        self._client = OpenAI(api_key=key)

    def query(self, prompt_text: str) -> str:
        # The Responses API web-search tool type was renamed; try the current name
        # and fall back to the preview name so this works across SDK versions.
        for tool_type in ("web_search", "web_search_preview"):
            try:
                resp = self._client.responses.create(
                    model=self.model,
                    input=prompt_text,
                    tools=[{"type": tool_type}],
                )
                return resp.output_text or ""
            except Exception as exc:  # noqa: BLE001
                if tool_type == "web_search" and "web_search" in str(exc):
                    continue  # retry with the preview tool name
                raise
        return ""
