# Implementation Plan — The Integrated Research State Machine

**Status:** active. Supersedes the "Implementation Plan" sections of
[`research_plan.md`](./research_plan.md) and the phased plan in
[`../history/refactor_plan.md`](../history/refactor_plan.md). Those documents
remain authoritative for the state machine theory (research_plan) and the
already-completed skills-first refactor (refactor_plan), but this is now the
live plan for what we build next.

**One-sentence goal:** make the two-layer state machine in
[`research_plan.md`](./research_plan.md) actually *run* — with human-owned
artifacts as state, skills and CLI verbs as transitions, and source code +
experiments as first-class citizens of the loop — while keeping the system
compact enough that a single researcher can hold it in their head.

---

## Part I. Mental Model

### I.1 Artifacts are the state; skills and verbs are the transitions

The existing code treats the state machine as *theory* — `pipelines/state_machine.py`
has pure functions for `g1..g5` and `t2..t15`, but nothing consults them at
runtime and nothing persists "which stage am I in." This plan makes the
state machine executable by binding it to **files on disk**:

```
                      state.json (current stage + history)
                             ▲
                             │ reads/writes
                             │
  ┌──────────┐   invokes   ┌─┴────────────┐   writes   ┌──────────────┐
  │ human    │────────────▶│  CLI verbs   │───────────▶│ artifacts    │
  │ (author) │             │  / pipelines │            │ (md + jsonl) │
  └──────────┘             │  / skills    │            └──────────────┘
      ▲                    └──────────────┘                    │
      │                            │                            │
      │   reads                    │ invokes                    │ read by
      │                            ▼                            │
      │                     ┌──────────────┐                    │
      └─────────────────────│ skills       │◀───────────────────┘
                            │ (SKILL.md)   │
                            └──────────────┘
```

A project's full state at any instant = the contents of its directory on
disk. The CLI and skills are deterministic transformations over that state.
The human is always the outermost controller — the agent never advances
stages on its own.

### I.2 What changes relative to today

- **Today**: the system evaluates papers and reviews drafts. Everything is
  literature-side.
- **After this plan**: the system sits alongside the researcher's actual
  lab — reads their method code, reads their experiment results, walks
  them through diagnose / challenge / approach / validate with persistent
  stage tracking and a provenance log that lets them answer "why did I run
  this experiment?" three weeks later.

We do **not** build a simulation platform, training framework, data
collection pipeline, or experiment launcher. The researcher already has
those. We build interfaces.

### I.3 The six stages in one picture

```
               ┌────────────────────────┐
               │ hamming.md ↺ (monthly) │
               └─────────┬──────────────┘
                         │
                         ▼
   ┌──────────────┐ g1  ┌───────────┐ g2  ┌──────────┐ g3  ┌───────────┐
   │ SIGNIFICANCE ├────▶│ FORMALIZE ├────▶│ DIAGNOSE ├────▶│ CHALLENGE │
   └──────▲───────┘     └─────▲─────┘     └─────▲────┘     └────┬──────┘
          │                   │                 │               │
          │ t2,t5,t9,t13      │ t4,t7,t10,t14  │t6,t8,t11,t15 │ g4
          │                   │                 │               ▼
          │                   │                 │          ┌──────────┐
          │                   │                 │   t12    │ APPROACH │
          │                   │                 │◀─────────┤          │
          │                   │                 │          └────┬─────┘
          │                   │                 │               │ g5
          │                   │                 │               ▼
          │                   │                 │          ┌──────────┐
          └───────────────────┴─────────────────┴──────────┤ VALIDATE │
                                                           └────┬─────┘
                                                                │
                                                                ▼
                                                           ┌──────────┐
                                                           │  DONE    │
                                                           └──────────┘
```

Forward arrows: forward guards (`g1..g5`) from [`research_plan.md`](./research_plan.md) §1.
Backward arrows: triggers (`t2..t15`) from [`research_plan.md`](./research_plan.md) §1.
All of these are already pure functions in
`src/alpha_research/pipelines/state_machine.py`. Phase 1 wires them to state.json.

---

## Part II. Project Layout (filesystem as state)

### II.1 A project is a directory

```
output/<project>/
  project.md                   # question, scope, why-now (HUMAN)
  hamming.md                   # researcher's running list of important problems (HUMAN, updated monthly)
  formalization.md             # the problem as math (HUMAN-drafted; agent reviews)
  benchmarks.md                # chosen benchmarks + baselines to reproduce (HUMAN, agent-proposed)
  one_sentence.md              # the evolving contribution statement (HUMAN)
  log.md                       # weekly research log (HUMAN, append-only)
  source.md                    # what the agent learned from reading the code (AGENT-written)
  state.json                   # current stage + history + guard status + open triggers (CLI-managed)
  provenance.jsonl             # append-only lineage of every action (CLI / skill / pipeline)

  # JSONL record streams (agent-written, one record per invocation)
  evaluations.jsonl            # per-paper rubric scores (paper-evaluate skill)
  significance_screens.jsonl   # significance-screen skill outputs
  formalization_checks.jsonl   # formalization-check skill outputs
  benchmark_surveys.jsonl      # benchmark-survey skill outputs (one per survey run)
  diagnoses.jsonl              # diagnose-system skill outputs
  challenges.jsonl             # challenge-articulate skill outputs
  method_surveys.jsonl         # method_survey pipeline + identify-method-gaps skill outputs
  concurrent_work.jsonl        # concurrent-work-check skill outputs
  experiment_designs.jsonl     # experiment-design skill outputs (one per proposed experiment)
  experiment_analyses.jsonl    # experiment-analyze skill outputs (one per completed experiment)
  findings.jsonl               # structured findings (from experiment analyses, diagnoses, reviews)
  reviews.jsonl                # adversarial-review skill outputs
  frontier.jsonl               # frontier_mapping pipeline snapshots
  gap_reports.jsonl            # gap-analysis skill outputs

  # Optional — the researcher's actual method code is elsewhere
  (code_dir is an absolute path in state.json, not a subdirectory)
```

**Principle**: a project is its directory. `tar czf project.tgz output/<project>/`
is a complete backup. No registry, no SQLite except the alpha_review paper
store (which is global and not per-project), no snapshots unless the
researcher runs git in the directory themselves.

### II.2 `state.json` schema

```python
@dataclass
class ProjectState:
    project_id: str                          # = directory basename
    created_at: str                          # ISO 8601
    current_stage: ResearchStage             # enum from models.blackboard
    stage_entered_at: str                    # ISO 8601
    stage_history: list[StageTransition]     # append-only
    open_triggers: list[OpenTrigger]         # backward triggers proposed but not resolved
    forward_guard_status: dict[str, GuardCheck]  # per-guard last check
    code_dir: str | None                     # absolute path to the researcher's method code
    target_venue: str                        # default "RSS"
    notes: str                               # free-form researcher notes

@dataclass
class StageTransition:
    from_stage: ResearchStage | None         # None for initial state
    to_stage: ResearchStage
    at: str                                  # ISO 8601
    trigger: str | None                      # "g1".."g5" or "t2".."t15" or "init"
    note: str                                # one-line human note
    carried_constraint: str | None           # for backward transitions, what we learned
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

### II.3 `provenance.jsonl` schema

```python
@dataclass
class ProvenanceRecord:
    id: str                                  # uuid
    created_at: str
    action_type: str                         # "skill"|"pipeline"|"cli"|"human"|"transition"
    action_name: str                         # e.g. "significance-screen", "project advance"
    project_stage: ResearchStage             # stage at time of action
    inputs: list[str]                        # artifact refs read (paths or record ids)
    outputs: list[str]                       # artifact refs written
    parent_ids: list[str]                    # prior provenance ids this action built on
    summary: str                             # one-line human description
