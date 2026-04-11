# Test Report — `test_state_machine_report`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 10 total — **10 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `forward transition table is linear`

**Result**: ✅ PASS
**Purpose**: Every non-terminal stage has exactly one successor; full_draft is terminal.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "significance": [
    "formalization"
  ],
  "formalization": [
    "diagnose"
  ],
  "diagnose": [
    "challenge"
  ],
  "challenge": [
    "approach"
  ],
  "approach": [
    "validate"
  ],
  "validate": [
    "full_draft"
  ],
  "full_draft": []
}
```

**Actual**:
```
{
  "significance": [
    "formalization"
  ],
  "formalization": [
    "diagnose"
  ],
  "diagnose": [
    "challenge"
  ],
  "challenge": [
    "approach"
  ],
  "approach": [
    "validate"
  ],
  "validate": [
    "full_draft"
  ],
  "full_draft": []
}
```

**Conclusion**: A linear forward chain keeps the state machine interpretable and uniquely testable.

---

## Case 2: `backward triggers are t2..t15 style`

**Result**: ✅ PASS
**Purpose**: BACKWARD_TRANSITIONS should enumerate at least 12 t* triggers.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "count >= 12": true,
  "all_t_prefixed": true
}
```

**Actual**:
```
{
  "triggers": [
    "t10",
    "t11",
    "t12",
    "t13",
    "t14",
    "t15",
    "t2",
    "t4",
    "t5",
    "t6",
    "t7",
    "t8",
    "t9"
  ],
  "count": 13
}
```

**Conclusion**: Backward triggers anchor the research_plan §2.4 regression matrix.

---

## Case 3: `valid_transitions(validate) includes forward + backward targets`

**Result**: ✅ PASS
**Purpose**: From validate, the machine can advance to full_draft or regress to several earlier stages.

**Inputs**:
```
{
  "stage": "validate"
}
```

**Expected**:
```
{
  "contains": [
    "full_draft",
    "significance",
    "diagnose"
  ]
}
```

**Actual**:
```
{
  "targets": [
    "full_draft",
    "significance",
    "formalization",
    "diagnose"
  ]
}
```

**Conclusion**: The transition surface for the validate stage is the most connected node in the graph.

---

## Case 4: `g1 passes when metadata has a significance key`

**Result**: ✅ PASS
**Purpose**: An explicit significance signal in metadata should unlock the SIGNIFICANCE → FORMALIZATION transition.

**Inputs**:
```
{
  "metadata": {
    "significance": 4
  }
}
```

**Expected**:
```
{
  "g1": true
}
```

**Actual**:
```
{
  "g1": true
}
```

**Conclusion**: Metadata is the cleanest signal; content-level heuristics are a fallback.

---

## Case 5: `g2 passes on explicit formal math content`

**Result**: ✅ PASS
**Purpose**: 'formal problem', 'argmin', and '\mathcal' markers unlock FORMALIZATION → DIAGNOSE.

**Inputs**:
```
{
  "content_excerpt": "formal problem ... argmin ... \\mathcal"
}
```

**Expected**:
```
{
  "g2": true
}
```

**Actual**:
```
{
  "g2": true
}
```

**Conclusion**: Math notation serves as a proxy for 'the problem is actually formalized'.

---

## Case 6: `g3 blocks diagnose when no failure is identified`

**Result**: ✅ PASS
**Purpose**: Without 'failure mode', 'fails when', 'diagnosed', the DIAGNOSE stage is not complete.

**Inputs**:
```
{
  "content": "We did some experiments."
}
```

**Expected**:
```
{
  "g3": false
}
```

**Actual**:
```
{
  "g3": false
}
```

**Conclusion**: Gate prevents the researcher from claiming diagnosis without naming the failure.

---

## Case 7: `'concurrent work' attack vector → t9`

**Result**: ✅ PASS
**Purpose**: backward_trigger_from_finding pattern-matches keywords in attack_vector.

**Inputs**:
```
{
  "attack_vector": "Concurrent work already solved this (Smith 2024)"
}
```

**Expected**:
```
t9
```

**Actual**:
```
t9
```

**Conclusion**: t9 correctly regresses the loop from validate to significance when novelty evaporates.

---

## Case 8: `'hamming' / 'incremental' → t13`

**Result**: ✅ PASS
**Purpose**: Hamming/incremental-contribution language should map to the t13 regression trigger.

**Inputs**:
```
{
  "attack_vector": "Incremental contribution \u2014 fails the Hamming test"
}
```

**Expected**:
```
t13
```

**Actual**:
```
t13
```

**Conclusion**: t13 is the canonical hamming-fail backward step per research_plan §2.4.

---

## Case 9: `explicit maps_to_trigger overrides keyword inference`

**Result**: ✅ PASS
**Purpose**: When the reviewer tags a finding with a specific trigger, it should win.

**Inputs**:
```
{
  "maps_to_trigger": "t14",
  "attack_vector_keyword": "concurrent work"
}
```

**Expected**:
```
t14
```

**Actual**:
```
t14
```

**Conclusion**: Explicit annotation is respected over heuristic fallback — correctly.

---

## Case 10: `minor findings never produce backward triggers`

**Result**: ✅ PASS
**Purpose**: Minor findings should return None regardless of attack_vector wording.

**Inputs**:
```
{
  "severity": "minor",
  "attack_vector": "concurrent work"
}
```

**Expected**:
```
None
```

**Actual**:
```
None
```

**Conclusion**: Prevents minor polish issues from triggering costly regressions.

---

## Summary

- **Total tests**: 10
- **Passed**: 10
- **Failed**: 0
- **Pass rate**: 100.0%
