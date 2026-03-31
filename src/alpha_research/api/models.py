"""Pydantic V2 response/request models for the FastAPI layer."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Paper responses
# ---------------------------------------------------------------------------

class PaperResponse(BaseModel):
    """Serialisable representation of a paper."""

    arxiv_id: str | None = None
    s2_id: str | None = None
    doi: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    year: int | None = None
    abstract: str = ""
    url: str | None = None
    status: str = "discovered"
    extraction_source: str = "abstract_only"


# ---------------------------------------------------------------------------
# Evaluation responses
# ---------------------------------------------------------------------------

class RubricScoreResponse(BaseModel):
    score: int
    confidence: str
    evidence: list[str] = Field(default_factory=list)
    reasoning: str = ""


class EvaluationResponse(BaseModel):
    """Serialisable representation of an evaluation."""

    paper_id: str
    cycle_id: str = ""
    mode: str = ""
    status: str = "skimmed"
    has_formal_problem_def: bool = False
    formal_framework: str | None = None
    structure_identified: list[str] = Field(default_factory=list)
    rubric_scores: dict[str, Any] = Field(default_factory=dict)
    novelty_vs_store: str = "unknown"
    extraction_limitations: list[str] = Field(default_factory=list)
    human_review_flags: list[str] = Field(default_factory=list)
    created_at: datetime | None = None


class FeedbackRequest(BaseModel):
    """Body for the POST /evaluations/{eval_id}/feedback endpoint."""

    score_override: float | None = None
    note: str = ""
    flagged: bool = False


# ---------------------------------------------------------------------------
# Graph responses
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    """A paper represented as a graph node."""

    id: str
    title: str
    year: int | None = None
    venue: str | None = None
    score: float | None = None


class GraphEdge(BaseModel):
    """A relation between two papers."""

    source: str
    target: str
    relation_type: str
    confidence: str = "medium"


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class AgentRunRequest(BaseModel):
    """Body for POST /agent/run."""

    mode: str = "digest"
    question: str
    venue: str = "RSS"


class AgentStatusResponse(BaseModel):
    """Current agent state."""

    state: str = "idle"  # "idle" | "running" | "error"
    iteration: int = 0
    mode: str | None = None
    question: str | None = None
    started_at: datetime | None = None


class AgentEvent(BaseModel):
    """A single SSE event emitted by the agent."""

    type: str
    data: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Project lifecycle
# ---------------------------------------------------------------------------

class CreateProjectRequest(BaseModel):
    """Body for POST /api/projects."""

    name: str
    project_type: str = "literature"
    primary_question: str = ""
    source_path: str | None = None
    description: str = ""
    domain: str = ""
    tags: list[str] = Field(default_factory=list)


class CreateSnapshotRequest(BaseModel):
    """Body for POST /api/projects/{project_id}/snapshots."""

    note: str = ""
    milestone: bool = False
    milestone_name: str | None = None


class ResumeProjectRequest(BaseModel):
    """Body for POST /api/projects/{project_id}/resume."""

    mode: str = "current_workspace"
    snapshot_id: str | None = None
