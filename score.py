"""Parse the raw response logs, apply the point rules, aggregate, and normalize.

This is the scoring stage — kept strictly separate from collection (CLAUDE.md).
Scoring is derived ONLY from the raw capture log (data/capture_log.csv); never
scored by hand. Aggregation is by team, by category, and by engine.

Point rules (CLAUDE.md §Scoring rules):
    1st team named            -> 5 pts
    2nd team named            -> 3 pts
    any other team mention    -> 1 pt
    attribution-only mention  -> 1 pt   (ballpark/owner/logo, no team name)
    one score per team per response (highest value wins; do not stack)

Normalization (CLAUDE.md §Normalization):
    top team -> 100.0; others -> (team raw / max raw) * 100

STUB ONLY — logic is not implemented yet. Scaffold and pseudocode only.
"""

from __future__ import annotations

import csv
import re

REFERENCE_CSV = "reference/teams.csv"

# ---------------------------------------------------------------------------
# Entity extraction (STAGE 1)
# ---------------------------------------------------------------------------
# Ambiguous bare tokens that map to >1 team — NEVER resolved on their own.
# A team is only credited for these via an unambiguous name/alias/ballpark:
#   "los angeles" -> LAD (Dodgers) or LAA (Angels)
#   "new york"    -> NYY (Yankees) or NYM (Mets)
#   "chicago"     -> CHC (Cubs) or CWS (White Sox)
#   "sox"         -> BOS (Red Sox) or CWS (White Sox)
# (LAD's alias list literally contains "Los Angeles"; it is dropped here so a
#  bare "Los Angeles" never silently becomes the Dodgers. "Red Sox"/"White Sox"
#  still resolve because longer, unambiguous tokens are matched first.)
AMBIGUOUS = {"los angeles", "new york", "chicago", "sox", "la", "ny", "nyc"}

# Generic owner words that must never match on their own (false-positive risk).
GENERIC_OWNER = {
    "baseball", "sports", "group", "holdings", "management", "enterprises",
    "family", "ownership", "communications", "global", "llc", "inc", "co",
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def clean_text(text: str) -> str:
    """Strip noise that would corrupt matching / mention order.

    Normalizes curly quotes to straight (so apostrophe aliases like A's / M's /
    O's / 'Stros match — responses use Unicode ' " but teams.csv uses straight '),
    removes markdown images, keeps markdown-link labels (drops the URL), removes
    bare URLs and [1][2] citation markers.
    """
    text = (text.replace("’", "'").replace("‘", "'")   # ' ' -> '
                .replace("“", '"').replace("”", '"')   # " " -> "
                .replace("ʼ", "'"))                          # modifier apostrophe
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)        # ![alt](url) images
    text = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", text)      # [label](url) -> label
    text = re.sub(r"\[\d+\]", " ", text)                      # [1] citation markers
    text = re.sub(r"https?://\S+", " ", text)                 # bare URLs
    return text


def _owner_tokens(owner: str) -> list[str]:
    """FULL owner match strings only — never a bare surname.

    Bare surnames (Cohen, Henry, Davis, Johnson, Sherman…) are common words that
    false-positive on unrelated text, so every owner token must be the FULL name
    (>=2 words): the full person name ("Steve Cohen"), the full org string
    ("Guggenheim Baseball Management", "Pohlad family"), or the lead name of an
    "-led ownership group" ("David Rubenstein"). Year/date parentheticals dropped.
    """
    toks: list[str] = []
    for paren in re.findall(r"\(([^)]*)\)", owner):           # person/org in parens
        paren = paren.strip()
        if paren and not re.search(r"\d", paren):             # skip "(2024)" etc.
            toks.append(paren)
    base = re.sub(r"\([^)]*\)", "", owner).strip(" -")
    low = base.lower()
    if "-led" in low:                                         # "David Rubenstein-led ..."
        toks.append(base[: low.index("-led")].strip())
    else:
        toks.append(base)                                     # full org / "X family"
    # Require the FULL name (>=2 words) and not all-generic words.
    out = []
    for t in (s.strip() for s in toks):
        words = t.split()
        if len(words) < 2:                                    # drops bare surnames
            continue
        if all(_norm(w) in GENERIC_OWNER for w in words):
            continue
        out.append(t)
    return out


def load_reference(path: str = REFERENCE_CSV) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def build_matchers(teams: list[dict]):
    """Compile (regex, team_id, kind, token) entries, longest token first.

    kind is 'name' (full name / alias) or 'attribution' (ballpark / owner).
    Word-boundary matching (no surrounding alnum) so 'Angels' never fires inside
    'Angeles'. Longest-first so multi-word names beat substrings.
    """
    seen: set[tuple] = set()
    entries: list[tuple[str, str, str]] = []

    def add(token: str, team_id: str, kind: str) -> None:
        t = _norm(token)
        if not t or t in AMBIGUOUS:
            return
        key = (t, team_id, kind)
        if key in seen:
            return
        seen.add(key)
        entries.append((token.strip(), team_id, kind))

    for r in teams:
        tid = r["team_id"]
        add(r["full_name"], tid, "name")
        for alias in r["aliases"].split(","):
            add(alias, tid, "name")
        ballpark = r["ballpark"]
        add(ballpark, tid, "attribution")
        if " at " in ballpark.lower():                        # "...at Camden Yards"
            add(ballpark.lower().split(" at ", 1)[1], tid, "attribution")
        for tok in _owner_tokens(r["owner"]):
            add(tok, tid, "attribution")

    compiled = []
    for token, tid, kind in entries:
        pat = re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        compiled.append((len(token), pat, tid, kind, token))
    compiled.sort(key=lambda x: -x[0])                        # longest token first
    return compiled


