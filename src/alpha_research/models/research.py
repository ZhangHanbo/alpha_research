"""Research-side data models.

Sources:
  - work_plan.md SM-1 (SearchState, SearchQuery, PaperCandidate, CoverageReport)
  - work_plan.md SM-2 (Paper, ExtractionQuality, PaperMetadata)
  - work_plan.md SM-3 (Evaluation, RubricScore, TaskChain, SignificanceAssessment)
"""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# SM-1: Search & Discovery
# ---------------------------------------------------------------------------

class SearchQuery(BaseModel):
    """A single search query executed against ArXiv or Semantic Scholar."""
    query: str
    source: Literal["arxiv", "semantic_scholar"]
    categories: list[str] = Field(default_factory=list)
    date_start: datetime | None = None
    date_end: datetime | None = None
    max_results: int = 50
    executed_at: datetime | None = None
    result_count: int = 0


class PaperCandidate(BaseModel):
    """A paper discovered during search, before full processing."""
    arxiv_id: str | None = None
    s2_id: str | None = None
    doi: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    abstract: str = ""
    venue: str | None = None
    year: int | None = None
    url: str | None = None
    relevance_score: float = 0.0
    source: Literal["arxiv", "semantic_scholar", "citation_graph"] = "arxiv"


class CoverageReport(BaseModel):
    """Assessment of search coverage for a topic."""
    groups_covered: list[str] = Field(default_factory=list)
    groups_missing: list[str] = Field(default_factory=list)
    approach_categories_found: list[str] = Field(default_factory=list)
    approach_categories_missing: list[str] = Field(default_factory=list)
    high_cited_refs_missing: list[str] = Field(default_factory=list)
    coverage_sufficient: bool = False


class SearchStatus(str, Enum):
    QUERYING = "querying"
    FILTERING = "filtering"
    ASSESSING = "assessing"
    EXPANDING = "expanding"
    CONVERGED = "converged"


class SearchState(BaseModel):
    """State of an iterative search process (SM-1)."""
    queries_executed: list[SearchQuery] = Field(default_factory=list)
    papers_found: dict[str, PaperCandidate] = Field(default_factory=dict)
    coverage_assessment: CoverageReport | None = None
    expansion_rounds: int = 0
    status: SearchStatus = SearchStatus.QUERYING


# ---------------------------------------------------------------------------
# SM-2: Paper Processing
# ---------------------------------------------------------------------------

class ExtractionQuality(BaseModel):
    """Quality assessment of text extraction from a paper."""
    overall: Literal["high", "medium", "low", "abstract_only"]
    math_preserved: bool = False
    sections_detected: list[str] = Field(default_factory=list)
    flagged_issues: list[str] = Field(default_factory=list)


class PaperMetadata(BaseModel):
    """Metadata from external sources (Semantic Scholar, etc.)."""
    citation_count: int = 0
    influential_citation_count: int = 0
    references_count: int = 0
    tldr: str | None = None
    code_url: str | None = None
    venue_normalized: str | None = None
    fields_of_study: list[str] = Field(default_factory=list)


class PaperStatus(str, Enum):
    DISCOVERED = "discovered"
    FETCHED = "fetched"
    EXTRACTED = "extracted"
    VALIDATED = "validated"
    ENRICHED = "enriched"
    STORED = "stored"


class Paper(BaseModel):
    """A fully processed research paper."""
    arxiv_id: str | None = None
    s2_id: str | None = None
    doi: str | None = None
    title: str
    authors: list[str] = Field(default_factory=list)
    venue: str | None = None
    year: int | None = None
    abstract: str = ""
    full_text: str | None = None
    sections: dict[str, str] = Field(default_factory=dict)
    extraction_source: Literal["pdf", "html", "abstract_only"] = "abstract_only"
    extraction_quality: ExtractionQuality | None = None
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    status: PaperStatus = PaperStatus.DISCOVERED
    url: str | None = None

    @property
    def primary_id(self) -> str:
        """Return the best available identifier."""
        return self.arxiv_id or self.s2_id or self.doi or self.title


# ---------------------------------------------------------------------------
# SM-3: Paper Evaluation
# ---------------------------------------------------------------------------

class TaskChain(BaseModel):
    """The extracted task→problem→challenge→approach→contribution chain."""
    task: str | None = None
    problem: str | None = None
    challenge: str | None = None
    approach: str | None = None
    one_sentence: str | None = None
    chain_complete: bool = False
    chain_coherent: bool = False

    def compute_completeness(self) -> float:
        """Fraction of non-null fields (out of 5 core fields)."""
        fields = [self.task, self.problem, self.challenge,
                  self.approach, self.one_sentence]
        return sum(1 for f in fields if f is not None) / 5.0

    @property
    def broken_links(self) -> list[str]:
        """Return names of missing chain links."""
        links = []
        if self.task is None:
            links.append("task")
        if self.problem is None:
            links.append("problem")
        if self.challenge is None:
            links.append("challenge")
        if self.approach is None:
            links.append("approach")
        if self.one_sentence is None:
            links.append("one_sentence")
        return links


class RubricScore(BaseModel):
    """Score for a single rubric dimension."""
    score: int = Field(ge=1, le=5)
    confidence: Literal["high", "medium", "low"]
    evidence: list[str] = Field(default_factory=list)
    reasoning: str = ""


class SignificanceAssessment(BaseModel):
    """Structured assessment of problem significance (§2.2 tests)."""
    hamming_score: int = Field(ge=1, le=5, default=3)
    hamming_reasoning: str = ""
    concrete_consequence: str | None = None
    durability_risk: Literal["low", "medium", "high"] = "medium"
    durability_reasoning: str = ""
    compounding_value: Literal["high", "medium", "low"] = "medium"
    compounding_reasoning: str = ""
    motivation_type: Literal["goal_driven", "idea_driven", "unclear"] = "unclear"


class EvaluationStatus(str, Enum):
    SKIMMED = "skimmed"
    DEEP_READ = "deep_read"
    EVALUATED = "evaluated"
    CROSS_CHECKED = "cross_checked"
    FINALIZED = "finalized"


class PaperRelation(BaseModel):
    """Relationship between two papers."""
    paper_id: str
    relation_type: Literal[
        "extends", "contradicts", "supersedes",
        "same_task", "same_method", "cites"
    ]
    evidence: str = ""
    confidence: Literal["high", "medium", "low"] = "medium"


class Contradiction(BaseModel):
    """A contradiction found between papers."""
    paper_id: str
    claim_a: str
    claim_b: str
    evidence: str = ""


class Evaluation(BaseModel):
    """Full evaluation of a paper against the research guidelines rubric."""
    paper_id: str
    cycle_id: str = ""
    mode: str = ""
    status: EvaluationStatus = EvaluationStatus.SKIMMED

    task_chain: TaskChain | None = None
    has_formal_problem_def: bool = False
    formal_framework: str | None = None
    structure_identified: list[str] = Field(default_factory=list)

    rubric_scores: dict[str, RubricScore] = Field(default_factory=dict)
    significance_assessment: SignificanceAssessment | None = None

    related_papers: list[PaperRelation] = Field(default_factory=list)
    contradictions: list[Contradiction] = Field(default_factory=list)
    novelty_vs_store: Literal[
        "novel", "incremental", "duplicate", "unknown"
    ] = "unknown"

    extraction_limitations: list[str] = Field(default_factory=list)
    human_review_flags: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
