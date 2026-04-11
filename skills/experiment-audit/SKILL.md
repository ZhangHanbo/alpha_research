---
name: experiment-audit
description: Check whether experiments support the claims. Verifies statistical sufficiency, baselines, ablation isolation, venue thresholds. Detects overclaiming and names the strongest missing baseline. Use for rigor or baseline checks.
allowed-tools: Bash, Read, Write, Grep
model: claude-sonnet-4-6
research_stages: [validate]
---

# Experiment Audit

## When to use
Applied to either the researcher's own experiment directory or a paper
under review. Maps to the VALIDATE stage and to review attack vectors
§3.5. Combines deterministic statistical checks (via `scripts/audit_stats.py`)
with judgment-heavy checks (missing baselines, overclaiming, ablation
isolation).

## Venue-calibrated thresholds (review_plan.md §1.6)

| Venue | Min trials/condition | CI required? | Real robot? |
|---|---|---|---|
| IJRR, T-RO, RSS, CoRL | ≥ 20 | Yes | Yes (strongly) |
| RA-L | ≥ 15 | Yes | Yes |
| ICRA, IROS | ≥ 10 | Preferred | Preferred |

Values below these thresholds trigger a "serious weakness" finding; values
below 5 trigger "fatal".

## Process

### Step 1 — Identify the input
- Own experiment: path to an experiment directory with `results.json`,
  `trials.csv`, or `seed_*/metrics.json`
- Paper: `paper_id` → fetch full text via `fetch_and_extract`, read
  the experiments section

### Step 2 — Run deterministic statistical audit

For an experiment directory:
```bash
python scripts/audit_stats.py <exp_dir> --venue RSS
```

Output JSON includes:
- `trials_per_condition`
- `mean_success_rate`
- `std_across_seeds`
- `ci_95: [low, high]`
- `venue_threshold_met: bool`
- `insufficient_trials: bool`

For a paper, extract these manually from reported tables and compute them
in the skill reasoning (or use the `scipy.stats` one-liner via
`python -c "..."` if numbers are available).

### Step 3 — Check baseline strength

Extract the list of baselines from the paper's experiments section.
Categorize each baseline:
- **Simple / scripted** — PID, heuristic, random, rule-based
- **Prior method** — specific named methods from the literature
- **Oracle** — perfect perception, perfect dynamics, etc.
- **SOTA** — the strongest known prior method for this problem

Flag missing categories:
- No simple baseline → weakness
- No SOTA baseline → serious weakness
- No oracle baseline → note (not required, but helps identify bottlenecks)

### Step 4 — Name the strongest MISSING baseline

This is the most useful single contribution of this skill. Search for
methods that SHOULD have been compared:
```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json, sys
# Search for methods the paper didn't cite
results = search_all(sys.argv[1], limit_per_source=15, year_lo=2022)
results.sort(key=lambda r: r.get('citationCount', 0), reverse=True)
print(json.dumps([{
    'title': r['title'],
    'year': r['year'],
    'cites': r.get('citationCount', 0),
    'venue': r.get('venue', ''),
} for r in results[:10]], indent=2))
" "<problem_keywords> <approach_keywords>"
```

Compare against the paper's actual baselines. Name the single strongest
missing one. If it existed before the paper's submission date and
outperforms the paper's method on a related benchmark, this is a serious
weakness.

### Step 5 — Check ablation isolation

Does the ablation remove the paper's CLAIMED contribution and show that
performance actually drops? If not → trigger `t15` (VALIDATE → DIAGNOSE,
wrong mechanism).

Extract the ablation table. For each row labeled "w/o X" where X is the
paper's claimed contribution, check whether the performance drops
significantly (ideally ≥10%). If the drop is small, flag it.

### Step 6 — Detect overclaiming patterns (review_guideline.md §3.5.3)

| Pattern | Detection rule |
|---|---|
| **Generality overclaim** | Claim scope > test scope by >1 level. E.g., "manipulation" claimed, 3 objects tested. |
| **Novelty overclaim** | Claim is "novel framework" but actual delta is "application to new domain". |
| **Comparison overclaim** | Claim "outperforms all baselines" but only tests on metrics where the paper's method wins. |
| **Learning overclaim** | "Robot learns to X" when robot executes a policy trained on X (attribution of agency). |
| **Robustness overclaim** | "Robust to perturbations" with only 3 perturbation types tested. |

For each pattern detected, record the specific quote from the paper and
the specific evidence that contradicts it.

### Step 7 — Persist

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'audit', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<audit_json>'
```

## Output format

```json
{
  "input": "arxiv:2501.12345" or "logs/minimal_run/",
  "venue_target": "RSS",
  "statistical_audit": {
    "trials_per_condition": 8,
    "mean_success_rate": 0.62,
    "std_across_seeds": 0.11,
    "ci_95": [0.51, 0.73],
    "venue_threshold_met": false,
    "severity": "serious"
  },
  "baselines": {
    "present": ["BC", "DiffusionPolicy"],
    "missing_by_category": {
      "simple": false,
      "sota": true,
      "oracle": true
    },
    "strongest_missing": {
      "name": "RT-2 fine-tuned",
      "year": 2024,
      "rationale": "Published 8 months before submission, same task class, cited 200+ times"
    }
  },
  "ablation": {
    "claimed_contribution": "tactile feedback",
    "ablation_row_present": true,
    "performance_drop_without": 0.02,
    "isolation_verdict": "weak",
    "backward_trigger": "t15"
  },
  "overclaiming": [
    {
      "pattern": "generality overclaim",
      "claimed": "manipulation of deformable objects",
      "tested": "3 cloth samples in 1 environment",
      "severity": "serious"
    }
  ],
  "overall_verdict": "serious weaknesses — 2 findings",
  "human_review_required": false
}
```

## Honesty protocol

You CAN assess with HIGH confidence:
- Trial counts (count them)
- Whether confidence intervals are reported
- Whether ablations remove the claimed contribution
- Whether baselines include simple/scripted/SOTA categories
- Statistical measures computed by `scripts/audit_stats.py`
- Claim scope vs. test scope (both are extractable from text)

You CAN assess with MODERATE confidence:
- Whether the "strongest missing baseline" you identified is actually
  stronger (search results suggest it, but you haven't run it)
- Whether the ablation is truly isolating the contribution (could be
  confounded)

You CANNOT assess:
- Whether a baseline is properly tuned (requires running it)
- Whether "human effort" is hidden (requires reviewer judgment)
- Whether statistical tests are appropriate for the data distribution
  (set `human_review_required=true` when in doubt)

## References

- `guidelines/doctrine/research_guideline.md` §8 — evaluation standards
- `guidelines/doctrine/review_guideline.md` §3.5 — validation attack vectors
- `guidelines/doctrine/review_guideline.md` §3.5.3 — overclaiming patterns
- `guidelines/spec/review_plan.md` §1.6 — experimental metrics and venue thresholds
- `scripts/audit_stats.py` — deterministic statistical audit CLI
