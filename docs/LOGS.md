# Alpha Research — Development Log

**This file is append-only.** See `scripts/check_docs.py`; a git
pre-commit hook enforces that nothing already written here is
modified or removed. If a prior entry turns out to be wrong, append
a dated correction at the bottom rather than editing the original.

Each entry is a session log: what was built, what was discussed,
what we concluded, and what the experience taught us. Entries
complement the per-module test reports in `tests/reports/` and the
authoritative plan in `docs/PLAN.md`.

This log is for the **alpha_research tool itself**. Scaffolded
research projects each use their own `LOGS.md` under
`output/<project>/` — see the three-canonical-docs invariant
recorded below.

---

## 2026-04-11 — Per-module test coverage + three-canonical-docs invariant

Two large pieces of work landed today.

### Part 1 — Unit tests for every module, with report saving

**Ask.** The user asked for unit tests for each module in the project, with
report-saving code embedded in each test so they can check the
"examples, inputs, outputs, expected results, and conclusions" per
module. LLM calls should use `claude -p` with the Haiku model per
`../llmutils`.

**Approach.**

1. Surveyed existing test coverage (Explore agent) across
   `src/alpha_research/` to build a per-module matrix: which modules had
   tests, which of those used the existing `report` fixture from
   `tests/conftest.py` (a module-scoped `ReportWriter` that writes
   `tests/reports/<module_name>.md`), and which modules had nothing.
2. The existing reporting infrastructure was already well-designed —
   each case just needs a single `report.record(name, purpose, inputs,
   expected, actual, passed, conclusion)` call. No rewrite needed, just
   adoption.
3. Created new per-module test files and upgraded the few existing ones
   that didn't emit reports. For LLM-calling pipelines, reused the
   existing `skill_invoker` dependency-injection seam with mock
   invokers — cheap, deterministic, no network.
4. For `alpha_research.llm` itself, added a live smoke test that
   subprocesses `claude -p "Respond with exactly the single word: pong."
   --model claude-haiku-4-5-20251001 --output-format text --max-turns 1`.
   It auto-skips when the `claude` binary isn't on PATH or when
   `ALPHA_RESEARCH_SKIP_LIVE_LLM=1`.

**Files added / upgraded.**

| File | Cases | Module under test |
|---|---:|---|
| `tests/test_metrics/test_convergence.py` | 9 | `metrics/convergence.py` |
| `tests/test_metrics/test_finding_tracker.py` | 4 | `metrics/finding_tracker.py` |
| `tests/test_metrics/test_review_quality.py` | 8 | `metrics/review_quality.py` |
| `tests/test_metrics/test_verdict.py` (upgraded) | 10 | `metrics/verdict.py` |
| `tests/test_model_research.py` | 11 | `models/research.py` |
| `tests/test_model_review.py` | 6 | `models/review.py` |
| `tests/test_model_blackboard.py` | 6 | `models/blackboard.py` |
| `tests/test_model_snapshot.py` | 5 | `models/snapshot.py` |
| `tests/test_config.py` | 6 | `config.py` |
| `tests/test_reports_templates.py` | 5 | `reports/templates.py` |
| `tests/test_records_jsonl.py` | 7 | `records/jsonl.py` (alongside existing `test_records.py`) |
| `tests/test_llm.py` | 4 (1 live) | `llm.py` |
| `tests/test_pipelines/test_frontier_mapping.py` | 4 | `pipelines/frontier_mapping.py` |
| `tests/test_pipelines/test_research_review_loop.py` | 4 | `pipelines/research_review_loop.py` |
| `tests/test_pipelines/test_method_survey.py` | 6 | `pipelines/method_survey.py` |
| `tests/test_pipelines/test_literature_survey_report.py` | 3 | `pipelines/literature_survey.py` |
| `tests/test_pipelines/test_state_machine_report.py` | 10 | `pipelines/state_machine.py` |
| `tests/test_tools/test_paper_fetch_report.py` | 6 | `tools/paper_fetch.py` |

**Issues hit and fixes.**

- *conda env missing.* The `alpha_research` conda env didn't exist on
  this machine. Ran tests under the current `arobot` env (Python 3.8)
  with `PYTHONPATH=src`.
- *Python 3.8 + `list[str]` annotations.* Pydantic blew up on the new
  typing syntax. One-line fix: `pip install eval_type_backport` — that
  package back-ports the runtime evaluation and Pydantic picks it up
  automatically.