```

Every CLI verb, every skill invocation, and every pipeline run appends
one record. This is the single source of truth for "what happened and in
what order." `alpha-research provenance` reads and renders this.

---

## Part III. Per-Stage Specifications

Each stage is specified as: **entry condition, inputs, actions, outputs,
forward guard, backward triggers**. This is the contract each stage must
satisfy; the CLI and skills enforce it.

### III.1 SIGNIFICANCE

> *"Is this problem worth working on?"*

**Entry**: project init, or backward from `t5 / t9 / t13`.
On backward entry, `carried_constraint` records *why* the previous attempt
failed downstream — the new search must not pick a problem with the same
structural deficiency.

**Human inputs**:
- `hamming.md` — the researcher's running list of 10–20 important unsolved problems (updated monthly; **the agent cannot produce this**).
- `project.md` — candidate question, concrete task, why-now guess.

**Agent skills / pipelines** (all stage-bound to SIGNIFICANCE):
- `literature-survey` pipeline — breadth-first scan of the candidate area; produces `evaluations.jsonl`, `gap_reports.jsonl`.
- `significance-screen` skill — applies Hamming/Consequence/Durability/Compounding tests to the current `project.md` problem; reads `hamming.md` for the researcher's filter. Writes `significance_screens.jsonl`.
- `frontier-mapping` pipeline — produces `frontier.jsonl` snapshot of reliable/sometimes/can't-yet.
- `gap-analysis` skill — surfaces recurring limitations across surveyed papers.
- `paper-evaluate` skill — on demand, for a specific interesting paper.

**Outputs**:
- `significance_screens.jsonl`, `frontier.jsonl`, `gap_reports.jsonl`, `evaluations.jsonl`
- `provenance.jsonl` (one record per invocation)
- Human updates: `project.md` (final problem statement), `hamming.md` (refinement)

**Forward guard g1** (`stage_guard_satisfied(SIGNIFICANCE, ...)`): ALL of
1. At least one `significance_screen` record exists in this stage with the current `project.md` version.
2. The record has at least one concrete `consequence: str` (non-null, not vague).
3. `durability_risk != "high"`.
4. A human has explicitly confirmed the Hamming test in the latest record (`human_confirmed: true`). This is non-automatable — the guard *requires* the human-in-the-loop confirmation.

**Backward triggers detected in later stages that send us BACK to SIGNIFICANCE**:
- `t2` (from FORMALIZE): problem is a trivial special case of a solved problem.
- `t5` (from APPROACH): the implemented method is a minor variant of prior work.
- `t9` (from APPROACH): concurrent work solved this.
- `t13` (from VALIDATE): contribution is incremental; one-sentence test fails.

### III.2 FORMALIZE

> *"Can I write the problem as math, and on what do I measure it?"*

**Entry**: from SIGNIFICANCE via `g1`, or backward from `t2 / t7 / t10 / t14`.

FORMALIZE has two tightly-coupled concerns: **the math** (what the problem
IS) and **the benchmark** (how we will measure progress on it). A benchmark
choice is itself a formalization decision — it pins down the observation
space, action space, success criterion, and evaluation distribution. You
cannot enter DIAGNOSE without both.

**Human inputs**:
- `project.md` (finalized problem)
- `formalization.md` — the problem as an optimization / estimation / decision problem with explicit objective, variables, constraints, information structure. The researcher writes this; the skill reviews it.
- `benchmarks.md` — the researcher's selection of which standard benchmark(s) this work will measure progress on, with rationale. The researcher writes this; the `benchmark-survey` skill produces a ranked proposal they work from.

**Agent skills**:
- `formalization-check` skill — reads `formalization.md`, detects formalization level (`formal_math` / `semi_formal` / `prose_only` / `absent`), detects framework mismatches, identifies claimed structure, invokes `scripts/sympy_verify.py` to check claimed properties (convexity, continuity, etc.). Writes `formalization_checks.jsonl`.
- `method_survey` pipeline — searches literature for similar formalizations to check for trivial special-case reduction.
- `benchmark-survey` skill **(new)** — reads `project.md` + `formalization.md`, surveys literature for benchmarks covering the problem class, extracts per-benchmark metadata (task scope, standard metrics, success criterion, published baseline numbers and trends, saturation risk, install pointer), ranks them by coverage of the formalization's core challenge, flags saturated or misaligned ones, and produces a ranked proposal the human uses to write `benchmarks.md`. Writes `benchmark_surveys.jsonl`.

**Outputs**:
- `formalization_checks.jsonl`, `benchmark_surveys.jsonl`, `method_surveys.jsonl` (when invoked)
- Human updates: `formalization.md` (iterated), `benchmarks.md` (written after reading the survey proposal)

**Forward guard g2** (`stage_guard_satisfied(FORMALIZE, ...)`):
1. `formalization.md` exists and is non-empty.
2. Latest `formalization_check` record has `formalization_level ∈ {formal_math, semi_formal}`.
3. At least one `structure_exploited` entry is non-null.
4. sympy verification of any claimed structural property passed (or is explicitly flagged as unverifiable).
5. **`benchmarks.md` exists and lists at least one chosen benchmark under "In scope" with: a rationale, a success criterion, at least one published baseline with its number, and a saturation assessment.**
6. **The latest `benchmark_survey` record has been reviewed (`human_confirmed: true`) — the agent surfaces candidates, the human picks.**

**Backward triggers detected here → fire OUT**:
- `t2` → back to SIGNIFICANCE (`formalization_check.reduces_to_known` non-null, OR `benchmark_survey` reveals the chosen task is already saturated on the standard benchmark to the point where meaningful improvement is noise).

**Backward triggers from downstream that send us BACK to FORMALIZE**:
- `t4` (from DIAGNOSE): empirical failures don't map to any formal term.
- `t7` (from CHALLENGE): challenge lives outside the formal frame (including: the chosen benchmark's observation space cannot express the challenge).
- `t10` (from APPROACH): structural assumptions are wrong.
- `t14` (from VALIDATE): can't formally state what was solved.

### III.3 DIAGNOSE

> *"What actually fails when I run a minimal end-to-end system?"*

**This is the stage the current system has zero coverage of.** It requires
the researcher's actual method code, a set-up benchmark from `benchmarks.md`,
and experiment results.

**Entry**: from FORMALIZE via `g2`, or backward from `t6 / t8 / t11 / t15`.

**Pre-entry requirement**: `state.code_dir` must be set, pointing at the
researcher's method repo. If `source.md` is stale, run `project-understanding`
first.

**Stage sub-ordering**. DIAGNOSE has three sub-phases the guards enforce:

1. **Setup** — install the benchmark(s) from `benchmarks.md`, wire them to
   `code_dir`, record the install recipe under `<code_dir>/experiments/<benchmark_id>_setup.md`.
2. **Reproduce** — run at least one reproduction experiment per chosen
   benchmark: execute a published baseline (or a scripted baseline from
   the benchmark's own defaults) and verify the measured number is within
   tolerance of the published number recorded in `benchmarks.md`. This is
   the reproducibility floor — if you can't hit a known-good number, your
   measurement infrastructure is broken and any subsequent failure
   observations are noise.
3. **Diagnose** — run the minimal system and observe failures; map each
   failure to a specific term/assumption in `formalization.md`.

**Human inputs**:
- The method code (in `code_dir`) — a minimal end-to-end system that can produce failures.
- `experiments/<exp_id>/` directories following the convention in Part V — at minimum `config.yaml`, `results.jsonl`, and `notes.md`. Reproduction experiments MUST include `reproduction_of: <paper_ref>` in their `config.yaml`.
- `log.md` — weekly log of what was tried / expected / observed / concluded.

**Agent skills**:
- `project-understanding` skill (**NEW**) — reads `code_dir`, produces/updates `source.md`: where the method lives, entry points, config files, training loop, eval harness, and how the benchmark(s) from `benchmarks.md` are wired in. On-demand, not automatic.
- `experiment-design` skill (**NEW**, reproduction mode) — given a benchmark from `benchmarks.md`, produces a reproduction experiment config that matches the published baseline's setup as closely as possible and targets the published number.
- `experiment-analyze` skill (**NEW**) — reads `experiments/<exp_id>/`, runs `scripts/audit_stats.py`, checks hypotheses against outcomes. In reproduction mode, it compares the measured aggregate metric against the `published_number` recorded in `benchmarks.md` and emits `reproducibility: pass | partial | fail` in the record. Outside reproduction mode, proposes backward triggers if appropriate. Writes `experiment_analyses.jsonl` and `findings.jsonl`.
- `diagnose-system` skill — reads `source.md` + `formalization.md` + latest non-reproduction `experiments/<exp_id>/results.jsonl` + `notes.md`, maps each observed failure to a specific term or assumption in the formalization. Writes `diagnoses.jsonl`.

**Outputs**:
- `source.md` (agent-written), `diagnoses.jsonl`, `experiment_analyses.jsonl`, `findings.jsonl`
- Per-experiment: `<code_dir>/experiments/<exp_id>/` with `config.yaml`, `results.jsonl`, `notes.md`
- Human updates: `log.md`, per-experiment `notes.md`, `benchmarks.md` (annotating reproducibility status)

**Forward guard g3** (`stage_guard_satisfied(DIAGNOSE, ...)`):
1. **For every benchmark listed in `benchmarks.md` under "In scope", at least one `experiment_analysis` record exists with `reproduction_of` set and `reproducibility ∈ {pass, partial}`** — the measurement infrastructure is trusted.
2. At least one `diagnosis` record with `failure_mapped_to_formal_term: str` non-null — the observed failure points to a specific variable, constraint, or assumption in `formalization.md`.
3. The mapped failure references a non-stale `experiments/<exp_id>/` — code, results, and `source.md` are aligned.

**Backward triggers detected here → fire OUT**:
- `t4` → back to FORMALIZE (no failure maps to any formal term, OR the reproduction fails in a way that reveals a formal mismatch — e.g., the benchmark's success criterion isn't expressible in your formalization's objective).
- `t7` → back to FORMALIZE (reproduction reveals the benchmark's observation space can't express your formalization's decision variables — you chose the wrong benchmark for this formalization).

**Backward triggers from downstream that send us BACK to DIAGNOSE**:
- `t6` (from CHALLENGE): challenge hypothesis contradicted by evidence.
- `t8` (from APPROACH): the approach exposes new failure modes.
- `t11` (from APPROACH): approach doesn't work, can't tell why.
- `t15` (from VALIDATE): ablation shows wrong mechanism.

### III.4 CHALLENGE

> *"What is the structural barrier that resists existing solutions?"*

**Entry**: from DIAGNOSE via `g3`, or backward from `t12`.

**Human inputs**:
- `diagnoses.jsonl` (the current diagnosis)
- `formalization.md`
- Researcher's taste (the step the agent cannot do)

**Agent skills**:
- `challenge-articulate` skill — reads the latest diagnosis + formalization, tests structural-vs-resource, tests solution-narrowing, looks up analogous challenges in literature. Writes `challenges.jsonl`.
- `concurrent-work-check` skill — checks whether this specific structural barrier has already been addressed.
- `method_survey` pipeline — given a proposed challenge, surveys which method class it implies.

**Outputs**:
- `challenges.jsonl`, `concurrent_work.jsonl`, `method_surveys.jsonl`
- Human updates: none directly — the challenge is an artifact record, not a standalone markdown file

**Forward guard g4** (`stage_guard_satisfied(CHALLENGE, ...)`):
1. Latest `challenge` record has `challenge_type == "structural"` (not `"resource_complaint"`).
2. `implied_method_class: str` is non-null.
3. The challenge passes the "predict the method class" test: the record includes a statement of which method class someone reading only the challenge would infer.
4. No unresolved `t12` in `open_triggers` (if the last APPROACH attempt fired t12, the new challenge must address it).

**Backward triggers detected here → fire OUT**:
- `t6` → back to DIAGNOSE (evidence contradicts challenge).
- `t7` → back to FORMALIZE (barrier lives outside formal frame).

**Backward triggers from downstream → back to CHALLENGE**:
- `t12` (from APPROACH): no method in the implied class works.

### III.5 APPROACH

> *"What is the method that follows from the challenge?"*

**Entry**: from CHALLENGE via `g4`.

**Human inputs**:
- Method code implementation in `code_dir` (iterated)
- `one_sentence.md` — draft contribution statement

**Agent skills**:
- `method_survey` pipeline — exhaustive survey of the implied method class.
- `identify-method-gaps` skill — what hasn't been tried in the class?
- `concurrent-work-check` skill — ongoing scoop detection.
- `experiment-design` skill (**NEW**) — reads formalization + challenge + current approach description; produces an `experiments/<exp_id>/config.yaml` proposing: hypothesis in formal terms, treatment/control/ablation conditions, required baselines (per doctrine §8.2), trial counts per venue (per review_plan §1.6), metrics, pre-registered failure modes to watch. Writes `experiment_designs.jsonl`. **Does not launch** the experiment.
- `project-understanding` skill — re-reads `code_dir` after code changes; updates `source.md`.
- `formalization-check` skill — re-run to detect formalization↔implementation drift.
- `paper-evaluate` skill — for specific comparison papers.

**Outputs**:
- `method_surveys.jsonl`, `experiment_designs.jsonl`, `source.md`, `concurrent_work.jsonl`
- Human updates: method code (external), `one_sentence.md`, `log.md`

**Forward guard g5** (`stage_guard_satisfied(APPROACH, ...)` for APPROACH→VALIDATE):
1. `one_sentence.md` exists and states a structural insight (not "SOTA on X"). The `formalization-check` skill's "one_sentence_test" metric must be `"insight"`, not `"performance_claim"` or `"absent"`.
2. At least one `experiment_design` record exists for this approach.
3. Latest `formalization-check` re-run shows `formal_impl_gap: "none"` or `"minor"` — the code matches the math.
4. No unresolved backward triggers in `open_triggers`.

**Backward triggers detected here → fire OUT**:
- `t5` → back to SIGNIFICANCE (trivial variant of prior work).
- `t8` → back to DIAGNOSE (new failure modes exposed).
- `t9` → back to SIGNIFICANCE (concurrent work scoops).
- `t10` → back to FORMALIZE (structural assumptions wrong).
- `t11` → back to DIAGNOSE (approach doesn't work, can't tell why).
- `t12` → back to CHALLENGE (no method in class works).

### III.6 VALIDATE

> *"Does the evidence support a claim worth publishing?"*

**Entry**: from APPROACH via `g5`.

**Human inputs**:
- Completed `experiments/<exp_id>/` directories with `results.jsonl`
- Draft write-up (markdown) — typically `report.md` in the project directory or in `code_dir/writeups/`
- `one_sentence.md` (final)

**Agent skills**:
- `experiment-analyze` skill — reads each completed experiment, audits statistics, checks baseline completeness, checks ablation isolation.
- `experiment-audit` skill — applies venue thresholds from `review_plan.md §1.6` to the results.
- `adversarial-review` skill — reviews the draft write-up. Three-pass protocol, full attack vectors, venue-calibrated. Writes `reviews.jsonl`.
- `research_review_loop` pipeline — drives adversarial convergence: review → human revision → re-review, up to `max_iterations` from `review_config.yaml`, with graduated pressure and meta-review quality checks.
- `classify-capability` skill — places the demonstrated capability on the frontier.
- `concurrent-work-check` skill — final check before submission.

**Outputs**:
- `experiment_analyses.jsonl`, `findings.jsonl`, `reviews.jsonl`, updated `frontier.jsonl`
- Human updates: `report.md` draft (iterated), `one_sentence.md` (final)

**Exit condition → DONE**:
1. Most recent `review` record has `verdict ∈ {ACCEPT, WEAK_ACCEPT}`.
2. No `fatal` findings in the latest review.
3. ≤1 `serious` finding, and it is `fixable: true`.
4. `one-sentence test` passes (record includes an insight, not a performance claim).
5. All ablations isolate the claimed contribution.
6. Human has given explicit final approval.

**Backward triggers detected here → fire OUT**:
- `t13` → back to SIGNIFICANCE (contribution incremental; one-sentence test fails).
- `t14` → back to FORMALIZE (can't formally state what was solved).
- `t15` → back to DIAGNOSE (ablation shows wrong mechanism).

---

## Part IV. CLI Verbs — The State Machine's I/O Surface

The CLI is the only way the state machine transitions. Skills and pipelines
are invoked via the CLI or via Claude Code directly; in both cases they
write to the project directory through the shared record helpers.

```
# ─── Project lifecycle ────────────────────────────────────────────────

