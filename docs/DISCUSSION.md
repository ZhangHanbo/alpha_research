# Alpha Research — Discussion Log

Timestamped record of substantive conversations between the human
developer and the assistant. Captures the *decisions* (and the
reasoning that led to them) — not the code changes themselves,
which live in `LOGS.md`, and not the resulting design, which lives
in `PROJECT.md` / `PLAN.md`.

This file is rewriteable: feel free to clean up prose, correct
transcription errors, or reorganize. The LOGS.md append-only rule
does NOT apply here.

Entries go oldest-first so the project evolution reads naturally.

---

## Entry — undated (project inception) — User principles

This is the user's original workflow ideals that drove the project
from the start. They are the scoring rubric for every design
decision. Where implementation has deviated, the deviation is
documented in the relevant PROJECT/PLAN section.

### Preliminary principles

- **SURVEY FIRST**: A hierarchical, iterative comprehensive online
  survey goes first. The survey pipeline should not be hardcoded.
  It should be iteratively done until atomic, executable,
  implementable units are fully identified.

- **STAND ON THE GIANTS**: Before implementation, a fully online
  survey, continuing the above one, should be done to see if there
  is any open-sourced, reliable, deployable repos/packages/toolkits/
  sdks to use as the basis, instead of implementing from scratch.

- **EVOLVING**: For each project, detailed reports of implementation
  plan, principles, details, and improvements should be recorded.
  A compact summary should be first generated, followed by an
  independent takeaway file for lessons learned and important
  failures — easily retrieved and reused.

- **VERSION CONTROL**: Keep versions well-organized and managed.
  Always make mistakes recoverable, and reviewable by humans.

- **BACKUP USERS**: Special critical case of version control. If
  agents modify things they didn't create, back up the original
  version as a user branch, then start with a new branch.

- **UNITEST**: A carefully designed unit-test system with carefully
  designed examples to check each unit/module works as expected.

- **SYSTEM TEST**: An iterative, quantifiable, verifiable system
  test loop. Start with online, comprehensive, domain-specific
  survey of how to do it.

- **SHARED TODO MANAGEMENT**: Maintain a shared TODO list for users
  and workers.

- **ITERATION MATTERS**: A complex work cannot be done in one shot.
  Reflection is necessary. Maintain a consistent objective, set up
  evaluation suites and metrics, run codes, monitor running, test
  results, reflect, write reports. Explicit and executable stopping
  signal preferred; otherwise the manager decides.

- **EXPERT REVIEW**: Important to verify if outputs are meaningful.
  Should be spawned first with prompts, with sufficient online
  survey of how an expert in the corresponding domain should be,
  and what are crucial to ensure project quality. Another survey
  of how to write a high-quality report should be explicitly
  written down and stored properly.

These principles are the scoring rubric for every design decision
that follows. The project honors them in specific ways:

- **SURVEY FIRST** → `literature-survey` pipeline wraps
  `alpha_review`'s PLAN → SCOPE → SEARCH/READ loop → WRITE
- **STAND ON THE GIANTS** → `alpha_review` dependency; zero new
  tools; adopted skills like the `paper-evaluate` rubric from
  Appendix B (doctrine-provided)
- **EVOLVING** → per-project evolving JSONL records; each record
  stream is a lineage of how the project evolved; the
  three-canonical-docs invariant captures per-project status,
  discussions, and append-only logs
- **VERSION CONTROL** → project-as-directory + `git init` in the
  directory handles versioning when the researcher wants it;
  `provenance.jsonl` + `state.json` track transitions
- **BACKUP USERS** → the integrated plan's `--force` path records
  `override_reason` in provenance, keeping cheating visible
- **UNITEST** → 323 passing tests, per-module reports in
  `tests/reports/` via `ReportWriter`
- **SYSTEM TEST** → `adversarial-review` skill + `research_review_loop`
  pipeline + graduated pressure + meta-reviewer. The
  `review_standards_reference.md` → `docs/SURVEY.md` round 1 is
  itself the online survey of how to review at top-venue standard
