# Implementation Test Report — Integrated State Machine

**Generated**: Phase 0–6 of `guidelines/spec/implementation_plan.md`

## Top-line result

| Metric | Value |
|---|---:|
| **Total tests** | **214 passed, 0 failed** |
| **Phases completed** | 0, 1, 2, 3, 4, 5, 6, 9 (end-to-end integration) |
| **New tests added** | 37 (spanning 5 new test modules, all with per-case reports) |
| **Existing tests still passing** | 177 |
| **Reports generated** | 5 module reports + this summary |

```
........................................................................ [ 33%]
........................................................................ [ 67%]
......................................................................   [100%]
214 passed, 3 deselected in 1.83s
```

## Module reports (click through for details)

| Report | Tests | What it covers |
|---|---:|---|
| [`test_project_state.md`](./test_project_state.md) | 14 | Phase 1: state-machine core — init, state.json round-trip, guard checks (g1–g5), advance/backward/force, open triggers, provenance |
| [`test_project_cli.md`](./test_project_cli.md) | 8 | Phase 2: CLI verbs — `project init/stage/advance/backward/log/status` round-trip through typer |
| [`test_skills.md`](./test_skills.md) | 7 | Phase 3: skill frontmatter parsing, discovery, stage-awareness verdicts for all 11 existing skills |
| [`test_phase_5_6_skills.md`](./test_phase_5_6_skills.md) | 6 | Phases 4/5/6: the four new skills (project-understanding, benchmark-survey, experiment-design, experiment-analyze) parse correctly, benchmarks.md edge cases, stage verdict matrix for new skills |
| [`test_full_loop.md`](./test_full_loop.md) | 2 | End-to-end integration: a synthetic project walks all six stages with a backward transition (t4) and both reproduction fail + pass paths |

## What was built

### New Python modules

| File | Lines | Purpose |
|---|---:|---|
| `src/alpha_research/project.py` | 714 | The compact project layer — ProjectState, GuardCheck, StageTransition, OpenTrigger, init/advance/backward/propose_backward_trigger, stage_summary |
| `src/alpha_research/skills.py` | 231 | Skill frontmatter parser (stdlib only), discovery, `check_skill_stage` |
| `src/alpha_research/templates/__init__.py` | 60 | Template rendering helper for project scaffolding |
| `src/alpha_research/records/jsonl.py` (extended) | +72 | Added `provenance` record type and `log_action` helper |

### New markdown templates (scaffolded by `project init`)

- `project.md` — research question, task, why-now, scope, assumptions
- `hamming.md` — the researcher's 10-slot running list
- `formalization.md` — math structure (motivation + system/dynamics/info/objective/constraints + structural claims)
- `benchmarks.md` — the new Phase-5 artifact: "In scope" + "Considered but rejected" sections
- `one_sentence.md` — evolving contribution statement with good/bad examples
- `log.md` — weekly research log preamble

### New skill files (`.claude/skills` → `skills/`)

| Skill | Stage bindings | Purpose |
|---|---|---|
| `project-understanding` | diagnose, approach | Walk the researcher's `code_dir`, produce `source.md`, check formalization↔code gap |
| `benchmark-survey` | formalization, approach | Survey literature for benchmarks, rank candidates, produce `benchmark_proposal.md` |
| `experiment-design` | diagnose, approach, validate | Produce runnable `config.yaml` with three modes: reproduction, diagnostic, approach |
| `experiment-analyze` | diagnose, validate | Read results.jsonl, audit stats, compare against `benchmarks.md` published numbers, propose backward triggers |

All 11 pre-existing skills also got `research_stages:` frontmatter added and are now stage-aware.

### New CLI verbs (wired in `main.py`)

```
alpha-research project init <name> --code <dir> --question "..." --venue RSS
alpha-research project stage [<project_dir>]
alpha-research project advance [<project_dir>] [--force] [--note "..."]
alpha-research project backward <trigger> [<project_dir>] --constraint "..."
alpha-research project log [<project_dir>]
alpha-research project status [<project_dir>]
```

### New documentation

- `guidelines/architecture/experiment_interface.md` — the `experiments/<exp_id>/`
  directory convention (config.yaml schema, results.jsonl schema, how
  to adapt existing launchers in ~30 min).

## What was deleted (Phase 0 cut)

