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

    from alpha_research.config import load_constitution
    from alpha_research.knowledge.store import KnowledgeStore

    try:
        _agent_state.update(
            state="running",
            iteration=0,
            mode=request.mode,
            question=request.question,
            started_at=datetime.now(),
        )

        await _emit("step_started", {"step": "init", "metadata": {"mode": request.mode}})

        # Initialise store and agent
        store = KnowledgeStore(db_path="data/knowledge.db")
        constitution = load_constitution("config/constitution.yaml")

        llm = None
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            from alpha_research.llm import AnthropicLLM

            llm = AnthropicLLM(api_key=api_key, model="claude-sonnet-4-20250514")

        from alpha_research.agents.research_agent import ResearchAgent

        agent = ResearchAgent(knowledge_store=store, config=constitution, llm=llm)

        await _emit("step_finished", {"step": "init", "duration_ms": 0})

        # --- Search phase ------------------------------------------------
        t0 = time.time()
        _agent_state["iteration"] = 1
        await _emit("step_started", {"step": "search", "metadata": {"question": request.question}})
        await _emit("activity", {"step": "search", "message": "Searching for papers...", "progress": 0.0})

        await _emit(
            "tool_call",
            {"tool": "arxiv_search", "args": {"query": request.question}},
        )

        # Run the actual agent mode
        if request.mode == "digest":
            if llm is not None:
                report = await agent.run_digest(request.question)
            else:
                report = f"[No LLM configured] Would run digest for: {request.question}"
        elif request.mode == "deep":
            if llm is not None:
                report = await agent.run_deep(request.question)
            else:
                report = f"[No LLM configured] Would run deep analysis for: {request.question}"
        else:
            report = f"Mode '{request.mode}' not yet implemented via API."

        duration_ms = int((time.time() - t0) * 1000)
        await _emit("tool_result", {"tool": "arxiv_search", "result_summary": f"Agent run completed ({duration_ms}ms)"})
        await _emit("step_finished", {"step": "search", "duration_ms": duration_ms})

        # --- Finished -----------------------------------------------------
        await _emit("activity", {"step": "search", "message": "Run complete", "progress": 1.0})
        await _emit("run_finished", {"status": "completed"})

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
