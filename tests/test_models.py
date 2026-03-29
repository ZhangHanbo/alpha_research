"""Tests for T1: Data Models.

Tests cover:
  - Pydantic V2 validation for all models
  - Required fields enforcement
  - Enum validation
  - Serialization round-trips (JSON)
  - Computed properties (TaskChain completeness, broken_links)
  - Edge cases (empty fields, boundary values)
  - Blackboard persistence (save/load)
"""

import json
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from alpha_research.models.research import (
    CoverageReport,
    Evaluation,
    EvaluationStatus,
    ExtractionQuality,
    Paper,
    PaperCandidate,
    PaperMetadata,
    RubricScore,
    SearchQuery,
    SearchState,
    SearchStatus,
    SignificanceAssessment,
    TaskChain,
)
from alpha_research.models.review import (
    AblationResult,
    AntiPatternCheck,
    ChallengeType,
    ContributionType,
    ExperimentAlignment,
    Finding,
    FindingDeferral,
    FindingDispute,
    FindingResponse,
    FormalizationLevel,
    MetricCheck,
    MotivationType,
    Review,
    ReviewQualityMetrics,
    ReviewQualityReport,
    RevisionResponse,
    Severity,
    ValidationMode,
    Verdict,
)
from alpha_research.models.blackboard import (
    ArtifactDiff,
    Blackboard,
    ConvergenceReason,
    ConvergenceState,
    HumanAction,
    HumanDecision,
    ResearchArtifact,
    ResearchStage,
    Venue,
    VENUE_ACCEPTANCE_RATES,
)


# ===================================================================
# Fixtures
# ===================================================================

@pytest.fixture
def sample_task_chain():
    return TaskChain(
        task="Pick and place deformable objects",
        problem="Given unknown deformable object, find grasp that maximizes success",
        challenge="Contact dynamics are discontinuous and sim-to-real gap is largest at contact",
        approach="Tactile feedback provides direct contact geometry at required resolution",
        one_sentence="Tactile servoing enables sub-mm insertion alignment without vision",
        chain_complete=True,
        chain_coherent=True,
    )


@pytest.fixture
def sample_finding():
    return Finding(
        id="f1",
        severity=Severity.SERIOUS,
        attack_vector="baseline_strength",
        what_is_wrong="Paper compares only against vanilla BC, not diffusion policy baseline",
        why_it_matters="Diffusion policies are the current SOTA for this task class",
        what_would_fix="Add comparison against Diffusion Policy (Chi et al. 2023)",
        falsification="If the method outperforms Diffusion Policy, this critique is invalidated",
        grounding="Table 2, Section 5.1",
        fixable=True,
        maps_to_trigger=None,
    )


@pytest.fixture
def sample_review(sample_task_chain, sample_finding):
    return Review(
        version=1,
        iteration=1,
        summary="The paper proposes tactile servoing for deformable object manipulation.",
        chain_extraction=sample_task_chain,
        steel_man="The core insight — that tactile feedback resolves alignment ambiguity below vision resolution — is well-motivated by the physics of the problem.",
        fatal_flaws=[],
        serious_weaknesses=[sample_finding],
        minor_issues=[],
        questions=["Would this generalize to transparent objects?"],
        verdict=Verdict.WEAK_ACCEPT,
        confidence=3,
        verdict_justification="No fatal flaws. One serious weakness (missing baseline) is addressable.",
        improvement_path="Add diffusion policy comparison and 10 more trials per condition.",
        target_venue="RSS",
    )


@pytest.fixture
def sample_paper():
    return Paper(
        arxiv_id="2401.12345",
        title="Tactile Servoing for Deformable Manipulation",
        authors=["Alice", "Bob"],
        venue="RSS",
        year=2024,
        abstract="We present a tactile servoing approach...",
        full_text="Full paper text here...",
        sections={"abstract": "We present...", "method": "Our approach..."},
        extraction_source="pdf",
        extraction_quality=ExtractionQuality(
            overall="high",
            math_preserved=True,
            sections_detected=["abstract", "method", "experiments"],
        ),
    )


# ===================================================================
# Test Research Models
# ===================================================================

class TestSearchQuery:
    def test_basic_creation(self):
        q = SearchQuery(query="tactile manipulation", source="arxiv")
        assert q.query == "tactile manipulation"
        assert q.source == "arxiv"
        assert q.max_results == 50

    def test_with_filters(self):
        q = SearchQuery(
            query="grasping",
            source="semantic_scholar",
            categories=["cs.RO"],
            max_results=20,
        )
        assert q.categories == ["cs.RO"]

    def test_json_roundtrip(self):
        q = SearchQuery(query="test", source="arxiv")
        data = q.model_dump(mode="json")
        q2 = SearchQuery.model_validate(data)
        assert q2.query == q.query


