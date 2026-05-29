# The MLB Citation Share Index — Build & Execution Playbook

**A concrete, step-by-step guide to producing an AI-visibility ranking of all 30 MLB franchises, modeled on the 5W NFL Citation Share Index 2026.**

Version 1.0 · Internal build document

---

## 0. The thesis (why this exists)

Sponsorship inventory, free-agent decisions, and fan acquisition are all priced on *attention*. A growing share of that attention now flows through AI answer engines — ChatGPT, Claude, Perplexity, Gemini, and Google AI Overviews — rather than broadcast or social feeds. When a fan, sponsor, agent, or investor asks an AI engine a baseball question, some teams get named constantly and others are invisible. No one has measured this for MLB, and no MLB club communications department is tracking it.

The deliverable is a defensible, replicable index that scores all 30 teams on "Citation Share," cross-references it against valuation and on-field performance to expose gaps, and produces a per-team one-pager that becomes the personalized hook for outreach.

The build itself is not technically hard. The value is in doing it rigorously, packaging it as an open standard rather than a sales gimmick, and being first.

---

## 1. Project overview & success criteria

**Objective:** Rank all 30 MLB franchises by AI Citation Share, identify the most newsworthy gaps, and produce outreach-ready collateral.

**Scope:** 30 teams. 5 AI engines. 50 prompts across 4 buckets. 3 passes per prompt per engine = **750 total queries**.

**Final deliverables:**
1. **Master CSV dataset** — team-by-team, bucket-by-bucket, engine-by-engine scoring (the proof).
2. **The ranked Index** — all 30 teams with Citation Share Score (0–100), bucket sub-scores, Performance Gap, Value Gap, tier.
3. **Per-team one-pagers** (×30) — the personalized outreach asset.
4. **Methodology PDF** — open, replicable spec that makes the whole thing credible.
5. **Headline findings narrative** — the 6–8 story angles that make it shareable.

**Definition of done:** Every team has a normalized 0–100 score, two gap columns, a one-pager, and the methodology is documented well enough that an outside skeptic could reproduce it.

**Realistic timeline:** 2–3 focused weeks solo. Phase breakdown and effort estimates are in each section below.

---

## 2. Lock the methodology first (the spec)

Decide and document these *before* collecting a single data point. Changing the rules mid-run destroys defensibility. This mirrors the 5W spec exactly so your results are directly comparable to their NFL precedent.

### Scoring rules
- First franchise named in an answer = **5 points**
- Second franchise named = **3 points**
- Any other mention of a team = **1 point**
- Logo, owner, or ballpark named *without* the team name = **1 point** (attribution credit)
- A team can only score once per response (take its highest-value mention; do not stack).

### Normalization
- Sum each team's raw points across all 750 queries → raw aggregate.
- Normalize so the **top team = 100.0**, and every other team = `(team raw / max raw) × 100`.
- This is why, in the NFL version, the leader scored exactly 100.0 and #2 landed at 51.6 — the spread is preserved, the top is anchored.

### Run structure
- **5 engines:** ChatGPT, Claude, Perplexity, Gemini, Google AI Overviews.
- **50 prompts** across 4 buckets (Fan, Sponsor, Free-Agent, Business).
- **3 passes** per prompt per engine to control for output variance.
- Capture every raw response with a timestamp and the model version used.

### Cross-reference layers (these create the story)
- 2025 MLB final standings (on-field rank).
- Forbes 2025 MLB franchise valuations (valuation rank).
- Social media engagement / follower totals.
- **Performance Gap** = Citation Share rank − on-field rank.
- **Value Gap** = Citation Share rank − Forbes valuation rank.

### Refresh cadence (state it up front)
- V1 now; refresh quarterly; **methodology held constant** across refreshes to preserve trend integrity. Announcing the cadence up front signals this is a standard, not a one-off.

---

## 3. Phase 1 — Setup & infrastructure (effort: ~1–2 days)

### 3.1 Build the team reference table (the entity-matching backbone)
This is the single most important asset for accurate scoring. For each of the 30 teams, capture every string an AI might use to refer to it:

