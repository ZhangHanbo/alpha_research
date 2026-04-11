---
name: concurrent-work-check
description: Detect whether a research problem has been solved by concurrent or recent work. Multi-query search, citation-graph expansion, pairwise comparison. Use for "has anyone done this?", "what concurrent work exists?", scooping risk checks.
allowed-tools: Bash, Read, Write
model: claude-sonnet-4-6
research_stages: [challenge, approach, validate]
---

# Concurrent Work Check

## When to use
Invoked in three situations:
1. Before committing to a research direction (part of `significance-screen`)
2. As a sub-skill called by `adversarial-review` to check §3.1 concurrent
   work attack vector
3. Periodically during the APPROACH stage to catch scooping risk

Maps to `research_guideline.md` §2.2 concurrent work test and §2.6 why-now,
and to backward triggers `t9` (scooped → SIGNIFICANCE) and `t5` (trivial
variant → SIGNIFICANCE).

## Process

### Step 1 — Receive the input
Inputs:
- `problem_statement: str` — what the research does
- `approach_summary: str` — how it does it
- `key_technical_terms: list[str]` — 3-5 specific terms (algorithms,
  benchmarks, sensors, task names)
- `time_window: str` — typically `"18m"` for scooping risk, `"5y"` for
  broader landscape
- `project_dir: Path` — for persisting the report

### Step 2 — Multi-angle search

Generate 3-5 query formulations from the inputs. A paper searched by only
its title keywords will miss scoops that used different terminology.

```bash
PYTHONPATH=src python -c "
from alpha_review.apis import search_all
import json, sys

queries = [
    sys.argv[1],  # problem statement
    sys.argv[2],  # approach summary
    sys.argv[3],  # key technical terms joined
]

all_results = {}
for q in queries:
    results = search_all(q, limit_per_source=10, year_lo=2024)
    for r in results:
        pid = r.get('paperId') or r.get('doi')
        if pid and pid not in all_results:
            all_results[pid] = {
                'query': q,
                'title': r['title'],
                'year': r['year'],
                'venue': r.get('venue',''),
                'cites': r.get('citationCount', 0),
                'abstract': r.get('abstract','')[:400],
                'doi': r.get('doi',''),
            }
print(json.dumps(list(all_results.values()), indent=2))
" "<problem>" "<approach>" "<key terms>"
```

### Step 3 — Citation-graph expansion

For the top 3 most-cited hits, traverse the citation graph to find papers
the first search missed:
```bash
PYTHONPATH=src python -c "
from alpha_review.apis import s2_references, s2_citations
import json, sys
pid = sys.argv[1]
refs = s2_references(pid, limit=20)
cites = s2_citations(pid, limit=20)
print(json.dumps({
    'references': [{'title': r['title'], 'year': r['year']} for r in refs],
    'citations': [{'title': c['title'], 'year': c['year']} for c in cites],
}, indent=2))
" "<top_hit_id>"
```

Look for papers in either list that also match the problem/approach
terminology.

### Step 4 — Google Scholar fallback (last resort)

Scholar rate-limits aggressively (8-15s between requests, 60-request
session cap) and requires `bs4` (may not be installed). Use only when
steps 2-3 didn't yield enough candidates:

```bash
PYTHONPATH=src python -c "
try:
    from alpha_review.scholar import scholar_search_papers
    import json, sys
    papers, avg_rel = scholar_search_papers(sys.argv[1], max_pages=1)
    print(json.dumps({'papers': papers, 'avg_relevance': avg_rel}, indent=2))
except ImportError as e:
    print(json.dumps({'error': f'scholar not available: {e}'}))
" "<problem_statement>"
```

If `bs4` is not installed, skip this step and note it in the report.

### Step 5 — Fetch full text for high-overlap candidates

For the top 3 candidates by apparent overlap (based on abstract), fetch
and read the full text:
```bash
PYTHONPATH=src python -c "
from alpha_research.tools.paper_fetch import fetch_and_extract
import json, sys
c = fetch_and_extract(sys.argv[1])
print(json.dumps({
    'title': c.title,
    'abstract': c.abstract,
    'intro': c.sections.get('introduction', '')[:2500],
    'method': c.sections.get('method', '')[:2000],
    'experiments': c.sections.get('experiments', '')[:1500],
    'quality': c.extraction_quality.overall,
}, indent=2))
" "<candidate_id>"
```

