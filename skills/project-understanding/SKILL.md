---
name: project-understanding
description: Walk the researcher's method-code directory and produce source.md — a map of entry points, the method module, the training loop, the eval harness, and the formalization↔code correspondence. Use when code_dir is set on a project and source.md is missing or stale, typically on DIAGNOSE entry or after significant code changes.
allowed-tools: Bash, Read, Write, Grep, Glob
model: claude-sonnet-4-6
research_stages: [diagnose, approach]
---

# Project Understanding

## When to use

Invoked when a project has a `code_dir` set in its `state.json` and needs
a `source.md` written or refreshed. Typical triggers:

- First entry into DIAGNOSE (before running a reproduction experiment).
- After substantial code changes in the researcher's method module.
- When `formalization-check` is about to run and needs `source.md` to
  compute the formalization↔implementation gap.

This skill reads the code tree — it does NOT run the code, edit the
code, or judge whether the architecture is correct. It produces a
structured map the other skills (and the human) consume.

## Inputs

- `state.json` — to get `code_dir` and the project stage
- `project.md` — to know what the method is *supposed* to do
- `formalization.md` — the formal objective / constraints the code is
  supposed to implement
- The code tree at `code_dir`, respecting `.gitignore`

## Process

### Step 1 — Load the project state

```bash
PYTHONPATH=src python -c "
from alpha_research.project import load_state
import json, sys
project_dir = sys.argv[1]
state = load_state(project_dir)
print(json.dumps({
    'project_id': state.project_id,
    'current_stage': state.current_stage,
    'code_dir': state.code_dir,
    'target_venue': state.target_venue,
}, indent=2))
" "<project_dir>"
```

If `code_dir` is null, stop and report that `code_dir` must be set via
`alpha-research project init --code <path>` (or the researcher must
edit `state.json` directly).

### Step 2 — Inventory the tree

Use `Glob` and `Read` to collect:

- Top-level files (README, setup.py, pyproject.toml, requirements.txt, Makefile)
- Entry-point candidates: files matching `main.py`, `train.py`, `eval.py`, `run_*.py`, `cli.py`
- Config files: `config*.yaml`, `*.cfg`, `*.toml`, `configs/*.yaml`
- The top three directories by Python file count (typical method modules live here)

Respect `.gitignore` when walking. Do NOT descend into `__pycache__`,
`.git`, `.venv`, `node_modules`, `wandb`, or any directory listed in
`.gitignore`.

### Step 3 — Trace the training loop

Starting from the most promising entry point (usually `train.py` or the
one imported by the top-level `main.py`), trace:

- Which module defines the *model* (the policy, network, or controller)
- Which module defines the *loss* or *reward*
- Which module loads the data / connects to the simulator
- Which module runs the evaluation loop
- Which logger is used (wandb, tensorboard, csv, stdout)

Quote the specific file paths and relevant lines — `source.md` must be
actionable for another reader to navigate the code.

### Step 4 — Compute the formalization↔implementation gap

Read `formalization.md`'s **Objective** section and compare it to the
loss function you identified in Step 3. Flag any of:

- **Loss mismatch**: the formal objective is `L_2` but the implemented
  loss is cross-entropy. This is a `t10` signal (formalization-reality gap).
- **Constraint drop**: a constraint stated in `formalization.md` is
  not enforced in the code (e.g., "trajectories must remain in the
  reachable set" but no projection step exists).
- **Assumption violation**: an assumption stated in `formalization.md`
  is broken by the data pipeline or the simulator used.

These flags do NOT fire backward triggers on their own — they are
observations the human reviews. Mark each as `CONFIRMED`, `LIKELY`, or
`UNCERTAIN` based on how directly you saw evidence.

### Step 5 — Write `source.md`

Write the following structure to `<project_dir>/source.md` (overwrite
any existing version; the previous version is recoverable from git if
the project directory is versioned).

```markdown
# Source Understanding — `<project_id>`

_Produced by the `project-understanding` skill at <ISO timestamp>.
This file is agent-written; do not edit by hand (re-run the skill instead)._

## Code location

- **Root**: `<absolute path from state.code_dir>`
- **Top-level layout**: brief list
- **Python file count**: N
- **Primary language(s)**: Python, CUDA, C++, ...

## Entry points

- `train.py` — the training loop
- `eval.py` — the evaluation harness
- `<...>`

## Method module

- **Location**: `src/<package>/`
- **Key classes/functions**:
  - `<class>` at `<file:line>` — <one-line purpose>
  - `<function>` at `<file:line>` — <one-line purpose>

## Training loop

- **File**: `<path>`
- **Model defined at**: `<path:line>`
- **Loss computed at**: `<path:line>`
- **Optimizer**: <name, hyperparams>
- **Logger**: wandb | tensorboard | csv | stdout
- **Quoted snippet** (the actual loss):
  ```python
  <pasted code>
  ```

## Evaluation harness

- **File**: `<path>`
- **Metrics computed**:
  - <metric>
  - <metric>
- **How results are written**: <path pattern — this must match the
  `experiments/<exp_id>/results.jsonl` convention for the
  experiment-analyze skill to consume>

## Data / simulator interface

- **Data loader**: `<path>`
- **Simulator / real robot**: <name, version>

## Formalization↔code correspondence

| Formal element (formalization.md) | Code location | Correspondence |
|---|---|---|
| Objective $f(x)$ | `loss.py:42` | CONFIRMED / LIKELY / UNCERTAIN |
| Constraint $g(x) \leq 0$ | `project.py:123` or "not enforced" | ... |
| Assumption A3 | `data.py:88` or "violated" | ... |

## Flagged gaps

- **[FLAG]** <one-line description of a formalization↔implementation gap>
  - Evidence: `<path:line>`
  - Severity: mismatch | constraint_drop | assumption_violation
  - Confidence: CONFIRMED | LIKELY | UNCERTAIN
  - Possible backward trigger (human decides): `t10` | `t4` | `t15`

## Open questions for the researcher

- <question about something ambiguous in the code>
- <question about an intentional deviation from formalization>

---
```

### Step 6 — Log provenance

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import log_action
log_action(
    '<project_dir>',
    action_type='skill',
    action_name='project-understanding',
    project_stage='<stage>',
    inputs=['state.json', 'project.md', 'formalization.md', '<code_dir>'],
    outputs=['source.md'],
    summary='walked code tree, wrote source.md',
)
"
```

## Honesty protocol

- You cannot RUN the code — flag anything you're not 100% sure about.
- You cannot judge whether the method's architecture is correct — that's
  the human's job. Only flag correspondence mismatches, not design choices.
- If the code tree is too large to walk thoroughly, cap the depth at 5
  levels and note the cap in `source.md`'s header.
- If you cannot find an entry point, write `source.md` anyway but mark
  every section as `UNKNOWN — could not trace`.

## References

- `guidelines/doctrine/research_guideline.md` §2.4, §3.1 — formalization
- `guidelines/spec/research_plan.md` §DIAGNOSE — role of the minimal system
- `guidelines/spec/review_plan.md` §1.3 — formalization-reality gap metric
- `guidelines/spec/implementation_plan.md` §V.4 — skill specification