| Field | Example (one team) |
|---|---|
| `team_id` | LAD |
| `full_name` | Los Angeles Dodgers |
| `nicknames / aliases` | Dodgers, LA Dodgers, the Boys in Blue |
| `city / market` | Los Angeles |
| `ballpark` | Dodger Stadium |
| `owner / ownership group` | Guggenheim Baseball Management |
| `division` | NL West |
| `2025_standing_rank` | (fill from standings) |
| `forbes_valuation_rank` | (fill from Forbes) |
| `social_followers` | (fill from public counts) |

Aliases and ballpark/owner strings power the **attribution-credit** rule (a response that says "Dodger Stadium" or "Guggenheim" without "Dodgers" still earns 1 point).

### 3.2 Decide engine access (the real execution constraint — read carefully)
The five engines do **not** all offer equal access. Plan around this honestly:

- **ChatGPT** — API available (OpenAI). Note the API model can differ from the consumer product with browsing; pick one and document it.
- **Claude** — API available (Anthropic).
- **Perplexity** — API available (Sonar models). Good for citation-style answers.
- **Gemini** — API available (Google AI Studio / Vertex).
- **Google AI Overviews** — **no public API.** These must be captured from real Google search result pages, either manually or via a SERP data provider (e.g., a SERP API service). This is the one that requires extra plumbing. Respect each platform's terms of service.

**Recommendation:** Run the four chat engines via their APIs for speed and consistency; handle Google AI Overviews via a SERP provider or structured manual capture. Document the method used for each engine in the methodology.

### 3.3 Consistency controls (protects defensibility)
- Fresh session / no conversation memory or personalization per query.
- Strip account-level personalization where possible.
- Fix and record region/locale (US), language (English), and temperature/settings.
- Record date and model version for every single call — model drift is real and dated results are your defense.

### 3.4 Design the data schema
One row per query response, so nothing is lost:

```
query_id | bucket | prompt_text | engine | model_version | pass_number |
date_run | raw_response_text | teams_mentioned (ordered list) |
first_team | second_team | other_teams | attribution_only_teams
```

Scoring is derived from this raw log — never score by hand off the top of your head.

---

## 4. Phase 2 — Finalize the prompt set (effort: ~half day)

50 prompts, baseball-specific, neutral (never name a team in the prompt), and phrased the way a real fan/sponsor/agent/investor would ask. Below is a ready-to-run MLB set matching the 5W bucket structure (Fan 13, Sponsor 12, Free-Agent 12, Business 13).

### Fan bucket (13)
1. What's the most exciting MLB team to watch right now?
2. Which MLB team has the best culture?
3. Best MLB team for a new fan to start following?
4. Which MLB franchise has the most loyal fans?
5. What's the most iconic MLB franchise?
6. Which MLB team has the best ballpark experience?
7. Most underrated MLB team in 2026?
8. Which MLB team has the most compelling storyline this season?
9. Best MLB team to watch on a national broadcast?
10. Which MLB franchise has the strongest brand identity?
11. Which MLB team has the best rivalries?
12. Which MLB team has the best uniforms?
13. Which MLB team has the most passionate fanbase?

### Sponsor bucket (12)
1. Which MLB franchise is the best brand-partnership opportunity?
2. Which MLB team has the most valuable sponsorship inventory?
3. Best MLB team for a luxury brand to sponsor?
4. Which MLB franchises have the strongest corporate partnerships?
5. Most innovative MLB team in marketing?
6. Which MLB team reaches the most affluent fans?
7. Best MLB franchise for a tech-brand partnership?
8. Which MLB team has the most international reach?
9. Most marketable MLB franchise globally?
10. Which MLB team has the highest social media engagement?
11. Best MLB franchise for a consumer-brand activation?
12. Which MLB team has the strongest jersey and merchandise sales?

### Free-agent bucket (12)
1. Best MLB team to play for as a starting pitcher?
2. Which MLB franchise treats its players the best?
3. Best MLB city for a free agent to sign with?
4. Which MLB team has the best ownership group?
5. Best MLB organization for a young player to develop?
6. Which MLB team has the best coaching staff right now?
7. Most stable MLB franchise to sign with long-term?
8. Best MLB team for a hitter to maximize their numbers?
9. Which MLB team offers the best off-field lifestyle?
10. Most player-friendly MLB franchise?
11. Best MLB team for a reliever to rebuild value?
12. Best MLB team for a veteran looking to win a ring?