- **SHARED TODO MANAGEMENT** → `docs/PLAN.md` §5 Active TODO list
- **ITERATION MATTERS** → two-layer state machine with backward
  triggers; `research_review_loop` pipeline with convergence
  detection; stagnation detection; 5-iteration cap
- **EXPERT REVIEW** → `adversarial-review` skill encodes the
  six attack vectors at venue standard; `meta-reviewer` catches
  toothless critiques; the Appendix B rubric is the expert framework

---

## Entry — 2026-03 to 2026-04-05 — The R0-R9 refactor journey

The project began as a T1-T10 tool-centric implementation (494 tests
passing) that built research and review agents from scratch as
Python classes backed by tool modules. This entry records why and
how it became the skills-first layout.

### The realization: zero new tools

Earlier drafts of the tools/skills architecture proposed an MCP
server with 5, 9, 11, or 19 custom tools. After repeated minimality
passes, the right answer turned out to be **zero new tools**. The
analysis in `guidelines/architecture/tools_and_skills.md` Part I
captures the logic:

A robotics researcher's day consists of activities in two buckets:

- **Bucket 1** — reading papers, writing code, running training
  scripts, launching simulators, querying wandb, running sympy
  checks, making plots, compiling LaTeX, git operations, searching
  the codebase, fetching web documentation. All of these are
  **`Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`, `WebSearch`,
  `WebFetch`**.
- **Bucket 2** — searching ArXiv / S2 / OpenAlex / Google Scholar,
  traversing citation graphs, extracting full-text sections from
  PDFs, persisting evaluations. All of these are **`alpha_review`**
  at `../alpha_review`, which already has `apis.search_all`,
  `apis.s2_references/s2_citations`, `apis.unpaywall_pdf_url`,
  `scholar.scholar_search_papers`, `models.ReviewState`,
  `sdk.run_plan/scope/search/read/write`, and the `alpha-review` CLI.

The first bucket is solved by Claude Code directly. The second is
solved by `alpha_review`. The existing `alpha_research/tools/paper_fetch.py`
handles PDF → structured sections. **The Python is already written.**
Building an MCP server to wrap it is pure indirection — it adds
schemas, adapters, and maintenance burden without expanding
capability.

**Bash is the bridge.** Any Python function in `alpha_review` or
`alpha_research` is reachable from a skill via one `bash python -c
"..."` call. No MCP server, no JSON Schema duplication, no adapter
layers.

### The refactor in phases (R0-R9)

`guidelines/history/refactor_plan.md` defined a 9-phase migration
plan. `guidelines/history/TASKS.md` operationalized it as an
executable task list.

**R0 — Preparation and baseline** (1 day): add `alpha_review` as
editable dependency, verify 494 existing tests pass, tag
`pre-refactor`.

**R1 — Records and helpers** (2 days): add `records/jsonl.py`
(append/read/count), `scripts/sympy_verify.py`, `scripts/audit_stats.py`,
`metrics/verdict.py` (extracted from `agents/review_agent.compute_verdict`).
~20-30 new tests. Purely additive.

**R2 — Delete redundant paper/knowledge code** (1 day, deleted
~1,990 lines cleanly):
- `tools/arxiv_search.py` (130 lines) → `alpha_review.apis.arxiv_search`
- `tools/semantic_scholar.py` (209 lines) → `alpha_review.apis.s2_*`
- `tools/knowledge.py` (116 lines) → deleted
- `test_store.py`, `test_arxiv_search.py`, `test_semantic_scholar.py`,
  `test_research_agent.py` deleted

R2 deferred three items into R6 because their consumers spanned KEEP
files requiring their own refactors:
1. `knowledge/store.py` + `knowledge/schema.py` deletion — imported
   by `main.py`, `api/app.py`, `api/routers/agent.py`,
   `projects/service.py`, `agents/research_agent.py`
2. `models.research.Paper/PaperMetadata/PaperStatus/ExtractionQuality`
   removal — the naive "import from alpha_review.models" shim did
   not work because `alpha_review.models.Paper` has an incompatible
   schema
