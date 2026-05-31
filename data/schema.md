# Capture-log schema — `data/capture_log.csv`

Every engine call produces exactly one row, appended by the collection pipeline
(`collect/run_collection.py`). Scoring is derived entirely from this log; nothing is
scored by hand. Keep the raw text verbatim — it is the audit trail.

| Column | Type | Description |
|---|---|---|
| `query_id` | string | Unique id, `<engine>_<prompt_id>_p<pass>`, e.g. `chatgpt_fan_01_p1`. |
| `category` | string | Prompt category (one of the 8 — see [prompts/prompts.csv](../prompts/prompts.csv)). |
| `prompt_id` | string | Prompt id, e.g. `fan_01` (matches prompts.csv). |
| `prompt_text` | string | The exact prompt sent. |
| `engine` | string | `ChatGPT`, `Claude`, `Perplexity`, `Gemini`, or `Google AI Overviews`. |
| `pass_number` | int | 1–3 for the 4 API engines; always 1 for Google AI Overviews (single cached Overview per query). |
| `model_version` | string | Exact pinned model string from `.env` (e.g. `gpt-4o`); `SERP/AIO` for AI Overviews. Model drift is real. |
| `date_run` | ISO 8601 | UTC timestamp of the call. |
| `raw_response_text` | string | The full, verbatim response. Never edited. |
| `search_enabled` | bool | Whether web search / grounding was on for the call (always true in V1). |
| `captured` | bool | True if the response was captured successfully; False rows are gaps to re-run. |

## Notes

- **One fresh call per query**, no history carried between calls. The pipeline is
  resumable: rows with `captured == true` are skipped on re-run.
- Scoring-derived fields (`teams_mentioned`, `first_team`, `second_team`,
  `other_teams`, `attribution_only_teams`) are **not** stored here — they are
  produced downstream by `score.py` from `raw_response_text`, using the
  alias/ballpark/owner strings in [reference/teams.csv](../reference/teams.csv).
- **One score per team per response** — highest-value mention wins; do not stack
  (applied at scoring time, not collection time).
- `data/raw/` is reserved for any out-of-band raw captures; the primary audit
  trail is `data/capture_log.csv`.

---

# Reference table schema — `reference/teams.csv`

One row per franchise (30 total). The entity-matching backbone and the source of the
cross-reference joins. Cross-reference values are filled from dated primary sources
(never model memory); see the locked source rules in [CLAUDE.md](../CLAUDE.md).

| Column | Type | Description |
|---|---|---|
| `team_id` | string | Short code, e.g. `LAD`. |
| `full_name` | string | Official franchise name, e.g. `Los Angeles Dodgers`. Join key for the fill files. |
| `aliases` | string | Comma-separated nicknames an AI might use (drives entity matching). |
| `city` | string | Home market. |
| `ballpark` | string | Home ballpark (powers attribution credit). |
| `owner` | string | Ownership group (powers attribution credit). |
| `division` | string | e.g. `NL West`. |
| `standing_2025_rank` | int | 2025 on-field rank, 1–30. |
| `valuation_rank` | int | Franchise valuation rank, 1–30. |
| `followers_x` | int | X (Twitter) followers, plain integer (no thousands separators). |
| `followers_tiktok` | int | TikTok followers, plain integer. |
| `followers_instagram` | int | Instagram followers, plain integer. |
| `followers_total` | int | `followers_x + followers_tiktok + followers_instagram`. |
| `standing_source` | string | Provenance for `standing_2025_rank`. |
| `valuation_source` | string | Provenance for `valuation_rank`. |
| `social_source` | string | Provenance for the four follower columns. |
| `date_pulled` | ISO 8601 | Date the cross-reference values were captured. |

## Locked sources

- **Standings** (`standing_2025_rank` / `standing_source`): MLB 2025 final standings,
  ranked by wins; ties broken by farther 2025 postseason advancement, then run
  differential.
- **Valuation** (`valuation_rank` / `valuation_source`): Forbes Most Valuable Teams
  2026 (published 2026-03-20).
- **Social** (four follower columns / `social_source`): team official verified
  accounts on X, TikTok, and Instagram, captured 2026-05-29. `followers_total` must
  equal the sum of the three platform columns.
