# Alpha Research

A **skills-first** research system for robotics paper discovery, evaluation,
and adversarial review.

**Architecture (post-R6 refactor, 2026-04-05):**

- **Skills** (`.claude/skills/*/SKILL.md`, currently staged in `skills/`) encode
  research- and review-guideline knowledge as Claude Code Agent Skills. 11
  skills cover paper evaluation (Appendix B rubric), significance screening
  (Hamming/Consequence/Durability/Compounding tests), formalization checking,
  empirical diagnosis, challenge articulation, experiment auditing,
  adversarial review at top-venue standard, concurrent work detection,
  gap analysis, and capability-frontier classification.
- **Python pipelines** (`src/alpha_research/pipelines/`) provide deterministic
  orchestration: literature-survey (wraps `alpha-review` CLI + paper-evaluate
  loop + synthesis), method-survey, frontier-mapping, and a
  research-review convergence loop.
- **alpha_review** (dependency at `../alpha_review`) provides all scholarly
  API clients (ArXiv, Semantic Scholar, OpenAlex, Google Scholar, Unpaywall),
  a SQLite-backed paper store, and the literature-survey-pipeline CLI
  `alpha-review`.
- **Claude Code skill invocation** drives all judgment-heavy work. Pipelines
  call skills via `claude -p`, which progressive-loads each skill when its
  description matches.

See `guidelines/tools_and_skills.md` for the architecture, `guidelines/refactor_plan.md`
for the migration history from the earlier agent-centric design, and
`guidelines/research_guideline.md` + `guidelines/review_guideline.md` for
the domain standards the skills encode.


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

The CLI surface (post-R6/R7 refactor):

```bash
# Full literature survey — wraps alpha-review CLI + paper-evaluate rubric loop
alpha-research survey "tactile manipulation for deformable objects" -o output/tactile

# Single-paper Appendix B rubric evaluation
alpha-research evaluate arxiv:2501.12345 -o output/single

# Adversarial review at top-venue standard
alpha-research review path/to/paper.md --venue RSS -o output/reviews

# Screen a candidate problem for significance (Hamming/Consequence/Durability/Compounding)
alpha-research significance "contact-rich manipulation under uncertainty"

# Run the full adversarial research-review convergence loop on a project
alpha-research loop output/tactile --venue RSS --max-iterations 5

# Summarize a project's JSONL records
alpha-research status output/tactile
```

Output is persisted as JSONL records (`evaluation.jsonl`, `review.jsonl`,
`finding.jsonl`, `frontier.jsonl`, etc.) under the project directory. The
`survey` command also produces a LaTeX survey + compiled PDF via
`alpha-review`'s `run_write` pipeline.

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

### 5. Run the full adversarial research-review loop (requires Claude CLI)

```bash
alpha-research loop output/my_project --venue RSS --max-iterations 5
```

The orchestrator will prompt for human input at checkpoints. The
blackboard saves to `data/blackboard.json`.


## CLI Reference

```
alpha-research survey       <query> -o <dir>                    # literature_survey pipeline
alpha-research evaluate     <paper_id> -o <dir>                 # paper-evaluate skill
alpha-research review       <artifact.md> --venue RSS -o <dir>  # adversarial-review skill
alpha-research significance <problem>                           # significance-screen skill
alpha-research loop         <project_dir> --venue RSS           # research_review_loop pipeline
alpha-research status       [<project_dir>]                     # summarize JSONL records

alpha-research project create|list|show|status|snapshot|resume  # project lifecycle
```

**Venues** (strictest to most lenient): IJRR, T-RO, RSS, CoRL, RA-L, ICRA, IROS.


## Project Structure