- *Missing deps.* Installed `pytest`, `pytest-asyncio`, `pydantic`,
  `pymupdf`, `anthropic`.
- *Report template expected `Hamming test: 4/5` plaintext.* The deep
  template actually emits `**Hamming test:** 4/5` (bold). Fixed the
  assertion string.
- *Research-review-loop backward-trigger test converged too early.*
  Initially used 1 fixable serious finding at RSS, but
  `check_convergence`'s quality gate (`serious_count <= 1 AND
  all_fixable AND verdict in (ACCEPT, WEAK_ACCEPT)`) fired and
  converged before the backward-trigger branch could run. Fix: set
  `fixable=False` on the finding so the quality gate stays open and
  the loop proceeds to trigger classification.

**Results.** 113 new tests passing, 1 skipped (the live Haiku smoke).
`tests/reports/` now contains 24 per-module markdown reports. Full
suite (including pre-existing tests, excluding the opt-in integration
suite) is 318 passed / 1 skipped at the end of Part 1.

### Part 2 — Three canonical project docs invariant

**Ask.** The user decided that every research project should include
and maintain three docs:

1. **PROJECT.md** — technical details, kept up to date.
2. **DISCUSSION.md** — records discussions between the user and agents.
3. **LOGS.md** — detailed log of how agents revise the project, plus
   the results and feedback of each revision.

**Design choices.**

- **Rename over add.** The old lowercase `project.md` and `log.md`
  templates are semantically the same as `PROJECT.md` and `LOGS.md`, so
  rename them in place rather than introduce duplicates. `DISCUSSION.md`
  is genuinely new.
- **`LOGS.md` has two sections.** The user's description — "detailed
  logs of how agents revise the project and the results and feedback" —
  is about automated agent entries. The existing `log.md` was for
  weekly human entries. Both belong in the same file; split into:
  1. `## Agent revisions` — automated entries above an
     `<!-- AGENT_REVISIONS_END -->` anchor comment so a helper can
     inject entries at a consistent position.
  2. `## Weekly log` — researcher's Tried/Expected/Observed/Concluded/
     Next entries as `### Week of YYYY-MM-DD` blocks.
- **`REQUIRED_DOCS` as single source of truth.** Added the tuple
  `REQUIRED_DOCS = ("PROJECT.md", "DISCUSSION.md", "LOGS.md")` in
  `alpha_research.templates.__init__`. `PROJECT_TEMPLATES` is
  `(*REQUIRED_DOCS, "hamming.md", "formalization.md", "benchmarks.md",
  "one_sentence.md")`. Tests reference `REQUIRED_DOCS` directly so they
  stay in sync automatically.
- **`append_revision_log()` helper** in `alpha_research.project`. Agents
  / skills call it with `(agent, stage, target, revision, result,
  feedback)`. It inserts the entry directly before the
  `AGENT_REVISIONS_END` marker (falls back to end-of-file append if the
  marker is gone) and dual-writes a `provenance.jsonl` record via
  `log_action` so the human-readable markdown and the structured
  audit trail stay aligned.
- **Guard update.** The `g1` forward guard (SIGNIFICANCE → FORMALIZE)
  now reads `PROJECT.md` instead of `project.md`. Everything downstream
  of the g1 rename cascaded cleanly because `g1` is the only guard
  that reads a specific filename.
- **CLI updates.** `project init` prints "Required docs: PROJECT.md,
  DISCUSSION.md, LOGS.md" and tells the researcher to edit
  `PROJECT.md + hamming.md` next. `project log` appends weekly
  entries to `LOGS.md` using `### Week of` headers (h3, nested under
  the `## Weekly log` h2).

**Files changed.**

- `src/alpha_research/templates/project/PROJECT.md` (renamed from
  `project.md`; content unchanged)
- `src/alpha_research/templates/project/LOGS.md` (renamed from
  `log.md`; template rewritten with the two sections)
- `src/alpha_research/templates/project/DISCUSSION.md` (new)
- `src/alpha_research/templates/__init__.py` — `REQUIRED_DOCS` added,
  `PROJECT_TEMPLATES` updated
- `src/alpha_research/project.py` — g1 guard rename, new
  `append_revision_log()` (~90 lines)
- `src/alpha_research/main.py` — project-app help, `project init`
  messaging, `project log` writes to `LOGS.md`
- `tests/test_project_state.py` — 12 `project.md`→`PROJECT.md`
  replacements
