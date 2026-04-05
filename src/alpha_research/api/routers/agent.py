"""Agent run and SSE streaming endpoints."""

from __future__ import annotations

import asyncio
import json
import time
import traceback
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from sse_starlette.sse import EventSourceResponse

from alpha_research.api.models import AgentRunRequest, AgentStatusResponse

router = APIRouter(prefix="/api/agent", tags=["agent"])

# ---------------------------------------------------------------------------
# Shared state  (module-level singleton; fine for a single-process server)
# ---------------------------------------------------------------------------

_agent_state: dict[str, Any] = {
    "state": "idle",
    "iteration": 0,
    "mode": None,
    "question": None,
    "started_at": None,
    "task": None,
}

_event_queue: asyncio.Queue | None = None


def _ensure_queue() -> asyncio.Queue:
    global _event_queue
    if _event_queue is None:
        _event_queue = asyncio.Queue()
    return _event_queue


async def _emit(event_type: str, data: dict[str, Any] | None = None) -> None:
    """Push an event onto the SSE queue."""
    q = _ensure_queue()
    await q.put({"type": event_type, "data": data or {}})


# ---------------------------------------------------------------------------
# Background task
# ---------------------------------------------------------------------------

async def _run_agent(request: AgentRunRequest) -> None:
    """Execute a research cycle in the background, emitting SSE events."""
    import os

    # NOTE (R6 refactor, 2026-04-05): the previous implementation instantiated
    # ``alpha_research.agents.research_agent.ResearchAgent`` directly. The
    # agents/ package has been deleted; research workflows now run through
    # ``alpha_research.pipelines.literature_survey.run_literature_survey`` or
    # ``alpha_research.pipelines.research_review_loop.run_research_review_loop``.
    # This endpoint is web-UI-only and has not yet been migrated to the pipeline
    # entry points — it returns a structured "not-yet-implemented" response so
    # the frontend continues to load.
    try:
        _agent_state.update(
            state="running",
            iteration=0,
            mode=request.mode,
            question=request.question,
            started_at=datetime.now(),
        )

        await _emit("step_started", {"step": "init", "metadata": {"mode": request.mode}})
        await _emit("step_finished", {"step": "init", "duration_ms": 0})

        t0 = time.time()
        _agent_state["iteration"] = 1
        await _emit("step_started", {"step": "search", "metadata": {"question": request.question}})
        await _emit(
            "activity",
            {
                "step": "search",
                "message": (
                    "Agent API endpoint is pending migration to the new "
                    "pipelines (post-R6 refactor). Use the CLI "
                    "`alpha-research survey ...` or "
                    "`alpha-research evaluate ...` meanwhile."
                ),
                "progress": 0.0,
            },
        )

        duration_ms = int((time.time() - t0) * 1000)
        await _emit(
            "step_finished",
            {"step": "search", "duration_ms": duration_ms},
        )
        await _emit(
            "run_finished",
            {
                "status": "not_implemented",
                "detail": "Agent API is pending pipeline migration",
            },
        )

        _agent_state["state"] = "idle"

    except Exception as exc:
        await _emit("error", {"message": str(exc), "traceback": traceback.format_exc()})
        _agent_state["state"] = "error"


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/run")
async def start_agent_run(body: AgentRunRequest):
    """Start a research cycle in the background."""
    if _agent_state["state"] == "running":
        raise HTTPException(status_code=409, detail="Agent is already running")

    # Reset the queue so old events don't leak
    global _event_queue
    _event_queue = asyncio.Queue()

    task = asyncio.create_task(_run_agent(body))
    _agent_state["task"] = task

    return {"status": "started", "mode": body.mode, "question": body.question}


@router.get("/status", response_model=AgentStatusResponse)
def agent_status():
    """Current agent state."""
    return AgentStatusResponse(
        state=_agent_state["state"],
        iteration=_agent_state["iteration"],
        mode=_agent_state["mode"],
        question=_agent_state["question"],
        started_at=_agent_state["started_at"],
    )


@router.get("/stream")
async def agent_stream():
    """SSE endpoint that streams agent events."""
    q = _ensure_queue()

    async def event_generator():
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                # Send keepalive comment
                yield {"event": "ping", "data": ""}
                continue

            payload = json.dumps(event)
            yield {"event": "message", "data": payload}

            # Stop streaming after terminal events
            if event.get("type") in ("run_finished", "error"):
                break

    return EventSourceResponse(event_generator())
