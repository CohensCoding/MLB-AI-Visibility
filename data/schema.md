# Data schema — one row per query response

Every engine call produces exactly one row. Scoring is derived entirely from this
log; nothing is scored by hand. Keep the raw text verbatim — it is the audit trail.

| Column | Type | Description |
|---|---|---|
| `query_id` | string | Unique id for this response, e.g. `F1_chatgpt_pass1`. |
| `bucket` | string | One of: `Fan`, `Sponsor`, `Free-Agent`, `Business`. |
| `prompt_text` | string | The exact prompt sent (matches [prompts/prompts.csv](../prompts/prompts.csv)). |
| `engine` | string | One of: `ChatGPT`, `Claude`, `Perplexity`, `Gemini`, `Google AI Overviews`. |
| `model_version` | string | Exact model/version used (e.g. `gpt-4o-2024-08-06`). Model drift is real. |
| `pass_number` | int | 1, 2, or 3. |
| `date_run` | ISO 8601 | Date/time the call was made. |
| `raw_response_text` | string | The full, verbatim response. Never edited. |
| `teams_mentioned` | list | Ordered list of `team_id`s detected, by position in the text. |
| `first_team` | string | `team_id` named first → 5 pts. |
| `second_team` | string | `team_id` named second → 3 pts. |
| `other_teams` | list | Remaining mentioned `team_id`s → 1 pt each. |
| `attribution_only_teams` | list | `team_id`s credited via ballpark/owner/logo with no team name → 1 pt each. |

## Notes

- **One score per team per response** — highest-value mention wins; do not stack.
- `teams_mentioned` is the ordered union that drives `first_team` / `second_team` /
  `other_teams`. Entity resolution uses the alias/ballpark/owner strings in
  [reference/teams.csv](../reference/teams.csv).
- A team appearing in `attribution_only_teams` should not also appear in
  `teams_mentioned` for the same response unless its name was also used.
- Store raw responses as individual files under `data/raw/`; this schema describes
  the parsed/structured log that `score.py` consumes.

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
