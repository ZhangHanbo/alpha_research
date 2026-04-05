# Implementation Tasks — Skills-First Refactor

Task breakdown for refactoring the alpha_research codebase from the T1-T10 tool-centric implementation to a skills-first architecture that depends on `alpha_review` and expresses domain knowledge as Claude Code skills.

**Status of T1-T10:** completed (494 tests passing). T1-T10 described the original build of the multi-agent system from scratch. That implementation is the starting point for this refactor, not the end state. For the historical record of T1-T10 and its dependency graph, see git tag `pre-refactor`.

**Source documents** (agents executing these tasks MUST read before implementing):
- `guidelines/tools_and_skills.md` — current architecture (skills + pipelines + helpers, zero new tools)
- `guidelines/refactor_plan.md` — the per-file audit, target layout, and phase plan this document operationalizes
- `guidelines/research_guideline.md` — standards the skills encode
- `guidelines/review_guideline.md` — adversarial review standards
- `guidelines/research_plan.md` — research state machine (SM-1..SM-6, still valid architectural spec)
- `guidelines/review_plan.md` — executable review metrics

---

## Task Dependency Graph

```
R0 (preparation) ──────────────────────────────────────────┐
  │                                                        │
  ├─► R1 (records + helpers)                               │
  │     ├─► R4 (pipelines)                                 │
  │     └─► R5 (skills)                                    │
  │                                                        │
  ├─► R2 (delete redundant paper/knowledge code)           │
  │     ├─► R3 (relocate reports)                          │
  │     ├─► R4 (pipelines)                                 │
  │     └─► R5 (skills)                                    │
  │                                                        │
  ├─► R3 (relocate reports) ─► R7 (CLI)                    │
  │                                                        │
  ├─► R4 (pipelines) ─► R6 (delete agents)                 │
  │                       └─► R7 (CLI)                     │
  │                                                        │
  ├─► R5 (skills) ──────► R6 (delete prompts)              │
  │                          └─► R7 (CLI)                  │
  │                                                        │
  └─► R6 (delete) ──► R7 (CLI) ──► R8 (integration) ──► R9 (docs)
```

**Parallelizable groups:**
- **Group A (parallel, after R0):** R1, R2 — R1 adds new infrastructure; R2 deletes redundant old code. They touch disjoint files.
- **Group B (parallel, after R1+R2):** R3, R4, R5 — R3 relocates reports; R4 writes pipelines; R5 writes skills. Each touches distinct directories.
- **Group C (sequential):** R6 → R7 → R8 → R9

---

## R0: Preparation and baseline

**Goal:** establish the pre-refactor baseline and create the migration scaffolding.

**Read before implementing:** `guidelines/refactor_plan.md` (entire document).

**Steps:**
1. Add `alpha_review` as editable dependency in `pyproject.toml`:
   ```toml
   [project]
   dependencies = [
       "alpha_review @ file:///${PROJECT_ROOT}/../alpha_review",
       ...
   ]
   ```
   Install: `pip install -e ../alpha_review && pip install -e .`
2. Verify all 494 existing tests pass on the current codebase:
   ```bash
   PYTHONPATH=/home/zhb/projects/alpha_research/src \
     /home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest -q
   ```
3. Create git tag `pre-refactor` marking the baseline.
4. Verify `guidelines/refactor_plan.md` and this updated `TASKS.md` are committed.

**Acceptance criteria:**
- `import alpha_review` works in the alpha_research environment
- `pytest` reports 494 passed (or the current baseline)
- Git tag `pre-refactor` exists
- `guidelines/refactor_plan.md` and `guidelines/TASKS.md` present

**Estimated scope:** ~1 day.

---

## R1: Records, helpers, and verdict function (new infrastructure)

**Goal:** add the small Python pieces that the pipelines and skills will call. No deletions in this task — purely additive.

**Depends on:** R0.

**Read before implementing:** `guidelines/refactor_plan.md` Part IV, `guidelines/tools_and_skills.md` Part III.

**What to build:**

