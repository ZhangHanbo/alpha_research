"""Review-side data models.

Sources:
  - review_plan.md §2.2 (Review, Finding, Verdict, RevisionResponse)
  - review_plan.md §1.1-1.7 (metric enums)
  - review_plan.md §1.8 (ReviewQualityMetrics)
  - review_guideline.md Part III (attack vectors → Finding.attack_vector)
  - review_guideline.md Part VI (rubric → verdict mapping)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Metric Enums (review_plan.md §1.1-1.7)
# ---------------------------------------------------------------------------

class FormalizationLevel(str, Enum):
    """How formally the problem is defined (§1.1)."""
    FORMAL_MATH = "formal_math"
    SEMI_FORMAL = "semi_formal"
    PROSE_ONLY = "prose_only"
    ABSENT = "absent"


class ChallengeType(str, Enum):
    """Type of challenge identified (§1.4)."""
    STRUCTURAL = "structural"
    RESOURCE_COMPLAINT = "resource_complaint"
    ABSENT = "absent"


class ChallengeSpecificity(str, Enum):
    """Whether the challenge constrains the solution class (§1.4)."""
    CONSTRAINS_CLASS = "constrains_class"
    VAGUE = "vague"
    ABSENT = "absent"


class ValidationMode(str, Enum):
    """How the paper validates its claims (§1.6.2)."""
    REAL_ROBOT = "real_robot"
    SIM_AND_REAL = "sim_and_real"
    SIM_ONLY = "sim_only"


class ContributionType(str, Enum):
    """Type of contribution (§1.7)."""
    STRUCTURAL_INSIGHT = "structural_insight"
    INCREMENTAL_ENGINEERING = "incremental_engineering"
    APPLICATION = "application"


class MotivationType(str, Enum):
    """Goal-driven vs idea-driven (§1.2)."""
    GOAL_DRIVEN = "goal_driven"
    IDEA_DRIVEN = "idea_driven"
    UNCLEAR = "unclear"


class OneSentenceType(str, Enum):
    """Type of one-sentence contribution claim (§1.1)."""
    INSIGHT = "insight"
    PERFORMANCE_CLAIM = "performance_claim"
    ABSENT = "absent"


class EvidenceSupport(str, Enum):
    """How well evidence supports the challenge (§1.4)."""
    STRONG = "strong"
    WEAK = "weak"
    CONTRADICTED = "contradicted"


class AblationResult(str, Enum):
    """Whether ablation isolates the contribution (§1.6.1)."""
    YES = "yes"
    PARTIAL = "partial"
    NO = "no"
    ABSENT = "absent"


class ExperimentAlignment(str, Enum):
    """Whether experiments test the stated claim (§1.6.1)."""
    DIRECT = "direct"
    INDIRECT = "indirect"
    MISALIGNED = "misaligned"


class SensingAppropriateness(str, Enum):
    """Whether sensing modality matches the task (§1.6.2)."""
    APPROPRIATE = "appropriate"
    QUESTIONABLE = "questionable"
    MISMATCHED = "mismatched"


class EnvironmentComplexity(str, Enum):
    """Level of environmental complexity in experiments (§1.6.2)."""
    REAL_WORLD = "real_world"
    SEMI_CONTROLLED = "semi_controlled"
    FULLY_CONTROLLED = "fully_controlled"


# ---------------------------------------------------------------------------
# Core Review Models
# ---------------------------------------------------------------------------

class Severity(str, Enum):
    """Finding severity classification (review_guideline.md §1.3)."""
    FATAL = "fatal"
    SERIOUS = "serious"
    MINOR = "minor"


class Verdict(str, Enum):
    """Review verdict (review_guideline.md §6.6)."""
    ACCEPT = "accept"
    WEAK_ACCEPT = "weak_accept"
    WEAK_REJECT = "weak_reject"
    REJECT = "reject"


class Finding(BaseModel):
    """A single review finding — the atomic unit of critique.

    Every finding must be:
    - Specific (grounded in the paper)
    - Actionable (what would fix it)
    - Falsifiable (what would invalidate the critique)

    Source: review_plan.md §2.2, review_guideline.md §1.4-1.5
    """
    id: str = Field(default="", description="Unique identifier for cross-iteration tracking")
    severity: Severity
    attack_vector: str = Field(
        description="Which attack vector from review_guideline.md §3.1-3.6"
    )
    what_is_wrong: str = Field(
        description="The specific logical, evidential, or structural gap"
    )
    why_it_matters: str = Field(
        description="What the consequence is for the paper's claims"
    )
    what_would_fix: str = Field(
        description="Concrete, actionable path to address the issue"
    )
    falsification: str = Field(
        description="What evidence would invalidate this critique"
    )
    grounding: str = Field(
        description="Specific section/figure/table/equation reference"
    )
    fixable: bool = Field(
        description="Whether this can be addressed in revision"
    )
    maps_to_trigger: str | None = Field(
        default=None,
        description="Which backward trigger (t2-t15) this maps to, if any"
    )


class Review(BaseModel):
    """Structured review output per review_guideline.md §2.2.

    The review follows the 8-section structure:
    summary, chain extraction, steel-man, fatal flaws,
    serious weaknesses, minor issues, questions, verdict.
    """
    version: int = Field(
        description="Which artifact version was reviewed"
    )
    iteration: int = Field(default=1, description="Review iteration number")

    # Section 1: Summary
    summary: str = Field(
        description="Restate the paper's argument (RSS principle)"
    )

    # Section 2: Logical chain extraction
    chain_extraction: "TaskChain" = Field(
        description="Extracted task→problem→challenge→approach→contribution"
    )

    # Section 3: Steel-man
    steel_man: str = Field(
        description="Strongest version of the paper's argument"
    )

    # Sections 4-6: Findings
    fatal_flaws: list[Finding] = Field(default_factory=list)
    serious_weaknesses: list[Finding] = Field(default_factory=list)
    minor_issues: list[Finding] = Field(default_factory=list)

    # Section 7: Questions
    questions: list[str] = Field(
        default_factory=list,
        description="3-5 points where author responses could change verdict"
    )

    # Section 8: Verdict
    verdict: Verdict
    confidence: int = Field(ge=1, le=5, description="NeurIPS confidence scale")
    verdict_justification: str = Field(
        default="", description="One-sentence justification"
    )
    improvement_path: str = Field(
        default="",
        description="What would the authors do to increase the score?"
    )

    # Metadata
    target_venue: str = ""
    review_mode: Literal["structural_scan", "full_review", "focused_rereview"] = "full_review"
    created_at: datetime = Field(default_factory=datetime.now)

    # Computed quality metrics (filled by meta-reviewer)
    quality_metrics: "ReviewQualityMetrics | None" = None

    @property
    def all_findings(self) -> list[Finding]:
        return self.fatal_flaws + self.serious_weaknesses + self.minor_issues

    @property
    def finding_count(self) -> dict[str, int]:
        return {
            "fatal": len(self.fatal_flaws),
            "serious": len(self.serious_weaknesses),
            "minor": len(self.minor_issues),
        }


# ---------------------------------------------------------------------------
# Review Quality Models (review_plan.md §1.8)
# ---------------------------------------------------------------------------

class ReviewQualityMetrics(BaseModel):
    """Quantified metrics for review quality."""
    actionability: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of findings with actionable fix"
    )
    grounding: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of serious+ findings with grounding"
    )
    specificity_violations: int = Field(
        ge=0,
        description="Count of vague critiques (must be 0)"
    )
    falsifiability: float = Field(
        ge=0.0, le=1.0,
        description="Fraction of serious+ findings with falsification"
    )
    steel_man_sentences: int = Field(
        ge=0,
        description="Sentence count of steel-man (must be >= 3)"
    )
    all_classified: bool = Field(
        description="Whether all findings have severity classification"
    )


class MetricCheck(BaseModel):
    """Pass/fail result for a single review quality metric."""
    name: str
    passed: bool
    actual: float | int
    threshold: float | int
    message: str = ""


class AntiPatternCheck(BaseModel):
    """Detection result for a review anti-pattern."""
    pattern: str
    detected: bool
    evidence: str = ""


class ReviewQualityReport(BaseModel):
    """Meta-reviewer's assessment of review quality."""
    passes: bool
    metric_checks: list[MetricCheck] = Field(default_factory=list)
    anti_pattern_checks: list[AntiPatternCheck] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    recommendation: str = ""


