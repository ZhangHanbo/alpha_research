# Test Report — `test_records_jsonl`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 7 total — **7 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `append_record → read_records round-trip`

**Result**: ✅ PASS
**Purpose**: Appending a record then reading it back should return the same payload plus auto-stamped id and created_at.

**Inputs**:
```
{
  "record_type": "evaluation",
  "data": {
    "paper": "X",
    "score": 7
  }
}
```

**Expected**:
```
{
  "count": 1,
  "paper": "X",
  "score": 7,
  "id_prefix": "eval_"
}
```

**Actual**:
```
{
  "count": 1,
  "paper": "X",
  "score": 7,
  "id": "eval_67365812fc"
}
```

**Conclusion**: This is the canonical write-read path for every skill that persists to JSONL.

---

## Case 2: `nested dotted-path filter finds matching records`

**Result**: ✅ PASS
**Purpose**: Filters support dotted paths so callers can query rubric scores directly.

**Inputs**:
```
{
  "filter": "rubric_scores.B.1.score == 5"
}
```

**Expected**:
```
{
  "count": 1,
  "name": "p2"
}
```

**Actual**:
```
{
  "count": 1,
  "name": "p2"
}
```

**Conclusion**: Dotted filters are how downstream skills query deeply nested rubric records.

---

## Case 3: `count_records agrees with read_records`

**Result**: ✅ PASS
**Purpose**: count_records should match the length of the equivalent read_records output.

**Inputs**:
```
{
  "records": [
    {
      "severity": "fatal"
    },
    {
      "severity": "serious"
    },
    {
      "severity": "fatal"
    },
    {
      "severity": "minor"
    },
    {
      "severity": "fatal"
    }
  ],
  "filter": {
    "severity": "fatal"
  }
}
```

**Expected**:
```
{
  "count": 3
}
```

**Actual**:
```
{
  "count": 3,
  "read_length": 3
}
```

**Conclusion**: Disagreement between count and read would signal a filter-logic bug; staying in sync is load-bearing.

---

## Case 4: `unsupported record_type raises ValueError`

**Result**: ✅ PASS
**Purpose**: append_record must reject record types not in SUPPORTED_RECORD_TYPES.

**Inputs**:
```
{
  "record_type": "not_a_type"
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

**Conclusion**: Guard protects the JSONL store schema so records remain queryable.

---

## Case 5: `malformed JSONL line is skipped with a warning`

**Result**: ✅ PASS
**Purpose**: Corrupt lines should not halt reading — they should be skipped and logged.

**Inputs**:
```
{
  "inject": "not json at all"
}
```

**Expected**:
```
{
  "records": 2,
  "warning_logged": true
}
```

**Actual**:
```
{
  "records": 2,
  "warning_logged": true
}
```

**Conclusion**: Resilience matters because JSONL files are edited by humans and crashed processes.

---

## Case 6: `log_action persists provenance correctly`

**Result**: ✅ PASS
**Purpose**: log_action is the canonical API every skill/pipeline uses to record its run.

**Inputs**:
```
{
  "action_type": "skill",
  "action_name": "paper-evaluate",
  "project_stage": "formalization",
  "parent_ids": [
    "root"
  ]
}
```

**Expected**:
```
{
  "records": 1,
  "action_name": "paper-evaluate",
  "parent_ids": [
    "root"
  ]
}
```

**Actual**:
```
{
  "records": 1,
  "action_name": "paper-evaluate",
  "parent_ids": [
    "root"
  ]
}
```

**Conclusion**: Provenance lineage is the audit trail for every research action.

---

## Case 7: `SUPPORTED_RECORD_TYPES contains the canonical 6+`

**Result**: ✅ PASS
**Purpose**: Regression guard: the core record types must not be removed.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "required_subset": [
    "evaluation",
    "finding",
    "frontier",
    "method_survey",
    "provenance",
    "review"
  ]
}
```

**Actual**:
```
{
  "present": [
    "audit",
    "benchmark_survey",
    "challenge",
    "concurrent_work",
    "diagnosis",
    "evaluation",
    "experiment_analysis",
    "experiment_design",
    "finding",
    "formalization_check",
    "frontier",
    "gap_report",
    "method_survey",
    "provenance",
    "review",
    "significance_screen"
  ]
}
```

**Conclusion**: Removing one of these types would silently break historical JSONL reads in active projects.

---

## Summary

- **Total tests**: 7
- **Passed**: 7
- **Failed**: 0
- **Pass rate**: 100.0%
