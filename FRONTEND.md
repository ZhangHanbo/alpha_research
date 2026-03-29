# Alpha Research — Frontend Plan

## Open-Source Landscape Review

We reviewed 7 open-source projects and 6 commercial products. Here's the honest assessment:

### Projects Evaluated (with quality verdicts)

| Project | Stars | License | Frontend Quality | Verdict |
|---------|-------|---------|-----------------|---------|
| **GPT Researcher** | 26k | Apache 2.0 | Poor (2/10) | Don't fork. 900-line monolithic page.tsx, `any` types everywhere, no WebSocket reconnection, multiple open XSS/RCE vulnerabilities, frontend issues stay open 12+ months. **Study the UX concepts only.** |
| **STORM** (Stanford) | 28k | MIT | Throwaway (1/10) | Don't fork. Streamlit demo, no error handling, hardcoded model, 6 months stale, 2 contributors, open TLS vulnerability with no maintainer response. **Study the mind map data structure.** |
| **Khoj** | 33k | **AGPL-3.0** | Moderate (5/10) | Don't fork. AGPL forces open-sourcing any network-deployed modification. 1,251-line chatMessage.tsx, no API abstraction, 8-13 days refactoring to adapt. **Reference shadcn/ui component patterns.** |
| **LangGraph Agent Studio** | 56 | Apache 2.0 | Low (3/10) | Don't fork. 1 contributor, abandoned 9 months, uses `window.location.reload()` as state management, deeply LangGraph-coupled. **Study the ActivityTimeline pattern (~130 lines).** |
| **CopilotKit** | 30k | MIT | High (8/10) | **Use as framework.** Production-grade React components, AG-UI protocol connects to custom backends, generative UI supports structured data (tables, graphs) alongside chat. Python SDK is pre-1.0 but AG-UI event spec is stable. |
| **AutoGen Studio** | 56k (repo) | MIT | Low | Don't use. Gatsby-based, "research prototype not intended for production." |
| **Langfuse** | 24k | MIT | High | Wrong tool — observability/tracing, not agent interaction UI. Could add later for debugging. |

### Decision: CopilotKit as Framework + Custom Views

**Why not fork any existing project:**
Every frontend we reviewed is either (a) code quality too low to build on (GPT Researcher, STORM, LangGraph Studio), (b) license-problematic (Khoj/AGPL), or (c) wrong tool for the job (Langfuse, AutoGen). The refactoring cost exceeds building clean from scratch in every case.

**Why CopilotKit:**
- Provides the hard parts: real-time agent streaming (AG-UI protocol), chat UI, generative UI (agent invokes React components with structured data), human-in-the-loop hooks
- MIT license, 30k stars, active development, 86k weekly npm downloads
- AG-UI protocol explicitly supports custom Python backends without LangGraph
- Leaves us free to build the research-specific views (evaluation table, knowledge graph) as custom components that CopilotKit's agent can invoke

**What we borrow (ideas, not code) from others:**
- **Elicit**: Table-based paper evaluation UI — papers as rows, rubric dimensions as columns, click-to-expand evidence
- **Connected Papers**: Force-directed knowledge graph — node size = score, color = approach type, edges = relation type
- **GPT Researcher**: Real-time streaming progress pattern (search → filter → evaluate → synthesize)
- **STORM Co-STORM**: Progressive mind map that grows during research
- **LangGraph Studio**: ActivityTimeline event pattern (`{title, data}` array → vertical timeline with icons)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js + CopilotKit)           │
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ Agent Activity│  │  Evaluation  │  │  Knowledge Graph  │  │
│  │   Timeline    │  │    Table     │  │   (Cytoscape.js)  │  │
│  │  (CopilotKit  │  │  (shadcn +   │  │                   │  │
│  │   generative  │  │  custom)     │  │                   │  │
│  │   UI)         │  │              │  │                   │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬──────────┘  │
│         │                 │                    │              │
│         └─────────────────┼────────────────────┘              │
│                           │                                   │
│              CopilotKit useAgent / AG-UI SSE                  │
└───────────────────────────┼───────────────────────────────────┘
                            │ SSE (Server-Sent Events)
                            │ AG-UI Protocol events
