# Alpha Research Project Lifecycle Revision Plan

## Implementation Task Assignment

Multi-agent task breakdown for implementing the lifecycle revision. Each task is self-contained with explicit dependencies, files to create/modify, and acceptance criteria so an implementation agent can execute it without additional context.

**Source documents (agents MUST read before implementing):**
- This file (`project_lifecycle_revision_plan.md`) — formal definitions §55-177, invariants §179-219, schemas §428-578, on-disk layout §630-658, resume protocol §666-709, service/agent boundary §738-768, lifecycle flows §857-889
- `src/alpha_research/models/blackboard.py` — current Blackboard, ResearchArtifact, ConvergenceState, Venue models
- `src/alpha_research/models/research.py` — current Paper, Evaluation, TaskChain models
- `src/alpha_research/knowledge/store.py` — current KnowledgeStore (SQLite CRUD)
- `src/alpha_research/agents/orchestrator.py` — current research-review loop orchestrator
- `src/alpha_research/main.py` — current CLI
- `src/alpha_research/api/` — current FastAPI backend

### Task Dependency Graph

```
L1 (project models) ─────────────────────────────────────────────────┐
  ├─► L2 (project registry + service)                                │
  │     └─► L4 (resume service)                                      │
  ├─► L3 (git state + source snapshot service)                       │
  │     ├─► L4 (resume service)                                      │
  │     └─► L5 (snapshot writer)                                     │
  ├─► L5 (snapshot writer)                                           │
  │     └─► L6 (project orchestrator)                                │
  ├─► L4 + L5 ──────────────────────► L6 (project orchestrator)      │
  │                                     └─► L8 (CLI revision)        │
  ├─► L7 (understanding agent) ───────► L6                           │
  └─► L6 ──────────────────────────────► L8 → L9 → L10              │
                                              │      │               │
                                              ▼      ▼               │
                                          L9 (API)  L10 (frontend)   │
                                              └──► L11 (integration) │
```

**Parallelizable groups:**
- **Group A (parallel):** L2, L3 — both depend only on L1
- **Group B (parallel):** L4, L5, L7 — depend on L1+L2+L3
- **Group C (sequential):** L6 → L8 → L9 → L10 → L11

---

### L1: Project & Snapshot Data Models (Foundation)

**Read before implementing:** §55-177 (formal definitions), §428-578 (proposed formal structures), §579-597 (what constitutes project state)

**Depends on:** Nothing

**What to build:**
- `src/alpha_research/models/project.py` — Project lifecycle Pydantic V2 models:
  - `ProjectManifest` — stable identity (§432-455): `project_id`, `slug`, `name`, `description`, `project_type` (literature|codebase|hybrid), `created_at`, `status` (draft|active|paused|completed|archived), `primary_question`, `domain`, `tags`, `source_bindings`, `alpha_research_version`
  - `SourceBinding` — link to external source (§456-473): `binding_id`, `binding_type` (git_repo|directory|paper_set), `root_path`, `include_paths`, `exclude_paths`, `is_primary`, `repo_remote`, `tracked_branch`
  - `ProjectState` — mutable operational head (§474-494): `project_id`, `current_snapshot_id`, `current_blackboard_path`, `current_status` (idle|understanding|researching|reviewing|paused|error), `last_understanding_snapshot_id`, `last_completed_run_id`, `active_run_id`, `resume_required`, `source_changed_since_last_snapshot`, `last_resumed_at`, `notes`
- `src/alpha_research/models/snapshot.py` — Snapshot and run Pydantic V2 models:
  - `SourceSnapshot` — immutable source-tree state (§495-515): `source_snapshot_id`, `binding_id`, `captured_at`, `vcs_type` (git|none), `commit_sha`, `branch_name`, `is_dirty`, `patch_path`, `untracked_manifest_path`, `source_fingerprint`
  - `UnderstandingSnapshot` — derived structured understanding (§516-536): `understanding_snapshot_id`, `project_id`, `source_snapshot_id`, `created_at`, `summary`, `architecture_map`, `important_paths`, `open_questions`, `assumptions`, `warnings`, `confidence`
  - `ProjectSnapshot` — immutable checkpoint binding (§537-557): `snapshot_id`, `project_id`, `created_at`, `snapshot_kind` (create|resume|pre_run|post_run|milestone|manual), `parent_snapshot_id`, `source_snapshot_id`, `understanding_snapshot_id`, `blackboard_path`, `artifact_refs`, `run_id`, `summary`, `note`
  - `ResearchRun` — execution record (§558-578): `run_id`, `project_id`, `started_at`, `finished_at`, `run_type` (understanding|digest|deep|loop|resume_refresh), `status` (running|completed|failed|cancelled), `input_snapshot_id`, `output_snapshot_id`, `summary`, `error`
- Update `src/alpha_research/models/__init__.py` to re-export all new models

**Key design rules:**
- All models must use Pydantic V2 (`BaseModel`)
- All snapshot models must be immutable after creation (no mutating methods)
- `ProjectManifest` and `ProjectState` must round-trip through JSON (implement `save(path)` and `load(path)` class methods, same pattern as `Blackboard`)
- IDs should be generated with `uuid4().hex[:12]` for human-readable uniqueness
- `SourceBinding.root_path` should be stored as an absolute path string

**Acceptance criteria:**
- All models validate with Pydantic V2
- `ProjectManifest` round-trips through JSON without data loss
- `ProjectState` round-trips through JSON without data loss
- `ProjectSnapshot` is frozen after creation (test that mutation raises)
- `SourceSnapshot.source_fingerprint` is a string field (computation is in L3, not here)
- Unit tests in `tests/test_project_models.py` covering validation, serialization, enum constraints
- Estimated scope: ~300 lines models + ~200 lines tests

---

### L2: Project Registry + Project Service

**Read before implementing:** §55-78 (project definition), §579-597 (what is project state), §630-658 (on-disk layout)

**Depends on:** L1

**What to build:**
- `src/alpha_research/projects/__init__.py`
- `src/alpha_research/projects/registry.py` — Project registry backed by `data/projects/index.json`:
  - `list_projects() -> list[ProjectManifest]`
  - `get_project(project_id: str) -> ProjectManifest | None`
  - `register_project(manifest: ProjectManifest) -> None`
  - `remove_project(project_id: str) -> None`
  - Auto-creates `data/projects/` directory structure on first use