alpha-research project init <name>
    [--code <absolute_path>]
    [--question "..."]
    [--venue RSS|CoRL|IJRR|T-RO|RA-L|ICRA|IROS]
    [-o <parent_dir>]             # default: output/
    # Creates output/<name>/ with templates: project.md, hamming.md,
    # formalization.md, benchmarks.md, one_sentence.md, log.md,
    # state.json (stage=SIGNIFICANCE), empty JSONL files,
    # empty provenance.jsonl.

alpha-research project stage [<project_dir>]
    # Shows: current stage, entered when, forward guard status
    # (pass/fail per condition), next recommended skill, open backward
    # triggers, last 5 stage transitions.

alpha-research project advance [<project_dir>] [--force] [--note "..."]
    # Runs the current stage's forward guard check. If it passes, transitions
    # forward and records the transition in state.json + provenance.jsonl.
    # If not, prints which conditions failed and exits non-zero.
    # --force allows override with mandatory --note explaining why.

alpha-research project backward <trigger> [<project_dir>]
    [--evidence <record_id>] [--note "..."]
    # <trigger> is one of t2..t15.
    # Executes a backward transition: updates current_stage, appends to
    # stage_history with the trigger + carried_constraint, marks the
    # open_trigger as resolved (or creates a new one).
    # The carried constraint is mandatory — what did we learn? This is the
    # constraint the re-entered stage carries.

