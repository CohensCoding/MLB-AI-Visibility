"""Orchestrate the full 1,500-run collection matrix.

100 prompts × 5 engines × 3 passes = 1,500 queries. Each query is one fresh API
call (no history carried between calls); the verbatim response is appended as one
row to data/capture_log.csv. Collection does NOT score — scoring is a separate
stage (score.py) derived only from this raw log.

Resumable: rows already captured successfully are skipped, so a re-run only fills
the gaps. Rate-limit retries and a progress counter are built in.

    python -m collect.run_collection            # all engines
    python -m collect.run_collection openai gemini   # subset

Run test_connection.py first to confirm keys + pinned models.
"""

from __future__ import annotations

import csv
import os
import sys
from datetime import datetime, timezone

from . import config
from .base import CaptureRow, CollectorError, append_row, with_retries

CAPTURE_LOG = os.path.join("data", "capture_log.csv")
PROMPTS_CSV = os.path.join("prompts", "prompts.csv")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def load_prompts() -> list[dict]:
    with open(PROMPTS_CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == config.PROMPT_COUNT, (
        f"expected {config.PROMPT_COUNT} prompts, found {len(rows)}"
    )
    return rows


def load_captured_ids() -> set[str]:
    """query_ids already captured successfully (captured == truthy)."""
    if not os.path.exists(CAPTURE_LOG):
        return set()
    truthy = {"true", "1", "yes"}
    with open(CAPTURE_LOG, newline="") as f:
        return {
            r["query_id"]
            for r in csv.DictReader(f)
            if str(r.get("captured", "")).strip().lower() in truthy
        }


def build_collector(engine_key: str):
    if engine_key == "openai":
        from .chatgpt import ChatGPTCollector

        return ChatGPTCollector()
    if engine_key == "anthropic":
        from .claude import ClaudeCollector

        return ClaudeCollector()
    if engine_key == "gemini":
        from .gemini import GeminiCollector

        return GeminiCollector()
    if engine_key == "perplexity":
        from .perplexity import PerplexityCollector

        return PerplexityCollector()
    if engine_key == "gaio":
        from .google_ai_overviews import GoogleAIOverviewsCollector

        return GoogleAIOverviewsCollector()
    raise ValueError(f"unknown engine: {engine_key}")


def run(engine_keys: list[str] | None = None) -> None:
    engine_keys = engine_keys or config.ALL_ENGINE_KEYS
    prompts = load_prompts()
    done = load_captured_ids()
    total = len(engine_keys) * len(prompts) * config.PASSES
    print(f"Matrix: {len(engine_keys)} engines × {len(prompts)} prompts × "
          f"{config.PASSES} passes = {total} queries "
          f"(full matrix is {config.TOTAL_RUNS}). Already captured: {len(done)}.")

    n = 0
    for engine_key in engine_keys:
        spec = config.ENGINES[engine_key]
        try:
            collector = build_collector(engine_key)
        except Exception as exc:  # noqa: BLE001
            print(f"✗ Skipping {spec.display}: {exc}")
            n += len(prompts) * config.PASSES
            continue

        model_version = getattr(collector, "model", None) or getattr(
            collector, "model_version", "UNKNOWN"
        )
        for p in prompts:
            for pass_number in range(1, config.PASSES + 1):
                n += 1
                query_id = f"{spec.key}_{p['id']}_p{pass_number}"
                if query_id in done:
                    print(f"[{n}/{total}] skip (done) {query_id}")
                    continue
                label = f"[{n}/{total}] {query_id}"
                try:
                    text = with_retries(
                        lambda c=collector, t=p["text"]: c.query(t), label=label
                    )
                    captured = True
                except CollectorError as exc:
                    print(f"  ✗ {label}: {exc}")
                    text, captured = "", False

                append_row(
                    CAPTURE_LOG,
                    CaptureRow(
                        query_id=query_id,
                        category=p["category"],
                        prompt_id=p["id"],
                        prompt_text=p["text"],
                        engine=spec.display,
                        pass_number=pass_number,
                        model_version=model_version,
                        date_run=_utc_now(),
                        raw_response_text=text,
                        search_enabled=getattr(collector, "search_enabled", False),
                        captured=captured,
                    ),
                )
                flag = "✓" if captured else "✗"
                print(f"{flag} {label} ({len(text)} chars)")

    print(f"Done. Capture log: {CAPTURE_LOG}")


if __name__ == "__main__":
    run(sys.argv[1:] or None)