- `src/alpha_research/projects/service.py` — Core project lifecycle service (deterministic, no LLM):
  - `create_project(name, project_type, primary_question, source_bindings, ...) -> ProjectManifest`
    - Generates `project_id` and `slug`
    - Creates on-disk directory structure per §634-658
    - Initializes empty `state.json`, `blackboard.json`
    - Initializes project-local `knowledge.db`
    - Registers in index
  - `load_project(project_id) -> tuple[ProjectManifest, ProjectState]`
  - `update_state(project_id, **updates) -> ProjectState`
  - `get_project_dir(project_id) -> Path`
  - `get_knowledge_store(project_id) -> KnowledgeStore`

**On-disk layout to create (§634-658):**
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

**Acceptance criteria:**
- `create_project` produces the full directory structure
- `load_project` reads manifest + state from disk
- `list_projects` returns all registered projects
- Registry survives process restart (persisted to `index.json`)
- `get_knowledge_store` returns a `KnowledgeStore` scoped to the project's `knowledge.db`
- Tests in `tests/test_project_registry.py` and `tests/test_project_service.py`
- Estimated scope: ~250 lines + ~200 lines tests

---

### L3: Git State + Source Snapshot Service

**Read before implementing:** §296-377 (git usage policy), §495-515 (SourceSnapshot schema), §792-806 (source snapshot service spec)

**Depends on:** L1

**What to build:**
- `src/alpha_research/projects/git_state.py` — Deterministic git inspection service (no LLM):
  - `is_git_repo(path: Path) -> bool`
  - `get_repo_info(path: Path) -> dict` — returns `{root, branch, commit_sha, remote, is_dirty}`
  - `get_tracked_diff(path: Path) -> str` — `git diff --binary` output
  - `get_untracked_files(path: Path) -> list[str]` — list of untracked file paths
  - `compute_source_fingerprint(commit_sha: str, diff: str) -> str` — `sha256(commit_sha + diff)`
  - `create_worktree(repo_path: Path, commit_sha: str, target_path: Path) -> Path` — `git worktree add`
  - `remove_worktree(worktree_path: Path) -> None` — `git worktree remove`

  All git commands via `subprocess.run` with proper error handling. No destructive operations (no reset, no force checkout, no stash — per §361-377).

- `capture_source_snapshot(binding: SourceBinding, snapshot_dir: Path) -> SourceSnapshot`:
  - For git_repo bindings: inspect repo, capture commit/branch/dirty state
  - If dirty: save `tracked.diff` and `untracked_manifest.json` under `snapshot_dir/patches/`
  - Optionally archive untracked file contents to `snapshot_dir/patches/untracked/`
  - Compute and store `source_fingerprint`
  - For non-git bindings: fingerprint is hash of file listing + mtimes
  - Return a populated `SourceSnapshot` model

**Safety rules (§730-736):**
- Never run `git reset --hard`, `git checkout` over local changes, `git stash`, or branch rewrites
- All git operations are read-only inspection + `git diff` + `git worktree`
- `create_worktree` is the only write operation, and it creates an isolated copy

**Acceptance criteria:**
- `get_repo_info` returns correct commit SHA, branch, dirty status for a test repo
- `capture_source_snapshot` on a clean repo stores commit SHA with `is_dirty=False`
- `capture_source_snapshot` on a dirty repo stores the diff patch file and sets `is_dirty=True`
- `compute_source_fingerprint` is deterministic (same input = same output)
- `create_worktree` creates an isolated worktree at the specified commit
- Tests in `tests/test_git_state.py` using a temporary git repo fixture
- Estimated scope: ~200 lines + ~200 lines tests

---

### L4: Resume Service

**Read before implementing:** §152-166 (resume definition), §666-709 (formal resume protocol), §710-736 (dirty workspace handling)

**Depends on:** L1, L2, L3

**What to build:**
- `src/alpha_research/projects/resume.py` — Deterministic resume lifecycle service (no LLM):
  - `ResumeMode` enum: `current_workspace | exact_snapshot | milestone`
  - `prepare_resume(project_id, mode, snapshot_id=None) -> ResumeContext`
    - Mode A (`current_workspace`, §670-685):
      1. Load project manifest and current state
      2. Inspect currently bound source directory
      3. Capture fresh `SourceSnapshot`
      4. Compare against source snapshot referenced by `current_snapshot_id`
      5. Return `ResumeContext` with source delta summary, previous understanding, new source snapshot
    - Mode B (`exact_snapshot`, §686-699):
      1. Select target `ProjectSnapshot`
      2. Resolve its `SourceSnapshot`
      3. If git-backed, create a `git worktree` at the stored commit
      4. If dirty patch exists, apply it in the isolated worktree
      5. Return `ResumeContext` with worktree path and prior understanding
    - Mode C (`milestone`, §700-709):
      1. Resolve milestone tag or snapshot id
      2. Follow Mode B flow
  - `ResumeContext` model: `source_snapshot`, `previous_understanding`, `source_delta_summary`, `worktree_path` (optional), `resume_mode`
  - `compute_source_delta(old_snapshot, new_snapshot) -> str` — human-readable summary of what changed (files added/removed/modified, commit range)

**Acceptance criteria:**
- Mode A: loads project, captures new source snapshot, detects changes since last snapshot
- Mode B: creates worktree at historical commit, applies dirty patch if present
- Mode C: resolves milestone → delegates to Mode B
- `compute_source_delta` produces a readable diff summary
- Resume never modifies the user's working tree (Invariant 6, §202-204)
- Tests in `tests/test_resume.py` with a temporary git repo fixture
- Estimated scope: ~200 lines + ~150 lines tests

---

### L5: Snapshot Writer

**Read before implementing:** §117-126 (project snapshot definition), §259-266 (snapshot semantics), §537-557 (ProjectSnapshot schema), §599-628 (snapshot hierarchy), §630-658 (on-disk layout)

**Depends on:** L1, L2, L3

