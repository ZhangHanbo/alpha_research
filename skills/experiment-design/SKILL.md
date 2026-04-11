---
name: experiment-design
description: Produce a runnable experiments/<exp_id>/config.yaml from formalization.md + benchmarks.md + current challenge + approach description. Supports three modes — reproduction (DIAGNOSE entry), diagnostic (DIAGNOSE core loop), approach (APPROACH+VALIDATE). Does NOT launch the experiment; generates the config, pre-registers hypothesis and failure modes, enumerates required baselines and trial counts per venue. Use when the researcher needs to run an experiment and wants the design checked against doctrine §8 and review_plan §1.6.
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-1-20250805
research_stages: [diagnose, approach, validate]
---

# Experiment Design

## When to use

Three modes, each tied to a stage:

- **`reproduction`** — used at DIAGNOSE entry. Target a specific published
  baseline from `benchmarks.md` and produce a config that mirrors it as
  faithfully as possible. Exists to verify the measurement infrastructure.

- **`diagnostic`** — used inside DIAGNOSE. Vary one specific term or
  assumption in `formalization.md` to test whether it is the load-bearing
  cause of an observed failure. The experiment's conditions map 1:1 to
  the formal terms being probed.

- **`approach`** — used in APPROACH and VALIDATE. Test a claim about the
  method. Conditions = treatment, control, ablations that isolate the
  claimed contribution.

This skill generates the config. The researcher launches it. The
`experiment-analyze` skill reads the results back and emits a verdict.

## Inputs

- `formalization.md` — the math and assumptions under test
- `benchmarks.md` — which benchmark(s) are in scope; which published
  baselines are the reproduction targets (for reproduction mode) or the
  comparisons to beat (for approach mode)
- `state.json` — project stage (must match the mode)
- `challenges.jsonl` — the current challenge (for diagnostic + approach modes)
- Current approach description (in `one_sentence.md` or a draft section
  in `project.md`) — for approach mode
- `review_config.yaml` — target venue for trial-count thresholds
- `source.md` — produced by `project-understanding` — to know where
  experiments should be launched from and what "condition" means in the
  code
- Prior `experiment_designs.jsonl` and `experiment_analyses.jsonl` — for
  continuity and to avoid re-running already-answered questions

## Process

### Step 1 — Determine mode and load inputs

```bash
PYTHONPATH=src python -c "
from alpha_research.project import load_state
from alpha_research.records.jsonl import read_records
import json, sys, pathlib

project_dir = pathlib.Path(sys.argv[1])
mode = sys.argv[2]  # reproduction | diagnostic | approach

state = load_state(project_dir)
print(json.dumps({
    'stage': state.current_stage,
    'venue': state.target_venue,
    'code_dir': state.code_dir,
    'mode': mode,
    'prior_designs': len(read_records(project_dir, 'experiment_design')),
    'prior_analyses': len(read_records(project_dir, 'experiment_analysis')),
}, indent=2))
" "<project_dir>" "<mode>"
```

Validate the mode against the stage:

- `reproduction` and `diagnostic` require `stage == diagnose`
- `approach` requires `stage in {approach, validate}`

If mismatched, warn and stop — the researcher should either switch
modes or transition stages first.

### Step 2 — Parse benchmarks.md to find the target

Read `<project_dir>/benchmarks.md`. Extract every benchmark under
`## In scope`. For each, capture:

- Benchmark name + variant
- Success criterion (exact string)
- Published baselines with numbers (Paper + year + method + score + metric)
- Install recipe
- Saturation risk

The target benchmark for this experiment is either:

- **reproduction**: specified via `--benchmark <name>` argument;
  reproduction target is the strongest-prior row (unless `--target-paper
  <ref>` overrides)
- **diagnostic / approach**: the primary benchmark from `benchmarks.md`
  (the first `## In scope` entry), unless `--benchmark` overrides

### Step 3 — Enumerate conditions

**Reproduction mode**:

- One condition: `reproduce_<paper>_<method>` with the reproduction target's
  hyperparameters as stated in its paper (if available) or default settings.
- NO ablations. The goal is to hit the published number.

**Diagnostic mode**:

- One condition per formal term/assumption you want to probe.
- Example: if you suspect observation resolution is the bottleneck,
  conditions might be `{high_res_depth, low_res_depth, tactile_only}`.

**Approach mode**:

- `full_method` — the researcher's full approach
- `scripted_baseline` — doctrine §8.2 REQUIRES a simple scripted baseline
- `strongest_prior` — the benchmark's strongest published baseline
  (from benchmarks.md)
- `oracle_baseline` (optional) — idealized with perfect perception /
  perfect dynamics (doctrine §8.2 recommends this)
- One condition per ablation that removes exactly one claimed component
  from `full_method`. Ablations must isolate the contribution — "remove
  A + B + C" does not isolate anything.

### Step 4 — Compute trial counts per venue

Read `review_config.yaml` for the target venue. Apply the thresholds
from `review_plan.md §1.6`:

