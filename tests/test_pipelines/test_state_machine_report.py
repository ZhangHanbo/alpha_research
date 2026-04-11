"""Report-emitting tests for ``alpha_research.pipelines.state_machine``.

Writes ``tests/reports/test_state_machine_report.md``. The existing
``test_state_machine.py`` exhaustively asserts the transition tables;
this file picks the 10 most informative cases and routes them through
the ``report`` fixture.
"""

from __future__ import annotations

from alpha_research.models.blackboard import ResearchArtifact, ResearchStage
from alpha_research.models.research import TaskChain
from alpha_research.models.review import Finding, Severity
from alpha_research.pipelines.state_machine import (
    BACKWARD_TRANSITIONS,
    FORWARD_TRANSITIONS,
    backward_trigger_from_finding,
    stage_guard_satisfied,
    valid_transitions,
)


def _artifact(stage: ResearchStage, content: str = "", chain: TaskChain | None = None, metadata: dict | None = None) -> ResearchArtifact:
    return ResearchArtifact(
        stage=stage,
        content=content,
        task_chain=chain or TaskChain(),
        metadata=metadata or {},
    )


def _finding(severity: Severity = Severity.SERIOUS, attack_vector: str = "", maps_to_trigger: str | None = None) -> Finding:
    return Finding(
        severity=severity,
        attack_vector=attack_vector,
        what_is_wrong="w",
        why_it_matters="w",
        what_would_fix="w",
        falsification="w",
        grounding="w",
        fixable=True,
        maps_to_trigger=maps_to_trigger,
    )


def test_forward_chain_covers_all_main_stages(report) -> None:
    # significance → formalization → diagnose → challenge → approach → validate → full_draft
    chain = [
        "significance", "formalization", "diagnose",
        "challenge", "approach", "validate", "full_draft",
    ]
    expected = {chain[i]: [chain[i + 1]] for i in range(len(chain) - 1)}
    expected["full_draft"] = []
    passed = FORWARD_TRANSITIONS == expected
    report.record(
        name="forward transition table is linear",
        purpose="Every non-terminal stage has exactly one successor; full_draft is terminal.",
        inputs={},
        expected=expected,
        actual=FORWARD_TRANSITIONS,
        passed=passed,
        conclusion="A linear forward chain keeps the state machine interpretable and uniquely testable.",
    )
    assert passed


def test_backward_transitions_have_trigger_keys(report) -> None:
    # All backward keys are t2, t4, .. t15
    all_triggers = sorted({t for tr in BACKWARD_TRANSITIONS.values() for t in tr})
    passed = all(t.startswith("t") for t in all_triggers) and len(all_triggers) >= 12
    report.record(
        name="backward triggers are t2..t15 style",
        purpose="BACKWARD_TRANSITIONS should enumerate at least 12 t* triggers.",
        inputs={},
        expected={"count >= 12": True, "all_t_prefixed": True},
        actual={"triggers": all_triggers, "count": len(all_triggers)},
        passed=passed,
        conclusion="Backward triggers anchor the research_plan §2.4 regression matrix.",
    )
    assert passed


def test_valid_transitions_includes_backward_targets(report) -> None:
    targets = [s.value for s in valid_transitions(ResearchStage.VALIDATE)]
    passed = "full_draft" in targets and "significance" in targets and "diagnose" in targets
    report.record(
        name="valid_transitions(validate) includes forward + backward targets",
        purpose="From validate, the machine can advance to full_draft or regress to several earlier stages.",
        inputs={"stage": "validate"},
        expected={"contains": ["full_draft", "significance", "diagnose"]},
        actual={"targets": targets},
        passed=passed,
        conclusion="The transition surface for the validate stage is the most connected node in the graph.",
    )
    assert passed


def test_g1_satisfied_by_metadata_signal(report) -> None:
    a = _artifact(ResearchStage.SIGNIFICANCE, metadata={"significance": 4})
    passed = stage_guard_satisfied(ResearchStage.SIGNIFICANCE, a) is True
    report.record(
        name="g1 passes when metadata has a significance key",
        purpose="An explicit significance signal in metadata should unlock the SIGNIFICANCE → FORMALIZATION transition.",
        inputs={"metadata": {"significance": 4}},
        expected={"g1": True},
        actual={"g1": passed},
        passed=passed,
        conclusion="Metadata is the cleanest signal; content-level heuristics are a fallback.",
    )
    assert passed


