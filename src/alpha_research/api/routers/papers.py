"""Paper endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from alpha_research.api.models import EvaluationResponse, PaperResponse

router = APIRouter(prefix="/api/papers", tags=["papers"])


def _get_store():
    """Lazy import to avoid circular / startup issues."""
    from alpha_research.api.app import get_store

    return get_store()


# ------------------------------------------------------------------
# helpers
# ------------------------------------------------------------------

def _paper_to_response(paper) -> PaperResponse:
    return PaperResponse(
        arxiv_id=paper.arxiv_id,
        s2_id=paper.s2_id,
        doi=paper.doi,
        title=paper.title,
        authors=paper.authors,
        venue=paper.venue,
        year=paper.year,
        abstract=paper.abstract,
        url=paper.url,
        status=paper.status.value if hasattr(paper.status, "value") else paper.status,
        extraction_source=paper.extraction_source,
    )


def _eval_to_response(ev) -> EvaluationResponse:
    rubric = {}
    for k, v in ev.rubric_scores.items():
        if hasattr(v, "model_dump"):
            rubric[k] = v.model_dump()
        else:
            rubric[k] = v
    return EvaluationResponse(
        paper_id=ev.paper_id,
        cycle_id=ev.cycle_id,
        mode=ev.mode,
        status=ev.status.value if hasattr(ev.status, "value") else ev.status,
        has_formal_problem_def=ev.has_formal_problem_def,
        formal_framework=ev.formal_framework,
        structure_identified=ev.structure_identified,
        rubric_scores=rubric,
        novelty_vs_store=ev.novelty_vs_store,
        extraction_limitations=ev.extraction_limitations,
        human_review_flags=ev.human_review_flags,
        created_at=ev.created_at,
    )


# ------------------------------------------------------------------
# endpoints
# ------------------------------------------------------------------

@router.get("", response_model=list[PaperResponse])
def list_papers(
    topic: str | None = Query(None, description="LIKE search on title/abstract"),
    year_min: int | None = Query(None, description="Minimum year (inclusive)"),
    year_max: int | None = Query(None, description="Maximum year (inclusive)"),
    limit: int = Query(50, ge=1, le=500),
):
    """List papers with optional filters."""
    store = _get_store()
    date_range = None
    if year_min is not None or year_max is not None:
        date_range = (str(year_min or 1900), str(year_max or 2100))
    papers = store.query_papers(topic=topic, date_range=date_range, limit=limit)
    return [_paper_to_response(p) for p in papers]


@router.get("/{paper_id}", response_model=PaperResponse)
def get_paper(paper_id: str):
    """Retrieve a single paper by arxiv_id, s2_id, doi, or row id."""
    store = _get_store()
    paper = store.get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    return _paper_to_response(paper)


@router.get("/{paper_id}/evaluations", response_model=list[EvaluationResponse])
def get_paper_evaluations(paper_id: str):
    """All evaluations for a paper."""
    store = _get_store()
    # Verify paper exists
    paper = store.get_paper(paper_id)
    if paper is None:
        raise HTTPException(status_code=404, detail="Paper not found")
    evals = store.get_evaluations(paper_id)
    return [_eval_to_response(e) for e in evals]
