"""Unit tests for the pure verdict computation (with per-case report)."""

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


def _case(report, *, name, purpose, findings, venue, sig, expected, conclusion):
    actual = compute_verdict(findings, venue, significance_score=sig) if sig is not None else compute_verdict(findings, venue)
    passed = actual == expected
    report.record(
        name=name,
        purpose=purpose,
        inputs={
            "severities": [f.severity.value for f in findings],
            "fixable": [f.fixable for f in findings],
            "venue": venue.value,
            "significance_score": sig,
        },
        expected=expected.value,
        actual=actual.value,
        passed=passed,
        conclusion=conclusion,
    )
    assert actual == expected


def test_any_fatal_rejects(report) -> None:
    _case(
        report,
        name="any fatal finding forces REJECT",
        purpose="Rule 1 of review_plan §1.9 — fatal dominates everything else.",
        findings=[_finding(Severity.FATAL), _finding(Severity.SERIOUS, fixable=True)],
        venue=Venue.RSS,
        sig=3,
        expected=Verdict.REJECT,
        conclusion="A fatal flaw is non-negotiable regardless of venue or significance.",
    )


def test_low_significance_rejects(report) -> None:
    _case(
        report,
        name="significance_score<=2 rejects even with no findings",
        purpose="Rule 2 — a low-significance problem can't be saved by a clean review.",
        findings=[],
        venue=Venue.RSS,
        sig=2,
        expected=Verdict.REJECT,
        conclusion="Significance is a hard floor — no one cares about a rigorous solution to a trivial problem.",
    )


def test_three_unresolvable_serious_rejects(report) -> None:
    _case(
        report,
        name="3 unresolvable serious → REJECT",
        purpose="Rule 3 — 3+ serious findings that can't be fixed make the paper non-salvageable.",
        findings=[_finding(Severity.SERIOUS, fixable=False) for _ in range(3)],
        venue=Venue.RSS,
        sig=3,
        expected=Verdict.REJECT,
        conclusion="Three structural problems is a rewrite, not a revision.",
    )


def test_zero_serious_accepts(report) -> None:
    _case(
        report,
        name="only minor findings → ACCEPT",
        purpose="Rule 4 — minor issues don't block acceptance.",
        findings=[_finding(Severity.MINOR), _finding(Severity.MINOR)],
        venue=Venue.RSS,
        sig=3,
        expected=Verdict.ACCEPT,
        conclusion="Minor issues are polish, not blockers.",
    )


def test_one_fixable_serious_weak_accept(report) -> None:
    _case(
        report,
        name="single fixable serious → WEAK_ACCEPT",
        purpose="Rule 5 — a single addressable serious finding converts to WEAK_ACCEPT.",
        findings=[_finding(Severity.SERIOUS, fixable=True)],
        venue=Venue.RSS,
        sig=3,
        expected=Verdict.WEAK_ACCEPT,
        conclusion="One tractable serious finding is a standard revision cycle.",
    )


def test_venue_calibration_ijrr_rejects_two_serious(report) -> None:
    _case(
        report,
        name="2 fixable serious at IJRR → REJECT",
        purpose="Rule 6 (top-tier) — IJRR/T-RO don't tolerate 2+ serious findings.",
        findings=[_finding(Severity.SERIOUS), _finding(Severity.SERIOUS)],
        venue=Venue.IJRR,
        sig=3,
        expected=Verdict.REJECT,
        conclusion="Top-tier venues are strict — two serious findings is rejection even if fixable.",
    )


def test_venue_calibration_icra_weak_reject_two_serious(report) -> None:
    _case(
        report,
        name="2 fixable serious at ICRA → WEAK_REJECT",
        purpose="Rule 6 (mid-tier) — ICRA/IROS/RA-L rate 2+ serious findings as weak reject.",
        findings=[_finding(Severity.SERIOUS), _finding(Severity.SERIOUS)],
        venue=Venue.ICRA,
        sig=3,
        expected=Verdict.WEAK_REJECT,
        conclusion="Mid-tier venues recognise that serious findings warrant revision, not outright rejection.",
    )


def test_venue_calibration_rss_weak_accept_two_fixable(report) -> None:
    _case(
        report,
        name="2 fixable serious at RSS → WEAK_ACCEPT",
        purpose="Rule 6 (selective) — RSS/CoRL accept all-fixable borderline papers.",
        findings=[_finding(Severity.SERIOUS), _finding(Severity.SERIOUS)],
        venue=Venue.RSS,
        sig=3,
        expected=Verdict.WEAK_ACCEPT,
        conclusion="Selective venues reward addressable work even when the issue count is borderline.",
    )


def test_four_fixable_serious_weak_reject(report) -> None:
    _case(
        report,
        name="4 fixable serious → WEAK_REJECT",
        purpose="Tail rule — 4+ serious findings at any venue are WEAK_REJECT (not ACCEPT, not outright REJECT).",
        findings=[_finding(Severity.SERIOUS) for _ in range(4)],
        venue=Venue.RSS,
        sig=3,
        expected=Verdict.WEAK_REJECT,
        conclusion="4 serious items is too much to land, even if individually fixable.",
    )


def test_empty_findings_accept(report) -> None:
    _case(
        report,
        name="empty findings list → ACCEPT",
        purpose="Zero findings + sane significance should always be ACCEPT.",
        findings=[],
        venue=Venue.IJRR,
        sig=5,
        expected=Verdict.ACCEPT,
        conclusion="A clean review is an acceptable review, full stop.",
    )
