"""Pure verdict computation (review_plan.md §1.9).

Extracted from ``agents/review_agent.py::compute_verdict`` so that skills
and pipelines can compute mechanical verdicts without instantiating the
full agent class. This module has no LLM or I/O dependencies.
"""

from __future__ import annotations

from alpha_research.models.blackboard import Venue
from alpha_research.models.review import Finding, Severity, Verdict


def compute_verdict(
    findings: list[Finding],
    venue: Venue = Venue.RSS,
    significance_score: int = 3,
) -> Verdict:
    """Mechanically compute a verdict from a list of findings.

    Rules (review_plan.md §1.9):

    1. Any fatal finding                                 -> REJECT
    2. ``significance_score <= 2``                       -> REJECT
    3. 3+ unresolvable (not fixable) serious findings    -> REJECT
    4. 0 serious findings                                -> ACCEPT
    5. <=1 serious finding, all fixable                  -> WEAK_ACCEPT
    6. Otherwise — venue-calibrated borderline:
       - 2-3 serious at top-tier venues (IJRR, T-RO)     -> REJECT
       - 2-3 serious at mid-tier venues (ICRA, IROS,
         RA-L)                                           -> WEAK_REJECT
       - 2-3 serious at selective-but-not-top (RSS,
         CoRL): WEAK_ACCEPT if all fixable else
         WEAK_REJECT
       - 3+ serious at any other venue                   -> WEAK_REJECT
    """
    fatals = [f for f in findings if f.severity == Severity.FATAL]
    serious = [f for f in findings if f.severity == Severity.SERIOUS]

    # Rule 1: any fatal -> REJECT
    if fatals:
        return Verdict.REJECT

    # Rule 2: significance too low -> REJECT
    if significance_score is not None and significance_score <= 2:
        return Verdict.REJECT

    serious_count = len(serious)
    unresolvable = [f for f in serious if not f.fixable]

    # Rule 3: 3+ unresolvable serious -> REJECT
    if len(unresolvable) >= 3:
        return Verdict.REJECT

    # Rule 4: 0 serious -> ACCEPT
    if serious_count == 0:
        return Verdict.ACCEPT

    # Rule 5: <=1 fixable serious -> WEAK_ACCEPT
    if serious_count <= 1 and all(f.fixable for f in serious):
        return Verdict.WEAK_ACCEPT

    # Rule 6: venue-calibrated borderline (2+ serious)
    top_tier = {Venue.IJRR, Venue.T_RO}
    mid_tier = {Venue.ICRA, Venue.IROS, Venue.RA_L}

    if 2 <= serious_count <= 3:
        if venue in top_tier:
            return Verdict.REJECT
        if venue in mid_tier:
            return Verdict.WEAK_REJECT
        # RSS, CoRL and any other selective venue:
        if all(f.fixable for f in serious):
            return Verdict.WEAK_ACCEPT
        return Verdict.WEAK_REJECT

    # 4+ serious at any venue -> WEAK_REJECT (fatal was already handled)
    return Verdict.WEAK_REJECT