### Business bucket (13)
1. Which MLB franchise is most valuable?
2. Which MLB team has the highest revenue?
3. Most profitable MLB franchise?
4. Which MLB team has the best business model?
5. Most innovative MLB ownership group?
6. Best-run MLB front office?
7. Which MLB franchise has the strongest balance sheet?
8. Which MLB team has the most media-rights leverage?
9. Most influential MLB franchise in league business decisions?
10. Which MLB team has the best stadium economics?
11. Best MLB franchise for institutional investors to study?
12. Which MLB team is best positioned for future revenue growth?
13. Which MLB franchise has the strongest international growth strategy?

**Prompt hygiene checklist:** neutral wording, no team named, consistent phrasing across passes, no leading qualifiers, US/English framing.

---

## 5. Phase 3 — Data collection (effort: ~2–4 days)

### The run matrix
50 prompts × 5 engines × 3 passes = **750 queries.** Track completion against this matrix so nothing is skipped.

### Execution steps
1. For each engine, loop through all 50 prompts, 3 passes each.
2. Save the full raw response verbatim into the data log, with timestamp + model version.
3. For Google AI Overviews, capture the Overview text from a real SERP via your chosen method.
4. Do not interpret or score during collection — collection and scoring are separate stages to avoid bias.
5. Spot-check 5% of responses live to confirm capture fidelity.

### Tip
Run all three passes of a given prompt close together in time so model drift within a prompt is minimal, but separate enough to capture genuine variance (fresh sessions each time).

---

## 6. Phase 4 — Parsing & scoring (effort: ~2–3 days)

### 6.1 Entity extraction
For each raw response, detect every team reference using the reference table (full names, aliases, ballparks, owners). Resolve each match to a `team_id`.

### 6.2 Determine mention order
Identify which team is named **first**, which is **second**, and which are **other** mentions, by position in the response text.

### 6.3 Apply the point rules
- 1st team → 5 pts
- 2nd team → 3 pts
- other mentioned teams → 1 pt each
- attribution-only (ballpark/owner/logo, no team name) → 1 pt
- one score per team per response (highest value wins)

### Scoring logic (pseudocode)
```
for each response:
    teams = extract_team_mentions(response, reference_table)  # ordered
    scored = {}
    for position, team in enumerate(teams):
        if position == 0:        pts = 5
        elif position == 1:      pts = 3
        else:                    pts = 1
        scored[team] = max(scored.get(team, 0), pts)
    for team in attribution_only_mentions(response):
        scored[team] = max(scored.get(team, 0), 1)
    add scored to running totals (by team, by bucket, by engine)
```