1. `src/alpha_research/records/__init__.py` and `src/alpha_research/records/jsonl.py`:
   ```python
   def append_record(project_dir: Path, record_type: str, data: dict) -> str:
       """Append a typed record to output/<project>/<record_type>.jsonl.
       Generates a UUID id, adds created_at, returns the record_id."""

   def read_records(project_dir: Path, record_type: str,
                    filters: dict | None = None, limit: int | None = None) -> list[dict]:
       """Read JSONL file, apply dict-based filters (exact match on top-level
       keys; nested keys via dotted path), apply limit."""

   def count_records(project_dir: Path, record_type: str,
                     filters: dict | None = None) -> int:
       """Return count matching filters without materializing all records."""
   ```
   Supported `record_type` values: `evaluation`, `finding`, `review`, `frontier`, `significance_screen`, `formalization_check`, `diagnosis`, `challenge`, `method_survey`, `audit`, `concurrent_work`, `gap_report`.

2. `scripts/sympy_verify.py` (standalone CLI, ~50 lines):
   ```
   python scripts/sympy_verify.py --expr "(x-2*y)**2 + exp(x)" --property convex --vars x,y
   ```
   Verifies one of: `convex`, `concave`, `continuous`, `differentiable`. Emits JSON to stdout. Pure sympy.

3. `scripts/audit_stats.py` (standalone CLI, ~100 lines):
   ```
   python scripts/audit_stats.py <exp_dir> --venue RSS
   ```
   Reads experiment results (wandb export, CSV, or JSON), computes: trials per condition, confidence intervals, seed variance, ablation performance delta. Applies venue-specific thresholds from `review_plan.md §1.6`. Emits JSON to stdout.

4. `src/alpha_research/metrics/verdict.py` (~60 lines):
   ```python
   def compute_verdict(findings: list[Finding], venue: Venue) -> Verdict:
       """Pure function implementing review_plan.md §1.9 rules:
       - any fatal → REJECT
       - significance ≤ 2 → REJECT
       - ≥3 unresolvable serious → REJECT
       - 0 serious → ACCEPT
       - ≤1 fixable serious → WEAK_ACCEPT
       - else venue-calibrated decision"""
   ```
   Extract from `agents/review_agent.py::compute_verdict`. Keep the same behavior.

**Tests:**
- `tests/test_records.py` — round-trip append/read, filter correctness, count, edge cases (empty file, bad JSON).
- `tests/test_scripts/test_sympy_verify.py` — feed known-convex / non-convex expressions, verify classification.
- `tests/test_scripts/test_audit_stats.py` — fixture experiment dir, verify trial counts + CI computation.
- `tests/test_metrics/test_verdict.py` — all 7 verdict rules from `review_plan.md §1.9`, plus venue calibration.

**Acceptance criteria:**
- All new modules importable
- All new tests pass (expect ~20-30 new tests)
- Existing 494 tests still pass
- `scripts/sympy_verify.py --expr "(x-1)**2" --property convex` returns `{"convex": true}`

**Estimated scope:** ~2 days.

---

## R2: Delete redundant paper/knowledge code

**Goal:** remove the ~1,250 lines of code that duplicates `alpha_review.apis.*` and `alpha_review.models.ReviewState`. No behavioral change — the tests that covered this code are either deleted or ported.

**Depends on:** R0.

**Read before implementing:** `guidelines/refactor_plan.md` Part I.1, I.2, I.3.

**Files to delete:**
- `src/alpha_research/tools/arxiv_search.py` (130 lines)
- `src/alpha_research/tools/semantic_scholar.py` (209 lines)
- `src/alpha_research/tools/knowledge.py` (116 lines)
- `src/alpha_research/knowledge/schema.py` (150 lines)
- `src/alpha_research/knowledge/store.py` (456 lines)
- `src/alpha_research/knowledge/__init__.py` → rewrite to re-export `alpha_research.records.jsonl` symbols
- `tests/test_store.py`
- `tests/test_tools/test_arxiv_search.py`
- `tests/test_tools/test_semantic_scholar.py`

**Files to shrink:**
- `src/alpha_research/models/research.py`:
  - Delete: `Paper`, `PaperMetadata` classes and helpers
  - Keep: `Evaluation`, `RubricScore`, `TaskChain`, `SignificanceAssessment`, `ExtractionQuality`, `SearchState`, `SearchQuery`, `PaperCandidate`, `CoverageReport`
- `src/alpha_research/models/__init__.py`: update re-exports
- `tests/test_models.py`: drop Paper tests (~40 test functions)

