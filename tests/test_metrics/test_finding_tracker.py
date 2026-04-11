"""Unit tests for ``alpha_research.metrics.finding_tracker.FindingTracker``.

Each case writes a row to ``tests/reports/test_finding_tracker.md``.
"""

from __future__ import annotations

from alpha_research.metrics.finding_tracker import FindingTracker
from alpha_research.models.research import TaskChain
from alpha_research.models.review import (
    Finding,
    FindingResponse,
    Review,
    RevisionResponse,
    Severity,
    Verdict,
)


def _finding(fid: str, sev: Severity) -> Finding:
    return Finding(
        id=fid,
        severity=sev,
        attack_vector="baseline",
        what_is_wrong="w",
        why_it_matters="w",
        what_would_fix="w",
        falsification="w",
        grounding="w",
        fixable=True,
    )


def _review(findings: list[Finding], iteration: int = 1) -> Review:
    serious = [f for f in findings if f.severity == Severity.SERIOUS]
    fatal = [f for f in findings if f.severity == Severity.FATAL]
    minors = [f for f in findings if f.severity == Severity.MINOR]
    return Review(
        version=1,
        iteration=iteration,
        summary="s",
        chain_extraction=TaskChain(),
        steel_man="a. b. c.",
        fatal_flaws=fatal,
        serious_weaknesses=serious,
        minor_issues=minors,
        verdict=Verdict.WEAK_REJECT,
        confidence=3,
    )


def test_addressed_finding_summary(report) -> None:
    tracker = FindingTracker()
    r1 = _review([_finding("f1", Severity.SERIOUS)])
    response = RevisionResponse(
        review_version=1,
        addressed=[FindingResponse(finding_id="f1", action_taken="added baseline", evidence="Table 2")],
    )
    tracker.track(r1, response)

    summary = tracker.get_summary()
    passed = summary == {"f1": "addressed"}
    report.record(
        name="addressed finding reported as addressed",
        purpose="track() + get_summary() classifies a finding with a FindingResponse as addressed.",
        inputs={"finding_id": "f1", "response": "addressed"},
        expected={"f1": "addressed"},
        actual=summary,
        passed=passed,
        conclusion="The tracker faithfully propagates per-finding response actions to its summary.",
    )
    assert passed


def test_persistent_finding_across_iterations(report) -> None:
    tracker = FindingTracker()
    r1 = _review([_finding("f1", Severity.SERIOUS)], iteration=1)
    r2 = _review([_finding("f1", Severity.SERIOUS)], iteration=2)
    tracker.track(r1, None)
    tracker.track(r2, None)

    summary = tracker.get_summary()
    passed = summary == {"f1": "persistent"}
    report.record(
        name="finding that reappears without response is persistent",
        purpose="A finding seen in iterations 1 AND 2 with no response should be 'persistent'.",
        inputs={"iterations": 2, "finding_id": "f1", "response": None},
        expected={"f1": "persistent"},
        actual=summary,
        passed=passed,
        conclusion="Persistent findings are the signal that triggers a backward transition or human review.",
    )
    assert passed


def test_monotonic_severity_catches_unjustified_downgrade(report) -> None:
    tracker = FindingTracker()
    prev = _review([_finding("f1", Severity.SERIOUS)], iteration=1)
    curr = _review([_finding("f1", Severity.MINOR)], iteration=2)
    tracker.track(prev, None)
    tracker.track(curr, None)

    downgrades = tracker.check_monotonic_severity(curr, prev)
    passed = downgrades == ["f1"]
    report.record(
        name="unaddressed serious→minor downgrade is flagged",
        purpose="check_monotonic_severity returns finding ids whose severity dropped without a FindingResponse.",
        inputs={"prev_severity": "serious", "curr_severity": "minor", "addressed": False},
        expected={"downgraded": ["f1"]},
        actual={"downgraded": downgrades},
        passed=passed,
        conclusion=(
            "Severity regression is the anti-collapse tripwire — without it, the "
            "review loop can quietly soften criticisms instead of resolving them."
        ),
    )
    assert passed


def test_resolution_history_for_multi_iteration(report) -> None:
    tracker = FindingTracker()
    r1 = _review([_finding("f1", Severity.SERIOUS), _finding("f2", Severity.SERIOUS)])
    resp1 = RevisionResponse(
        review_version=1,
        addressed=[FindingResponse(finding_id="f1", action_taken="ok", evidence="Sec 1")],
    )
    r2 = _review([_finding("f2", Severity.SERIOUS)], iteration=2)
    resp2 = RevisionResponse(
        review_version=2,
        addressed=[FindingResponse(finding_id="f2", action_taken="ok", evidence="Sec 2")],
    )
    tracker.track(r1, resp1)
    tracker.track(r2, resp2)

    history = tracker.get_resolution_history()
    passed = history == [0.5, 1.0]
    report.record(
        name="resolution history reports per-iteration rates",
        purpose="get_resolution_history() walks tracked iterations and returns each response's addressed-fraction.",
        inputs={
            "iter_1": {"findings": 2, "addressed": 1},
            "iter_2": {"findings": 1, "addressed": 1},
        },
        expected=[0.5, 1.0],
        actual=history,
        passed=passed,
        conclusion="Resolution rate should increase as the researcher addresses the backlog — this is the convergence proxy.",
    )
    assert passed
