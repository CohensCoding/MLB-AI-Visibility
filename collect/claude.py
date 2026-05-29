"""Claude collector — Anthropic API.

Reads ANTHROPIC_API_KEY from .env. Record the exact model id as `model_version`
on every call.

STUB ONLY — no API calls implemented yet.
"""

from __future__ import annotations

import os

from .base import EngineCollector, RawResponse


class ClaudeCollector(EngineCollector):
    name = "Claude"
    model_version = "TODO-pin-exact-anthropic-model"

    def __init__(self) -> None:
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        # TODO: instantiate the Anthropic client with a fresh session per call.
        raise NotImplementedError("Claude collector not implemented yet (scaffold only).")

    def query(self, query_id: str, bucket: str, prompt_text: str, pass_number: int) -> RawResponse:
        # TODO: call the Anthropic Messages API, US/English, fixed temperature,
        # no personalization; capture verbatim text + timestamp.
        raise NotImplementedError
