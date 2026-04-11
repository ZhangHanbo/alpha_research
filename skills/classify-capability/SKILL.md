---
name: classify-capability
description: "Classify a paper's demonstrated capability into the three-tier frontier (reliable/sometimes/can't-yet) from research_guideline §5.1 Axis 3. Small skill called in a loop by the frontier-mapping pipeline."
allowed-tools: Read
model: claude-sonnet-4-6
research_stages: [significance, validate]
---

# Classify Capability

## When to use
Invoked in a loop by the `frontier-mapping` pipeline — once per paper.
Given a single paper's task chain + reported success rate + scope of
evaluation, classify the demonstrated capability into one of three
tiers from `research_guideline.md` §5.1 Axis 3:

- **Reliable** — works consistently across objects, environments,
  conditions. Production-viable today. Examples (2026): pick-and-place
  of rigid objects; language-conditioned foundation-model manipulation
  for coarse tasks.
- **Sometimes** — works in demonstrated conditions but degrades off-
  distribution. Examples: deformable manipulation; tool use; multi-
  step with recovery; in-hand dexterity; bimanual; tactile-guided
  insertion.
- **Can't yet** — demonstrations are preliminary or the capability is
  not achieved. Examples: general unstructured manipulation; transparent/
  reflective objects; contact-rich with force reasoning at scale; long-
  horizon physical causal reasoning; human-level dexterity.

This skill does NOT make tool calls — it is pure reasoning on provided
input.

## Process

### Step 1 — Receive input
```json
{
  "paper_id": "arxiv:2501.12345",
  "task_chain": {
    "task": "Contact-rich peg-in-hole insertion of 3 object types",
    "problem": "...",
    "challenge": "...",
    "approach": "..."
  },
  "reported_results": {
    "success_rate": 0.85,
    "n_objects_tested": 3,
    "n_environments": 1,
    "real_robot": true,
    "perturbation_tested": false,
    "ablation_strong": true
  },
  "venue": "RSS",
  "year": 2025,
  "domain": "contact-rich manipulation"
}
```

### Step 2 — Apply classification heuristics

Work through these questions in order:

1. **Is there a demonstrated success rate in a realistic setting?**
   - No → `can't_yet`
   - Yes, but only in simulation for a task requiring real-world proof → `can't_yet`
   - Yes → continue

2. **Does the demonstration span diverse objects / environments / conditions?**
   - Single object in a single environment → `sometimes` (at best)
   - 3-10 objects in 1-2 environments → `sometimes`
   - 10+ objects, multiple environments, perturbation tests → potentially `reliable`

3. **Is the reported success rate ≥ 90% with confidence intervals?**
   - < 70% → `sometimes` (or `can't_yet` if < 50%)
   - 70-90% → `sometimes`
   - ≥ 90% with CI → potentially `reliable`

4. **Has the capability been independently reproduced by other groups?**
   - (Inferable from citations + follow-up papers in the same domain)
   - No independent reproduction → max tier is `sometimes`
   - Multiple groups reporting similar results → `reliable` possible

5. **Are there known "can't-yet" capabilities from `research_guideline.md`
   §5.1 Axis 3 that overlap with this task?**
   - If yes, default to `sometimes` or `can't_yet` unless evidence is
     overwhelming

### Step 3 — Produce output

## Output format

```json
{
  "paper_id": "arxiv:2501.12345",
  "capability_description": "Contact-rich peg-in-hole insertion (3 peg types)",
  "tier": "sometimes",
  "evidence": [
    "Success rate 85% on 3 objects, single environment (§5.1 of paper)",
    "No perturbation tests reported",
    "Single-group result, no independent reproduction"
  ],
  "rationale": "Reported in a realistic setting with reasonable success but demonstration scope is narrow: 3 objects, 1 environment, no perturbation tests. Meets 'sometimes' criteria but falls short of 'reliable' which requires diverse conditions and independent reproduction.",
  "confidence": "high",
  "boundary_notes": "If authors extend evaluation to 10+ objects with perturbation, upgrade to borderline reliable."
}
```

`tier` is one of `"reliable"`, `"sometimes"`, `"can't_yet"`.

`confidence` indicates how confident the classification is:
- `high` — clear-cut case, fits the heuristics well
- `medium` — borderline between two tiers
- `low` — insufficient data to classify; caller should flag for human

## Honesty protocol

You CAN classify with reasonable confidence based on the reported scope
and success rate alone. This is a LIGHTWEIGHT skill — the frontier-mapping
pipeline calls you many times and aggregates the results. It is not
a substitute for the researcher's own judgment of the field.

You CANNOT assess:
- Whether the paper's reported success rate is calibrated correctly
  (maybe they cherry-picked)
- Whether the task is representative of the capability class
- Whether "sometimes" in 2025 will become "reliable" in 2027 (the
  frontier moves — this is a snapshot)

When in doubt between two tiers, pick the more conservative (`can't_yet`
or `sometimes` rather than `reliable`). False-positive "reliable" claims
are more damaging to the frontier map than conservative "sometimes"
claims.

## References

- `guidelines/doctrine/research_guideline.md` §5.1 Axis 3 — capability frontier
  (primary source for tier definitions)
- `guidelines/doctrine/research_guideline.md` §1.5 — the long tail of the physical
  world (context for why "sometimes" is a large category)
