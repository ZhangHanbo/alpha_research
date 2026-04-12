# Alpha Research

**A skills-first robotics research system.** Automates paper discovery,
evaluation, and adversarial review by encoding doctoral-level robotics
research judgment into Claude Code Agent Skills paired with Python
pipelines.

You run it from the CLI. It surveys literature via the `alpha_review`
dependency, applies the Appendix B rubric to every paper, walks a
two-layer research state machine (SIGNIFICANCE → FORMALIZE → DIAGNOSE
→ CHALLENGE → APPROACH → VALIDATE) with backward error detection, and
runs an adversarial research-review convergence loop that applies
six attack vectors at venue standard.

This README is the **entrance**: install, run, CLI reference,
project layout. For the design, see `docs/PROJECT.md`. For the
plan, see `docs/PLAN.md`. For the surveys that grounded it, see
`docs/SURVEY.md`. For design decisions and migration history, see
`docs/DISCUSSION.md`. For the append-only development log, see
`docs/LOGS.md`.

---

## Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────────┐
│  Claude Code                                                        │
│    reads skills/*/SKILL.md when description matches                 │
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
│   └─ ... (11 more)           └─ state_machine (pure)                │
│                                                                     │
│   Helpers                    Records                                │
│   ├─ metrics/verdict.py      └─ JSONL project memory                │
│   ├─ scripts/sympy_verify       (evaluation/finding/review/         │
│   └─ scripts/audit_stats          frontier/...)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alpha_review (editable dependency at ../alpha_review)              │
│    apis.search_all, s2_*, openalex_search, unpaywall_pdf_url, ...   │
│    scholar.scholar_search_papers                                    │
│    models.ReviewState (SQLite-backed papers/themes store)           │
│    sdk.run_plan/scope/search/read/write (the survey pipeline)       │
│    alpha-review CLI (entry point used by literature_survey pipe)    │
└─────────────────────────────────────────────────────────────────────┘
```

**Zero new tools.** Everything a researcher needs is reachable through
Claude Code's built-ins (`Bash`, `Read`, `Write`, `Edit`, `Grep`,
`Glob`) plus the `alpha_review` Python module. Skills encode the
research doctrine; pipelines run deterministic orchestration; JSONL
files hold per-project state. See `docs/PROJECT.md` §Skills-First
Architecture for the full rationale.

**Project-as-directory.** A research project is literally a directory
on disk under `output/<name>/` containing human-owned markdown
(project.md, hamming.md, formalization.md, benchmarks.md,
one_sentence.md, log.md), CLI-managed `state.json`, agent-written
`source.md`, and an append-only log of JSONL record streams
(evaluations.jsonl, significance_screens.jsonl, formalization_checks.jsonl,
diagnoses.jsonl, challenges.jsonl, reviews.jsonl, frontier.jsonl, ...).

---

## Prerequisites

- **Conda** (Miniconda or Anaconda)
- **Python 3.10+**
- **Node.js 20+** (only if you want the legacy Next.js dashboard —
  deferred per Phase 0 cut)
- **Claude CLI** (`claude`) installed and authenticated — skills are
  invoked via `claude -p`
- The sibling **`alpha_review`** project checked out at
  `../alpha_review`, installed as an editable dependency
- An **`ANTHROPIC_API_KEY`** exported in the shell (optional for
  search/fetch-only runs; required for LLM-based evaluation and review)

---

## Setup

### 1. Create and activate the conda environment

```bash
conda create -n alpha_research python=3.11 -y
conda activate alpha_research
```

### 2. Install `alpha_review` and `alpha_research`

```bash
# From the repo parent directory (so ../alpha_review resolves)
pip install -e ../alpha_review
pip install -e ".[dev]"
```

### 3. Install the git pre-commit hook

```bash
./scripts/install_hooks.sh
```

This enforces:
- `docs/` contains exactly 5 files (`PROJECT.md`, `PLAN.md`,
  `SURVEY.md`, `DISCUSSION.md`, `LOGS.md`)
- `docs/LOGS.md` is append-only (new content must be a byte-exact
  extension of the committed version)

### 4. Set your API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Without a key, the system still runs literature search, paper
fetching, and report generation — it just skips LLM-based evaluation
and review.

---

## Quick Start

### 1. Run a literature survey

Wraps the `alpha-review` CLI (PLAN → SCOPE → SEARCH/READ loop →
WRITE) and layers the Appendix B rubric via the `paper-evaluate`
skill over every included paper.

```bash
alpha-research survey "tactile manipulation for deformable objects" -o output/tactile
```

Outputs:
- `output/tactile/review.db` — `alpha_review`'s papers+themes store
- `output/tactile/review_grounded.tex` — LaTeX survey
- `output/tactile/review_grounded.pdf` — compiled PDF (if pdflatex available)
- `output/tactile/evaluations.jsonl` — our rubric scores with evidence
- `output/tactile/alpha_research_report.md` — synthesis with taxonomy,
  frontier, and identified gaps

### 2. Evaluate a single paper (Appendix B rubric)

```bash
alpha-research evaluate arxiv:2501.12345 -o output/single
```

### 3. Screen a candidate problem for significance

Applies the four tests from `research_guideline.md` §2.2: Hamming,
Consequence, Durability, Compounding.

```bash
alpha-research significance "contact-rich manipulation under uncertainty"
```

### 4. Adversarial review at venue standard

Six attack vectors from `review_guideline.md` Part III, steel-man
first, fatal/serious/minor classification, mechanical verdict.

```bash
alpha-research review path/to/paper.md --venue RSS -o output/reviews
```

### 5. Run the full adversarial convergence loop on a project

```bash
alpha-research loop output/tactile --venue RSS --max-iterations 5
```

Drives review → human revision → re-review with graduated adversarial
pressure (structural scan → full review → focused re-review) and a
meta-reviewer that catches vague or toothless critiques.

### 6. Summarize a project's JSONL records

```bash
alpha-research status output/tactile
```

---

## CLI Reference

```
alpha-research survey       <query> -o <dir>                    # literature_survey pipeline
alpha-research evaluate     <paper_id> -o <dir>                 # paper-evaluate skill
alpha-research review       <artifact.md> --venue RSS -o <dir>  # adversarial-review skill
alpha-research significance <problem>                           # significance-screen skill
alpha-research loop         <project_dir> --venue RSS           # research_review_loop pipeline
alpha-research status       [<project_dir>]                     # summarize JSONL records

alpha-research project init|stage|advance|backward|log|status   # project lifecycle
```

**Venues** (strictest to most lenient): `IJRR`, `T-RO`, `RSS`,
`CoRL`, `RA-L`, `ICRA`, `IROS`. Each triggers venue-calibrated
thresholds on trial counts, real-robot expectations, formalization
depth, and baseline strength. See `docs/SURVEY.md` Round 1 Venue
Calibration for the full per-venue rubric.

---

## Project Structure

```
alpha_research/
├── skills/                        # Claude Code Agent Skills (runtime artifacts — LEAVE IN PLACE)
│   ├── paper-evaluate/            #   Canonical rubric scoring (Sonnet)
│   ├── significance-screen/       #   Hamming/Consequence/Durability/Compounding (Opus)
│   ├── formalization-check/       #   Math detection + sympy verify (Opus)
│   ├── diagnose-system/           #   Failure taxonomy + formal mapping (Sonnet)
│   ├── challenge-articulate/      #   Structural barrier identification (Opus)
│   ├── experiment-audit/          #   Stats + baselines + overclaiming (Sonnet)
│   ├── adversarial-review/        #   Full 6-attack-vector review (Opus, largest)
│   ├── concurrent-work-check/     #   Scoop detection (Sonnet)
│   ├── gap-analysis/              #   Semantic clustering (Opus)
│   ├── classify-capability/       #   Frontier tier assignment (Sonnet)
│   ├── identify-method-gaps/      #   Method-class coverage gaps (Sonnet)
│   ├── benchmark-survey/          #   Benchmark selection survey (planned)
│   ├── experiment-design/         #   Reproduction / diagnostic / approach (planned)
│   ├── experiment-analyze/        #   Results audit with reproducibility gate (planned)
│   └── project-understanding/     #   Code-tree understanding → source.md (planned)
│
├── config/                        # YAML configs (constitution, review)
├── docs/                          # Canonical 5-file documentation set
│   ├── PROJECT.md                 #   Design reference (doctrine + architecture)
│   ├── PLAN.md                    #   Active plan + phased roadmap
│   ├── SURVEY.md                  #   Venue calibration + methodology research
│   ├── DISCUSSION.md              #   Design decisions + migration history
│   └── LOGS.md                    #   Append-only development log
│
├── scripts/                       # Helper CLIs
│   ├── sympy_verify.py            #   Mathematical property verification
│   ├── audit_stats.py             #   Statistical audit
│   ├── check_docs.py              #   Docs-layout enforcer
│   └── install_hooks.sh           #   git pre-commit hook installer
│
├── src/alpha_research/
│   ├── pipelines/                 # Deterministic Python orchestration
│   │   ├── state_machine.py       #   Pure functions: g1-g5, t2-t15
│   │   ├── literature_survey.py   #   alpha-review CLI + paper-evaluate loop
│   │   ├── method_survey.py       #   Search + graph + evaluate loop
│   │   ├── frontier_mapping.py    #   classify-capability loop + diff
│   │   └── research_review_loop.py#   Adversarial convergence loop
│   ├── records/jsonl.py           # append/read/count JSONL records
│   ├── metrics/
│   │   ├── verdict.py             #   Pure compute_verdict per review_plan §1.9
│   │   ├── review_quality.py      #   Actionability, grounding, anti-patterns
│   │   ├── convergence.py         #   Convergence + stagnation detection
│   │   └── finding_tracker.py     #   Cross-iteration finding tracking
│   ├── reports/templates.py       # DIGEST + DEEP rubric templates (Jinja2)
│   ├── models/                    # Pydantic data models
│   │   ├── research.py            #   Evaluation, TaskChain, RubricScore, ...
│   │   ├── review.py              #   Finding, Review, Verdict, ...
│   │   ├── blackboard.py          #   Blackboard, ResearchArtifact, Venue
│   │   ├── project.py             #   ProjectManifest, ProjectState (legacy)
│   │   └── snapshot.py            #   SourceSnapshot, ProjectSnapshot (legacy)
│   ├── tools/paper_fetch.py       # PDF download + pymupdf extraction
│   ├── projects/                  # Legacy project lifecycle layer (being collapsed — see PLAN)
│   ├── templates/project/         # Project scaffold markdown templates
│   ├── api/                       # Legacy FastAPI backend (deferred — see PLAN)
│   ├── config.py                  # YAML config loaders
│   ├── llm.py                     # Anthropic API client wrapper
│   ├── project.py                 # New per-project state + append_revision_log
│   ├── skills.py                  # Skill invoker and stage-check helper
│   └── main.py                    # Typer CLI
│
├── tests/                         # 300+ unit + integration (integration opt-in)
├── data/                          # Runtime: search cache, global paper store
├── output/                        # Runtime: one directory per project
└── pyproject.toml
```

**Note.** Earlier versions of this tree had a `frontend/` directory
(Next.js dashboard), an `api/` layer (FastAPI + AG-UI), a rich
`agents/` package, and a `knowledge/` SQLite store. Phase 0 of the
integrated state-machine plan cuts those — see `docs/DISCUSSION.md`
R0-R9 refactor journey and the project lifecycle debate for why.

---

## Per-Project Artifacts

A project directory under `output/<name>/` contains:

**Human-owned markdown** (the researcher writes these):
- `project.md` — question, task, why-now, scope
- `hamming.md` — running list of 10-20 important unsolved problems
- `formalization.md` — the problem as math (objective, variables,
  constraints, information structure)
- `benchmarks.md` — chosen benchmarks with rationale, success
  criterion, published baselines, saturation assessment
- `one_sentence.md` — evolving contribution statement
- `log.md` — weekly Tried/Expected/Observed/Concluded/Next entries

**Agent-written markdown**:
- `source.md` — what the `project-understanding` skill learned from
  reading `code_dir`

**CLI-owned state**:
- `state.json` — current stage, history, forward-guard status, open
  backward triggers, `code_dir`, target venue
- `provenance.jsonl` — append-only lineage of every action (CLI,
  skill, pipeline)

**Agent-written JSONL record streams**:
- `evaluations.jsonl` — per-paper Appendix B rubric scores
- `significance_screens.jsonl` — four significance-test outputs
- `formalization_checks.jsonl` — formalization-level + structure findings
- `diagnoses.jsonl` — failure mode → formal term mappings
- `challenges.jsonl` — challenge articulations with implied method class
- `method_surveys.jsonl` — method class coverage surveys
- `concurrent_work.jsonl` — scoop checks
- `experiment_designs.jsonl` — proposed experiment configs
- `experiment_analyses.jsonl` — experiment audits + reproducibility verdicts
- `findings.jsonl` — structured findings from analyses, diagnoses, reviews
- `reviews.jsonl` — adversarial review records (verdict + findings)
- `frontier.jsonl` — frontier_mapping pipeline snapshots (reliable/sometimes/can't-yet)
- `gap_reports.jsonl` — gap-analysis skill outputs

The researcher's **actual method code lives outside** the project
directory (at `state.code_dir` in `state.json`). Experiments live
under `<code_dir>/experiments/<exp_id>/` next to the code they
produced, following the convention in `docs/PROJECT.md` §Experiment
Interface.

---

## Configuration

### `config/constitution.yaml` — research agent domain focus

```yaml
name: "Robotics Research"
focus_areas:
  - "mobile manipulation"
  - "contact-rich manipulation"
  - "tactile sensing and feedback"
max_papers_per_cycle: 50
```

### `config/review_config.yaml` — review loop behavior

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

---

## Testing

```bash
# Fast suite (no network, no LLM calls)
python -m pytest tests/ -q

# With coverage
python -m pytest tests/ --cov=alpha_research --cov-report=term-missing

# Include the opt-in integration tests that hit real CLIs / APIs
python -m pytest -m "" tests/
```

Tests emit per-module markdown reports to `tests/reports/` via the
`ReportWriter` fixture — a reviewer can understand what each module
guarantees by reading its report without running pytest. See
`docs/LOGS.md` 2026-04-11 entry Part 1 for the pattern.

---

## Troubleshooting

### `alpha_review` import fails

Ensure it's installed as an editable dependency from the sibling
directory:

```bash
pip install -e ../alpha_review
python -c "import alpha_review; print(alpha_review.__file__)"
```

### `claude` CLI not found

Skills are invoked via `claude -p`. Install Claude Code and log in,
or disable LLM features by unsetting `ANTHROPIC_API_KEY` and avoiding
the `evaluate`/`review`/`loop` verbs.

### Python 3.8 + `list[str]` annotations

If you're stuck on Python 3.8 (not recommended; minimum is 3.10):
`pip install eval_type_backport`.

### `pytest` imports missing

```bash
pip install -e ".[dev]"
```

### Docs layout pre-commit check fails

If you see `docs/ layout check FAILED` when committing:
- `docs/ missing required files` → restore the missing file or
  re-run the docs migration
- `docs/ contains files outside the canonical set` → move the
  file out of `docs/` (only the 5 canonical files are allowed)
- `docs/LOGS.md is append-only but its new content does not start
  with the HEAD content` → you edited the old part of `LOGS.md`
  instead of appending. Append a correction entry at the bottom
  instead.

To bypass in an emergency: `git commit --no-verify` (but fix the
issue in a follow-up).

---

## Next Steps

- **Read the design**: `docs/PROJECT.md` — the two-layer state
  machine, research doctrine, review doctrine, problem formulation
  methodology, skills-first architecture, experiment interface
- **Read the plan**: `docs/PLAN.md` — active implementation plan
  (Phases 0-10), TODO list, open questions, risks
- **Read the surveys**: `docs/SURVEY.md` — venue-specific calibration
  (RSS, CoRL, NeurIPS, ICML, IJRR, T-RO) and the open-source
  landscape review that informed the deferred frontend plan
- **Read the decisions**: `docs/DISCUSSION.md` — the R0-R9 refactor
  journey, the project lifecycle debate, the three-canonical-docs
  invariant
- **Read the history**: `docs/LOGS.md` — append-only development log
