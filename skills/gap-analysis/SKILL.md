---
name: gap-analysis
description: Identify recurring limitations and research opportunities across a body of evaluated papers. Semantic clustering of weaknesses, Hamming-list cross-reference, direction proposals. Use for "what are the open problems?", "where are the gaps?".
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
research_stages: [significance]
---

# Gap Analysis

## When to use
Invoked after a literature survey has produced a body of `evaluation`
records (typically 20-100 papers). Your job is to aggregate the weaknesses
across those papers, identify recurring limitations, and propose research
directions that address real gaps rather than artifacts of missed papers.

Maps to `research_guideline.md` §5.1 Axis 1 (Bottleneck Diagnosis) and is
invoked by the `literature-survey` pipeline as its synthesis step.

## Process

### Step 1 — Aggregate evaluations from project memory

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import read_records
from pathlib import Path
import json, sys

project_dir = Path(sys.argv[1])
records = read_records(project_dir, 'evaluation', limit=500)
print(json.dumps({
    'total': len(records),
    'with_weaknesses': sum(1 for r in records if r.get('rubric_scores', {}).get('B.3', {}).get('score', 5) < 4),
    'papers': [
        {
            'id': r.get('paper_id'),
            'title': r.get('title'),
            'weaknesses': r.get('human_review_flags', []),
            'rubric_b3': r.get('rubric_scores', {}).get('B.3', {}).get('evidence', []),
            'rubric_b5': r.get('rubric_scores', {}).get('B.5', {}).get('evidence', []),
            'task_chain': r.get('task_chain', {}),
        }
        for r in records
    ]
}, indent=2))
" "<project_dir>"
```

If there are fewer than 10 evaluations, stop and warn: gap analysis
requires a sufficient sample. Direct the user to run `literature-survey`
first.

### Step 2 — Semantic clustering of weaknesses

This is the LLM-reasoning heart of the skill. Two papers saying "limited
by the lack of depth resolution" and "struggles with thin objects" are
expressing the SAME gap in different words. A deterministic string match
would miss this. Your job is to group semantically-equivalent limitations.

For each weakness mentioned in any evaluation, group it under one of
these candidate categories (or propose a new category):
- Sensing limitations (resolution, modality, calibration)
- Data / sample complexity
- Formalization absent or inadequate
- Sim-to-real gap
- Single-embodiment / narrow task coverage
- Real-time / deployment viability
- Failure recovery / long-horizon robustness
- Safety guarantees
- Reproducibility / human-effort hiding
- Contact modeling
- Grounding gap (semantic vs physical)

Track how many papers each cluster appears in. A gap that appears in ≥3
papers is a **candidate recurring limitation**.

### Step 3 — Verify each candidate gap is REAL (not missed papers)

For each candidate recurring limitation:
```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json, sys
results = search_all(sys.argv[1], limit_per_source=10, year_lo=2023)
print(json.dumps([{
    'title': r['title'],
    'year': r['year'],
    'abstract': r.get('abstract','')[:300],
} for r in results[:5]], indent=2))
" "<gap description + keyword>"
```

If the search turns up recent papers that explicitly address the gap,
it's not a real gap — it's a missed-paper artifact in the survey. Drop
the candidate (but note it so the survey can be expanded).

### Step 4 — Cross-reference with the Hamming list

```bash
if [ -f guidelines/hamming_list.md ]; then
    cat guidelines/hamming_list.md
else
    echo "NO_HAMMING_LIST — unable to cross-reference"
fi
```

For each verified gap, check whether it corresponds to an item on the
researcher's Hamming list. High-alignment gaps are high-priority.

### Step 5 — Propose research directions

For each verified recurring limitation, propose 1-2 research directions.
Each direction must:
- Have a concrete problem statement
- Cite which papers motivated it (≥3 papers from the clusters)
- Apply a lightweight significance check (consequence, durability,
  compounding)
- Flag as `human_judgment_required=true` for the Hamming test

Do NOT invoke the full `significance-screen` skill for each proposal —
that's the researcher's next step. Produce lightweight scaffolding for
their review.

### Step 6 — Persist

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'gap_report', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<report_json>'
```

## Output format

```json
{
  "project_dir": "output/tactile_survey",
  "papers_analyzed": 47,
  "analysis_date": "2026-04-05",
  "recurring_limitations": [
    {
      "cluster": "sensing — sub-mm depth resolution insufficient for precision tasks",
      "papers_count": 8,
      "supporting_papers": ["arxiv:2403.xxx", "arxiv:2404.yyy", "arxiv:2409.zzz"],
      "verified_real_gap": true,
      "verification_note": "Searched 'sub-mm depth RGBD robotics' — no recent paper addresses this specific limitation",
      "hamming_list_match": "problem #7 in guidelines/hamming_list.md"
    },
    {
      "cluster": "failure recovery — no paper in the cluster reports recovery from perception failures",
      "papers_count": 12,
      "supporting_papers": ["..."],
      "verified_real_gap": true,
      "hamming_list_match": null
    }
  ],
  "dropped_candidates": [
    {
      "cluster": "offline RL for manipulation",
      "papers_count": 4,
      "dropped_reason": "Recent paper arxiv:2501.xxx explicitly addresses this; our survey missed it"
    }
  ],
  "proposed_directions": [
    {
      "title": "Active depth-modality switching for precision manipulation",
      "problem_statement": "Current manipulation pipelines use fixed RGB-D; they fail on sub-mm features. Propose active switching between RGB-D and tactile/confocal depending on task phase.",
      "motivating_papers": ["arxiv:2403.xxx", "arxiv:2404.yyy", "arxiv:2409.zzz"],
      "consequence_sketch": "Enables precision insertion on objects where fixed depth fails today",
      "durability_sketch": "Structural (sensing physics), not solvable by scale",
      "compounding_sketch": "Active sensing primitive reusable across tasks",
      "human_judgment_required": true
    }
  ],
  "coverage_recommendations": [
    "Expand survey to include the 4 missed papers on offline RL",
    "Run literature-survey with additional query: 'active perception robotics'"
  ]
}
```

## Honesty protocol

You CAN assess:
- Frequency of a limitation across papers (count the clusters)
- Whether a candidate gap has been addressed by a specific recent paper
  (via search)
- Whether a proposed direction has a concrete problem statement

You CANNOT assess:
- True significance of a proposed direction (Hamming test — human)
- Whether the clustering correctly groups semantically equivalent
  weaknesses (you are the one clustering, and you may miss subtleties)
- Whether the researcher cares about a particular gap (their priorities
  are theirs to set)

**Always flag every proposed direction with
`human_judgment_required=true`.** Your proposals are candidates for the
researcher's consideration, not authoritative recommendations.

Watch for your own bias: if your clustering is too coarse, you'll
collapse distinct gaps; too fine and you'll report trivial differences
as separate gaps. When in doubt, report both the fine and coarse views
and let the human choose.

## References

- `guidelines/doctrine/research_guideline.md` §5.1 Axis 1 — bottleneck diagnosis
- `guidelines/doctrine/research_guideline.md` §2.2 — significance tests (lightweight
  application to proposed directions)
- `guidelines/doctrine/review_guideline.md` §3.3 — challenge attack (for what makes
  a gap "structural" vs "resource")
- `guidelines/hamming_list.md` — the researcher's own list (if present)
