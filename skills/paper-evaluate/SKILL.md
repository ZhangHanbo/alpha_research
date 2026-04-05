---
name: paper-evaluate
description: Evaluate a robotics paper against the Appendix B rubric (B.1-B.7). Produces scores with evidence, task chain, significance assessment, honesty flags. Use to evaluate, score, grade, or analyze a paper.
allowed-tools: Bash, Read, Write, Grep
model: claude-sonnet-4-6
---

# Paper Evaluate

## When to use
Invoked to evaluate a single paper against the research guideline's Appendix B
rubric. This is the canonical per-paper assessment skill — other skills
(`literature-survey` pipeline, `method-survey`, `gap-analysis`) invoke it in a
loop to populate `evaluations.jsonl`. Maps to the EVALUATE state in research
plan SM-3.

The rubric has seven dimensions (B.1-B.7), each scored 1-5 with evidence,
confidence, and an optional human-review flag.

## Process

### Step 1 — Fetch the paper (full text + metadata)
```bash
PYTHONPATH=src python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
from alpha_review.apis import s2_paper_details
import json, sys

paper_id = sys.argv[1]
paper = fetch_and_extract(paper_id)
meta = s2_paper_details(paper_id) or {}

print(json.dumps({
    'id': paper.arxiv_id or paper.s2_id or paper.doi or paper_id,
    'title': paper.title,
    'authors': paper.authors,
    'year': paper.year,
    'venue': paper.venue or meta.get('venue', ''),
    'abstract': paper.abstract,
    'sections': {k: v[:3000] for k, v in paper.sections.items()},
    'extraction_quality': {
        'overall': paper.extraction_quality.overall,
        'math_preserved': paper.extraction_quality.math_preserved,
        'sections_detected': paper.extraction_quality.sections_detected,
        'flagged_issues': paper.extraction_quality.flagged_issues,
    },
    'citation_count': meta.get('citationCount', 0),
}, indent=2, default=str))
" "<paper_id>"
```

Critical: check `extraction_quality.overall`. If it is `"abstract_only"` or
`"low"`, do NOT score dimensions that depend on the method or experiments
sections — mark them with `human_flag=true` and `confidence=low`.

### Step 2 — Skim pass (relevance + quality estimate)
Read title, abstract, and conclusion only. Produce:
- `relevance_score: float` (0.0 - 1.0, relative to the project's focus)
- `quality_tier: "high" | "medium" | "low"`
- `proceed_to_deep_read: bool`

If `proceed_to_deep_read` is False, write a minimal evaluation record with
only `relevance_score` populated and stop.

### Step 3 — Deep read + rubric scoring
For each of the seven B.1-B.7 dimensions, produce a RubricScore object:
- `score: int` (1-5)
- `confidence: "high" | "medium" | "low"`
- `evidence: list[str]` — quotes with section references, e.g.
  `"§4.2: 'we train on 3 objects in a single environment'"`
- `reasoning: str` — one sentence connecting evidence to score
- `human_flag: bool`

The seven dimensions:
- **B.1 Significance and Problem Definition** (weight: highest) — Hamming
  test, formal problem definition, structural challenge, one-sentence insight
- **B.2 Technical Approach** (high) — does the insight connect challenge to
  solution? Does it exploit formal structure?
- **B.3 Experimental Rigor** (high) — real robot, ≥10 trials, strong
  baselines, ablation isolation, failure analysis, perturbation tests
- **B.4 Representation and Sensing** (medium) — choice motivated by the
  task/challenge? Appropriate modalities?
- **B.5 Generalization and Compositionality** (medium) — tests beyond
  training distribution? Composes with other skills?
- **B.6 Practical Viability** (medium) — real-time, data-efficient,
  failure recovery, deployment path
- **B.7 Clarity and Reproducibility** (low-medium) — reimplementable from
  paper? code/data released?

### Step 4 — Extract the task chain
The task chain is the single most important extraction. Per `research_guideline.md` §2.1,
every strong paper follows:
```
SIGNIFICANCE → TASK → PROBLEM DEFINITION → CHALLENGE → APPROACH → SCOPE
```

Extract each link as one sentence:
- `task` — what the robot does physically
- `problem` — the formal problem structure (or null if prose-only)
- `challenge` — the structural barrier (NOT a resource complaint)
- `approach` — the structural insight exploited
- `one_sentence` — the one-sentence insight (NOT "we achieve SOTA on X")
- `chain_complete: bool` — are all five fields present?
- `chain_coherent: bool` — does approach follow from challenge follow from problem?

### Step 5 — Significance assessment (§2.2 tests)
- `hamming_score: 1-5` — independently reconstructable significance argument
  (HUMAN_FLAG always true — you cannot judge this without the researcher's
  own Hamming list)
- `concrete_consequence: str | null` — specific downstream system/capability
  that would improve. Reject "others would cite us" as not-an-answer.
- `durability_risk: "low" | "medium" | "high"` — does scaling solve this
  in 24 months?
- `compounding_value: "low" | "medium" | "high"` — does it enable other
  research?
- `motivation_type: "goal_driven" | "idea_driven" | "unclear"`

### Step 6 — Cross-check novelty against prior evaluations
```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import read_records
from pathlib import Path
import json, sys

project_dir = Path(sys.argv[1])
prior = read_records(project_dir, 'evaluation', limit=200)
# Simple title keyword overlap
title_kw = set(w for w in sys.argv[2].lower().split() if len(w) > 4)
related = [r for r in prior
           if title_kw & set(r.get('title','').lower().split())]
print(json.dumps(related[:5], indent=2))
" "<project_dir>" "<paper_title>"
```

Use the output to assess novelty relative to what we've already seen (not
absolute novelty).

