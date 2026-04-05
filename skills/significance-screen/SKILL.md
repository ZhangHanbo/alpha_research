---
name: significance-screen
description: Evaluate whether a research problem is worth pursuing. Applies Hamming, Consequence, Durability, and Compounding tests from research_guideline §2.2. Use for "is this significant?", "should I work on X?".
allowed-tools: Bash, Read, Write, Grep
model: claude-opus-4-6
---

# Significance Screen

## When to use
The researcher proposes a candidate problem and asks whether it's worth
committing months or years to. Maps to the SIGNIFICANCE stage of the
research state machine — the most commonly-skipped step in average research.
Your job is to ensure it does not get skipped.

## The four tests (from research_guideline.md §2.2)

### 1. Hamming Test — necessity
- Is the problem on the researcher's Hamming list of important unsolved
  problems? (Check `guidelines/hamming_list.md` if present.)
- Is there a reasonable attack? Importance requires BOTH (a) solution
  would matter AND (b) a viable path exists.
- Would solving it generate MORE interest over time, not less?
  (Sim-to-real for rigid pick-and-place is becoming LESS interesting as
  foundation models improve. Contact-rich manipulation under uncertainty
  is becoming MORE interesting.)

### 2. Consequence Test — impact
- If magically solved overnight, what concretely changes?
- Name a specific downstream system, capability, or understanding that
  improves.
- **REJECT "others would cite us" as not-an-answer.** Demand concreteness.

### 3. Durability Test
- Will a 10x bigger model or 10x more data trivially solve this in 24
  months? Does it require structural insight that resists scaling?
- Problems that resist scaling are good. Problems scaling will kill are
  bad bets.

### 4. Compounding Test — portfolio (Schulman)
- Does solving this enable OTHER research?
  - High-value: representations that transfer, formal frameworks, data
    infrastructure, safety guarantees.
  - Low-value: task-specific controllers, benchmark tweaks, marginal
    accuracy improvements.
- Is it goal-driven ("Problem Y is important, the bottleneck is Z,
  suggests method X") or idea-driven ("I have method X, let me find a
  problem")? Goal-driven wins.

## Process

### Step 1 — Find recent work on the problem
```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json, sys
query = sys.argv[1]
results = search_all(query, limit_per_source=15, year_lo=2023)
print(json.dumps([{
    'id': r.get('paperId'),
    'title': r['title'],
    'year': r['year'],
    'venue': r.get('venue',''),
    'citations': r.get('citationCount', 0),
    'doi': r.get('doi',''),
    'abstract': r.get('abstract','')[:400],
} for r in results[:20]], indent=2))
" "<problem_statement>"
```

### Step 2 — Fetch full text for the top 5 hits
For each of the top 5 by citation count or recency:
```bash
PYTHONPATH=src python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
import json, sys
c = fetch_and_extract(sys.argv[1])
print(json.dumps({
    'title': c.title,
    'abstract': c.abstract,
    'intro': c.sections.get('introduction', '')[:2000],
    'conclusion': c.sections.get('conclusion', '')[:1000],
    'quality': c.extraction_quality.overall,
}, indent=2))
" "<paper_id>"
```

### Step 3 — Impact trajectory check
For 2-3 seminal prior papers on the topic, check the citation trajectory:
```bash
PYTHONPATH=src python -c "
from alpha_review.apis import s2_citations
import json, sys
cites = s2_citations(sys.argv[1], limit=50)
by_year = {}
for c in cites:
    y = c.get('year', 0) or 0
    by_year[y] = by_year.get(y, 0) + 1
print(json.dumps(dict(sorted(by_year.items())), indent=2))
" "<seminal_paper_id>"
```

Is the trajectory rising (field moving toward) or falling (field moving on)?
Rising → Durability test favorable. Falling → caution.

### Step 4 — Check the researcher's Hamming list
```bash
if [ -f guidelines/hamming_list.md ]; then
    cat guidelines/hamming_list.md
else
    echo "NO_HAMMING_LIST_FOUND — flag for human to populate"
fi
```

Attempt to match the candidate problem against entries. Flag whether it
aligns with any listed problem.

### Step 5 — Check prior evaluations in project memory
```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import read_records
from pathlib import Path
import json, sys
records = read_records(Path(sys.argv[1]), 'significance_screen', limit=50)
print(json.dumps([{'problem': r.get('problem'), 'recommendation': r.get('overall_recommendation')} for r in records], indent=2))
" "<project_dir>"
```

If the problem has been screened before, consider the prior result.

### Step 6 — Score each test with evidence
For EACH of the four tests, produce:
- `score: int` (1-5, where 5 is strongest)
- `evidence: list[str]` (specific quotes, citation counts, trend data)
- `confidence: "high" | "medium" | "low"`
- `human_flag: bool` — TRUE if you cannot independently verify

### Step 7 — Write the result to project memory
```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'significance_screen', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<result_json>'
```

## Output format

```json
{
  "problem": "<the candidate problem statement>",
  "hamming": {
    "score": 4,
    "evidence": ["Listed in guidelines/hamming_list.md line 7", "Cited by 3 recent position papers"],
    "confidence": "medium",
    "human_flag": true
  },
  "consequence": {
    "score": 5,
    "evidence": ["If solved: enables autonomous assembly of consumer electronics without CAD — specific downstream system"],
    "confidence": "high",
    "human_flag": false
  },
  "durability": {
    "score": 4,
    "evidence": ["Requires structural insight (contact complementarity); unlikely to be solved by a larger VLA"],
    "confidence": "medium",
    "human_flag": true
  },
  "compounding": {
    "score": 4,
    "evidence": ["Produces a reusable tactile-alignment primitive that other manipulation tasks can consume"],
    "confidence": "medium",
    "human_flag": true
  },
  "concurrent_work_risk": "low",
  "motivation_type": "goal_driven",
  "overall_recommendation": "proceed with caveats",
  "human_checkpoint_required": true,
  "notes": "Hamming test always requires human confirmation; other tests are plausibility-checked from literature signal."
}
```

`overall_recommendation` is one of: `"proceed"`, `"proceed with caveats"`,
`"do not proceed"`. Require human checkpoint for anything above a clean
"do not proceed".

## Honesty protocol

You CANNOT judge actual significance — that requires the researcher's
Hamming list and field taste. Your job is to verify that significance
ARGUMENTS exist and are plausible, and to FLAG assessments that require
human judgment. **ALWAYS set `human_flag=true` for the Hamming test.**

Concrete, falsifiable consequence claims CAN be verified (set
`human_flag=false` when the paper or argument names a specific
downstream system, capability, or understanding that would change).

Durability assessment is moderate-confidence: citation-trajectory data
gives signal but not certainty.

## References

- `guidelines/research_guideline.md` §2.2 — significance tests (primary)
- `guidelines/review_guideline.md` §3.1 — significance attack vectors
- `guidelines/review_plan.md` §1.2 — significance metrics
- `guidelines/hamming_list.md` — the researcher's own list (if present)
