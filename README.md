# Alpha Research

A multi-agent system for automated research paper discovery, evaluation, and
adversarial review in robotics.

Three LLM-powered agents collaborate through a shared blackboard: a
**Research Agent** that searches and evaluates papers, a **Review Agent**
that adversarially critiques research artifacts calibrated to specific
venues (RSS, IJRR, CoRL, etc.), and a **Meta-Reviewer** that
quality-checks reviews against quantitative thresholds. An
**Orchestrator** drives the loop until convergence. A **web dashboard**
provides real-time monitoring with an evaluation table, activity
timeline, and knowledge graph.


## Quick Start

### 1. Install

```bash
conda create -n alpha_research python=3.11 -y
conda activate alpha_research
conda install -c conda-forge nodejs=20 -y

# Install backend
pip install -e ".[dev]"
pip install fastapi uvicorn sse-starlette

# Install frontend
cd frontend && npm install && cd ..
```

### 2. Set your API key (optional — needed for LLM features)

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Without a key, the system still runs search, paper fetching, and report
generation — it just skips LLM-based evaluation and review.

### 3. Run a research task (CLI)

```bash
# Search ArXiv and produce a digest of recent papers on a topic
alpha-research research "tactile manipulation for deformable objects" --mode digest

# Fetch and analyze a single paper by ArXiv ID
alpha-research research "2401.12345" --mode deep
```

Output prints to stdout and saves to `output/reports/`.

### 4. Launch the web dashboard to monitor tasks

Open two terminals:

**Terminal 1 — Backend API:**