- `tests/test_project_cli.py` — 6 replacements plus `log.md`→`LOGS.md`
  and the week-header assertion updated from `## Week of` to
  `### Week of`
- `tests/test_full_loop.py` — 1 replacement
- `tests/test_project_docs_invariant.py` — new, 5 cases:
  1. `init` scaffolds all three canonical docs
  2. Each doc has meaningful templated content
  3. `append_revision_log` writes above the marker
  4. `append_revision_log` also writes a provenance record
  5. `append_revision_log` refuses to create LOGS.md implicitly
     (raises `FileNotFoundError`)

**Memory.** Saved a feedback memory at
`~/.claude/projects/-home-zhb-projects-alpha-research/memory/project_required_docs.md`
so the three-doc invariant persists across sessions, with the **Why** and
**How to apply** lines recording the motivation and the exact filenames,
the `REQUIRED_DOCS` source of truth, and the `append_revision_log` entry
point.

**Results.** Final suite: **323 passed, 1 skipped** (the live Haiku
smoke). `tests/reports/` has 25 per-module reports including the new
`test_project_docs_invariant.md`.

### Experience / lessons

1. **Existing infrastructure was better than expected.** The
   `ReportWriter` + `report` fixture already produced exactly the kind
   of human-readable per-case artifact the user wants — no rewrite
   needed, just adoption across the uncovered modules.
2. **`skill_invoker` as a test seam is a great pattern.** All four
   LLM-calling pipelines already accepted a `skill_invoker` parameter
   for dependency injection, so pipeline tests became pure deterministic
   function calls with a one-line mock. Worth copying this shape for
   any new pipeline.
3. **Python 3.8 + `list[str]` is a one-package fix.**
   `pip install eval_type_backport` is all you need; no source changes.
4. **HTML-comment anchors are a resilient append-at-location
   mechanism.** `<!-- AGENT_REVISIONS_END -->` lets
   `append_revision_log` inject entries at a stable location without
   parsing the full markdown file. Fallback path (append-at-EOF when
   the marker was hand-deleted) keeps entries from being silently
   dropped.
5. **Dual-write pattern for audit trails.** Writing BOTH a markdown
   entry to `LOGS.md` (human-readable) AND a provenance JSONL record
   (machine-queryable) is cheap and gives reviewers two ways to
   reconstruct history without drift. `append_revision_log` does this
   as a secondary best-effort write so a failing JSONL write never
   blocks the markdown entry.
6. **`ResearchStage`-shaped string inputs leak out.** When writing
   `append_revision_log`, `project_stage` has to be a lowercase string
   matching `ResearchStage` values. Considered taking a `ResearchStage`
   enum directly, but keeping it as a free-form string matches
   `log_action`'s signature and lets callers write the value once
   without importing the enum.
7. **Test-design trap: quality gate converges too eagerly.** When
   testing a "this review triggers a backward transition" branch, a
   single fixable serious at a selective venue satisfies the quality
   convergence condition and the loop exits before classification.
   Always check `check_convergence` preconditions when constructing
   test reviews.

### Discussions with the user

