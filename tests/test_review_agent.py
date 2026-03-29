"""Tests for the ReviewAgent.

Covers:
  - Construction for different venues
  - Prompt building (venue variation, iteration/graduated pressure)
  - Response parsing from mock JSON
  - Verdict computation (pure logic)
  - Chain extraction from sample text
  - Re-review mode (previous findings included)
"""

from __future__ import annotations

import json

import pytest

from alpha_research.agents.review_agent import ReviewAgent
from alpha_research.models.blackboard import ResearchArtifact, ResearchStage
from alpha_research.models.research import TaskChain
from alpha_research.models.review import Finding, Review, Severity, Verdict


# =====================================================================
# Fixtures
# =====================================================================

@pytest.fixture
def agent_rss() -> ReviewAgent:
    return ReviewAgent(venue="RSS")


@pytest.fixture
def agent_ijrr() -> ReviewAgent:
    return ReviewAgent(venue="IJRR")


@pytest.fixture
def agent_icra() -> ReviewAgent:
    return ReviewAgent(venue="ICRA")


@pytest.fixture
def sample_artifact() -> ResearchArtifact:
    return ResearchArtifact(
        stage=ResearchStage.FULL_DRAFT,
        content=(
            "# Mobile Manipulation for Kitchen Tasks\n\n"
            "**Task:** Enable a mobile manipulator to clear a dining table.\n\n"
            "**Problem:** Given a cluttered table with N objects of unknown geometry, "
            "plan a sequence of pick-and-place actions that clears the table in "
            "minimum time while avoiding collisions.\n\n"
            "**Challenge:** The combinatorial explosion of grasp-transport sequences "
            "grows factorially with N, and each grasp must account for object geometry "
            "uncertainty from partial point clouds.\n\n"
            "**Approach:** We decompose the problem into a task-level sequencer "
            "(solved via constraint-based scheduling) and a grasp planner (solved via "
            "learned shape completion), connected by a shared geometric representation.\n\n"
            "**Contribution:** A decomposition that reduces factorial complexity to "
            "polynomial by exploiting the independence structure between scheduling "
            "and geometric uncertainty.\n"
        ),
        version=1,
    )


def _make_finding(
    severity: Severity,
    fixable: bool = True,
    fid: str = "",
) -> Finding:
    """Helper: create a minimal valid Finding."""
    return Finding(
        id=fid or f"{severity.value}-test",
        severity=severity,
        attack_vector="hamming_failure",
        what_is_wrong="Test issue",
        why_it_matters="Test consequence",
        what_would_fix="Test fix",
        falsification="Test falsification condition",
        grounding="Section 3",
        fixable=fixable,
    )


def _make_review_json(
    *,
    fatal: int = 0,
    serious: int = 0,
    minor: int = 0,
    verdict: str = "accept",
) -> str:
    """Build a mock JSON response matching the Review schema."""
    def _findings(sev: str, count: int) -> list[dict]:
        return [
            {
                "id": f"{sev}-{i}",
                "severity": sev,
                "attack_vector": "hamming_failure",
                "what_is_wrong": f"Issue {i}",
                "why_it_matters": f"Consequence {i}",
                "what_would_fix": f"Fix {i}",
                "falsification": f"Falsification {i}",
                "grounding": f"Section {i}",
                "fixable": True,
                "maps_to_trigger": None,
            }
            for i in range(1, count + 1)
        ]

    data = {
        "version": 1,
        "iteration": 1,
        "summary": "The paper proposes a decomposition approach.",
        "chain_extraction": {
            "task": "Clear a dining table",
            "problem": "Plan pick-and-place sequence",
            "challenge": "Combinatorial explosion",
            "approach": "Decomposition into scheduling + grasp planning",
            "one_sentence": "Reduces factorial to polynomial complexity",
            "chain_complete": True,
            "chain_coherent": True,
        },
        "steel_man": (
            "The paper identifies a genuine structural barrier in mobile "
            "manipulation task planning. The proposed decomposition exploits "
            "independence structure that prior work overlooked. Even if the "
            "individual components are known, the insight is in the separation."
        ),
        "fatal_flaws": _findings("fatal", fatal),
        "serious_weaknesses": _findings("serious", serious),
        "minor_issues": _findings("minor", minor),
        "questions": [
            "How does performance scale with N?",
            "What happens with highly non-convex objects?",
            "Was the scheduling solver tested with real timing constraints?",
        ],
        "verdict": verdict,
        "confidence": 3,
        "verdict_justification": "The logical chain is complete.",
        "improvement_path": "Add real-robot experiments.",
    }
    return json.dumps(data, indent=2)