┌───────────────────────────┼───────────────────────────────────┐
│                    Backend (FastAPI)                           │
│                                                               │
│  ┌────────────────────────┐   ┌────────────────────────────┐  │
│  │   AG-UI Adapter Layer  │   │    REST API                │  │
│  │   (~200 lines)         │   │    /papers, /evaluations,  │  │
│  │                        │   │    /knowledge, /reports     │  │
│  │   Translates agent     │   │                            │  │
│  │   events → AG-UI       │   │    Direct DB queries for   │  │
│  │   SSE events           │   │    table/graph views       │  │
│  └───────────┬────────────┘   └────────────┬───────────────┘  │
│              │                              │                  │
│              ▼                              ▼                  │
│  ┌─────────────────────┐       ┌───────────────────────┐      │
│  │  Claude Agent SDK   │       │   SQLite Knowledge    │      │
│  │  (existing agent)   │       │   Store (existing)    │      │
│  └─────────────────────┘       └───────────────────────┘      │
└───────────────────────────────────────────────────────────────┘
```

### Two Communication Channels

1. **AG-UI SSE stream** — Real-time agent activity. When the agent runs (digest, deep, survey, etc.), the backend streams AG-UI events: `StepStarted/Finished` for each SM stage, `ActivityDelta` for progress within stages, `TextMessageChunk` for agent reasoning, tool call events for each tool invocation. CopilotKit renders these as the activity timeline + chat.

2. **REST API** — Structured data queries. The evaluation table and knowledge graph don't come from the agent stream — they query the knowledge store directly. This separates "agent is working" (streaming) from "show me what's stored" (REST).

---

## Tech Stack

| Component | Choice | Why |
|-----------|--------|-----|
| Framework | **Next.js 15** | Static export, API proxy in dev, proven with CopilotKit |
| Agent UI | **CopilotKit** (`@copilotkit/react-core`, `@copilotkit/react-ui`) | Streaming, generative UI, human-in-the-loop |
| UI primitives | **shadcn/ui + Radix UI** | Accessible, composable, CopilotKit-compatible |
| Styling | **Tailwind CSS 4** | Standard |
| Data table | **TanStack Table** | Sorting, filtering, column visibility for rubric scores |
| Graph viz | **Cytoscape.js** (`react-cytoscapejs`) | Mature, handles relationship types from SM-4 |
| State | **Zustand** | Lightweight, avoids the useState cascade problem seen in Khoj/GPT Researcher |
| Backend bridge | **FastAPI** | Same Python stack, AG-UI SSE + REST endpoints |
| AG-UI adapter | **`ag_ui.core` + `ag_ui.encoder`** | Framework-agnostic AG-UI event primitives |
| Build | **Vite** (via Next.js) or standalone Vite | Fast dev builds |

---

## The Three Key Views

### View 1: Agent Activity Panel (left sidebar)

Shows real-time agent progress during a research cycle.

```
┌─ Agent Activity ─────────────────────────┐
│                                          │
│ Mode: survey │ Stage: DIAGNOSE │ Cycle: 2│
│                                          │
│ ✓ SM-1: Search                    [12s]  │
│   ├─ ArXiv query: "tactile manip..."     │
│   ├─ 47 papers found                     │
│   ├─ Expanded: citation graph (+12)      │
│   └─ Converged: 53 papers total          │
│                                          │
│ ✓ SM-2: Paper Processing          [34s]  │
│   ├─ 48/53 extracted (5 failed)          │
│   └─ Quality: 39 high, 9 medium          │
│                                          │
│ ▶ SM-3: Evaluation                [...]  │
│   ├─ Skimmed: 48/48                      │
│   ├─ Deep reading: 15/22 relevant        │
│   └─ Evaluating: 8/15...                 │
│     └─ "Contact-Implicit MPC for..."     │
│        Rubric: ████░░ 4/7 dimensions     │
│                                          │
│ ○ SM-4: Knowledge Store (pending)        │
│ ○ SM-5: Report Generation (pending)      │
│                                          │
│ ⟲ Backward transitions: 1               │
│   SM-3→SM-1: gap found (no TAMP papers)  │
│                                          │
│ [Stop] [Pause]                           │
└──────────────────────────────────────────┘
```

**Implementation:** CopilotKit `StepStarted/StepFinished` events map to SM stages. `ActivityDelta` events update progress within each step. The backend emits these as the Claude Agent SDK agent calls tools.

### View 2: Evaluation Table (main content area)

Elicit-inspired table for reviewing paper evaluations.

```
┌─ Evaluations ─────────────────────────────────────────────────────────────────────┐
│ Filter: [mode ▼] [score ≥ ▼] [human flags only ☐] [cycle ▼]    Search: [______]  │
│                                                                                    │
│ ┌──────────────────┬─────┬──────┬──────┬──────┬──────┬──────┬──────┬─────────────┐│
│ │ Paper            │ Sig │ Form │ Tech │Rigor │ Rep  │ Gen  │ Prac │ Flags       ││
│ ├──────────────────┼─────┼──────┼──────┼──────┼──────┼──────┼──────┼─────────────┤│
│ │▸ Diffusion Pol...│ 4▲  │ 3●   │ 4▲   │ 2▼   │ 4●   │ 2●   │ 3●   │ ⚠ signif.  ││
│ │▸ Tactile Inse...│ 3●  │ 5▲   │ 4▲   │ 4●   │ 3●   │ 3●   │ 4●   │ ⚠ math     ││
│ │▾ VLA for Mobi...│ 2▼  │ 1▼   │ 3●   │ 3●   │ 2●   │ 2●   │ 2▼   │ ⚠ no form. ││
│ │  ┌──────────────────────────────────────────────────────────────────────────┐  ││
│ │  │ Significance (2/5, low confidence)                                       │  ││
│ │  │ Evidence: "We propose a VLA for mobile manipulation" — no consequence    │  ││
│ │  │ test, no durability argument. Paper skips significance entirely.         │  ││
│ │  │ ⚠ HUMAN JUDGMENT REQUIRED: Is this problem on your Hamming list?        │  ││
│ │  │                                                                          │  ││
│ │  │ Formalization (1/5, high confidence)                                     │  ││
│ │  │ Evidence: No formal problem statement found. Method described in prose.  │  ││
│ │  │ "Per guidelines §2.4: if you can't write the math, you don't            │  ││
│ │  │ understand the problem."                                                 │  ││
│ │  │                                                                          │  ││
│ │  │ [✓ Reviewed] [Override Score ▼] [Add Note] [Flag for Follow-up]         │  ││
│ │  └──────────────────────────────────────────────────────────────────────────┘  ││
│ └──────────────────────────────────────────────────────────────────────────────────┘│
└────────────────────────────────────────────────────────────────────────────────────┘
```

**Implementation:** TanStack Table with custom cell renderers. Expandable rows show per-dimension evidence, reasoning, and confidence. Human feedback buttons write to the `feedback` table in the knowledge store via REST API.

### View 3: Knowledge Graph (togglable overlay / separate tab)

Force-directed graph from SM-4's `paper_relations` table.

```
┌─ Knowledge Graph ──────────────────────────────────────────┐
│                                                            │
│ Layout: [force ▼]  Color: [approach ▼]  Filter: [cycle ▼] │
│                                                            │
│            ○ CQL                                           │
│           ╱  ╲                                             │
│      ○───○    ○ Conservative RL                            │
│     ╱   DiffPol ╲                                          │
│    ○              ◉ ← Tactile Insertion (selected)         │
│   TAMP         ╱  ╲                                        │
│    ╲          ○    ○ GelSight Assembly                     │
│     ○───────╱                                              │
│    Contact-MPC                                             │
│                                                            │
│ ── extends   ╌╌ same_task   ── contradicts (red)           │
│ Node size = overall score  Color = approach type           │
│                                                            │
│ Selected: "Tactile Insertion with Sub-mm Alignment"        │
│ Score: 4.2  │  Approach: tactile sensing  │  2026          │
│ Relations: extends [GelSight'24], same_task [Assembly'25]  │
│ [Open Evaluation] [Open Paper]                             │
└────────────────────────────────────────────────────────────┘
```

**Implementation:** `react-cytoscapejs` with `cose-bilkent` layout. Node/edge data from REST API querying `papers` + `paper_relations` tables. Click events open the evaluation detail panel.

---

## Multi-Agent Implementation Plan

The frontend work is split across specialized agents working in parallel where possible. Dependencies between agents are marked explicitly.

```
                    ┌──────────────┐
                    │  AGENT 0     │
                    │  Plan Review │  ← YOU ARE HERE
                    │  (human)     │
                    └──────┬───────┘
                           │ approved
              ┌────────────┼────────────┐
              ▼            ▼            ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ AGENT 1  │  │ AGENT 2  │  │ AGENT 3  │
      │ Scaffold │  │ Backend  │  │ CopilotKit│
      │ + Config │  │ API      │  │ Research  │
      └─────┬────┘  └─────┬────┘  └─────┬────┘
            │              │             │
            ▼              ▼             ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ AGENT 4  │  │ AGENT 5  │  │ AGENT 6  │
      │ Eval     │  │ AG-UI    │  │ Agent    │
      │ Table    │  │ Adapter  │  │ Activity  │
      └─────┬────┘  └─────┬────┘  └─────┬────┘
            │              │             │
            └──────────────┼─────────────┘
                           ▼
                    ┌──────────┐
                    │ AGENT 7  │
                    │ Knowledge│
                    │ Graph    │
                    └─────┬────┘
                          ▼
                    ┌──────────┐
                    │ AGENT 8  │
                    │ Integrate│
                    │ + Polish │
                    └─────┬────┘
                          ▼
                    ┌──────────┐
                    │ AGENT 9  │
                    │ Test +   │
                    │ Review   │
                    └──────────┘