3. `test_models.py` Paper tests

**R3 — Relocate report templates** (0.5 days): split
`tools/report.py` into a slimmer `reports/templates.py` keeping only
the rubric-heavy digest + deep templates unique to alpha_research,
dropping the survey template (replaced by `alpha_review`'s
`run_write`).

**R4 — Write pipelines** (4 days): extract deterministic orchestration
from `agents/*.py` into pipeline functions:
- `pipelines/state_machine.py` — pure functions for `g1..g5` and
  `t2..t15` (no LLM calls, no I/O)
- `pipelines/literature_survey.py` — subprocess call to `alpha-review`
  CLI + paper-evaluate loop + gap-analysis + frontier
- `pipelines/method_survey.py` — search + graph + paper-evaluate
- `pipelines/frontier_mapping.py` — classify-capability loop + diff
- `pipelines/research_review_loop.py` — extracted from
  `agents/orchestrator.py`

**R5 — Write the 10 SKILL.md files** (5 days): the highest-leverage
phase. Each SKILL.md migrates 50-500 lines of existing prompt code
into markdown. Key migrations:
- `paper-evaluate` — seeded from `prompts/research_system.py`
  (Appendix B rubric block, ~150 lines) + `prompts/rubric.py`
  (B.1-B.7 criteria, ~150 lines)
- `significance-screen` — seeded from `prompts/research_system.py`
  §2.2 block
- `formalization-check` — seeded from §2.4, §3.1 blocks
- `diagnose-system` — seeded from §2.4 empirical block
- `challenge-articulate` — seeded from §2.5, §2.7 blocks
- `experiment-audit` — seeded from `prompts/review_system.py` §3.5
  + `review_plan.md` §1.6
- **`adversarial-review`** — the largest migration. All 505 lines
  of `prompts/review_system.py`: six attack vectors, venue
  calibration, graduated pressure, anti-patterns
- `concurrent-work-check`, `gap-analysis`, `classify-capability`,
  `identify-method-gaps`

**R6 — Delete superseded prompts and agents** (1 day, ~3,300 lines):
- `prompts/meta_review_system.py` (324 lines) — logic already in
  `metrics/review_quality.py`
- `prompts/research_system.py` (467 lines) — content in 3 skills
- `prompts/review_system.py` (505 lines) — content in adversarial-review
- `prompts/rubric.py` (398 lines) — content distributed
- `prompts/understanding_system.py` (210 lines) — content in
  project-understanding skill
- `prompts/__init__.py` (21 lines)
- `agents/research_agent.py` (509 lines)
- `agents/review_agent.py` (325 lines)
- `agents/meta_reviewer.py` (138 lines)
- `agents/orchestrator.py` (276 lines)
- `agents/__init__.py` (8 lines)
- Test files: `test_prompts.py`, `test_research_agent.py`,
  `test_review_agent.py`, `test_orchestrator.py`

**R7 — Update CLI and entry points** (1 day): rewrite `main.py`
commands:
- `alpha-research survey <query> -o <dir>` → `pipelines.literature_survey.run`
- `alpha-research evaluate <paper_id> -o <dir>` → invoke
  `paper-evaluate` skill via `claude -p`
- `alpha-research review <artifact> -o <dir>` → invoke
  `adversarial-review` skill
- `alpha-research loop <project_dir>` →
  `pipelines.research_review_loop.run`
- `alpha-research status` → unchanged

**R8 — Integration testing and validation** (2 days): five
end-to-end tests:
- `survey` on a real topic produces LaTeX + evaluations.jsonl +
  alpha_research_report.md
- `review` produces a Review record via adversarial-review skill
- Calibration against 10 human-scored papers with agreement within
  ±1 on 70%+ dimensions (T10 threshold)
- Skill description discovery test — verify Claude picks the right
  skill from the description
- State machine coverage — `pipelines.research_review_loop.run` on
  a fixture project that triggers each of `t2..t15`