alpha-research project log [<project_dir>]
    # Opens $EDITOR on log.md with a weekly template appended.
    # Template:
    #   ## Week of 2026-04-14
    #   - Tried:
    #   - Expected:
    #   - Observed:
    #   - Concluded:
    #   - Next:

alpha-research project status [<project_dir>]
    # One-screen summary: stage, days in stage, key artifact counts,
    # last finding, last review verdict, open triggers.

# ─── Stage-bound actions ──────────────────────────────────────────────

alpha-research observe <exp_id> [<project_dir>]
    # Opens $EDITOR on a failure-note template, saves it as
    # experiments/<exp_id>/notes.md, appends a structured record to
    # findings.jsonl, prompts "invoke diagnose-system now? [y/N]".

alpha-research calibrate <project_dir> --papers <id1,id2,...>
    # Takes N paper ids the human has manually scored (stored in
    # calibration/human_scores.jsonl under the project), runs paper-evaluate
    # on each, prints a per-dimension diff table. Monthly ritual.

alpha-research provenance [<project_dir>]
    [--since <stage>] [--action <type>] [--limit N]
    # Prints the provenance tree. Each record shows its parent_ids, so
    # you can trace "why did we run this experiment?" back to the
    # formalization version that motivated it.

alpha-research skill <skill_name> [--project <dir>] [args...]
    # Invoke a skill. Checks the skill's research_stages frontmatter
    # against the project's current stage and warns (not errors) if
    # out-of-stage. Logs to provenance.jsonl.

# ─── Pipeline wrappers (already exist; become stage-aware) ────────────

alpha-research survey <query> [-o <project_dir>]         # SIGNIFICANCE only
alpha-research evaluate <paper_id> [-o <project_dir>]    # SIGNIFICANCE|APPROACH
alpha-research review <draft.md> [-o <project_dir>]      # VALIDATE only
alpha-research significance <problem> [-o <project_dir>] # SIGNIFICANCE only
alpha-research loop <project_dir>                        # VALIDATE only
```

**Guard semantics**: `project advance` NEVER transitions without the guard
passing, except with `--force + --note`. The `--force` path records an
`override_reason` field in the stage transition — the cheating is visible
in provenance.

**Backward semantics**: `project backward` can be invoked by the human
directly (after reading a review finding) OR proposed by a skill (written
to `state.open_triggers`). The skill never executes the backward transition
itself; only the CLI verb does, and the human must confirm.

---

## Part V. The Experiment Interface (Convention, Not Platform)

We do not build an experiment runner. We define a **directory convention**
that any lab's existing launcher can be adapted to in 30 minutes. This
convention lives in `code_dir/experiments/<exp_id>/` — next to the method
code, not inside the project directory, because experiments belong with
the code that produced them.

### V.1 Directory layout

```
<code_dir>/experiments/<exp_id>/
  config.yaml              # the experiment definition (human or skill-generated)
  results.jsonl            # one record per trial — THE contract
  logs/                    # whatever the launcher writes (wandb export, stdout, csv, etc.)
  notes.md                 # researcher's post-hoc observations
  provenance_ref.txt       # id of the provenance record for the design that motivated this experiment