### Step 7 — Persist
```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys

evaluation = json.loads(sys.stdin.read())
rid = append_record(Path(sys.argv[1]), 'evaluation', evaluation)
print(rid)
" "<project_dir>" <<< '<evaluation_json>'
```

## Output format

```json
{
  "paper_id": "arxiv:2501.12345",
  "title": "...",
  "authors": ["..."],
  "year": 2025,
  "venue": "RSS",
  "relevance_score": 0.85,
  "quality_tier": "high",
  "rubric_scores": {
    "B.1": {"score": 4, "confidence": "medium", "evidence": ["..."], "reasoning": "...", "human_flag": true},
    "B.2": {"score": 3, "confidence": "high", "evidence": ["..."], "reasoning": "...", "human_flag": false},
    "B.3": {"score": 2, "confidence": "high", "evidence": ["..."], "reasoning": "...", "human_flag": false},
    "B.4": {"score": 4, "confidence": "medium", "evidence": ["..."], "reasoning": "...", "human_flag": false},
    "B.5": {"score": 2, "confidence": "high", "evidence": ["..."], "reasoning": "...", "human_flag": false},
    "B.6": {"score": 3, "confidence": "low", "evidence": ["..."], "reasoning": "...", "human_flag": false},
    "B.7": {"score": 3, "confidence": "high", "evidence": ["..."], "reasoning": "...", "human_flag": false}
  },
  "task_chain": {
    "task": "Contact-rich assembly of rigid objects without CAD models",
    "problem": "min_π E[cost(s,a)] s.t. force-closure constraints, ...",
    "challenge": "Vision-only policies fail at sub-mm alignment",
    "approach": "GelSight tactile feedback closes the alignment loop",
    "one_sentence": "Tactile resolves what vision cannot at working distance",
    "chain_complete": true,
    "chain_coherent": true
  },
  "significance_assessment": {
    "hamming_score": 4,
    "concrete_consequence": "Enables assembly of consumer electronics without CAD",
    "durability_risk": "low",
    "compounding_value": "high",
    "motivation_type": "goal_driven",
    "human_flag": true
  },
  "extraction_limitations": [],
  "human_review_flags": ["significance", "formalization_quality"],
  "cross_check_notes": "Related to arxiv:2410.xxxxx — incremental extension"
}
```

## Honesty protocol

You CAN assess with high confidence:
- Presence or absence of a formal problem statement
- Number of trials per condition (count them)
- Whether baselines include simple/scripted comparisons
- Whether code/data is released
- Whether failure analysis section exists
- Task chain completeness (is each link present as text?)
- Claim-evidence alignment (do experiments test what's claimed?)

You CANNOT assess — always set `human_flag=true`:
- True significance (Hamming test requires the researcher's own field taste)
- Formalization quality (does the math capture the RIGHT structure?)
- Physical feasibility (requires embodied robot experience)
- True novelty against the full field history (requires deep field knowledge)
- Whether sim-to-real gap matters for THIS specific task

If `extraction_quality.overall` is `"low"` or `"abstract_only"`, mark the
affected dimensions with `confidence="low"` and add an entry to
`extraction_limitations`.

## References

- `guidelines/research_guideline.md` Appendix B — full rubric (B.1-B.7)
- `guidelines/research_guideline.md` §2.1 — the task chain
- `guidelines/research_guideline.md` §2.2 — significance tests
- `guidelines/review_plan.md` §1.1 — logical chain completeness metrics
- `skills/paper-evaluate/rubric.md` (companion file, to be added after approval)
