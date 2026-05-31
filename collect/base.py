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

    Catches two non-recoverable cases, while leaving transient per-minute rate
    limits to the normal retry path:
      - Google RESOURCE_EXHAUSTED with a zero limit / *daily* quota violation
      - billing/credit exhaustion (e.g. OpenAI `insufficient_quota`) — the account
        is out of credit, so retrying within a run can never succeed
    """
    text = str(exc).lower()
    # Billing/credit exhaustion — independent of the resource_exhausted/quota gate.
    if (
        "insufficient_quota" in text
        or "exceeded your current quota" in text
        or "check your plan and billing" in text
    ):
        return True
    if "resource_exhausted" not in text and "quota" not in text:
        return False
    return (
        "limit: 0" in text
        or "limit:0" in text
        or "perday" in text
        or "per day" in text
        or "/day" in text
    )


def _is_timeout(exc: Exception) -> bool:
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return "timeout" in name or "timeout" in text or "timed out" in text


def _is_transient(exc: Exception) -> bool:
    """Retryable errors: rate limits, timeouts, and connection drops.

    A stale socket after the machine sleeps surfaces as a timeout / connection
    error — retrying re-establishes the connection rather than failing the row.
    """
    if _is_rate_limit(exc) or _is_timeout(exc):
        return True
    name = type(exc).__name__.lower()
    text = str(exc).lower()
    return (
        "connection" in name
        or "connection error" in text
        or "apiconnection" in name
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


def with_retries(
    fn,
    *,
    max_retries: int = 5,
    max_timeout_retries: int = 3,
    base_delay: float = 2.0,
    label: str = "",
):
    """Call fn() with exponential backoff + jitter on transient errors.

    - Hard quota (limit:0 / daily): fail fast, no retry (raises HardQuotaError).
    - Timeouts: retried up to `max_timeout_retries`; after that the query is
      skipped (raises CollectorError) so one dead query can't stall the run.
    - Other transient errors (rate limit / connection): retried up to `max_retries`.
    """
    attempt = 0
    timeout_attempts = 0
    while True:
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001 - provider SDKs raise varied types
            if _is_hard_quota(exc):
                raise HardQuotaError(
                    f"{label}: hard quota, not retrying — {type(exc).__name__}: {exc}"
                ) from exc
            if not _is_transient(exc):
                raise CollectorError(f"{label}: {type(exc).__name__}: {exc}") from exc

            attempt += 1
            if _is_timeout(exc):
                timeout_attempts += 1
                if timeout_attempts >= max_timeout_retries:
                    raise CollectorError(
                        f"{label}: timed out {timeout_attempts}× in a row — "
                        f"skipping (re-run later): {type(exc).__name__}: {exc}"
                    ) from exc
            if attempt > max_retries:
                raise CollectorError(f"{label}: {type(exc).__name__}: {exc}") from exc

            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            kind = "timeout" if _is_timeout(exc) else "transient"
            print(f"  ⏳ {label}: {kind} ({type(exc).__name__}) "
                  f"(attempt {attempt}/{max_retries}); retrying in {delay:.1f}s")
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
