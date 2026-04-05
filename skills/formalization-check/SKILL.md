---
name: formalization-check
description: Assess whether a problem has a proper formal math definition. Detects formalization level, identifies framework (MDP/POMDP/opt/Bayesian), extracts objective/variables/constraints, verifies properties via sympy. Use for "is this well-formalized?".
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
---

# Formalization Check

## When to use
Applied to a paper, a proposed problem, or the researcher's own draft. Maps
to the FORMALIZE stage of the research state machine and to review attack
vectors §3.2.

Per Tedrake: *"If you can't write the math, you do not understand the
problem."* Your job is to enforce this standard — detect absence of formal
statements, classify the framework when present, and check whether
claimed mathematical properties hold up under symbolic verification.

## Process

### Step 1 — Obtain the problem statement

If input is a paper:
```bash
PYTHONPATH=src python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
import json, sys
c = fetch_and_extract(sys.argv[1])
print(json.dumps({
    'abstract': c.abstract,
    'intro': c.sections.get('introduction', '')[:3000],
    'problem': c.sections.get('problem', '') or c.sections.get('preliminaries', ''),
    'method': c.sections.get('method', '')[:2000],
    'quality': c.extraction_quality.overall,
    'math_preserved': c.extraction_quality.math_preserved,
}, indent=2))
" "<paper_id>"
```

If input is the researcher's own draft, use `Read` on the markdown/tex file
directly.

**Critical**: if `extraction_quality.math_preserved == false`, you are
reading a version of the paper where LaTeX math was garbled during PDF
extraction. In that case, flag ALL formalization assessments as low
confidence and recommend re-fetching via ar5iv HTML or the arxiv source.

### Step 2 — Classify the formalization level

Read the problem statement and classify:
- **`formal_math`** — explicit objective function, variables, constraints,
  and information structure written as mathematics
- **`semi_formal`** — some mathematical notation but key pieces are in prose
- **`prose_only`** — English description with no mathematical objects
- **`absent`** — no attempt at a formal problem statement

### Step 3 — If math is present, extract the structure

For `formal_math` or `semi_formal`, identify:
- **Framework**: MDP, POMDP, constrained optimization, Bayesian inference,
  dynamical system, hybrid system, game, SDE, contact-implicit, other
- **Objective function**: what is being optimized / estimated / decided?
- **Decision variables**: what does the agent choose?
- **Constraints**: what restricts the feasible set?
- **Information structure**: what is observable, what is known a priori,
  what is stochastic?
- **Exploited structure**: convexity, symmetries (SE(3), permutation, time
  invariance), decomposability, sparsity, low-dimensional manifolds,
  Lyapunov structure, contact complementarity, equivariance

### Step 4 — Check framework-reality fit

Common mismatches to flag:
- MDP used when the problem has partial observability → should be POMDP (t7)
- Deterministic formulation for stochastic dynamics
- Continuous formulation for a problem with hybrid contact switching
- Quasi-static when dynamics matter (acceleration-dependent slip)
- Convex relaxation whose violated original constraints matter in practice (t10)

### Step 5 — Optional sympy verification

If the paper claims specific mathematical properties (convexity, smoothness,
gradient form, closed-form solution), verify via `scripts/sympy_verify.py`:

```bash
python scripts/sympy_verify.py \
    --expr "(x - 2*y)**2 + exp(x)" \
    --property convex \
    --vars "x,y"
```

Supported properties: `convex`, `concave`, `differentiable`. Output is JSON
with `{result: true|false|"unknown", reason: "..."}`.

Report whether the sympy check agreed with the paper's claim. "Unknown" is
not a failure — it means symbolic proof was not tractable, a human may
need to verify manually.

### Step 6 — Search for alternative formalizations

```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json, sys
results = search_all(sys.argv[1], limit_per_source=10, year_lo=2020)
print(json.dumps([{
    'title': r['title'],
    'year': r['year'],
    'abstract': r.get('abstract','')[:300],
} for r in results[:10]], indent=2))
" "<framework> <problem keywords>"
```

Compare how other papers formalize similar problems. If most use a
different framework, note the discrepancy — this is signal for the human.

### Step 7 — Persist the result

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'formalization_check', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<result_json>'
```

## Output format

```json
{
  "input": "arxiv:2501.12345" or "local:draft.md",
  "level": "formal_math | semi_formal | prose_only | absent",
  "framework": "MDP | POMDP | constrained_opt | Bayesian | hybrid_system | ...",
  "objective": "Maximize P(success | g, z) over grasp candidates g",
  "decision_variables": ["grasp pose g ∈ SE(3)", "gripper width w"],
  "constraints": ["kinematic reachability", "collision avoidance", "force closure"],
  "information_structure": "Observable: RGB-D image z. Unknown: object mass, friction",
  "exploited_structure": ["SE(3) equivariance", "contact complementarity"],
  "assumptions": ["quasi-static", "rigid objects", "known camera extrinsics"],
  "framework_mismatch": "none | minor | major",
  "mismatch_details": "",
  "sympy_verification": {
    "run": true,
    "expression": "...",
    "property": "convex",
    "result": true,
    "reason": "Hessian PSD"
  },
  "alternative_formalizations_found": [
    {"title": "...", "framework": "POMDP", "year": 2024}
  ],
  "confidence": "high | medium | low",
  "human_flag": true,
  "notes": "formalization quality requires human math intuition"
}
```

## Honesty protocol

You CAN detect with HIGH confidence:
- Presence or absence of mathematical notation
- Presence or absence of a formal problem statement
- Whether the paper names an objective function, variables, constraints
- Whether the paper identifies exploited structure
- Whether a claimed property holds under sympy symbolic check

You CANNOT deeply judge — ALWAYS set `human_flag=true`:
- Whether the formalization captures the RIGHT structure
- Whether the framework choice is optimal for the problem
- Whether assumed invariants actually hold in the real system
- Whether an alternative framework would be strictly better

Provide strong signal. Defer final judgment.

## References

- `guidelines/research_guideline.md` §2.4 — formalization standards (primary)
- `guidelines/research_guideline.md` §3.1 — mathematical structure
- `guidelines/review_guideline.md` §3.2 — formalization attack vectors
- `guidelines/review_plan.md` §1.3 — formalization metrics
- `scripts/sympy_verify.py` — symbolic property verification CLI
