"""Perplexity collector — Sonar API.

Reads PERPLEXITY_API_KEY from .env. Sonar models are good for citation-style
answers. Record the exact model id as `model_version` on every call.

STUB ONLY — no API calls implemented yet.
"""

from __future__ import annotations

import os

from .base import EngineCollector, RawResponse


class PerplexityCollector(EngineCollector):
    name = "Perplexity"
    model_version = "TODO-pin-exact-sonar-model"

    def __init__(self) -> None:
        self.api_key = os.environ.get("PERPLEXITY_API_KEY")
        # TODO: instantiate the Perplexity client with a fresh session per call.
        raise NotImplementedError("Perplexity collector not implemented yet (scaffold only).")

    def query(self, query_id: str, bucket: str, prompt_text: str, pass_number: int) -> RawResponse:
        # TODO: call the Perplexity Sonar API, US/English, fixed settings,
        # no personalization; capture verbatim text + timestamp.
        raise NotImplementedError