```
alpha_research/
├── .claude/skills/                # ACTIVE Claude Code skills (populated from skills/)
├── skills/                        # STAGING — 11 SKILL.md files pending review
│   ├── paper-evaluate/            #   Canonical rubric scoring (Sonnet)
│   ├── significance-screen/       #   Hamming/Consequence/Durability tests (Opus)
│   ├── formalization-check/       #   Math detection + sympy verify (Opus)
│   ├── diagnose-system/           #   Failure taxonomy + formal mapping (Sonnet)
│   ├── challenge-articulate/      #   Structural barrier ID (Opus)
│   ├── experiment-audit/          #   Stats + baselines + overclaiming (Sonnet)
│   ├── adversarial-review/        #   Full 6-attack-vector review (Opus, largest)
│   ├── concurrent-work-check/     #   Scoop detection (Sonnet)
│   ├── gap-analysis/              #   Semantic clustering (Opus)
│   ├── classify-capability/       #   Frontier tier assignment (Sonnet)
│   └── identify-method-gaps/      #   Method-class coverage gaps (Sonnet)
│
├── config/                        # YAML configs (constitution, review)
├── guidelines/                    # Doctrinal + plan documents
│   ├── research_guideline.md      #   Standards the skills encode
│   ├── review_guideline.md        #   Adversarial review standards
│   ├── research_plan.md           #   State machine + SM-1..SM-6 specs
│   ├── review_plan.md             #   Executable metrics
│   ├── tools_and_skills.md        #   Current architecture
│   ├── refactor_plan.md           #   R0-R9 migration plan
│   └── TASKS.md                   #   Task breakdown
│
├── scripts/                       # Helper CLIs called by skills
│   ├── sympy_verify.py            #   Mathematical property verification
│   └── audit_stats.py             #   Statistical audit
│
├── src/alpha_research/
│   ├── pipelines/                 # Deterministic Python orchestration
│   │   ├── state_machine.py       #   Pure functions: g1-g5, t2-t15
│   │   ├── literature_survey.py   #   alpha-review CLI + paper-evaluate loop
│   │   ├── method_survey.py       #   Search + graph + evaluate loop
│   │   ├── frontier_mapping.py    #   classify-capability loop + diff
│   │   └── research_review_loop.py#   Adversarial convergence loop
│   ├── records/
│   │   └── jsonl.py               #   append/read/count JSONL records
│   ├── metrics/
│   │   ├── verdict.py             #   Pure compute_verdict (per review_plan §1.9)
│   │   ├── review_quality.py      #   Actionability, grounding, anti-patterns
│   │   ├── convergence.py         #   Convergence, stagnation detection
│   │   └── finding_tracker.py     #   Cross-iteration finding tracking
│   ├── reports/
│   │   └── templates.py           #   DIGEST + DEEP rubric templates (Jinja2)
│   ├── models/                    # Pydantic data models
│   │   ├── research.py            #   Evaluation, TaskChain, RubricScore, ...
│   │   ├── review.py              #   Finding, Review, Verdict, ...
│   │   ├── blackboard.py          #   Blackboard, ResearchArtifact, Venue
│   │   ├── project.py             #   ProjectManifest, ProjectState
│   │   └── snapshot.py            #   SourceSnapshot, ProjectSnapshot
│   ├── tools/
│   │   └── paper_fetch.py         #   PDF download + pymupdf extraction
│   ├── projects/                  # Project lifecycle layer (KEEP)
│   │   ├── orchestrator.py        #   Project-level orchestration
│   │   ├── registry.py, resume.py, snapshots.py, ...
│   │   └── understanding.py       #   Project understanding (uses claude_call)
│   ├── api/                       # FastAPI backend (KEEP)
│   │   ├── app.py, models.py
│   │   └── routers/               #   papers, evaluations, graph, agent
│   ├── config.py                  # YAML config loaders
│   ├── llm.py                     # Anthropic API client wrapper
│   └── main.py                    # Typer CLI
│
├── frontend/                      # Next.js 15 web dashboard
└── tests/                         # 277 unit + 3 integration (opt-in)
```

**Note:** `src/alpha_research/agents/` and `src/alpha_research/prompts/` were
removed in Phase R6 of the refactor. Their logic migrated to `pipelines/`
(Python orchestration) and `skills/` (domain-knowledge markdown recipes).
`knowledge/store.py` is DEFERRED — it's still consumed by `main.py` web-UI
paths and `projects/service.py`; its removal is scheduled for a follow-up
refactor once those callers migrate to `records.jsonl` + `alpha_review.ReviewState`.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Claude Code                                                        │
│    reads .claude/skills/*/SKILL.md when description matches         │
│    invokes tools: Bash, Read, Write, Edit, Grep, Glob, Task, ...    │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alpha_research                                                     │
│                                                                     │
│   Skills (markdown)          Pipelines (Python)                     │
│   ├─ paper-evaluate          ├─ literature_survey  ─┐               │
│   ├─ significance-screen     ├─ method_survey       │               │
│   ├─ formalization-check     ├─ frontier_mapping    │ call skills   │
│   ├─ adversarial-review  ◀───┤  research_review_loop│ via claude -p │
│   └─ ... (8 more)            └─ state_machine (pure)                │
│                                                                     │
│   Helpers                   Records                                 │
│   ├─ metrics/verdict.py     └─ JSONL project memory                 │
│   ├─ scripts/sympy_verify      (evaluation/finding/review/          │
│   └─ scripts/audit_stats         frontier/...)                      │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alpha_review (editable dependency at ../alpha_review)              │
│    apis.search_all, s2_*, openalex_search, unpaywall_pdf_url, ...  │
│    scholar.scholar_search_papers                                    │
│    models.ReviewState (SQLite-backed papers/themes store)           │
│    sdk.run_plan/scope/search/read/write (the survey pipeline)       │
│    alpha-review CLI (entry point used by literature_survey pipe)    │
└─────────────────────────────────────────────────────────────────────┘
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
