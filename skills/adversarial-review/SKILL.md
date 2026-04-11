---
name: adversarial-review
description: Full adversarial review at top-venue standard (RSS/CoRL/IJRR/T-RO). Graduated pressure, six attack vectors from review_guideline §3.1-3.6, mechanical verdict via metrics.verdict. Use to review, critique, audit a paper, or self-review a draft.
allowed-tools: Bash, Read, Write, Edit, Grep, Task
model: claude-opus-4-6
research_stages: [validate]
---

# Adversarial Review

## When to use
Invoked for full adversarial review at the standard of top robotics venues
(RSS, CoRL, IJRR, T-RO, ICRA, IROS). This is the largest and most
judgment-heavy skill in the system. It composes three sub-skills via the
`Task` tool:
- `concurrent-work-check` (for §3.1 scoop detection)
- `formalization-check` (for §3.2 formalization attack)
- `experiment-audit` (for §3.5 validation attack)

Maps to the VALIDATE stage of the research state machine (for self-review)
or to the review-agent workflow (for external paper review).

## The kill-chain (review_guideline.md §1.2)

Average reviewers score dimensions independently and average. Top
reviewers trace the **logical chain** and find where it breaks:

```
SIGNIFICANCE → FORMALIZATION → CHALLENGE → APPROACH → VALIDATION
```

One broken link is a structural flaw that no score-averaging can
compensate for. Search for breaks.

## Finding hierarchy (review_guideline.md §1.3)

- **Fatal** (any one → REJECT):
  - Broken link in the logical chain
  - Central claim unsupported by own evidence
  - Trivial variant of existing work
  - Evaluation does not test what was claimed
- **Serious** (accumulation → REJECT):
  - Missing critical baselines
  - Ablations don't isolate contribution
  - Overclaiming
  - Statistical insufficiency
  - Missing formal problem definition where demanded
- **Minor**:
  - Writing clarity, notation, figure quality
  - Missing tangential references

## Graduated pressure (review_plan.md §3)

### Iteration 1 — Structural scan (≈5 min budget)
Extract the logical chain. Quick fatal-flaw scan per Appendix A.1 of
`review_guideline.md`:
- Can you state the paper's contribution in one sentence?
- Is there a formal problem definition?
- Does the approach follow from the challenge?
- Is the central claim supported by experiments?
- Is this a trivial variant?

Stop on the first fatal flaw for first-pass efficiency. If none, proceed.

### Iteration 2 — Full review (≈30 min budget)
Apply ALL six attack vectors systematically (§3.1-3.6). Invoke sub-skills
for the deepest checks. Produce findings with severity classification.

### Iteration 3+ — Focused re-review
For each previous finding, track: `addressed | partially | not | regressed`.
Check for NEW weaknesses introduced by revisions. Regression check on
severity.

## Process

### Step 1 — Fetch the artifact

```bash
PYTHONPATH=src python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
import json, sys
c = fetch_and_extract(sys.argv[1])
print(json.dumps({
    'title': c.title,
    'abstract': c.abstract,
    'sections': c.sections,
    'extraction_quality': c.extraction_quality.overall,
    'math_preserved': c.extraction_quality.math_preserved,
}, indent=2, default=str))
" "<paper_id>"
```

If the artifact is a local draft, use `Read` directly.

### Step 2 — Iteration 1: extract the logical chain + quick scan

Extract each link of the chain as ONE sentence each:
- **Task** — what the robot does physically
- **Problem** — formal statement (or flag as absent)
- **Challenge** — the structural barrier (flag as absent or resource-complaint)
- **Approach** — the structural insight exploited
- **Contribution** — one sentence (reject "SOTA on X" as weak contribution)

Run the Appendix A.1 quick scan. If any check fails with severity fatal,
return early with that single finding.

### Step 3 — Iteration 2: apply all six attack vectors

#### §3.1 Attacking Significance (the "So What?" test)
- Hamming failure
- Consequence failure
- Durability failure
- Compounding failure
- Goal-vs-idea driven
- **Concurrent work test** — invoke `concurrent-work-check` via Task tool

#### §3.2 Attacking Formalization (the "Where's the Math?" test)
Invoke `formalization-check` via Task tool. Import its findings as
serious weaknesses if formalization level is `prose_only` at a top venue
or `absent` at any venue.

#### §3.3 Attacking the Challenge
- Resource complaint? → serious
- Challenge-approach disconnect? (If someone understood only the
  challenge, would they predict the method class?) → structural disconnect
- Challenge misidentification (evidence contradicts the claimed
  challenge)? → fatal
- Pre-solved challenge? → trigger `t12`
- Depth test (too vague)? → serious

