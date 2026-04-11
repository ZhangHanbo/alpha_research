# Test Report — `test_model_research`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 11 total — **11 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `full task chain has completeness 1.0`

**Result**: ✅ PASS
**Purpose**: TaskChain.compute_completeness counts populated fields / 5.

**Inputs**:
```
{
  "task": "Pick deformable objects",
  "problem": "Unknown dynamics",
  "challenge": "Contact discontinuities",
  "approach": "Tactile servoing",
  "one_sentence": "Tactile feedback enables sub-mm alignment",
  "chain_complete": true,
  "chain_coherent": true
}
```

**Expected**:
```
{
  "completeness": 1.0,
  "broken_links": []
}
```

**Actual**:
```
{
  "completeness": 1.0,
  "broken_links": []
}
```

**Conclusion**: A complete chain gates forward stage transitions (g2, g3, g4).

---

## Case 2: `partial chain lists broken links`

**Result**: ✅ PASS
**Purpose**: compute_completeness + broken_links identify the missing chain fields.

**Inputs**:
```
{
  "task": "Pick",
  "problem": "Grasp"
}
```

**Expected**:
```
{
  "completeness": 0.4,
  "broken_links_contains": [
    "challenge",
    "approach",
    "one_sentence"
  ]
}
```

**Actual**:
```
{
  "completeness": 0.4,
  "broken_links": [
    "challenge",
    "approach",
    "one_sentence"
  ]
}
```

**Conclusion**: Broken links drive diagnostic skills that prompt the researcher to fill the gap.

---

## Case 3: `rubric score must be in [1, 5]`

**Result**: ✅ PASS
**Purpose**: Pydantic enforces Field(ge=1, le=5) on RubricScore.score.

**Inputs**:
```
{
  "valid": 4,
  "invalid_low": 0,
  "invalid_high": 6
}
```

**Expected**:
```
{
  "valid_accepted": true,
  "low_rejected": true,
  "high_rejected": true
}
```

**Actual**:
```
{
  "valid_accepted": true,
  "low_rejected": true,
  "high_rejected": true
}
```

**Conclusion**: The 1–5 scale matches Appendix B of the research guideline.

---

## Case 4: `Paper.primary_id prefers arxiv_id > s2_id > doi > title`

**Result**: ✅ PASS
**Purpose**: Verify the fallback chain for a paper identifier.

**Inputs**:
```
[
  {
    "arxiv_id": "2401.00001",
    "s2_id": "s2x",
    "doi": "10.0/x"
  },
  {
    "s2_id": "s2x"
  },
  {
    "title only": true
  }
]
```

**Expected**:
```
[
  "2401.00001",
  "s2x",
  "Just a Title"
]
```

**Actual**:
```
[
  "2401.00001",
  "s2x",
  "Just a Title"
]
```

**Conclusion**: A paper always has SOME primary identifier so JSONL records can dedupe.

---

## Case 5: `SignificanceAssessment defaults are conservative`

