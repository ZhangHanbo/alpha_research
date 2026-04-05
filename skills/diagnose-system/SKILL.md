---
name: diagnose-system
description: Run a minimal end-to-end robotics system, observe failures, classify into a taxonomy, and map each failure to terms in the formal problem structure. Use for "diagnose what's failing", "what's actually the bottleneck".
allowed-tools: Bash, Read, Write, Edit, Grep, Glob, NotebookEdit
model: claude-sonnet-4-6
---

# Diagnose System

## When to use
The researcher has a formalized problem (from `formalization-check`) and
needs to see what actually fails when a minimal system attempts the task.
Per `research_guideline.md` §2.4: *"AFTER formalization, build the simplest
possible system and run it. Watch it fail."*

This skill DOES NOT include its own simulator or training stack — it drives
the **lab's existing infrastructure** via `Bash`. The lab-specific commands
below are **placeholders** that must be customized with the local
conventions (config paths, simulator name, wandb project, etc.).

## Process

### Step 1 — Locate the minimal system config

```bash
# Standard locations in order of preference
ls configs/minimal.yaml 2>/dev/null || \
ls configs/*minimal*.yaml 2>/dev/null || \
ls experiments/minimal/ 2>/dev/null
```

If not found, use `Read` to explore and ask the researcher for the correct
path. Do not invent a config.

### Step 2 — Run the experiment (LAB-SPECIFIC — customize)

Replace these commands with the lab's convention:
```bash
# Training / policy run (placeholder)
python scripts/run_policy.py --config configs/minimal.yaml \
    --seeds 0 1 2 --n_trials 20

# Simulation-only (placeholder)
mjpython scripts/eval_sim.py --config configs/minimal.yaml --n_trials 20

# Real-robot (placeholder)
roslaunch alpha_research eval_real.launch config:=configs/minimal.yaml
```

If long-running, execute with `run_in_background=true` and poll for
completion. If training, save checkpoints; if eval, write trial logs to
a structured directory.

### Step 3 — Collect results

```bash
# From wandb
PYTHONPATH=src python -c "
import wandb, json
api = wandb.Api()
runs = api.runs('alpha_research/minimal', filters={'config.config_name': 'minimal.yaml'})
results = [{
    'run_id': r.id,
    'success_rate': r.summary.get('success_rate'),
    'n_trials': r.summary.get('n_trials'),
    'failure_reasons': r.summary.get('failure_reasons'),
    'seed': r.config.get('seed'),
} for r in runs[:6]]
print(json.dumps(results, indent=2))
"
```

Alternatively, use `scripts/audit_stats.py` for local directories:
```bash
python scripts/audit_stats.py logs/minimal_run/ --venue RSS
```

### Step 4 — Classify failures into the taxonomy

For each failed trial, classify into ONE of:
- **Perception** — observation was wrong or insufficient (missed object,
  wrong depth, lost tracking)
- **Planning** — decision was wrong given the observation (wrong grasp
  pose, infeasible trajectory)
- **Execution** — action did not produce intended state change (slip,
  collision, motor saturation)
- **Physics** — unexpected dynamics (contact transition, deformation,
  friction regime change)
- **Spec** — success criterion was met but the task wasn't actually done
  (reward hacking)

Produce a table: `trial_id | failure_type | specific_description`.

### Step 5 — Write SPECIFIC failure descriptions (CRITICAL)

Do not write vague descriptions. Per `research_guideline.md` §2.4:

| BAD (reject) | GOOD (accept) |
|---|---|
| "grasping fails" | "grasping fails on objects <2mm thick because the depth camera has 3mm resolution at working distance, so the gripper closes on empty space" |
| "the policy doesn't generalize" | "the visual encoder maps objects of similar color to nearby features despite different shapes, so the policy executes the mean action and fails on asymmetric objects" |
| "planning is too slow" | "collision checking dominates (78% of wall-clock time); each check requires full forward kinematics on a 7-DOF arm (~2ms); total plan time 1.8s at 500Hz fk calls" |

For each failure mode, ask: **can you name the specific mechanism?** If no,
push back until you can, or flag it for human investigation.

### Step 6 — Map failures to the formal structure

Load the most recent formalization check:
```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import read_records
from pathlib import Path
import json
recs = read_records(Path('<project_dir>'), 'formalization_check')
print(json.dumps(recs[-1] if recs else None, indent=2))
"
```

For each failure mode, identify which term in the formal structure breaks:
- Observation model P(z|s) insufficient → perception failure on specific state dimension
- State representation missing a relevant dimension → planning failure
- Action representation discretized wrong → execution failure
- Dynamics model missing an effect → physics failure

**If failures map cleanly to formal terms** → the formalization is on
track; proceed to CHALLENGE stage.

**If failures have NO mapping** (live outside the formal structure) →
trigger `t4` (DIAGNOSE → FORMALIZE): retreat to re-formalize. Flag this
explicitly in the output.

### Step 7 — Persist

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'diagnosis', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<diagnosis_json>'
```

## Output format

```json
{
  "system_config": "configs/minimal.yaml",
  "n_trials": 60,
  "success_rate": 0.35,
  "failure_taxonomy": {
    "perception": 18,
    "planning": 12,
    "execution": 9,
    "physics": 0,
    "spec": 0
  },
  "specific_failures": [
    {
      "trial": 3,
      "type": "perception",
      "description": "depth camera could not resolve the 1.5mm bolt head at 40cm working distance; detected object center 4mm offset from truth; grasp aimed at empty space"
    },
    {
      "trial": 7,
      "type": "execution",
      "description": "motor saturation during 0.2N target force; actual force peaked at 1.1N before safety abort; PID tuned for free-space motion, not contact"
    }
  ],
  "failure_to_formalism_map": {
    "depth_resolution": "observation model P(z|s) insufficient for state dim h (object height)",
    "motor_saturation": "dynamics model assumed free-space; contact-regime dynamics missing"
  },
  "unmapped_failures": [],
  "dominant_failure_mode": "perception — insufficient depth resolution",
  "suggested_next_stage": "CHALLENGE",
  "backward_trigger": null,
  "human_review_required": ["physical_intuition_on_edge_cases"]
}
```

`backward_trigger` is one of `"t4"` (DIAGNOSE→FORMALIZE), `"t8"` or `"t11"`
(if approach-stage failures emerged), otherwise null. Set it only when at
least 2 failures cannot be mapped to the current formal structure.

## Honesty protocol

You CANNOT run the physical robot yourself. You cannot *see* what went
wrong in a failed trial — you see logs, numbers, and possibly rendered
frames or recorded videos.

Always flag for human confirmation:
- Failure mechanisms that depend on physical intuition (why did the
  object slip? why did contact regime switch?)
- Unexpected interactions between components (the perception module and
  the control frequency, for example)
- Whether a proposed fix is feasible in the lab's infrastructure

When in doubt, write "flagged for human verification" and let the
researcher watch the trial recording.

## References

- `guidelines/research_guideline.md` §2.4 — empirical diagnosis (primary)
- `guidelines/research_guideline.md` §8.1 — failure taxonomy
- `guidelines/research_plan.md` — backward trigger t4 (DIAGNOSE→FORMALIZE)
- `scripts/audit_stats.py` — for local log directory statistics