class TestPaperCandidate:
    def test_basic(self):
        p = PaperCandidate(title="Test Paper", arxiv_id="2401.00001")
        assert p.title == "Test Paper"
        assert p.relevance_score == 0.0

    def test_minimal(self):
        p = PaperCandidate(title="Minimal")
        assert p.arxiv_id is None
        assert p.source == "arxiv"


class TestCoverageReport:
    def test_default_not_sufficient(self):
        c = CoverageReport()
        assert c.coverage_sufficient is False

    def test_with_data(self):
        c = CoverageReport(
            groups_covered=["Berkeley", "MIT"],
            groups_missing=["Stanford"],
            coverage_sufficient=False,
        )
        assert len(c.groups_covered) == 2


class TestSearchState:
    def test_default_status(self):
        s = SearchState()
        assert s.status == SearchStatus.QUERYING
        assert s.expansion_rounds == 0

    def test_with_papers(self):
        s = SearchState(
            papers_found={"2401.1": PaperCandidate(title="P1")},
            status=SearchStatus.CONVERGED,
        )
        assert len(s.papers_found) == 1


class TestExtractionQuality:
    def test_all_levels(self):
        for level in ["high", "medium", "low", "abstract_only"]:
            eq = ExtractionQuality(overall=level)
            assert eq.overall == level

    def test_invalid_level(self):
        with pytest.raises(Exception):
            ExtractionQuality(overall="invalid")


class TestPaper:
    def test_basic(self, sample_paper):
        assert sample_paper.primary_id == "2401.12345"

    def test_primary_id_fallback(self):
        p = Paper(title="No IDs", s2_id="s2_123")
        assert p.primary_id == "s2_123"

        p2 = Paper(title="Title Only")
        assert p2.primary_id == "Title Only"

    def test_json_roundtrip(self, sample_paper):
        data = sample_paper.model_dump(mode="json")
        p2 = Paper.model_validate(data)
        assert p2.title == sample_paper.title
        assert p2.extraction_quality.overall == "high"


class TestTaskChain:
    def test_complete_chain(self, sample_task_chain):
        assert sample_task_chain.compute_completeness() == 1.0
        assert sample_task_chain.broken_links == []

    def test_partial_chain(self):
        tc = TaskChain(task="Pick objects", problem="Grasp planning")
        assert tc.compute_completeness() == 0.4
        assert "challenge" in tc.broken_links
        assert "approach" in tc.broken_links
        assert "one_sentence" in tc.broken_links

    def test_empty_chain(self):
        tc = TaskChain()
        assert tc.compute_completeness() == 0.0
        assert len(tc.broken_links) == 5

    def test_json_roundtrip(self, sample_task_chain):
        data = sample_task_chain.model_dump(mode="json")
        tc2 = TaskChain.model_validate(data)
        assert tc2.compute_completeness() == 1.0


class TestRubricScore:
    def test_valid_range(self):
        rs = RubricScore(score=5, confidence="high", evidence=["Section 3"])
        assert rs.score == 5

    def test_out_of_range(self):
        with pytest.raises(Exception):
            RubricScore(score=0, confidence="high")
        with pytest.raises(Exception):
            RubricScore(score=6, confidence="high")

    def test_invalid_confidence(self):
        with pytest.raises(Exception):
            RubricScore(score=3, confidence="very_high")


class TestSignificanceAssessment:
    def test_defaults(self):
        sa = SignificanceAssessment()
        assert sa.hamming_score == 3
        assert sa.durability_risk == "medium"
        assert sa.motivation_type == "unclear"

    def test_with_values(self):
        sa = SignificanceAssessment(
            hamming_score=5,
            concrete_consequence="Robots handle 3x more SKU diversity",
            durability_risk="low",
            compounding_value="high",
            motivation_type="goal_driven",
        )
        assert sa.concrete_consequence is not None


class TestEvaluation:
    def test_basic(self):
        ev = Evaluation(paper_id="2401.12345")
        assert ev.status == EvaluationStatus.SKIMMED
        assert ev.novelty_vs_store == "unknown"

    def test_with_rubric(self):
        ev = Evaluation(
            paper_id="test",
            rubric_scores={
                "significance": RubricScore(score=4, confidence="medium"),
                "technical": RubricScore(score=3, confidence="high"),
            },
        )
        assert len(ev.rubric_scores) == 2

    def test_json_roundtrip(self):
        ev = Evaluation(
            paper_id="test",
            task_chain=TaskChain(task="Pick things"),
            has_formal_problem_def=True,
            formal_framework="POMDP",
        )
        data = ev.model_dump(mode="json")
        ev2 = Evaluation.model_validate(data)
        assert ev2.formal_framework == "POMDP"


# ===================================================================
# Test Review Models
# ===================================================================