### Step 6 — Pairwise comparison

For each candidate, assess along three dimensions:
- **Problem overlap**: does the candidate solve the same problem?
  (not just adjacent)
- **Approach overlap**: does the candidate use a similar approach class?
- **Scope overlap**: similar benchmarks, similar evaluation conditions?

Assign an overall overlap degree:
- **none** — unrelated
- **minor** — same sub-area, different problem or approach
- **significant** — same problem but different approach (differentiable
  via the structural insight)
- **scooped** — same problem, same approach, published / submitted first

### Step 7 — Produce differentiation plan (if significant overlap)

If any candidate hits `significant` or `scooped`:
- Name the specific structural differentiator (what your work does that
  theirs does not, or vice versa)
- If no differentiator exists, trigger `t5` or `t9` (backward to
  SIGNIFICANCE)

### Step 8 — Persist

```bash
PYTHONPATH=src python -c "
from alpha_research.records.jsonl import append_record
from pathlib import Path
import json, sys
rid = append_record(Path(sys.argv[1]), 'concurrent_work', json.loads(sys.stdin.read()))
print(rid)
" "<project_dir>" <<< '<report_json>'
```

## Output format

```json
{
  "input": {
    "problem_statement": "...",
    "approach_summary": "...",
    "key_technical_terms": ["GelSight", "contact-implicit MPC", "peg-in-hole"]
  },
  "queries_run": [
    "contact-rich peg insertion tactile",
    "GelSight MPC",
    "learned tactile impedance control"
  ],
  "candidates_found": 23,
  "overlap_analysis": [
    {
      "id": "arxiv:2403.xxxxx",
      "title": "...",
      "year": 2024,
      "venue": "CoRL",
      "problem_overlap": "significant",
      "approach_overlap": "minor",
      "scope_overlap": "significant",
      "overall_degree": "significant",
      "differentiator": "Their approach uses fixed impedance; ours adapts online from tactile signal"
    },
    {
      "id": "arxiv:2411.yyyyy",
      "title": "...",
      "overall_degree": "scooped",
      "differentiator": null,
      "rationale": "Same problem, same approach class, published 3 months before our planned submission"
    }
  ],
  "scholar_consulted": false,
  "scholar_error": "bs4 not installed in environment",
  "overall_risk": "scooped",
  "backward_trigger": "t9",
  "differentiation_plan_required": true,
  "recommendations": [
    "Retreat to SIGNIFICANCE stage and re-scope the problem",
    "OR: differentiate via dynamic impedance adaptation (our unique angle)"
  ],
  "human_review_required": true
}
```

`overall_risk` is the MAX overlap degree across all candidates.
`backward_trigger` is set if `overall_risk` is `scooped` (t9) or
`significant` with no viable differentiator (t5).

## Honesty protocol

You CAN assess with moderate confidence:
- Lexical overlap between abstracts
- Author overlap (indicates same group's extension)
- Venue match
- Publication dates
- Whether two papers use the same benchmark / dataset

You CANNOT assess with high confidence:
- True scientific overlap (requires reading both papers carefully — a
  similar-sounding title can mask different contributions)
- Whether a differentiator is genuinely meaningful
- Whether the reviewer's interpretation of "scooping" matches the
  researcher's own threshold for concern

**Always set `human_review_required=true`** when `overall_risk` is
`significant` or above. The researcher must make the final call.

Note: `scholar_search_papers` requires `bs4` which may not be installed.
If unavailable, note it — the other sources (OpenAlex/S2/ArXiv) cover
the bulk of the literature and are usually sufficient.

## References

- `guidelines/doctrine/research_guideline.md` §2.2 — concurrent work test
- `guidelines/doctrine/research_guideline.md` §2.6 — why-now timing
- `guidelines/doctrine/review_guideline.md` §3.1 — concurrent work attack vector
- `guidelines/spec/research_plan.md` — backward triggers t5, t9
