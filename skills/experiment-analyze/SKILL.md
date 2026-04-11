---
name: experiment-analyze
description: Read experiments/<exp_id>/results.jsonl, run audit_stats.py for statistical rigor, compare observed outcomes against pre-registered hypotheses and failure modes, and emit a finding record with a per-condition verdict. In reproduction mode, compares the measured aggregate against the target number from benchmarks.md and writes reproducibility={pass|partial|fail}. Proposes backward triggers (t4/t5/t7/t8/t15) when patterns suggest the research state machine should regress. Does NOT execute backward transitions; the human decides. Use after an experiment completes.
allowed-tools: Bash, Read, Write, Grep
model: claude-sonnet-4-6
research_stages: [diagnose, validate]
---

# Experiment Analyze

## When to use

An experiment has finished and its results are on disk under
`<code_dir>/experiments/<exp_id>/`. This skill reads the results,
audits them, and emits a finding + zero or more proposed backward
triggers. It is the counterpart to `experiment-design` — one produces
configs, the other consumes results.

## Inputs

- `<code_dir>/experiments/<exp_id>/config.yaml` — the design
- `<code_dir>/experiments/<exp_id>/results.jsonl` — one record per trial
  (schema in `guidelines/spec/implementation_plan.md §V.3`)
- `<code_dir>/experiments/<exp_id>/notes.md` — researcher's post-hoc
  observations
- `formalization.md` — to check whether observed failures map to formal terms
- `benchmarks.md` — for reproduction-mode comparison
- `one_sentence.md` — for approach-mode claim check
- Prior `diagnoses.jsonl` — to check whether new failure modes emerged
- `state.json` — for stage and code_dir

## Process

### Step 1 — Load the experiment

```bash
PYTHONPATH=src python -c "
import yaml, json, pathlib, sys
exp_dir = pathlib.Path(sys.argv[1])
config = yaml.safe_load((exp_dir / 'config.yaml').read_text())
trials = []
with (exp_dir / 'results.jsonl').open() as fp:
    for line in fp:
        line = line.strip()
        if line:
            trials.append(json.loads(line))
print(json.dumps({
    'exp_id': config.get('exp_id'),
    'mode': config.get('mode'),
    'benchmark_id': config.get('benchmark_id'),
    'hypothesis': config.get('hypothesis', '')[:200],
    'n_trials': len(trials),
    'conditions': sorted({t['condition'] for t in trials}),
}, indent=2))
" "<code_dir>/experiments/<exp_id>"
```

### Step 2 — Run the statistical audit

```bash
python scripts/audit_stats.py <code_dir>/experiments/<exp_id> --venue <venue> --json
```

The script reports:

- Trials per condition (vs. required minimum)
- Success rate (and any other metric in `metrics`)
- 95% CI (bootstrap for small N)
- Variance across seeds
- Effect sizes between conditions

Flag any of:

- Trials per condition below the venue minimum → `statistical_insufficiency`
- Missing confidence intervals when venue requires them → `missing_ci`
- Missing strong baselines (compare config's `baselines_required` against
  the conditions actually run) → `missing_baseline`

### Step 3 — Mode-specific analysis

#### Reproduction mode

```bash
PYTHONPATH=src python -c "
import json, pathlib, sys, yaml, re
exp_dir = pathlib.Path(sys.argv[1])
project_dir = pathlib.Path(sys.argv[2])
config = yaml.safe_load((exp_dir / 'config.yaml').read_text())

# Read target from config (was copied from benchmarks.md at design time)
target = config.get('target_metric')
trials = [json.loads(l) for l in (exp_dir / 'results.jsonl').read_text().splitlines() if l.strip()]

# Compute observed aggregate for the one condition
observed = sum(1 for t in trials if t.get('outcome') == 'success') / len(trials)
rel_diff = abs(observed - target) / target

if rel_diff <= 0.10:
    verdict = 'pass'
elif rel_diff <= 0.20:
    verdict = 'partial'
else:
    verdict = 'fail'

print(json.dumps({
    'observed': observed,
    'target': target,
    'relative_diff': rel_diff,
    'reproducibility': verdict,
}, indent=2))
" "<code_dir>/experiments/<exp_id>" "<project_dir>"
```

A `fail` result does NOT automatically propose a backward trigger. The
first diagnosis is always "check your setup" — wrong install, wrong
version pin, wrong hyperparameters, wrong hardware. The researcher should
confirm the setup is correct before considering the failure structural.

If the researcher confirms setup is correct and the number still doesn't
match, propose `t4` (failure doesn't map to the formal frame — the
benchmark's notion of success isn't what your formalization predicts)
or `t7` (the benchmark is in the wrong framework for this formalization).

#### Diagnostic mode

Compare observed per-condition outcomes to the pre-registered hypothesis.

- If the hypothesized pattern held → the experiment has evidence for
  the corresponding formal term. Emit a positive finding.
- If the observed failure mode matches a `pre_registered_failure_modes`
  entry → no backward trigger, the experiment did its job.