def test_g2_satisfied_by_formal_problem_text(report) -> None:
    a = _artifact(
        ResearchStage.FORMALIZATION,
        content="We define a formal problem: $x \\in \\mathcal{X}$ with argmin over L(x).",
    )
    passed = stage_guard_satisfied(ResearchStage.FORMALIZATION, a) is True
    report.record(
        name="g2 passes on explicit formal math content",
        purpose="'formal problem', 'argmin', and '\\mathcal' markers unlock FORMALIZATION → DIAGNOSE.",
        inputs={"content_excerpt": "formal problem ... argmin ... \\mathcal"},
        expected={"g2": True},
        actual={"g2": passed},
        passed=passed,
        conclusion="Math notation serves as a proxy for 'the problem is actually formalized'.",
    )
    assert passed


def test_g3_fails_without_failure_mode(report) -> None:
    a = _artifact(ResearchStage.DIAGNOSE, content="We did some experiments.")
    passed = stage_guard_satisfied(ResearchStage.DIAGNOSE, a) is False
    report.record(
        name="g3 blocks diagnose when no failure is identified",
        purpose="Without 'failure mode', 'fails when', 'diagnosed', the DIAGNOSE stage is not complete.",
        inputs={"content": "We did some experiments."},
        expected={"g3": False},
        actual={"g3": passed is False if False else not passed},
        passed=passed,
        conclusion="Gate prevents the researcher from claiming diagnosis without naming the failure.",
    )
    assert passed


def test_trigger_inference_from_attack_vector(report) -> None:
    f = _finding(attack_vector="Concurrent work already solved this (Smith 2024)")
    trig = backward_trigger_from_finding(f)
    passed = trig == "t9"
    report.record(
        name="'concurrent work' attack vector → t9",
        purpose="backward_trigger_from_finding pattern-matches keywords in attack_vector.",
        inputs={"attack_vector": "Concurrent work already solved this (Smith 2024)"},
        expected="t9",
        actual=trig,
        passed=passed,
        conclusion="t9 correctly regresses the loop from validate to significance when novelty evaporates.",
    )
    assert passed


def test_trigger_inference_hamming(report) -> None:
    f = _finding(attack_vector="Incremental contribution — fails the Hamming test")
    trig = backward_trigger_from_finding(f)
    passed = trig == "t13"
    report.record(
        name="'hamming' / 'incremental' → t13",
        purpose="Hamming/incremental-contribution language should map to the t13 regression trigger.",
        inputs={"attack_vector": "Incremental contribution — fails the Hamming test"},
        expected="t13",
        actual=trig,
        passed=passed,
        conclusion="t13 is the canonical hamming-fail backward step per research_plan §2.4.",
    )
    assert passed


def test_explicit_maps_to_trigger_wins(report) -> None:
    f = _finding(attack_vector="concurrent work", maps_to_trigger="t14")
    trig = backward_trigger_from_finding(f)
    passed = trig == "t14"
    report.record(
        name="explicit maps_to_trigger overrides keyword inference",
        purpose="When the reviewer tags a finding with a specific trigger, it should win.",
        inputs={"maps_to_trigger": "t14", "attack_vector_keyword": "concurrent work"},
        expected="t14",
        actual=trig,
        passed=passed,
        conclusion="Explicit annotation is respected over heuristic fallback — correctly.",
    )
    assert passed


def test_minor_finding_has_no_trigger(report) -> None:
    f = _finding(severity=Severity.MINOR, attack_vector="concurrent work")
    trig = backward_trigger_from_finding(f)
    passed = trig is None
    report.record(
        name="minor findings never produce backward triggers",
        purpose="Minor findings should return None regardless of attack_vector wording.",
        inputs={"severity": "minor", "attack_vector": "concurrent work"},
        expected=None,
        actual=trig,
        passed=passed,
        conclusion="Prevents minor polish issues from triggering costly regressions.",
    )
    assert passed
