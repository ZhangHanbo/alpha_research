"""Exhaustive tests for the pure state-machine pipeline."""

from __future__ import annotations

import pytest

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _artifact(
    stage: ResearchStage = ResearchStage.SIGNIFICANCE,
    content: str = "",
    chain: TaskChain | None = None,
    metadata: dict | None = None,
) -> ResearchArtifact:
    return ResearchArtifact(
        stage=stage,
        content=content,
        task_chain=chain or TaskChain(),
        metadata=metadata or {},
    )


def _finding(
    severity: Severity = Severity.SERIOUS,
    attack_vector: str = "",
    maps_to_trigger: str | None = None,
) -> Finding:
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


# ---------------------------------------------------------------------------
# Transition table tests
# ---------------------------------------------------------------------------

def test_forward_transitions_cover_all_main_stages():
    # significance → formalization → diagnose → challenge → approach → validate → full_draft
    expected = [
        ("significance", "formalization"),
        ("formalization", "diagnose"),
        ("diagnose", "challenge"),
        ("challenge", "approach"),
        ("approach", "validate"),
        ("validate", "full_draft"),
    ]
    for src, tgt in expected:
        assert FORWARD_TRANSITIONS[src] == [tgt]


def test_full_draft_is_terminal():
    assert FORWARD_TRANSITIONS["full_draft"] == []


def test_backward_transitions_structure():
    # formalization can only go back to significance via t2
    assert BACKWARD_TRANSITIONS["formalization"] == {"t2": "significance"}
    # approach has 5 backward targets
    assert set(BACKWARD_TRANSITIONS["approach"].keys()) == {
        "t5", "t8", "t10", "t11", "t12",
    }


def test_valid_transitions_significance():
    assert valid_transitions(ResearchStage.SIGNIFICANCE) == [
        ResearchStage.FORMALIZATION
    ]


def test_valid_transitions_formalization_includes_forward_and_backward():
    out = valid_transitions(ResearchStage.FORMALIZATION)
    assert ResearchStage.DIAGNOSE in out  # forward
    assert ResearchStage.SIGNIFICANCE in out  # backward via t2


def test_valid_transitions_approach_includes_all_backward_targets():
    out = valid_transitions(ResearchStage.APPROACH)
    # Forward target first
    assert out[0] == ResearchStage.VALIDATE
    # All backward targets present
    for target in ("significance", "diagnose", "formalization", "challenge"):
        assert ResearchStage(target) in out


def test_valid_transitions_validate():
    out = valid_transitions(ResearchStage.VALIDATE)
    assert ResearchStage.FULL_DRAFT in out
    assert ResearchStage.SIGNIFICANCE in out
    assert ResearchStage.FORMALIZATION in out
    assert ResearchStage.DIAGNOSE in out


def test_valid_transitions_full_draft_is_empty():
    assert valid_transitions(ResearchStage.FULL_DRAFT) == []


def test_valid_transitions_accepts_str_argument():
    # Callers that persist stage as a raw string should still work.
    assert valid_transitions("significance") == [ResearchStage.FORMALIZATION]


def test_valid_transitions_dedupes():
    # approach has t8 and t11 both pointing to diagnose; the result should
    # contain DIAGNOSE exactly once.
    out = valid_transitions(ResearchStage.APPROACH)
    assert out.count(ResearchStage.DIAGNOSE) == 1


# ---------------------------------------------------------------------------
# Forward guard tests
# ---------------------------------------------------------------------------

def test_g1_significance_guard_passes_with_keyword():
    art = _artifact(content="This section evaluates the significance and impact.")
    assert stage_guard_satisfied(ResearchStage.SIGNIFICANCE, art)


def test_g1_significance_guard_passes_with_metadata():
    art = _artifact(metadata={"significance": "high"})
    assert stage_guard_satisfied(ResearchStage.SIGNIFICANCE, art)


def test_g1_significance_guard_fails_on_empty():
    art = _artifact(content="")
    assert not stage_guard_satisfied(ResearchStage.SIGNIFICANCE, art)


def test_g2_formalization_guard_passes_with_task_chain_problem():
    chain = TaskChain(problem="min_x f(x) subject to g(x) <= 0")
    art = _artifact(stage=ResearchStage.FORMALIZATION, chain=chain)
    assert stage_guard_satisfied(ResearchStage.FORMALIZATION, art)


def test_g2_formalization_guard_passes_with_math_marker():
    art = _artifact(
        stage=ResearchStage.FORMALIZATION,
        content="We define the formal problem as argmin over the constraint set.",
    )
    assert stage_guard_satisfied(ResearchStage.FORMALIZATION, art)


def test_g2_formalization_guard_fails_without_problem():
    art = _artifact(stage=ResearchStage.FORMALIZATION, content="some prose")
    assert not stage_guard_satisfied(ResearchStage.FORMALIZATION, art)


def test_g3_diagnose_guard_passes_with_failure_language():
    art = _artifact(
        stage=ResearchStage.DIAGNOSE,
        content="The system fails when the object is occluded (failure mode A).",
    )
    assert stage_guard_satisfied(ResearchStage.DIAGNOSE, art)