```bash
conda activate alpha_research
uvicorn alpha_research.api.app:app --port 8000 --reload
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

Open **http://localhost:3000**. The dashboard shows three views:

- **Evaluation Table** — papers as rows, rubric scores as columns,
  click to expand evidence
- **Activity Timeline** (left sidebar) — real-time agent progress
  when a research run is active
- **Knowledge Graph** — force-directed visualization of paper
  relationships

To start a run from the dashboard, type a research question in the top
bar, choose a mode and venue, and click **Run**.

### 5. Run the full adversarial research-review loop (requires API key)

```bash
alpha-research loop "contact-rich manipulation under uncertainty" --venue RSS
```

The orchestrator will prompt for human input at checkpoints. The
blackboard saves to `data/blackboard.json`.


## CLI Reference

```
alpha-research research <question> [--mode digest|deep|survey] [--api-key KEY] [--model MODEL]
alpha-research review <artifact.md> [--venue RSS|IJRR|...] [--api-key KEY]
alpha-research loop <question> [--venue RSS] [--max-iterations 5] [--api-key KEY]
alpha-research status
```

**Venues** (strictest to most lenient): IJRR, T-RO, RSS, CoRL, RA-L, ICRA, IROS.


## Project Structure

```
alpha_research/
├── config/
│   ├── constitution.yaml          # Research agent domain focus
│   └── review_config.yaml         # Review thresholds, pressure schedule
│
├── src/alpha_research/
│   ├── models/                    # Pydantic V2 data models
│   │   ├── research.py            #   Paper, Evaluation, TaskChain, ...
│   │   ├── review.py              #   Finding, Review, Verdict, ...
│   │   ├── blackboard.py          #   Blackboard, ResearchArtifact, Venue
│   │   ├── project.py             #   ProjectManifest, ProjectState, SourceBinding
│   │   └── snapshot.py            #   SourceSnapshot, ProjectSnapshot, ResearchRun
│   │
│   ├── knowledge/                 # SQLite persistent storage
│   │   ├── schema.py              #   8-table schema
│   │   └── store.py               #   KnowledgeStore CRUD
│   │
│   ├── tools/                     # Shared agent toolset
│   │   ├── arxiv_search.py        #   ArXiv search
│   │   ├── paper_fetch.py         #   PDF download + text extraction
│   │   ├── semantic_scholar.py    #   S2 API: metadata, citations
│   │   ├── knowledge.py           #   Agent-facing store interface
│   │   └── report.py              #   Jinja2 report generation
│   │
│   ├── prompts/                   # System prompt builders
│   │   ├── research_system.py     #   Research agent prompt
│   │   ├── review_system.py       #   Review agent prompt
│   │   ├── meta_review_system.py  #   Meta-reviewer prompt
│   │   ├── understanding_system.py#   Understanding agent prompt
│   │   └── rubric.py              #   Shared rubric text
│   │
│   ├── agents/                    # Agent implementations
│   │   ├── research_agent.py      #   Generate/revise artifacts
│   │   ├── review_agent.py        #   Three-pass review, verdict
│   │   ├── meta_reviewer.py       #   Review quality checks
│   │   └── orchestrator.py        #   Research-review loop
│   │
│   ├── projects/                  # Project lifecycle layer
│   │   ├── understanding.py       #   Understanding agent
│   │   └── ...                    #   Registry, git state, snapshots, resume
│   │
│   ├── metrics/                   # Pure-Python metrics
│   │   ├── review_quality.py      #   Actionability, grounding, anti-patterns
│   │   ├── convergence.py         #   Convergence, stagnation detection
│   │   └── finding_tracker.py     #   Cross-iteration finding tracking
│   │
│   ├── api/                       # FastAPI backend
│   │   ├── app.py                 #   CORS, routers, startup
│   │   ├── models.py              #   API response models
│   │   └── routers/               #   papers, evaluations, graph, agent
│   │
│   ├── config.py                  # YAML config loaders
│   ├── llm.py                     # Anthropic API client wrapper
│   └── main.py                    # Typer CLI entry point
│
├── frontend/                      # Next.js 15 web dashboard
│   └── src/
│       ├── app/page.tsx           #   3-panel dashboard
│       ├── components/
│       │   ├── evaluation/        #   TanStack Table with rubric scores
│       │   ├── activity/          #   SSE-powered activity timeline
│       │   ├── graph/             #   Cytoscape.js knowledge graph
│       │   └── layout/            #   Dashboard shell
│       ├── hooks/                 #   Zustand store, SSE, REST hooks
│       └── lib/                   #   API client, TypeScript types
│
└── tests/                         # 472 tests
```

### Architecture

```
Frontend (Next.js)                     Backend (FastAPI)
┌────────────────────┐                ┌────────────────────────┐
│ Evaluation Table   │──── REST ────▶│ /api/papers            │
│ Knowledge Graph    │──── REST ────▶│ /api/graph             │
│ Activity Timeline  │──── SSE ─────▶│ /api/agent/stream      │
│ Run Controls       │──── POST ────▶│ /api/agent/run         │
└────────────────────┘                └──────────┬─────────────┘
                                                 │
                                      ┌──────────▼─────────────┐
                                      │ Orchestrator           │
                                      │  ├── Research Agent    │
                                      │  ├── Review Agent      │
                                      │  └── Meta-Reviewer     │
                                      └──────────┬─────────────┘
                                                 │
                                      ┌──────────▼─────────────┐
                                      │ Knowledge Store        │
                                      │ (SQLite)               │
                                      └────────────────────────┘
```


## Configuration

### `config/constitution.yaml` — Research agent domain focus

```yaml
name: "Robotics Research"
focus_areas:
  - "mobile manipulation"
  - "contact-rich manipulation"
  - "tactile sensing and feedback"
max_papers_per_cycle: 50
```

### `config/review_config.yaml` — Review loop behavior

```yaml
target_venue: "RSS"
max_iterations: 5
graduated_pressure:
  iteration_1: "structural_scan"
  iteration_2: "full_review"
  iteration_3_plus: "focused_rereview"
review_quality_thresholds:
  min_actionability: 0.80
  min_grounding: 0.90
  max_vague_critiques: 0
  min_falsifiability: 0.70
```


## Testing

```bash
# Run all tests (no network access or API keys needed)
python -m pytest tests/ -q

# Run with coverage
python -m pytest tests/ --cov=alpha_research --cov-report=term-missing
```


## Design Documents

- `work_plan.md` — Research agent architecture, state machines, build order
- `research_guideline.md` — Evaluation rubric, significance tests, formalization standards
- `review_guideline.md` — Attack vectors, review protocol, anti-patterns
- `review_plan.md` — Executable metrics, iteration protocol
- `FRONTEND.md` — Frontend architecture, three key views, tech stack decisions
- `project_lifecycle_revision_plan.md` — Project-oriented lifecycle layer design
