# MLB Citation Share Index

A defensible, replicable ranking of all **30 MLB franchises** by **AI Citation
Share** — how often each team gets named when fans, sponsors, free agents, and
investors ask AI answer engines baseball questions. Modeled exactly on the
[5W NFL Citation Share Index 2026](spec/5W-NFL-Citation-Share-Index-2026.csv) so
results are directly comparable to that precedent.

The locked methodology is in **[CLAUDE.md](CLAUDE.md)**. The full build guide is
in [spec/MLB-Citation-Share-Index-Build-Playbook.md](spec/MLB-Citation-Share-Index-Build-Playbook.md).

> **Status: scaffold only.** Structure is in place; no data has been collected and
> no API-calling code is implemented yet.

## The run matrix — 750 queries

**5 engines × 50 prompts × 3 passes = 750 queries.**

- **Engines:** ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews.
- **Prompts (50):** 4 buckets — Fan 13, Sponsor 12, Free-Agent 12, Business 13.
- **Passes:** 3 per prompt per engine, to control for output variance.

Four engines run via public APIs; **Google AI Overviews has no public API** and is
captured from real SERPs via a SERP provider or structured manual capture.

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
collect/   → data/raw/   → score.py        → generate/
(query the    (verbatim     (parse, apply     (ranked index CSV
 engines)      audit trail)   point rules,      + 30 one-pagers)
                              aggregate,
                              normalize)
```

Collection and scoring are **separate stages** to avoid bias.

## Layout

| Path | Purpose |
|---|---|
| [CLAUDE.md](CLAUDE.md) | Locked methodology spec — source of truth. |
| [prompts/prompts.csv](prompts/prompts.csv) | The 50 locked prompts (id, bucket, text). |
| [reference/teams.csv](reference/teams.csv) | 30-team entity-matching backbone (aliases, ballpark, owner, division, +cross-ref columns to fill). |
| [data/schema.md](data/schema.md) | One-row-per-response data schema. |
| `data/raw/` | Verbatim engine responses — the audit trail. |
| `collect/` | One module per engine; reads keys from `.env`. |
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