def test_g3_diagnose_guard_fails_without_failure_info():
    art = _artifact(stage=ResearchStage.DIAGNOSE, content="nothing specific")
    assert not stage_guard_satisfied(ResearchStage.DIAGNOSE, art)


def test_g4_challenge_guard_passes_with_chain_and_approach():
    chain = TaskChain(challenge="occlusion handling", approach="learned pose prior")
    art = _artifact(stage=ResearchStage.CHALLENGE, chain=chain)
    assert stage_guard_satisfied(ResearchStage.CHALLENGE, art)


def test_g4_challenge_guard_passes_with_text_cue():
    art = _artifact(
        stage=ResearchStage.CHALLENGE,
        content="The structural challenge constrains the solution class to ...",
    )
    assert stage_guard_satisfied(ResearchStage.CHALLENGE, art)


def test_g5_approach_guard_passes_with_one_sentence():
    chain = TaskChain(approach="diffusion policy", one_sentence="key insight: X")
    art = _artifact(stage=ResearchStage.APPROACH, chain=chain)
    assert stage_guard_satisfied(ResearchStage.APPROACH, art)


def test_g5_approach_guard_fails_without_contribution():
    art = _artifact(stage=ResearchStage.APPROACH, content="we solve stuff")
    assert not stage_guard_satisfied(ResearchStage.APPROACH, art)


def test_guard_full_draft_returns_false():
    art = _artifact(stage=ResearchStage.FULL_DRAFT, content="done")
    assert not stage_guard_satisfied(ResearchStage.FULL_DRAFT, art)


def test_guard_validate_requires_approach_and_one_sentence():
    chain = TaskChain(approach="X", one_sentence="insight: Y")
    art = _artifact(stage=ResearchStage.VALIDATE, chain=chain)
    assert stage_guard_satisfied(ResearchStage.VALIDATE, art)


# ---------------------------------------------------------------------------
# Backward trigger mapping tests
# ---------------------------------------------------------------------------

def test_trigger_explicit_maps_to_trigger_field():
    f = _finding(maps_to_trigger="t12")
    assert backward_trigger_from_finding(f) == "t12"


def test_trigger_explicit_trumps_attack_vector():
    f = _finding(
        maps_to_trigger="t2",
        attack_vector="concurrent work",  # would otherwise map to t9
    )
    assert backward_trigger_from_finding(f) == "t2"


def test_trigger_concurrent_work_maps_to_t9():
    f = _finding(attack_vector="§3.1 concurrent work nullifies novelty")
    assert backward_trigger_from_finding(f) == "t9"


def test_trigger_hamming_maps_to_t13():
    f = _finding(attack_vector="Hamming test fails — incremental contribution only")
    assert backward_trigger_from_finding(f) == "t13"


def test_trigger_trivial_special_case_maps_to_t2():
    f = _finding(attack_vector="trivial special case of known problem")
    assert backward_trigger_from_finding(f) == "t2"


def test_trigger_wrong_framework_maps_to_t7():
    f = _finding(attack_vector="wrong mathematical framework")
    assert backward_trigger_from_finding(f) == "t7"


def test_trigger_formalization_reality_gap_maps_to_t10():
    f = _finding(attack_vector="formalization-reality gap in validation")
    assert backward_trigger_from_finding(f) == "t10"


def test_trigger_wrong_challenge_maps_to_t6():
    f = _finding(attack_vector="wrong challenge identified")
    assert backward_trigger_from_finding(f) == "t6"


def test_trigger_pre_solved_maps_to_t12():
    f = _finding(attack_vector="this challenge is pre-solved in prior work")
    assert backward_trigger_from_finding(f) == "t12"


def test_trigger_wrong_mechanism_maps_to_t15():
    f = _finding(attack_vector="wrong mechanism hypothesis")
    assert backward_trigger_from_finding(f) == "t15"


def test_trigger_theoretical_justification_gap_maps_to_t14():
    f = _finding(attack_vector="theoretical justification gap")
    assert backward_trigger_from_finding(f) == "t14"


def test_trigger_unknown_attack_vector_returns_none():
    f = _finding(attack_vector="completely unrelated bug")
    assert backward_trigger_from_finding(f) is None


def test_trigger_minor_severity_always_returns_none():
    f = _finding(severity=Severity.MINOR, attack_vector="concurrent work")
    assert backward_trigger_from_finding(f) is None


def test_trigger_fatal_severity_still_maps():
    f = _finding(severity=Severity.FATAL, attack_vector="concurrent work")
    assert backward_trigger_from_finding(f) == "t9"


def test_trigger_invalid_explicit_falls_back_to_inference():
    f = _finding(maps_to_trigger="t999", attack_vector="wrong challenge")
    # 't999' is not in known triggers, so it should fall through to
    # attack_vector inference.
    assert backward_trigger_from_finding(f) == "t6"


@pytest.mark.parametrize(
    "stage",
    [ResearchStage.SIGNIFICANCE, ResearchStage.FORMALIZATION,
     ResearchStage.DIAGNOSE, ResearchStage.CHALLENGE,
     ResearchStage.APPROACH, ResearchStage.VALIDATE],
)
def test_every_non_terminal_stage_has_forward_edge(stage):
    assert FORWARD_TRANSITIONS[stage.value]
