# Test Report — `test_model_review`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 6 total — **6 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `Finding rejects missing required fields`

**Result**: ✅ PASS
**Purpose**: Pydantic enforces what_is_wrong/why_it_matters/what_would_fix/falsification/grounding/fixable.

**Inputs**:
```
{
  "severity": "minor",
  "attack_vector": "x"
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

**Conclusion**: Every finding is guaranteed to be specific, actionable, and falsifiable.

---

## Case 2: `Review.all_findings concatenates the three buckets in order`

**Result**: ✅ PASS
**Purpose**: The all_findings property should flatten fatal → serious → minor, and finding_count should tally each bucket.

**Inputs**:
```
{
  "fatal": 1,
  "serious": 2,
  "minor": 1
}
```

**Expected**:
```
{
  "ids_order": [
    "f1",
    "f2",
    "f3",
    "f4"
  ],
  "counts": {
    "fatal": 1,
    "serious": 2,
    "minor": 1
  }
}
```

**Actual**:
```
{
  "ids_order": [
    "f1",
    "f2",
    "f3",
    "f4"
  ],
  "counts": {
    "fatal": 1,
    "serious": 2,
    "minor": 1
  }
}
```

**Conclusion**: Helper property keeps metric code DRY across convergence, quality, and verdict checks.

---

## Case 3: `Review.confidence must be in [1, 5]`

**Result**: ✅ PASS
**Purpose**: NeurIPS confidence scale is 1–5; boundary values outside are rejected.

**Inputs**:
```
{
  "low": 0,
  "high": 6
}
```

**Expected**:
```
{
  "low_rejected": true,
  "high_rejected": true
}
```

**Actual**:
```
{
  "low_rejected": true,
  "high_rejected": true
}
```

**Conclusion**: Confidence is strictly bounded to prevent drift beyond the standard venue scale.

---

## Case 4: `resolution_rate counts addressed / (addressed+deferred+disputed)`

**Result**: ✅ PASS
**Purpose**: Deferred and disputed responses should NOT count toward the resolution rate.

**Inputs**:
```
{
  "addressed": 1,
  "deferred": 1,
  "disputed": 1
}
```

**Expected**:
```
{
  "resolution_rate": "0.3333333333333333 \u00b1 3.3e-07"
}
```

**Actual**:
```
{
  "resolution_rate": 0.3333333333333333
}
```

**Conclusion**: Only an accepted fix counts as 'resolved' — the metric can't be gamed by deferring work.

---

## Case 5: `ReviewQualityMetrics enforces 0≤x≤1 bounds`

**Result**: ✅ PASS
**Purpose**: actionability/grounding/falsifiability must be valid fractions.

**Inputs**:
```
{
  "valid": 0.85,
  "invalid": 1.5
}
```

**Expected**:
```
{
  "valid_accepted": true,
  "invalid_rejected": true
}
```

**Actual**:
```
{
  "valid_accepted": true,
  "invalid_rejected": true
}
```

**Conclusion**: Strict bounds prevent miscomputed metrics from propagating into the report.

---

## Case 6: `ReviewQualityReport holds pass/fail verdict and attached issues`

**Result**: ✅ PASS
**Purpose**: Instantiate a passing and a failing report and verify their fields.

**Inputs**:
```
[
  {
    "passes": true,
    "metric_checks": [
      {
        "name": "actionability",
        "passed": true,
        "actual": 0.9,
        "threshold": 0.8,
        "message": ""
      }
    ],
    "anti_pattern_checks": [
      {
        "pattern": "dimension_averaging",
        "detected": false,
        "evidence": ""
      }
    ],
    "issues": [],
    "recommendation": ""
  },
  {
    "passes": false,
    "metric_checks": [],
    "anti_pattern_checks": [],
    "issues": [
      "Vague critique found."
    ],
    "recommendation": ""
  }
]
```

**Expected**:
```
{
  "pass_report.passes": true,
  "fail_report.passes": false
}
```

**Actual**:
```
{
  "pass_report.passes": true,
  "fail_report.passes": false
}
```

**Conclusion**: Holds the structured output of evaluate_review for programmatic meta-review.

---

## Summary

- **Total tests**: 6
- **Passed**: 6
- **Failed**: 0
- **Pass rate**: 100.0%