**R9 — Documentation and cleanup** (0.5 days): update README,
`pyproject.toml`, add `research_plan.md` status pointer, delete
`tools_and_skills_implementation.md`, tag `post-refactor`.

### Net result

**Deleted**: ~4,550 lines of redundant / superseded Python
**Added**: ~1,100 lines of new Python (pipelines, records, helpers, scripts)
**Added**: ~2,500 lines of markdown (skill bodies + reference files)
**Added**: ~800 lines of new tests

**Net Python**: −3,450 lines. **Net total (incl. markdown)**: −150
lines. The project got materially smaller AND gained the entire
skills layer.

### The key insights from R0-R9

1. **Zero new tools is not a cut, it's a realization.** Claude Code's
   built-ins plus `alpha_review` already reach every capability a
   researcher needs. Building an MCP wrapper over `alpha_review.apis`
   is pure indirection. The skill writes `bash python -c "..."`;
   Bash runs it; stdout returns structured JSON; the LLM reasons
   over it.

2. **Skills are the deliverable, not the code.** 15 SKILL.md files
   (~3,323 lines of markdown) are where the domain value lives. The
   Python pipelines are deterministic orchestration — hundreds of
   lines, not thousands.

3. **JSONL beats SQLite for agent memory.** Earlier designs had an
   8-table SQLite schema (evaluations, paper_relations, findings,
   frontier_snapshots, topic_clusters, questions, feedback, audits).
   At research scale (hundreds of records, not millions), this was
   all ceremony. Replacing it with JSONL removed ~600 lines of code
   and eliminated migrations.

4. **`skill_invoker` as a test seam.** All four LLM-calling
   pipelines accept a `skill_invoker` parameter for dependency
   injection. This makes pipeline tests pure deterministic function
   calls with a one-line mock. Worth copying this shape for any new
   pipeline.

5. **The state machine was theory until bound to disk.**
   `pipelines/state_machine.py` had pure functions for `g1..g5` and
   `t2..t15` from the start, but nothing consulted them at runtime.
   The Phase 1 wiring (in the integrated plan, post-R9) is the
   change that makes the state machine executable.

---

## Entry — 2026-04-05 — The project lifecycle debate

**Context**: During the R4-R6 refactor it became clear that the
`projects/` module (1,300 lines: `orchestrator.py`, `git_state.py`,
`registry.py`, `resume.py`, `service.py`, `snapshots.py`,
`understanding.py`, `_understanding_prompt.py`) modeled a problem
the project didn't yet have. The module was drafted under an
ambitious design in `project_lifecycle_revision_plan.md` (1,654
lines) that proposed:

- `ProjectManifest` — stable identity with UUID, slug, `project_type`
  (literature | codebase | hybrid), `source_bindings`, `alpha_research_version`
- `SourceBinding` — link to external source (git_repo, directory, paper_set)
- `ProjectState` — mutable operational head with `current_snapshot_id`,
  `current_blackboard_path`, `active_run_id`, `resume_required`,
  `source_changed_since_last_snapshot`
- `SourceSnapshot` — immutable source-tree state with `vcs_type`,
  `commit_sha`, `branch_name`, `is_dirty`, `patch_path`,
  `untracked_manifest_path`, `source_fingerprint`
- `UnderstandingSnapshot` — derived structured understanding with
  `summary`, `architecture_map`, `important_paths`, `open_questions`,
  `assumptions`, `warnings`, `confidence`
- `ProjectSnapshot` — immutable checkpoint binding pre_run / post_run
  / milestone / manual
- `ResearchRun` — execution record
- Project registry + project service (JSON index, CRUD)
- Git state capture (read-only inspection + `git worktree`, no
  destructive operations)
- Source snapshot service (captures commit/branch/dirty, stores
  `tracked.diff` and `untracked_manifest.json` for dirty repos)
- Resume service with three modes: `current_workspace` (fresh
  source snapshot + delta against prior), `exact_snapshot` (git
  worktree at stored commit + apply dirty patch), `milestone`
  (resolve tag, follow Mode B)
