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


def aggregate(raw_log, reference_table):
    """Sum points per team overall, and separately per category and per engine.

    Returns the running totals needed for the index and the one-pager category cuts.
    TODO: load raw_log, run extract/score per row, accumulate.
    """
    raise NotImplementedError


def normalize(team_totals):
    """Anchor the top team to 100.0; others = (raw / max raw) * 100.

    TODO: implement once aggregation returns real totals.
    """
    raise NotImplementedError


CAPTURE_LOG = "data/capture_log.csv"


def main():
    # TODO: load data/capture_log.csv + reference/teams.csv, aggregate, normalize,
    # and write a scored dataset for generate/ to consume.
    raise NotImplementedError("score.py is a scaffold — scoring not implemented yet.")


if __name__ == "__main__":
    main()
