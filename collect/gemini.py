"""Gemini collector — Google AI Studio / Vertex API.

Reads GOOGLE_API_KEY from .env. Record the exact model id as `model_version`
on every call.

STUB ONLY — no API calls implemented yet.
"""

from __future__ import annotations

import os

from .base import EngineCollector, RawResponse


class GeminiCollector(EngineCollector):
    name = "Gemini"
    model_version = "TODO-pin-exact-gemini-model"

    def __init__(self) -> None:
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        # TODO: instantiate the Google GenAI client with a fresh session per call.
        raise NotImplementedError("Gemini collector not implemented yet (scaffold only).")

    def query(self, query_id: str, bucket: str, prompt_text: str, pass_number: int) -> RawResponse:
        # TODO: call the Gemini API, US/English, fixed settings,
        # no personalization; capture verbatim text + timestamp.
        raise NotImplementedError