**Import redirects:**
- Any file that imports `from alpha_research.tools.arxiv_search import ...` → `from alpha_review.apis import arxiv_search`
- Similar for `semantic_scholar` and `knowledge`
- Any file that imports `from alpha_research.models.research import Paper` → `from alpha_review.models import Paper`
- Grep for broken imports after deletion: `grep -r "from alpha_research.tools.arxiv_search\|from alpha_research.tools.semantic_scholar\|from alpha_research.knowledge.schema\|from alpha_research.knowledge.store\|from alpha_research.tools.knowledge" src/ tests/`

**Acceptance criteria:**
- `git diff --stat` shows ~1,250 lines deleted in the target files
- `pytest` passes (tests that relied on deleted code are removed or ported)
- No broken imports (`python -c "import alpha_research"` succeeds)
- `Paper` and `PaperMetadata` are no longer defined anywhere in `alpha_research`

**Estimated scope:** ~1 day.

---

## R3: Relocate report templates

**Goal:** split `tools/report.py` into a slimmer `reports/templates.py` that keeps only the rubric-heavy templates unique to alpha_research, dropping the survey template (replaced by `alpha_review`'s `run_write`).

**Depends on:** R0.

**Read before implementing:** `guidelines/refactor_plan.md` Part I.1.

**Steps:**
1. Create `src/alpha_research/reports/__init__.py` and `src/alpha_research/reports/templates.py`
2. Move the `DIGEST_TEMPLATE` and `DEEP_TEMPLATE` Jinja2 definitions from `tools/report.py` to `reports/templates.py`
3. Delete the `SURVEY_TEMPLATE` definition (superseded by `alpha_review.sdk.run_write`)
4. Update the `generate_report` function signature to accept `mode ∈ {"digest", "deep"}` only
5. Delete `src/alpha_research/tools/report.py`
6. Update `src/alpha_research/tools/__init__.py` to remove the `report` re-export
7. Rename `tests/test_tools/test_report.py` → `tests/test_reports.py`
8. Update imports in any file that references `from alpha_research.tools.report import generate_report` → `from alpha_research.reports.templates import generate_report`
9. Remove survey-template tests

**Acceptance criteria:**
- `tools/report.py` no longer exists
- `reports/templates.py` exists and contains exactly 2 templates
- `tests/test_reports.py` passes
- `pytest` passes overall

**Estimated scope:** ~0.5 days.

---

## R4: Pipelines (Python orchestration layer)

**Goal:** extract the deterministic orchestration logic from `agents/*.py` into reusable pipeline functions. Pipelines are pure Python, testable with mocks, and invoke skills via `alpha_research.llm.claude_call` (or equivalent).

**Depends on:** R1 (needs records + verdict helpers), R2 (needs clean model imports).

**Read before implementing:** `guidelines/refactor_plan.md` Part IV, `guidelines/tools_and_skills.md` Part IV (skill-bash-python patterns).

**What to build:**

1. `src/alpha_research/pipelines/__init__.py` — re-exports of the pipeline entry points.

2. `src/alpha_research/pipelines/state_machine.py` — pure functions extracted from `agents/research_agent.py`:
   ```python
   def valid_transitions(stage: ResearchStage) -> list[ResearchStage]: ...
   def stage_guard_satisfied(stage: ResearchStage, artifact: ResearchArtifact) -> bool:
       """Implements g1..g5 from research_plan.md."""
   def backward_trigger_from_finding(finding: Finding) -> BackwardTrigger | None:
       """Maps a finding to t2..t15 if applicable."""
   ```
   No LLM calls, no I/O, no state — pure functions. Unit-testable exhaustively.

3. `src/alpha_research/pipelines/literature_survey.py`:
   ```python
   async def run_literature_survey(
       query: str,
       output_dir: Path,
       apply_rubric: bool = True,
       parallel_evaluations: int = 4,
   ) -> LiteratureSurveyResult
   ```
   Steps:
   - Subprocess call: `alpha-review "<query>" -o <output_dir> --yes`
   - Load `alpha_review.models.ReviewState` from `<output_dir>/review.db`
   - For each included paper, invoke the `paper-evaluate` skill via `alpha_research.llm.claude_call` (parallelize via `asyncio.gather`)
   - Write each evaluation result to `evaluations.jsonl` via `records.append_record`
   - Invoke `gap-analysis` skill on the aggregated evaluations
   - Invoke `pipelines.frontier_mapping.run` on the domain
   - Write `alpha_research_report.md` as the synthesis

4. `src/alpha_research/pipelines/method_survey.py`:
   ```python
   async def run_method_survey(
       challenge_id: str,
       project_dir: Path,
   ) -> MethodSurveyResult
   ```
   Steps:
   - Load the challenge from `challenges.jsonl`
   - Build search queries from `challenge_type` via the §2.7 mapping
   - `alpha_review.apis.search_all` on each query
   - For top-3 methods, expand via `alpha_review.apis.s2_references` and `s2_citations`
   - Parallel `paper-evaluate` skill invocations
   - Build comparison table from evaluation records
   - Invoke `identify-method-gaps` skill
   - Persist method survey record

5. `src/alpha_research/pipelines/frontier_mapping.py`:
   ```python
   async def run_frontier_mapping(
       project_dir: Path,
       domain: str,
   ) -> FrontierReport
   ```
   Steps:
   - `records.read_records(project_dir, "evaluation", filters={"domain": domain})`
   - For each evaluation, invoke `classify-capability` skill
   - Aggregate into reliable / sometimes / cant-yet tiers
   - Load previous frontier snapshot via `read_records(..., "frontier")`
   - Compute diff
   - `append_record(project_dir, "frontier", new_snapshot)`

6. `src/alpha_research/pipelines/research_review_loop.py` (extracted from `agents/orchestrator.py`):
   ```python
   async def run_research_review_loop(
       project_dir: Path,
       max_iterations: int = 5,
       venue: str = "RSS",
   ) -> LoopResult
   ```
   Steps:
   - Load current `ResearchArtifact` from the blackboard
   - Loop up to `max_iterations`:
     - Invoke `adversarial-review` skill
     - Parse review; compute verdict via `metrics.verdict.compute_verdict`
     - Check convergence via `metrics.convergence.check_convergence`
     - If converged or submit-ready → return
     - Else detect backward triggers via `pipelines.state_machine.backward_trigger_from_finding`
     - Human checkpoint: if trigger requires human judgment, pause
     - Invoke `paper-evaluate` (revision mode) or `significance-screen` based on trigger
   - Apply anti-collapse check via `metrics.finding_tracker`

**Tests:**
- `tests/test_pipelines/test_state_machine.py` — exhaustive: all g1-g5 guards, all t2-t15 triggers, all stage transitions.
- `tests/test_pipelines/test_literature_survey.py` — mock `subprocess.run` (for alpha-review CLI) and mock `claude_call`; verify correct sequence.
- `tests/test_pipelines/test_method_survey.py` — mock `alpha_review.apis.*` and skills; verify orchestration.
- `tests/test_pipelines/test_frontier_mapping.py` — fixture evaluations.jsonl; verify tier diff.
- `tests/test_pipelines/test_research_review_loop.py` — mock skill invocations; verify convergence and backward triggers.

**Acceptance criteria:**
- All 5 pipeline modules exist and are importable
- All pipeline tests pass (estimate ~40 new tests)
- Existing tests still pass
- `from alpha_research.pipelines import run_literature_survey` works

**Estimated scope:** ~4 days.

---

## R5: Skills (the core deliverable)

**Goal:** author the 10 `SKILL.md` files that encode the research and review guideline knowledge. This is the highest-leverage phase — approximately 1,150 lines of existing prompt content migrates into 10 markdown files, plus new content for gap-analysis and classify-capability.

**Depends on:** R1 (needs records helper for persistence snippets in skill bodies), R2 (needs model imports clean).

**Read before implementing:** `guidelines/tools_and_skills.md` Part IV, `guidelines/refactor_plan.md` Part III, the relevant existing `prompts/*.py` files as seed content.

**Skill structure (every SKILL.md must have):**
```yaml
---
name: <slug>                               # lowercase, ≤64 chars
description: <≤250 chars>                  # keyword discovery
allowed-tools: Bash, Read, Write, ...      # which tools the skill may invoke
model: claude-opus-4-6                     # or claude-sonnet-4-6 / claude-haiku-4-5
---
```
Plus markdown body with six required sections:
1. **When to use** — trigger conditions
2. **Process** — step-by-step with concrete `bash python -c "..."` snippets
3. **Output format** — JSON schema of the skill's result
4. **Honesty protocol** — what the LLM cannot judge, what to flag
5. **References** — pointers to guideline sections
6. (implicit) frontmatter

**10 skills to author:**

| # | Skill slug | Model | Seed source | New content? |
|---|---|---|---|---|
| 1 | `paper-evaluate` | Sonnet | `prompts/research_system.py` Appendix B block + `prompts/rubric.py` B.1-B.7 | — |
| 2 | `significance-screen` | Opus | `prompts/research_system.py` §2.2 block | — |
| 3 | `formalization-check` | Opus | `prompts/research_system.py` §2.4, §3.1 blocks | sympy verify step |
| 4 | `diagnose-system` | Sonnet | `prompts/research_system.py` empirical diagnosis block | lab-conventions template |
| 5 | `challenge-articulate` | Opus | `prompts/research_system.py` §2.5, §2.7 blocks | — |
| 6 | `experiment-audit` | Sonnet | `prompts/review_system.py` §3.5 + `review_plan.md` §1.6 | audit_stats.py integration |
| 7 | `adversarial-review` | Opus | `prompts/review_system.py` entire file | verdict.py integration |
| 8 | `concurrent-work-check` | Sonnet | `prompts/review_system.py` concurrent-work attack vector | — |
| 9 | `gap-analysis` | Opus | research_guideline §5.1 Axis 1 | fully new |
| 10 | `classify-capability` | Sonnet | research_guideline §5.1 Axis 3 | fully new (small) |
| 11 | `identify-method-gaps` | Sonnet | — | fully new (small) |

Note: the list is 11 items because `classify-capability` and `identify-method-gaps` were factored out of pipelines during the skill-vs-pipeline analysis. They are small skills.

**Reference subfiles** (shared across skills):
- `.claude/skills/adversarial-review/attack_vectors.md` — the 6 attack vectors (§3.1-3.6) in detail
- `.claude/skills/adversarial-review/venue_calibration.md` — venue thresholds (§4)
- `.claude/skills/paper-evaluate/rubric.md` — Appendix B rubric with examples per dimension
- `.claude/skills/formalization-check/reference.md` — §2.4 formalization standards + §3.1 mathematical structure

**Tests:**
- `tests/test_skills/fixtures/` — 3-5 sample papers (short text) + expected evaluation outputs
- `tests/test_skills/test_frontmatter.py` — lints every SKILL.md for valid YAML frontmatter + required fields
- `tests/test_skills/test_sections.py` — verifies each SKILL.md has the 6 required sections
- `tests/test_skills/test_paper_evaluate.py` (integration, marked `@pytest.mark.integration`) — invoke via `claude -p` on a fixture paper, verify output is valid JSON matching the paper-evaluate schema
- `tests/test_skills/test_adversarial_review.py` (integration) — longer fixture, verify Review schema
- `tests/test_skills/test_significance_screen.py` (integration) — fixture problem statement, verify `human_flag=true` for Hamming test

**Acceptance criteria:**
- 11 SKILL.md files exist under `.claude/skills/<slug>/`
- Every SKILL.md passes frontmatter and section lints
- At least 3 integration tests pass via real `claude -p` calls (cached)
- Skills invoke `alpha_review.apis.*`, `alpha_research.tools.paper_fetch`, `alpha_research.records.jsonl`, `alpha_research.metrics.verdict` via Bash snippets in their bodies

**Estimated scope:** ~5 days.

---

## R6: Delete superseded prompts and agents

**Goal:** remove the ~3,300 lines of Python prompt code and agent classes whose content and logic have migrated to skills (R5) and pipelines (R4).

**Depends on:** R4 and R5 complete.

**Read before implementing:** `guidelines/refactor_plan.md` Part I.4, I.5.

**Files to delete:**
- `src/alpha_research/prompts/meta_review_system.py` (324 lines)
- `src/alpha_research/prompts/research_system.py` (467 lines)
- `src/alpha_research/prompts/review_system.py` (505 lines)
- `src/alpha_research/prompts/rubric.py` (398 lines)
- `src/alpha_research/prompts/understanding_system.py` (210 lines)
- `src/alpha_research/prompts/__init__.py` (21 lines)
- `src/alpha_research/prompts/` (directory)
- `src/alpha_research/agents/research_agent.py` (509 lines)
- `src/alpha_research/agents/review_agent.py` (325 lines)
- `src/alpha_research/agents/meta_reviewer.py` (138 lines) — logic already in `metrics/review_quality.py`
- `src/alpha_research/agents/orchestrator.py` (276 lines)
- `src/alpha_research/agents/__init__.py` (8 lines)
- `src/alpha_research/agents/` (directory)
- `tests/test_prompts.py`
- `tests/test_research_agent.py`
- `tests/test_review_agent.py`
- `tests/test_orchestrator.py`

**Import redirects:**
- Grep for all references to `alpha_research.agents.*` and `alpha_research.prompts.*`
- Update to use pipelines + skills + metrics
- `from alpha_research.agents.orchestrator import Orchestrator` → `from alpha_research.pipelines.research_review_loop import run_research_review_loop`
- `from alpha_research.prompts.research_system import build_research_prompt` → no replacement; the content lives in `.claude/skills/paper-evaluate/SKILL.md`
- Any remaining `prompts/*` import is a bug — flag and fix

**Acceptance criteria:**
- ~3,300 lines deleted
- No imports of `alpha_research.prompts.*` or `alpha_research.agents.*` anywhere
- `pytest` passes (tests covering deleted modules have been deleted or replaced by pipeline/skill tests)

**Estimated scope:** ~1 day.

---

## R7: Update CLI and entry points

**Goal:** rewrite `main.py` so the CLI commands route to the new pipelines and skills. CLI shape changes minimally from the user perspective.

**Depends on:** R4, R5, R6.

**Read before implementing:** current `src/alpha_research/main.py`, `guidelines/refactor_plan.md` Part I.7.

**New command layout:**

```
alpha-research survey <query> -o <dir>
    → pipelines.literature_survey.run_literature_survey(query, dir)

alpha-research evaluate <paper_id> -o <dir> [--project <proj_dir>]
    → invoke paper-evaluate skill via claude_call, append to evaluations.jsonl

alpha-research review <artifact_path> -o <dir> [--venue RSS]
    → invoke adversarial-review skill via claude_call, append to reviews.jsonl

alpha-research loop <project_dir> [--max-iterations 5] [--venue RSS]
    → pipelines.research_review_loop.run_research_review_loop(project_dir, ...)

alpha-research significance <problem> [--project <proj_dir>]
    → invoke significance-screen skill, append to significance_screens.jsonl

alpha-research status [<project_dir>]
    → unchanged; reads JSONL files and summarizes
```

**Steps:**
1. Rewrite `main.py` with Typer commands matching the above
2. Delete obsolete commands (old `research`, old `loop` that referenced Orchestrator)
3. Wire each command to the corresponding pipeline function or skill invocation
4. Update help text to reference the new architecture
5. Add `--dry-run` flag for non-destructive testing

**Tests:**
- Update `tests/test_cli.py` to use new commands
- Verify each command's help text
- Integration test: `alpha-research survey "test topic" -o /tmp/cli_test --dry-run` exits cleanly

**Acceptance criteria:**
- `main.py` is ~250 lines (down from 455)
- All CLI tests pass
- `alpha-research --help` shows the new command list

**Estimated scope:** ~1 day.

---

## R8: Integration testing and calibration

**Goal:** validate the refactored system end-to-end on real inputs. This replaces the T10 calibration tests from the original implementation.

**Depends on:** R7.

**What to test:**

### R8.1 Literature survey end-to-end
- `alpha-research survey "tactile manipulation for deformable objects" -o /tmp/e2e_survey`
- Acceptance:
  - LaTeX survey file exists and is non-trivial
  - `evaluations.jsonl` has ≥ 10 records
  - `alpha_research_report.md` exists and has approach taxonomy + frontier + gap sections
  - No exceptions during run

### R8.2 Adversarial review end-to-end
- `alpha-research review tests/fixtures/sample_paper.md -o /tmp/e2e_review --venue RSS`
- Acceptance:
  - `reviews.jsonl` has a new record
  - Review has all required fields (chain_extraction, steel_man, findings, verdict)
  - `metrics.verdict.compute_verdict` was called and the result matches the verdict in the record
  - Findings are classified (fatal/serious/minor)

### R8.3 Calibration against human gold labels
- Fixture: 10 papers with human-assigned rubric scores (curated during T10; reuse if available)
- Run `alpha-research evaluate <paper_id>` on each
- Acceptance: agreement within ±1 on 70%+ of B.1-B.7 dimensions (the T10 threshold)

### R8.4 Skill description discovery
- Verify that `claude -p "screen this research problem for significance: <topic>"` triggers the `significance-screen` skill (not another skill)
- Verify that `claude -p "review this paper adversarially: <path>"` triggers `adversarial-review`
- This is a description-quality test — if skill descriptions don't discriminate well, Claude picks the wrong skill

### R8.5 State machine coverage
- Run `pipelines.research_review_loop.run_research_review_loop` on a fixture project that should trigger each of `t2..t15`
- Verify each backward trigger fires correctly

**Acceptance criteria:**
- All 5 integration tests pass
- Calibration agreement meets T10 threshold (70%+ dimensions within ±1)
- Full `pytest -q` on main tree passes

**Estimated scope:** ~2 days.

---

## R9: Documentation and cleanup

**Goal:** final polish, delete obsolete docs, update README and pointers.

**Depends on:** R8.

**Steps:**
1. Update `README.md`:
   - New architecture diagram (skills + pipelines + helpers + alpha_review dependency)
   - New CLI command reference
   - Quick-start updated for the new commands
   - Remove references to the deleted MCP server plans
2. Update `pyproject.toml`:
   - Confirm `alpha_review` dependency is pinned (to a git SHA or version)
   - Update `[project.scripts]` if CLI entry-point names changed
3. Update `guidelines/research_plan.md`:
   - Add a "Status 2026-04-05" header block at the top pointing to `tools_and_skills.md` and `refactor_plan.md`
   - Keep SM-1..SM-6 sections as-is (still valid architectural spec)
   - Mark "Phase 1-4 build order" as **superseded** by `refactor_plan.md` R0-R9
4. Delete `guidelines/tools_and_skills_implementation.md` (obsolete — its content was for the 19-tool architecture)
5. Verify all tests pass one final time
6. Git tag `post-refactor`

**Acceptance criteria:**
- README updated and accurate
- `pyproject.toml` correct
- `research_plan.md` has the status pointer
- `tools_and_skills_implementation.md` is deleted
- `git status` clean
- `git tag post-refactor` exists

**Estimated scope:** ~0.5 days.

---

## Summary

| Task | Scope | Dependencies | Deliverable |
|---|---|---|---|
| R0 | 1 day | — | alpha_review installed, pre-refactor baseline tagged |
| R1 | 2 days | R0 | `records/jsonl.py`, `metrics/verdict.py`, `scripts/sympy_verify.py`, `scripts/audit_stats.py` + tests |
| R2 | 1 day | R0 | ~1,250 lines of redundant paper/knowledge code deleted |
| R3 | 0.5 days | R0 | `reports/templates.py` created, `tools/report.py` deleted |
| R4 | 4 days | R1, R2 | 5 pipeline modules + tests |
| R5 | 5 days | R1, R2 | 11 `SKILL.md` files + reference subfiles + skill tests |
| R6 | 1 day | R4, R5 | ~3,300 lines of prompts + agents deleted |
| R7 | 1 day | R4, R5, R6 | CLI rewritten to use pipelines + skills |
| R8 | 2 days | R7 | 5 end-to-end integration tests passing, calibration ≥ 70% |
| R9 | 0.5 days | R8 | README, pyproject, docs updated; obsolete files removed |

**Total estimated scope: ~18 days** of focused work.

**Net code change:**
- **Deleted: ~4,550 lines** of redundant / superseded Python
- **Added: ~1,100 lines** of new Python (pipelines, records, helpers, scripts)
- **Added: ~2,500 lines** of markdown (skill bodies + reference files)
- **Added: ~800 lines** of new tests
- **Net Python: -3,450 lines**. Net total (incl. markdown): -150 lines. The project gets smaller AND gains the skills layer.

---

## Parallelizable groups (for multi-agent execution)

- **Group A (parallel, after R0):** R1, R2
- **Group B (parallel, after R1 + R2):** R3, R4, R5 — each touches disjoint directories
- **Group C (sequential, after Group B):** R6 → R7 → R8 → R9