**Result**: ✅ PASS
**Purpose**: Defaults should start from 'unknown/medium' so the researcher is forced to commit values.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "hamming_score": 3,
  "durability_risk": "medium",
  "compounding_value": "medium",
  "motivation_type": "unclear"
}
```

**Actual**:
```
{
  "hamming_score": 3,
  "hamming_reasoning": "",
  "concrete_consequence": null,
  "durability_risk": "medium",
  "durability_reasoning": "",
  "compounding_value": "medium",
  "compounding_reasoning": "",
  "motivation_type": "unclear"
}
```

**Conclusion**: Mid-range defaults prevent the tool from pretending to have assessed significance.

---

## Case 6: `Evaluation serializes through JSON without data loss`

**Result**: ✅ PASS
**Purpose**: Pydantic model_dump/model_validate round-trip for nested rubric scores and task chain.

**Inputs**:
```
{
  "paper_id": "arxiv:2401.12345",
  "cycle_id": "",
  "mode": "",
  "status": "skimmed",
  "task_chain": {
    "task": "Grasp deformable objects",
    "problem": null,
    "challenge": null,
    "approach": null,
    "one_sentence": null,
    "chain_complete": false,
    "chain_coherent": false
  },
  "has_formal_problem_def": true,
  "formal_framework": "POMDP",
  "structure_identified": [],
  "rubric_scores": {
    "B.1": {
      "score": 4,
      "confidence": "medium",
      "evidence": [],
      "reasoning": ""
    }
  },
  "significance_assessment": null,
  "related_papers": [],
  "contradictions": [],
  "novelty_vs_store": "unknown",
  "extraction_limitations": [],
  "human_review_flags": [],
  "created_at": "2026-04-11T14:36:26.676581"
}
```

**Expected**:
```
{
  "paper_id": "arxiv:2401.12345",
  "formal_framework": "POMDP",
  "B.1.score": 4
}
```

**Actual**:
```
{
  "paper_id": "arxiv:2401.12345",
  "formal_framework": "POMDP",
  "B.1.score": 4
}
```

**Conclusion**: Round-trip integrity is required because evaluations are persisted to evaluation.jsonl.

---

## Case 7: `SearchState holds a keyed map of candidates and status`

**Result**: ✅ PASS
**Purpose**: A SearchState with one candidate and CONVERGED status should instantiate without error.

**Inputs**:
```
{
  "papers_found": {
    "p1": {
      "title": "Test Paper"
    }
  },
  "status": "converged"
}
```

**Expected**:
```
{
  "status": "converged",
  "candidates": [
    "p1"
  ]
}
```

**Actual**:
```
{
  "status": "converged",
  "candidates": [
    "p1"
  ]
}
```

**Conclusion**: SearchState is the Pydantic shell for SM-1; its enum types are round-trippable.

---

## Case 8: `ExtractionQuality.overall rejects values outside the Literal`

**Result**: ✅ PASS
**Purpose**: Pydantic Literal type enforces high/medium/low/abstract_only.

**Inputs**:
```
{
  "overall": "excellent"
}
```

**Expected**:
```
{
  "raises": true
}
```

**Actual**:
```
{
  "raises": true
}
```

**Conclusion**: Strict Literal typing keeps downstream UI rendering deterministic.

---

## Case 9: `PaperStatus enum matches SM-2 pipeline`

**Result**: ✅ PASS
**Purpose**: Regression guard: the PaperStatus enum must match the six stages in SM-2.

**Inputs**:
```
{}
```

**Expected**:
```
[
  "discovered",
  "enriched",
  "extracted",
  "fetched",
  "stored",
  "validated"
]
```

**Actual**:
```
[
  "discovered",
  "enriched",
  "extracted",
  "fetched",
  "stored",
  "validated"
]
```

**Conclusion**: Any drift in the enum would silently break JSONL records that filter by status.

---

## Case 10: `SearchQuery defaults`

**Result**: ✅ PASS
**Purpose**: Unspecified fields default to empty lists / None / max_results=50.

**Inputs**:
```
{
  "query": "grasping",
  "source": "arxiv"
}
```

**Expected**:
```
{
  "max_results": 50,
  "categories": [],
  "executed_at": null
}
```

**Actual**:
```
{
  "max_results": 50,
  "categories": [],
  "executed_at": null
}
```

**Conclusion**: Reasonable defaults let callers construct searches with only query + source.

---

## Case 11: `Evaluation starts as SKIMMED and unknown novelty`

**Result**: ✅ PASS
**Purpose**: New evaluations should initialise to the earliest state in SM-3.

**Inputs**:
```
{
  "paper_id": "p"
}
```

**Expected**:
```
{
  "status": "skimmed",
  "novelty_vs_store": "unknown"
}
```

**Actual**:
```
{
  "status": "skimmed",
  "novelty_vs_store": "unknown"
}
```

**Conclusion**: Forced 'unknown' novelty means the researcher must explicitly declare it.

---

## Summary

- **Total tests**: 11
- **Passed**: 11
- **Failed**: 0
- **Pass rate**: 100.0%
