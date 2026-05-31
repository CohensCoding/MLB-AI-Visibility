# MLB Citation Share Index — Locked Spec

This file is the **single source of truth** for the methodology. It is locked.
Changing these rules mid-run destroys defensibility — do not alter them once data
collection begins. Modeled exactly on the 5W NFL Citation Share Index 2026 so MLB
results are directly comparable to that precedent.

The full narrative build guide lives in
[spec/MLB-Citation-Share-Index-Build-Playbook.md](spec/MLB-Citation-Share-Index-Build-Playbook.md).
The finished NFL reference output we are reproducing is
[spec/5W-NFL-Citation-Share-Index-2026.csv](spec/5W-NFL-Citation-Share-Index-2026.csv).

---

## Scoring rules

Applied per response, derived only from the raw logs — never scored by hand.

| Mention | Points |
|---|---|
| 1st team named in the response | **5** |
| 2nd team named | **3** |
| Any other mention of a team | **1** |
| Attribution-only — ballpark / owner / logo named, no team name | **1** |

- A team can score **only once per response** — take its highest-value mention,
  do not stack. (Named first *and* mentioned again later = 5, not 6.)
- Mention order is determined by position in the response text.
- Attribution credit is powered by the alias / ballpark / owner strings in
  [reference/teams.csv](reference/teams.csv). "Dodger Stadium" or "Guggenheim"
  without "Dodgers" still earns that team 1 point.

## Normalization

