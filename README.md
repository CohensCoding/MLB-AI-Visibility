# MLB Citation Share Index

A defensible, replicable ranking of all **30 MLB franchises** by **AI Citation
Share** — how often each team gets named when fans, sponsors, free agents, and
investors ask AI answer engines baseball questions. Modeled exactly on the
[5W NFL Citation Share Index 2026](spec/5W-NFL-Citation-Share-Index-2026.csv) so
results are directly comparable to that precedent.

The locked methodology is in **[CLAUDE.md](CLAUDE.md)**. The full build guide is
in [spec/MLB-Citation-Share-Index-Build-Playbook.md](spec/MLB-Citation-Share-Index-Build-Playbook.md).

> **Status: collection pipeline built, not yet run.** The API collectors are in
> place; run `python -m collect.test_connection` to verify keys + pinned models,
> then `python -m collect.run_collection` to fill the matrix.

## The run matrix — 1,300 queries

**4 API engines × 100 prompts × 3 passes (1,200) + Google AI Overviews × 100
prompts × 1 pass (100) = 1,300 queries.**

- **Engines:** ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews.
- **Prompts (100):** 8 categories — AI-First Fan 15, Fan Experience & Tickets 13,
  Sponsorship & Brand Partnership 15, Audience & Reach 12, Market Relevance &
  Competitive Standing 12, Brand Identity & Narrative 13, Business & Franchise
  Strength 12, Talent & Org Reputation 8.
- **Passes:** 3 per prompt for the 4 API engines; **1 for Google AI Overviews**
  (Google serves one cached Overview per repeated query, so extra passes add no
  variance).

Collection is via provider APIs (OpenAI, Anthropic, Google Gemini, Perplexity),
one fresh call per query with web search / grounding on. **Google AI Overviews has
no public API** and is captured from real Google SERPs via SerpApi, pinned to a
neutral US locale (`location="United States"`, `hl=en`, `gl=us`). API keys and
pinned model strings are read from `.env`; see [CLAUDE.md](CLAUDE.md) for the locked
collection method.

## Scoring (summary)

- 1st team named = **5 pts**, 2nd = **3 pts**, any other mention = **1 pt**.
- Ballpark / owner / logo named without the team = **1 pt** (attribution credit).
- One score per team per response (highest value wins).
- Normalize so the top team = **100.0**; others = `(raw / max raw) × 100`.

Cross-references add the story: **Performance Gap** (citation rank − on-field rank)
and **Value Gap** (citation rank − valuation rank). Teams fall into four
tiers: I Dominant (50+), II Established (20–49), III Present (1–19), IV Dead Zone (0.0).

See [CLAUDE.md](CLAUDE.md) for the complete, locked rules.

## Pipeline

```
collect/   → data/capture_log.csv → score.py        → generate/
(API calls    (verbatim               (parse, apply     (ranked index CSV
 + SERP,       audit trail,            point rules,      + 30 one-pagers)
 search on)    one row per query)      aggregate,
                                       normalize)
```

Collection and scoring are **separate stages** to avoid bias. Run
`python -m collect.test_connection` first, then `python -m collect.run_collection`.

## Layout

| Path | Purpose |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Locked methodology spec — source of truth. |
| [prompts/prompts.csv](prompts/prompts.csv) | The 100 locked prompts (id, category, text). |
| [reference/teams.csv](reference/teams.csv) | 30-team entity-matching backbone (aliases, ballpark, owner, division, +cross-ref columns to fill). |
| [data/schema.md](data/schema.md) | Capture-log + reference-table schemas. |
| `data/capture_log.csv` | Verbatim API/SERP responses — the audit trail (one row per query). |
| `collect/` | API collection pipeline (config, per-engine collectors, `run_collection`, `test_connection`); reads keys + model pins from `.env`. |
| `score.py` | Parse → score → aggregate → normalize. |
| `generate/` | Emit the index CSV + 30 one-pagers. |
| `spec/` | Source playbook + NFL reference CSV (inputs). |

## Setup

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # then fill in your API keys (.env is gitignored)
```

## Refresh cadence

V1 now; refresh quarterly with the **methodology held constant** to preserve trend
integrity. Open · replicable · auditable.
