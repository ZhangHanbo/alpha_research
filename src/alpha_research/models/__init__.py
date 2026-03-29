"""Data models for the alpha_research system."""

from alpha_research.models.research import (
    CoverageReport,
    Evaluation,
    ExtractionQuality,
    Paper,
    PaperCandidate,
    PaperMetadata,
    RubricScore,
    SearchQuery,
    SearchState,
    SignificanceAssessment,
    TaskChain,
)
from alpha_research.models.review import (
    ChallengeType,
    ContributionType,
    Finding,
    FindingDeferral,
    FindingDispute,
    FindingResponse,
    FormalizationLevel,
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
    Blackboard,
    ConvergenceState,
    HumanDecision,
    ResearchArtifact,
    Venue,
)

__all__ = [
    # research
    "Paper", "ExtractionQuality", "PaperMetadata", "Evaluation",
    "RubricScore", "TaskChain", "SignificanceAssessment",
    "SearchState", "SearchQuery", "PaperCandidate", "CoverageReport",
    # review
    "Finding", "Review", "Verdict", "Severity",
    "ReviewQualityMetrics", "ReviewQualityReport",
    "RevisionResponse", "FindingResponse", "FindingDeferral", "FindingDispute",
    "FormalizationLevel", "ChallengeType", "ValidationMode",
    "ContributionType", "MotivationType",
    # blackboard
    "Blackboard", "ResearchArtifact", "ConvergenceState",
    "HumanDecision", "Venue",
]
