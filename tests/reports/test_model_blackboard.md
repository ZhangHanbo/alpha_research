# Test Report — `test_model_blackboard`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 6 total — **6 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `venue acceptance rates follow tier ordering`

**Result**: ✅ PASS
**Purpose**: Top-tier venues (IJRR, T-RO) must have stricter acceptance than mid-tier.

**Inputs**:
```
{
  "IJRR": 0.2,
  "T-RO": 0.25,
  "RSS": 0.3,
  "CoRL": 0.3,
  "RA-L": 0.4,
  "ICRA": 0.45,
  "IROS": 0.45
}
```

**Expected**:
```
{
  "IJRR < ICRA": true,
  "RSS < IROS": true
}
```

**Actual**:
```
{
  "IJRR < ICRA": true,
  "RSS < IROS": true
}
```

**Conclusion**: Acceptance-rate ordering drives verdict calibration in compute_verdict.

---

## Case 2: `ResearchStage enum matches research_plan outer state machine`

**Result**: ✅ PASS
**Purpose**: Regression guard: the stage order must match research_plan §2.4.

**Inputs**:
```
{}
```

**Expected**:
```
[
  "significance",
  "formalization",
  "diagnose",
  "challenge",
  "approach",
  "validate",
  "full_draft"
]
```

**Actual**:
```
[
  "significance",
  "formalization",
  "diagnose",
  "challenge",
  "approach",
  "validate",
  "full_draft"
]
```

**Conclusion**: Any drift in the enum would invalidate state.json records in existing projects.

---

## Case 3: `Blackboard JSON round-trip preserves every field`

**Result**: ✅ PASS
**Purpose**: save()/load() must losslessly persist the shared state between research and review agents.

**Inputs**:
```
{
  "artifact_version": 2,
  "stage": "challenge",
  "iteration": 3,
  "target_venue": "CoRL"
}
```

**Expected**:
```
{
  "artifact_version": 2,
  "stage": "challenge",
  "iteration": 3,
  "target_venue": "CoRL",
  "verdict_history": [
    "weak_reject",
    "weak_accept"
  ],
  "decisions": 1
}
```

**Actual**:
```
{
  "artifact_version": 2,
  "stage": "challenge",
  "iteration": 3,
  "target_venue": "CoRL",
  "verdict_history": [
    "weak_reject",
    "weak_accept"
  ],
  "decisions": 1
}
```

**Conclusion**: Disk persistence of the blackboard is the only way the review loop survives a crash.

---

## Case 4: `Blackboard.save creates missing parent directories`

**Result**: ✅ PASS
**Purpose**: save() should mkdir -p the parent of the target path.

**Inputs**:
```
{
  "path": "/tmp/pytest-of-zhb/pytest-32/test_blackboard_save_creates_p0/nested/subdir/bb.json"
}
```

**Expected**:
```
{
  "exists": true
}
```

**Actual**:
```
{
  "exists": true
}
```

**Conclusion**: Convenience: caller never needs to preflight the directory.

---

## Case 5: `ConvergenceState defaults to not-converged`

**Result**: ✅ PASS
**Purpose**: Default convergence state must be safe — the loop should not think it converged by accident.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "converged": false,
  "reason": "not_converged"
}
```

**Actual**:
```
{
  "converged": false,
  "reason": "not_converged"
}
```

**Conclusion**: Conservative default prevents accidental early termination.

---

## Case 6: `HumanDecision carries iteration, action, and details`

**Result**: ✅ PASS
**Purpose**: Smoke test construction of HumanDecision with an APPROVE_BACKWARD action.

**Inputs**:
```
{
  "iteration": 2,
  "action": "approve_backward",
  "details": "approved to significance"
}
```

**Expected**:
```
{
  "iteration": 2,
  "action": "approve_backward"
}
```

**Actual**:
```
{
  "iteration": 2,
  "action": "approve_backward"
}
```

**Conclusion**: Human decisions are append-only; the timestamp is default-now.

---

## Summary

- **Total tests**: 6
- **Passed**: 6
- **Failed**: 0
- **Pass rate**: 100.0%
