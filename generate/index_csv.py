"""Emit the ranked Index CSV — the master table.

Columns (mirrors the 5W NFL reference, spec §9.1):
    Rank, Team, Citation Share, Fan, Sponsor, Free-Agent, Business,
    On-Field rank, Perf Gap, Forbes rank, Val Gap, Tier

Gaps (CLAUDE.md §Cross-reference layers):
    Perf Gap = Citation Share rank - on-field rank
    Val Gap  = Citation Share rank - Forbes valuation rank

Tiers (CLAUDE.md §Tiers):
    I Dominant 50+ | II Established 20-49 | III Present 1-19 | IV Dead Zone 0.0

STUB ONLY.
"""

from __future__ import annotations


def assign_tier(citation_share: float) -> str:
    """Map a normalized 0-100 Citation Share to a tier label."""
    if citation_share >= 50:
        return "I · Dominant"
    if citation_share >= 20:
        return "II · Established"
    if citation_share >= 1:
        return "III · Present"
    return "IV · Dead Zone"


def build_index(scored_dataset, reference_table):
    """Join scores to cross-reference data, rank, compute gaps, assign tiers.

    TODO: implement and write the index CSV.
    """
    raise NotImplementedError("index_csv is a scaffold — not implemented yet.")
