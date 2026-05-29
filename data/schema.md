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