class TestEnums:
    def test_formalization_level(self):
        assert FormalizationLevel.FORMAL_MATH.value == "formal_math"
        assert FormalizationLevel.ABSENT.value == "absent"

    def test_challenge_type(self):
        assert ChallengeType.STRUCTURAL.value == "structural"

    def test_validation_mode(self):
        assert ValidationMode.REAL_ROBOT.value == "real_robot"

    def test_contribution_type(self):
        assert ContributionType.STRUCTURAL_INSIGHT.value == "structural_insight"

    def test_severity(self):
        assert Severity.FATAL.value == "fatal"
        assert Severity.SERIOUS.value == "serious"
        assert Severity.MINOR.value == "minor"

    def test_verdict(self):
        assert Verdict.ACCEPT.value == "accept"
        assert Verdict.REJECT.value == "reject"


class TestFinding:
    def test_all_fields_required(self):
        """Finding must have all fields populated (TASKS.md T1 acceptance)."""
        f = Finding(
            id="f1",
            severity=Severity.FATAL,
            attack_vector="trivial_variant",
            what_is_wrong="Method is functionally equivalent to impedance control",
            why_it_matters="No novel contribution beyond existing work",
            what_would_fix="Show structural difference from impedance control",
            falsification="Demonstrate a case where impedance control fails but this method succeeds",
            grounding="Section 3.2, Equation 5",
            fixable=False,
            maps_to_trigger="t5",
        )
        assert f.severity == Severity.FATAL
        assert f.maps_to_trigger == "t5"

    def test_missing_required_field(self):
        """Should fail if required fields are missing."""
        with pytest.raises(Exception):
            Finding(
                severity=Severity.MINOR,
                attack_vector="test",
                # missing other required fields
            )

    def test_json_roundtrip(self, sample_finding):
        data = sample_finding.model_dump(mode="json")
        f2 = Finding.model_validate(data)
        assert f2.attack_vector == sample_finding.attack_vector


class TestReview:
    def test_basic_creation(self, sample_review):
        assert sample_review.verdict == Verdict.WEAK_ACCEPT
        assert sample_review.confidence == 3

    def test_all_findings(self, sample_review):
        assert len(sample_review.all_findings) == 1
        assert sample_review.all_findings[0].severity == Severity.SERIOUS

    def test_finding_count(self, sample_review):
        counts = sample_review.finding_count
        assert counts["fatal"] == 0
        assert counts["serious"] == 1
        assert counts["minor"] == 0

    def test_json_roundtrip(self, sample_review):
        data = sample_review.model_dump(mode="json")
        r2 = Review.model_validate(data)
        assert r2.verdict == Verdict.WEAK_ACCEPT
        assert len(r2.serious_weaknesses) == 1
        assert r2.chain_extraction.task is not None

    def test_confidence_range(self, sample_task_chain):
        with pytest.raises(Exception):
            Review(
                version=1,
                summary="test",
                chain_extraction=sample_task_chain,
                steel_man="test",
                verdict=Verdict.ACCEPT,
                confidence=0,  # out of range
            )
        with pytest.raises(Exception):
            Review(
                version=1,
                summary="test",
                chain_extraction=sample_task_chain,
                steel_man="test",
                verdict=Verdict.ACCEPT,
                confidence=6,  # out of range
            )


class TestReviewQualityMetrics:
    def test_valid(self):
        m = ReviewQualityMetrics(
            actionability=0.85,
            grounding=0.92,
            specificity_violations=0,
            falsifiability=0.75,
            steel_man_sentences=4,
            all_classified=True,
        )
        assert m.actionability == 0.85

    def test_bounds(self):
        with pytest.raises(Exception):
            ReviewQualityMetrics(
                actionability=1.5,  # > 1.0
                grounding=0.9,
                specificity_violations=0,
                falsifiability=0.7,
                steel_man_sentences=3,
                all_classified=True,
            )


class TestReviewQualityReport:
    def test_passing(self):
        r = ReviewQualityReport(
            passes=True,
            metric_checks=[
                MetricCheck(name="actionability", passed=True, actual=0.9, threshold=0.8),
            ],
            anti_pattern_checks=[
                AntiPatternCheck(pattern="dimension_averaging", detected=False),
            ],
        )
        assert r.passes is True

    def test_failing(self):
        r = ReviewQualityReport(
            passes=False,
            issues=["Vague critique found: 'the evaluation is weak'"],
        )
        assert r.passes is False