```

### V.2 `config.yaml` schema

Produced by `experiment-design` skill (or hand-written); consumed by the
researcher's launcher and by `experiment-analyze`.

```yaml
exp_id: insertion_tactile_01
design_provenance_id: <uuid>         # links to experiment_designs.jsonl record
hypothesis: >
  The tactile-only ablation should fail at sub-millimeter alignment
  (|error| < 0.5mm) because the depth camera's resolution at working
  distance cannot observe this regime (formalization §2.3 assumption A3).
formal_terms_tested:
  - "A3 (observation resolution)"
  - "policy π's dependence on tactile features φ_t"

conditions:
  - id: full_method
    description: "tactile + vision fusion"
  - id: vision_only        # ablation of the contribution
    description: "depth camera features only"
  - id: tactile_only       # complementary ablation
    description: "GelSight features only"
  - id: scripted_baseline  # simple baseline (per doctrine §8.2)
    description: "impedance control + position search"

baselines_required:
  - scripted                # per §8.2
  - strongest_prior         # per review_guideline §3.5.1
  - oracle                  # optional but recommended

trials_per_condition: 20     # per venue RSS (review_plan §1.6)
metrics:
  - success_rate
  - mean_insertion_time
  - failure_mode_taxonomy    # required — see doctrine §8.1

seeds: [0, 1, 2, 3, 4]
pre_registered_failure_modes:
  - "slip at contact initiation"
  - "overshoot from compliance mismatch"
  - "vision dropout on reflective surface"