### 6.4 Aggregate & normalize
- Sum per team overall, and separately per bucket and per engine (you'll want the bucket cuts for the one-pagers).
- Normalize overall: `score = (team_raw / max_team_raw) × 100`. Top team = 100.0.

---

## 7. Phase 5 — Cross-reference & gap analysis (effort: ~1 day)

1. Join the normalized scores to the reference table's standing rank, valuation rank, and social data.
2. Rank teams 1–30 by Citation Share.
3. Compute **Performance Gap** = Citation Share rank − on-field rank.
4. Compute **Value Gap** = Citation Share rank − Forbes valuation rank.
5. Assign tiers, e.g.:
   - **Tier I · Dominant** — Citation Share 50+
   - **Tier II · Established** — 20–49
   - **Tier III · Present** — 1–19
   - **Tier IV · Dead Zone** — 0.0 (invisible despite real value)

The gap columns are where the headlines live. A team that is highly valued but low in citations, or a recent winner that AI hasn't "caught up to," is a story.

---

## 8. Phase 6 — Insight generation (effort: ~1 day)

Mine the table for the 6–8 most newsworthy findings. Use the 5W finding archetypes as your hunting list:

- **Concentration** — what % of all queries does the #1 team take? (NFL: Cowboys took 39%.)
- **Dead zone** — which teams scored 0.0, and what's their combined valuation?
- **Champion underexposed** — does the most recent World Series winner rank low?
- **Brand survives losing** — a non-contender that still ranks high.
- **Largest negative gap** — high on-field, low visibility.
- **Sponsorship mispricing** — high valuation, low citations (the sponsor-facing hook).
- **Brand outperforming valuation** — "invisible assets on the balance sheet."
- **Nobody is measuring this** — the closing argument.

Write each as a one-line headline + a two-sentence support. These become the report's spine and your outreach subject lines.

---

## 9. Phase 7 — Deliverable production (effort: ~2–3 days)

### 9.1 The ranked Index (master table)
All 30 teams: Rank · Team · Citation Share · Fan · Sponsor · FA · Business · On-Field · Perf Gap · Forbes · Val Gap · Tier.

### 9.2 Per-team one-pager (your outreach asset — build a template, generate ×30)
Each should contain:
- Team name + their Citation Share Score and overall rank.
- Their rank in each of the 4 buckets (where are they strong/invisible?).
- Their Performance Gap and Value Gap, in plain language.
- 2–3 representative prompts where they were absent but a rival was named first.
- One sentence on the commercial implication ("a sponsor is paying for reach the AI engines aren't returning").
- A single forward CTA ("here's what closing this gap looks like").

### 9.3 Methodology one-pager
Engines, prompt count, buckets, scoring rules, normalization, cross-references, refresh cadence, and a clear limitations section. "Open · Replicable · Quarterly refresh" framing.

### 9.4 The CSV
The full raw + scored dataset, downloadable, so the work is auditable. This is what makes skeptics believe you.

---

## 10. Phase 8 — QA & defensibility (effort: ~1 day)

- Re-run any anomalous result (e.g., a top-valued team scoring 0) to confirm it's real, not a capture error.
- Confirm every team alias resolves correctly — entity-matching errors are the #1 risk to credibility.
- Verify the three passes show plausible variance, not identical or wildly divergent output.
- Date- and version-stamp everything.
- Write the **limitations** section honestly: it's a snapshot of model behavior in a defined window; only 5 engines and 50 prompts; Citation Share is a proxy for AI surface frequency, not a measure of authority, accuracy, or operational performance; correlation isn't causation. Stating limits *increases* credibility.

---

## 11. Refresh & productization

- Schedule quarterly refreshes (e.g., offseason, spring training, mid-season, postseason), methodology unchanged.
- Turn the pipeline into a repeatable script so each refresh is a re-run, not a rebuild.
- Trend lines across refreshes ("Team X climbed 6 spots") become their own recurring story and a reason for teams to keep paying attention.

---

## 12. Risk register

| Risk | Mitigation |
|---|---|
| No API for Google AI Overviews | Use a SERP data provider or structured manual capture; document the method. |
| Engine ToS / rate limits | Respect terms; throttle; keep volumes reasonable; document access method. |
| Model drift between runs | Timestamp + version every call; run passes close in time; hold methodology constant. |
| Entity-matching errors | Build a thorough alias/ballpark/owner table; QA every team's matches. |
| "It's just a proxy" pushback | Lead with the honest limitations section; frame as one metric among several. |
| Looks like a sales gimmick | Publish open methodology + downloadable data; let the numbers carry it. |

---

## 13. Recommended tech stack

**Fastest credible path (Python):**
- API clients for OpenAI, Anthropic, Perplexity, Google.
- A SERP provider for Google AI Overviews.
- `pandas` for the data log and scoring; simple string/alias matching for entity extraction (a small curated alias table beats a fancy NLP model here).
- Output to CSV; generate one-pagers from a template.

**No-/low-code fallback:** run queries manually, log into a spreadsheet, score with formulas. Slower, but fully viable for V1 and arguably *more* defensible because every response is human-verified.

---

## 14. Execution checklist (do these in order)

1. Lock the methodology spec (Section 2).
2. Build the 30-team reference/alias table (3.1).
3. Decide and set up engine access, incl. the Google AI Overviews path (3.2).
4. Finalize the 50 prompts (Section 4).
5. Run the 750-query matrix; log every raw response (Section 5).
6. Parse, score, normalize (Section 6).
7. Join cross-reference data; compute both gaps; assign tiers (Section 7).
8. Mine the 6–8 headline findings (Section 8).
9. Produce the Index table, 30 one-pagers, methodology page, and CSV (Section 9).
10. QA and write the limitations section (Section 10).
11. (You handle distribution to the teams.)
12. Schedule the first quarterly refresh (Section 11).

---

*Modeled on the publicly published methodology of The 5W NFL Citation Share Index 2026 (Ronn Torossian, 5WPR). Adapted for Major League Baseball's 30 franchises.*
