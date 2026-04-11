# Test Report — `test_frontier_mapping`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 4 total — **4 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `three-tier classification aggregates correctly`

**Result**: ✅ PASS
**Purpose**: run_frontier_mapping partitions mocked classifications into reliable/sometimes/cant_yet.

**Inputs**:
```
{
  "papers": [
    "Paper A",
    "Paper B",
    "Paper C"
  ],
  "tier_map": {
    "Paper A": "reliable",
    "Paper B": "sometimes",
    "Paper C": "cant_yet"
  }
}
```

**Expected**:
```
{
  "reliable": 1,
  "sometimes": 1,
  "cant_yet": 1
}
```

**Actual**:
```
{
  "reliable": 1,
  "sometimes": 1,
  "cant_yet": 1
}
```

**Conclusion**: The tier partition is the core observable output of frontier_mapping.

---

## Case 2: `frontier snapshot appended to frontier.jsonl`

**Result**: ✅ PASS
**Purpose**: Each run should append one frontier record with the full tier partition.

**Inputs**:
```
{
  "domain": "grasp"
}
```

**Expected**:
```
{
  "records": 1,
  "domain": "grasp",
  "reliable_count": 1
}
```

**Actual**:
```
{
  "records": 1,
  "domain": "grasp",
  "reliable_count": 1
}
```

**Conclusion**: Persistence gives the dashboard and downstream diff logic a stable store.

---

## Case 3: `shift from cant_yet → reliable detected`

**Result**: ✅ PASS
**Purpose**: A second run that promotes a capability should emit a shift record.

**Inputs**:
```
{
  "first_run_tier": "cant_yet",
  "second_run_tier": "reliable"
}
```

**Expected**:
```
{
  "shift_observed": true
}
```

**Actual**:
```
{
  "shifts": [
    {
      "capability": "capability(Shifter)",
      "from": "cant_yet",
      "to": "reliable"
    }
  ]
}
```

**Conclusion**: The diff drives narrative signal in the dashboard: 'capability X moved up a tier'.

---

## Case 4: `domain word-match filters irrelevant evaluations`

**Result**: ✅ PASS
**Purpose**: Papers whose task chain doesn't share a significant word with the query should be skipped.

**Inputs**:
```
{
  "query": "robot grasp",
  "titles": [
    "Grasp Paper",
    "Other"
  ]
}
```

**Expected**:
```
{
  "included_titles": [
    "Grasp Paper"
  ]
}
```

**Actual**:
```
{
  "included_titles": [
    "Grasp Paper"
  ]
}
```

**Conclusion**: Word-level matching is how frontier scoping stays on-topic.

---

## Summary

- **Total tests**: 4
- **Passed**: 4
- **Failed**: 0
- **Pass rate**: 100.0%
