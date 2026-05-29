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

- Sum each team's raw points across all 750 queries → raw aggregate.
- Top team is anchored to **100.0**.
- Every other team = `(team raw / max raw) × 100`.
- This preserves the spread while fixing the top (in the NFL version the leader
  scored 100.0 and #2 landed at 51.6).

## Run matrix — 750 queries

**5 engines × 50 prompts × 3 passes = 750 queries.**

| Dimension | Values |
|---|---|
| Engines (5) | ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews |
| Prompts (50) | See [prompts/prompts.csv](prompts/prompts.csv) |
| Passes (3) | Repeat each prompt 3× per engine to control output variance |

Engine access note: ChatGPT, Claude, Perplexity, and Gemini have public APIs.
**Google AI Overviews has no public API** and must be captured from real SERPs
via a SERP provider or structured manual capture. Document the method per engine.

Consistency controls: fresh session / no memory per query, personalization
stripped where possible, fixed US/English locale, recorded temperature/settings,
and date + model version stamped on **every** call.

## Prompt buckets (50 total)

| Bucket | Count |
|---|---|
| Fan | 13 |
| Sponsor | 12 |
| Free-Agent | 12 |
| Business | 13 |

## Cross-reference layers

Joined to the normalized scores to create the story:

- **2025 MLB final standings** → on-field rank.
- **Forbes 2025 MLB franchise valuations** → valuation rank.
- **Social media followers / engagement** → reach context.

Gap columns:

- **Performance Gap = Citation Share rank − on-field rank.**
- **Value Gap = Citation Share rank − Forbes valuation rank.**

A positive gap means the team ranks worse in citations than it "should" given its
on-field or valuation rank — that is where the headlines live.

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
prompts/      prompts.csv — the 50 locked prompts (id, bucket, text)
reference/    teams.csv — 30-team entity-matching backbone (aliases, ballpark, owner…)
data/raw/     Verbatim engine responses — the audit trail (one file per response)
data/schema.md   The one-row-per-response data schema
collect/      One stub module per engine; reads API keys from .env (calls NOT yet implemented)
score.py      Stub: parse raw logs → apply point rules → aggregate by team/bucket/engine → normalize
generate/     Stub: emit the ranked index CSV + 30 per-team one-pagers
```

## Working agreements

- **Collection and scoring are separate stages** — do not interpret or score
  during collection, to avoid bias.
- Secrets live only in `.env` (gitignored). Never commit keys.
- The raw response log is the audit trail; everything downstream is derived from it
  and must be reproducible from it alone.
