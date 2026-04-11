# LOG — Development log for the alpha_research tool

> This is the development log for the **tool itself** — the alpha_research
> repo. (Scaffolded research projects use `LOGS.md` instead; see the
> three-canonical-docs invariant recorded on 2026-04-11.)

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