**What to build:**
- `src/alpha_research/projects/snapshots.py` — Snapshot persistence service (deterministic, no LLM):
  - `create_project_snapshot(project_id, kind, source_snapshot, understanding_snapshot=None, blackboard_path=None, run_id=None, parent_snapshot_id=None, summary="", note="") -> ProjectSnapshot`
    - Generates `snapshot_id`
    - Creates `data/projects/<slug>/snapshots/<snapshot_id>/` directory
    - Copies/writes `snapshot.json`, `source.json`, `understanding.json`, `blackboard.json` into it
    - The snapshot directory is self-contained — all referenced files are stored within it
    - Returns the `ProjectSnapshot` model
  - `load_snapshot(project_id, snapshot_id) -> ProjectSnapshot`
  - `list_snapshots(project_id) -> list[ProjectSnapshot]` — sorted by `created_at`
  - `get_latest_snapshot(project_id, kind=None) -> ProjectSnapshot | None`
  - `tag_milestone(project_id, snapshot_id, tag_name: str) -> None` — creates a git tag `alpha-research/<slug>/milestone/<tag_name>` if git-backed

**Snapshot immutability (Invariant 2, §188-189):**
- Once written, snapshot directory contents must not be modified
- `create_project_snapshot` writes files atomically (write to temp, then rename)

**Acceptance criteria:**
- Created snapshot directory contains all referenced JSON files
- `load_snapshot` reconstructs the exact `ProjectSnapshot` model from disk
- `list_snapshots` returns snapshots in chronological order
- Snapshot files are not modified after creation
- `tag_milestone` creates a git tag at the source snapshot's commit SHA
- Tests in `tests/test_snapshots.py`
- Estimated scope: ~200 lines + ~150 lines tests

---

### L6: Project Orchestrator

**Read before implementing:** §772-790 (project orchestrator spec), §857-889 (lifecycle flows A and B)

**Depends on:** L1, L2, L3, L4, L5, L7

**What to build:**
- `src/alpha_research/projects/orchestrator.py` — Top-level project coordinator (deterministic service that calls agents):
  - `create_and_understand(name, project_type, question, source_path, ...) -> ProjectManifest`
    Flow A (§859-871):
    1. Call `ProjectService.create_project` (L2)
    2. Call `SourceSnapshotService.capture_source_snapshot` (L3)
    3. Call `UnderstandingAgent.understand` (L7) → produces `UnderstandingSnapshot`
    4. Call `SnapshotWriter.create_project_snapshot(kind="create")` (L5)
    5. Update project state
    6. Return manifest
  - `resume_and_continue(project_id, mode, snapshot_id=None) -> ProjectState`
    Flow B (§873-889):
    1. Call `ResumeService.prepare_resume` (L4) → get `ResumeContext`
    2. Call `UnderstandingAgent.refresh_understanding` (L7) with source delta
    3. Create resume snapshot (L5)
    4. Update project state
    5. Return updated state (caller then decides whether to run research/review)
  - `run_research(project_id, mode, question) -> ResearchRun`
    1. Create `pre_run` snapshot
    2. Create `ResearchRun` record
    3. Load project's `KnowledgeStore`
    4. Call existing `Orchestrator.run_loop` (from `agents/orchestrator.py`) with project context
    5. Create `post_run` snapshot
    6. Update project state with run results
    7. Return completed `ResearchRun`
  - `create_manual_snapshot(project_id, note) -> ProjectSnapshot`

**Key design rule (§738-768):**
This orchestrator is a deterministic coordinator. It calls agents but does not contain prompt logic. It manages state transitions, snapshot creation, and persistence.

**Acceptance criteria:**
- `create_and_understand` produces a project with manifest, state, initial snapshot, and understanding
- `resume_and_continue` detects source changes, refreshes understanding, creates resume snapshot
- `run_research` wraps the existing research loop with pre/post snapshots and run records
- Every run produces a snapshot (Invariant 8, §212-216) or records why it didn't
- Project state is updated after each operation
- Tests in `tests/test_project_orchestrator.py` (mock the agents, test the lifecycle flow)
- Estimated scope: ~350 lines + ~250 lines tests

---

### L7: Understanding Agent

**Read before implementing:** §128-135 (understanding snapshot definition), §808-820 (understanding agent spec), §516-536 (UnderstandingSnapshot schema)

**Depends on:** L1

**What to build:**
- `src/alpha_research/projects/understanding.py` — LLM-based understanding agent:
  - `UnderstandingAgent` class:
    - `__init__(llm=None)` — optional LLM callable (same pattern as existing agents)
    - `understand(project: ProjectManifest, source_snapshot: SourceSnapshot, file_contents: dict[str, str]) -> UnderstandingSnapshot`
      - Builds a system prompt instructing the agent to analyze the source material
      - For `codebase` projects: identify architecture, modules, entry points, dependencies, open questions
      - For `literature` projects: identify research landscape, key themes, gaps, methodology
      - For `hybrid`: combine both
      - Parses LLM response into structured `UnderstandingSnapshot`
    - `refresh_understanding(project: ProjectManifest, previous: UnderstandingSnapshot, source_delta: str, file_contents: dict[str, str]) -> UnderstandingSnapshot`
      - Given prior understanding + what changed, produce an updated understanding
      - Must explicitly note what changed and what assumptions may be invalidated
- `src/alpha_research/prompts/understanding_system.py` — System prompt builder:
  - `build_understanding_prompt(project_type, source_summary, previous_understanding=None, source_delta=None) -> str`
  - Encodes: project type expectations, required output fields, depth requirements
  - Output format: JSON matching `UnderstandingSnapshot` schema

**File selection strategy:**
- The agent does NOT select files — it receives `file_contents: dict[str, str]` from the project orchestrator
- File selection is a deterministic service responsibility (done by the orchestrator using source binding paths, gitignore filtering, size limits)
- Total content should be capped at ~100K tokens by the caller

**Acceptance criteria:**
- `understand` produces a valid `UnderstandingSnapshot` with non-empty `summary`, `important_paths`, `open_questions`
- `refresh_understanding` includes delta-awareness (what changed since last understanding)
- Agent works without LLM (returns a structured stub when `llm=None`, same pattern as `ResearchAgent`)
- Prompt builder produces different prompts for `codebase` vs `literature` project types
- Tests in `tests/test_understanding.py` (mock LLM, test prompt construction and response parsing)
- Estimated scope: ~250 lines agent + ~150 lines prompts + ~150 lines tests

---

### L8: CLI Revision

**Read before implementing:** §920-943 (CLI revision plan)

**Depends on:** L6

**What to build:**

