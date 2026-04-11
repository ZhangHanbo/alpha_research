---
name: challenge-articulate
description: From diagnosed failures, identify the structural barrier that resists current solutions. Applies three structural tests and classifies via research_guideline §2.7 challenge→approach table. Use for "what's the real challenge?".
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
research_stages: [challenge]
---

# Challenge Articulate

## When to use
The researcher has diagnosed specific failure modes (from `diagnose-system`)
and needs to identify the structural barrier underneath them. This is
where research taste lives. Maps to the CHALLENGE stage.

## The three structural tests (from research_guideline.md §2.5)

A well-articulated challenge must pass ALL THREE:

### Test 1 — Structural, not resource
A structural barrier, not a difficulty or resource complaint.
- BAD: "we need more data"
- GOOD: "the data distribution shifts when the policy changes, creating
  a non-stationary optimization problem"

### Test 2 — Constrains the solution class
The challenge should narrow the solution space dramatically. If any
method could "address" it, the challenge is not sharp enough.

### Test 3 — Predicts the method class
If someone understood ONLY the challenge, they should be able to predict
the method class (not the specific method, but the class) from the
`research_guideline.md` §2.7 table.

## The §2.7 challenge → method class map

| Challenge type | Suggested method class |
|---|---|
| Sample complexity | Better priors: equivariance, physics, sim pretraining, data augmentation |
| Distribution shift | Robust methods, online adaptation, domain randomization, conservative estimation |
| Combinatorial explosion | Abstraction, decomposition, hierarchy, guided search |
| Model uncertainty | Bayesian methods, ensembles, robust optimization, learning residuals |
| Sensing limitation | New sensors, multi-modal fusion, active/interactive perception |
| Hardware limitation | Co-design, compliance, mechanism design |
| Discontinuity | Contact-implicit methods, hybrid system formulations, smoothing |
| Long-horizon credit | Hierarchical policies, skill primitives, causal reasoning |
| Grounding gap | Grounded representations, affordances, physics sim as verifier |

## Process

### Step 1 — Load the diagnosis

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import read_records
from pathlib import Path
import json
recs = read_records(Path('<project_dir>'), 'diagnosis')
if recs:
    print(json.dumps(recs[-1], indent=2))
else:
    print('NO_DIAGNOSIS — run diagnose-system first')
"
```

If no diagnosis exists, stop and ask the user to run `diagnose-system` first.

### Step 2 — Propose 2-3 candidate challenges

For the `dominant_failure_mode` from the diagnosis, propose 2-3 candidate
structural explanations. For each:
- State in one sentence, structural, not a resource complaint
- Classify its type using the §2.7 table above
- Identify the implied solution class from the table

### Step 3 — Apply the three structural tests to each candidate

For each candidate, check:
1. Structural or resource complaint?
2. Constrains solution class?
3. Predicts method class? (Would another researcher, given only this
   challenge, predict the method class?)

Discard any candidate that fails any test.

### Step 4 — Search for how others articulate similar challenges

```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json, sys
results = search_all(sys.argv[1], limit_per_source=10, year_lo=2020)
results.sort(key=lambda r: r.get('citationCount', 0), reverse=True)
print(json.dumps([{
    'title': r['title'],
    'cites': r.get('citationCount', 0),
    'abstract': r.get('abstract','')[:400],
} for r in results[:5]], indent=2))
" "<challenge_keywords>"
```

For top hits, fetch full text and extract how they articulate the
challenge. Look for papers that already framed this exact structural
barrier in sharp terms — they are templates.

### Step 5 — Check for prior work already addressing this specific barrier

```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json
results = search_all('<specific_challenge_and_solution_keywords>', limit_per_source=10, year_lo=2023)
print(json.dumps([{'title': r['title'], 'year': r['year'], 'venue': r.get('venue','')} for r in results], indent=2))
"
```

If the specific structural barrier has been addressed by recent work, this
is trigger `t12` (backward to CHALLENGE re-articulation) or `t9` (scooped,
backward to SIGNIFICANCE).

### Step 6 — Persist the articulated challenge

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'challenge', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<challenge_json>'
```

## Output format

```json
{
  "diagnosis_id": "diag_abc123",
  "candidates": [
    {
      "statement": "Depth sensor resolution is fundamentally insufficient for the sub-mm alignment required by precision insertion",
      "type": "sensing_limitation",
      "implied_solution_class": "New sensors, multi-modal fusion, active/interactive perception",
      "passes_structural_test": true,
      "passes_narrowing_test": true,
      "passes_prediction_test": true,
      "discarded": false
    },
    {
      "statement": "We need more training data on small objects",
      "type": null,
      "discarded": true,
      "discard_reason": "resource complaint, not structural"
    }
  ],
  "selected_challenge": {
    "statement": "...",
    "type": "sensing_limitation",
    "implied_solution_class": "..."
  },
  "related_articulations": [
    {"title": "GelSight for precision insertion", "year": 2023, "cites": 150}
  ],
  "prior_work_addressing_specific_barrier": [],
  "backward_trigger": null,
  "human_review_required": true,
  "notes": "Selection of the 'right' challenge requires research taste; human must confirm"
}
```

`backward_trigger` is `"t12"` if all candidates fail the narrowing test,
`"t9"` if prior work has already addressed the specific challenge,
`"t6"` if the diagnosis evidence contradicts the challenge, otherwise null.

## Honesty protocol

Identifying the RIGHT structural barrier is where research taste lives.
You CAN enforce the three structural-test criteria mechanically. You
CAN propose candidates from the §2.7 table. You CAN detect when a
candidate is a resource complaint.

You CANNOT authoritatively name the "correct" challenge — that requires
the researcher's taste and deep knowledge of the problem's mechanics.
**Always set `human_review_required: true`** for the final selection.

## References

- `guidelines/doctrine/research_guideline.md` §2.5 — challenge analysis
- `guidelines/doctrine/research_guideline.md` §2.7 — challenge → approach table (primary)
- `guidelines/doctrine/review_guideline.md` §3.3 — challenge attack vectors
- `guidelines/spec/research_plan.md` — guards g3, g4; triggers t6, t12
