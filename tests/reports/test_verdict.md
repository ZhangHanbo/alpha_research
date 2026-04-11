# Test Report — `test_verdict`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 10 total — **10 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `any fatal finding forces REJECT`

**Result**: ✅ PASS
**Purpose**: Rule 1 of review_plan §1.9 — fatal dominates everything else.

**Inputs**:
```
{
  "severities": [
    "fatal",
    "serious"
  ],
  "fixable": [
    true,
    true
  ],
  "venue": "RSS",
  "significance_score": 3
}
```

**Expected**:
```
reject
```

**Actual**:
```
reject
```

**Conclusion**: A fatal flaw is non-negotiable regardless of venue or significance.

---

## Case 2: `significance_score<=2 rejects even with no findings`

**Result**: ✅ PASS
**Purpose**: Rule 2 — a low-significance problem can't be saved by a clean review.

**Inputs**:
```
{
  "severities": [],
  "fixable": [],
  "venue": "RSS",
  "significance_score": 2
}
```

**Expected**:
```
reject
```

**Actual**:
```
reject
```

**Conclusion**: Significance is a hard floor — no one cares about a rigorous solution to a trivial problem.

---

## Case 3: `3 unresolvable serious → REJECT`

**Result**: ✅ PASS
**Purpose**: Rule 3 — 3+ serious findings that can't be fixed make the paper non-salvageable.

**Inputs**:
```
{
  "severities": [
    "serious",
    "serious",
    "serious"
  ],
  "fixable": [
    false,
    false,
    false
  ],
  "venue": "RSS",
  "significance_score": 3
}
```

**Expected**:
```
reject
```

**Actual**:
```
reject
```

**Conclusion**: Three structural problems is a rewrite, not a revision.

---

## Case 4: `only minor findings → ACCEPT`

**Result**: ✅ PASS
**Purpose**: Rule 4 — minor issues don't block acceptance.

**Inputs**:
```
{
  "severities": [
    "minor",
    "minor"
  ],
  "fixable": [
    true,
    true
  ],
  "venue": "RSS",
  "significance_score": 3
}
```

**Expected**:
```
accept
```

**Actual**:
```
accept
```

**Conclusion**: Minor issues are polish, not blockers.

---

## Case 5: `single fixable serious → WEAK_ACCEPT`

**Result**: ✅ PASS
**Purpose**: Rule 5 — a single addressable serious finding converts to WEAK_ACCEPT.

**Inputs**:
```
{
  "severities": [
    "serious"
  ],
  "fixable": [
    true
  ],
  "venue": "RSS",
  "significance_score": 3
}
```

**Expected**:
```
weak_accept
```

**Actual**:
```
weak_accept
```

**Conclusion**: One tractable serious finding is a standard revision cycle.

---

## Case 6: `2 fixable serious at IJRR → REJECT`

**Result**: ✅ PASS
**Purpose**: Rule 6 (top-tier) — IJRR/T-RO don't tolerate 2+ serious findings.

**Inputs**:
```
{
  "severities": [
    "serious",
    "serious"
  ],
  "fixable": [
    true,
    true
  ],
  "venue": "IJRR",
  "significance_score": 3
}
```

**Expected**:
```
reject
```

**Actual**:
```
reject
```

**Conclusion**: Top-tier venues are strict — two serious findings is rejection even if fixable.

---

## Case 7: `2 fixable serious at ICRA → WEAK_REJECT`

**Result**: ✅ PASS
**Purpose**: Rule 6 (mid-tier) — ICRA/IROS/RA-L rate 2+ serious findings as weak reject.

**Inputs**:
```
{
  "severities": [
    "serious",
    "serious"
  ],
  "fixable": [
    true,
    true
  ],
  "venue": "ICRA",
  "significance_score": 3
}
```

**Expected**:
```
weak_reject
```

**Actual**:
```
weak_reject
```

**Conclusion**: Mid-tier venues recognise that serious findings warrant revision, not outright rejection.

---

## Case 8: `2 fixable serious at RSS → WEAK_ACCEPT`

**Result**: ✅ PASS
**Purpose**: Rule 6 (selective) — RSS/CoRL accept all-fixable borderline papers.

**Inputs**:
```
{
  "severities": [
    "serious",
    "serious"
  ],
  "fixable": [
    true,
    true
  ],
  "venue": "RSS",
  "significance_score": 3
}
```

**Expected**:
```
weak_accept
```

**Actual**:
```
weak_accept
```

**Conclusion**: Selective venues reward addressable work even when the issue count is borderline.

---

## Case 9: `4 fixable serious → WEAK_REJECT`

**Result**: ✅ PASS
**Purpose**: Tail rule — 4+ serious findings at any venue are WEAK_REJECT (not ACCEPT, not outright REJECT).

**Inputs**:
```
{
  "severities": [
    "serious",
    "serious",
    "serious",
    "serious"
  ],
  "fixable": [
    true,
    true,
    true,
    true
  ],
  "venue": "RSS",
  "significance_score": 3
}
```

**Expected**:
```
weak_reject
```

**Actual**:
```
weak_reject
```

**Conclusion**: 4 serious items is too much to land, even if individually fixable.

---

## Case 10: `empty findings list → ACCEPT`

**Result**: ✅ PASS
**Purpose**: Zero findings + sane significance should always be ACCEPT.

**Inputs**:
```
{
  "severities": [],
  "fixable": [],
  "venue": "IJRR",
  "significance_score": 5
}
```

**Expected**:
```
accept
```

**Actual**:
```
accept
```

**Conclusion**: A clean review is an acceptable review, full stop.

---

## Summary

- **Total tests**: 10
- **Passed**: 10
- **Failed**: 0
- **Pass rate**: 100.0%
