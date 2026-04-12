# Alpha Research — Implementation Plan

Phased roadmap, active TODO list, open questions, and risks. This is
the authoritative plan for what to build next and why.

For the **design principles** behind these choices, see
`docs/PROJECT.md`. For the **venue calibration surveys** that
grounded the review standards, see `docs/SURVEY.md`. For the
**development history** of what was actually built, see
`docs/LOGS.md` (append-only). For the **design decisions** that
shaped the plan, see `docs/DISCUSSION.md`.

---

## Table of Contents

1. [Current Status](#1-current-status)
2. [Phased Roadmap](#2-phased-roadmap)
3. [The Active Plan — Integrated State Machine](#3-the-active-plan--integrated-state-machine)
4. [Review Plan — Agent Architecture](#4-review-plan--agent-architecture)
5. [Active TODO List](#5-active-todo-list)
6. [Open Questions](#6-open-questions)
7. [Risks and Rollback](#7-risks-and-rollback)
8. [Archive — Superseded Plans](#8-archive--superseded-plans)

---

## 1. Current Status

### 1.1 Where we are

**The R0-R9 skills-first refactor is complete.** See `docs/DISCUSSION.md`
R0-R9 refactor journey for the full narrative. Summary:

| Metric | Value |
|---|---|
| Phase | R0-R9 complete; integrated state-machine plan Phase 0 next |
| Lines of production code | ~6,647 Python (post-R6 refactor) |
| Lines of markdown (skills) | ~3,323 across 15 SKILL.md files |
| Tests | 323 passed, 1 skipped (live Haiku smoke) |
| Per-module test reports | 25 files in `tests/reports/` |
| Skills registered | 15 (11 core + 4 planned but staged) |
| Pipelines implemented | 5 (literature_survey, method_survey, frontier_mapping, research_review_loop, state_machine) |
| Python metrics modules | 4 (verdict, review_quality, convergence, finding_tracker) |
| JSONL record types | 12 (evaluation, finding, review, frontier, significance_screen, formalization_check, diagnosis, challenge, method_survey, audit, concurrent_work, gap_report) |
| Dependencies | Editable on `../alpha_review` |

**The pipeline runs end-to-end on real topics.** `alpha-research
survey` wraps `alpha-review` CLI + paper-evaluate loop; `alpha-research
review` produces structured reviews with mechanical verdicts;
`alpha-research loop` drives research-review convergence with
graduated pressure.

**What still exists but is slated for Phase 0 deletion**:
- `src/alpha_research/api/` (legacy FastAPI backend + CopilotKit adapter)
- `frontend/` (Next.js 15 dashboard with three views)
- `src/alpha_research/projects/` (1,300 lines of project lifecycle layer)
- `src/alpha_research/knowledge/` (legacy SQLite store shim)
- `src/alpha_research/tools/report.py` (12-line backward-compat shim)

**What still needs wiring**:
- The state machine's pure functions (`g1..g5`, `t2..t15`) exist in
  `pipelines/state_machine.py` but nothing consults them at runtime
- `state.json` is not yet written by any CLI verb
- `provenance.jsonl` is not yet appended by skill invocations
- The four new skills (`benchmark-survey`, `project-understanding`,
  `experiment-design`, `experiment-analyze`) are staged but not written
- Skills do not yet have `research_stages:` frontmatter
- `.claude/skills` symlink to `skills/` is not yet created

Phase 0 through Phase 10 of the integrated state-machine plan in §3
close these gaps.

### 1.2 Architecture foundations already working

From the R0-R9 refactor (all working, not placeholders):

- `records/jsonl.py` — `append_record`, `read_records`, `count_records`
- `metrics/verdict.py` — pure `compute_verdict` per review_plan §1.9
- `metrics/review_quality.py` — actionability / grounding / falsifiability checks
- `metrics/convergence.py` — research-review loop stopping conditions
- `metrics/finding_tracker.py` — cross-iteration finding resolution
- `pipelines/state_machine.py` — pure functions for `g1..g5` and `t2..t15`
- `pipelines/literature_survey.py` — `alpha-review` CLI + paper-evaluate loop
- `pipelines/method_survey.py` — search + graph + paper-evaluate loop
- `pipelines/frontier_mapping.py` — classify-capability loop + frontier diff
- `pipelines/research_review_loop.py` — adversarial convergence
- `reports/templates.py` — DIGEST + DEEP Jinja2 rubric templates
- `tools/paper_fetch.py` — PDF → sections with extraction quality flags
- `project.py` — `ProjectState` dataclass, `init_project`, `append_revision_log`
- `templates/project/` — PROJECT.md.j2, DISCUSSION.md.j2, LOGS.md.j2,
  hamming.md.j2, formalization.md.j2, one_sentence.md.j2 scaffolds
- 11 existing `SKILL.md` files under `skills/`: paper-evaluate,
  significance-screen, formalization-check, diagnose-system,
  challenge-articulate, experiment-audit, adversarial-review,
  concurrent-work-check, gap-analysis, classify-capability,
  identify-method-gaps

---

## 2. Phased Roadmap

The integrated state-machine plan supersedes the original T1-T10
implementation and the earlier project-lifecycle plan. Each phase
leaves the codebase in a working state (tests green, CLI functional).
Phases are ordered by dependency.

| Phase | Goal | Status | Duration |
|---|---|---|---|
| **R0-R9** | Skills-first refactor: delete tool wrappers, move prompts into SKILL.md, write pipelines + records + metrics | ✅ Complete | ~18 days (pre-2026-04-11) |
| **0** | Cut and consolidate: delete frontend/, api/, projects/, knowledge/, tools/report.py; activate skills symlink; trim main.py | 🚧 Next | 1 day |
| **1** | State machine wiring: stage_guard_check, advance/backward transitions, records/state.py, provenance.jsonl, unit tests for every guard and trigger | Planned | 2 days |
| **2** | Artifact templates + project lifecycle CLI: project init/stage/advance/backward/log/status verbs | Planned | 2 days |
| **3** | Wire existing skills to state machine: add `research_stages:` frontmatter, stage-check helper, pipelines log to provenance | Planned | 2 days |
| **4** | Source binding + `project-understanding` skill: `code_dir` handling, source.md generation, formalization↔code gap check | Planned | 1 day |
| **5** | Benchmark survey + selection: `benchmark-survey` skill, tightened g2 (benchmarks.md required), tightened g3 (reproducibility floor) | Planned | 2 days |
| **6** | Experiment interface: `experiment-design` (reproduction / diagnostic / approach modes), `experiment-analyze` with reproducibility verdict | Planned | 3 days |
| **7** | Diagnose + challenge rewiring to consume experiment records | Planned | 1 day |
| **8** | Observe / log / calibrate / provenance cross-stage commands | Planned | 1 day |
| **9** | End-to-end integration test walking all six stages with at least one backward transition and one reproduction cycle | Planned | 2 days |
| **10** | Documentation and cleanup: update README, delete stale TASKS.md sections | Planned | 0.5 days |

**Total Phase 0-10 estimate**: ~17.5 working days. Net code delta is
roughly **−150 lines**, with ~1,100 of the additions being skill
markdown rather than Python. The codebase gets materially simpler
while gaining the entire "doing research" half of the loop, including
benchmark survey, selection, and reproducibility-gated diagnosis.

---

## 3. The Active Plan — Integrated State Machine

**Source**: `guidelines/spec/implementation_plan.md` (1149 lines).
This is the live plan for what we build next. It supersedes the
"Implementation Plan" sections of `research_plan.md` and the phased
plan in `refactor_plan.md`.

**One-sentence goal**: make the two-layer state machine actually
*run* — with human-owned artifacts as state, skills and CLI verbs as
transitions, and source code + experiments as first-class citizens
of the loop — while keeping the system compact enough that a single
researcher can hold it in their head.

### 3.1 Mental model

**Artifacts are the state; skills and verbs are the transitions.**
The existing code treats the state machine as *theory* —
`pipelines/state_machine.py` has pure functions for `g1..g5` and
`t2..t15`, but nothing consults them at runtime and nothing persists
"which stage am I in." This plan makes the state machine executable
by binding it to **files on disk** (see `docs/PROJECT.md` §2.1
Architecture at a Glance diagram).

A project's full state at any instant = the contents of its
directory on disk. The CLI and skills are deterministic
transformations over that state. The human is always the outermost
controller — the agent never advances stages on its own.

**What changes relative to today**:
- **Today**: the system evaluates papers and reviews drafts. Everything is literature-side.
- **After this plan**: the system sits alongside the researcher's actual lab — reads their method code, reads their experiment results, walks them through diagnose / challenge / approach / validate with persistent stage tracking and a provenance log that lets them answer "why did I run this experiment?" three weeks later.

**What we do NOT build**: a simulation platform, training framework,
data collection pipeline, or experiment launcher. The researcher
already has those. We build interfaces.

### 3.2 Project layout (filesystem as state)

```
output/<project>/
  PROJECT.md                   # technical details (HUMAN, required)
  DISCUSSION.md                # user/agent discussions (HUMAN, required)
  LOGS.md                      # weekly log + agent revisions (HUMAN + AGENT, required)
  hamming.md                   # researcher's Hamming list (HUMAN, updated monthly)
  formalization.md             # the problem as math (HUMAN-drafted; agent reviews)
  benchmarks.md                # chosen benchmarks + baselines to reproduce (HUMAN, agent-proposed)
  one_sentence.md              # evolving contribution statement (HUMAN)
  source.md                    # what agent learned from reading code_dir (AGENT-written)
  state.json                   # current stage + history + guard status + open triggers (CLI-managed)
  provenance.jsonl             # append-only lineage of every action

  # JSONL record streams (agent-written, one record per invocation)
  evaluations.jsonl
  significance_screens.jsonl
  formalization_checks.jsonl
  benchmark_surveys.jsonl
  diagnoses.jsonl
  challenges.jsonl
  method_surveys.jsonl
  concurrent_work.jsonl
  experiment_designs.jsonl
  experiment_analyses.jsonl
  findings.jsonl
  reviews.jsonl
  frontier.jsonl
  gap_reports.jsonl

  # Optional — the researcher's actual method code is elsewhere
  (code_dir is an absolute path in state.json, not a subdirectory)
```

**Principle**: a project is its directory. `tar czf project.tgz
output/<project>/` is a complete backup. No registry, no SQLite
except the `alpha_review` paper store (which is global and not
per-project), no snapshots unless the researcher runs `git` in the
directory themselves.

### 3.3 `state.json` schema

```python
@dataclass
class ProjectState:
    project_id: str                          # = directory basename
    created_at: str                          # ISO 8601
    current_stage: ResearchStage             # enum from models.blackboard
    stage_entered_at: str
    stage_history: list[StageTransition]     # append-only
    open_triggers: list[OpenTrigger]         # backward triggers proposed but not resolved
    forward_guard_status: dict[str, GuardCheck]
    code_dir: str | None                     # absolute path to method code
    target_venue: str                        # default "RSS"
    notes: str                               # free-form researcher notes

@dataclass
class StageTransition:
    from_stage: ResearchStage | None
    to_stage: ResearchStage
    at: str                                  # ISO 8601
    trigger: str | None                      # "g1".."g5" or "t2".."t15" or "init"
    note: str
    carried_constraint: str | None           # for backward transitions
    provenance_id: str                       # FK into provenance.jsonl

@dataclass
class OpenTrigger:
    trigger: str                             # "t5", "t15", ...
    proposed_by: str                         # skill name
    proposed_at: str
    evidence: str                            # pointer to a finding / review record
    resolved: bool = False
    resolution_note: str | None = None

@dataclass
class GuardCheck:
    guard: str                               # "g1".."g5"
    passed: bool
    checked_at: str
    failing_conditions: list[str]            # empty if passed
```

### 3.4 `provenance.jsonl` schema

```python
@dataclass
class ProvenanceRecord:
    id: str                                  # uuid
    created_at: str
    action_type: str                         # "skill"|"pipeline"|"cli"|"human"|"transition"
    action_name: str                         # e.g. "significance-screen", "project advance"
    project_stage: ResearchStage
    inputs: list[str]                        # artifact refs read
    outputs: list[str]                       # artifact refs written
    parent_ids: list[str]                    # prior provenance ids this built on
    summary: str
```

Every CLI verb, every skill invocation, and every pipeline run
appends one record. This is the single source of truth for "what
happened and in what order." `alpha-research provenance` reads and
renders this.

### 3.5 Per-stage specifications

Each stage is specified by: **entry condition, inputs, actions,
outputs, forward guard, backward triggers**. The CLI and skills
enforce these contracts. See `docs/PROJECT.md` §3 The Two-Layer
State Machine for the g1..g5 / t2..t15 definitions; this section
records only what's new per stage in the integrated plan.

#### 3.5.1 SIGNIFICANCE
**Agent skills** (stage-bound): `literature-survey`, `significance-screen`,
`frontier-mapping` pipeline, `gap-analysis`, `paper-evaluate`.
**Key human input**: `hamming.md` (the agent cannot produce this).
**Forward guard g1**: significance_screen with concrete consequence,
`durability_risk != "high"`, human-confirmed Hamming test.
**Backward triggers fired into this stage**: `t2`, `t5`, `t9`, `t13`.

#### 3.5.2 FORMALIZE
**New responsibility**: benchmark selection is a formalization
decision — a benchmark pins down the observation space, action
space, success criterion, and evaluation distribution. You cannot
enter DIAGNOSE without both the math AND a benchmark.
**Agent skills**: `formalization-check`, `method_survey`,
**`benchmark-survey` (new)**.
**Key human inputs**: `formalization.md` (the math),
`benchmarks.md` (benchmark choices with rationale).
**Forward guard g2**: formalization_check at level `formal_math | semi_formal`,
claimed structure non-null, sympy verification passed,
**AND** benchmarks.md has ≥1 chosen benchmark with rationale + success
criterion + ≥1 published baseline with its number + saturation
assessment, **AND** latest benchmark_survey has `human_confirmed: true`.
**Backward triggers detected here**: `t2` (problem reduces to a
solved one, OR chosen benchmark is already saturated).

#### 3.5.3 DIAGNOSE
**The stage the current system has zero coverage of.** Requires the
researcher's actual method code, a set-up benchmark, and experiment
results.
**Pre-entry requirement**: `state.code_dir` must be set. If
`source.md` is stale, run `project-understanding` first.
**Sub-ordering enforced by g3**:
1. **Setup** — install benchmark(s), wire to `code_dir`, record
   install recipe under `<code_dir>/experiments/<benchmark_id>_setup.md`
2. **Reproduce** — run at least one reproduction experiment per
   chosen benchmark; verify measured number is within tolerance
   of the published number. This is the **reproducibility floor**
3. **Diagnose** — run the minimal system, observe failures, map
   each to a specific term in `formalization.md`
**Agent skills**: `project-understanding` (new), `experiment-design`
(new, reproduction + diagnostic modes), `experiment-analyze` (new,
with reproducibility verdict), `diagnose-system`.
**Forward guard g3**: for every in-scope benchmark, ≥1
experiment_analysis record with `reproduction_of` set and
`reproducibility ∈ {pass, partial}`; ≥1 diagnosis with
`failure_mapped_to_formal_term` non-null; non-stale experiments.
**Backward triggers detected here**: `t4` (failure doesn't map),
`t7` (observation space can't express the decision variables).

#### 3.5.4 CHALLENGE
**Agent skills**: `challenge-articulate`, `concurrent-work-check`,
`method_survey`.
**Forward guard g4**: challenge_type structural (not resource
complaint), implied_method_class non-null, passes "predict the
method class" test, no unresolved `t12`.

#### 3.5.5 APPROACH
**Agent skills**: `method_survey`, `identify-method-gaps`,
`concurrent-work-check`, `experiment-design` (new, approach mode),
`project-understanding` (re-reads `code_dir` after code changes),
`formalization-check` (re-run for drift detection), `paper-evaluate`.
**Forward guard g5**: one_sentence.md states a structural insight,
`one_sentence_test: "insight"`, ≥1 experiment_design record,
`formal_impl_gap: "none" | "minor"`, no unresolved triggers.

#### 3.5.6 VALIDATE
**Agent skills**: `experiment-analyze`, `experiment-audit`,
`adversarial-review`, `research_review_loop` pipeline,
`classify-capability`, `concurrent-work-check`.
**Exit to DONE**: no fatal findings; ≤1 fixable serious; one-sentence
test passes; ablations isolate contribution; explicit human approval.

### 3.6 CLI verbs — the state machine's I/O surface

The CLI is the only way the state machine transitions. See
`docs/PROJECT.md` §9 Public API for the target surface. The full
verb list and semantics:

```bash
# ─── Project lifecycle ─────────────────────────────────────────────────

alpha-research project init <name>
    [--code <absolute_path>]
    [--question "..."]
    [--venue RSS|CoRL|IJRR|T-RO|RA-L|ICRA|IROS]
    [-o <parent_dir>]

alpha-research project stage [<project_dir>]
alpha-research project advance [<project_dir>] [--force] [--note "..."]
alpha-research project backward <trigger> [<project_dir>]
    [--evidence <record_id>] [--note "..."]
alpha-research project log [<project_dir>]
alpha-research project status [<project_dir>]

# ─── Stage-bound actions ───────────────────────────────────────────────

alpha-research observe <exp_id> [<project_dir>]
alpha-research calibrate <project_dir> --papers <id1,id2,...>
alpha-research provenance [<project_dir>]
    [--since <stage>] [--action <type>] [--limit N]
alpha-research skill <skill_name> [--project <dir>] [args...]

# ─── Pipeline wrappers (already exist; become stage-aware) ─────────────

alpha-research survey <query> [-o <project_dir>]         # SIGNIFICANCE only
alpha-research evaluate <paper_id> [-o <project_dir>]    # SIGNIFICANCE|APPROACH
alpha-research review <draft.md> [-o <project_dir>]      # VALIDATE only
alpha-research significance <problem> [-o <project_dir>] # SIGNIFICANCE only
alpha-research loop <project_dir>                        # VALIDATE only
```

**Guard semantics**: `project advance` NEVER transitions without the
guard passing, except with `--force + --note`. The `--force` path
records an `override_reason` field in the stage transition — the
cheating is visible in provenance.

**Backward semantics**: `project backward` can be invoked by the
human directly OR proposed by a skill (written to
`state.open_triggers`). The skill never executes the backward
transition itself; only the CLI verb does, and the human must
confirm.

### 3.7 The experiment interface (convention, not platform)

See `docs/PROJECT.md` §11 The Experiment Interface for the full
specification. Summary:

- Experiments live under `<code_dir>/experiments/<exp_id>/` — **next
  to the method code**, not inside the project directory
- One `config.yaml` per experiment (written by `experiment-design`)
- One `results.jsonl` per experiment with one JSON object per trial
  — **THE hard contract**
- Optional `logs/`, `checkpoints/`, `notes.md`, `provenance_ref.txt`
- Any launcher that writes `results.jsonl` can be consumed by
  `experiment-analyze` — 10 lines of Python to adapt
- Reproduction mode is the g3 hard guard: before leaving DIAGNOSE,
  at least one published baseline must be reproduced within
  tolerance per in-scope benchmark

### 3.8 The four new skills (specifications)

**`benchmark-survey`** (new, ~200 lines SKILL.md, Sonnet)

- **Inputs**: `project.md`, `formalization.md`, literature via
  `alpha_review.apis.search_all` / `s2_citations` / Papers With Code
  / benchmark READMEs, prior `benchmark_surveys.jsonl`
- **Actions**:
  1. Extract problem class from `formalization.md` (observation
     type, action type, task semantics, info structure)
  2. Query literature for the 5-20 most common benchmarks used by
     papers addressing this class. Prefer: Papers With Code
     leaderboards, benchmark survey papers, "Experiments" sections of
     top venues, community-maintained suites (RLBench, Meta-World,
     LIBERO, CALVIN, RoboSuite, ManiSkill, Open X-Embodiment, NIST
     ATB, FurnitureBench, ...)
  3. For each candidate: task scope, observation/action spaces,
     standard metrics, success criterion, top published baselines
     with numbers (≥3 if available), recent-year score trend,
     install pointer, hardware requirements, community usage volume
  4. Rank candidates by coverage of the formalization's core
     challenge, non-saturation, community acceptance, and install
     effort
  5. Flag candidates that are saturated, misaligned, or abandoned
  6. Produce a ranked proposal markdown (5-10 pages) the researcher
     reads before writing `benchmarks.md`
- **Outputs**: `benchmark_surveys.jsonl` + `benchmark_proposal.md`
- **Stage**: FORMALIZE (primary), APPROACH (scope-check)
- **Honesty**: cannot verify install instructions work, cannot know
  compute budget, cannot judge whether the benchmark's notion of
  "success" aligns with what the researcher cares about. Sets
  `human_flag: true` on every recommendation.

**`experiment-design`** (new, ~200 lines SKILL.md, Opus)

- **Inputs**: `formalization.md`, `benchmarks.md` (required — this
  is the evaluation contract), `challenges.jsonl`, `one_sentence.md`,
  `source.md`, prior `experiment_designs.jsonl`, `review_config.yaml`
- **Three modes**:
  - **`reproduction`** (DIAGNOSE entry): target a specific published
    baseline from `benchmarks.md`, produce a config that mirrors the
    baseline's setup as faithfully as possible, with `reproduction_of`
    and `target_metric` in the config
  - **`diagnostic`** (DIAGNOSE): target a specific formalization
    term suspected of causing failure — produce a config with
    conditions that vary exactly that term
  - **`approach`** (APPROACH / VALIDATE): target a specific claim
    about the method — produce treatment/control/ablations that
    isolate the claimed contribution
- **Actions**: enumerate required baselines per `doctrine §8.2` and
  `review_guideline §3.5.1` (in approach mode, always include the
  strongest prior recorded in `benchmarks.md`); compute trial counts
  per venue (`review_plan §1.6`); enumerate ablations that isolate
  (not composite); pre-register failure modes from diagnosis history;
  emit `config.yaml` into `<code_dir>/experiments/<exp_id>/`
- **Outputs**: `experiment_designs.jsonl` + the config file
- **Stage**: DIAGNOSE (reproduction + diagnostic), APPROACH, VALIDATE
- **Honesty**: cannot know whether the proposed experiment is
  physically feasible — human confirms before launch

**`experiment-analyze`** (new, ~200 lines SKILL.md, Sonnet)

- **Inputs**: `<code_dir>/experiments/<exp_id>/{config.yaml, results.jsonl, notes.md}`,
  `formalization.md`, `one_sentence.md`, `benchmarks.md`
- **Mode-aware**:
  - **`reproduction`**: compute aggregate from `results.jsonl`,
    compare to `target_metric` (from config, copied from
    `benchmarks.md`'s `published_baselines`), emit
    `reproducibility: pass` (within ±10%) / `partial` (within 20%)
    / `fail` (outside tolerance). **Failing reproduction does NOT
    auto-propose a backward trigger** — first check setup bugs
    (wrong install, wrong version, wrong hyperparameters, different
    hardware). Only after setup is confirmed does the skill
    consider the failure structural and propose `t4` or `t7`.
  - **`diagnostic`**: check whether the hypothesized failure mode
    fired, and whether for the hypothesized reason. Propose `t4` if
    failure doesn't map to the formal term the experiment was
    designed around.
  - **`approach`**: full audit + trigger proposals per below
- **Actions (all modes)**:
  1. Run `scripts/audit_stats.py` on `results.jsonl` for trial
     counts, CI, variance, effect size
  2. Compare observed outcomes against `pre_registered_failure_modes`
  3. Detect: hypothesis held? new unexpected failure modes?
     ablation supports contribution? reproduction matches published?
  4. Propose zero or more backward triggers:
     - reproduction fails after setup confirmed → `t4` or `t7`
     - observed failures didn't match formal terms → `t4`
     - new failure modes emerged → `t8`
     - ablation shows contribution is doing nothing → `t15`
     - method is effectively a prior method's variant → `t5`
  5. Write a `finding` record with mode-specific verdict
- **Outputs**: `experiment_analyses.jsonl` (with `reproducibility`
  field when reproduction), `findings.jsonl`, possible
  `open_triggers` append
- **Stage**: DIAGNOSE (reproduction + diagnostic) or VALIDATE (approach)

**`project-understanding`** (new, ~150 lines SKILL.md, Sonnet)

- **Inputs**: `state.code_dir`, `project.md`, `formalization.md`
- **Actions**:
  1. Walk the code tree (respect `.gitignore`)
  2. Identify entry points (`main.py`, `train.py`, `eval.py`, ...)
  3. Identify method module, config files, data loaders, eval harness
  4. Extract the loss function(s) from training code
  5. Compare the extracted loss to `formalization.md`'s objective —
     flag any mismatch as a formalization-implementation gap
  6. Write `source.md` with sections: *Entry points*, *Method module*,
     *Training loop*, *Evaluation harness*, *Data handling*,
     *Formalization↔code correspondence*, *Open questions*
- **Outputs**: `source.md`
- **Stage**: any stage after `code_dir` is set; typically first at DIAGNOSE entry
- **Honesty**: cannot run the code; cannot judge whether the
  architecture is correct; flags everything inferential

### 3.9 Skill stage-awareness

Every SKILL.md gains a `research_stages:` frontmatter field listing
the stages where the skill is valid. The CLI's skill invoker checks
this and **warns (never blocks)** when the project is out-of-stage.

| Skill | Valid stages |
|---|---|
| `significance-screen` | SIGNIFICANCE |
| `gap-analysis` | SIGNIFICANCE |
| `frontier-mapping` (pipeline) | SIGNIFICANCE |
| `paper-evaluate` | SIGNIFICANCE, APPROACH |
| `literature-survey` (pipeline) | SIGNIFICANCE |
| `formalization-check` | FORMALIZE, APPROACH |
| `benchmark-survey` *(new)* | FORMALIZE, APPROACH |
| `project-understanding` *(new)* | DIAGNOSE, APPROACH (any stage after `code_dir` set) |
| `diagnose-system` | DIAGNOSE |
| `experiment-design` *(new)* | DIAGNOSE (reproduction + diagnostic modes), APPROACH, VALIDATE |
| `experiment-analyze` *(new)* | DIAGNOSE, VALIDATE |
| `challenge-articulate` | CHALLENGE |
| `concurrent-work-check` | CHALLENGE, APPROACH, VALIDATE |
| `method_survey` (pipeline) | CHALLENGE, APPROACH |
| `identify-method-gaps` | APPROACH |
| `experiment-audit` | VALIDATE |
| `adversarial-review` | VALIDATE |
| `research_review_loop` (pipeline) | VALIDATE |
| `classify-capability` | SIGNIFICANCE, VALIDATE |

The enforcement is **soft** (warn) because researchers need escape
hatches: sometimes you re-run `paper-evaluate` in VALIDATE to
double-check a claimed concurrent work. `--force` silences the
warning and records the override in provenance.

### 3.10 Phase-by-phase execution

#### Phase 0 — Cut and consolidate *(1 day, net deletion)*

1. `rm -rf frontend/ src/alpha_research/api/`
2. `rm -rf src/alpha_research/projects/` (after moving any still-needed logic)
3. Write `src/alpha_research/project.py` (~100 lines) per §3.3
4. `rm -rf src/alpha_research/knowledge/`
5. `rm src/alpha_research/tools/report.py`
6. `ln -sfn ../skills .claude/skills` — **the single highest-leverage
   one-line change in the whole plan**. Without this, Claude Code
   never loads any of the 15 skills we wrote.
7. Trim `pyproject.toml` (remove `fastapi`, `uvicorn`, `sse-starlette`;
   remove api entrypoint if any)
8. Trim `main.py` — remove `project create|list|show|status|snapshot|resume`
   subcommands, keep only the new `project init|stage|advance|backward|log|status`
   verbs (added in Phase 2)
9. Fix any broken imports; run `pytest`

**Acceptance**: tests pass; `python -c "import alpha_research"`
succeeds; `ls .claude/skills/` shows the 15 skills; line count of
`src/alpha_research/` down by ≥2,500.

#### Phase 1 — State machine wiring *(2 days)*

1. Extend `src/alpha_research/pipelines/state_machine.py`:
   - `stage_guard_check(stage, project_dir) -> GuardCheck`
   - `advance_transition(project_dir, force=False, note=None) -> StageTransition`
   - `backward_transition(project_dir, trigger, evidence, note) -> StageTransition`
   - `detect_backward_triggers(finding_or_review) -> list[str]`
   - All functions are pure over (disk, inputs) → disk + return value
2. Write `src/alpha_research/records/state.py` — `load_state`,
   `save_state`, `append_transition`, `append_open_trigger`,
   `resolve_open_trigger`. All operate on `<project_dir>/state.json`
3. Add `provenance` as a record type in `records/jsonl.py`. Add a
   `log_action(project_dir, action_type, action_name, inputs, outputs,
   parent_ids, summary)` helper
4. Unit test every guard `g1..g5` and every trigger `t2..t15` with
   fixture project directories. ~40 new tests

**Acceptance**: `pytest tests/test_pipelines/test_state_machine.py`
exhaustively covers guards and triggers. No integration; pure
functions over file fixtures.

#### Phase 2 — Artifact templates and project lifecycle CLI *(2 days)*

1. Add templates under `src/alpha_research/templates/project/`:
   - `project.md.j2` — question, task, why-now, scope, assumptions
   - `hamming.md.j2` — 10-slot template, empty slots for the human
   - `formalization.md.j2` — five-component structure from
     `doctrine/problem_formulation_guide.md`
   - `benchmarks.md.j2` — sections: *In scope* (with per-benchmark
     subsection template: rationale, variant, metrics, success
     criterion, published baselines with numbers, install recipe,
     reproducibility status, saturation risk), *Considered but rejected*
   - `one_sentence.md.j2` — placeholder + "what it should NOT look like" examples
   - `log.md.j2` — weekly log preamble
2. Add CLI verbs in `main.py`:
   - `project init` — scaffolds a project directory
   - `project stage` — reads state.json + guards and renders
   - `project advance` — runs `advance_transition`
   - `project backward` — runs `backward_transition`
   - `project log` — opens `$EDITOR` on LOGS.md with an appended weekly section
   - `project status` — one-screen summary
3. Integration tests: create a project, advance it from SIGNIFICANCE
   to FORMALIZE (mocking the significance-screen skill with a passing
   fixture record), confirm state.json and provenance.jsonl are
   written correctly

**Acceptance**: a researcher can run `alpha-research project init
foo -q "tactile insertion" -c /home/me/code` and see the scaffold;
`project stage` prints the initial state.

#### Phase 3 — Wire existing skills to the state machine *(2 days)*

1. Add `research_stages:` frontmatter field to each of the 11
   existing SKILL.md files per §3.9
2. Add a stage-check helper `check_skill_stage(skill_name,
   project_stage)` used by `main.py`'s skill invoker and by
   pipelines
3. Pipelines (`literature_survey`, `method_survey`, `frontier_mapping`,
   `research_review_loop`) start calling:
   - `check_skill_stage` on entry, warning if out of stage
   - `log_action` for every meaningful step
4. Wire `significance-screen` to read `<project_dir>/hamming.md`
   (currently it reads `guidelines/hamming_list.md` which is the
   wrong location)
5. Wire `formalization-check` to read `<project_dir>/formalization.md`
   as its primary input when invoked inside a project

**Acceptance**: a skill invoked via `alpha-research skill ...` logs
to provenance, warns on out-of-stage, reads artifacts from the
project.

#### Phase 4 — Source binding and `project-understanding` skill *(1 day)*

1. Add `code_dir` handling in `project init` and `ProjectState`
2. Write `skills/project-understanding/SKILL.md` per §3.8
3. Update `formalization-check` to optionally read `source.md` for
   the formalization↔implementation gap check
4. Integration test: point a project at a tiny fake `code_dir`, run
   `project-understanding`, verify `source.md` is produced

**Acceptance**: running `alpha-research skill project-understanding
-p foo` produces a `source.md`.

#### Phase 5 — Benchmark survey and selection *(2 days)*

1. Write `skills/benchmark-survey/SKILL.md` per §3.8 (~200 lines)
2. Add `benchmark_surveys` to the supported record types in
   `records/jsonl.py` (one-line addition)
3. Tighten `stage_guard_check(FORMALIZE, ...)` (conditions 5 and 6):
   require `benchmarks.md` to exist with at least one benchmark in
   "In scope" carrying a rationale, success criterion, ≥1 published
   baseline number, and saturation assessment. Require the latest
   `benchmark_survey` record to have `human_confirmed: true`. Add
   the new guard-condition tests
4. Tighten `stage_guard_check(DIAGNOSE, ...)` (condition 1): require
   that for every in-scope benchmark there exists ≥1
   `experiment_analysis` record with mode=`reproduction` and
   `reproducibility ∈ {pass, partial}`. Add the corresponding tests
5. Update the `benchmarks.md.j2` template with a worked example for
   one benchmark so researchers have a concrete pattern
6. Integration test: fixture project with a stub `benchmark_survey`
   record and a hand-written `benchmarks.md`; `project advance` from
   FORMALIZE passes only after both conditions 5 and 6 are met

**Acceptance**: a project cannot leave FORMALIZE without
`benchmarks.md` populated, and cannot leave DIAGNOSE without at
least one reproduction experiment recorded per in-scope benchmark.

#### Phase 6 — Experiment interface: design and analyze *(3 days)*

1. Write `guidelines/architecture/experiment_interface.md` — the
   convention spec (1 page) [already exists — update to reference docs/]
2. Write `skills/experiment-design/SKILL.md` per §3.8 with all three
   modes. Reproduction mode reads `benchmarks.md` to target a
   specific published baseline number
3. Write `skills/experiment-analyze/SKILL.md` per §3.8 with
   mode-aware behavior. Reproduction mode compares measured
   aggregate against `benchmarks.md`'s `published_baselines` and
   writes a `reproducibility: pass|partial|fail` field
4. Extend `scripts/audit_stats.py` if needed to support the
   `results.jsonl` schema directly. Currently it already reads
   CSV/JSON; add jsonl
5. Wire `experiment-analyze` to append open triggers to `state.json`
   when it detects `t4 / t5 / t7 / t8 / t15`
6. Integration test: a synthetic experiment directory with a known
   outcome, run `experiment-analyze`, verify the correct trigger is
   proposed. Include a fixture that exercises reproduction-pass and
   reproduction-fail paths explicitly

**Acceptance**: a researcher can run `alpha-research skill
experiment-design -p foo --mode reproduction --benchmark <id>` in
DIAGNOSE stage and get a `config.yaml`; after running it,
`experiment-analyze` records a reproducibility verdict that gates
`g3`.

#### Phase 7 — Diagnose-system and challenge-articulate integration *(1 day)*

1. Update `diagnose-system` skill to read from
   `experiments/<exp_id>/` in `code_dir` rather than expecting a
   verbal failure taxonomy as input
2. Update `challenge-articulate` skill to read `diagnoses.jsonl` for
   the current stage's diagnosis rather than accepting it as argument
3. Both skills log to provenance with `parent_ids` linking to the
   experiment_analyses or diagnoses that motivated them

**Acceptance**: a synthetic project in DIAGNOSE stage with one
completed experiment can advance through DIAGNOSE → CHALLENGE →
APPROACH by invoking the appropriate skills, with `state.json`
tracking each transition.

#### Phase 8 — Observe, log, calibrate commands *(1 day)*

1. `alpha-research observe <exp_id>` — opens `$EDITOR` on a
   failure-note template; saves to `notes.md`; appends a structured
   record; prompts for `diagnose-system` invocation
2. `alpha-research log` is already in Phase 2
3. `alpha-research calibrate` — reads `calibration/human_scores.jsonl`,
   runs `paper-evaluate` on each paper, prints a per-dimension
   score-delta table
4. `alpha-research provenance` — renders the provenance tree (flat
   list with timestamps or indented by parent_id DAG)

**Acceptance**: all six cross-stage commands (`observe`, `log`,
`calibrate`, `provenance`, `status`, `stage`) are functional and
covered by CLI tests.

#### Phase 9 — End-to-end integration test *(2 days)*

A single pytest that walks a synthetic project through all six
stages, invoking mocked versions of each skill, exercising at least
one backward transition, and verifying:

1. Every stage transition is logged to `state.json` and `provenance.jsonl`
2. Every guard is checked before advancing
3. A backward trigger proposed by a skill lands in `open_triggers`
4. `project backward` resolves the trigger and updates the carried
   constraint
5. At VALIDATE, a review with no fatal flaws transitions to DONE
6. `alpha-research provenance` can trace a finding back to the
   formalization version that motivated the experiment that produced
   it

**Acceptance**: `pytest tests/test_integration/test_full_loop.py`
passes with no network calls and no real LLM invocations.

#### Phase 10 — Documentation and cleanup *(0.5 days)*

1. Update root `README.md` with the new CLI (the `project init/stage/
   advance/backward/log/observe/calibrate/provenance` verbs) — already
   done as part of the docs-consolidation migration
2. Update `docs/PROJECT.md` with a "State machine integration" note
3. Add a *Walkthrough* section to `docs/PROJECT.md`: "From zero to a
   published paper — the full loop in 20 commands"
4. Delete any now-stale sections of `guidelines/history/TASKS.md` or
   mark them fully superseded — **deleted entirely in the docs
   consolidation migration**; historical narrative absorbed into
   `docs/DISCUSSION.md`

**Acceptance**: a new researcher landing on the repo can follow the
walkthrough and reach a toy published state in under an hour.

### 3.11 Running totals

| Phase | Lines added | Lines deleted | Days |
|---|---:|---:|---:|
| 0. Cut and consolidate | +100 | −3,000 | 1 |
| 1. State machine wiring | +400 (code+tests) | 0 | 2 |
| 2. Artifact templates + CLI | +400 | −100 (main.py trim) | 2 |
| 3. Skill stage-awareness wiring | +150 | 0 | 2 |
| 4. Source binding + `project-understanding` skill | +200 (mostly markdown) | 0 | 1 |
| 5. Benchmark survey + `benchmark-survey` skill + g2/g3 tightening | +350 (mostly markdown) | 0 | 2 |
| 6. Experiment interface + `experiment-design` + `experiment-analyze` | +550 (mostly markdown) | 0 | 3 |
| 7. Diagnose + challenge rewiring | +100 | −50 | 1 |
| 8. Observe / log / calibrate / provenance | +300 | 0 | 1 |
| 9. End-to-end integration test | +450 | 0 | 2 |
| 10. Docs | +200 | −200 | 0.5 |
| **Total** | **+3,200** | **−3,350** | **~17.5 working days** |

Net code delta: roughly **−150 lines**, with ~1,100 of the additions
being skill markdown rather than Python. The codebase gets materially
simpler while gaining the entire "doing research" half of the loop.

### 3.12 Plan-level acceptance criteria

The plan is complete when all of the following are true:

1. **Stage lives on disk.** Every project has a `state.json` that
   tracks current stage, history, guard status, and open triggers.
   All transitions go through the CLI.

2. **Every artifact has an owner and a home.**
   - Human-owned markdown: `PROJECT.md`, `DISCUSSION.md`, `LOGS.md`,
     `hamming.md`, `formalization.md`, `benchmarks.md`, `one_sentence.md`
   - Agent-owned markdown: `source.md`, `benchmark_proposal.md`
   - Agent-owned JSONL: all the record streams
   - CLI-owned JSON: `state.json`
   - CLI-owned append-only JSONL: `provenance.jsonl`

3. **Benchmarks are first-class.** Every project has a `benchmarks.md`
   with at least one chosen benchmark before leaving FORMALIZE, and
   at least one successfully reproduced published baseline per chosen
   benchmark before leaving DIAGNOSE. Reproducibility is a hard
   guard, not a suggestion.

4. **The doing side is wired in.** `project-understanding` reads
   code, `benchmark-survey` surfaces and ranks evaluation
   frameworks, `experiment-design` produces runnable configs
   (reproduction / diagnostic / approach modes), `experiment-analyze`
   reads results and proposes triggers. The researcher's sim
   platform, training code, and experiment launcher remain theirs.

5. **Every skill knows its stage.** Invoking a skill out of its
   valid stages produces a warning with `--force` override; the
   override is recorded in provenance.

6. **Provenance is real.** Running `alpha-research provenance` on a
   project lets a human trace any finding or review back to the
   formalization version and benchmark choice that motivated the
   experiment that produced it.

7. **The frontend and the heavy project lifecycle layer are gone.**
   The codebase is materially smaller and the CLI + `$EDITOR`
   workflow is sufficient for a single researcher.

8. **The end-to-end integration test walks all six stages** with at
   least one backward transition AND at least one reproduction-experiment
   cycle (pass path and fail path), entirely in fixtures, no network.

9. **None of the following were built**: a simulation platform, a
   training framework, a data collection UI, an experiment launcher,
   a reproducibility/containerization layer, a web dashboard, a
   multi-user collaboration feature, a daemon or autonomous
   execution mode.

---

## 4. Review Plan — Agent Architecture

**Source**: `guidelines/spec/review_plan.md` (737 lines).
Executable metrics for every review attack vector, the three-agent
architecture, and the iterative research-review interaction protocol.

### 4.1 Executable metrics summary

Each attack vector in `review_guideline.md` Part III produces a
**machine-evaluable signal** — a binary check, a numeric score, or
a structured extraction that can be programmatically verified. Vague
assessments are not acceptable outputs. See `review_plan.md` §1.1-1.8
for the full metric tables; a summary:

- **§1.1 Logical Chain Completeness**: `task_extracted`,
  `formalization_level`, `challenge_type`, `approach_follows_from_challenge`,
  `one_sentence_test`, `chain_coherent`, `broken_links`. Chain
  completeness = non-null fields / 5. <0.6 = fatal structural flaw.
- **§1.2 Significance Metrics**: `hamming_score`,
  `concrete_consequence`, `durability_risk`, `compounding_value`,
  `motivation_type`, `concurrent_coverage`
- **§1.3 Formalization Metrics**: `formalization_level`,
  `framework_mismatch`, `structure_exploited`, `reduces_to_known`,
  `assumptions_explicit`, `formal_impl_gap`
- **§1.4 Challenge Metrics**: `challenge_type`,
  `challenge_constrains_solution`, `evidence_supports_challenge`,
  `prior_solution_exists`, `challenge_specificity`
- **§1.5 Approach Metrics**: `method_interchangeable`,
  `nearest_prior_method`, `structural_delta`, `uses_identified_structure`,
  `ablation_supports_claim`
- **§1.6 Validation Metrics** (experimental design + robotics-specific
  + overclaiming): `baselines`, `includes_simple/oracle/sota`,
  `strongest_missing_baseline`, `ablation_isolates_contribution`,
  `trials_per_condition`, `has_confidence_intervals`, `validation_type`,
  `robot_count`, `contact_modeled`, `sensing_appropriate`,
  `reproducibility_score`, overclaiming patterns
- **§1.7 Novelty Metrics**: `closest_prior`, `differentiation`,
  `contribution_type`, `missing_refs`
- **§1.8 Review Quality Metrics** (meta-review): `actionable_points`,
  `grounded_points`, `vague_critiques`, `falsifiable_points`,
  `steel_man_length`, classification consistency. Thresholds:
  actionability ≥80%, grounding ≥90%, vague critiques = 0,
  falsifiability ≥70%, steel-man ≥3 sentences.

### 4.2 Agent architecture — centralized orchestrator with specialized sub-agents

```
                          ┌─────────────────────────┐
                          │      ORCHESTRATOR        │
                          │                          │
                          │  Owns: shared blackboard │
                          │  Owns: convergence logic │
                          │  Owns: human checkpoint  │
                          │         routing          │
                          └────────┬────────────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
        ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
        │  RESEARCH   │    │   REVIEW    │    │    META-    │
        │   AGENT     │    │   AGENT     │    │  REVIEWER   │
        │             │    │             │    │             │
        │ Produces    │    │ Attacks per │    │ Evaluates   │
        │ research    │    │ review_     │    │ review      │
        │ artifacts   │    │ guideline   │    │ quality     │
        │ per research│    │             │    │ per §1.8    │
        │ guideline   │    │             │    │ metrics     │
        └─────────────┘    └─────────────┘    └─────────────┘
```

**Why three agents, not two**: the meta-reviewer prevents mode
collapse between research and review. If the review agent produces
vague or toothless critiques, the meta-reviewer catches it. If the
review agent is unfairly harsh, the meta-reviewer catches that too.
This mirrors the area chair role at RSS / NeurIPS — someone who
reviews the reviews.

### 4.3 The shared blackboard

All agents read from and write to a shared state object persisted
to disk between iterations:

```python
class Blackboard(BaseModel):
    artifact: ResearchArtifact           # The current paper/proposal/analysis
    artifact_version: int
    artifact_history: list[ArtifactDiff]

    current_review: Review | None
    review_history: list[Review]

    review_quality: ReviewQualityReport | None

    iteration: int
    convergence_state: ConvergenceState
    human_decisions: list[HumanDecision]

    target_venue: Venue
    review_mode: Literal["full", "focused", "quick"]
```

### 4.4 Iteration protocol

```
ORCHESTRATOR MAIN LOOP

iteration = 0
while not converged(blackboard):
    iteration += 1

    ┌─── PHASE 1: RESEARCH ───────────────────────────┐
    │  if iteration == 1: research_agent.generate()    │
    │  else: research_agent.revise(focus=prev_findings)│
    │  blackboard.artifact_version += 1                │
    └──────────────────────────────────────────────────┘

    ┌─── PHASE 2: REVIEW ─────────────────────────────┐
    │  review = review_agent.review(blackboard)        │
    │  ┌── PHASE 2a: META-REVIEW ──────────────────┐  │
    │  │  quality = meta_reviewer.check(review)    │  │
    │  │  if not quality.passes:                   │  │
    │  │    review = review_agent.revise_review()  │  │
    │  │    (max 2 meta-review rounds)             │  │
    │  └───────────────────────────────────────────┘  │
    └──────────────────────────────────────────────────┘

    ┌─── PHASE 3: HUMAN CHECKPOINT (conditional) ─────┐
    │  Trigger when:                                    │
    │  - ≥1 finding marked low-confidence on           │
    │    significance or formalization                  │
    │  - Research agent triggers backward → SIGNIFICANCE│
    │  - iteration ≥ max_iterations - 1                │
    │  - Review verdict is ACCEPT (final check)        │
    └──────────────────────────────────────────────────┘

    ┌─── PHASE 4: CONVERGENCE CHECK ──────────────────┐
    │  converged = check_convergence(blackboard)       │
    └──────────────────────────────────────────────────┘
```

### 4.5 Convergence criteria (four independent stopping conditions)

**Condition 1 — Quality Threshold Met**:
```python
def quality_met(review):
    return (
        len(review.fatal_flaws) == 0 and
        len(review.serious_weaknesses) <= 1 and
        all(w.fixable for w in review.serious_weaknesses) and
        review.verdict in [Verdict.ACCEPT, Verdict.WEAK_ACCEPT]
    )
```

**Condition 2 — Human Approval**: human explicitly approves.

**Condition 3 — Iteration Limit**: hard cap at 5 iterations.
Rationale: multi-agent debate literature shows 94.2% convergence
within 5 iterations; Self-Refine shows diminishing returns after 2-3;
MART red-teaming converges in 4 rounds. 5 is a safe upper bound.

**Condition 4 — Stagnation Detection**:
```python
def stagnated(blackboard):
    prev = blackboard.review_history[-2]
    curr = blackboard.review_history[-1]
    return (
        set_of_attack_vectors(prev) == set_of_attack_vectors(curr) and
        prev.verdict == curr.verdict
    )
```

If stagnated, the orchestrator escalates to human or stops.

### 4.6 Graduated adversarial pressure

Inspired by MART (Multi-round Automatic Red-Teaming), the review
agent increases its scrutiny across iterations:

| Iteration | Review Depth | Attack Focus |
|---|---|---|
| 1 | **Structural scan** | Chain completeness, significance gate, formalization presence. Quick-reference checklist only. |
| 2 | **Full review** | All attack vectors from §3.1-3.6. Complete three-pass protocol. |
| 3 | **Focused re-review** | Only the findings from iteration 2 that the research agent claimed to address. Plus: regression check. |
| 4+ | **Residual scan** | Only unresolved findings. Pairwise comparison of current vs. previous. |

### 4.7 Anti-collapse mechanisms

1. **The meta-reviewer** — structural defense. Measures review
   quality independently and rejects declining reviews.
2. **Quantified findings vs. gestalt.** Review agent produces
   `Finding` objects with all fields filled, not prose reviews.
3. **Monotonic severity rule.** Fatal/serious findings cannot be
   downgraded in iteration N+1 without explicit evidence.
4. **Cross-iteration tracking.** `finding_resolution_rate` — fraction
   of previous findings marked addressed. Below 50% flags the
   research agent as ignoring findings.
5. **Fresh-eyes pass.** Final iteration re-reviews from scratch
   without seeing prior reviews — catches issues masked by iterative
   tunnel vision.

### 4.8 Stage-level review

The review agent doesn't only review full paper drafts. It reviews
artifacts at every stage of the research state machine:

| Research Stage | Artifact | Review Focus | Primary Attack Vectors |
|---|---|---|---|
| **SIGNIFICANCE** | Significance argument | §3.1 only | Hamming, Consequence, Durability, Compounding |
| **FORMALIZE** | Formal problem definition | §3.1 + §3.2 | Absent formalization, wrong framework, missing structure, trivial special case |
| **DIAGNOSE** | Failure analysis of minimal system | §3.3 | Resource complaint, challenge-approach disconnect |
| **CHALLENGE** | Challenge statement | §3.3 + §3.4 (partial) | All §3.3 |
| **APPROACH** | Method description + justification | §3.4 | All §3.4 |
| **VALIDATE** | Experimental results + analysis | §3.5 + §3.6 | All §3.5 + §3.6 |
| **full_draft** | Complete paper | ALL attack vectors | Everything |

Catching a significance failure at the SIGNIFICANCE stage saves
months of wasted work on formalization, approach, and experiments.
The earlier a flaw is caught, the cheaper the fix.

### 4.9 Configuration (`review_config.yaml`)

```yaml
target_venue: "RSS"

iteration:
  max_iterations: 5
  meta_review_max_rounds: 2
  stagnation_threshold: 2

convergence:
  quality_threshold:
    max_fatal: 0
    max_serious: 1
    min_verdict: "weak_accept"

graduated_pressure:
  iteration_1: "structural_scan"
  iteration_2: "full_review"
  iteration_3_plus: "focused_rereview"

human_checkpoints:
  on_backward_to_significance: true
  on_low_confidence_significance: true
  on_low_confidence_formalization: true
  on_final_accept: true
  periodic: 3

review_quality_thresholds:
  min_actionability: 0.80
  min_grounding: 0.90
  max_vague_critiques: 0
  min_falsifiability: 0.70
  min_steel_man_sentences: 3

anti_collapse:
  monotonic_severity: true
  min_finding_resolution: 0.50
  fresh_eyes_final: true
```

---

## 5. Active TODO List

Updated continuously. Items are removed when complete.

### 5.1 Highest priority (Phase 0)

- [ ] **Delete `frontend/` and `src/alpha_research/api/`** — legacy
  Next.js dashboard + FastAPI backend + CopilotKit adapter. Deferred
  per `docs/DISCUSSION.md` project lifecycle debate.
- [ ] **Collapse `src/alpha_research/projects/` into a 100-line
  `project.py`** — replaces the ambitious ProjectManifest /
  ProjectState / ProjectSnapshot lifecycle layer with the
  "directory is state" model.
- [ ] **Delete `src/alpha_research/knowledge/`** — the SQLite store
  shim. Remaining consumers migrated off already in R2/R6.
- [ ] **Delete `src/alpha_research/tools/report.py`** — 12-line
  backward-compat shim; `reports/templates.py` has the real code.
- [ ] **`ln -sfn ../skills .claude/skills`** — activates the 15
  skills for Claude Code. The single highest-leverage one-line
  change in the whole plan.
- [ ] **Trim `pyproject.toml`** — remove `fastapi`, `uvicorn`,
  `sse-starlette`, and the API entrypoint.
- [ ] **Trim `main.py`** — remove `project create|list|show|status|
  snapshot|resume` subcommands; keep only
  `project init|stage|advance|backward|log|status` for Phase 2.

### 5.2 Phase 1 priority (state machine wiring)

- [ ] **Extend `pipelines/state_machine.py`** with `stage_guard_check`,
  `advance_transition`, `backward_transition`,
  `detect_backward_triggers`
- [ ] **Write `records/state.py`** — load/save state.json, append
  transitions, append/resolve open triggers
- [ ] **Add `provenance` record type** to `records/jsonl.py`;
  `log_action` helper
- [ ] **~40 unit tests** for every guard `g1..g5` and every trigger
  `t2..t15` with fixture project directories

### 5.3 Phase 2 priority (templates + CLI)

- [ ] **Add project templates** under `templates/project/`:
  `project.md.j2`, `hamming.md.j2`, `formalization.md.j2`,
  `benchmarks.md.j2`, `one_sentence.md.j2`, `log.md.j2` (existing
  `PROJECT.md.j2`, `DISCUSSION.md.j2`, `LOGS.md.j2` remain)
- [ ] **Add `project init|stage|advance|backward|log|status` CLI
  verbs** in `main.py`
- [ ] **Integration test**: scaffold a project, advance from
  SIGNIFICANCE to FORMALIZE with mock skill, confirm state.json
  and provenance.jsonl

### 5.4 Phase 3-4 priority (skill wiring + source binding)

- [ ] **Add `research_stages:` frontmatter** to each of the 11
  existing SKILL.md files
- [ ] **`check_skill_stage(skill_name, project_stage)` helper**
- [ ] **Pipelines log to provenance** via `log_action` on every
  meaningful step
- [ ] **Wire `significance-screen` to read `<project_dir>/hamming.md`**
- [ ] **Wire `formalization-check` to read `<project_dir>/formalization.md`**
- [ ] **Write `skills/project-understanding/SKILL.md`** per §3.8
- [ ] **Update `formalization-check` to optionally read `source.md`**
  for the formalization↔implementation gap check

### 5.5 Phase 5 priority (benchmarks)

- [ ] **Write `skills/benchmark-survey/SKILL.md`** per §3.8 (~200 lines)
- [ ] **Add `benchmark_surveys` record type** to `records/jsonl.py`
- [ ] **Tighten `g2` and `g3`** per §3.10 Phase 5

### 5.6 Phase 6 priority (experiments)

- [ ] **Write `skills/experiment-design/SKILL.md`** per §3.8 (~200 lines,
  three modes)
- [ ] **Write `skills/experiment-analyze/SKILL.md`** per §3.8 (~200 lines,
  mode-aware)
- [ ] **Extend `scripts/audit_stats.py`** to read `results.jsonl`
  directly if needed
- [ ] **Wire `experiment-analyze` to append open triggers** on
  detection of `t4 / t5 / t7 / t8 / t15`

### 5.7 Phase 7-10 priority (integration)

- [ ] **Update `diagnose-system`** to read `experiments/<exp_id>/`
  rather than verbal failure taxonomy
- [ ] **Update `challenge-articulate`** to read `diagnoses.jsonl`
- [ ] **Add `observe / log / calibrate / provenance`** CLI verbs
- [ ] **End-to-end integration test** walking all six stages +
  ≥1 backward transition + reproduction-pass + reproduction-fail paths

### 5.8 Documentation tasks (this migration)

- [x] Write `docs/PROJECT.md` (consolidated doctrine + architecture + spec)
- [x] Write `docs/PLAN.md` (this file)
- [x] Write `docs/SURVEY.md` (venue calibration + methodology surveys)
- [x] Write `docs/DISCUSSION.md` (design decisions + migration history)
- [x] Write `docs/LOGS.md` (seeded from LOG.md + this migration entry)
- [x] Rewrite `README.md` to delegate to docs/
- [x] Copy `scripts/check_docs.py` and `scripts/install_hooks.sh`
- [ ] Delete `guidelines/` directory
- [ ] Delete `LOG.md` (content now in `docs/LOGS.md`)

---

## 6. Open Questions

### 6.1 Should `alpha_research` keep `projects/` and `api/` around a little longer?

**Context**: Phase 0 of the integrated plan deletes both. But the
FastAPI server + Next.js frontend + CopilotKit adapter + Cytoscape
knowledge graph + Elicit-style evaluation table did work at one
point and some users may still find the UI useful.

**Options**:
1. Delete both in Phase 0 as planned (simplest, smallest codebase)
2. Keep both until the CLI loop is proven sufficient
3. Move both to a separate `alpha_research_frontend` project

**Decision**: Option 1. The integrated plan is explicit that the
CLI + `$EDITOR` workflow is sufficient for a single researcher, and
the frontend is in `docs/PLAN.md` §8 Archive as a possible Phase-2
delivery once the research loop proves useful. Parked for Phase-2.

### 6.2 Model assignment per skill

**Context**: the 15-skill inventory in §3.9 assigns Haiku / Sonnet /
Opus per skill. Multi-model pipelines are a cost optimization; the
integrated plan explicitly defers this as "premature until the loop
works."

**Decision**: Use the current defaults (Haiku for `paper-evaluate`
SKIM pass; Sonnet for `paper-evaluate` deep pass, `challenge-articulate`,
`adversarial-review`, `gap-analysis`, `benchmark-survey`,
`experiment-design`, `project-understanding`; Opus where marked).
Revisit after Phase 9 integration test.

### 6.3 How to handle reproducibility failures

**Context**: `experiment-analyze` in reproduction mode emits
`reproducibility: fail` when the measured aggregate is outside
tolerance. The question is what to do next.

**Decision**: Per §3.8 experiment-analyze spec: a failing
reproduction does **NOT** auto-propose a backward trigger. The first
thing to check is setup bugs (wrong install, wrong version pin,
wrong hyperparameters, different hardware). Only after the setup is
confirmed should the failure be treated as structural, at which
point the skill proposes `t4` or `t7`. The researcher confirms setup
via a human checkpoint in the `experiments/<exp_id>/notes.md` file.

### 6.4 Cross-project knowledge graph

**Context**: Today each project is isolated. A shared frontier map
or Hamming list across projects would be valuable — e.g., if
multiple projects are in "tactile manipulation," they should share
the frontier snapshot and the Hamming list.

**Decision**: Defer to Phase-2. Adds state management we don't
currently need. The researcher can copy-paste between `hamming.md`
files until a concrete need surfaces.

### 6.5 Multi-project registry

**Context**: When a researcher has 5+ active projects, a lightweight
registry becomes helpful. Until then, `ls output/` is fine.

**Decision**: Defer. Add when users report it as a pain point.

### 6.6 Snapshot/resume lineage

**Context**: The original project-lifecycle plan had git-backed
checkpointing with `git worktree`-based resume and source
fingerprinting. Phase 0 deletes all of it. Is this a loss?

**Decision**: No. `cd output/<project>` is resume. `git init` in the
project directory is versioning. The researcher runs git themselves
when they want a snapshot. See `docs/DISCUSSION.md` project
lifecycle debate for the full analysis.

### 6.7 Real-time experiment streaming

**Context**: Watching a training run live is different from analyzing
completed results; both are useful, but the latter is load-bearing
for the state machine and the former is polish.

**Decision**: The state machine consumes completed `results.jsonl`
files, not live streams. If the researcher wants live monitoring,
they use wandb or their launcher's native UI. `experiment-analyze`
runs post-hoc.

---

## 7. Risks and Rollback

### 7.1 Phase 0 risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Frontend deletion breaks a use case users depend on | Low | The integrated plan makes the CLI + `$EDITOR` sufficient; users can re-clone from git history if needed |
| `projects/` deletion orphans tests that exercise lifecycle invariants | Medium | Port the still-useful invariants (3-canonical-docs, `REQUIRED_DOCS`) into `tests/test_project_docs_invariant.py` — already done in the 2026-04-11 entry |
| `knowledge/` deletion breaks import chains | Medium | Grep for `from alpha_research.knowledge` and migrate each to `records/jsonl.py` or `alpha_review.ReviewState` |

### 7.2 Phase 1-6 risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| State machine guard conditions are too strict and block legitimate advances | Medium | `--force + --note` override path recorded in provenance |
| `experiment-analyze` auto-proposes wrong backward triggers | High | Never auto-execute; always append to `open_triggers` and require human `project backward` confirmation |
| Benchmark survey skill misses the right benchmark | Medium | Always produce a `benchmark_proposal.md` for the human to read; the human picks, not the agent |
| `project-understanding` skill hallucinates formalization↔code matches | Medium | Set `human_flag: true` on every formalization-implementation gap; require human confirmation before advancing |

### 7.3 Phase 9 integration test risks

| Risk | Likelihood | Mitigation |
|---|---|---|
| Test flakiness from skill LLM calls | High | Phase 9 uses **mocked** skills; real LLM calls only in the opt-in `-m integration` suite |
| Backward transition logic has subtle bugs | High | ~40 unit tests in Phase 1 cover every guard and trigger independently before integration |
| Provenance tree becomes unreadable at scale | Medium | `alpha-research provenance` supports `--since`, `--action`, `--limit` filters |

### 7.4 Rollback plan

Each phase is **purely additive except Phase 0** (which deletes
legacy code). To roll back:

1. For Phase 1+: revert the new files, revert patches to existing files, run `pytest`
2. For Phase 0: the legacy `frontend/`, `api/`, `projects/`, `knowledge/`, `tools/report.py` are in git history; `git checkout` restores them

**Regression guard**: the existing 323-test suite is the floor. Any
new change that breaks an existing test must be reverted before
merging.

---

## 8. Archive — Superseded Plans

These plans contributed to the design but are mostly superseded.
They are preserved for lineage; their load-bearing content has
been absorbed into `docs/PROJECT.md`, this PLAN, or
`docs/DISCUSSION.md`.

### 8.1 The ambitious project lifecycle plan (1,654 lines)

**Source**: `guidelines/history/project_lifecycle_revision_plan.md`.

**What it proposed**:
- `ProjectManifest` — stable identity
- `SourceBinding` — link to external source (git_repo, directory, paper_set)
- `ProjectState` — mutable operational head
- `SourceSnapshot` — immutable source-tree state with `commit_sha`, `patch_path`, `source_fingerprint`
- `UnderstandingSnapshot` — derived structured understanding
- `ProjectSnapshot` — immutable checkpoint binding
- `ResearchRun` — execution record
- Project registry + project service + git state + source snapshot service + resume service + snapshot writer + project orchestrator
- Git-backed checkpointing with commit/branch capture, dirty patch capture, milestone tagging, exact snapshot resume via `git worktree`
- Understanding agent lifecycle with diff-aware re-understanding on resume

**Why superseded**: the simpler "a project is a directory" model in
`guidelines/spec/implementation_plan.md` Part II makes all of this
redundant.

- `cd output/<project>` replaces `resume`
- `git init` in the project directory replaces git_state + snapshots
- `tar czf` replaces snapshots for backup
- `state.json` + `provenance.jsonl` replace the snapshot/run tracking
- The `project-understanding` skill replaces the understanding agent
- The researcher's own `git` handles versioning when they want it

The decision: delete the entire `src/alpha_research/projects/`
directory (1,300 lines) and replace with a 100-line `project.py`
containing just `ProjectState`, `init_project`, `load_state`,
`save_state`, `current_stage`, `transition`. Phase 0 of the
integrated plan executes this.

**What was absorbed**:
- The three-canonical-docs invariant (`PROJECT.md`, `DISCUSSION.md`,
  `LOGS.md`) went into `src/alpha_research/templates/__init__.py`
  as `REQUIRED_DOCS` and into `project.py` as `append_revision_log()`
- The `ProjectState` dataclass structure (simplified) went into
  `project.py`
- The understanding agent's `_understanding_prompt.py` content went
  into the new `project-understanding` skill

### 8.2 The deferred frontend plan (507 lines)

**Source**: `guidelines/history/FRONTEND.md`.

**What it proposed**:
- Next.js 15 dashboard with CopilotKit (MIT, 30k stars) for agent
  streaming (AG-UI protocol) + generative UI + human-in-the-loop
  hooks
- Three key views:
  1. **Agent Activity Panel** (left sidebar) — real-time SM-1..SM-5
     progress via SSE streaming with StepStarted/StepFinished events
  2. **Evaluation Table** (main area) — Elicit-inspired: papers as
     rows, 7 rubric dimensions as columns, click-to-expand evidence,
     TanStack Table + shadcn/ui
  3. **Knowledge Graph** (overlay/tab) — Connected Papers-inspired
     force-directed graph via Cytoscape.js: size=score,
     color=approach_type, edges=relation_type from SM-4's
     `paper_relations` table
- Tech stack: Next.js 15 + React 18 + TypeScript + Tailwind + shadcn/ui
  + Radix + TanStack Table + Cytoscape.js + Zustand + FastAPI
  + AG-UI adapter
- 9-agent parallel build plan across 5 phases

**Why deferred**: Phase 0 of the integrated plan explicitly deletes
`frontend/` and `src/alpha_research/api/`. The rationale: a
researcher using this from the CLI + `$EDITOR` loses nothing. The
frontend is a plausible Phase-2 delivery, but it is not necessary
for the research loop.

**What was absorbed**:
- The three-panel visualization pattern is preserved in
  `docs/SURVEY.md` §Open-source landscape (the STORM, Connected
  Papers, Elicit, ResearchRabbit patterns are documented there)
- The AG-UI protocol and CopilotKit evaluation is preserved in
  `docs/SURVEY.md` as open questions for a future UI revival
- The 15 critical review findings are preserved (e.g., "pipeline
  must run in `threading.Thread`, not `asyncio.Task`, because
  nested `asyncio.run` will crash the backend") in case Phase-2
  revisits the frontend

### 8.3 The R0-R9 refactor plan (738 lines)

**Source**: `guidelines/history/refactor_plan.md` +
`guidelines/history/TASKS.md` (604 lines).

**What it proposed**: migrate the T1-T10 tool-centric codebase
(10,171 lines, 494 tests) to the skills-first architecture:
- Delete `tools/arxiv_search.py`, `tools/semantic_scholar.py`,
  `tools/knowledge.py` — redundant with `alpha_review.apis.*`
- Delete `knowledge/schema.py`, `knowledge/store.py` — redundant
  with `alpha_review.models.ReviewState` + JSONL files
- Shrink `tools/report.py` → relocate to `reports/templates.py`;
  delete the survey template
- Refactor `agents/research_agent.py` (509 lines) → `pipelines/` +
  skills
- Refactor `agents/review_agent.py` (325 lines) → `pipelines/` +
  skill + `metrics/verdict.py`
- Absorb `agents/meta_reviewer.py` (138 lines) into
  `metrics/review_quality.py`
- Refactor `agents/orchestrator.py` (276 lines) →
  `pipelines/research_review_loop.py`
- Seed `prompts/*.py` (1904 lines) into SKILL.md files (10-11 skills)
- Add `records/jsonl.py`, `metrics/verdict.py`, `scripts/sympy_verify.py`,
  `scripts/audit_stats.py`
- Net: ~4,550 lines deleted + ~1,100 lines added (Python) + ~2,500
  lines added (markdown). Project gets smaller AND gains the skills
  layer.

**Status**: ✅ Complete per git log: commits `R0-R1`, `R2`, `R3`,
`R4+R5`, `R6+R7`, `R8+R9`, plus the 2026-04-11 entry adding
per-module test coverage and the three-canonical-docs invariant.

**What was absorbed**: the entire narrative of the R0-R9 journey is
in `docs/DISCUSSION.md` The R0-R9 Refactor Journey, with the key
insights distilled into `docs/PROJECT.md` §12 Takeaways from the
R0-R9 Refactor. The task-level breakdown (R0-R9 steps) is no longer
needed as actionable TODO but is preserved in DISCUSSION for context.

### 8.4 The original work plan (1,583 lines)

**Source**: `guidelines/spec/research_plan.md`.

**Status**: partially superseded. The **state machine theory**
(two-layer machine, outer SIGNIFICANCE → FORMALIZE → DIAGNOSE →
CHALLENGE → APPROACH → VALIDATE with backward triggers `t2..t15`
and forward guards `g1..g5`; SM-1 through SM-6 component
specifications) remains authoritative and has been preserved in
`docs/PROJECT.md` §3 The Two-Layer State Machine.

**What was superseded**:
- "Implementation Plan" / "Phase 1-4 build order" sections —
  replaced by refactor_plan.md R0-R9 (now complete) and
  implementation_plan.md Phases 0-10 (integrated state machine plan
  in §3 above)
- Project structure and file layout — replaced by the target layout
  in refactor_plan.md Part II and then further simplified by
  implementation_plan.md Part II ("a project is a directory")
- Knowledge store schema (SQLite tables) — replaced by
  `alpha_review.ReviewState` (papers/themes) plus JSONL files
  (evaluations, findings, reviews, frontier snapshots)
- "Tools" as a first-class concept — the refactor is
  zero-new-tools; all capabilities are reached via Claude Code
  built-ins (`Bash`, `Read`, `Write`, etc.) + `alpha_review` Python
  module

---

*This document is rewriteable. The append-only log lives in
`docs/LOGS.md`.*