#### §3.4 Attacking the Approach
- Method-shopping (method chosen for novelty, not challenge)?
- Trivial variant (Smith Category 4)?
- Structure exploitation (approach uses the formal structure)?
- Wrong mechanism (ablation shows contribution doesn't matter)? → trigger `t15`
- Theoretical justification gap?

#### §3.5 Attacking Validation
Invoke `experiment-audit` via Task tool. Fold its findings in:
- Baseline strength
- Missing baseline (name it)
- Ablation isolation
- Statistical sufficiency
- Cherry-picking
- Human effort hiding
- Robotics-specific: sim-only for real claims, single-embodiment
  generality, contact gap, sensing mismatch, environment simplification,
  failure severity, reproducibility, cycle time

#### §3.6 Attacking Novelty
- Prior work overlap
- Incremental engineering (no structural insight)?
- Missing related work (≥3 highly relevant) → serious
- Novelty vs. insight
- Combination vs. contribution

### Step 4 — Steel-man (≥3 sentences)

Per review_guideline.md §1.1, before attacking you must construct the
STRONGEST version of the paper's argument. Write 3-5 sentences that
re-express the paper's position "so clearly, vividly, and fairly that
the authors would say 'I wish I'd put it that way'" (RSS).

This is not optional. A review without a substantive steel-man is an
unfair review.

### Step 5 — Classify findings

For each finding produced in Iteration 2, classify:
- `severity: "fatal" | "serious" | "minor"`
- `attack_vector: "3.1" | "3.2" | ... | "3.6"`
- `what_is_wrong: str`
- `why_it_matters: str`
- `what_would_fix_it: str`
- `falsification: str` — "If the authors showed X, this critique would
  be invalidated"
- `grounding: str` — specific section/figure/equation reference
- `fixable: bool` — can this be addressed in a revision?
- `maps_to_trigger: "t2" | "t4" | ... | "t15" | null`

Vague findings are PROHIBITED. Every finding must be specific, grounded,
and falsifiable.

### Step 6 — Compute verdict MECHANICALLY

```bash
PYTHONPATH=src python -c "
from alpha_research.metrics.verdict import compute_verdict
from alpha_research.models.review import Finding, Severity
from alpha_research.models.blackboard import Venue
import json, sys

findings_json = json.loads(sys.argv[1])
findings = [Finding(**f) for f in findings_json]
venue = Venue[sys.argv[2]]
significance_score = int(sys.argv[3])

verdict = compute_verdict(findings, venue=venue, significance_score=significance_score)
print(json.dumps({'verdict': verdict.value if hasattr(verdict, 'value') else str(verdict)}))
" '<findings_json>' RSS 3
```

The verdict is computed per `review_plan.md §1.9`:
1. Any fatal → REJECT
2. Significance score ≤ 2 → REJECT
3. ≥3 unresolvable serious → REJECT
4. 0 serious → ACCEPT
5. ≤1 serious (fixable) → WEAK_ACCEPT
6. Venue-calibrated decision otherwise

**DO NOT** form a gestalt judgment. Use the mechanical output.

### Step 7 — Persist

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'review', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<review_json>'
```

## Output format

```json
{
  "artifact_id": "arxiv:2501.12345",
  "venue": "RSS",
  "iteration": 2,
  "chain_extraction": {
    "task": "...",
    "problem": "...",
    "challenge": "...",
    "approach": "...",
    "contribution": "...",
    "chain_complete": true,
    "broken_links": []
  },
  "steel_man": "The paper's central insight is that ... This is non-obvious because ... The experimental result on X genuinely demonstrates ...",
  "findings": {
    "fatal": [],
    "serious": [
      {
        "severity": "serious",
        "attack_vector": "3.5",
        "what_is_wrong": "Only 6 trials per condition reported in Table 2",
        "why_it_matters": "Below RSS threshold of 20; variance estimates are unreliable at this sample size",
        "what_would_fix_it": "Rerun with 20+ trials per condition and report 95% CI",
        "falsification": "If authors show CI [.55,.80] after rerunning with n=20, this concern is addressed",
        "grounding": "Table 2, §5.1",
        "fixable": true,
        "maps_to_trigger": null
      }
    ],
    "minor": []
  },
  "verdict": "weak_reject",
  "confidence": 4,
  "questions_for_authors": [
    "Please provide trial counts and CI for Table 2 results.",
    "Did you compare against RT-2 fine-tuned on your task? If not, why not?"
  ],
  "what_would_increase_score": "Address the missing RT-2 baseline AND provide ≥20 trials per condition with CI. Both fixes are feasible in a rebuttal period.",
  "anti_patterns_avoided": ["dimension_averaging", "false_balance", "novelty_fetishism"]
}
```

## Honesty protocol

You CAN assess with high confidence:
- Chain completeness (is each link present as text?)
- Claim-evidence alignment
- Baseline presence/absence
- Statistical sufficiency (count trials)
- Overclaiming patterns (text-level comparison of scope vs. tested)
- Missing related work relative to what's in your knowledge

You CANNOT assess:
- True significance (Hamming test — human)
- Formalization quality — delegate to `formalization-check` and flag
- Physical feasibility — flag for human
- Whether sim-to-real gap matters for THIS specific task
- True novelty against full field history

Anti-patterns to avoid (review_guideline.md §5.4):
- **Dimension averaging** — a fatal flaw is not compensated by high
  scores elsewhere
- **False balance** — do not manufacture weaknesses if none exist
- **Novelty fetishism** — novel insight from evaluating existing
  approaches is legitimate
- **Recency bias** — judge on depth, not trendiness
- **"Not how I would do it"** — reject only for flawed, not for different
- **Blanket rejection on single factors** — single weakness is fatal
  only if genuinely fatal
- **Punishing honest limitations** — reported limitations are strengths

## References

- `guidelines/doctrine/review_guideline.md` Part III — attack vectors §3.1-3.6 (primary)
- `guidelines/doctrine/review_guideline.md` Part IV — venue calibration
- `guidelines/doctrine/review_guideline.md` §5.4 — anti-patterns
- `guidelines/spec/review_plan.md` §1 — executable metrics for every finding
- `guidelines/spec/review_plan.md` §1.9 — verdict computation rules
- `guidelines/spec/review_plan.md` §3 — graduated pressure protocol
- `skills/concurrent-work-check/SKILL.md` — sub-skill
- `skills/formalization-check/SKILL.md` — sub-skill
- `skills/experiment-audit/SKILL.md` — sub-skill