cycle_time_target_s: 5.0
human_effort_estimate_hours: 2.0    # per doctrine §10.2 "hiding human effort"
```

### V.3 `results.jsonl` schema (the only hard contract)

One record per trial:

```json
{
  "exp_id": "insertion_tactile_01",
  "trial_id": 0,
  "seed": 0,
  "condition": "full_method",
  "started_at": "2026-04-20T10:00:00Z",
  "finished_at": "2026-04-20T10:00:07Z",
  "metrics": {
    "success": true,
    "insertion_time_s": 4.2,
    "final_error_mm": 0.3
  },
  "outcome": "success",
  "failure_mode": null,
  "notes": ""
}
```

As long as the lab's launcher writes this file, `experiment-analyze` can
audit the run. Wandb export → results.jsonl is a 10-line Python script.

### V.4 The new skills: `benchmark-survey`, `experiment-design`, `experiment-analyze`, `project-understanding`

**`benchmark-survey` (new, ~200 lines SKILL.md, Sonnet)**

- **Inputs**: `project.md`, `formalization.md`, literature via `alpha_review.apis.search_all` / `s2_citations` / Papers With Code / benchmark READMEs, prior `benchmark_surveys.jsonl` (for continuity across re-runs).
- **Actions**:
  1. Extract the problem class from `formalization.md` (observation type, action type, task semantics, info structure).
  2. Query literature for the 5–20 most common benchmarks used by papers addressing this class. Prefer: Papers With Code leaderboards, benchmark survey papers, the "Experiments" sections of top venues, community-maintained benchmark suites (RLBench, Meta-World, LIBERO, CALVIN, RoboSuite, ManiSkill, Open X-Embodiment, NIST ATB, FurnitureBench, etc.).
  3. For each candidate benchmark, extract: task scope, observation/action spaces, standard metrics, success criterion definition, top published baselines with numbers (at least 3 if available), recent-year score trend (for saturation assessment), install pointer (GitHub, pip, Docker), hardware requirements, and community usage volume (rough citation count of the benchmark paper).
  4. Rank candidates by: coverage of the formalization's core challenge, non-saturation (room for meaningful improvement), community acceptance, and reasonable install effort.
  5. Flag candidates that are (a) saturated (top score asymptoting above threshold), (b) misaligned with the formalization (e.g., the task's observation space doesn't include the modalities your formalization requires), or (c) abandoned (no updates in 3+ years).
  6. Produce a ranked proposal markdown (5–10 pages) the researcher reads before writing `benchmarks.md`. The proposal is a *recommendation*, not a decision — the human picks.
- **Outputs**: `benchmark_surveys.jsonl` record containing all candidates with metadata + scores + flags; a proposal markdown at `<project_dir>/benchmark_proposal.md` the human reads.
- **Stage**: FORMALIZE (primary — initial survey before entering DIAGNOSE), APPROACH (scope-check — when reviewing competitor papers' benchmarks to see if a strong paper needs additional benchmarks for generality claims).
- **Honesty**: Cannot verify that install instructions actually work on the researcher's system, cannot know compute budget, cannot judge whether the benchmark's notion of "success" aligns with what the researcher truly cares about. Sets `human_flag: true` on every recommendation.

**`experiment-design` (new, ~200 lines SKILL.md, Opus)**

- **Inputs**: `formalization.md`, `benchmarks.md` (required — this is the evaluation contract), `challenges.jsonl` (current challenge, if in APPROACH), `one_sentence.md`, `source.md`, prior `experiment_designs.jsonl`, `review_config.yaml` (target venue).
- **Modes**:
  - `reproduction` (DIAGNOSE entry): target a specific published baseline from `benchmarks.md`, produce a config that mirrors the baseline's setup as faithfully as possible, with `reproduction_of: <paper_ref>` and `target_metric: <published_number>` in the config.
  - `diagnostic` (DIAGNOSE): target a specific formalization term suspected of causing failure — produce a config with conditions that vary exactly that term.
  - `approach` (APPROACH / VALIDATE): target a specific claim about the method — produce a config with treatment/control/ablations that isolate the claimed contribution.
- **Actions**:
  1. Read the mode-specific inputs and the chosen benchmark(s) from `benchmarks.md`.
  2. Enumerate required baselines per `doctrine/research_guideline.md` §8.2 and `doctrine/review_guideline.md` §3.5.1. In `approach` mode, always include the strongest prior recorded in `benchmarks.md` for the chosen benchmark.
  3. Compute trial counts per condition based on venue thresholds (`spec/review_plan.md` §1.6).
  4. Enumerate ablations that isolate the claimed contribution (not composite ablations).
  5. Pre-register failure modes from the diagnosis history.
  6. Emit a `config.yaml` into `<code_dir>/experiments/<exp_id>/config.yaml` with `benchmark_id` and `mode` set.
- **Outputs**: `experiment_designs.jsonl` record + the config file.
- **Stage**: DIAGNOSE (reproduction + diagnostic modes), APPROACH, VALIDATE (approach mode).
- **Honesty**: Cannot know whether the proposed experiment is physically feasible — human confirms before launch.

**`experiment-analyze` (new, ~200 lines SKILL.md, Sonnet)**

- **Inputs**: `<code_dir>/experiments/<exp_id>/{config.yaml, results.jsonl, notes.md}`, `formalization.md`, `one_sentence.md`, `benchmarks.md` (for reproduction-mode comparison).
- **Modes** (determined by the experiment's `config.yaml` mode field):
  - `reproduction`: the experiment targeted a specific published baseline number. The skill computes the aggregate metric from `results.jsonl`, compares it to the `target_metric` from the config (which was copied from `benchmarks.md`'s `published_baselines` section), and emits:
    - `reproducibility: pass` — within tolerance (default ±10% relative)
    - `reproducibility: partial` — within 20%, but meaningful deviation
    - `reproducibility: fail` — outside tolerance; flag for investigation
    A failing reproduction does NOT auto-propose a backward trigger — it first requires the researcher to check setup (wrong install, wrong version, wrong hyperparameters, different hardware). Only after setup is confirmed does the skill consider the failure structural and propose `t4` or `t7`.
  - `diagnostic`: the experiment targeted a specific formalization term. The skill checks whether the hypothesized failure mode fired, and whether it fired for the hypothesized reason. Proposes `t4` if the failure doesn't map to the formal term the experiment was designed around.
  - `approach`: the experiment tested a claim about the method. The skill runs the full audit and proposes triggers per below.
- **Actions (common to all modes)**:
  1. Run `scripts/audit_stats.py` on `results.jsonl` for trial counts, CI, variance, effect size.
  2. Compare observed outcomes against `pre_registered_failure_modes`.
  3. Detect: (a) did the hypothesis hold? (b) did new unexpected failure modes appear? (c) does the ablation support the claimed contribution? (d) in reproduction mode, does the measured metric match the published number?
  4. Based on the pattern, propose zero or more backward triggers:
     - reproduction fails after setup confirmed → propose `t4` or `t7`
     - observed failures didn't match formal terms → propose `t4`
     - new failure modes emerged → propose `t8`
     - ablation shows contribution is doing nothing → propose `t15`
     - method is effectively a prior method's variant → propose `t5`
     - no trigger → experiment is consistent with current stage; advance
  5. Write a `finding` record summarizing the audit and mode-specific verdict.
- **Outputs**: `experiment_analyses.jsonl` record (includes `reproducibility` field when mode is reproduction), `findings.jsonl` record, possible `open_triggers` append to `state.json`.
- **Stage**: `DIAGNOSE` (reproduction + diagnostic modes) or `VALIDATE` (approach mode).

**`project-understanding` (new, ~150 lines SKILL.md, Sonnet)**

- **Inputs**: `state.code_dir`, `project.md`, `formalization.md`.
- **Actions**:
  1. Walk the code tree (respect `.gitignore`).
  2. Identify entry points (`main.py`, `train.py`, `eval.py`, etc.).
  3. Identify the method module, config files, data loaders, and evaluation harness.
  4. Extract the loss function(s) from training code.
  5. Compare the extracted loss to `formalization.md`'s objective — flag any mismatch as a formalization-implementation gap.
  6. Write `source.md` with sections: *Entry points*, *Method module*, *Training loop*, *Evaluation harness*, *Data handling*, *Formalization↔code correspondence*, *Open questions*.
- **Outputs**: `source.md`.
- **Stage**: any stage after `code_dir` is set, typically first invoked at DIAGNOSE entry.
- **Honesty**: Cannot run the code; cannot judge whether the architecture is correct; flags everything inferential.

---

## Part VI. Skill Stage-Awareness

Every SKILL.md gains a `research_stages:` frontmatter field listing the
stages where the skill is valid. The CLI's skill invoker checks this and
warns (never blocks) when the project is out-of-stage.

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

The enforcement is **soft** (warn) because researchers need escape hatches:
sometimes you re-run `paper-evaluate` in VALIDATE to double-check a claimed
concurrent work. `--force` silences the warning and records the override
in provenance.

---

## Part VII. Cuts — What We Delete to Stay Compact

Before building the new parts we delete the unfinished / speculative parts.
Net deletion is ~3,000 lines, net addition is ~1,500 lines of code + ~800
lines of new skill markdown + ~500 lines of templates/docs.

### VII.1 Delete the frontend

- Remove `frontend/` entirely.
- Remove `src/alpha_research/api/` entirely.
- Remove `fastapi`, `uvicorn`, `sse-starlette` from `pyproject.toml`.

**Justification**: a researcher using this from the CLI + `$EDITOR` loses
nothing. The frontend is a plausible Phase-2 delivery, but it is not
necessary for the research loop. (See [`../history/FRONTEND.md`](../history/FRONTEND.md) for the plan we are deferring.)

### VII.2 Collapse the project lifecycle layer

- Delete `src/alpha_research/projects/` (1,300 lines: `orchestrator.py`,
  `git_state.py`, `registry.py`, `resume.py`, `service.py`, `snapshots.py`,
  `understanding.py`, `_understanding_prompt.py`).
- Replace with `src/alpha_research/project.py` (~100 lines): just the
  `ProjectState` dataclass from Part II.2 plus `init_project`,
  `load_state`, `save_state`, `current_stage`, `transition`. No registry,
  no snapshots, no git-worktree resume.

**Justification**: the lifecycle layer models a problem we don't have yet.
`cd output/<project>` is resume. `git init` in the directory is versioning.
The understanding agent becomes the `project-understanding` skill.
(See [`../history/project_lifecycle_revision_plan.md`](../history/project_lifecycle_revision_plan.md)
for the ambitious design we're simplifying.)

### VII.3 Delete the stale knowledge module

- Delete `src/alpha_research/knowledge/{__init__.py, schema.py, store.py}`.
- Any remaining consumers now go through `records/jsonl.py` + `alpha_review.ReviewState`.

This was scheduled in R2/R6 of the refactor plan and deferred because of
the frontend and projects consumers. Phase VII.1 and VII.2 remove those
consumers, so the deletion becomes trivial.

### VII.4 Delete the report.py shim

- Delete `src/alpha_research/tools/report.py` (it's a 12-line backward-
  compatibility shim; `reports/templates.py` already has the real code).

### VII.5 Activate the skills

- `mkdir -p .claude && ln -sfn ../skills .claude/skills` (or copy).
- Without this, Claude Code never loads any of the 11 skills we wrote.
  This is the single highest-leverage one-line change in the whole plan.

---

## Part VIII. Implementation Phases

Each phase leaves the codebase in a working state (tests green, CLI
functional). Phases are ordered by dependency; where independent, noted.

### Phase 0 — Cut and consolidate *(1 day, net deletion)*

1. `rm -rf frontend/ src/alpha_research/api/`
2. `rm -rf src/alpha_research/projects/` (after moving any still-needed logic)
3. Write `src/alpha_research/project.py` (~100 lines) per Part II.2.
4. `rm -rf src/alpha_research/knowledge/`
5. `rm src/alpha_research/tools/report.py`
6. `ln -sfn ../skills .claude/skills`
7. Trim `pyproject.toml` (remove fastapi, uvicorn, sse-starlette; remove api entrypoint if any).
8. Trim `main.py` — remove `project create|list|show|status|snapshot|resume` subcommands, keep only `project init|stage|advance|backward|log|status` (several of these are added in Phase 2).
9. Fix any broken imports; run `pytest`.

**Acceptance**: tests pass; `python -c "import alpha_research"` succeeds;
`ls .claude/skills/` shows the 11 skills; line count of `src/alpha_research/`
down by ≥2,500.

### Phase 1 — State machine wiring *(2 days)*

1. Extend `src/alpha_research/pipelines/state_machine.py`:
   - Add `stage_guard_check(stage, project_dir) -> GuardCheck` that reads
     artifacts from disk and returns pass/fail per condition.
   - Add `advance_transition(project_dir, force=False, note=None) -> StageTransition`.
   - Add `backward_transition(project_dir, trigger, evidence, note) -> StageTransition`.
   - Add `detect_backward_triggers(finding_or_review) -> list[str]` that
     maps finding types → triggers per `research_plan.md` §1.
   - All functions are pure over (disk, inputs) → disk + return value.
2. Write `src/alpha_research/records/state.py` — `load_state`, `save_state`,
   `append_transition`, `append_open_trigger`, `resolve_open_trigger`. All
   operate on `<project_dir>/state.json`.
3. Add `provenance` as a record type in `records/jsonl.py`. Add a
   `log_action(project_dir, action_type, action_name, inputs, outputs,
   parent_ids, summary)` helper.
4. Unit test every guard `g1..g5` and every trigger `t2..t15` with fixture
   project directories. ~40 new tests.

**Acceptance**: `pytest tests/test_pipelines/test_state_machine.py`
exhaustively covers guards and triggers. No integration; just pure
functions over file fixtures.

### Phase 2 — Artifact templates and project lifecycle CLI *(2 days)*

1. Add templates under `src/alpha_research/templates/project/`:
   - `project.md.j2` — question, task, why-now, scope, assumptions
   - `hamming.md.j2` — 10-slot template, empty slots for the human
   - `formalization.md.j2` — five-component structure from
     `doctrine/problem_formulation_guide.md`
   - `benchmarks.md.j2` — sections: *In scope* (with per-benchmark
     subsection template: rationale, variant, metrics, success criterion,
     published baselines with numbers, install recipe, reproducibility
     status, saturation risk), *Considered but rejected*
   - `one_sentence.md.j2` — placeholder + "what it should NOT look like" examples
   - `log.md.j2` — weekly log preamble
2. Add CLI verbs in `main.py`:
   - `project init` — scaffolds a project directory
   - `project stage` — reads state.json + guards and renders
   - `project advance` — runs `advance_transition`
   - `project backward` — runs `backward_transition` (takes trigger + evidence + note)
   - `project log` — opens `$EDITOR` on log.md with an appended weekly section
   - `project status` — one-screen summary
3. Integration tests: create a project, advance it from SIGNIFICANCE to
   FORMALIZE (mocking the significance-screen skill with a passing fixture
   record), confirm state.json and provenance.jsonl are written correctly.

**Acceptance**: a researcher can run `alpha-research project init foo -q
"tactile insertion" -c /home/me/code` and see the scaffold; `project stage`
prints the initial state.

### Phase 3 — Wire existing skills to the state machine *(2 days)*

1. Add `research_stages:` frontmatter field to each of the 11 existing
   SKILL.md files per Part VI.
2. Add a stage-check helper `check_skill_stage(skill_name, project_stage)`
   used by `main.py`'s skill invoker and by pipelines.
3. Pipelines (`literature_survey`, `method_survey`, `frontier_mapping`,
   `research_review_loop`) start calling:
   - `check_skill_stage` on entry, warning if out of stage
   - `log_action` for every meaningful step
4. Wire `significance-screen` to read `<project_dir>/hamming.md` (currently
   it reads `guidelines/hamming_list.md` which is the wrong location).
5. Wire `formalization-check` to read `<project_dir>/formalization.md` as
   its primary input when invoked inside a project.

**Acceptance**: a skill invoked via `alpha-research skill ...` logs to
provenance, warns on out-of-stage, reads artifacts from the project.

### Phase 4 — Source binding and `project-understanding` skill *(1 day)*

1. Add `code_dir` handling in `project init` and `ProjectState`.
2. Write `skills/project-understanding/SKILL.md` per Part V.4.
3. Update `formalization-check` to optionally read `source.md` for the
   formalization↔implementation gap check.
4. Integration test: point a project at a tiny fake code_dir, run
   `project-understanding`, verify `source.md` is produced.

**Acceptance**: running `alpha-research skill project-understanding -p foo`
produces a `source.md`.

### Phase 5 — Benchmark survey and selection *(2 days)*

This phase adds the missing "what do we measure progress on" half of the
FORMALIZE stage. It must land before Phase 6 because `experiment-design`'s
reproduction mode reads `benchmarks.md`.

1. Write `skills/benchmark-survey/SKILL.md` per Part V.4 (~200 lines).
   Key inputs: `project.md`, `formalization.md`; key outputs:
   `benchmark_surveys.jsonl` + a proposal markdown at
   `<project_dir>/benchmark_proposal.md`.
2. Add `benchmark_surveys` to the supported record types in
   `records/jsonl.py` (one-line addition).
3. Tighten `stage_guard_check(FORMALIZE, ...)` (conditions 5 and 6 from
   Part III.2): require `benchmarks.md` to exist with at least one
   benchmark in "In scope" carrying a rationale, success criterion,
   ≥1 published baseline number, and saturation assessment. Require the
   latest `benchmark_survey` record to have `human_confirmed: true`.
   Add the new guard-condition tests.
4. Tighten `stage_guard_check(DIAGNOSE, ...)` (condition 1 from
   Part III.3): require that for every benchmark listed in
   `benchmarks.md` under "In scope" there exists at least one
   `experiment_analysis` record with mode=`reproduction` and
   `reproducibility ∈ {pass, partial}`. Add the corresponding tests.
5. Update the `benchmarks.md.j2` template (already staged in Phase 2)
   with a worked example for one benchmark so researchers have a
   concrete pattern.
6. Integration test: fixture project with a stub `benchmark_survey`
   record and a hand-written `benchmarks.md`; `project advance` from
   FORMALIZE passes only after both conditions 5 and 6 are met.

**Acceptance**: a project cannot leave FORMALIZE without `benchmarks.md`
populated, and cannot leave DIAGNOSE without at least one reproduction
experiment recorded per in-scope benchmark.

### Phase 6 — Experiment interface: design and analyze *(3 days)*

1. Write `guidelines/architecture/experiment_interface.md` — the convention
   spec from Part V (V.1, V.2, V.3). 1 page.
2. Write `skills/experiment-design/SKILL.md` per Part V.4 with all three
   modes (`reproduction`, `diagnostic`, `approach`). Reproduction mode
   reads `benchmarks.md` to target a specific published baseline number.
3. Write `skills/experiment-analyze/SKILL.md` per Part V.4 with mode-aware
   behavior. Reproduction mode compares the measured aggregate against
   `benchmarks.md`'s `published_baselines` and writes a
   `reproducibility: pass|partial|fail` field into the record.
4. Extend `scripts/audit_stats.py` if needed to support the `results.jsonl`
   schema directly. Currently it already reads CSV/JSON; add jsonl.
5. Wire `experiment-analyze` to append open triggers to `state.json` when
   it detects `t4 / t5 / t7 / t8 / t15`.
6. Integration test: a synthetic experiment directory with a known
   outcome, run `experiment-analyze`, verify the correct trigger is
   proposed. Include a fixture that exercises the reproduction-pass and
   reproduction-fail paths explicitly.

**Acceptance**: a researcher can run `alpha-research skill experiment-design
-p foo --mode reproduction --benchmark <id>` in DIAGNOSE stage and get a
config.yaml; after running it, `experiment-analyze` records a
reproducibility verdict that gates `g3`.

### Phase 7 — Diagnose-system and challenge-articulate integration *(1 day)*

1. Update `diagnose-system` skill to read from `experiments/<exp_id>/` in
   `code_dir` rather than expecting a verbal failure taxonomy as input.
2. Update `challenge-articulate` skill to read `diagnoses.jsonl` for the
   current stage's diagnosis rather than accepting it as argument.
3. Both skills log to provenance with parent_ids linking to the
   experiment_analyses or diagnoses that motivated them.

**Acceptance**: a synthetic project in DIAGNOSE stage with one completed
experiment can advance through DIAGNOSE → CHALLENGE → APPROACH by
invoking the appropriate skills, with state.json tracking each transition.

### Phase 8 — Observe, log, calibrate commands *(1 day)*

1. `alpha-research observe <exp_id>` — opens `$EDITOR` on a failure-note
   template; saves to `notes.md`; appends a structured record; prompts
   for `diagnose-system` invocation.
2. `alpha-research log` is already in Phase 2.
3. `alpha-research calibrate` — reads `calibration/human_scores.jsonl` (a
   file the researcher curates), runs `paper-evaluate` on each paper,
   prints a per-dimension score-delta table.
4. `alpha-research provenance` — renders the provenance tree (either
   flat list with timestamps or indented by parent_id DAG).

**Acceptance**: all six cross-stage commands (`observe`, `log`, `calibrate`,
`provenance`, `status`, `stage`) are functional and covered by CLI tests.

### Phase 9 — End-to-end integration test *(2 days)*

A single pytest that walks a synthetic project through all six stages,
invoking mocked versions of each skill, exercising at least one backward
transition, and verifying:

1. Every stage transition is logged to state.json and provenance.jsonl.
2. Every guard is checked before advancing.
3. A backward trigger proposed by a skill lands in `open_triggers`.
4. `project backward` resolves the trigger and updates the carried
   constraint.
5. At VALIDATE, a review with no fatal flaws transitions to DONE.
6. `alpha-research provenance` can trace a finding back to the
   formalization version that motivated the experiment that produced it.

**Acceptance**: `pytest tests/test_integration/test_full_loop.py` passes
with no network calls and no real LLM invocations.

### Phase 10 — Documentation and cleanup *(0.5 days)*

1. Update root `README.md` with the new CLI (the `project init/stage/
   advance/backward/log/observe/calibrate/provenance` verbs).
2. Update `guidelines/architecture/tools_and_skills.md` with a "State
   machine integration" section pointing at this plan.
3. Add a *Walkthrough* section to `guidelines/README.md`: "From zero to
   a published paper — the full loop in 20 commands."
4. Delete any now-stale sections of `guidelines/history/TASKS.md` or mark
   them fully superseded.

**Acceptance**: a new researcher landing on the repo can follow the
walkthrough and reach a toy published state in under an hour.

---

## Part IX. Running Totals

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

Net code delta: roughly **−150 lines**, with ~1,100 of the additions being
skill markdown rather than Python. The codebase gets materially simpler
while gaining the entire "doing research" half of the loop, including
benchmark survey, selection, and reproducibility-gated diagnosis.

---

## Part X. Acceptance Criteria (Plan-Level)

The plan is complete when all of the following are true:

1. **Stage lives on disk.** Every project has a `state.json` that tracks
   current stage, history, guard status, and open triggers. All
   transitions go through the CLI.

2. **Every artifact has an owner and a home.**
   - Human-owned markdown: `project.md`, `hamming.md`, `formalization.md`,
     `benchmarks.md`, `one_sentence.md`, `log.md`.
   - Agent-owned markdown: `source.md`, `benchmark_proposal.md`.
   - Agent-owned JSONL: all the record streams in Part II.1.
   - CLI-owned JSON: `state.json`.
   - CLI-owned append-only JSONL: `provenance.jsonl`.

3. **Benchmarks are first-class.** Every project has a `benchmarks.md`
   with at least one chosen benchmark before leaving FORMALIZE, and at
   least one successfully reproduced published baseline per chosen
   benchmark before leaving DIAGNOSE. Reproducibility is a hard guard,
   not a suggestion.

4. **The doing side is wired in.** `project-understanding` reads code,
   `benchmark-survey` surfaces and ranks evaluation frameworks,
   `experiment-design` produces runnable configs (reproduction /
   diagnostic / approach modes), `experiment-analyze` reads results and
   proposes triggers. The researcher's sim platform, training code, and
   experiment launcher remain theirs.

5. **Every skill knows its stage.** Invoking a skill out of its valid
   stages produces a warning with `--force` override; the override is
   recorded in provenance.

6. **Provenance is real.** Running `alpha-research provenance` on a
   project lets a human trace any finding or review back to the
   formalization version and benchmark choice that motivated the
   experiment that produced it.

7. **The frontend and the heavy project lifecycle layer are gone.** The
   codebase is materially smaller and the CLI + `$EDITOR` workflow is
   sufficient for a single researcher.

8. **The end-to-end integration test walks all six stages** with at least
   one backward transition AND at least one reproduction-experiment cycle
   (pass path and fail path), entirely in fixtures, no network.

9. **None of the following were built**: a simulation platform, a
   training framework, a data collection UI, an experiment launcher, a
   reproducibility/containerization layer, a web dashboard, a multi-user
   collaboration feature, a daemon or autonomous execution mode.

---

## Part XI. What We Explicitly Defer to a Possible Phase-2

These are all real concerns, and all deliberately out of scope:

- **Frontend dashboard.** The plan in [`../history/FRONTEND.md`](../history/FRONTEND.md) is
  well thought out; revisit after the CLI loop proves useful.
- **Multi-project navigation.** When a researcher has 5+ active projects,
  a lightweight registry becomes helpful. Until then, `ls output/`.
- **Snapshot / resume lineage.** The design in
  [`../history/project_lifecycle_revision_plan.md`](../history/project_lifecycle_revision_plan.md)
  is worth re-reading *after* we've lived with the compact version and
  know which parts are actually needed.
- **Real-time experiment streaming.** Watching a training run live is
  different from analyzing completed results; both are useful, but the
  latter is load-bearing for the state machine and the former is polish.
- **Multi-model pipelines.** Assigning Haiku to skim and Opus to deep
  analysis is a cost optimization; premature until the loop works.
- **Cross-project knowledge graph.** Today each project is isolated.
  A shared frontier map or Hamming list across projects is valuable
  eventually, but adds state management we don't currently need.

---

## Part XII. Authoring Note

The hardest thing about this plan is resisting the temptation to design
everything it could become. The six stages, the state tracking, the
source binding, the experiment interface, the provenance log — these are
load-bearing for the research loop. Everything else is premature.

The invariant to maintain through implementation: **a researcher can go
from `project init` to a published result using this system, without
ever running a web server, without ever opening a browser, using plain
markdown files and a CLI**. If a proposed feature requires breaking that
invariant, it belongs in Phase-2.
