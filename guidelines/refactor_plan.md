# Refactor Plan — Skills-First Architecture

Sanity check of the existing `alpha_research` codebase against the new skills-first architecture defined in `tools_and_skills.md`, with concrete per-file deletion / refactor / keep decisions and a migration plan.

**Status**: the original T1-T10 implementation is complete (494 tests passing). This document plans the transition from T1-T10's tool-centric layout to the skills-first layout.

---

## Part 0. Context

### What changed
1. **`alpha_review`** at `../alpha_review` is now a dependency. It provides all scholarly API clients, a SQLite-backed paper store (`ReviewState`), and a full literature-survey pipeline (`run_plan/scope/search/read/write`) with its own CLI (`alpha-review`).
2. **Zero new MCP tools** — the project's deliverable is skills + Python pipelines + small helpers (per `tools_and_skills.md`).
3. **Eight of the twelve original skills are genuine skills** (LLM judgment tasks); **three become Python pipelines** (deterministic orchestration); **several need small Python helpers** (sympy verification, statistical audit, verdict computation).

### Source of truth
- `guidelines/tools_and_skills.md` — the architecture (skills + pipelines + helpers, no MCP tools)
- `guidelines/research_guideline.md` — the standards skills encode
- `guidelines/review_guideline.md` — the adversarial review standards
- `guidelines/research_plan.md` — the research state machine (SM-1..SM-6, still valid as architectural spec)
- `guidelines/review_plan.md` — executable review metrics

---

## Part I. Per-File Audit

The existing codebase is 10,171 source lines across 55 Python files. This section decides the fate of every file.

Legend:
- **DELETE** — file is fully redundant with `alpha_review` or the new architecture
- **SHRINK** — keep partial content, delete the rest
- **REFACTOR** — logic moves into a new location (pipeline, helper, or skill seed)
- **KEEP** — unique to `alpha_research`, no changes needed
- **SEED** — content migrates into SKILL.md files

### I.1 `tools/` — redundancy with `alpha_review.apis`

