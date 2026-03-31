"""Evaluation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from alpha_research.api.models import EvaluationResponse, FeedbackRequest

router = APIRouter(prefix="/api/evaluations", tags=["evaluations"])


def _get_store():
    from alpha_research.api.app import get_store

    return get_store()


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


def _resolve_store(project_id: str | None):
    """Return the project-scoped or global store."""
    if project_id:
        from alpha_research.api.app import get_orchestrator
        orch = get_orchestrator()
        return orch.service.get_knowledge_store(project_id)
    return _get_store()


@router.get("", response_model=list[EvaluationResponse])
def list_evaluations(
    cycle_id: str | None = Query(None),
    mode: str | None = Query(None),
    min_score: float | None = Query(None, description="Minimum average rubric score"),
    project_id: str | None = Query(None, description="Scope to a project's knowledge store"),
):
    """List evaluations with optional filters."""
    import json
    import sqlite3

    store = _resolve_store(project_id)
    conn = store._connect()
    try:
        clauses: list[str] = []
        params: list = []

        if cycle_id is not None:
            clauses.append("cycle_id = ?")
            params.append(cycle_id)

        if mode is not None:
            clauses.append("mode = ?")
            params.append(mode)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"SELECT * FROM evaluations{where} ORDER BY created_at DESC"
        rows = conn.execute(sql, params).fetchall()

        evaluations = [store._row_to_evaluation(r) for r in rows]

        # Optional client-side score filter
        if min_score is not None:
            filtered = []
            for ev in evaluations:
                scores = []
                for v in ev.rubric_scores.values():
                    if hasattr(v, "score"):
                        scores.append(v.score)
                    elif isinstance(v, dict) and "score" in v:
                        scores.append(v["score"])
                if scores and (sum(scores) / len(scores)) >= min_score:
                    filtered.append(ev)
            evaluations = filtered

        return [_eval_to_response(e) for e in evaluations]
    finally:
        conn.close()


@router.post("/{eval_id}/feedback")
def save_evaluation_feedback(eval_id: str, body: FeedbackRequest):
    """Save human feedback for an evaluation.

    The eval_id is used as the paper_id reference in the feedback table.
    """
    store = _get_store()

    # Build feedback content
    import json

    content = json.dumps(
        {
            "eval_id": eval_id,
            "score_override": body.score_override,
            "note": body.note,
            "flagged": body.flagged,
        }
    )

    row_id = store.save_feedback(
        cycle_id="",
        paper_id=eval_id,
        source="human_api",
        content=content,
    )

    return {"id": row_id, "status": "saved"}