- Understanding agent lifecycle: understanding snapshot on create,
  diff-aware re-understanding on resume
- Project-aware outer orchestrator binding research/review loop to
  project lifecycle
- CLI project commands (`project create|list|show|status|snapshot|resume`)
- FastAPI routes + frontend project list / snapshot / resume flows
- `alpha_robot` as the first real project instance

The on-disk layout was:

```
data/projects/<slug>/
  project.json
  state.json
  blackboard.json
  knowledge.db
  runs/
  snapshots/
  reports/
  notes/
  cache/
```

**Proposal**: the integrated state-machine plan in
`guidelines/spec/implementation_plan.md` Part II proposed a simpler
model:

> *"A project is a directory. `tar czf project.tgz output/<project>/`
> is a complete backup. No registry, no SQLite except the alpha_review
> paper store (which is global and not per-project), no snapshots
> unless the researcher runs git in the directory themselves."*

Specifically:

- `output/<project>/` contains the whole project
- `state.json` tracks current stage, history, guard status, open
  backward triggers, `code_dir`, target venue
- `provenance.jsonl` is the append-only lineage of every action
- The researcher's own `git` handles versioning when they want it
- `cd output/<project>` replaces `resume`
- The `project-understanding` skill replaces the understanding agent
- The research code lives in `state.code_dir` (an absolute path
  outside the project directory)

**Decision**: Adopt the simpler model. Phase 0 of the integrated
plan deletes the entire `src/alpha_research/projects/` directory
(1,300 lines) and replaces it with a 100-line `project.py`
containing just `ProjectState`, `init_project`, `load_state`,
`save_state`, `current_stage`, `transition`.

**Rationale**:

1. The lifecycle layer modeled a problem we didn't have yet. No
   user was asking for snapshot/resume across git-worktrees. No one
   had run into "I need to reproduce the exact source state from
   three weeks ago" as a pain point.

2. `cd output/<project>` is resume. The researcher's terminal
   history + `ls output/` is the registry. `git init` in the
   directory is versioning. `git tag` is milestone marking. The
   researcher already knows these tools.

3. The understanding agent → `project-understanding` skill is a
   strict simplification: the skill reads `code_dir`, produces
   `source.md`, runs on-demand (not automatic on every create/resume).
   The formalization↔implementation gap check that the ambitious
   plan wanted is still present — it's just inside the skill, not
   spread across six services.

4. The research agent reads `code_dir` for the actual method. The
   project directory holds the research STATE (stage, artifacts,
   records). **These two concerns were always cleanly separable;
   the ambitious plan conflated them.**

5. Re-cloning ambition is cheap. If a concrete pain point ever
   surfaces (registry, snapshot, resume), we can re-implement from
   `project_lifecycle_revision_plan.md` incrementally. Until then,
   deleting is free.

**What was preserved from the ambitious plan**:

- The distinction between `project.md` / `formalization.md` /
  `one_sentence.md` markdown artifacts (human-owned) and JSONL
  records (agent-written)
- The idea that the agent should understand the code (→
  `project-understanding` skill)
- The git-safety rules (no destructive operations; `git worktree`
  as the only write operation; no reset, stash, checkout over local
  changes, branch rewrites)

**What was absorbed elsewhere in a simpler form**:

- `ProjectState` dataclass → `src/alpha_research/project.py` with
  the same name but ~100 lines instead of spread across 8 modules
- `SourceSnapshot` → the researcher's own `git log` + `git status`
  (the CLI never captures patches)
- `UnderstandingSnapshot` → `source.md` (rewritable markdown)
- `ProjectSnapshot` → stage transitions in `state.json` +
  provenance.jsonl entries (no separate snapshots directory)
- Resume modes → `cd output/<project>`; the researcher handles
  git themselves

---

## Entry — 2026-04-05 — Minimum-first skill audit

**Context**: Earlier drafts of `tools_and_skills.md` proposed 12,
11, and 10 skills. The count was creeping toward "one skill per
section of the research guideline." During R5 the scope was
challenged with a two-clause test:

> *A skill earns its place only if (a) the doctrine explicitly says
> "this must be a skill," AND (b) a research-state-machine stage
> goes uncovered without it.*

Applying the test produced the final 11-skill set for R5:

| # | Skill | Verdict | Reason |
|---|---|---|---|
| 1 | `significance-screen` | **Keep** | SIGNIFICANCE stage requires the four-test check; irreducibly a skill (judgment task) |
| 2 | `formalization-check` | **Keep** | FORMALIZE requires the math detection + framework check + sympy verify |
| 3 | `diagnose-system` | **Keep** | DIAGNOSE requires the failure → formal term mapping |
| 4 | `challenge-articulate` | **Keep** | CHALLENGE requires the structural-vs-resource test |
| 5 | `experiment-audit` | **Keep** | VALIDATE requires the stats + baseline + overclaiming audit |
| 6 | `adversarial-review` | **Keep** | VALIDATE requires the six attack vectors at venue standard |
| 7 | `paper-evaluate` | **Keep** | Per-paper Appendix B rubric is the heart of SIGNIFICANCE and APPROACH |
| 8 | `concurrent-work-check` | **Keep** | APPROACH and VALIDATE both need scoop detection; maps to trigger t9 |
| 9 | `gap-analysis` | **Keep** | SIGNIFICANCE and CHALLENGE both need the semantic clustering of weaknesses |
| 10 | `classify-capability` | **Keep** (factored out from frontier-mapping) | Small, reusable — placing one paper on the frontier |
| 11 | `identify-method-gaps` | **Keep** (factored out from method-survey) | Small, reusable — given a method class, what hasn't been tried |

Two skills were **cut** during the audit:

| Cut skill | Why cut |
|---|---|
| `literature-survey` (as a standalone skill) | Implementation is a pipeline (`pipelines/literature_survey.py`) that wraps the `alpha-review` CLI + `paper-evaluate` skill loop. The "skill" is just the pipeline. |
| `method-survey` (as a standalone skill) | Same — implemented as `pipelines/method_survey.py` + the `identify-method-gaps` skill |

Two skills were **factored out** of larger skills to stay focused:

- `classify-capability` factored out of `frontier-mapping`
- `identify-method-gaps` factored out of `method-survey`

**Decision**: the 11-skill set plus four planned new skills
(`benchmark-survey`, `project-understanding`, `experiment-design`,
`experiment-analyze`) is the committed skill catalog. Each skill
earned its place against either a doctrine requirement or a
stage-machine coverage gap.

**Key insight from this discussion**: "**Minimum-first beats
maximum-useful.**" Every skill we don't write is a skill we don't
have to maintain, test, version, and keep current. Two skills that
were in earlier drafts were cut; two were factored *out* of larger
skills during the audit. Each of the 15 survivors can be traced to
a concrete line in the doctrine or a stage-machine coverage need.

---

## Entry — 2026-04-11 — The three-canonical-docs invariant

**Context**: The user decided that every research project should
include and maintain three docs at its root:

1. **`PROJECT.md`** — technical details, kept up to date
2. **`DISCUSSION.md`** — records discussions between the user and agents
3. **`LOGS.md`** — detailed log of how agents revise the project,
   plus the results and feedback of each revision

**Design discussion**:

- **Rename over add**. The old lowercase `project.md` and `log.md`
  templates are semantically the same as `PROJECT.md` and `LOGS.md`,
  so rename them in place rather than introduce duplicates.
  `DISCUSSION.md` is genuinely new.

- **`LOGS.md` has two sections**. The user's description — "detailed
  logs of how agents revise the project and the results and feedback"
  — is about automated agent entries. The existing `log.md` was for
  weekly human entries. Both belong in the same file; split into:
  1. **`## Agent revisions`** — automated entries above an
     `<!-- AGENT_REVISIONS_END -->` anchor comment so a helper can
     inject entries at a consistent position
  2. **`## Weekly log`** — researcher's Tried/Expected/Observed/Concluded/Next
     entries as `### Week of YYYY-MM-DD` blocks