# ---------------------------------------------------------------------------
# Revision Response Models (review_plan.md §3.2)
# ---------------------------------------------------------------------------

class FindingResponse(BaseModel):
    """Research agent's response to an addressed finding."""
    finding_id: str
    action_taken: str
    evidence: str = Field(
        description="Where in the artifact the change is"
    )


class FindingDeferral(BaseModel):
    """Research agent's deferral of a finding."""
    finding_id: str
    reason: str
    plan: str = Field(
        description="When/how it will be addressed"
    )


class FindingDispute(BaseModel):
    """Research agent's dispute of a finding."""
    finding_id: str
    argument: str
    evidence: str


class RevisionResponse(BaseModel):
    """Research agent's structured response to a review."""
    review_version: int
    addressed: list[FindingResponse] = Field(default_factory=list)
    deferred: list[FindingDeferral] = Field(default_factory=list)
    disputed: list[FindingDispute] = Field(default_factory=list)

    @property
    def resolution_rate(self) -> float:
        """Fraction of findings that were addressed (not deferred/disputed)."""
        total = len(self.addressed) + len(self.deferred) + len(self.disputed)
        if total == 0:
            return 1.0
        return len(self.addressed) / total


# Deferred import resolution for Review.chain_extraction type hint
from alpha_research.models.research import TaskChain  # noqa: E402

Review.model_rebuild()
