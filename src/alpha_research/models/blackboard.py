"""Shared blackboard model for multi-agent coordination.

Sources:
  - review_plan.md §2.2 (Blackboard, ResearchArtifact, ConvergenceState)
  - review_plan.md §2.4-2.5 (convergence criteria)
  - review_plan.md §4.4 (configuration)
"""

from __future__ import annotations

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from alpha_research.models.research import TaskChain
from alpha_research.models.review import Review, RevisionResponse


# ---------------------------------------------------------------------------
# Venue Configuration
# ---------------------------------------------------------------------------

class Venue(str, Enum):
    """Target publication venue (review_guideline.md §4.1)."""
    IJRR = "IJRR"
    T_RO = "T-RO"
    RSS = "RSS"
    CORL = "CoRL"
    RA_L = "RA-L"
    ICRA = "ICRA"
    IROS = "IROS"


# Venue-specific thresholds from review_guideline.md §4.1
VENUE_ACCEPTANCE_RATES: dict[Venue, float] = {
    Venue.IJRR: 0.20,
    Venue.T_RO: 0.25,
    Venue.RSS: 0.30,
    Venue.CORL: 0.30,
    Venue.RA_L: 0.40,
    Venue.ICRA: 0.45,
    Venue.IROS: 0.45,
}

VENUE_REQUIRES_REAL_ROBOT: dict[Venue, str] = {
    Venue.IJRR: "strongly_encouraged",
    Venue.T_RO: "strongly_encouraged",
    Venue.RSS: "preferred",
    Venue.CORL: "required_for_scope",
    Venue.RA_L: "expected",
    Venue.ICRA: "preferred",
    Venue.IROS: "preferred",
}

VENUE_REQUIRES_FORMALIZATION: dict[Venue, str] = {
    Venue.IJRR: "yes_deep",
    Venue.T_RO: "yes",
    Venue.RSS: "preferred",
    Venue.CORL: "preferred",
    Venue.RA_L: "helpful",
    Venue.ICRA: "helpful",
    Venue.IROS: "helpful",
}


# ---------------------------------------------------------------------------
# Research Artifact
# ---------------------------------------------------------------------------

class ResearchStage(str, Enum):
    """Stage in the research state machine (work_plan.md §top)."""
    SIGNIFICANCE = "significance"
    FORMALIZATION = "formalization"
    DIAGNOSE = "diagnose"
    CHALLENGE = "challenge"
    APPROACH = "approach"
    VALIDATE = "validate"
    FULL_DRAFT = "full_draft"


class ArtifactDiff(BaseModel):
    """Record of what changed between artifact versions."""
    version: int
    timestamp: datetime = Field(default_factory=datetime.now)
    changes_summary: str = ""
    findings_addressed: list[str] = Field(default_factory=list)


class ResearchArtifact(BaseModel):
    """What the research agent produces at each stage."""
    stage: ResearchStage
    content: str = Field(description="Markdown content of the artifact")
    task_chain: TaskChain = Field(default_factory=TaskChain)
    metadata: dict = Field(default_factory=dict)
    version: int = 1
    created_at: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Convergence State
# ---------------------------------------------------------------------------

class ConvergenceReason(str, Enum):
    """Why the loop converged (review_plan.md §2.5)."""
    QUALITY_MET = "quality_met"
    HUMAN_APPROVED = "human_approved"
    ITERATION_LIMIT = "iteration_limit"
    STAGNATED = "stagnated"
    NOT_CONVERGED = "not_converged"


class ConvergenceState(BaseModel):
    """Current convergence status of the review loop."""
    converged: bool = False
    reason: ConvergenceReason = ConvergenceReason.NOT_CONVERGED
    iterations_completed: int = 0
    finding_resolution_rates: list[float] = Field(default_factory=list)
    verdict_history: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Human Decisions
# ---------------------------------------------------------------------------

class HumanAction(str, Enum):
    """Actions a human can take at a checkpoint."""
    APPROVE = "approve"
    OVERRIDE_FINDING = "override_finding"
    ADD_FINDING = "add_finding"
    FORCE_ITERATION = "force_iteration"
    APPROVE_BACKWARD = "approve_backward"
    DENY_BACKWARD = "deny_backward"


class HumanDecision(BaseModel):
    """A human decision at a checkpoint."""
    iteration: int
    action: HumanAction
    details: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)


# ---------------------------------------------------------------------------
# Blackboard (shared state)
# ---------------------------------------------------------------------------

class Blackboard(BaseModel):
    """Shared state between research and review agents.

    Persisted to disk between iterations. The single source of truth.
    Source: review_plan.md §2.2
    """
    # Research artifact
    artifact: ResearchArtifact | None = None
    artifact_version: int = 0
    artifact_history: list[ArtifactDiff] = Field(default_factory=list)

    # Review state
    current_review: Review | None = None
    review_history: list[Review] = Field(default_factory=list)

    # Revision responses
    revision_responses: list[RevisionResponse] = Field(default_factory=list)

    # Meta-review state
    review_quality: "ReviewQualityReport | None" = None

    # Convergence tracking
    iteration: int = 0
    convergence_state: ConvergenceState = Field(
        default_factory=ConvergenceState
    )

    # Human checkpoints
    human_decisions: list[HumanDecision] = Field(default_factory=list)

    # Configuration
    target_venue: Venue = Venue.RSS
    review_mode: Literal["full", "focused", "quick"] = "full"
    max_iterations: int = 5

    # Persistence
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    def save(self, path: Path) -> None:
        """Persist blackboard to disk as JSON."""
        path.parent.mkdir(parents=True, exist_ok=True)
        data = self.model_dump(mode="json")
        path.write_text(json.dumps(data, indent=2, default=str))

    @classmethod
    def load(cls, path: Path) -> Blackboard:
        """Load blackboard from disk."""
        data = json.loads(path.read_text())
        return cls.model_validate(data)

    def update_timestamp(self) -> None:
        self.updated_at = datetime.now()


# Deferred import for type hint
from alpha_research.models.review import ReviewQualityReport  # noqa: E402, F811

Blackboard.model_rebuild()
