"""Google AI Overviews collector.

There is NO public API for AI Overviews. These must be captured from real Google
search result pages — either via a SERP data provider (reads SERP_API_KEY from
.env) or through structured manual capture. Respect Google's terms of service.
Document the exact capture method in the methodology.

STUB ONLY — no calls / capture implemented yet.
"""

from __future__ import annotations

import os

from .base import EngineCollector, RawResponse


class GoogleAIOverviewsCollector(EngineCollector):
    name = "Google AI Overviews"
    model_version = "TODO-record-capture-method-and-date"

    def __init__(self) -> None:
        # SERP-provider path; for manual capture this key may be unused.
        self.serp_api_key = os.environ.get("SERP_API_KEY")
        # TODO: configure SERP provider OR define the manual-capture procedure.
        raise NotImplementedError("Google AI Overviews collector not implemented yet (scaffold only).")

    def query(self, query_id: str, bucket: str, prompt_text: str, pass_number: int) -> RawResponse:
        # TODO: fetch the AI Overview text for the prompt from a real US/English SERP;
        # capture verbatim text + timestamp + the capture method used.
        raise NotImplementedError