```

### Agent 0: Plan Review (Human)

**You review this plan.** Approve, modify, or reject before any code is written.

### Agent 1: Project Scaffold + Configuration

**Depends on:** Agent 0 (approval)
**Parallel with:** Agents 2, 3

**Tasks:**
1. Initialize Next.js 15 project with TypeScript strict mode
2. Install and configure: CopilotKit, shadcn/ui, Tailwind CSS 4, Zustand, TanStack Table, react-cytoscapejs
3. Set up project structure:
   ```
   frontend/
   ├── package.json
   ├── next.config.mjs          # static export, API proxy to FastAPI
   ├── tsconfig.json             # strict: true
   ├── tailwind.config.ts
   ├── src/
   │   ├── app/
   │   │   ├── layout.tsx        # CopilotKit provider, Zustand provider
   │   │   ├── page.tsx          # Main dashboard layout (3-panel)
   │   │   └── globals.css
   │   ├── components/
   │   │   ├── ui/               # shadcn/ui primitives (button, table, badge, etc.)
   │   │   ├── activity/         # Agent activity timeline components
   │   │   ├── evaluation/       # Paper evaluation table components
   │   │   ├── graph/            # Knowledge graph components
   │   │   └── layout/           # Dashboard shell, panels, navigation
   │   ├── hooks/
   │   │   ├── use-agent-stream.ts    # CopilotKit AG-UI hook wrapper
   │   │   ├── use-evaluations.ts     # REST API hook for evaluations
   │   │   ├── use-knowledge-graph.ts # REST API hook for graph data
   │   │   └── use-research-store.ts  # Zustand store
   │   ├── lib/
   │   │   ├── api.ts            # Centralized API client (no scattered fetch!)
   │   │   ├── types.ts          # All TypeScript types (mirroring backend Pydantic models)
   │   │   └── utils.ts
   │   └── styles/
   ```
4. Configure ESLint with strict rules (no `any`, import ordering, complexity limits)
5. Add shadcn/ui primitives: button, table, badge, collapsible, tabs, tooltip, dialog, scroll-area, select

**Output:** Buildable skeleton that renders an empty 3-panel dashboard layout.

### Agent 2: Backend REST API

**Depends on:** Agent 0 (approval)
**Parallel with:** Agents 1, 3

**Tasks:**
1. Create `src/alpha_research/api/` directory with FastAPI app
2. Implement REST endpoints:
   ```python
   # Papers + Evaluations
   GET  /api/papers                    # list papers, filterable by cycle/topic/score
   GET  /api/papers/{id}               # single paper with full text
   GET  /api/papers/{id}/evaluation    # full evaluation with rubric scores

   # Evaluations (for the table view)
   GET  /api/evaluations               # list evaluations with filters
   POST /api/evaluations/{id}/feedback # human feedback on a score

   # Knowledge graph
   GET  /api/graph/nodes               # papers as nodes (id, title, score, approach_type)
   GET  /api/graph/edges               # paper_relations as edges (source, target, type)

   # Agent
   POST /api/agent/run                 # start a research cycle (mode, question)
   GET  /api/agent/status              # current agent state
   ```
3. All endpoints query existing SQLite knowledge store (`knowledge/store.py`)
4. Add CORS middleware for frontend dev server
5. Pydantic response models mirroring the frontend TypeScript types

**Output:** Running FastAPI server with all endpoints returning data from knowledge store.

### Agent 3: CopilotKit Integration Research

**Depends on:** Agent 0 (approval)
**Parallel with:** Agents 1, 2

**Tasks:**
1. Clone CopilotKit's example repos, specifically the "Research Canvas" tutorial
2. Build a minimal proof-of-concept: CopilotKit frontend → AG-UI SSE → FastAPI backend → dummy agent that emits step events
3. Verify: `StepStarted/StepFinished` events render in the CopilotKit UI
4. Verify: `useFrontendTool` can render a custom React component (e.g., a simple table)
5. Verify: Human-in-the-loop hook works (agent pauses, user confirms)
6. Document findings: what works, what doesn't, any CopilotKit limitations discovered
7. If CopilotKit AG-UI integration proves unreliable for our custom backend (given the known event routing issues #3519), document a **fallback plan**: raw SSE + custom React hooks (no CopilotKit dependency)

**Output:** Working PoC + written assessment of CopilotKit viability. Go/no-go decision for Agents 4-6.

### Agent 4: Evaluation Table View

**Depends on:** Agent 1 (scaffold), Agent 2 (REST API)
**Parallel with:** Agents 5, 6

**Tasks:**
1. Build `EvaluationTable` component using TanStack Table + shadcn/ui table primitive
2. Columns: paper title, 7 rubric dimensions (Sig, Form, Tech, Rigor, Rep, Gen, Prac), human flags
3. Each cell renders: score (1-5) + confidence indicator (▲ high, ● medium, ▼ low)
4. Expandable rows: clicking a paper expands to show per-dimension evidence, reasoning, and quotes
5. Human feedback: "Reviewed" checkbox, score override dropdown, note textarea, flag button
6. Filters: by mode, minimum score, human-flags-only, cycle
7. Sorting on any column
8. Hook: `useEvaluations()` that calls REST API with filter params
9. Color coding: red for scores 1-2, yellow for 3, green for 4-5

**Output:** Fully functional evaluation table that renders real data from the knowledge store.

### Agent 5: AG-UI Adapter for Claude Agent SDK

**Depends on:** Agent 3 (CopilotKit PoC confirms viability)
**Parallel with:** Agents 4, 6

**Tasks:**
1. Create `src/alpha_research/api/agui_adapter.py`
2. Implement AG-UI SSE endpoint at `POST /api/agent/stream`
3. Map agent events to AG-UI protocol:
   ```python
   # SM-1 Search stage → StepStarted("search", metadata={...})
   # Tool call (arxiv_search) → ToolCallChunkEvent
   # Papers found → ActivityDelta with count
   # SM-1 complete → StepFinished("search")

   # SM-3 Evaluation → StepStarted("evaluate")
   # Per-paper evaluation → ActivityDelta with paper title + progress
   # Rubric complete → ToolCallResult with structured evaluation data
   # → triggers useFrontendTool to render EvaluationTable row

   # Backward transition → custom ActivityDelta with backward flag
   ```
4. Handle agent lifecycle: `RunStartedEvent`, `RunFinishedEvent`, error events
5. Wire into existing `agent.py` — intercept tool calls and agent state transitions
6. Test with CopilotKit frontend from Agent 3 PoC

**Output:** Working streaming pipeline: Claude Agent SDK → AG-UI events → CopilotKit frontend.

### Agent 6: Agent Activity Timeline

**Depends on:** Agent 1 (scaffold), Agent 3 (CopilotKit PoC)
**Parallel with:** Agents 4, 5

**Tasks:**
1. Build `ActivityTimeline` component that renders AG-UI step events
2. Each SM stage (SM-1 through SM-5) renders as a collapsible section:
   - Header: stage name, status icon (✓ done, ▶ running, ○ pending), elapsed time
   - Body: sub-events (queries executed, papers found, evaluation progress)
3. Backward transitions render as highlighted entries with explanation
4. Overall progress bar showing stage completion
5. Mode/cycle indicator at the top
6. Stop/pause controls that send signals to backend
7. Auto-scroll to current activity

**Output:** Real-time activity sidebar that shows agent progress during research cycles.

### Agent 7: Knowledge Graph View

**Depends on:** Agent 1 (scaffold), Agent 2 (REST API)
**Sequential after:** Agents 4-6 (lower priority — useful after 50+ papers accumulated)

**Tasks:**
1. Build `KnowledgeGraph` component using `react-cytoscapejs`
2. Load nodes from `GET /api/graph/nodes`, edges from `GET /api/graph/edges`
3. Node rendering: size = overall score, color = approach type (from constitution categories)
4. Edge rendering: solid = extends, dashed = same_task, red dashed = contradicts
5. Layout: `cose-bilkent` (force-directed, good for clustered graphs)
6. Interaction: click node → show paper info card, double-click → open evaluation detail
7. Filters: by cycle, approach type, minimum score
8. Color legend and edge type legend
9. Optional: time slider to animate graph growth across cycles

**Output:** Interactive knowledge graph visualization.

### Agent 8: Integration + Dashboard Layout

**Depends on:** Agents 4, 5, 6, 7

**Tasks:**
1. Assemble the 3-panel dashboard layout:
   - Left panel (resizable): Agent Activity Timeline
   - Center panel: Evaluation Table (default) or Knowledge Graph (tab)
   - Top bar: mode selector, question input, cycle picker
2. Wire CopilotKit provider with AG-UI endpoint
3. State coordination via Zustand store:
   - Agent running state → disable new runs, show activity panel
   - New evaluation arrives → table auto-updates, graph adds node
   - Human feedback submitted → table cell updates, feedback stored
4. Responsive layout (collapse activity panel on small screens)
5. Dark/light theme via shadcn/ui theme provider
6. Error boundaries around each panel (one panel crashing doesn't kill the app)
7. Loading states and empty states for all views

**Output:** Complete, integrated dashboard.

### Agent 9: Test + Quality Review

**Depends on:** Agent 8

**Tasks:**
1. End-to-end test: start a `digest` mode run → verify activity timeline streams → verify evaluation table populates
2. End-to-end test: start a `deep` mode run on a known paper → verify full evaluation renders with expandable evidence
3. Human feedback test: override a score → verify it persists to knowledge store
4. Knowledge graph test: load graph with 10+ papers → verify layout, click interactions, edge types
5. Error handling test: kill backend mid-stream → verify graceful degradation (not blank screen)
6. Code quality review: no `any` types, no monolithic components (max 200 lines each), centralized API client, proper TypeScript interfaces
7. Performance: table with 100+ papers renders without lag, graph with 50+ nodes is interactive
8. Accessibility: keyboard navigation through table, proper ARIA labels on graph

**Output:** Quality report with pass/fail per criterion, list of issues to fix.

---

## Build Order and Dependencies (Summary)

```
Phase 0:  Human reviews this plan                         [YOU]
Phase 1:  Agents 1 + 2 + 3 in parallel                   [scaffold + API + CopilotKit PoC]
          ↓ go/no-go on CopilotKit from Agent 3
