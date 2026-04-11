---
name: benchmark-survey
description: Survey the literature for benchmarks that measure progress on the project's formalized problem class. Extract standard metrics, published baseline numbers, saturation trends, and install recipes; rank candidates by coverage of the formalization's core challenge and non-saturation; produce a ranked proposal markdown the researcher uses to write benchmarks.md. Use in FORMALIZE before advancing to DIAGNOSE, or in APPROACH when scope-checking competitor benchmarks.
allowed-tools: Bash, Read, Write, Grep, WebFetch
model: claude-sonnet-4-6
research_stages: [formalization, approach]
---

# Benchmark Survey

## When to use

You're in FORMALIZE and the researcher is about to write `benchmarks.md`.
Or you're in APPROACH and you want to scope-check whether competitor
papers used benchmarks the researcher missed. This skill **surfaces and
ranks** candidate benchmarks; it does NOT select them. The human picks.

The forward guard `g2` (FORMALIZE → DIAGNOSE) requires `benchmarks.md`
to contain at least one benchmark under `## In scope` with a rationale,
success criterion, published baseline number, and saturation assessment.
That content comes from the human reading this skill's proposal and
writing the `benchmarks.md` by hand.

## Inputs

- `project.md` — the problem statement in prose
- `formalization.md` — the math; the observation/action space and
  constraint set are the matching keys for benchmark lookup
- Optional: `benchmark_proposal.md` from a prior run (for continuity)
- `state.json` — for `project_stage` in provenance

## Process

### Step 1 — Extract the problem class

Read `formalization.md` and summarize in one paragraph:

- What is the observation type? (RGB, RGB-D, point cloud, tactile, proprioception, multimodal)
- What is the action type? (joint position, torque, end-effector pose, discrete primitive, language)
- What is the task semantics? (manipulation / navigation / locomotion / HRI / ...)
- What is the info structure? (full observability, POMDP, multi-agent)
- What specific constraints distinguish this from the general case?

This summary is the search query vocabulary for Step 2.

### Step 2 — Query the literature for benchmark candidates

Use several sources, in order:

1. **Papers With Code leaderboards** — fetch pages matching the task
   semantics via `WebFetch` (only if the researcher has approved
   external network in their settings).
2. **`alpha_review.apis.search_all`** — literature search for
   "benchmark" + task-class keywords. Filter to papers that are
   primarily benchmark introductions, not method papers:

   ```bash
   PYTHONPATH=src python -c "
   from alpha_review.apis import search_all
   import json
   hits = search_all('benchmark <keyword> manipulation', limit=30)
   # Heuristic filter: title contains 'benchmark' | 'suite' | 'environment'
   keep = [h for h in hits if any(k in (h.title or '').lower() for k in ['benchmark', 'suite', 'environment', 'challenge'])]
   print(json.dumps(keep[:15], default=str, indent=2))
   "
   ```

3. **Survey papers and reviews** — search for "survey" + task-class;
   their "Benchmarks" sections are a rich source of cross-benchmark
   comparisons.

4. **Citation expansion** — for the top three benchmark papers found,
   use `alpha_review.apis.s2_citations` to find recent papers using the
   benchmark (measures community adoption).

### Step 3 — Extract per-benchmark metadata

For each candidate, read the benchmark paper (via `fetch_and_extract`)
and extract:

- **Task scope**: what exactly is being measured?
- **Observation / action spaces**: must match the formalization
- **Standard metrics**: the canonical columns on the leaderboard
- **Success criterion**: the exact definition of "success"
- **Published baselines with numbers**: at least 3 if the leaderboard
  is rich; cite paper + year + method + score + metric
- **Saturation trend**: compute the slope of top score vs year;
  "saturated" if top is within 5% of theoretical ceiling AND has plateau'd
- **Install recipe**: `pip`, `git clone`, `docker pull`, `conda env
  create -f ...`
- **Hardware requirements**: real robot? specific arm? GPU? sim only?
- **Community usage**: count recent (last 18 months) method papers
  reporting numbers on this benchmark

If extraction quality is low for a given benchmark paper, mark the
metadata as `UNKNOWN — extraction failed` rather than fabricating.

### Step 4 — Rank candidates

Score each candidate on four axes (1–5):

- **coverage**: does this benchmark exercise the formalization's core
  challenge? (5 = dead center; 1 = tangential)
- **non_saturation**: is there headroom for meaningful improvement?
  (5 = room to grow; 1 = saturated at 0.98+)
- **community_adoption**: how many recent papers report on it?
  (5 = >20 recent; 1 = <3)
