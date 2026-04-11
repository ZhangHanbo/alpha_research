# Test Report — `test_method_survey`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 6 total — **6 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `structural challenges produce structural-method queries`

**Result**: ✅ PASS
**Purpose**: For a structural challenge, _build_queries instantiates templates that emphasise formalization.

**Inputs**:
```
{
  "challenge_type": "structural",
  "name": "contact-rich manipulation"
}
```

**Expected**:
```
{
  "contains_structural_method": true,
  "all_contain_name": true
}
```

**Actual**:
```
{
  "queries": [
    "contact-rich manipulation structural method",
    "contact-rich manipulation formalization",
    "contact-rich manipulation theoretical guarantees"
  ]
}
```

**Conclusion**: Query templates are tuned to the challenge type per research_guideline §2.7.

---

## Case 2: `resource_complaint challenges produce efficiency queries`

**Result**: ✅ PASS
**Purpose**: Data-/sample-efficient queries target the 'we just need more X' framing.

**Inputs**:
```
{
  "challenge_type": "resource_complaint",
  "name": "sim2real"
}
```

**Expected**:
```
{
  "contains_data_efficient": true,
  "contains_sample_efficient": true
}
```

**Actual**:
```
[
  "sim2real data efficient",
  "sim2real sample efficient"
]
```

**Conclusion**: Matching the query to the challenge class keeps survey recall high.

---

## Case 3: `fallback uses what_is_wrong when name is absent`

**Result**: ✅ PASS
**Purpose**: challenge_name_fallback should pull a human-readable label from what_is_wrong.

**Inputs**:
```
{
  "what_is_wrong": "Long description of the problem and all its nasty details."
}
```

**Expected**:
```
{
  "starts_with": "Long description",
  "length <= 80": true
}
```

**Actual**:
```
{
  "name": "Long description of the problem and all its nasty details.",
  "length": 58
}
```

**Conclusion**: Fallback keeps the pipeline usable even when record schemas vary.

---

## Case 4: `duplicate paperId is dropped and order preserved`

**Result**: ✅ PASS
**Purpose**: _merge_search_results keeps first occurrence of each key.

**Inputs**:
```
{
  "batch1_ids": [
    "a",
    "b"
  ],
  "batch2_ids": [
    "b",
    "c"
  ]
}
```

**Expected**:
```
{
  "merged_ids": [
    "a",
    "b",
    "c"
  ]
}
```

**Actual**:
```
{
  "merged_ids": [
    "a",
    "b",
    "c"
  ]
}
```

**Conclusion**: Dedup keeps downstream evaluation counts stable across search backends.

---

## Case 5: `top-3 selection by citation count`

**Result**: ✅ PASS
**Purpose**: _top_by_citations returns the N most-cited papers in descending order.

**Inputs**:
```
{
  "papers": [
    {
      "id": "low",
      "cites": 1
    },
    {
      "id": "high",
      "cites": 100
    },
    {
      "id": "mid",
      "cites": 20
    }
  ]
}
```

**Expected**:
```
{
  "top2_ids": [
    "high",
    "mid"
  ]
}
```

**Actual**:
```
{
  "top2_ids": [
    "high",
    "mid"
  ]
}
```

**Conclusion**: Citation-based seeds bias the expansion toward influential papers.

---

## Case 6: `missing challenge surfaces an error in the result`

**Result**: ✅ PASS
**Purpose**: run_method_survey should short-circuit when the challenge_id doesn't exist.

**Inputs**:
```
{
  "challenge_id": "nonexistent"
}
```

**Expected**:
```
{
  "methods_surveyed": 0,
  "error_contains": "not found"
}
```

**Actual**:
```
{
  "methods_surveyed": 0,
  "errors": [
    "challenge 'nonexistent' not found"
  ]
}
```

**Conclusion**: Typos in challenge_id are caught without hitting the search APIs.

---

## Summary

- **Total tests**: 6
- **Passed**: 6
- **Failed**: 0
- **Pass rate**: 100.0%