Phase 2:  Agents 4 + 5 + 6 in parallel                   [table + adapter + timeline]
Phase 3:  Agent 7                                          [knowledge graph]
Phase 4:  Agent 8                                          [integration]
Phase 5:  Agent 9                                          [test + review]
```

**Total estimated phases:** 5 phases after approval. Phases 1 and 2 each have 3 agents running in parallel.

---

## Fallback Plan

If CopilotKit's AG-UI integration proves unreliable for our custom Claude Agent SDK backend (Agent 3 PoC fails):

1. **Drop CopilotKit.** Use the same tech stack (Next.js + shadcn/ui + Tailwind) but without CopilotKit.
2. **Replace AG-UI with raw SSE.** FastAPI `StreamingResponse` → custom `useEventSource` React hook.
3. **Build streaming UI manually.** The activity timeline and progress events are straightforward to render from raw SSE events — CopilotKit saves perhaps 2-3 days of work here, not weeks.
4. **Keep everything else the same.** The evaluation table, knowledge graph, REST API, and Zustand store are CopilotKit-independent.

The fallback adds ~3 days of work (SSE hook + manual streaming UI) but removes a dependency risk. Agent 3's PoC is specifically designed to make this go/no-go decision early.

---

## What This Plan Explicitly Does NOT Include

- **Chat interface.** The agent is not a chatbot. It runs research cycles and produces structured output. The activity timeline shows what it's doing; the evaluation table shows what it found. No freeform chat.
- **Mobile responsiveness.** This is a researcher's desktop tool. Tablet/phone layouts are out of scope.
- **User authentication.** Single-user tool. No login, no multi-tenancy.
- **Deployment/hosting.** Runs locally (`npm run dev` + `uvicorn`). No Docker, no cloud deploy.
- **The knowledge graph time-slider animation.** Listed as optional in Agent 7. Only build if graph view proves useful with real data.