# =====================================================================
# Construction
# =====================================================================

class TestConstruction:
    def test_default_venue(self) -> None:
        agent = ReviewAgent()
        assert agent.venue == "RSS"

    def test_custom_venue(self) -> None:
        for venue in ("RSS", "IJRR", "ICRA", "CoRL", "IROS", "RA-L", "T-RO"):
            agent = ReviewAgent(venue=venue)
            assert agent.venue == venue


# =====================================================================
# Prompt building
# =====================================================================

class TestPromptBuilding:
    def test_prompt_contains_venue(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        prompt = agent_rss._build_prompt(sample_artifact, iteration=1)
        assert "RSS" in prompt

    def test_prompt_differs_by_venue(
        self, sample_artifact: ResearchArtifact
    ) -> None:
        prompt_rss = ReviewAgent("RSS")._build_prompt(sample_artifact, 1)
        prompt_ijrr = ReviewAgent("IJRR")._build_prompt(sample_artifact, 1)
        prompt_icra = ReviewAgent("ICRA")._build_prompt(sample_artifact, 1)
        # Each should mention its own venue calibration
        assert "IJRR" in prompt_ijrr
        assert "ICRA" in prompt_icra
        # IJRR demands formalization more strongly
        assert "HIGHEST standard" in prompt_ijrr
        assert "HIGHEST standard" not in prompt_icra

    def test_iteration_1_structural_scan(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        prompt = agent_rss._build_prompt(sample_artifact, iteration=1)
        assert "STRUCTURAL SCAN" in prompt

    def test_iteration_2_full_review(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        prompt = agent_rss._build_prompt(sample_artifact, iteration=2)
        assert "FULL REVIEW" in prompt
        # Full review includes attack vectors
        assert "Attack Vectors" in prompt

    def test_iteration_3_focused_rereview(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        """Iteration 3+ with auto mode triggers focused re-review."""
        prompt = agent_rss._build_prompt(sample_artifact, iteration=3)
        assert "FOCUSED RE-REVIEW" in prompt

    def test_prompt_contains_artifact_content(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        prompt = agent_rss._build_prompt(sample_artifact, iteration=1)
        assert "Mobile Manipulation" in prompt
        assert "dining table" in prompt

    def test_prompt_contains_stage_and_version(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        prompt = agent_rss._build_prompt(sample_artifact, iteration=1)
        assert "full_draft" in prompt
        assert "Version:** 1" in prompt


# =====================================================================
# Response parsing
# =====================================================================

class TestParsing:
    def test_parse_clean_json(self) -> None:
        raw = _make_review_json(fatal=0, serious=1, minor=2, verdict="weak_accept")
        review = ReviewAgent._parse_response(raw)
        assert isinstance(review, Review)
        assert review.verdict == Verdict.WEAK_ACCEPT
        assert len(review.serious_weaknesses) == 1
        assert len(review.minor_issues) == 2

    def test_parse_json_in_markdown_fence(self) -> None:
        raw = "Here is my review:\n\n```json\n" + _make_review_json() + "\n```\n"
        review = ReviewAgent._parse_response(raw)
        assert review.verdict == Verdict.ACCEPT

    def test_parse_json_with_surrounding_prose(self) -> None:
        raw = (
            "I have carefully reviewed the paper. My structured review:\n\n"
            + _make_review_json(serious=2, verdict="weak_reject")
            + "\n\nThank you."
        )
        review = ReviewAgent._parse_response(raw)
        assert review.verdict == Verdict.WEAK_REJECT

    def test_parse_preserves_chain(self) -> None:
        raw = _make_review_json()
        review = ReviewAgent._parse_response(raw)
        assert review.chain_extraction.task == "Clear a dining table"
        assert review.chain_extraction.chain_complete is True

    def test_parse_preserves_findings(self) -> None:
        raw = _make_review_json(fatal=1, serious=2, minor=3)
        review = ReviewAgent._parse_response(raw)
        assert len(review.fatal_flaws) == 1
        assert len(review.serious_weaknesses) == 2
        assert len(review.minor_issues) == 3
        assert review.fatal_flaws[0].severity == Severity.FATAL

    def test_parse_invalid_json_raises(self) -> None:
        with pytest.raises((json.JSONDecodeError, Exception)):
            ReviewAgent._parse_response("This is not JSON at all.")


# =====================================================================
# Verdict computation
# =====================================================================

class TestVerdictComputation:
    def test_fatal_flaw_rejects(self) -> None:
        findings = [_make_finding(Severity.FATAL)]
        assert ReviewAgent.compute_verdict(findings) == Verdict.REJECT

    def test_fatal_plus_others_still_rejects(self) -> None:
        findings = [
            _make_finding(Severity.FATAL, fid="f1"),
            _make_finding(Severity.SERIOUS, fid="s1"),
            _make_finding(Severity.MINOR, fid="m1"),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.REJECT

    def test_no_findings_accepts(self) -> None:
        assert ReviewAgent.compute_verdict([]) == Verdict.ACCEPT

    def test_only_minor_accepts(self) -> None:
        findings = [
            _make_finding(Severity.MINOR, fid="m1"),
            _make_finding(Severity.MINOR, fid="m2"),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.ACCEPT

    def test_one_fixable_serious_weak_accept(self) -> None:
        findings = [_make_finding(Severity.SERIOUS, fixable=True)]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_ACCEPT

    def test_three_plus_serious_weak_reject(self) -> None:
        findings = [
            _make_finding(Severity.SERIOUS, fixable=True, fid="s1"),
            _make_finding(Severity.SERIOUS, fixable=True, fid="s2"),
            _make_finding(Severity.SERIOUS, fixable=True, fid="s3"),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_REJECT

    def test_three_unresolvable_serious_rejects(self) -> None:
        findings = [
            _make_finding(Severity.SERIOUS, fixable=False, fid="s1"),
            _make_finding(Severity.SERIOUS, fixable=False, fid="s2"),
            _make_finding(Severity.SERIOUS, fixable=False, fid="s3"),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.REJECT

    def test_two_fixable_serious_borderline_weak_accept(self) -> None:
        findings = [
            _make_finding(Severity.SERIOUS, fixable=True, fid="s1"),
            _make_finding(Severity.SERIOUS, fixable=True, fid="s2"),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_ACCEPT

    def test_two_serious_one_unfixable_borderline_weak_reject(self) -> None:
        findings = [
            _make_finding(Severity.SERIOUS, fixable=True, fid="s1"),
            _make_finding(Severity.SERIOUS, fixable=False, fid="s2"),
        ]
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_REJECT

    def test_mixed_serious_and_minor(self) -> None:
        findings = [
            _make_finding(Severity.SERIOUS, fixable=True, fid="s1"),
            _make_finding(Severity.MINOR, fid="m1"),
            _make_finding(Severity.MINOR, fid="m2"),
        ]
        # 1 fixable serious + minors -> WEAK_ACCEPT
        assert ReviewAgent.compute_verdict(findings) == Verdict.WEAK_ACCEPT


# =====================================================================
# Chain extraction
# =====================================================================

class TestChainExtraction:
    def test_extract_labelled_chain(self) -> None:
        text = (
            "Task: Clear a dining table autonomously.\n"
            "Problem: Plan collision-free pick-and-place.\n"
            "Challenge: Factorial combinatorial explosion.\n"
            "Approach: Decomposition into scheduling and grasping.\n"
            "Contribution: Polynomial reduction via independence.\n"
        )
        chain = ReviewAgent.extract_chain(text)
        assert chain.task is not None
        assert "dining table" in chain.task
        assert chain.problem is not None
        assert chain.challenge is not None
        assert chain.approach is not None
        assert chain.one_sentence is not None
        assert chain.chain_complete is True

    def test_extract_partial_chain(self) -> None:
        text = (
            "Task: Fold laundry.\n"
            "Problem: Deformable object manipulation.\n"
        )
        chain = ReviewAgent.extract_chain(text)
        assert chain.task is not None
        assert chain.problem is not None
        assert chain.challenge is None
        assert chain.chain_complete is False

    def test_extract_heading_style(self) -> None:
        text = (
            "## Task\nClear a dining table.\n\n"
            "## Problem\nPlan pick-and-place actions.\n\n"
            "## Challenge\nCombinatorial growth.\n\n"
            "## Approach\nDecomposition.\n\n"
            "## Contribution\nPolynomial complexity.\n"
        )
        chain = ReviewAgent.extract_chain(text)
        assert chain.task is not None
        assert chain.chain_complete is True

    def test_extract_empty_text(self) -> None:
        chain = ReviewAgent.extract_chain("")
        assert chain.task is None
        assert chain.chain_complete is False
        assert chain.compute_completeness() == 0.0

    def test_extract_bold_labels(self) -> None:
        text = (
            "**Task:** Robot dishwashing.\n"
            "**Problem:** Contact-rich manipulation.\n"
            "**Challenge:** Sim-to-real transfer for contacts.\n"
            "**Approach:** Domain randomization.\n"
            "**Contribution:** Structured domain randomization.\n"
        )
        chain = ReviewAgent.extract_chain(text)
        assert chain.task is not None
        assert "dishwashing" in chain.task
        assert chain.chain_complete is True

    def test_completeness_computed(self) -> None:
        chain = ReviewAgent.extract_chain("Task: X\nProblem: Y\n")
        assert chain.compute_completeness() == pytest.approx(0.4)


# =====================================================================
# Re-review mode
# =====================================================================

class TestRereview:
    def test_rereview_prompt_includes_previous_findings(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        """Re-review prompt should include previous review findings."""
        previous = Review(
            version=1,
            iteration=1,
            summary="Previous summary.",
            chain_extraction=TaskChain(
                task="Clear table",
                chain_complete=True,
                chain_coherent=True,
            ),
            steel_man="Strong argument.",
            fatal_flaws=[],
            serious_weaknesses=[
                _make_finding(Severity.SERIOUS, fid="prev-s1"),
            ],
            minor_issues=[
                _make_finding(Severity.MINOR, fid="prev-m1"),
            ],
            verdict=Verdict.WEAK_REJECT,
            confidence=3,
        )
        prompt = agent_rss._build_prompt(
            sample_artifact,
            iteration=3,
            previous_review=previous,
        )
        # Should contain previous findings context
        assert "Previous Finding" in prompt
        assert "prev-s1" in prompt
        # Should use focused re-review mode
        assert "FOCUSED RE-REVIEW" in prompt
        # Should include pairwise comparison section
        assert "Previous verdict" in prompt
        assert "weak_reject" in prompt

    def test_rereview_prompt_without_previous_is_auto(
        self, agent_rss: ReviewAgent, sample_artifact: ResearchArtifact
    ) -> None:
        """Without a previous review, iteration 3 still gets focused mode."""
        prompt = agent_rss._build_prompt(sample_artifact, iteration=3)
        assert "FOCUSED RE-REVIEW" in prompt
        # But no previous findings section
        assert "Previous Finding" not in prompt
