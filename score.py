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

# import pandas as pd  # enable when implementing


def extract_team_mentions(raw_response_text, reference_table):
    """Return an ordered list of team_ids by position in the response text.

    Uses full names + aliases + ballpark/owner strings from reference/teams.csv.
    TODO: implement curated alias string matching.
    """
    raise NotImplementedError


def attribution_only_mentions(raw_response_text, reference_table):
    """Return team_ids referenced solely via ballpark/owner/logo (no team name).

    TODO: implement.
    """
    raise NotImplementedError


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
