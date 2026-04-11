# The Experiment Interface Convention

This is a **convention**, not a framework. `alpha_research` does not
install benchmarks, launch training runs, or ship data collection tools.
It reads and writes a documented directory layout that any lab's
existing launcher can be adapted to in ~30 minutes.

The `experiment-design` skill writes configs into this layout.
The `experiment-analyze` skill reads results from this layout.
The researcher's own launcher fills in the middle.

## Directory layout

Each experiment lives in its own directory under the method code tree:

```
<code_dir>/experiments/<exp_id>/
├── config.yaml              # the experiment definition
├── results.jsonl            # one record per trial — THE hard contract
├── logs/                    # whatever the launcher writes (wandb export, stdout, csv)
├── checkpoints/             # optional model checkpoints
├── notes.md                 # researcher's post-hoc observations
└── provenance_ref.txt       # id of the experiment_design record that motivated this run
```

`<exp_id>` should be stable and meaningful. Recommended format:
`<mode>_<benchmark_short>_<YYYYMMDD>` — e.g. `reproduction_nistatb_20260415`.

## config.yaml — written by `experiment-design`

```yaml
exp_id: reproduction_nistatb_20260415
mode: reproduction | diagnostic | approach
design_provenance_id: prov_9b2e4f1a
benchmark_id: NIST ATB

hypothesis: |
  The tactile+vision fusion baseline from Paper A (2024) should reach
  0.62 success on single-peg-in-hole insertion under default conditions.

formal_terms_tested:
  - "A3 (observation resolution)"

# Reproduction mode only:
reproduction_of: "paperA_2024"
target_metric: 0.62    # the published number this run targets

conditions:
  - id: reproduce_paperA
    description: "Paper A impedance baseline, reproduced on our hardware"

baselines_required:
  - scripted       # doctrine §8.2
  - strongest_prior
  - oracle         # recommended but optional

trials_per_condition: 20
seeds: [0, 1, 2, 3, 4]

metrics:
  - success_rate
  - mean_insertion_time
  - failure_mode_taxonomy    # required by doctrine §8.1

pre_registered_failure_modes:
  - "slip at contact initiation"
  - "overshoot from compliance mismatch"
  - "vision dropout on reflective surface"

cycle_time_target_s: 5.0
human_effort_estimate_hours: 2.0
```

## results.jsonl — the one hard contract

One JSON object per line, one object per trial. Any launcher that
writes this format can be consumed by `experiment-analyze`.

```json
{
  "exp_id": "reproduction_nistatb_20260415",
  "trial_id": 0,
  "seed": 0,
  "condition": "reproduce_paperA",
  "started_at": "2026-04-15T10:00:00Z",
  "finished_at": "2026-04-15T10:00:07Z",
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

### Required fields per trial

| Field | Type | Purpose |
|---|---|---|
| `exp_id` | str | Must match `config.yaml`'s `exp_id` |
| `trial_id` | int | Unique within this experiment |
| `seed` | int / null | For stochastic conditions |
| `condition` | str | Must match a `conditions[].id` in config.yaml |
| `outcome` | str | `"success"` / `"failure"` / the launcher's own taxonomy |
| `metrics` | object | Per-trial metric dict matching config.yaml's `metrics` list |

### Optional fields

| Field | Type | Purpose |
|---|---|---|
| `started_at`, `finished_at` | ISO 8601 | For cycle-time audits |
| `failure_mode` | str / null | Must be one of `config.pre_registered_failure_modes` or `"new:<description>"` |
| `notes` | str | Free-form per-trial notes |

## Adapting an existing launcher

Whatever launcher you already use (bash + Hydra, wandb sweep, SLURM,
...), write a small post-processor that emits `results.jsonl` from the
launcher's native log format. Example skeleton:

```python
# scripts/to_results_jsonl.py
import json, sys, pandas as pd

config_path, wandb_export, out_path = sys.argv[1:4]
df = pd.read_csv(wandb_export)

with open(out_path, "w") as fp:
    for i, row in df.iterrows():
        fp.write(json.dumps({
            "exp_id": row["exp_id"],
            "trial_id": int(row["trial_id"]),
            "seed": int(row["seed"]),
            "condition": row["condition"],
            "outcome": "success" if row["success"] else "failure",
            "metrics": {
                "success": bool(row["success"]),
                "time_s": float(row["time_s"]),
            },
            "failure_mode": row.get("failure_mode") or None,
        }) + "\n")
```

That's the whole integration. `experiment-analyze` reads `config.yaml`
and `results.jsonl`; it does not care how they were produced.

## What `experiment-analyze` does NOT do

- It does not run your code.
- It does not compute new metrics beyond what's already in `results.jsonl`.
- It does not re-analyze old experiments unless you pass `--exp <id>`
  explicitly.
- It does not auto-execute backward triggers — it only proposes them.

## Reproducibility floor

At DIAGNOSE entry, the researcher must produce one `reproduction` mode
experiment per in-scope benchmark, run it, and let `experiment-analyze`
record a `reproducibility: pass | partial` result. The forward guard
`g3` checks for this before allowing DIAGNOSE → CHALLENGE.

A `reproducibility: fail` result is the **first** thing to check for
setup bugs: wrong install, wrong version pin, wrong hyperparameters,
wrong hardware. Only after the setup is confirmed should a failing
reproduction be treated as a formal mismatch (trigger `t4` or `t7`).

## References

- `guidelines/spec/implementation_plan.md` Part V — full contract
  specification
- `guidelines/doctrine/research_guideline.md` §8 — evaluation standards
  (baselines, trial counts, failure taxonomies)
- `guidelines/spec/review_plan.md` §1.6 — venue-specific thresholds