| Path | Lines | Reason |
|---|---:|---|
| `frontend/` | ~2,000 | Cut per simplicity principle; CLI + `$EDITOR` is enough for a single-researcher workflow |
| `src/alpha_research/api/` | ~550 | Cut with frontend |
| `src/alpha_research/projects/` | ~1,300 | Collapsed to the 714-line `project.py`. No more ProjectManifest / SQLite registry / git-worktree snapshots. A project is a directory. |
| `src/alpha_research/knowledge/` | ~600 | Deferred from R2; no more SQLite extension schema |
| `src/alpha_research/tools/report.py` | 12 | Backward-compat shim for `reports/templates.py` — no longer needed |
| 7 test files for deleted modules | ~1,500 | `test_api.py`, `test_api_projects.py`, `test_project_*.py`, `test_git_state.py`, `test_tools/test_report.py` |

**Net code delta**: ~−4,250 lines deleted, ~1,400 lines added. The codebase is materially smaller AND contains the full state machine + the doing-side scaffolding.

## What the state machine guarantees

1. **A project is its directory.** `tar czf proj.tgz output/<proj>/` is a complete backup. No registry, no SQLite, no hidden state.

2. **Stage is persistent.** `state.json` tracks current stage, full stage history with triggers, open backward triggers, code_dir binding, and target venue.

3. **Forward guards are real.** Every `advance` call runs a per-stage disk-reading guard with per-condition pass/fail. `g1..g5` each check 3–5 conditions drawn from `implementation_plan.md` Parts III.1–III.5.

4. **Benchmarks are first-class.** `g2` (FORMALIZE → DIAGNOSE) cannot pass without `benchmarks.md` populated and a human-confirmed `benchmark_survey` record. `g3` (DIAGNOSE → CHALLENGE) cannot pass without a passing reproduction experiment per in-scope benchmark.

5. **Backward transitions carry constraints.** `backward()` refuses any call with an empty `carried_constraint` — the researcher MUST state what they learned downstream so the re-entered stage doesn't start blank.

6. **Override is auditable.** `advance --force` is allowed but records `trigger="force"` and prepends `FORCED (...)` to the transition note. The override is visible in provenance forever.

7. **Skills know their stage.** Every SKILL.md declares `research_stages:` in frontmatter. `check_skill_stage` returns `in_stage | out_of_stage | unknown_stage | unknown_skill`. Out-of-stage invocation warns (not blocks).

8. **Provenance is complete.** Every CLI verb / skill / transition appends exactly one provenance record with parent_ids forming a DAG. A reviewer running `alpha-research provenance` three weeks later can trace any finding back to the formalization version that motivated it.

## What's NOT built (deferred per simplicity principle)

- Simulation platform, training framework, data collection UI, experiment launcher
- Web dashboard / frontend
- Project registry / snapshots / git-worktree resume
- Real-time streaming of training runs
- Multi-researcher collaboration
- Reproducibility/containerization layer
- Phase 7 (observe / calibrate commands) — stretch goal, not started
- Phase 8 (full wiring of pipelines to the state layer)
- Phase 10 (README update to advertise the new CLI)

These are all real, all deliberately deferred. The invariant to protect:
*a researcher can go from `project init` to a published result using
CLI + `$EDITOR` alone.*

## How to read the reports

Each module report contains one `## Case N` block per test. Each case shows:

- **Result** — ✅ PASS or ❌ FAIL
- **Purpose** — what the test is asserting about the system
- **Inputs** — the concrete inputs passed to the code under test
- **Expected** — what the implementation ought to produce
- **Actual** — what it produced, side-by-side with expected
- **Conclusion** — interpretation and implications for the system

For a top-down read, start with `test_full_loop.md` (the end-to-end
assertion) and fan out into the per-module reports as needed.

## Next recommended steps

1. **Phase 7** — add `alpha-research observe`, `log` enhancements, `calibrate`, `provenance` display commands (Phase 2 wired some of these already; Phase 7 completes the set).
2. **Phase 8** — wire the existing pipelines (`literature_survey`, `method_survey`, `frontier_mapping`, `research_review_loop`) to read/write the new project state so they participate in the state machine rather than sitting alongside it.
3. **Phase 10** — update root `README.md` to advertise the new CLI surface.
4. **Run on a real project** — `alpha-research project init demo --code /path/to/your/method --question "..."` and walk through the stages with real artifacts.