- **`REQUIRED_DOCS` as single source of truth**. Add the tuple
  `REQUIRED_DOCS = ("PROJECT.md", "DISCUSSION.md", "LOGS.md")` in
  `alpha_research.templates.__init__`. `PROJECT_TEMPLATES` becomes
  `(*REQUIRED_DOCS, "hamming.md", "formalization.md", "benchmarks.md",
  "one_sentence.md")`. Tests reference `REQUIRED_DOCS` directly so
  they stay in sync automatically.

- **`append_revision_log()` helper** in `alpha_research.project`.
  Agents / skills call it with `(agent, stage, target, revision,
  result, feedback)`. It inserts the entry **directly before the
  `AGENT_REVISIONS_END` marker** (falls back to end-of-file append
  if the marker is gone) and dual-writes a `provenance.jsonl`
  record via `log_action` so the human-readable markdown and the
  structured audit trail stay aligned.

- **Guard update**. The `g1` forward guard (SIGNIFICANCE → FORMALIZE)
  now reads `PROJECT.md` instead of `project.md`. Everything
  downstream of the `g1` rename cascaded cleanly because `g1` is
  the only guard that reads a specific filename.

- **CLI updates**. `project init` prints "Required docs: PROJECT.md,
  DISCUSSION.md, LOGS.md" and tells the researcher to edit
  `PROJECT.md + hamming.md` next. `project log` appends weekly
  entries to `LOGS.md` using `### Week of` headers (h3, nested under
  the `## Weekly log` h2).

**Decision**: adopted the invariant as a standing project rule.
Implemented as:

- `src/alpha_research/templates/project/PROJECT.md` (renamed from
  `project.md`; content unchanged)
- `src/alpha_research/templates/project/LOGS.md` (renamed from
  `log.md`; template rewritten with the two sections)
- `src/alpha_research/templates/project/DISCUSSION.md` (new)
- `src/alpha_research/templates/__init__.py` — `REQUIRED_DOCS` added,
  `PROJECT_TEMPLATES` updated
- `src/alpha_research/project.py` — `g1` guard rename, new
  `append_revision_log()` (~90 lines)
- `src/alpha_research/main.py` — project-app help, `project init`
  messaging, `project log` writes to `LOGS.md`

**Tests added** — `tests/test_project_docs_invariant.py` with 5
cases:
1. `init` scaffolds all three canonical docs
2. Each doc has meaningful templated content
3. `append_revision_log` writes above the marker
4. `append_revision_log` also writes a provenance record
5. `append_revision_log` refuses to create LOGS.md implicitly
   (raises `FileNotFoundError`)

**Memory saved** at
`~/.claude/projects/-home-zhb-projects-alpha-research/memory/project_required_docs.md`
so the three-doc invariant persists across sessions.

**Key insight**: the invariant propagates cleanly through every
downstream component because `REQUIRED_DOCS` is **imported** rather
than stringified. Tests reference the tuple directly; the `g1`
guard reads the filename from the tuple; CLI messages pull from the
same source. A rename cascades in one place.

---

## Entry — 2026-04-11 — Skills-first docs consolidation (this discussion)

**Context**: The project had two parallel documentation locations
that grew out of sync over the R0-R9 and 2026-04-11 work:

1. **Root `README.md`** (315 lines) — excellent dual-purpose
   entrance + quick reference
2. **`guidelines/` directory** (~11,807 lines across 14 files in
   four semantic layers: doctrine, spec, architecture, history)

The guidelines directory organized content well for navigation —
doctrine for stable standards, spec for operational machine-executable
specs, architecture for current implementation, history for
superseded plans — but it grew large, and the sibling projects
(`alpha_manager`, `alpha_review`, `llmutils`, `mediatoolkits`) had
consolidated onto a canonical 5-file layout under `docs/`:

- `docs/PROJECT.md` — design reference (subsumes doctrine + spec + architecture)
- `docs/PLAN.md` — active plan + roadmap (subsumes implementation_plan)
- `docs/SURVEY.md` — multi-round survey log (subsumes venue calibration + landscape reviews)
- `docs/DISCUSSION.md` — timestamped decisions (subsumes refactor narratives)
- `docs/LOGS.md` — append-only dev log (subsumes LOG.md)

Plus a rewritten root `README.md` as the entrance.

**Proposal**: consolidate `guidelines/` + `LOG.md` into the 5-file
layout. Enforce with the same `scripts/check_docs.py` +
`scripts/install_hooks.sh` the sibling projects use.

**Discussion topics**:

- **Preserve the semantic layers.** The doctrine → spec →
  architecture → history hierarchy is real and load-bearing. The
  consolidation should preserve this as sections within the 5
  files:
  - Doctrine → `PROJECT.md` §4 Research Doctrine + §5 Review Doctrine + §6 Problem Formulation
  - Spec → `PROJECT.md` §3 Two-Layer State Machine + `PLAN.md` §3 Integrated State Machine + §4 Review Plan
  - Architecture → `PROJECT.md` §7 Skills-First Architecture + §8 Module Layout + §11 Experiment Interface
  - History → `DISCUSSION.md` R0-R9 refactor journey + project lifecycle debate

- **Preserve verbatim** the load-bearing tables:
  - The state machine forward guards (`g1..g5`) and backward triggers (`t2..t15`)
  - The Appendix B rubric (B.1-B.7)
  - The six attack vectors (§3.1-3.6)
  - The venue standards matrix + calibration rules
  - The 15-skill inventory

- **Target condensation ratio**: ~40-60% reduction of the 11,807
  lines of guidelines. Cut redundancy between overlapping docs
  (e.g., the state machine theory appears in both `research_plan.md`
  and `implementation_plan.md`); keep all unique content.

- **Leave `skills/` in place.** The 15 SKILL.md files under
  `skills/` are runtime artifacts (analogous to
  `alpha_manager/skills/builtin/`). They are not documentation;
  they are the deliverable. Do not move or delete.

- **LOGS.md append-only, others rewritable.** Enforced by
  `scripts/check_docs.py` plus a pre-commit hook installed
  automatically by `scripts/install_hooks.sh`. The script also
  enforces that `docs/` contains exactly the five canonical files.

**Key decisions**:

1. **Scope: the repo level**. The 5-file pattern applies at the
   meta-project level (alpha_research itself). Per-project
   instances (each `output/<task_id>/`) use the separate three-canonical-docs
   invariant (`PROJECT.md` + `DISCUSSION.md` + `LOGS.md`) documented
   above. These are independent invariants.

2. **Content treatment: condense but keep all useful info**. Do
   not lose load-bearing content from the guidelines. The
   doctrine, spec, and architecture layers are authoritative.

3. **`guidelines/` deletion**. After verifying all content is in
   `docs/`, delete the entire `guidelines/` directory. Its
   semantic structure is preserved as sections within the 5 files;
   its file-level navigation is lost but that's acceptable because
   the 5-file layout has its own navigation (README.md links +
   Table of Contents in each doc).

4. **`LOG.md` deletion**. After copying its content into
   `docs/LOGS.md` verbatim plus a new consolidation entry, delete
   `LOG.md` from the root.

5. **Git hook auto-install**. `scripts/install_hooks.sh` is run
   immediately so the enforcement is active starting from the
   migration commit.

**This discussion motivates the migration entry recorded in
`docs/LOGS.md` 2026-04-11 "Documentation consolidation migration."**

---

## Entry template for future discussions

Copy-paste this block when starting a new discussion entry:

```
## Entry — YYYY-MM-DD — Short topic title

**Context**: one-line reason the discussion happened.

**Proposal / Question**: what was on the table.

**Decision**: what was decided.

**Rationale**: why. Link to LOGS.md entries, PLAN.md sections, or
external sources where relevant.

**Open follow-ups**: anything that was explicitly deferred.
```