def find_mentions(text: str, compiled) -> list[dict]:
    """All non-overlapping team matches in cleaned text, sorted by position.

    Longest tokens win overlaps (so 'White Sox' beats 'Sox', 'Los Angeles
    Dodgers' beats the dropped 'Los Angeles', etc.).
    """
    cleaned = clean_text(text)
    occupied: list[tuple[int, int]] = []
    hits: list[dict] = []
    for _, pat, tid, kind, token in compiled:                 # already longest-first
        for m in pat.finditer(cleaned):
            s, e = m.start(), m.end()
            if any(not (e <= os or s >= oe) for os, oe in occupied):
                continue                                      # inside an accepted longer span
            occupied.append((s, e))
            hits.append({"pos": s, "team_id": tid, "kind": kind,
                         "token": token, "matched": m.group(0)})
    hits.sort(key=lambda h: h["pos"])
    return hits


def extract_team_mentions(raw_response_text, compiled) -> list[str]:
    """Ordered list of team_ids by first position in the response text."""
    order: list[str] = []
    for h in find_mentions(raw_response_text, compiled):
        if h["team_id"] not in order:
            order.append(h["team_id"])
    return order


def attribution_only_mentions(raw_response_text, compiled) -> list[str]:
    """team_ids referenced ONLY via ballpark/owner (never by name/alias)."""
    name_teams, attr_teams = set(), set()
    for h in find_mentions(raw_response_text, compiled):
        (name_teams if h["kind"] == "name" else attr_teams).add(h["team_id"])
    return [t for t in attr_teams if t not in name_teams]


def score_response(teams, attribution_only):
    """Apply the point rules to one response. Returns {team_id: points}.

    for position, team in enumerate(teams):
        pts = 5 if position == 0 else 3 if position == 1 else 1
        scored[team] = max(scored.get(team, 0), pts)
    for team in attribution_only:
        scored[team] = max(scored.get(team, 0), 1)
    """
    scored: dict[str, int] = {}
    for position, team in enumerate(teams):
        pts = 5 if position == 0 else 3 if position == 1 else 1
        scored[team] = max(scored.get(team, 0), pts)
    for team in attribution_only:
        scored[team] = max(scored.get(team, 0), 1)
    return scored


def score_one(text, compiled):
    """Score one response. Returns (scored, name_order, attr_only, attr_detail).

    Positional 5/3/1 applies to the order teams are NAMED (name/alias hits only);
    attribution-only teams (ballpark/owner, never named) score 1. Highest per team.
    """
    hits = find_mentions(text, compiled)
    name_order: list[str] = []
    for h in hits:
        if h["kind"] == "name" and h["team_id"] not in name_order:
            name_order.append(h["team_id"])
    named = set(name_order)
    attr_only: list[str] = []
    for h in hits:
        if h["kind"] == "attribution" and h["team_id"] not in named and h["team_id"] not in attr_only:
            attr_only.append(h["team_id"])
    scored = score_response(name_order, attr_only)
    attr_detail = [(h["team_id"], h["matched"]) for h in hits
                   if h["team_id"] in set(attr_only)]
    return scored, name_order, attr_only, attr_detail


CAPTURE_LOG = "data/capture_log.csv"
INDEX_CSV = "data/citation_index.csv"
AUDIT_CSV = "data/attribution_audit.csv"

# Engine display name -> short rank-column key (mirrors NFL schema).
ENGINE_KEYS = {
    "ChatGPT": "chatgpt", "Claude": "claude", "Gemini": "gemini",
    "Perplexity": "perplexity", "Google AI Overviews": "gaio",
}
# Category -> short rank-column key.
CATEGORY_KEYS = {
    "AI-First Fan": "ai_fan",
    "Fan Experience & Tickets": "experience",
    "Sponsorship & Brand Partnership": "sponsorship",
    "Audience & Reach": "audience",
    "Market Relevance & Competitive Standing": "market",
    "Brand Identity & Narrative": "brand",
    "Business & Franchise Strength": "business",
    "Talent & Org Reputation": "talent",
}


