"""Generate the 30 per-team one-pagers — the outreach asset.

Each one-pager (spec §9.2) contains:
    - team name + Citation Share Score + overall rank
    - rank in each of the 4 buckets (Fan / Sponsor / Free-Agent / Business)
    - Performance Gap and Value Gap in plain language
    - 2-3 representative prompts where the team was absent but a rival was named first
    - one sentence on the commercial implication
    - a single forward CTA

Build one template, generate x30.

STUB ONLY.
"""

from __future__ import annotations


def render_one_pager(team_id, index_row, scored_dataset):
    """Render a single team's one-pager from the index row + scored detail.

    TODO: implement template rendering.
    """
    raise NotImplementedError


def generate_all(index, scored_dataset):
    """Generate one-pagers for all 30 teams.

    TODO: loop teams, render, write out.
    """
    raise NotImplementedError("one_pagers is a scaffold — not implemented yet.")
