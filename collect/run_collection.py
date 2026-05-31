"""Orchestrate the full 1,500-run collection matrix.

4 API engines × 100 prompts × 3 passes (1,200) + Google AI Overviews × 100 × 1
pass (100) = 1,300 queries. Each query is one fresh API call (no history carried
between calls); the verbatim response is appended as one row to
data/capture_log.csv. Collection does NOT score — scoring is a separate stage
(score.py) derived only from this raw log.

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
from .base import CaptureRow, CollectorError, HardQuotaError, append_row, with_retries

CAPTURE_LOG = os.path.join("data", "capture_log.csv")
PROMPTS_CSV = os.path.join("prompts", "prompts.csv")
PROGRESS_LOG = os.path.join("logs", "collection_progress.log")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _progress(msg: str) -> None:
    """Append a timestamped line to the progress log AND echo to stdout.

    Lets the run be verified as actually advancing (not just 'alive').
    """
    line = f"{_utc_now()}  {msg}"
    print(line, flush=True)
    os.makedirs(os.path.dirname(PROGRESS_LOG), exist_ok=True)
    with open(PROGRESS_LOG, "a") as f:
        f.write(line + "\n")


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


def run(engine_keys: list[str] | None = None, limit: int | None = None) -> None:
    engine_keys = engine_keys or config.ALL_ENGINE_KEYS
    prompts = load_prompts()
    # --limit / TEST_LIMIT: run only the first N prompts (test batch). Rows are
    # written to data/capture_log.csv exactly as the full run would write them.
    if limit is None:
        env_limit = os.environ.get("TEST_LIMIT")
        limit = int(env_limit) if env_limit else None
    if limit is not None:
        prompts = prompts[:limit]
        print(f"⚠ TEST BATCH: limited to the first {len(prompts)} prompts.")

    done = load_captured_ids()
    total = len(prompts) * sum(config.passes_for(e) for e in engine_keys)
    _progress(f"START — {len(prompts)} prompts × ["
              f"{len(config.API_ENGINE_KEYS)} API × {config.PASSES} + AIO × {config.AIO_PASSES}] "
              f"= {total} queries (full matrix {config.TOTAL_RUNS}). "
              f"Already captured: {len(done)}.")

    n = 0
    for engine_key in engine_keys:
        spec = config.ENGINES[engine_key]
        passes = config.passes_for(engine_key)
        try:
            collector = build_collector(engine_key)
        except Exception as exc:  # noqa: BLE001
            print(f"✗ Skipping {spec.display}: {exc}")
            n += len(prompts) * passes
            continue

        model_version = getattr(collector, "model", None) or getattr(
            collector, "model_version", "UNKNOWN"
        )
        quota_hit = False
        for pi, p in enumerate(prompts):
            for pass_number in range(1, passes + 1):
                n += 1
                query_id = f"{spec.key}_{p['id']}_p{pass_number}"
                if query_id in done:
                    print(f"[{n}/{total}] skip (done) {query_id}")
                    continue
                label = f"[{n}/{total}] {query_id}"
                try:
                    text = with_retries(
                        lambda c=collector, t=p["text"]: c.query(t),
                        max_timeout_retries=config.MAX_TIMEOUT_RETRIES,
                        label=label,
                    )
                    captured = True
                except HardQuotaError as exc:
                    print(f"  ⨯ {label}: {exc}")
                    text, captured, quota_hit = "", False, True
                except CollectorError as exc:
                    print(f"  ✗ {label}: {exc}")
                    text, captured = "", False
                except Exception as exc:  # noqa: BLE001 - bulletproof
                    # No single query may kill the run. Log verbatim (traceback to
                    # stderr/run.out), mark captured=false, and keep going.
                    # (KeyboardInterrupt/SystemExit deliberately NOT caught, so the
                    # run can still be stopped intentionally.)
                    import traceback
                    _progress(f"  ‼ {label}: UNEXPECTED {type(exc).__name__}: {exc}")
                    traceback.print_exc()
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
                _progress(f"{flag} [{n}/{total}] {query_id} ({len(text)} chars)")
                if quota_hit:
                    break
            if quota_hit:
                remaining = passes - pass_number + (len(prompts) - 1 - pi) * passes
                n += remaining
                print(f"  ⨯ {spec.display}: hard quota — skipping remaining "
                      f"{remaining} queries for this engine. Fix billing/quota and re-run.")
                break

    _progress(f"DONE. Capture log: {CAPTURE_LOG}")


def _parse_args(argv: list[str]) -> tuple[list[str] | None, int | None]:
    """Split CLI args into engine keys and an optional --limit N."""
    engines: list[str] = []
    limit: int | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--limit":
            limit = int(argv[i + 1])
            i += 2
        elif arg.startswith("--limit="):
            limit = int(arg.split("=", 1)[1])
            i += 1
        else:
            engines.append(arg)
            i += 1
    return (engines or None), limit


if __name__ == "__main__":
    keys, lim = _parse_args(sys.argv[1:])
    run(keys, lim)