def aggregate(capture_log=CAPTURE_LOG, compiled=None):
    """Score every captured response; accumulate points overall, per category,
    per engine, plus first-place counts, appearances, and the attribution audit."""
    if compiled is None:
        compiled = build_matchers(load_reference())
    overall = {}
    by_cat = {}            # cat_key -> {team: pts}
    by_eng = {}            # eng_key -> {team: pts}
    first_place = {}       # team -> count of responses where named first
    appearances = {}       # team -> count of responses where it scored
    audit = []             # attribution-only credits, for review
    with open(capture_log, newline="") as f:
        for r in csv.DictReader(f):
            if str(r.get("captured", "")).strip().lower() not in {"true", "1", "yes"}:
                continue
            scored, name_order, attr_only, attr_detail = score_one(
                r["raw_response_text"], compiled)
            ck = CATEGORY_KEYS.get(r["category"])
            ek = ENGINE_KEYS.get(r["engine"])
            for team, pts in scored.items():
                overall[team] = overall.get(team, 0) + pts
                appearances[team] = appearances.get(team, 0) + 1
                by_cat.setdefault(ck, {})[team] = by_cat.setdefault(ck, {}).get(team, 0) + pts
                by_eng.setdefault(ek, {})[team] = by_eng.setdefault(ek, {}).get(team, 0) + pts
            if name_order:
                first_place[name_order[0]] = first_place.get(name_order[0], 0) + 1
            for team, matched in attr_detail:
                audit.append({"query_id": r["query_id"], "engine": r["engine"],
                              "category": r["category"], "team_id": team,
                              "match_type": "attribution", "matched_string": matched})
    return {"overall": overall, "by_cat": by_cat, "by_eng": by_eng,
            "first_place": first_place, "appearances": appearances, "audit": audit}


def normalize(team_totals):
    """Anchor the top team to 100.0; others = (raw / max raw) * 100 (1 decimal)."""
    top = max(team_totals.values()) if team_totals else 0
    if not top:
        return {t: 0.0 for t in team_totals}
    return {t: round(v / top * 100, 1) for t, v in team_totals.items()}


def _rank_map(points_by_team, all_teams):
    """1..N rank by points desc (tie-break team_id) over all_teams (0 allowed)."""
    ordered = sorted(all_teams, key=lambda t: (-points_by_team.get(t, 0), t))
    return {t: i + 1 for i, t in enumerate(ordered)}


def _tier(share):
    if share >= 50:
        return "I Dominant"
    if share >= 20:
        return "II Established"
    if share > 0:
        return "III Present"
    return "IV Dead Zone"


def build_index(agg, teams):
    """Build the ranked 1-30 index rows mirroring the NFL schema."""
    ref = {t["team_id"]: t for t in teams}
    all_ids = list(ref)
    overall = {t: agg["overall"].get(t, 0) for t in all_ids}
    shares = normalize(overall)
    cite_rank = _rank_map(overall, all_ids)
    cat_ranks = {ck: _rank_map(agg["by_cat"].get(ck, {}), all_ids) for ck in CATEGORY_KEYS.values()}
    eng_ranks = {ek: _rank_map(agg["by_eng"].get(ek, {}), all_ids) for ek in ENGINE_KEYS.values()}

    rows = []
    for tid in sorted(all_ids, key=lambda t: cite_rank[t]):
        r = ref[tid]
        sr = int(r["standing_2025_rank"]); vr = int(r["valuation_rank"])
        row = {
            "rank": cite_rank[tid], "team": r["full_name"], "team_id": tid,
            "citation_share": shares[tid], "total_points": overall[tid],
        }
        for ck in CATEGORY_KEYS.values():
            row[f"{ck}_rank"] = cat_ranks[ck][tid]
        for ek in ENGINE_KEYS.values():
            row[f"{ek}_rank"] = eng_ranks[ek][tid]
        row["first_place_count"] = agg["first_place"].get(tid, 0)
        row["appearances"] = agg["appearances"].get(tid, 0)
        row["standing_2025_rank"] = sr
        row["perf_gap"] = cite_rank[tid] - sr
        row["valuation_rank"] = vr
        row["val_gap"] = cite_rank[tid] - vr
        row["tier"] = _tier(shares[tid])
        rows.append(row)
    return rows


def main():
    teams = load_reference()
    compiled = build_matchers(teams)
    agg = aggregate(CAPTURE_LOG, compiled)
    rows = build_index(agg, teams)

    with open(INDEX_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader(); w.writerows(rows)
    with open(AUDIT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["query_id", "engine", "category",
                                          "team_id", "match_type", "matched_string"])
        w.writeheader(); w.writerows(agg["audit"])

    print(f"Wrote {INDEX_CSV} ({len(rows)} teams) and {AUDIT_CSV} "
          f"({len(agg['audit'])} attribution-only hits).")
    print()
    hdr = f"{'#':>2} {'team':22} {'share':>6} {'pts':>5} {'1st':>4} {'app':>4} {'stand':>5} {'pgap':>5} {'val':>4} {'vgap':>5}  tier"
    print(hdr); print("-" * len(hdr))
    for r in rows:
        print(f"{r['rank']:>2} {r['team']:22} {r['citation_share']:>6.1f} {r['total_points']:>5} "
              f"{r['first_place_count']:>4} {r['appearances']:>4} {r['standing_2025_rank']:>5} "
              f"{r['perf_gap']:>+5} {r['valuation_rank']:>4} {r['val_gap']:>+5}  {r['tier']}")


if __name__ == "__main__":
    main()
