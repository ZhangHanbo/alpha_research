---
name: identify-method-gaps
description: Given a comparison table of methods within a solution class, identify what has not yet been tried. Surfaces coverage gaps, unexplored assumption relaxations, novel combinations. Sub-skill of the method-survey pipeline.
allowed-tools: Read
model: claude-sonnet-4-6
research_stages: [approach]
---

# Identify Method Gaps

## When to use
Invoked by the `method-survey` pipeline as its final judgment step.
Given a list of evaluated methods in a specific solution class (as
defined by a `challenge-articulate` output), identify what hasn't been
tried.

This is NOT the same as `gap-analysis`. `gap-analysis` operates across
an ENTIRE survey and looks for recurring weaknesses. `identify-method-gaps`
operates on a narrow comparison table WITHIN a solution class and looks
for unexplored regions of the method-design space.

This skill does NOT make tool calls — it reasons on provided input.

## Process

### Step 1 — Receive input
```json
{
  "challenge": {
    "statement": "Offline RL suffers from distributional shift",
    "type": "distribution_shift",
    "implied_solution_class": "Robust methods, conservative estimation, online adaptation"
  },
  "methods_surveyed": [
    {
      "paper_id": "arxiv:2020.xxx",
      "name": "CQL (Conservative Q-Learning)",
      "assumption": "penalize OOD actions in Q values",
      "performance": "SOTA on D4RL 2020",
      "complexity": "moderate",
      "code_released": true,
      "weaknesses_from_evaluation": ["hyperparameter sensitive", "slow"]
    },
    {
      "paper_id": "arxiv:2021.yyy",
      "name": "IQL (Implicit Q-Learning)",
      "assumption": "expectile regression avoids OOD queries entirely",
      "performance": "Competitive with CQL, simpler",
      "complexity": "low",
      "code_released": true,
      "weaknesses_from_evaluation": ["weaker on sparse rewards"]
    }
  ]
}
```

### Step 2 — Axis extraction

Extract the axes of variation across the methods:
- **Mechanism axis** — how does each method address the challenge?
  (penalty, constraint, avoidance, adaptation, ...)
- **Assumption axis** — what does each method assume? (reward density,
  data coverage, dynamics model, ...)
- **Objective axis** — what does each method optimize? (Q-value,
  advantage, policy likelihood, ...)
- **Computational axis** — complexity, train time, inference time
- **Evaluation axis** — which benchmarks, which tasks

### Step 3 — Gap identification

Walk through the axes and look for:

1. **Sparse regions**: Points in the method-design space where no
   method exists. For example, if all methods use penalty-based
   mechanisms, a constraint-based mechanism is a gap.

2. **Unrelaxed assumptions**: Assumptions that every method makes.
   An unrelaxed assumption is a potential research opportunity.
   Example: all offline RL methods assume i.i.d. data sampling — what
   about non-i.i.d.?

3. **Obvious combinations not yet attempted**: If methods A and B
   exist and have complementary strengths, has anyone tried A+B?

4. **Methods borrowing from adjacent solution classes**: Has anyone
   tried techniques from a different §2.7 challenge category? (e.g.,
   applying equivariance — typically used for sample complexity — to
   distribution shift)

5. **Assumptions that might not hold in practice**: Look at the
   weaknesses_from_evaluation field — if multiple methods fail on
   the same condition (e.g., "weak on sparse rewards"), that's a
   structural gap.

### Step 4 — Rank gaps by promise

For each identified gap, assess:
- **Feasibility**: Is there a plausible attack?
- **Novelty**: Has it been tried (even unsuccessfully)?
- **Payoff**: If it worked, would it dominate existing methods?

Rank gaps high → low. Report top 3-5.

### Step 5 — Produce output

## Output format

```json
{
  "challenge_id": "chal_abc123",
  "methods_analyzed": 12,
  "axes_of_variation": {
    "mechanism": ["penalty", "constraint", "avoidance", "adaptation"],
    "assumption_common": ["i.i.d. data", "markovian dynamics"],
    "objective": ["Q-value", "advantage", "policy likelihood"]
  },
  "identified_gaps": [
    {
      "description": "No method uses constraint-based mechanism for offline RL; all use penalty or avoidance",
      "axis": "mechanism",
      "type": "sparse_region",
      "feasibility": "high",
      "novelty": "high",
      "payoff": "moderate",
      "rank": 1,
      "rationale": "Constraint-based methods have succeeded in safe RL (CBFs, constrained MDPs). Transferring the framework to offline RL's distributional-shift problem is a natural but untried move."
    },
    {
      "description": "All surveyed methods assume i.i.d. data. Real logs from deployed policies are often non-i.i.d. (sequential, correlated)",
      "axis": "assumption",
      "type": "unrelaxed_assumption",
      "feasibility": "medium",
      "novelty": "medium",
      "payoff": "high",
      "rank": 2
    },
    {
      "description": "CQL and diffusion policies have never been combined; complementary strengths on exploration vs. multimodal behavior",
      "axis": "mechanism + policy_class",
      "type": "obvious_combination",
      "feasibility": "high",
      "novelty": "medium",
      "payoff": "moderate",
      "rank": 3
    }
  ],
  "suggested_direction": "Constraint-based offline RL via learned CBFs — combines the guarantees of constraint-based safe RL with the offline-data setting",
  "human_judgment_required": true,
  "notes": "Ranking is subjective — researcher should re-rank against their own taste and capabilities"
}
```

## Honesty protocol

You CAN identify:
- Coverage gaps in the comparison table (a region no listed method occupies)
- Assumptions shared by all methods
- Obvious combinations that literature searches did not turn up
- Recurring weaknesses across multiple methods

You CANNOT assess:
- Whether a gap is novel GLOBALLY (the survey may be incomplete —
  the `method-survey` pipeline was responsible for completeness)
- Whether a proposed direction will actually work
- Whether it aligns with the researcher's strategic priorities

**Always set `human_judgment_required=true`.** Your output is input
to the researcher's taste, not a replacement for it.

Watch your own pattern of "combination fetishism" — proposing A+B
just because neither paper has done it is cheap. A proposed combination
should have a principled reason to work (e.g., complementary failure
modes, not just "nobody has tried it").

## References

- `guidelines/doctrine/research_guideline.md` §2.7 — challenge → method class map
- `guidelines/doctrine/research_guideline.md` §11.2 — research taste (the
  "Prediction Exercise" and "Survival Exercise" apply here)
- `skills/challenge-articulate/SKILL.md` — the skill that produces the
  challenge classification this skill consumes