Revise `src/alpha_research/main.py` to add project-aware commands using Typer subcommand groups.

**New `project` command group:**
- `alpha-research project create <name> --type codebase --source-path <path> --question <question>` — calls `ProjectOrchestrator.create_and_understand`
- `alpha-research project list` — calls `Registry.list_projects`, prints table
- `alpha-research project show <project_id>` — prints manifest + current state + latest snapshot summary
- `alpha-research project status <project_id>` — prints operational status, dirty flags, last run
- `alpha-research project snapshot <project_id> [--note <note>] [--milestone]` — calls `ProjectOrchestrator.create_manual_snapshot`
- `alpha-research project resume <project_id> [--mode current_workspace|exact_snapshot|milestone] [--snapshot <id>]` — calls `ProjectOrchestrator.resume_and_continue`

**Revised existing commands:**
- `alpha-research research --project <project_id> <question>` — runs research within a project context
- `alpha-research loop --project <project_id> <question>` — runs the full loop within a project
- When `--project` is provided, use project-scoped `KnowledgeStore` and blackboard

**CLI design rules (§939-943):**
- No implicit singleton project — `--project` must be explicit
- No destructive git operations without `--force` and confirmation prompt
- Resume mode defaults to `current_workspace`

**Acceptance criteria:**
- `alpha-research project create "my project" --type literature --question "tactile manipulation"` creates a project directory and prints the project ID
- `alpha-research project list` shows all projects with status
- `alpha-research project resume <id>` performs current_workspace resume
- Existing commands (`research`, `review`, `loop`, `status`) continue to work without `--project` (backward compatible)
- Tests in `tests/test_cli_project.py`
- Estimated scope: ~250 lines + ~150 lines tests

---

### L9: API Revision

**Read before implementing:** §945-960 (API revision plan)

**Depends on:** L6

**What to build:**

Add `src/alpha_research/api/routers/projects.py` — new project-aware endpoints:
- `POST /api/projects` — create project (body: name, type, question, source_path)
- `GET /api/projects` — list all projects
- `GET /api/projects/{project_id}` — get project manifest
- `GET /api/projects/{project_id}/state` — get current project state
- `GET /api/projects/{project_id}/snapshots` — list snapshots
- `POST /api/projects/{project_id}/snapshots` — create manual snapshot
- `POST /api/projects/{project_id}/resume` — trigger resume (body: mode, snapshot_id)
- `GET /api/projects/{project_id}/runs` — list research runs

Update `src/alpha_research/api/models.py` with Pydantic response models for project endpoints.

Mount the new router in `src/alpha_research/api/app.py`.

Thread `project_id` as an optional query parameter through existing endpoints:
- `GET /api/papers?project_id=<id>` — scope to project's knowledge store
- `GET /api/evaluations?project_id=<id>` — scope to project's knowledge store
- `GET /api/graph/nodes?project_id=<id>` — scope to project

**Acceptance criteria:**
- All new endpoints return correct data
- Project creation returns a project ID
- Snapshot listing returns snapshots in chronological order
- Existing endpoints continue to work without `project_id` (backward compatible)
- Tests in `tests/test_api_projects.py`
- Estimated scope: ~250 lines + ~150 lines tests

---

### L10: Frontend Revision

**Read before implementing:** §962-986 (frontend revision plan)

**Depends on:** L9

**What to build:**

Add project lifecycle views to `frontend/src/`:

- `components/project/project-list.tsx` — list of projects with status badges, create button
- `components/project/create-project-dialog.tsx` — form: name, type, question, source path
- `components/project/project-overview.tsx` — shows manifest, current state, latest understanding summary
- `components/project/snapshot-history.tsx` — timeline of snapshots with kind badges, expandable details
- `components/project/resume-dialog.tsx` — shows source delta, last understanding, mode selector, confirm button
- `components/project/run-history.tsx` — list of research runs with status, duration, links to snapshots

Update `src/app/page.tsx`:
- Add project selector in the top bar (dropdown or sidebar)
- When a project is selected, scope all data fetching to that project
- Show project overview as default view when no research is running

Add hooks:
- `hooks/use-projects.ts` — CRUD for projects list
- `hooks/use-project-detail.ts` — project state, snapshots, runs

Add API calls to `lib/api.ts` for all new project endpoints.

Add types to `lib/types.ts` for `ProjectManifest`, `ProjectState`, `ProjectSnapshot`, `ResearchRun`.

**Acceptance criteria:**
- Project list page shows all projects
- Create dialog submits to API and refreshes list
- Project overview displays manifest + state + understanding summary
- Snapshot history renders chronologically with kind badges
- Resume dialog shows source delta and mode selection
- Frontend builds without TypeScript errors
- Estimated scope: ~500 lines components + ~100 lines hooks/api

---

### L11: Integration Test — `alpha_robot` as First Project

**Read before implementing:** §1099-1140 (alpha_robot guidance)

**Depends on:** L8, L9

**What to build:**
- `tests/test_project_integration.py` — end-to-end lifecycle test:
  1. Create a temporary git repo with sample Python files
  2. `create_and_understand` → verify project directory, manifest, initial snapshot, understanding
  3. Add a commit to the repo
  4. `resume_and_continue(mode="current_workspace")` → verify source delta detected, understanding refreshed, resume snapshot created
  5. `run_research(mode="digest")` → verify pre/post snapshots, run record created
  6. `create_manual_snapshot(note="milestone 1")` → verify milestone snapshot
  7. Check that all invariants hold:
     - Every snapshot is immutable (§188-189)
     - Every run has a snapshot (§212-216)
     - Source fingerprint changes when source changes (§188)
     - Resume detects dirty workspace (§199-200)

**Acceptance criteria:**
- Full create → resume → research → snapshot lifecycle completes without error
- All 9 invariants from §179-219 are verified
- Tests pass with mocked LLM (no API key required)
- Estimated scope: ~300 lines tests

---

### Build Order Summary

```
Phase 0:  L1 (project models)                ← foundation, parallelize nothing
Phase 1:  L2 + L3 (parallel)                 ← registry/service + git state
Phase 2:  L4 + L5 + L7 (parallel)            ← resume + snapshots + understanding agent
Phase 3:  L6                                  ← project orchestrator (binds everything)
Phase 4:  L8 + L9 (parallel)                 ← CLI + API revisions
Phase 5:  L10                                 ← frontend revision
Phase 6:  L11                                 ← integration test
```

