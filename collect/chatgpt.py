"""ChatGPT collector — OpenAI API.

Reads OPENAI_API_KEY from .env. The API model can differ from the consumer
product with browsing; pick one and record `model_version` on every call.

STUB ONLY — no API calls implemented yet.
"""

from __future__ import annotations

import os

from .base import EngineCollector, RawResponse


class ChatGPTCollector(EngineCollector):
    name = "ChatGPT"
    model_version = "TODO-pin-exact-openai-model"

    def __init__(self) -> None:
        self.api_key = os.environ.get("OPENAI_API_KEY")
        # TODO: instantiate the OpenAI client with a fresh session per call.
        raise NotImplementedError("ChatGPT collector not implemented yet (scaffold only).")

    def query(self, query_id: str, bucket: str, prompt_text: str, pass_number: int) -> RawResponse:
        # TODO: call the OpenAI Chat Completions / Responses API, US/English,
        # fixed temperature, no personalization; capture verbatim text + timestamp.
        raise NotImplementedError