- Sum each team's raw points across all 1,500 queries → raw aggregate.
- Top team is anchored to **100.0**.
- Every other team = `(team raw / max raw) × 100`.
- This preserves the spread while fixing the top (in the NFL version the leader
  scored 100.0 and #2 landed at 51.6).

## Run matrix — 1,500 queries

**5 engines × 100 prompts × 3 passes = 1,500 queries.**

| Dimension | Values |
|---|---|
| Engines (5) | ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews |
| Prompts (100) | See [prompts/prompts.csv](prompts/prompts.csv) — 8 categories |
| Passes (3) | Repeat each prompt 3× per engine to control output variance |

### Collection method — API (locked)

Collection is via **provider APIs**, programmatically, one fresh call per query
with **no history carried between calls**. Run with `python -m collect.run_collection`
(pre-flight: `python -m collect.test_connection`). Each response is appended
verbatim to [data/capture_log.csv](data/capture_log.csv).

| Engine | Access | Model pin (.env) | Web search / grounding |
|---|---|---|---|
| ChatGPT | OpenAI Responses API | `OPENAI_MODEL` | **on** — `web_search` tool |
| Claude | Anthropic Messages API | `ANTHROPIC_MODEL` | **on** — `web_search` tool |
| Gemini | Google AI Studio | `GEMINI_MODEL` | **on** — Google Search grounding |
| Perplexity | Sonar API | `PERPLEXITY_MODEL` | **on** — Sonar searches natively |
| Google AI Overviews | **No public API** — captured from real Google SERPs via SerpApi (`SERPAPI_API_KEY`) | n/a (`model_version` = `SERP/AIO`) | **on** — live SERP |

- **Locked model per engine:** the exact model string is read from the `*_MODEL`
  var in `.env` and **written to `model_version` on every row** — never hardcoded —
  so a refresh is reproducible from the recorded pin alone.
- **Search is on** for every engine (the `search_enabled` column records this).
- **Consistency controls:** fresh call per query, no conversation memory,
  US/English locale (`hl=en`, `gl=us` for SERPs), and date + model version stamped
  on **every** call.
- **Deprecated:** the prior **manual capture** approach is superseded by this API
  pipeline. The hand-captured ChatGPT responses are **retained verbatim** at
  `data/capture_log_chatgpt.csv` (old 50-prompt/bucket schema, model
  `GPT-5.5 Instant`, captured 2026-05-29) — kept for history, **not** consumed by
  the API pipeline or `score.py`. Do not delete; the manual path may return only if
  we ever need an engine without an API.

## Prompt categories (100 total)

| Category | Count |
|---|---|
| AI-First Fan | 15 |
| Fan Experience & Tickets | 13 |
| Sponsorship & Brand Partnership | 15 |
| Audience & Reach | 12 |
| Market Relevance & Competitive Standing | 12 |
| Brand Identity & Narrative | 13 |
| Business & Franchise Strength | 12 |
| Talent & Org Reputation | 8 |

## Cross-reference layers

Joined to the normalized scores to create the story:

- **2025 MLB final standings** → on-field rank.
- **MLB franchise valuations** → valuation rank.
- **Social media followers** (X + TikTok + Instagram) → reach context.

Gap columns:

- **Performance Gap = Citation Share rank − on-field rank.**
- **Value Gap = Citation Share rank − valuation rank.**

A positive gap means the team ranks worse in citations than it "should" given its
on-field or valuation rank — that is where the headlines live.

### Cross-reference source rules (locked)

Every value in `standing_2025_rank`, `valuation_rank`, and the four follower
columns in [reference/teams.csv](reference/teams.csv) is filled from a **dated
primary source — never from model memory** — with provenance recorded in the
per-metric source columns (`standing_source`, `valuation_source`, `social_source`)
and `date_pulled`.

- **Standings** (`standing_2025_rank` · `standing_source`): **MLB 2025 final
  standings**, ranked by wins; ties broken by farther 2025 postseason advancement,
  then run differential. Completed-season anchor — not in-progress or projected.
- **Valuation** (`valuation_rank` · `valuation_source`): **Forbes Most Valuable
  Teams 2026** (published 2026-03-20). Use the **2026** edition, not 2025. One
  publisher, held constant: **CNBC and Forbes 2026 figures diverge** (Mike Ozanian,
  who originated the Forbes valuations, now publishes via CNBC) — **Forbes** is used
  here to match the 5W NFL precedent.
- **Social** (`followers_x` · `followers_tiktok` · `followers_instagram` ·
  `followers_total` · `social_source`): **team official verified accounts on X,
  TikTok, and Instagram**, captured **2026-05-29**. `followers_total` = the sum of
  the three platform columns. Stored as plain integers (no thousands separators).

## Tiers

| Tier | Label | Citation Share |
|---|---|---|
| I | Dominant | 50+ |
| II | Established | 20–49 |
| III | Present | 1–19 |
| IV | Dead Zone | 0.0 (invisible despite real value) |

## Refresh cadence

V1 now; refresh quarterly; **methodology held constant** across refreshes to
preserve trend integrity.

---

## Repo structure

```
spec/         Source playbook + NFL reference CSV (read-only inputs)
prompts/      prompts.csv — the 100 locked prompts (id, category, text)
reference/    teams.csv — 30-team entity-matching backbone (aliases, ballpark, owner…)
data/capture_log.csv  Verbatim API/SERP responses — the audit trail (one row per query)
data/raw/     Reserved for any out-of-band raw captures
data/schema.md   The capture-log + reference-table schemas
collect/      API collection pipeline (config + per-engine collectors + run_collection + test_connection)
score.py      Stub: parse capture log → apply point rules → aggregate by team/category/engine → normalize
generate/     Stub: emit the ranked index CSV + 30 per-team one-pagers
```

## Working agreements

- **Collection and scoring are separate stages** — do not interpret or score
  during collection, to avoid bias.
- Secrets live only in `.env` (gitignored). Never commit keys.
- The raw response log is the audit trail; everything downstream is derived from it
  and must be reproducible from it alone.

## Runtime

- The `.venv` is built on **`/usr/bin/python3` (Apple system Python 3.9)** — the
  only working interpreter on this machine. Homebrew Python is currently broken by
  an **expat / libexpat version mismatch**, so it is not usable.
- Python 3.9 is end-of-life (google-auth emits a deprecation warning); it **works
  for now**, so this is not a blocker. **Long-term, move to a newer non-Homebrew
  Python** (e.g. a pyenv/python.org 3.11+ build) once the expat breakage is sorted.
