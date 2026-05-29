"""Shared scaffolding for engine collectors.

Defines the common record shape (data/schema.md) and consistency-control settings
that every engine must honor. No API calls here — structure only.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Consistency controls (CLAUDE.md §Run matrix). Held constant across all engines.
LOCALE = "US"
LANGUAGE = "en"
TEMPERATURE = 0.0  # deterministic settings recorded per call


@dataclass
class RawResponse:
    """One row per query response — see data/schema.md."""

    query_id: str
    bucket: str
    prompt_text: str
    engine: str
    model_version: str
    pass_number: int
    date_run: str  # ISO 8601
    raw_response_text: str
    # The following are populated downstream by score.py, not at collection time.
    teams_mentioned: list = field(default_factory=list)
    first_team: str | None = None
    second_team: str | None = None
    other_teams: list = field(default_factory=list)
    attribution_only_teams: list = field(default_factory=list)


class EngineCollector:
    """Base class for per-engine collectors.

    Subclasses set `name` and `model_version` and implement `query`. Fresh session
    per call, no conversation memory, personalization stripped where possible.
    """

    name: str = "base"
    model_version: str = "UNSET"

    def __init__(self) -> None:
        # TODO: load the engine's API key from .env via python-dotenv.
        raise NotImplementedError("Engine collectors are not implemented yet (scaffold only).")

    def query(self, query_id: str, bucket: str, prompt_text: str, pass_number: int) -> RawResponse:
        """Run one fresh query and return a RawResponse. NOT yet implemented."""
        raise NotImplementedError