| File | Lines | Fate | Reason |
|---|---|---|---|
| `tools/arxiv_search.py` | 130 | **DELETE** | Fully redundant with `alpha_review.apis.arxiv_search`. Skills call the alpha_review function directly via `bash python -c`. |
| `tools/semantic_scholar.py` | 209 | **DELETE** | Fully redundant with `alpha_review.apis.s2_*`. |
| `tools/knowledge.py` | 116 | **DELETE** | Thin wrapper over `KnowledgeStore`. Becomes obsolete when `KnowledgeStore` itself shrinks to the JSONL-record helper. |
| `tools/paper_fetch.py` | 275 | **KEEP + enhance** | `alpha_review` has no full-text extraction. Enhance with Unpaywall fallback via `alpha_review.apis.unpaywall_pdf_url`. Callable from skills as `bash python -c "from alpha_research.tools.paper_fetch import fetch_and_extract; ..."`. |
| `tools/report.py` | 310 | **SHRINK → refactor** | Split: delete the `survey` template (alpha_review's `run_write` handles LaTeX surveys); keep the `digest` and `deep` templates (rubric-heavy markdown reports unique to alpha_research). Move to `src/alpha_research/reports/templates.py`. |
| `tools/__init__.py` | small | **SHRINK** | Re-exports — trim to keep only `paper_fetch` and renamed report module. |

**Net deletion**: ~455 lines (arxiv_search + semantic_scholar + knowledge wrapper).
**Net refactor**: ~310 lines (report.py shrinks and relocates).

### I.2 `knowledge/` — redundancy with `alpha_review.models.ReviewState`

| File | Lines | Fate | Reason |
|---|---|---|---|
| `knowledge/schema.py` | 150 | **DELETE** | `papers` table is redundant with `alpha_review.ReviewState`. The 7 extension tables (`evaluations`, `paper_relations`, `findings`, `frontier_snapshots`, `topic_clusters`, `questions`, `feedback`) become JSONL files per `tools_and_skills.md` Part II. |
| `knowledge/store.py` | 456 | **DELETE** | Same reason. All CRUD paths are replaced: papers → `alpha_review.ReviewState`; evaluations/findings/reviews/frontier → JSONL append/read; topic_clusters/questions/feedback → not migrated (unused in the skill layer). |
| `knowledge/__init__.py` | small | **REPLACE** | New contents: re-export JSONL helper from the new `records/` module. |

**Net deletion**: ~606 lines.

**Replacement**: a new file `src/alpha_research/records/jsonl.py` (~80 lines) providing:
```python
def append_record(project_dir: Path, record_type: str, data: dict) -> str:
    """Append a typed record to output/<project>/<record_type>.jsonl with uuid id."""

def read_records(project_dir: Path, record_type: str,
                 filters: dict | None = None, limit: int | None = None) -> list[dict]:
    """Read and filter records from a JSONL file."""
```

Record types: `evaluation`, `finding`, `review`, `frontier`, `significance_screen`, `formalization_check`, `diagnosis`, `challenge`, `method_survey`, `audit`, `concurrent_work`, `gap_report`.

### I.3 `models/` — data models

| File | Lines | Fate | Reason |
|---|---|---|---|
| `models/research.py` | 240 | **SHRINK** | Remove `Paper` and `PaperMetadata` (use `alpha_review.models.Paper`). Keep `Evaluation`, `RubricScore`, `TaskChain`, `SignificanceAssessment`, `ExtractionQuality`, `SearchState`, `SearchQuery`, `PaperCandidate`, `CoverageReport` — these are alpha_research-specific concepts. |
| `models/review.py` | 342 | **KEEP** | Review / Finding / Verdict / Severity / ReviewQualityMetrics / RevisionResponse — all unique to the review_guideline. No equivalents in `alpha_review`. |
| `models/blackboard.py` | ~170 | **KEEP** | Blackboard / ResearchArtifact / ConvergenceState / HumanDecision / Venue — shared state for the adversarial loop. Unique. |
| `models/project.py` | ~100 | **KEEP** | From project_lifecycle_revision_plan. Unique. |
| `models/snapshot.py` | small | **KEEP** | Same. |
| `models/__init__.py` | small | **UPDATE** | Re-exports — remove deleted symbols. |

**Net deletion**: ~80 lines (Paper + PaperMetadata + related code in research.py).

### I.4 `agents/` — becomes Python pipelines + skill seed content

The existing agents are well-factored: each is a Python class that isolates LLM interaction (via an injected `LLMCallable`) from orchestration logic. This structure refactors cleanly.

| File | Lines | Fate | Reason |
|---|---|---|---|
| `agents/research_agent.py` | 509 | **REFACTOR** into pipelines + skills | State-machine logic (`_TRANSITIONS`, `get_valid_transitions`) → keep as pure functions in `pipelines/state_machine.py`. JSON parsing (`_parse_response`) → move to a skill-output parser helper. Prompt building (`_build_prompt` + `research_system.py` content) → SEED content for `.claude/skills/paper-evaluate/SKILL.md` and `.claude/skills/literature-survey/` pipeline glue. |
| `agents/review_agent.py` | 325 | **REFACTOR** into `pipelines/adversarial_review.py` + skill | `compute_verdict` (pure function) → move to `metrics/verdict.py`. `extract_chain` (heuristic parser) → keep as helper. Prompt-building + orchestration → SEED for `.claude/skills/adversarial-review/SKILL.md`. |
| `agents/meta_reviewer.py` | 138 | **REFACTOR** → pure Python helper | Already mostly deterministic (metric checks). Move logic into `metrics/review_quality.py::evaluate_review` (which already exists). Delete the wrapper class. |
| `agents/orchestrator.py` | 276 | **REFACTOR** → `pipelines/research_review_loop.py` | Convergence loop, backward-trigger detection, anti-collapse check → keep as a Python pipeline. Calls skills via `claude -p` (through the existing `alpha_research.llm` client). |
| `agents/__init__.py` | 8 | **UPDATE** | Trim to keep only whatever remains (likely empty or deleted). |

**Net**: 1256 lines refactored. Approximately 60% of the prompt/prose content moves into SKILL.md files; the pure Python logic (state transitions, verdict computation, convergence detection) becomes pipeline/helper functions.

### I.5 `prompts/` — SEED content for SKILL.md files

This is the highest-leverage refactor. The 1904 lines of prompt code contain the domain knowledge that becomes the skills' body content.

| File | Lines | Fate | SKILL.md target |
|---|---|---|---|
| `prompts/rubric.py` | 398 | **SEED** | Shared by multiple skills. Split: significance tests → `significance-screen/SKILL.md`. Appendix B rubric → `paper-evaluate/SKILL.md`. Attack vectors → `adversarial-review/SKILL.md`. Shared text ("One-Sentence Test", "task chain") → include files (`.claude/skills/<slug>/reference.md`) referenced by multiple skills. |
| `prompts/research_system.py` | 467 | **SEED** | Body content for `paper-evaluate/SKILL.md` (rubric application), `significance-screen/SKILL.md` (§2.2 tests), `formalization-check/SKILL.md` (§2.4 formalization). Honesty protocol → shared reference. |
| `prompts/review_system.py` | 505 | **SEED** | Body content for `adversarial-review/SKILL.md`. All six attack vectors (§3.1-3.6), venue calibration (§4), graduated pressure (§2.6), anti-patterns (§5.4). |
| `prompts/meta_review_system.py` | 324 | **DELETE** (logic stays) | Meta-review becomes a pure Python function in `metrics/review_quality.py` (already done). The prompt text was for an LLM-based meta-review which is no longer used; the metric checks are deterministic. |
| `prompts/understanding_system.py` | 210 | **SEED** | From the project_lifecycle_revision_plan understanding agent. Body content for `.claude/skills/project-understanding/SKILL.md` (a 13th skill added by the lifecycle plan; not in the core 10). |
| `prompts/__init__.py` | 21 | **DELETE** | Re-exports no longer needed. |

**Net**: 1904 lines reviewed. ~60% (≈1150 lines) of text migrates into SKILL.md bodies; ~40% is deleted as structural scaffolding (Python string assembly, Jinja fragments) that doesn't translate to markdown.

### I.6 `metrics/` — Python helpers (the "small helpers" from the analysis)

| File | Lines | Fate | Reason |
|---|---|---|---|
| `metrics/review_quality.py` | 464 | **KEEP + adjust** | Already a pure Python module. Used by `adversarial-review` skill as a helper (skill calls `bash python -c "from alpha_research.metrics.review_quality import evaluate_review; ..."`). Add CLI entry point for convenience. |
| `metrics/convergence.py` | ~150 | **KEEP** | Used by `pipelines/research_review_loop.py`. |
| `metrics/finding_tracker.py` | ~100 | **KEEP** | Same. |
| `metrics/__init__.py` | small | **KEEP** | |

**New file**: `metrics/verdict.py` (~60 lines) — moved out of `agents/review_agent.py::compute_verdict`. Pure function that implements the `review_plan.md §1.9` rules. Unit-tested independently.

### I.7 `config.py` and `main.py`

| File | Lines | Fate | Reason |
|---|---|---|---|
| `config.py` | 179 | **KEEP** | Constitution loader + Venue enum. Unique. Possibly add `alpha_review.yaml` path resolution. |
| `main.py` | 455 | **SHRINK + refactor** | Typer CLI. Current commands: `research`, `review`, `loop`, `status`. New commands: `survey` (delegates to `alpha-review` CLI), `evaluate` (invokes paper-evaluate skill), `review-paper` (invokes adversarial-review skill), `loop` (invokes `pipelines.research_review_loop.run`). Roughly halves in size as orchestration moves to pipelines. |
| `llm.py` | 137 | **KEEP** | Provides `LLMCallable` protocol + concrete clients. **Not redundant with `alpha_review.llm`** — ours uses the Anthropic SDK directly for API-key auth; `alpha_review.llm.claude_call` uses the `claude -p` CLI. Both mechanisms are valid and serve different deployment models. Pipelines that run inside Claude Code use the CLI route; pipelines that run standalone (e.g., batch evaluation without Claude Code) use our SDK client. |

### I.8 `api/` — FastAPI backend

| File | Lines | Fate | Reason |
|---|---|---|---|
| `api/app.py`, `api/models.py` | ~50 | **KEEP** | FastAPI app + request/response models. |
| `api/routers/*.py` (papers, evaluations, graph, agent, projects) | ~500 | **KEEP** | Frontend monitoring endpoints. `alpha_review.server` has parallel endpoints for its own surveys; our endpoints serve project-level artifacts (evaluations, reviews, findings, frontier, project lifecycle). No overlap. |

### I.9 `projects/` — project lifecycle system

| File | Lines | Fate | Reason |
|---|---|---|---|
| `projects/git_state.py` | 275 | **KEEP** | From project_lifecycle_revision_plan. Unique. |
| `projects/orchestrator.py` | 492 | **KEEP (or merge)** | Project-level orchestrator. May merge with the new `pipelines/research_review_loop.py` if there's overlap. |
| `projects/registry.py` | ~120 | **KEEP** | |
| `projects/resume.py` | 265 | **KEEP** | |
| `projects/service.py`, `projects/snapshots.py`, `projects/understanding.py` | ~400 | **KEEP** | |

---

## Part II. Target Codebase Layout (Post-Refactor)

```
alpha_research/
├── .claude/
│   └── skills/                              # NEW — the core deliverable
│       ├── significance-screen/SKILL.md
│       ├── formalization-check/
│       │   ├── SKILL.md
│       │   └── reference.md                 # shared §2.4, §3.1 text
│       ├── diagnose-system/SKILL.md
│       ├── challenge-articulate/SKILL.md
│       ├── experiment-audit/SKILL.md
│       ├── adversarial-review/
│       │   ├── SKILL.md
│       │   ├── attack_vectors.md            # §3.1-3.6 detail
│       │   └── venue_calibration.md         # §4
│       ├── paper-evaluate/
│       │   ├── SKILL.md
│       │   └── rubric.md                    # Appendix B detail
│       ├── concurrent-work-check/SKILL.md
│       ├── gap-analysis/SKILL.md
│       ├── classify-capability/SKILL.md     # NEW (factored from frontier-mapping)
│       └── identify-method-gaps/SKILL.md    # NEW (factored from method-survey)
│
├── guidelines/                              # unchanged except updates below
│   ├── research_guideline.md
│   ├── review_guideline.md
│   ├── research_plan.md                     # updated with status pointer
│   ├── review_plan.md
│   ├── tools_and_skills.md                  # current architecture doc
│   ├── refactor_plan.md                     # THIS FILE
│   ├── TASKS.md                             # rewritten as R1-R15 refactor tasks
│   └── ... (rest unchanged)
│
├── scripts/                                 # NEW — helper scripts called via Bash
│   ├── sympy_verify.py                      # for formalization-check skill
│   └── audit_stats.py                       # for experiment-audit skill
│
├── src/alpha_research/
│   ├── __init__.py
│   ├── config.py                            # KEEP (constitution, venues)
│   ├── llm.py                               # KEEP (LLMCallable + Anthropic client)
│   ├── main.py                              # SHRUNK Typer CLI
│   │
│   ├── pipelines/                           # NEW — deterministic orchestration
│   │   ├── __init__.py
│   │   ├── literature_survey.py             # wraps alpha-review CLI + paper-evaluate loop
│   │   ├── method_survey.py                 # search + graph + paper-evaluate loop
│   │   ├── frontier_mapping.py              # classify-capability loop + diff
│   │   ├── research_review_loop.py          # adversarial convergence (from agents/orchestrator.py)
│   │   └── state_machine.py                 # transitions g1-g5, triggers t2-t15 (pure functions)
│   │
│   ├── records/                             # NEW — JSONL project memory
│   │   ├── __init__.py
│   │   └── jsonl.py                         # append_record, read_records
│   │
│   ├── models/
│   │   ├── __init__.py                      # updated re-exports
│   │   ├── research.py                      # SHRUNK (Paper/PaperMetadata removed)
│   │   ├── review.py                        # KEEP
│   │   ├── blackboard.py                    # KEEP
│   │   ├── project.py                       # KEEP
│   │   └── snapshot.py                      # KEEP
│   │
│   ├── metrics/                             # Python helpers (called by skills via Bash)
│   │   ├── __init__.py
│   │   ├── review_quality.py                # KEEP + CLI entry point
│   │   ├── convergence.py                   # KEEP
│   │   ├── finding_tracker.py               # KEEP
│   │   └── verdict.py                       # NEW (pure function, from review_agent.compute_verdict)
│   │
│   ├── reports/                             # was tools/report.py, relocated and shrunk
│   │   ├── __init__.py
│   │   └── templates.py                     # digest + deep rubric templates (survey template deleted)
│   │
│   ├── tools/                               # SHRUNK — only paper_fetch remains
│   │   ├── __init__.py
│   │   └── paper_fetch.py                   # KEEP + Unpaywall fallback
│   │
│   ├── api/                                 # KEEP (frontend backend)
│   │   ├── app.py
│   │   ├── models.py
│   │   └── routers/
│   │
│   └── projects/                            # KEEP (project lifecycle)
│       ├── git_state.py
│       ├── orchestrator.py
│       ├── registry.py
│       ├── resume.py
│       ├── service.py
│       ├── snapshots.py
│       └── understanding.py
│
└── tests/
    ├── test_pipelines/                      # NEW
    │   ├── test_literature_survey.py
    │   ├── test_method_survey.py
    │   ├── test_frontier_mapping.py
    │   ├── test_research_review_loop.py
    │   └── test_state_machine.py
    ├── test_records.py                      # NEW
    ├── test_skills/                         # NEW — fixture-based skill integration tests
    │   └── fixtures/                        # sample papers, expected outputs
    ├── test_metrics/                        # renamed from test_review_quality.py
    ├── test_tools/test_paper_fetch.py       # KEEP
    ├── test_models.py                       # SHRUNK
    ├── test_api.py, test_api_projects.py    # KEEP
    ├── test_project_*.py                    # KEEP
    └── test_cli.py                          # UPDATED (new CLI commands)
```

### What disappears

| Disappeared path | Line count | Now lives in |
|---|---|---|
| `src/alpha_research/tools/arxiv_search.py` | 130 | `alpha_review.apis.arxiv_search` |
| `src/alpha_research/tools/semantic_scholar.py` | 209 | `alpha_review.apis.s2_*` |
| `src/alpha_research/tools/knowledge.py` | 116 | Deleted; JSONL helper in `records/` |
| `src/alpha_research/knowledge/schema.py` | 150 | `alpha_review.models.ReviewState` + JSONL |
| `src/alpha_research/knowledge/store.py` | 456 | Same |
| `src/alpha_research/prompts/meta_review_system.py` | 324 | Deleted (logic in `metrics/review_quality.py`) |
| `src/alpha_research/prompts/research_system.py` | 467 | `.claude/skills/paper-evaluate/`, `significance-screen/`, `formalization-check/` |
| `src/alpha_research/prompts/review_system.py` | 505 | `.claude/skills/adversarial-review/` |
| `src/alpha_research/prompts/rubric.py` | 398 | Split across skills + shared reference files |
| `src/alpha_research/prompts/understanding_system.py` | 210 | `.claude/skills/project-understanding/` |
| `src/alpha_research/prompts/__init__.py` | 21 | Deleted |
| `src/alpha_research/agents/research_agent.py` | 509 | `pipelines/literature_survey.py` + skills |
| `src/alpha_research/agents/review_agent.py` | 325 | `pipelines/adversarial_review.py` + skill + `metrics/verdict.py` |
| `src/alpha_research/agents/meta_reviewer.py` | 138 | Absorbed into `metrics/review_quality.py` |
| `src/alpha_research/agents/orchestrator.py` | 276 | `pipelines/research_review_loop.py` |
| `src/alpha_research/agents/__init__.py` | 8 | Deleted |

**Total deletion: ~4,242 lines.** Approximately 42% of the current source code is either redundant with `alpha_review` or represents structural scaffolding that no longer fits the skills-first architecture.

### What stays + shrinks
- `models/` shrinks by ~80 lines (Paper removal)
- `tools/report.py` shrinks and relocates to `reports/` (~200 lines, down from 310)
- `main.py` shrinks by ~150 lines (orchestration moves to pipelines)

### What gets added
- 10 `.claude/skills/*/SKILL.md` files — total ~2000-2500 lines of markdown (the migrated prompt content)
- 2 small skills (`classify-capability`, `identify-method-gaps`) — ~200 lines
- `src/alpha_research/pipelines/` — ~600 lines of pure Python orchestration (distilled from the current agents/)
- `src/alpha_research/records/jsonl.py` — ~80 lines
- `src/alpha_research/metrics/verdict.py` — ~60 lines
- `scripts/sympy_verify.py` + `scripts/audit_stats.py` — ~150 lines
- Test suites for pipelines, records, skills — ~800 lines

**Net: the codebase shrinks from ~10,200 source lines to roughly ~6,500 source lines + ~2,500 markdown lines + ~800 new test lines.**

---

## Part III. Skills Design — Mapping Existing Code to SKILL.md

For each of the 10 final skills (8 original irreducibles + 2 factored out), this section specifies where the content comes from in the existing codebase and what it becomes.

### S1. `significance-screen`
- **Verdict from analysis**: irreducibly a skill
- **Existing source**: `prompts/research_system.py` (§2.2 significance-test block, ~80 lines) + `prompts/rubric.py` (SIGNIFICANCE_TESTS constant, ~60 lines)
- **Uses**:
  - `bash python -c "from alpha_review.apis import search_all; ..."` for literature search
  - `bash python -c "from alpha_research.tools.paper_fetch import fetch_and_extract; ..."` for full text
  - `alpha_review.apis.s2_citations` for impact trajectory
  - `bash python -c "from alpha_research.records.jsonl import append_record; ..."` for persistence
- **Output**: JSON with four test scores + human_flag set true for Hamming
- **Honesty**: flags Hamming always; Consequence can be verified from concrete downstream claims

### S2. `formalization-check`
- **Verdict**: skill + sympy helper
- **Existing source**: `prompts/research_system.py` (§2.4 formalization block, ~70 lines) + `prompts/rubric.py` (B.1 criterion, ~30 lines)
- **Uses**:
  - `fetch_and_extract` for paper text with math_preserved flag
  - `scripts/sympy_verify.py <expression>` for claimed-property checks
  - `alpha_review.apis.search_all` to find alternative formalizations
- **Output**: formalization level, framework, structure, sympy verification result, human_flag always true

### S3. `diagnose-system`
- **Verdict**: skill + Bash for experiments
- **Existing source**: `prompts/research_system.py` (§2.4 empirical diagnosis block, ~50 lines)
- **Uses**:
  - `Bash` with lab-specific experiment launch commands (no generic tool — skill text contains the lab's conventions)
  - `Read` on log files or `Bash python -c "import wandb; ..."` for results
  - `bash python -c "from alpha_research.records.jsonl import append_record; ..."`
- **Output**: failure taxonomy, specific descriptions, failure-to-formalism map, suggested next stage (forward / backward trigger)

### S4. `challenge-articulate`
- **Verdict**: irreducibly a skill
- **Existing source**: `prompts/research_system.py` (§2.5, §2.7 challenge→approach table, ~80 lines) + `prompts/rubric.py` (challenge structural tests, ~40 lines)
- **Uses**:
  - `read_records` on diagnoses.jsonl (latest diagnosis)
  - `alpha_review.apis.search_all` for similar challenge articulations
  - `fetch_and_extract` for top related papers
- **Output**: challenge statement, type (from §2.7 table), implied solution class, prior-work check

### S5. `experiment-audit`
- **Verdict**: skill + Python stats helper
- **Existing source**: `prompts/review_system.py` (§3.5.1-3.5.3 experimental attack vectors, ~100 lines) + `prompts/rubric.py` (B.3 criteria, ~50 lines) + `review_plan.md` §1.6 metrics
- **Uses**:
  - `scripts/audit_stats.py <exp_dir>` for trial counts, CI, variance, power
  - `alpha_review.apis.search_all` to find the strongest missing baseline
  - `Read` on wandb exports / CSV logs
- **Output**: per-check pass/fail, missing baselines, overclaiming flags, venue threshold assessment

### S6. `adversarial-review`
- **Verdict**: skill + `metrics/verdict.py` helper + sub-skill composition via Task
- **Existing source**: `prompts/review_system.py` (all 505 lines — the largest single migration) + `prompts/rubric.py` (attack vectors, ~100 lines) + `agents/review_agent.py::_build_prompt` for graduated pressure logic
- **Uses**:
  - `fetch_and_extract` for paper content
  - `alpha_review.apis.search_all` for concurrent-work search
  - `alpha_review.apis.s2_citations` for impact check
  - `Task` to invoke `concurrent-work-check`, `formalization-check`, `experiment-audit` as sub-skills
  - `bash python -m alpha_research.metrics.verdict <findings.jsonl>` for mechanical verdict computation
  - `append_record` to reviews.jsonl
- **Output**: Review object — chain_extraction, steel_man (≥3 sentences), findings (classified fatal/serious/minor), verdict, confidence, questions_for_authors

### S7. `paper-evaluate`
- **Verdict**: canonical skill (text in → structured assessment out)
- **Existing source**: `prompts/research_system.py` (Appendix B rubric application block, ~150 lines) + `prompts/rubric.py` (B.1-B.7 criteria, ~150 lines)
- **Uses**:
  - `fetch_and_extract` for sections
  - `alpha_review.apis.s2_paper_details` for metadata (venue, citations)
  - `read_records` on evaluations.jsonl for novelty cross-check
  - `append_record` to persist
- **Output**: rubric scores B.1-B.7 with evidence + confidence, task chain, significance assessment, human flags

### S8. `concurrent-work-check`
- **Verdict**: irreducibly a skill
- **Existing source**: `prompts/review_system.py` (concurrent-work attack vector, ~30 lines) + research_guideline §2.2 (concurrent work test)
- **Uses**:
  - `alpha_review.apis.search_all` with multiple query formulations
  - `alpha_review.apis.s2_citations` for citation-graph expansion
  - `alpha_review.scholar.scholar_search_papers` as last resort
  - `fetch_and_extract` for high-overlap hits
- **Output**: overlap degree ∈ {none, minor, significant, scooped}, differentiation plan

### S9. `gap-analysis`
- **Verdict**: skill (semantic clustering is LLM work)
- **Existing source**: research_guideline §5.1 Axis 1 + no existing prompt code (new content)
- **Uses**:
  - `read_records` on evaluations.jsonl to aggregate weaknesses across papers
  - `alpha_review.apis.search_all` to verify each gap is real (not missed papers)
- **Output**: recurring limitations, unsolved failures, proposed directions (each with significance flag)

### S10. `classify-capability`
- **Verdict**: small skill factored from frontier-mapping
- **Purpose**: given one paper's task chain + reported results, classify the demonstrated capability into reliable / sometimes / can't-yet for its domain
- **Existing source**: research_guideline §5.1 Axis 3 (frontier definitions)
- **Uses**: takes task_chain dict as input, no tool calls
- **Output**: tier ∈ {reliable, sometimes, cant_yet} + evidence

### S11. `identify-method-gaps` (small)
- **Verdict**: small skill factored from method-survey pipeline
- **Purpose**: given a list of evaluated methods in a solution class, identify what hasn't been tried
- **Uses**: takes list of method summaries as input
- **Output**: list of gaps with rationale

---

## Part IV. Pipelines Design

### P1. `pipelines/literature_survey.py`

Replaces the `literature-survey` "skill" from earlier drafts. Pure Python orchestration.

```python
async def run_literature_survey(
    query: str,
    output_dir: Path,
    hamming_list: list[str] | None = None,
    apply_rubric: bool = True,
) -> LiteratureSurveyResult:
    """
    1. Run `alpha-review "<query>" -o <output_dir>` via subprocess
    2. Load included papers from alpha_review's ReviewState
    3. For each paper (parallel via asyncio), invoke `paper-evaluate` skill
       via claude -p, write result to evaluations.jsonl
    4. Invoke `gap-analysis` skill on aggregated evaluations
    5. Run `pipelines.frontier_mapping.run` on the evaluations
    6. Write alpha_research_report.md synthesizing all of the above
    """
```

Inputs: query, output directory. Outputs: paths to LaTeX survey + alpha_research report + counts.

Dependencies: `alpha_review` CLI on PATH, `claude` CLI on PATH (for skill invocation via `alpha_research.llm.claude_call` or equivalent).

### P2. `pipelines/method_survey.py`

```python
async def run_method_survey(
    challenge_id: str,
    project_dir: Path,
) -> MethodSurveyResult:
    """
    1. Load the challenge from challenges.jsonl
    2. Build search queries from challenge_type → method class (§2.7 table)
    3. alpha_review.apis.search_all on each query
    4. For top-3 methods, alpha_review.apis.s2_references + s2_citations
    5. Parallel paper-evaluate on all candidates
    6. Build comparison table from evaluation records
    7. Invoke identify-method-gaps skill on the comparison table
    8. Persist method_survey record
    """
```

### P3. `pipelines/frontier_mapping.py`

```python
async def run_frontier_mapping(
    project_dir: Path,
    domain: str,
) -> FrontierReport:
    """
    1. read_records on evaluations.jsonl filtered to domain
    2. For each evaluation, invoke classify-capability skill
    3. Aggregate into reliable/sometimes/cant-yet tiers
    4. Load previous frontier snapshot (if any) and diff
    5. append_record to frontier.jsonl
    """
```

### P4. `pipelines/research_review_loop.py`

Replaces `agents/orchestrator.py`. The adversarial convergence loop.

```python
async def run_research_review_loop(
    project_dir: Path,
    max_iterations: int = 5,
    venue: str = "RSS",
) -> LoopResult:
    """
    1. Load current ResearchArtifact from blackboard
    2. For iteration in range(max_iterations):
       a. Invoke adversarial-review skill (via claude -p)
       b. Parse review, compute verdict via metrics/verdict.py
       c. Check convergence (metrics/convergence.py)
       d. If converged or submit-ready, return
       e. Otherwise invoke revision via paper-evaluate + human checkpoint
    3. Apply anti-collapse check (metrics/finding_tracker.py)
    """
```

### P5. `pipelines/state_machine.py`

Pure functions extracted from `agents/research_agent.py::_TRANSITIONS` and related logic. No LLM calls. Unit-testable.

```python
def valid_transitions(stage: str) -> list[str]: ...
def backward_trigger_from_finding(finding: Finding) -> str | None: ...  # returns t2..t15 or None
def stage_guard_satisfied(stage: str, artifact: ResearchArtifact) -> bool: ...  # g1..g5
```

---

## Part V. Migration Phases

Phase boundaries chosen so every phase ends with a green test suite.

### Phase R0 — Preparation (1 day)

- [ ] Add `alpha_review` as editable dependency: `pip install -e ../alpha_review`
- [ ] Verify all 494 existing tests still pass (baseline)
- [ ] Create `guidelines/refactor_plan.md` (this file) and new `TASKS.md`
- [ ] Back up `src/alpha_research/` via git tag `pre-refactor`

### Phase R1 — Records and helpers (new infrastructure, ~2 days)

- [ ] Write `src/alpha_research/records/jsonl.py` (append + read)
- [ ] Write `scripts/sympy_verify.py` (standalone CLI: `python scripts/sympy_verify.py --expr "..." --property convex`)
- [ ] Write `scripts/audit_stats.py` (standalone CLI: `python scripts/audit_stats.py <exp_dir> --venue RSS`)
- [ ] Write `src/alpha_research/metrics/verdict.py` (extract `compute_verdict` from `agents/review_agent.py`)
- [ ] Write tests: `tests/test_records.py`, `tests/test_metrics/test_verdict.py`
- [ ] All new tests pass; all existing tests still pass

### Phase R2 — Delete redundant paper/knowledge code (~1 day)

- [ ] Delete `src/alpha_research/tools/arxiv_search.py`
- [ ] Delete `src/alpha_research/tools/semantic_scholar.py`
- [ ] Delete `src/alpha_research/tools/knowledge.py`
- [ ] Delete `src/alpha_research/knowledge/schema.py`
- [ ] Delete `src/alpha_research/knowledge/store.py`
- [ ] Delete related tests (`test_store.py`, `test_tools/test_arxiv_search.py`, `test_tools/test_semantic_scholar.py`)
- [ ] Redirect any remaining imports to `alpha_review.apis.*` / `alpha_review.models.ReviewState` / JSONL helpers
- [ ] Shrink `models/research.py`: remove `Paper`, `PaperMetadata` classes; update re-exports
- [ ] Update `tests/test_models.py` to drop Paper tests
- [ ] Remaining tests pass

### Phase R3 — Relocate report templates (~0.5 days)

- [ ] Create `src/alpha_research/reports/__init__.py` and `templates.py`
- [ ] Move digest + deep templates from `tools/report.py` to `reports/templates.py`
- [ ] Delete the survey template from `report.py` (alpha_review's `run_write` replaces it)
- [ ] Delete the now-empty `tools/report.py`; update `tools/__init__.py`
- [ ] Update `tests/test_tools/test_report.py` → `tests/test_reports.py`
- [ ] Tests pass

### Phase R4 — Write pipelines (~4 days)

- [ ] `pipelines/state_machine.py` — pure functions, extract from `agents/research_agent.py`. Unit test.
- [ ] `pipelines/literature_survey.py` — subprocess call to `alpha-review` CLI + paper-evaluate loop. Integration-test with a tiny topic.
- [ ] `pipelines/method_survey.py` — orchestrates search + graph + evaluate loop.
- [ ] `pipelines/frontier_mapping.py` — evaluations filter + classify-capability loop + diff.
- [ ] `pipelines/research_review_loop.py` — extract from `agents/orchestrator.py`, invoke adversarial-review skill via `alpha_research.llm.claude_call`.
- [ ] Tests: `tests/test_pipelines/*.py`
- [ ] Tests pass

### Phase R5 — Write the 10 SKILL.md files (~5 days)

This is the highest-leverage phase. Each SKILL.md migrates 50-500 lines of existing prompt code into markdown.

- [ ] `.claude/skills/paper-evaluate/` — SKILL.md + rubric.md (seeded from `prompts/research_system.py` + `prompts/rubric.py` Appendix B block)
- [ ] `.claude/skills/significance-screen/SKILL.md` — seeded from `prompts/research_system.py` §2.2 block
- [ ] `.claude/skills/formalization-check/` — SKILL.md + reference.md (seeded from §2.4, §3.1 blocks)
- [ ] `.claude/skills/diagnose-system/SKILL.md` — seeded from §2.4 empirical block + skill-specific lab-convention template
- [ ] `.claude/skills/challenge-articulate/SKILL.md` — seeded from §2.5, §2.7 blocks
- [ ] `.claude/skills/experiment-audit/SKILL.md` — seeded from `prompts/review_system.py` §3.5 + `review_plan.md` §1.6
- [ ] `.claude/skills/adversarial-review/` — SKILL.md + attack_vectors.md + venue_calibration.md (the largest migration; 500+ lines from `prompts/review_system.py`)
- [ ] `.claude/skills/concurrent-work-check/SKILL.md`
- [ ] `.claude/skills/gap-analysis/SKILL.md` — new content, no direct prompt source
- [ ] `.claude/skills/classify-capability/SKILL.md` — small, new
- [ ] `.claude/skills/identify-method-gaps/SKILL.md` — small, new
- [ ] Skill fixture tests: `tests/test_skills/` with sample papers; verify skills produce valid structured output via `claude -p`
- [ ] Tests pass (slow — skill integration tests hit the Claude API or mock it)

### Phase R6 — Delete superseded prompts and agents (~1 day)

- [ ] Delete `src/alpha_research/prompts/meta_review_system.py` (logic already in `metrics/review_quality.py`)
- [ ] Delete `src/alpha_research/prompts/research_system.py` (content now in 3 skills)
- [ ] Delete `src/alpha_research/prompts/review_system.py` (content now in adversarial-review skill)
- [ ] Delete `src/alpha_research/prompts/rubric.py` (content distributed across skills)
- [ ] Delete `src/alpha_research/prompts/understanding_system.py` (content now in project-understanding skill)
- [ ] Delete `src/alpha_research/prompts/__init__.py` and the directory
- [ ] Delete `src/alpha_research/agents/research_agent.py` (logic in pipelines + skills)
- [ ] Delete `src/alpha_research/agents/review_agent.py`
- [ ] Delete `src/alpha_research/agents/meta_reviewer.py`
- [ ] Delete `src/alpha_research/agents/orchestrator.py` (logic in `pipelines/research_review_loop.py`)
- [ ] Delete `src/alpha_research/agents/__init__.py` and the directory
- [ ] Delete test files: `tests/test_prompts.py`, `tests/test_research_agent.py`, `tests/test_review_agent.py`, `tests/test_orchestrator.py`
- [ ] Tests pass (skill and pipeline tests cover what the deleted tests used to cover)

### Phase R7 — Update CLI and entry points (~1 day)

- [ ] Rewrite `src/alpha_research/main.py` commands:
  - `alpha-research survey <query> -o <dir>` → `pipelines.literature_survey.run`
  - `alpha-research evaluate <paper_id> -o <dir>` → invoke `paper-evaluate` skill via `claude -p`
  - `alpha-research review <artifact> -o <dir>` → invoke `adversarial-review` skill
  - `alpha-research loop <project_dir>` → `pipelines.research_review_loop.run`
  - `alpha-research status <project_dir>` → unchanged
- [ ] Update `tests/test_cli.py`
- [ ] Tests pass

### Phase R8 — Integration testing and validation (~2 days)

- [ ] End-to-end test: `alpha-research survey "tactile manipulation for deformable objects" -o /tmp/e2e` produces LaTeX survey + evaluations.jsonl + alpha_research_report.md with non-trivial content
- [ ] End-to-end test: `alpha-research review <fixture_artifact> -o /tmp/rev` produces a valid Review record via the adversarial-review skill
- [ ] Calibration test: score 10 fixture papers, compare against human gold labels, verify B.1-B.7 agreement within ±1 on 70%+ dimensions (T10 acceptance criterion)
- [ ] Tests pass

### Phase R9 — Documentation and cleanup (~0.5 days)

- [ ] Update `README.md` with new architecture and CLI commands
- [ ] Update `pyproject.toml` with `alpha_review` dependency
- [ ] Update `guidelines/research_plan.md` with status pointer to this refactor
- [ ] Delete `guidelines/tools_and_skills_implementation.md` (obsolete — replaced by this file + SKILL.md files)
- [ ] `git tag post-refactor`

---

## Part VI. Risks and Open Questions

### Risks

1. **Skill fixture tests are slow and flaky.** Each skill invocation hits `claude -p` (real API) unless mocked. Mitigation: fixtures + response caching; mock in unit tests, real calls only in end-to-end.

2. **Context loss when migrating prompts to markdown.** Some Python prompts have f-string interpolation (venue, iteration, stage). Markdown skills can't do this — we have to use `$ARGUMENTS` pattern or move the parameterization into the skill invocation text. Mitigation: document each parameterization point during migration.

3. **Pipeline output parsing.** Skills produce JSON-ish text; pipelines need to parse it. The existing `agents/*.py` already have `_parse_response` methods — reuse them.

4. **`alpha_review` dependency stability.** It's a file-path editable dependency. Version drift between alpha_research and alpha_review could break things. Mitigation: pin to a git SHA in `pyproject.toml` once both stabilize.

5. **`llmutils` dependency in `llm.py`.** Not universally available. Already has fallback to direct Anthropic client. Verify fallback works in the post-refactor environment.

6. **`projects/` module has its own orchestrator.** `projects/orchestrator.py` (492 lines) and our new `pipelines/research_review_loop.py` might overlap. Decide during R4 whether to merge or keep separate (project-level vs research-level orchestration).

### Open questions

1. **Where do helper scripts live?** `scripts/` at the repo root, or `src/alpha_research/scripts/` as an entry-point module? Recommendation: `scripts/` at root for clarity; no import-path conflicts.

2. **Should pipelines live in `src/alpha_research/pipelines/` or elsewhere?** Consistent with the current package layout, keep inside the package so they're importable as `from alpha_research.pipelines import run_literature_survey`.

3. **`llm.py` vs `alpha_review.llm.claude_call`** — pipelines can use either. Pick one canonical path per pipeline. Tentative rule: pipelines that run **inside Claude Code** (invoked by skills via `Bash`) use `alpha_research.llm.claude_call` which delegates to `claude -p`. Pipelines that run **standalone** (invoked by the CLI outside Claude Code) use `alpha_research.llm.AnthropicLLM` with an API key.

4. **Versioning of skill files.** Skills are markdown; git tracks changes. But skills that load via progressive disclosure are described by their frontmatter `description` — changing it mid-project may break description-based discovery. Mitigation: semver in frontmatter? Not needed initially.

5. **Frontend compatibility.** The FastAPI server and frontend currently read from `KnowledgeStore` via `api/routers/*.py`. After R2, these need to read from `alpha_review.ReviewState` + JSONL files instead. The API shape stays the same; only the backend changes.

---

## Part VII. Acceptance Criteria

The refactor is **done** when:

- [ ] ~4,200 lines of redundant/superseded code are deleted
- [ ] 10 SKILL.md files exist under `.claude/skills/`
- [ ] 5 pipeline modules exist under `src/alpha_research/pipelines/`
- [ ] 3 helper scripts exist under `scripts/`
- [ ] `records/jsonl.py` replaces the paper-portion of `knowledge/store.py`
- [ ] `metrics/verdict.py` exists as a standalone pure function module
- [ ] All 494 pre-refactor tests either still pass or are replaced by equivalent pipeline/skill tests
- [ ] `alpha-research survey "<topic>" -o <dir>` end-to-end produces a LaTeX survey + rubric report on a real topic
- [ ] `alpha-research review <artifact>` end-to-end produces a structured review with mechanical verdict
- [ ] README updated
- [ ] `research_plan.md` has a status pointer to this refactor
- [ ] `tools_and_skills_implementation.md` is deleted (obsolete)
- [ ] Git tagged `post-refactor`

---

## Appendix A: File-by-File Fate Summary

| Path | Lines | Fate |
|---|---|---|
| `src/alpha_research/tools/arxiv_search.py` | 130 | DELETE |
| `src/alpha_research/tools/semantic_scholar.py` | 209 | DELETE |
| `src/alpha_research/tools/knowledge.py` | 116 | DELETE |
| `src/alpha_research/tools/paper_fetch.py` | 275 | KEEP + Unpaywall fallback |
| `src/alpha_research/tools/report.py` | 310 | SHRINK → `reports/templates.py` |
| `src/alpha_research/knowledge/schema.py` | 150 | DELETE |
| `src/alpha_research/knowledge/store.py` | 456 | DELETE |
| `src/alpha_research/models/research.py` | 240 | SHRINK (remove Paper) |
| `src/alpha_research/models/review.py` | 342 | KEEP |
| `src/alpha_research/models/blackboard.py` | ~170 | KEEP |
| `src/alpha_research/models/project.py` | ~100 | KEEP |
| `src/alpha_research/models/snapshot.py` | ~50 | KEEP |
| `src/alpha_research/agents/research_agent.py` | 509 | REFACTOR → pipelines + skills |
| `src/alpha_research/agents/review_agent.py` | 325 | REFACTOR → pipelines + skill + `metrics/verdict.py` |
| `src/alpha_research/agents/meta_reviewer.py` | 138 | ABSORBED into `metrics/review_quality.py` |
| `src/alpha_research/agents/orchestrator.py` | 276 | REFACTOR → `pipelines/research_review_loop.py` |
| `src/alpha_research/prompts/meta_review_system.py` | 324 | DELETE |
| `src/alpha_research/prompts/research_system.py` | 467 | SEED (3 skills) |
| `src/alpha_research/prompts/review_system.py` | 505 | SEED (adversarial-review) |
| `src/alpha_research/prompts/rubric.py` | 398 | SEED (distributed) |
| `src/alpha_research/prompts/understanding_system.py` | 210 | SEED (project-understanding) |
| `src/alpha_research/metrics/review_quality.py` | 464 | KEEP |
| `src/alpha_research/metrics/convergence.py` | ~150 | KEEP |
| `src/alpha_research/metrics/finding_tracker.py` | ~100 | KEEP |
| `src/alpha_research/llm.py` | 137 | KEEP |
| `src/alpha_research/config.py` | 179 | KEEP |
| `src/alpha_research/main.py` | 455 | SHRINK |
| `src/alpha_research/api/*` | ~550 | KEEP |
| `src/alpha_research/projects/*` | ~1300 | KEEP (verify orchestrator overlap with new pipeline) |

---

## Appendix B: Dependencies on `alpha_review`

After the refactor, the following `alpha_review` symbols are imported by `alpha_research`:

| Symbol | Used by |
|---|---|
| `alpha_review.apis.search_all` | skills (via `bash python -c`) + `pipelines/literature_survey.py` + `pipelines/method_survey.py` |
| `alpha_review.apis.s2_paper_details` | `paper-evaluate` skill |
| `alpha_review.apis.s2_references` | `method-survey`, `adversarial-review` skills |
| `alpha_review.apis.s2_citations` | `significance-screen`, `adversarial-review`, `concurrent-work-check` skills |
| `alpha_review.apis.unpaywall_pdf_url` | `tools/paper_fetch.py` (as fallback) |
| `alpha_review.scholar.scholar_search_papers` | `concurrent-work-check` skill (last-resort path) |
| `alpha_review.models.ReviewState` | `pipelines/literature_survey.py` + skills (via JSONL helper wrapper) |
| `alpha_review.sdk.run_plan / run_scope / run_search / run_read / run_write` | NOT imported directly — used via `alpha-review` CLI |
| `alpha_review` CLI | `pipelines/literature_survey.py` (via subprocess) |

No MCP wrappers. No adapter classes. Direct Python imports via `bash python -c "..."` from skills, or direct imports from pipelines.