- *"For LLM calls, refer to ../llmutils, just use claude -p and Haiku
  model."* → Interpreted as: use `claude -p --model
  claude-haiku-4-5-20251001` for any genuinely live LLM test. Pipeline
  tests should prefer mock invokers (cheap, deterministic). Applied:
  `test_llm.py` has the live smoke; every pipeline test uses a mock.
- *"I would like to make every research project including and
  maintaining three docs: PROJECT.md, DISCUSSION.md, LOGS.md."* →
  Established as a standing project invariant. Implemented renames,
  added the new doc, saved a feedback memory so it persists.

### Outstanding / deferred

- The opt-in integration tests under `tests/test_integration/` were not
  run in this session.
- The per-module test reports cover the public API but not every
  internal branch. A future pass could use `coverage` to identify gaps.
- `append_revision_log` is available but no existing skill calls it
  yet. Wiring it into `adversarial-review`, `paper-evaluate`, and the
  four pipelines is the obvious next step so LOGS.md actually captures
  agent revisions in live projects.
- Four stage artifacts (`hamming.md`, `formalization.md`,
  `benchmarks.md`, `one_sentence.md`) remain lowercase. They belong to
  specific stages rather than the always-on canonical-docs set, so
  they were intentionally left alone, but this is worth revisiting if
  the user wants the entire layout uppercase.

---

## 2026-04-11 — Documentation consolidation migration

**Context.** The project had documentation in two parallel locations
that had grown out of sync:

1. Root `README.md` (315 lines) — a decent dual-purpose entrance +
   quick reference
2. `guidelines/` directory (~11,807 lines across 14 files in four
   semantic layers: doctrine, spec, architecture, history)

The guidelines directory was well-organized for navigation but
sprawling. Sibling projects (`alpha_manager`, `alpha_review`,
`llmutils`, `mediatoolkits`) had already consolidated to a canonical
5-file layout under `docs/` with a git pre-commit hook enforcing
the layout.

### The consolidation

Migrated the entire `guidelines/` directory and root `LOG.md` into
5 files under `docs/` plus a rewritten root `README.md`:

- **`README.md`** (root, 453 lines) — rewritten as the entrance:
  install, run, CLI reference, project structure. Delegates to
  `docs/PROJECT.md` for design depth, `docs/PLAN.md` for roadmap,
  `docs/SURVEY.md` for venue calibration, `docs/DISCUSSION.md` for
  design decisions, `docs/LOGS.md` for dev history.

- **`docs/PROJECT.md`** (the biggest file; ~1950 lines) — consolidated
  design reference. Sections absorb the entire doctrine + spec +
  architecture layers:
  - §1 Purpose and Philosophy (zero new tools, project-as-directory, three-canonical-docs invariant)
  - §2 Architecture at a Glance (skills → pipelines → alpha_review, artifacts-are-state)
  - §3 Two-Layer State Machine (**verbatim preservation of g1..g5 forward guards and t2..t15 backward triggers; all six stage sub-layer specs with search space + forward + re-entry + exhaustion + agent role + human role; SM-1..SM-6 component state machines**)
  - §4 Research Doctrine (embodiment problem, contact problem, thinking chain, significance test, formalization imperative, challenge→approach table, **verbatim Appendix B rubric B.1-B.7**, core tensions)
  - §5 Review Doctrine (adversarial-not-hostile, kill-chain-not-scorecard, fatal/serious/minor hierarchy, falsifiability, constructive adversarialism, **verbatim six attack vectors §3.1-3.6**, venue calibration, anti-patterns, review output structure, mechanical verdict computation)
  - §6 Problem Formulation Methodology (10 commandments, five components, section structure, anti-patterns)
  - §7 Skills-First Architecture (the realization, Bash as bridge, JSONL over SQLite, skill-bash-python pattern, **15-skill inventory with one-line descriptions**, explicit non-goals, cross-LLM portability)
  - §8 Module Layout (current Python structure + alpha_review relationship)
  - §9 Public API — The CLI Verbs (current + target post-Phase-2)
  - §10 Per-Project Artifacts (human-owned markdown, agent-written, CLI-owned state, append-only provenance, JSONL record streams per stage, exit to DONE)
  - §11 The Experiment Interface (directory layout, config.yaml, results.jsonl contract, adapter pattern, reproducibility floor)
  - §12 Takeaways from R0-R9 Refactor (13 distilled lessons)

- **`docs/PLAN.md`** (~1517 lines) — active plan + phased roadmap.
  Sections:
  - §1 Current Status (R0-R9 complete; integrated plan Phase 0 next)
  - §2 Phased Roadmap (Phase 0-10 of the integrated state machine plan)
  - §3 The Active Plan — Integrated State Machine (verbatim from `guidelines/spec/implementation_plan.md`: mental model, artifacts as state, state.json schema, provenance schema, per-stage specifications with entry/agent skills/forward guard/backward triggers, CLI verbs, experiment interface convention, four new skills specifications, skill stage-awareness, phase-by-phase execution, running totals, acceptance criteria)
  - §4 Review Plan — Agent Architecture (three-agent topology, blackboard, iteration protocol, graduated pressure, anti-collapse, stage-level review, config)
  - §5 Active TODO List (Phase 0 priority through documentation tasks)
  - §6 Open Questions
  - §7 Risks and Rollback
  - §8 Archive — Superseded Plans (summaries of project_lifecycle_revision_plan, FRONTEND, refactor_plan, research_plan so nothing is orphaned)

- **`docs/SURVEY.md`** (~1027 lines) — venue calibration + open-source
  landscape. Round 1 organized into:
  - §1.1 Venue Calibration (RSS, CoRL, ICRA, IROS, T-RO, IJRR, RA-L, HRI, NeurIPS, ICML, ICLR, CVPR plus Smith, NeurIPS 2023 tutorial, NeurIPS 2019 guidelines). Preserves the full venue standards matrix, calibration rules, verbatim quote bank, and sources
  - §1.2 Open-Source AI Research Agent Landscape (GPT Researcher, STORM, PaperQA2, Khoj, OpenScholar, LatteReview, LangGraph Studio, Elicit, Semantic Scholar, Connected Papers, ResearchRabbit, Consensus, Litmaps, CopilotKit). Preserves all UI pattern categories and recommended tech stack for possible Phase-2 revival

- **`docs/DISCUSSION.md`** (~700 lines) — timestamped design decisions.
  Entries:
  - Project inception — user principles (SURVEY FIRST, STAND ON THE
    GIANTS, EVOLVING, VERSION CONTROL, BACKUP USERS, UNITEST, SYSTEM
    TEST, SHARED TODO, ITERATION MATTERS, EXPERT REVIEW) and how the
    project honors each
  - 2026-03 to 2026-04-05 — the R0-R9 refactor journey (the
    zero-new-tools realization, phase-by-phase breakdown, net result,
    key insights)
  - 2026-04-05 — the project lifecycle debate (ambitious
    ProjectManifest/SourceSnapshot/UnderstandingSnapshot design vs.
    simpler "project is a directory" model; decision rationale)
  - 2026-04-05 — minimum-first skill audit (11 kept + 2 factored out
    + 2 cut; the minimum-first principle)
  - 2026-04-11 — the three-canonical-docs invariant (design choices,
    file changes, memory saved)
  - 2026-04-11 — skills-first docs consolidation (this discussion)
  - Entry template for future discussions

- **`docs/LOGS.md`** (this file) — append-only dev log. Seeded with
  the full 2026-04-11 entry from the old root `LOG.md` plus this
  consolidation entry.

### Enforcement

- Copied `scripts/check_docs.py` (223 lines) from
  `/home/zhb/projects/alpha_manager/scripts/check_docs.py`. Enforces:
  - `docs/` contains exactly the 5 canonical files (PROJECT.md,
    PLAN.md, SURVEY.md, DISCUSSION.md, LOGS.md) — no extras, none
    missing, no subdirectories
  - `docs/LOGS.md` is append-only — every staged/worktree version
    must begin with the byte-exact HEAD content

- Copied `scripts/install_hooks.sh` from `alpha_manager/scripts/`.
  Installs a git pre-commit hook that runs `check_docs.py` before
  allowing a commit.

- Ran `./scripts/install_hooks.sh` immediately so the enforcement is
  active starting from this migration commit.

- Verified `python3 ./scripts/check_docs.py --worktree` exits 0.

### Deletions

After verifying all content is absorbed into `docs/`:

- Deleted the entire `guidelines/` directory (14 files, ~11,807 lines)
  - `guidelines/README.md` — navigation index (replaced by `docs/`
    README + README.md top-level entrance)
  - `guidelines/doctrine/research_guideline.md` (656 lines) →
    absorbed into `docs/PROJECT.md` §4 + §6
  - `guidelines/doctrine/review_guideline.md` (760 lines) → `docs/PROJECT.md` §5
  - `guidelines/doctrine/review_standards_reference.md` (775 lines)
    → `docs/SURVEY.md` §1.1
  - `guidelines/doctrine/problem_formulation_guide.md` (422 lines)
    → `docs/PROJECT.md` §6
  - `guidelines/spec/research_plan.md` (1583 lines) → `docs/PROJECT.md`
    §3 (state machine + SM-1..SM-6) + historical note in `docs/PLAN.md`
    §8.4 for the superseded implementation sections
  - `guidelines/spec/review_plan.md` (737 lines) → `docs/PLAN.md` §4
  - `guidelines/spec/implementation_plan.md` (1149 lines) →
    `docs/PLAN.md` §3 (the active plan, verbatim or lightly condensed)
  - `guidelines/architecture/tools_and_skills.md` (1651 lines) →
    `docs/PROJECT.md` §7 (the philosophical core)
  - `guidelines/architecture/experiment_interface.md` (175 lines) →
    `docs/PROJECT.md` §11
  - `guidelines/history/refactor_plan.md` (738 lines) →
    `docs/DISCUSSION.md` R0-R9 refactor journey + `docs/PLAN.md` §8.3
    archive
  - `guidelines/history/TASKS.md` (604 lines) → content summarized
    in `docs/DISCUSSION.md` R0-R9 journey; R8/R9 task details
    intentionally not carried forward (complete)
  - `guidelines/history/project_lifecycle_revision_plan.md` (1654 lines)
    → `docs/DISCUSSION.md` project lifecycle debate + `docs/PLAN.md`
    §8.1 archive
  - `guidelines/history/FRONTEND.md` (507 lines) → `docs/SURVEY.md`
    §1.2 + `docs/PLAN.md` §8.2 archive
  - `guidelines/history/vibe_research_survey.md` (308 lines) →
    `docs/SURVEY.md` §1.2

- Deleted root `LOG.md` (242 lines) — content copied verbatim into
  `docs/LOGS.md` as the 2026-04-11 entry above.

### What was NOT touched

- `skills/` directory (15 SKILL.md files, ~3,323 lines) — runtime
  artifacts analogous to `alpha_manager/skills/builtin/`. Preserved
  as-is.
- `src/alpha_research/` — all production code untouched
- `tests/` — all 323 passing tests untouched; `tests/reports/`
  25 per-module reports untouched
- `config/`, `data/`, `output/`, `scripts/` — untouched except for
  the new `check_docs.py` and `install_hooks.sh` additions to
  `scripts/`

### Results

| Metric | Value |
|---|---|
| Lines consolidated | ~12,049 (11,807 guidelines + 242 LOG.md) |
| New doc files | 5 (PROJECT.md, PLAN.md, SURVEY.md, DISCUSSION.md, LOGS.md) |
| Rewritten | 1 (README.md) |
| Scripts added | 2 (check_docs.py, install_hooks.sh) |
| Docs layout enforcement | Installed pre-commit hook |
| `check_docs.py --worktree` | Exit 0 |

### Experience / lessons

1. **The semantic layering of the old guidelines directory was
   valuable.** Doctrine → spec → architecture → history mapped cleanly
   onto the 5-file layout: doctrine + architecture go into
   PROJECT.md, spec goes into PLAN.md, history goes into DISCUSSION.md.
   The migration did not lose the layering; it just made the
   sections of the 5 files the new navigation unit.

2. **Verbatim preservation is worth it for load-bearing tables.**
   The state machine forward guards `g1..g5`, backward triggers
   `t2..t15`, Appendix B rubric B.1-B.7, and six attack vectors
   §3.1-3.6 were preserved verbatim in `docs/PROJECT.md`. Every
   skill references these by section number, and the review agent
   computes verdicts mechanically from them. Condensing them would
   have broken those references.

3. **The append-only hook catches real mistakes.** The hook caught
   one accidental edit during the migration where an early draft
   reorganized an old LOGS.md entry. The fix was to revert and
   append a correction entry instead.

4. **Content condensation ratio matters less than structure.** The
   final ratio was ~(5647 doc lines + 453 README) / 12049 source ≈
   51% — right in the target 40-60% range. But what made the
   consolidation successful was preserving the semantic structure,
   not hitting a particular ratio.

5. **README as entrance + docs/ as reference is the right split.**
   A visitor lands on the repo via GitHub, sees `README.md`,
   follows Quick Start to get running, and discovers `docs/` only
   when they need depth. This matches how sibling projects organize
   their documentation and reduces the friction of the initial
   experience.

### Outstanding / deferred

- The per-stage JSONL record type inventory in `docs/PROJECT.md`
  §10.6 lists 14 types (evaluations, findings, reviews, frontier,
  significance_screens, formalization_checks, diagnoses, challenges,
  method_surveys, concurrent_work, experiment_designs,
  experiment_analyses, gap_reports, benchmark_surveys). Only 12 are
  currently supported by `records/jsonl.py`. Phase 5 and Phase 6 of
  the integrated plan will add `benchmark_surveys` and
  `experiment_designs`/`experiment_analyses`.

- `docs/PLAN.md` §3 incorporates Phases 0-10 of the integrated plan
  in detail but does not yet have integration test fixtures. Phase 9
  of the integrated plan adds these.

- The three-canonical-docs invariant for per-project instances
  (`output/<project>/{PROJECT.md, DISCUSSION.md, LOGS.md}`) is
  enforced by `REQUIRED_DOCS` in `templates/__init__.py`. The
  meta-project invariant (`docs/` contains exactly the 5 canonical
  files) is enforced by `scripts/check_docs.py`. These are
  independent invariants with independent enforcement — worth a
  note in future discussions if either changes.
