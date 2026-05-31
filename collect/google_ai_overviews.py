"""Google AI Overviews collector — captured from real Google SERPs via SerpApi.

There is no public API for AI Overviews. We query Google through SerpApi
(SERPAPI_API_KEY) with a pinned neutral US locale (location="United States",
hl=en, gl=us) so results are not personalized to the operator's account/IP, and
extract the AI Overview text. model_version is recorded as "SERP/AIO" since there
is no model string to pin. AI Overviews are collected at 1 pass (Google serves
one cached Overview per repeated query).

Some SERPs return the AI Overview inline; others return only a `page_token` that
must be redeemed against SerpApi's `google_ai_overview` engine — both handled.
"""

from __future__ import annotations

import requests

from .config import ENGINES, get_key

SPEC = ENGINES["gaio"]
SEARCH_URL = "https://serpapi.com/search"
MODEL_VERSION = "SERP/AIO"

# Pinned neutral US locale so results are NOT personalized to the operator's
# account/IP location. Documented in CLAUDE.md. `location` (canonical SerpApi
# name) makes SerpApi generate the matching `uule`; hl/gl fix language + country.
LOCATION = "United States"
HL = "en"
GL = "us"


class GoogleAIOverviewsCollector:
    display = SPEC.display
    search_enabled = True
    model_version = MODEL_VERSION

    def __init__(self) -> None:
        key = get_key(SPEC)
        if not key:
            raise RuntimeError(f"{SPEC.key_var} is not set in .env")
        self._key = key

    def _get(self, params: dict) -> dict:
        params = {**params, "api_key": self._key}
        resp = requests.get(SEARCH_URL, params=params, timeout=60)
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def _flatten(ai_overview: dict) -> str:
        """Flatten SerpApi's ai_overview text_blocks into plain text."""
        out: list[str] = []
        for block in ai_overview.get("text_blocks", []) or []:
            if block.get("snippet"):
                out.append(block["snippet"])
            for item in block.get("list", []) or []:
                if item.get("snippet"):
                    out.append(f"- {item['snippet']}")
        return "\n".join(out).strip()

    def query(self, prompt_text: str) -> str:
        data = self._get({
            "engine": "google", "q": prompt_text,
            "location": LOCATION, "hl": HL, "gl": GL,
        })
        ai = data.get("ai_overview")
        if not ai:
            return ""  # no AI Overview surfaced for this query
        # Two-step flow: redeem page_token if the overview wasn't returned inline.
        if "text_blocks" not in ai and ai.get("page_token"):
            data = self._get({"engine": "google_ai_overview", "page_token": ai["page_token"]})
            ai = data.get("ai_overview", {})
        return self._flatten(ai)
