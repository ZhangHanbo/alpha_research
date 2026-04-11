# Test Report — `test_finding_tracker`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 4 total — **4 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `addressed finding reported as addressed`

**Result**: ✅ PASS
**Purpose**: track() + get_summary() classifies a finding with a FindingResponse as addressed.

**Inputs**:
```
{
  "finding_id": "f1",
  "response": "addressed"
}
```

**Expected**:
```
{
  "f1": "addressed"
}
```

**Actual**:
```
{
  "f1": "addressed"
}
```

**Conclusion**: The tracker faithfully propagates per-finding response actions to its summary.

---

## Case 2: `finding that reappears without response is persistent`

**Result**: ✅ PASS
**Purpose**: A finding seen in iterations 1 AND 2 with no response should be 'persistent'.

**Inputs**:
```
{
  "iterations": 2,
  "finding_id": "f1",
  "response": null
}
```

**Expected**:
```
{
  "f1": "persistent"
}
```

**Actual**:
```
{
  "f1": "persistent"
}
```

**Conclusion**: Persistent findings are the signal that triggers a backward transition or human review.

---

## Case 3: `unaddressed serious→minor downgrade is flagged`

**Result**: ✅ PASS
**Purpose**: check_monotonic_severity returns finding ids whose severity dropped without a FindingResponse.

**Inputs**:
```
{
  "prev_severity": "serious",
  "curr_severity": "minor",
  "addressed": false
}
```

**Expected**:
```
{
  "downgraded": [
    "f1"
  ]
}
```

**Actual**:
```
{
  "downgraded": [
    "f1"
  ]
}
```

**Conclusion**: Severity regression is the anti-collapse tripwire — without it, the review loop can quietly soften criticisms instead of resolving them.

---

## Case 4: `resolution history reports per-iteration rates`

**Result**: ✅ PASS
**Purpose**: get_resolution_history() walks tracked iterations and returns each response's addressed-fraction.

**Inputs**:
```
{
  "iter_1": {
    "findings": 2,
    "addressed": 1
  },
  "iter_2": {
    "findings": 1,
    "addressed": 1
  }
}
```

**Expected**:
```
[
  0.5,
  1.0
]
```

**Actual**:
```
[
  0.5,
  1.0
]
```

**Conclusion**: Resolution rate should increase as the researcher addresses the backlog — this is the convergence proxy.

---

## Summary

- **Total tests**: 4
- **Passed**: 4
- **Failed**: 0
- **Pass rate**: 100.0%