| Venue | trials/condition | CI required? | stochastic → 2× trials |
|---|---|---|---|
| IJRR, T-RO | ≥ 20 | yes | yes |
| RSS | ≥ 20 | yes | yes |
| CoRL | ≥ 10 | expected | recommended |
| ICRA, IROS | ≥ 10 | optional | recommended |
| RA-L | ≥ 10 | optional | recommended |

Always use a seed set of at least 5 random seeds for stochastic
conditions.

### Step 5 — Pre-register hypothesis and failure modes

**Reproduction mode**:

- Hypothesis: "the measured aggregate on `success_rate` will be within
  ±10% of `<published_number>` (relative)"
- Pre-registered failures: "published number is not reproducible — check
  install, version pin, hyperparameters, hardware"

**Diagnostic mode**:

- Hypothesis: quote the formal term under test. E.g. "varying
  `observation resolution` from 4mm to 0.5mm will produce monotonic
  improvement on `insertion_success`, because assumption A3 predicts it."
- Pre-registered failures: "no monotonic improvement (A3 wrong)",
  "improvement plateaus (different bottleneck)", "improvement reverses
  (interaction with another term)"

**Approach mode**:

- Hypothesis: quote the one-sentence contribution. "full_method will
  outperform strongest_prior on <metric> by at least <delta>."
- Pre-registered failures from diagnosis history: any failure mode the
  method is supposed to fix must be watched.

### Step 6 — Estimate cycle time and human effort

Read `source.md` to find the evaluation harness timing info. Compute:

- Estimated cycle time per trial (seconds)
- Total wall-clock time for the whole experiment
- Human effort estimate (reset time, demos if needed, calibration)

Doctrine §10.2 warns about "hiding human effort" — this must be in the
config so `experiment-audit` can challenge it later.

### Step 7 — Write the config

Emit `<code_dir>/experiments/<exp_id>/config.yaml`:

```yaml
exp_id: <mode>_<benchmark_id>_<timestamp>
mode: reproduction | diagnostic | approach
design_provenance_id: <will be filled by step 8>
benchmark_id: <from benchmarks.md>

hypothesis: |
  <one paragraph stating the hypothesis in formal terms>

formal_terms_tested:
  - <term or assumption from formalization.md>

target_metric: <published_number>   # reproduction mode only
reproduction_of: <paper_ref>         # reproduction mode only

conditions:
  - id: <condition_name>
    description: <what this condition varies>
  - ...

baselines_required:
  - scripted
  - strongest_prior
  - oracle             # optional but recommended

trials_per_condition: <N from venue table>
seeds: [0, 1, 2, 3, 4]

metrics:
  - <metric>
  - failure_mode_taxonomy

pre_registered_failure_modes:
  - <mode 1>
  - <mode 2>

cycle_time_target_s: <from source.md>
human_effort_estimate_hours: <from source.md>
```

### Step 8 — Append the experiment_design record + provenance

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record, log_action
rec_id = append_record(
    '<project_dir>',
    'experiment_design',
    {
        'mode': '<mode>',
        'benchmark_id': '<benchmark>',
        'exp_id': '<exp_id>',
        'config_path': '<code_dir>/experiments/<exp_id>/config.yaml',
        'hypothesis': '<one-sentence summary>',
        'reproduction_of': '<paper_ref or null>',
        'target_metric': '<number or null>',
        'trials_per_condition': <N>,
        'conditions': [<list of ids>],
        'baselines_required': [...],
        'pre_registered_failure_modes': [...],
    },
)
log_action(
    '<project_dir>',
    action_type='skill',
    action_name='experiment-design',
    project_stage='<stage>',
    inputs=['formalization.md', 'benchmarks.md', 'source.md'],
    outputs=[f'experiments/<exp_id>/config.yaml', f'experiment_design.jsonl#{rec_id}'],
    summary=f'<mode> experiment for <benchmark>: <one-line hypothesis>',
)
"
```

### Step 9 — Stop. Do NOT launch.

Tell the researcher:

```
✓ Experiment config written: <code_dir>/experiments/<exp_id>/config.yaml
Run it with your usual launcher, then:
  alpha-research skill experiment-analyze --exp <exp_id>
```

## Honesty protocol

- You CAN write a well-structured config that satisfies doctrine §8.2
  baseline requirements and venue trial counts.
- You CANNOT know whether the experiment will actually run on the
  researcher's hardware — they must check.
- You CANNOT know whether the pre-registered hypothesis is physically
  feasible — that's the one thing the researcher brings.
- Never launch the experiment. Never edit the method code. If `source.md`
  is missing, ask the researcher to run `project-understanding` first
  instead of guessing.

## References

- `guidelines/doctrine/research_guideline.md` §8 — evaluation standards,
  baselines, statistical rigor
- `guidelines/doctrine/review_guideline.md` §3.5 — validation attack
  vectors, "strongest missing baseline" rule
- `guidelines/spec/review_plan.md` §1.6 — trial counts per venue
- `guidelines/spec/implementation_plan.md` §III.3, §III.5, §V — stage
  contracts for DIAGNOSE/APPROACH/VALIDATE and the experiment interface
  convention