- If a NEW failure mode appeared → propose `t8` (approach exposes new
  failure modes).
- If the failure modes don't map to ANY formal term in `formalization.md`
  → propose `t4` (failure doesn't map to math).

#### Approach mode

Compare `full_method` vs `strongest_prior` vs ablations.

- If `full_method` does not significantly outperform `strongest_prior` →
  propose `t5` (method is a trivial variant).
- If the ablation that removes the claimed contribution does NOT hurt
  performance → propose `t15` (wrong mechanism hypothesis). This is
  the most important check and the one that most papers skip.
- If `full_method` works but the one-sentence claim cannot be stated in
  formal terms (because the mechanism isn't what the formalization
  predicted) → propose `t14` (theoretical justification gap).

### Step 4 — Synthesize the finding

Build a finding record with:

- `exp_id`, `mode`, `benchmark_id`, `verdict_summary`
- `statistical_audit` (trials/CI/effect sizes/flags)
- `hypothesis_status` — `supported` | `contradicted` | `inconclusive`
- `observed_failure_modes` — list matching `pre_registered_failure_modes`
  AND a list of new ones
- `reproducibility` (reproduction mode only)
- `proposed_backward_triggers` — list of `{trigger, evidence, severity}`
  for each detected trigger. May be empty.
- `revised_one_sentence_test` (approach mode only) — if the observed
  mechanism differs from the predicted one, suggest a new one-sentence
  contribution for the researcher to consider.
- `human_flag: true` — every finding requires human review before
  executing any proposed trigger.

### Step 5 — Append records + provenance

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record, log_action
from alpha_research.project import propose_backward_trigger

# Append the experiment_analysis record
analysis_id = append_record(
    '<project_dir>',
    'experiment_analysis',
    {
        'exp_id': '<exp_id>',
        'mode': '<mode>',
        'benchmark_id': '<benchmark>',
        'reproducibility': '<pass|partial|fail|null>',
        'hypothesis_status': '<supported|contradicted|inconclusive>',
        'statistical_audit': {...},
        'pre_registered_failure_modes_fired': [...],
        'new_failure_modes': [...],
        'proposed_backward_triggers': [...],
        'human_flag': True,
    },
)

# Also append a finding record (what adversarial-review and project stage read)
finding_id = append_record(
    '<project_dir>',
    'finding',
    {
        'source': 'experiment-analyze',
        'exp_id': '<exp_id>',
        'summary': '<one-line>',
        'severity': '<serious|minor>',
        'analysis_id': analysis_id,
    },
)

# Surface any proposed backward triggers
for trig in <proposed_backward_triggers>:
    propose_backward_trigger(
        '<project_dir>',
        trigger=trig['trigger'],
        proposed_by='experiment-analyze',
        evidence=trig['evidence'],
    )

log_action(
    '<project_dir>',
    action_type='skill',
    action_name='experiment-analyze',
    project_stage='<stage>',
    inputs=['experiments/<exp_id>/results.jsonl', 'formalization.md', 'benchmarks.md'],
    outputs=[f'experiment_analysis.jsonl#{analysis_id}', f'finding.jsonl#{finding_id}'],
    parent_ids=[<design_provenance_id from config>],
    summary='<verdict> on <exp_id>: <1-line>',
)
"
```

### Step 6 — Report to the researcher

Print a human-readable summary to stdout:

```
Experiment: <exp_id>  (mode=<mode>, benchmark=<id>)
────────────────────────────────────────────────────
Trials:        <n> across <k> conditions
Statistical:   <pass|warnings>
Hypothesis:    <supported|contradicted|inconclusive>
Reproducibility: <pass|partial|fail|n/a>

Proposed backward triggers:
  - t15: ablation shows wrong mechanism (see finding.jsonl#<id>)

Next: review the finding, then either
  alpha-research project backward t15 --constraint "..."
  alpha-research project advance
```

## Honesty protocol

- You CAN compute statistics from the results file.
- You CAN compare observed to expected and report the delta.
- You CANNOT run the experiment yourself, and you CANNOT re-run it if
  the numbers look wrong — just report what's on disk.
- You CANNOT decide whether a reproduction failure is a setup bug or a
  formal mismatch — tell the researcher to check setup first.
- You CANNOT execute a backward trigger — you can only propose one.
  `propose_backward_trigger` appends to `open_triggers` in state.json;
  the human runs `project backward` to actually transition.
- If `results.jsonl` is malformed or has fewer trials than `config.yaml`
  says were planned, stop and report the mismatch — do NOT proceed with
  a partial analysis.

## References

- `guidelines/doctrine/research_guideline.md` §8 — evaluation standards
- `guidelines/doctrine/review_guideline.md` §3.5 — validation attacks
- `guidelines/spec/review_plan.md` §1.6 — trial count thresholds
- `guidelines/spec/implementation_plan.md` §III.3, §III.6, §V — stage
  contracts and experiment interface convention
- `scripts/audit_stats.py` — the statistical audit helper this skill calls
