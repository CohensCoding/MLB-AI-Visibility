"""Shared scaffolding for engine collectors: the row schema, a rate-limit-aware
retry wrapper, and the capture-log CSV writer.

Consistency controls are held constant across engines (see CLAUDE.md):
fresh call per query, no history carried between calls, US/English framing.
"""

from __future__ import annotations

import csv
import os
import random
import time
from dataclasses import asdict, dataclass, field

# One row per response — written to data/capture_log.csv.
CAPTURE_LOG_COLUMNS = [
    "query_id",
    "category",
    "prompt_id",
    "prompt_text",
    "engine",
    "pass_number",
    "model_version",
    "date_run",
    "raw_response_text",
    "search_enabled",
    "captured",
]


@dataclass
class CaptureRow:
    query_id: str
    category: str
    prompt_id: str
    prompt_text: str
    engine: str
    pass_number: int
    model_version: str
    date_run: str  # ISO 8601 UTC
    raw_response_text: str
    search_enabled: bool
    captured: bool

    def as_dict(self) -> dict:
        return asdict(self)


class CollectorError(Exception):
    """Raised when a collector cannot produce a response after retries."""


class HardQuotaError(CollectorError):
    """Raised on a non-recoverable quota error (limit:0 / daily quota exhausted).

    Distinct from a transient per-minute rate limit: retrying within a run cannot
    succeed, so the orchestrator should skip the rest of that engine.
    """


def _is_hard_quota(exc: Exception) -> bool:
    """True for quota errors that retrying within this run cannot clear.

    Catches RESOURCE_EXHAUSTED with a zero limit or a *daily* quota violation,
    while leaving transient per-minute rate limits to the normal retry path.
    """
    text = str(exc).lower()
    if "resource_exhausted" not in text and "quota" not in text:
        return False
    return (
        "limit: 0" in text
        or "limit:0" in text
        or "perday" in text
        or "per day" in text
        or "/day" in text
    )


def _is_rate_limit(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    return (
        status == 429
        or "rate" in name and "limit" in name
        or "ratelimit" in name
        or "429" in text
        or "rate limit" in text
        or "overloaded" in text
        or "quota" in text
    )


def with_retries(fn, *, max_retries: int = 5, base_delay: float = 2.0, label: str = ""):
    """Call fn() with exponential backoff + jitter on rate-limit / transient errors."""
    attempt = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - provider SDKs raise varied types
            # Hard quota (limit:0 / daily) can't clear by retrying — fail fast.
            if _is_hard_quota(exc):
                raise HardQuotaError(
                    f"{label}: hard quota, not retrying — {type(exc).__name__}: {exc}"
                ) from exc
            attempt += 1
            transient = _is_rate_limit(exc)
            if attempt > max_retries or not transient:
                raise CollectorError(f"{label}: {type(exc).__name__}: {exc}") from exc
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            print(f"  ⏳ {label}: rate-limited (attempt {attempt}/{max_retries}); "
                  f"retrying in {delay:.1f}s")
            time.sleep(delay)


def append_row(path: str, row: CaptureRow) -> None:
    """Append one row to the capture log, writing the header if the file is new."""
    new_file = not os.path.exists(path) or os.path.getsize(path) == 0
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CAPTURE_LOG_COLUMNS)
        if new_file:
            writer.writeheader()
        writer.writerow(row.as_dict())


def load_existing_query_ids(path: str) -> set[str]:
    """Return query_ids already present in the capture log (for resume/skip)."""
    if not os.path.exists(path):
        return set()
    with open(path, newline="") as f:
        return {r["query_id"] for r in csv.DictReader(f) if r.get("query_id")}