**Critical path:** L1 → L3 → L5 → L6 → L8. The git state service (L3) and snapshot writer (L5) are the most correctness-critical pieces.

**What to build first for validation:** L1 + L2 + L3 + L5 gives a minimal system that can create a project, capture source state, and persist snapshots — the deterministic lifecycle foundation. Then add L7 (understanding) and L6 (orchestrator) to get the full create/resume flows.

---

## Objective

Revise `alpha_research` so it can:

1. create a new research project and operate on it as a first-class entity
2. resume an existing project, re-read and re-understand it, then continue research safely
3. preserve important checkpoints of the project in a formally defined, inspectable, and reproducible way

This revision plan is intentionally grounded in the current repo state, not the aspirational README alone. The guiding principle is to add a robust **project lifecycle layer** around the existing blackboard-and-agent core rather than rewriting that core.

## Why The Previous Plan Was Not Yet Sufficient

The earlier version correctly identified the need for:

- project identity
- project-scoped blackboards
- understanding snapshots
- create/resume flows

But it still left several implementation-critical questions too loose:

- what exactly counts as **project state**
- what exactly a **snapshot** stores
- when to use **git branch**, **git commit**, **git tag**, **git worktree**, or non-git storage
- how resume works when the source tree is dirty
- what is immutable history versus mutable head state
- which lifecycle pieces should be deterministic services versus LLM agents

Those questions need formal answers before implementation, or the system will become ambiguous and fragile.

## Design Thesis

The clean design is:

- **Project** is the top-level durable research container
- **Git** is the authoritative tool for source-tree lineage when the project is backed by a repository
- **Project snapshots** are immutable checkpoints that bind source state, blackboard state, understanding state, and artifacts together
- **Project state** is the mutable HEAD pointer and operational status of the project
- **Understanding snapshots** are derived artifacts, not the only checkpoint type
- **Create** and **resume** are deterministic lifecycle operations that call agents only for interpretation and synthesis

In short:

- use `git` for source versioning
- use structured files and SQLite for project/research state
- use agents for understanding, research, review, and critique
- do not use agents as the source of truth for lifecycle bookkeeping

## Formal Definitions Required Before Implementation

These concepts should be explicitly defined in models and documentation before writing lifecycle code.

### 1. Project

A **Project** is a durable research container representing a single coherent research effort.

A project is not:

- just a question string
- just a repo path
- just a blackboard
- just a set of papers

A project is the tuple of:

- stable identity
- source bindings
- goals and scope
- mutable current state
- immutable snapshot history
- research artifacts
- knowledge state
- run history

### 2. Project Source

The **Project Source** is the external material the research is grounded in.

Depending on project type, this may include:

- one git repo
- multiple directories
- papers / PDFs
- reports
- configs
- datasets or dataset manifests

For `alpha_robot`, the primary source is a live codebase plus configs and outputs.

### 3. Project State

**Project State** is the mutable operational head of the project. It is not the same thing as project history.

Project state should answer:

- what project is this
- where are its sources
- what source revision is currently bound
- what is the current blackboard
- what was the last formal checkpoint
- what was the last understanding snapshot
- what run is active or last completed
- whether resume is required
- whether the current source differs from the last captured source

Project state is the state that changes often. It should be stored explicitly, separately from immutable history.

### 4. Project Snapshot

A **Project Snapshot** is an immutable checkpoint that binds together:

- source state
- blackboard state
- understanding snapshot reference
- produced artifacts
- the run that created it
- provenance metadata

This is the core missing abstraction for resume.

Every important checkpoint in the project should be represented as a project snapshot.

### 5. Understanding Snapshot

An **Understanding Snapshot** is a derived, structured interpretation of the project at a specific source snapshot.

It should not be treated as the source of truth. It is an agent-produced artifact derived from:

- source snapshot
- prior blackboard and artifacts
- run history

It exists so resume can begin from a saved understanding and then refresh it.

### 6. Research Run

A **Research Run** is one bounded execution of the system against a project.

Examples:

- initial project understanding
- resume pass
- digest run
- deep analysis run
- one full research-review loop

A run produces logs, events, outputs, and often a new snapshot.

### 7. Resume

**Resume** is a formal lifecycle operation, not a convenience flag.

To resume a project means:

1. load current project state and selected snapshot
2. capture or inspect current source state
3. compare with the last captured source state
4. refresh understanding
5. record the new resume context
6. only then continue research

Resume must never mean "deserialize blackboard and continue blindly."

### 8. Mutable HEAD vs Immutable History

This must be explicit.

- `ProjectManifest`: mostly stable identity
- `ProjectState`: mutable head
- `ProjectSnapshot`: immutable checkpoint
- `UnderstandingSnapshot`: immutable derived artifact
- `ResearchRun`: immutable execution record

If this boundary is not formalized, resume semantics will drift and become unreliable.

## Lifecycle Invariants

These invariants should hold in implementation and tests.

### Invariant 1

Every project has exactly one mutable current state file and zero or more immutable snapshots.

### Invariant 2

Every immutable project snapshot points to exactly one source snapshot and one blackboard version.

### Invariant 3

The authoritative identifier for a git-backed source snapshot is the **commit SHA**, not the branch name.

### Invariant 4

A branch is a moving collaboration reference, not a reliable historical checkpoint by itself.

### Invariant 5

If the source tree is dirty, the snapshot must explicitly record that fact and preserve the delta needed to reconstruct or inspect that state.

### Invariant 6

Resume must not destructively rewrite the user’s working tree without explicit approval.

### Invariant 7

Understanding snapshots are versioned artifacts tied to source snapshots; they are not free-floating summaries.

### Invariant 8

Every research run either:

- produces a new snapshot
- explicitly records why it did not

### Invariant 9

Project-local research state must remain usable even if global field knowledge evolves independently.

## What Should Be Formally Structured Before Implementation

The following should be designed in concrete schemas first.

### A. Project Identity

Must define:

- `project_id`
- `slug`
- human-readable `name`
- `project_type`
- adapter type
- source bindings

### B. Source Binding

Must define:

- whether the project is git-backed
- repo root or source paths
- selected inclusion roots
- excluded paths
- default branch or tracked branch

### C. Project State

Must define:

- current lifecycle status
- current blackboard pointer
- current snapshot pointer
- current source binding state
- last understanding snapshot pointer
- active run pointer
- dirty / stale flags

### D. Snapshot Semantics

Must define:

- what triggers snapshot creation
- which fields are immutable
- how parent-child relationships are represented
- which files are stored under the snapshot directory

### E. Resume Modes

Must define:

- resume from current workspace
- resume from exact historical snapshot
- resume from latest named milestone

### F. Dirty Workspace Policy

Must define:

- whether dirty workspaces are allowed
- how tracked and untracked changes are captured
- when user approval is needed

### G. Tool Ownership

Must define which responsibilities are:

- deterministic services
- agentic reasoning tasks

This is crucial. Project lifecycle must not be implemented as opaque prompt logic.

## Recommended Tooling Choices

This section answers which concrete tools should structure the important state.

## Git Usage Policy

### Use `git commit` as the primary source checkpoint

For git-backed projects, the immutable checkpoint anchor should be:

- `commit_sha`

Why:

- immutable
- reproducible
- easy to diff
- compatible with worktrees
- easy to compare against later resume states

### Use `git branch` as the moving line of development

Recommended managed branch naming:

- `alpha-research/<project_slug>`

Why:

- expresses the current collaboration head
- useful for continued research work
- easy to resume by convention

But branch name is not sufficient for exact resume because it moves.

### Use `git tag` only for named milestones

Recommended milestone tag naming:

- `alpha-research/<project_slug>/milestone/<snapshot_id>`

Why:

- milestone tags are human-meaningful
- they should not be created for every auto snapshot

Do not use tags as the only snapshot mechanism.

### Use `git worktree` for safe exact historical resume

`git worktree` should be the preferred tool when the system needs to inspect or continue from an exact historical commit without disturbing the user’s active checkout.

This is especially valuable for:

- exact snapshot resume
- historical comparison
- side-by-side analysis
- safe execution in codebase projects

### Use `git diff --binary` plus a file manifest for dirty states

When the working tree is dirty and we need a checkpoint without forcing a commit:

- store the base `commit_sha`
- store a binary-safe patch generated from tracked changes
- store a manifest of untracked files
- optionally archive untracked file contents under the snapshot directory

This should be the default non-invasive snapshot strategy.

### Do not use `git stash` as a formal system primitive

Reasons:

- mutable and easy to lose
- poor provenance
- not a durable checkpoint mechanism
- not good for inspectable project history

### Do not auto-commit user changes without explicit approval

Default policy:

- capture dirty state non-invasively
- offer optional managed commits only with explicit user consent

This matters for both safety and trust.

## Non-Git Storage Policy

Git is for source lineage, not for all project state.

### Use JSON + Pydantic for canonical project metadata and snapshots

Use JSON files for:

- `project.json`
- `state.json`
- `blackboard.json`
- `snapshot.json`
- `understanding.json`
- `run.json`

Reasons:

- inspectable
- aligns with current Pydantic models
- easy to diff
- easy to test

### Use SQLite for queryable project-local research memory

Use SQLite for:

- knowledge store
- evaluations
- findings
- feedback
- optional run event indexing later

Reasons:

- current repo already uses SQLite
- good for structured querying
- local and durable

### Use Markdown for human-facing artifacts

Use Markdown for:

- reports
- milestone summaries
- manual notes
- resume briefs

Markdown is not the canonical machine state, but it remains the best human-readable output format.

## Proposed Formal Structures

The model layer should explicitly separate stable identity, mutable head state, immutable snapshots, and derived understanding.

### `ProjectManifest`

Purpose:

- stable identity and configuration

Fields:

- `project_id`
- `slug`
- `name`
- `description`
- `project_type`: `literature | codebase | hybrid`
- `adapter_type`: `literature | codebase | hybrid`
- `created_at`
- `updated_at`
- `status`: `draft | active | paused | completed | archived`
- `primary_question`
- `domain`
- `tags`
- `source_bindings`
- `default_resume_mode`
- `alpha_research_version`

### `SourceBinding`

Purpose:

- formal link from project to external source roots

Fields:

- `binding_id`
- `binding_type`: `git_repo | directory | paper_set | artifact_set`
- `root_path`
- `include_paths`
- `exclude_paths`
- `is_primary`
- `repo_remote`
- `tracked_branch`
- `default_worktree_path` optional

### `ProjectState`

Purpose:

- mutable operational head

Fields:

- `project_id`
- `current_snapshot_id`
- `current_blackboard_path`
- `current_status`: `idle | understanding | researching | reviewing | paused | error`
- `last_understanding_snapshot_id`
- `last_completed_run_id`
- `active_run_id`
- `resume_required`
- `source_changed_since_last_snapshot`
- `last_seen_source_snapshot_id`
- `last_resumed_at`
- `notes`

### `SourceSnapshot`

Purpose:

- immutable captured source-tree state

Fields:

- `source_snapshot_id`
- `binding_id`
- `captured_at`
- `vcs_type`: `git | none`
- `repo_root`
- `branch_name`
- `commit_sha`
- `is_dirty`
- `patch_path` optional
- `untracked_manifest_path` optional
- `source_fingerprint`
- `selected_paths`

### `UnderstandingSnapshot`

Purpose:

- derived structured understanding of the source snapshot

Fields:

- `understanding_snapshot_id`
- `project_id`
- `source_snapshot_id`
- `created_at`
- `summary`
- `architecture_map`
- `important_paths`
- `open_questions`
- `assumptions`
- `warnings`
- `artifact_refs`
- `confidence`

### `ProjectSnapshot`

Purpose:

- immutable checkpoint binding source, understanding, blackboard, and artifacts

Fields:

- `snapshot_id`
- `project_id`
- `created_at`
- `snapshot_kind`: `create | resume | pre_run | post_run | milestone | manual`
- `parent_snapshot_id`
- `source_snapshot_id`
- `understanding_snapshot_id`
- `blackboard_path`
- `artifact_refs`
- `run_id`
- `summary`
- `note`

### `ResearchRun`

Purpose:

- record one execution boundary

Fields:

- `run_id`
- `project_id`
- `started_at`
- `finished_at`
- `run_type`: `understanding | digest | deep | loop | resume_refresh`
- `question`
- `status`: `running | completed | failed | cancelled`
- `input_snapshot_id`
- `output_snapshot_id`
- `outputs`
- `summary`
- `error`

