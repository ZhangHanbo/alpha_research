"""Unit tests for the pure verdict computation."""

from __future__ import annotations

from alpha_research.metrics.verdict import compute_verdict
from alpha_research.models.blackboard import Venue
from alpha_research.models.review import Finding, Severity, Verdict


def _finding(severity: Severity, fixable: bool = True) -> Finding:
    return Finding(
        severity=severity,
        attack_vector="test",
        what_is_wrong="w",
        why_it_matters="w",
        what_would_fix="w",
        falsification="w",
        grounding="w",
        fixable=fixable,
    )


def test_any_fatal_rejects() -> None:
    findings = [
        _finding(Severity.FATAL),
        _finding(Severity.SERIOUS, fixable=True),
    ]
    assert compute_verdict(findings, Venue.RSS) == Verdict.REJECT


def test_low_significance_rejects() -> None:
    assert compute_verdict([], Venue.RSS, significance_score=2) == Verdict.REJECT
    assert compute_verdict([], Venue.RSS, significance_score=1) == Verdict.REJECT


def test_three_unresolvable_serious_rejects() -> None:
    findings = [
        _finding(Severity.SERIOUS, fixable=False),
        _finding(Severity.SERIOUS, fixable=False),
        _finding(Severity.SERIOUS, fixable=False),
    ]
    assert compute_verdict(findings, Venue.RSS) == Verdict.REJECT


def test_zero_serious_accepts() -> None:
    findings = [_finding(Severity.MINOR), _finding(Severity.MINOR)]
    assert compute_verdict(findings, Venue.RSS) == Verdict.ACCEPT


def test_one_fixable_serious_weak_accept() -> None:
    findings = [_finding(Severity.SERIOUS, fixable=True)]
    assert compute_verdict(findings, Venue.RSS) == Verdict.WEAK_ACCEPT


def test_venue_calibration_ijrr_vs_icra() -> None:
    findings = [
        _finding(Severity.SERIOUS, fixable=True),
        _finding(Severity.SERIOUS, fixable=True),
    ]
    # Top-tier venue: 2 serious -> REJECT
    assert compute_verdict(findings, Venue.IJRR) == Verdict.REJECT
    # Mid-tier venue: 2 serious -> WEAK_REJECT
    assert compute_verdict(findings, Venue.ICRA) == Verdict.WEAK_REJECT
    # RSS (selective-but-not-top), all fixable -> WEAK_ACCEPT
    assert compute_verdict(findings, Venue.RSS) == Verdict.WEAK_ACCEPT


def test_empty_findings_accept() -> None:
    assert compute_verdict([], Venue.RSS) == Verdict.ACCEPT
    assert compute_verdict([], Venue.IJRR, significance_score=5) == Verdict.ACCEPT


def test_two_serious_rss_not_all_fixable() -> None:
    findings = [
        _finding(Severity.SERIOUS, fixable=True),
        _finding(Severity.SERIOUS, fixable=False),
    ]
    assert compute_verdict(findings, Venue.RSS) == Verdict.WEAK_REJECT


def test_four_fixable_serious_at_rss_weak_reject() -> None:
    findings = [_finding(Severity.SERIOUS, fixable=True) for _ in range(4)]
    # Not 3+ unresolvable, not 0 serious, not <=1 fixable, falls into rule 6/tail
    result = compute_verdict(findings, Venue.RSS)
    assert result == Verdict.WEAK_REJECT