- **install_effort**: how hard is it to get running? (5 = `pip install`;
  1 = requires a specific real-robot setup with non-standard hardware)

Weighted score: `coverage × 3 + non_saturation × 2 + community × 2 + install × 1`.

### Step 5 — Flag each candidate

Flag each candidate as one of:

- `RECOMMENDED_PRIMARY` — the researcher should use this as the primary benchmark
- `RECOMMENDED_SECONDARY` — include alongside the primary for generality claims
- `CONSIDER` — not strong enough to recommend but worth the human's attention
- `REJECT_SATURATED` — too saturated; published numbers are noise
- `REJECT_MISMATCHED` — observation/action space doesn't match the formalization
- `REJECT_ABANDONED` — no updates in 3+ years and no recent papers citing it

### Step 6 — Write the proposal

Emit `<project_dir>/benchmark_proposal.md` with this structure:

```markdown
# Benchmark Proposal — `<project_id>`

_Produced by the `benchmark-survey` skill at <timestamp>.
This is a recommendation, not a decision. Review, then write benchmarks.md._

## Problem class summary

<the one-paragraph summary from Step 1>

## Ranked candidates

### 1. <Benchmark name> — RECOMMENDED_PRIMARY (weighted score: X.X)

- **Coverage**: 5/5 — <why>
- **Non-saturation**: 4/5 — <why>
- **Community adoption**: 5/5 — <recent count>
- **Install effort**: 4/5 — <brief>
- **Published baselines**:
  - <Paper A, 2024> method: 0.62
  - <Paper B, 2025> method: 0.78 ← strongest prior
- **Success criterion**: <exact>
- **Why primary**: <one sentence>

### 2. <Benchmark name> — RECOMMENDED_SECONDARY ...

### 3. <Benchmark name> — CONSIDER ...

### Rejected

- <name>: REJECT_SATURATED — top is 0.99, asymptotic
- <name>: REJECT_MISMATCHED — no tactile observations, but formalization requires them

## Suggested structure for benchmarks.md

Copy-paste the RECOMMENDED entries into `benchmarks.md` under `## In scope`.
Include the rejected entries under `## Considered but rejected` with the
one-sentence "why not".
```

### Step 7 — Append the benchmark_survey record

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record, log_action
rec_id = append_record(
    '<project_dir>',
    'benchmark_survey',
    {
        'problem_class_summary': '<...>',
        'candidates_considered': <count>,
        'top_candidates': [
            {'name': '<name>', 'flag': 'RECOMMENDED_PRIMARY', 'weighted_score': 4.3, 'published_baselines': [...]},
            ...
        ],
        'proposal_path': 'benchmark_proposal.md',
        'human_confirmed': False,
    },
)
log_action(
    '<project_dir>',
    action_type='skill',
    action_name='benchmark-survey',
    project_stage='formalization',
    inputs=['project.md', 'formalization.md'],
    outputs=['benchmark_proposal.md', f'benchmark_survey.jsonl#{rec_id}'],
    summary='surveyed benchmarks; <N> candidates, <M> recommended',
)
"
```

### Step 8 — Await human confirmation

Tell the researcher:

```
✓ benchmark_proposal.md written (N candidates ranked)
Next steps:
  1. Read benchmark_proposal.md
  2. Choose your primary (and optional secondary) benchmark(s)
  3. Copy them into benchmarks.md under '## In scope' with rationale
  4. Once benchmarks.md has ≥1 entry, rerun this skill with --confirm to
     flip human_confirmed=true on the latest benchmark_survey record.
```

The `g2` forward guard requires the most-recent `benchmark_survey`
record to have `human_confirmed: true`. The researcher flips that
flag by either rerunning this skill with `--confirm` or editing the
JSONL directly.

## Honesty protocol

- You CAN detect whether a benchmark paper exists and extract its metadata.
- You CANNOT know whether the benchmark's notion of "success" aligns with
  what the researcher ultimately cares about. Set `human_flag: true` on
  every recommendation.
- You CANNOT verify that install instructions actually work on the
  researcher's system — set `install_verified: false` and let the
  researcher confirm.
- You CANNOT know compute budget constraints.
- If two benchmarks tie on weighted score, list both and let the human
  pick — do NOT break ties arbitrarily.

## References

- `guidelines/doctrine/research_guideline.md` §8 — evaluation standards
- `guidelines/doctrine/review_guideline.md` §3.5 — missing baseline and
  saturation attacks
- `guidelines/spec/review_plan.md` §1.6 — statistical sufficiency thresholds
- `guidelines/spec/implementation_plan.md` §III.2, §V.4 — FORMALIZE
  stage contract and benchmark-survey specification