## What Exactly Represents “Project State”

This must be explicit because it was previously underspecified.

**Project state is not one file.** It is composed of:

1. `project.json`
   - stable identity and configuration
2. `state.json`
   - mutable HEAD pointers and status
3. current `blackboard.json`
   - active reasoning state for research/review loop
4. latest `ProjectSnapshot`
   - immutable checkpoint of the last important moment
5. project-local `knowledge.db`
   - project memory and structured findings

That combination is the project state model.

## Snapshot Hierarchy

The system should distinguish three levels of historical memory:

### 1. Source Snapshot

Captures the code / source tree state.

Tool:

- `git commit`
- `git diff`
- `git worktree`

### 2. Understanding Snapshot

Captures the system’s structured understanding of the source.

Tool:

- deterministic extraction plus agent synthesis

### 3. Project Snapshot

Captures the full research checkpoint that binds source + understanding + blackboard + outputs.

Tool:

- JSON snapshot metadata plus referenced files

This three-layer model is important. It avoids confusing “what the code was,” “what the system understood,” and “where the research process stood.”

## Recommended On-Disk Layout

Revise the previous layout so snapshots are first-class and self-contained.

```text
data/
  projects/
    <project_slug>/
      project.json
      state.json
      blackboard.json
      knowledge.db
      runs/
        <run_id>.json
      snapshots/
        <snapshot_id>/
          snapshot.json
          source.json
          understanding.json
          blackboard.json
          artifacts/
          patches/
            tracked.diff
            untracked_manifest.json
            untracked/
      reports/
      notes/
      cache/
```

Keep a top-level registry:

```text
data/projects/index.json
```

## Formal Resume Protocol

This is the exact behavior that should be implemented.

### Resume Mode A: `current_workspace`

Default for local codebase work.

Behavior:

1. load project manifest and current state
2. inspect the currently bound source directory
3. capture a fresh `SourceSnapshot`
4. compare against the source snapshot referenced by `current_snapshot_id`
5. generate a refreshed `UnderstandingSnapshot`
6. create a new `ProjectSnapshot` of kind `resume`
7. continue research from that new head

This mode never auto-checks out a different commit.

### Resume Mode B: `exact_snapshot`

Used when the user wants exact historical continuation.

Behavior:

1. select a `ProjectSnapshot`
2. resolve its `SourceSnapshot`
3. if git-backed, create a `git worktree` at the stored commit
4. if the source snapshot had a stored dirty patch, apply it in the isolated worktree
5. read and understand from that isolated workspace
6. either continue there or return a refreshed understanding before the next step

This mode is the safest path for reproducible replay.

### Resume Mode C: `milestone`

Used for named important checkpoints.

Behavior:

- resolve the milestone tag or milestone snapshot id
- follow the same flow as `exact_snapshot`

## Dirty Workspace Handling

This deserves explicit policy because it is one of the easiest places to get the design wrong.

### Default policy

- allow dirty workspace capture
- do not force commit
- preserve tracked diff and untracked file manifest in snapshot storage

### Optional strict mode

For some projects, we may later support:

- require clean git state before exact snapshot resume

But this should not be the default for the first implementation because real development projects often have uncommitted state.

### Safety rule

The system must never run destructive git commands such as:

- hard reset
- forced checkout over local changes
- branch rewrites

without explicit user approval.

## What Should Be Deterministic Services vs LLM Agents

This is one of the most important architectural boundaries.

## Deterministic Services

These should be implemented as ordinary Python services, not prompt-driven agents:

- project registry
- project loading and path resolution
- git inspection
- source snapshot capture
- patch and untracked file capture
- snapshot persistence
- state transitions
- resume mode selection
- worktree creation and cleanup
- blackboard file IO

These are lifecycle primitives and must be fully inspectable and testable.

## LLM Agents

These should do interpretation and critique:

- understanding agent
- research agent
- review agent
- meta-reviewer

Agents should consume structured lifecycle context, not invent it.

## Multi-Agent Runtime Design

The revised runtime should use a multi-agent architecture with deterministic lifecycle services around it.

### 1. Project Orchestrator

Type:

- deterministic coordinator service

Responsibilities:

- create project
- load project
- choose resume mode
- call source capture service
- call understanding agent
- call research/review/meta-review pipeline
- persist snapshots and state transitions

This is the new outer orchestrator above the current research/review loop.

### 2. Source Snapshot Service

Type:

- deterministic service

Responsibilities:

- inspect git repo state
- capture commit / branch / dirty info
- store patch data when needed
- compute source fingerprint

This service is responsible for using `git` correctly and safely.

### 3. Understanding Agent

Type:

- LLM agent

Responsibilities:

- read important files and prior outputs
- produce structured `UnderstandingSnapshot`
- explain what changed since the last understanding snapshot
- identify open questions and likely next steps

This agent is mandatory on create and resume for `codebase` and `hybrid` projects.

### 4. Research Agent

Type:

- LLM agent

Responsibilities:

- continue investigation using project context
- produce artifacts and structured outputs
- update blackboard through orchestrator-owned persistence

This is the existing `ResearchAgent`, but it now receives explicit project context.

### 5. Review Agent

Type:

- LLM agent

Responsibilities:

- critique research artifacts in context of project goals and current stage

### 6. Meta-Reviewer

Type:

- LLM + programmatic checker

Responsibilities:

- validate review quality
- prevent low-quality or collapsed review behavior

## Multi-Agent Lifecycle Flows

## A. Create New Project

1. `Project Orchestrator`
   - validates source paths and project metadata
2. `Source Snapshot Service`
   - captures initial source state
3. `Understanding Agent`
   - produces the first understanding snapshot
4. `Project Orchestrator`
   - writes blackboard, snapshot, and state
5. `Research Agent`
   - begins the first research run only after understanding is persisted

## B. Resume Existing Project

1. `Project Orchestrator`
   - loads project state and selected snapshot
2. `Source Snapshot Service`
   - captures current source state and computes delta
3. `Understanding Agent`
   - refreshes understanding in light of the source delta and prior outputs
4. `Project Orchestrator`
   - records a resume snapshot
5. `Research Agent`
   - continues research from the refreshed understanding
6. `Review Agent`
   - critiques any new artifact