class TestRevisionResponse:
    def test_resolution_rate(self):
        rr = RevisionResponse(
            review_version=1,
            addressed=[
                FindingResponse(finding_id="f1", action_taken="Added baseline", evidence="Table 2"),
                FindingResponse(finding_id="f2", action_taken="Added trials", evidence="Section 5"),
            ],
            deferred=[
                FindingDeferral(finding_id="f3", reason="Needs real robot", plan="Phase 2"),
            ],
        )
        assert rr.resolution_rate == pytest.approx(2/3)

    def test_empty_response(self):
        rr = RevisionResponse(review_version=1)
        assert rr.resolution_rate == 1.0  # no findings = fully resolved

    def test_dispute(self):
        rr = RevisionResponse(
            review_version=1,
            disputed=[
                FindingDispute(
                    finding_id="f1",
                    argument="Our method differs structurally because...",
                    evidence="Section 3.2 shows the key difference",
                ),
            ],
        )
        assert rr.resolution_rate == 0.0  # disputes don't count as addressed


# ===================================================================
# Test Blackboard Models
# ===================================================================

class TestVenue:
    def test_all_venues(self):
        assert len(Venue) == 7
        for v in Venue:
            assert v in VENUE_ACCEPTANCE_RATES

    def test_acceptance_rates_ordered(self):
        """IJRR should be strictest, ICRA/IROS most lenient."""
        assert VENUE_ACCEPTANCE_RATES[Venue.IJRR] < VENUE_ACCEPTANCE_RATES[Venue.ICRA]
        assert VENUE_ACCEPTANCE_RATES[Venue.RSS] < VENUE_ACCEPTANCE_RATES[Venue.IROS]


class TestResearchArtifact:
    def test_basic(self):
        a = ResearchArtifact(
            stage=ResearchStage.SIGNIFICANCE,
            content="# Significance Argument\n\nThis problem matters because...",
        )
        assert a.version == 1
        assert a.stage == ResearchStage.SIGNIFICANCE

    def test_all_stages(self):
        for stage in ResearchStage:
            a = ResearchArtifact(stage=stage, content="test")
            assert a.stage == stage


class TestConvergenceState:
    def test_default(self):
        cs = ConvergenceState()
        assert cs.converged is False
        assert cs.reason == ConvergenceReason.NOT_CONVERGED

    def test_converged(self):
        cs = ConvergenceState(
            converged=True,
            reason=ConvergenceReason.QUALITY_MET,
            iterations_completed=3,
        )
        assert cs.converged is True


class TestHumanDecision:
    def test_creation(self):
        hd = HumanDecision(
            iteration=2,
            action=HumanAction.APPROVE_BACKWARD,
            details="Approved backward transition to SIGNIFICANCE",
        )
        assert hd.action == HumanAction.APPROVE_BACKWARD


class TestBlackboard:
    def test_empty_creation(self):
        bb = Blackboard()
        assert bb.iteration == 0
        assert bb.artifact is None
        assert bb.current_review is None

    def test_with_artifact(self):
        bb = Blackboard(
            artifact=ResearchArtifact(
                stage=ResearchStage.FORMALIZATION,
                content="# Problem Definition\n...",
            ),
            artifact_version=1,
            target_venue=Venue.RSS,
        )
        assert bb.artifact.stage == ResearchStage.FORMALIZATION
        assert bb.target_venue == Venue.RSS

    def test_save_load_roundtrip(self, sample_review):
        """Blackboard must round-trip through JSON without data loss (T1 acceptance criteria)."""
        bb = Blackboard(
            artifact=ResearchArtifact(
                stage=ResearchStage.CHALLENGE,
                content="Test content",
                task_chain=TaskChain(task="Pick objects"),
            ),
            artifact_version=2,
            current_review=sample_review,
            review_history=[sample_review],
            iteration=3,
            convergence_state=ConvergenceState(
                converged=False,
                iterations_completed=3,
                verdict_history=["weak_reject", "weak_accept", "weak_accept"],
            ),
            target_venue=Venue.CORL,
            human_decisions=[
                HumanDecision(iteration=1, action=HumanAction.FORCE_ITERATION),
            ],
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "blackboard.json"
            bb.save(path)

            assert path.exists()
            bb2 = Blackboard.load(path)

            assert bb2.artifact_version == 2
            assert bb2.artifact.stage == ResearchStage.CHALLENGE
            assert bb2.current_review.verdict == Verdict.WEAK_ACCEPT
            assert len(bb2.review_history) == 1
            assert bb2.iteration == 3
            assert bb2.target_venue == Venue.CORL
            assert len(bb2.human_decisions) == 1
            assert bb2.convergence_state.verdict_history == [
                "weak_reject", "weak_accept", "weak_accept"
            ]

    def test_save_creates_parent_dirs(self):
        bb = Blackboard()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nested" / "dir" / "bb.json"
            bb.save(path)
            assert path.exists()

    def test_update_timestamp(self):
        bb = Blackboard()
        old = bb.updated_at
        import time
        time.sleep(0.01)
        bb.update_timestamp()
        assert bb.updated_at > old