7. `Meta-Reviewer`
   - validates review quality
8. `Project Orchestrator`
   - persists post-run snapshot and advances state

## Concrete Module Revision Plan

The following additions are recommended.

### New model modules

- `src/alpha_research/models/project.py`
- `src/alpha_research/models/snapshot.py`

### New lifecycle modules

- `src/alpha_research/projects/registry.py`
- `src/alpha_research/projects/service.py`
- `src/alpha_research/projects/git_state.py`
- `src/alpha_research/projects/snapshots.py`
- `src/alpha_research/projects/resume.py`
- `src/alpha_research/projects/understanding.py`

### Existing modules to revise

- `src/alpha_research/main.py`
- `src/alpha_research/api/models.py`
- `src/alpha_research/api/routers/agent.py`
- `src/alpha_research/api/routers/papers.py`
- `src/alpha_research/api/routers/evaluations.py`
- `src/alpha_research/api/routers/graph.py`
- `src/alpha_research/agents/orchestrator.py`
- `src/alpha_research/agents/research_agent.py`

## CLI Revision Plan

Current CLI should become explicitly project-aware and git-aware.

### New commands

- `alpha-research project create <name> --type codebase --source-path <path> --question <...>`
- `alpha-research project list`
- `alpha-research project show <project_id>`
- `alpha-research project status <project_id>`
- `alpha-research project snapshot <project_id> [--kind manual] [--milestone]`
- `alpha-research project resume <project_id> [--mode current_workspace|exact_snapshot|milestone] [--snapshot <id>]`

### Revised commands

- `alpha-research research --project <project_id> ...`
- `alpha-research loop --project <project_id> ...`
- `alpha-research status --project <project_id>`

### CLI design rules

- no implicit singleton project
- no destructive git operations without approval
- resume mode must be explicit or have a safe default

## API Revision Plan

Add project-aware endpoints:

- `POST /api/projects`
- `GET /api/projects`
- `GET /api/projects/{project_id}`
- `GET /api/projects/{project_id}/state`
- `GET /api/projects/{project_id}/snapshots`
- `POST /api/projects/{project_id}/snapshots`
- `POST /api/projects/{project_id}/resume`
- `GET /api/projects/{project_id}/runs`

Then thread `project_id` through agent, paper, evaluation, and graph endpoints.

The current frontend/backend contract mismatches should be resolved before or during this work, not after it.

## Frontend Revision Plan

The frontend needs to expose project lifecycle explicitly.

### Required views

- project list
- create project dialog
- project overview
- snapshot history
- resume dialog with mode selection
- latest understanding snapshot
- recent run history

### Required UX for resume

Before continuing, show:

- target source branch and commit
- whether the workspace is dirty
- what changed since the last snapshot
- the last understanding summary
- which resume mode will be used

Resume should feel transparent and inspectable.

## Testing Plan

These behaviors should be formalized in tests before broad rollout.

### Model tests

- manifest roundtrip
- state roundtrip
- snapshot immutability expectations

### Git snapshot tests

- clean repo snapshot capture
- dirty repo snapshot capture
- untracked file manifest capture
- exact snapshot resume via worktree

### Lifecycle tests

- create new project
- create first snapshot
- resume current workspace
- resume exact snapshot
- multi-project isolation

### Agent integration tests

- understanding snapshot creation on project create
- understanding refresh on resume
- research loop consumes latest project context

## Recommended Phased Implementation

### Phase 0: Formalize schemas and invariants

Implement first:

- `ProjectManifest`
- `ProjectState`
- `SourceSnapshot`
- `UnderstandingSnapshot`
- `ProjectSnapshot`
- `ResearchRun`

Deliverable:

- the data model and lifecycle rules are explicit and testable

### Phase 1: Build deterministic project services

Implement:

- registry
- project service
- git state capture
- snapshot writer
- resume service

Deliverable:

- project create, snapshot, and resume exist without full agent integration

### Phase 2: Add git-backed checkpointing

Implement:

- commit / branch capture
- dirty patch capture
- milestone tagging
- exact snapshot resume via `git worktree`

Deliverable:

- source checkpoints are formal and reproducible

### Phase 3: Add understanding agent lifecycle

Implement:

- understanding snapshot generator
- diff-aware re-understanding on resume
- project overview summary artifact

Deliverable:

- every create and resume operation produces refreshed understanding

### Phase 4: Bind research/review loop to project lifecycle

Implement:

- project-aware outer orchestrator
- project context injection into research agent
- snapshot creation pre-run and post-run

Deliverable:

- research happens inside projects rather than as global singleton sessions

### Phase 5: Expose lifecycle through CLI/API/frontend

Implement:

- CLI project commands
- API project routes
- frontend project list / snapshot / resume flows

Deliverable:

- complete user-facing project lifecycle

### Phase 6: Make `alpha_robot` the first real project instance

Implement:

- create `alpha_robot` as a `codebase` or `hybrid` project
- capture initial git-backed source snapshot
- generate first understanding snapshot
- test resume after meaningful source changes

Deliverable:

- `alpha_robot` becomes the first validated project instance of `alpha_research`

## Specific Guidance For `alpha_robot`

`alpha_robot` should be the first project that exercises the full design.

For `alpha_robot`, formally capture:

- repo root
- tracked branch
- head commit
- key training entrypoints
- dataset pipeline
- evaluation flow
- uncertainty modules
- experiment/config surfaces
- known open questions

Recommended initial adapter:

- `codebase` if the primary task is source understanding and implementation tracking
- `hybrid` if literature synthesis and code understanding are both first-class

Recommended initial resume default:

- `current_workspace`

Recommended exact historical replay tool:

- `git worktree`

## Final Recommendation

The next implementation should not begin with more prompt engineering. It should begin by formally defining and implementing:

1. project identity
2. project state
3. source snapshots
4. project snapshots
5. resume modes
6. git-backed checkpoint capture

Then the multi-agent runtime should be layered on top of that deterministic lifecycle foundation.

The most important design choice is this:

**Use `git` as the source-state backbone, but do not mistake `git` for the entirety of project state.**

The project needs both:

- a reproducible source checkpoint system
- a structured research-state system

That is the correct foundation for create, snapshot, and resume behavior in `alpha_research`, and it is the right way to make `alpha_robot` the first serious project instance.
