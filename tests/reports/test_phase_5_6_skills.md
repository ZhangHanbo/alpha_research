# Test Report — `test_phase_5_6_skills`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 6 total — **6 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `new skills exist and declare correct stages`

**Result**: ✅ PASS
**Purpose**: Phase 4/5/6 add four new SKILL.md files. Each must parse cleanly and declare the exact research_stages specified in implementation_plan.md Part VI.

**Inputs**:
```
{
  "expected_stages": {
    "project-understanding": [
      "diagnose",
      "approach"
    ],
    "benchmark-survey": [
      "formalization",
      "approach"
    ],
    "experiment-design": [
      "diagnose",
      "approach",
      "validate"
    ],
    "experiment-analyze": [
      "diagnose",
      "validate"
    ]
  }
}
```

**Expected**:
```
{
  "project-understanding": [
    "diagnose",
    "approach"
  ],
  "benchmark-survey": [
    "formalization",
    "approach"
  ],
  "experiment-design": [
    "diagnose",
    "approach",
    "validate"
  ],
  "experiment-analyze": [
    "diagnose",
    "validate"
  ]
}
```

**Actual**:
```
{
  "project-understanding": [
    "diagnose",
    "approach"
  ],
  "benchmark-survey": [
    "formalization",
    "approach"
  ],
  "experiment-design": [
    "diagnose",
    "approach",
    "validate"
  ],
  "experiment-analyze": [
    "diagnose",
    "validate"
  ]
}
```

**Conclusion**: All four new skills are well-formed and their stage bindings match the plan. The runtime can route invocations correctly.

---

## Case 2: `_has_scope_benchmarks edge cases`

**Result**: ✅ PASS
**Purpose**: The benchmarks.md parser must correctly count ### subheaders under the '## In scope' section only, ignoring rejected benchmarks. This is what the g2 guard relies on.

**Inputs**:
```
{
  "cases": [
    "missing",
    "only_rejected_section",
    "empty_scope",
    "one_in_scope",
    "three_in_scope"
  ]
}
```

**Expected**:
```
{
  "missing": [
    false,
    0
  ],
  "only_rejected_section": [
    false,
    0
  ],
  "empty_scope": [
    false,
    0
  ],
  "one_in_scope": [
    true,
    1
  ],
  "three_in_scope": [
    true,
    3
  ]
}
```

**Actual**:
```
{
  "missing": [
    false,
    0
  ],
  "only_rejected_section": [
    false,
    0
  ],
  "empty_scope": [
    false,
    0
  ],
  "one_in_scope": [
    true,
    1
  ],
  "three_in_scope": [
    true,
    3
  ]
}
```

**Conclusion**: The parser is robust: missing files, misplaced sections, and multi-entry in-scope lists all resolve to the right count. The g2 guard gets a reliable signal.

---

## Case 3: `experiment_analysis records flow end-to-end`

**Result**: ✅ PASS
**Purpose**: Three experiment-analyze records (reproduction pass, diagnostic contradiction, approach null ablation) must be appendable and filterable through the records layer.

**Inputs**:
```
{
  "records_written": 3,
  "modes": [
    "reproduction",
    "diagnostic",
    "approach"
  ]
}
```

**Expected**:
```
{
  "total_count": 3,
  "reproduction_passes": 1,
  "first_pass_id_matches": true
}
```

**Actual**:
```
{
  "total_count": 3,
  "reproduction_passes": 1,
  "first_pass_id_matches": true
}
```

**Conclusion**: The records/jsonl layer supports the new experiment_analysis record type with full filter semantics. Downstream skills (adversarial-review, project stage) can query by mode and reproducibility without custom code.

---

## Case 4: `propose_backward_trigger from experiment-analyze`

**Result**: ✅ PASS
**Purpose**: When experiment-analyze detects a backward-trigger pattern (e.g. t15 ablation), it calls propose_backward_trigger and the open trigger lands in state.json for the human to review via `project stage`.

**Inputs**:
```
{
  "trigger": "t15",
  "proposed_by": "experiment-analyze",
  "evidence": "ablation removing contact prior did not hurt accuracy"
}
```

**Expected**:
```
{
  "open_triggers_count": 1,
  "trigger": "t15",
  "proposed_by": "experiment-analyze",
  "not_resolved": true
}
```

**Actual**:
```
{
  "open_triggers_count": 1,
  "trigger": "t15",
  "proposed_by": "experiment-analyze",
  "not_resolved": true,
  "evidence_preserved": true
}
```

**Conclusion**: The skill-to-state bridge works: a skill surfaces a proposal, the state tracks it, and `project stage` will render it for the human to act on.

---

## Case 5: `provenance chain: design → analyze`

**Result**: ✅ PASS
**Purpose**: Every experiment_analysis action must link back to the experiment_design that motivated it, so `alpha-research provenance` can reconstruct 'why did we run this experiment?'.

**Inputs**:
```
{
  "design_action": "experiment-design",
  "analyze_action": "experiment-analyze"
}
```

**Expected**:
```
{
  "provenance_count": 2,
  "design_has_no_parent": true,
  "analyze_parent_is_design": true
}
```

**Actual**:
```
{
  "provenance_count": 2,
  "design_parent_ids": [],
  "analyze_parent_ids": [
    "prov_47efe8bb2e"
  ],
  "analyze_parent_is_design": true
}
```

**Conclusion**: Provenance DAG is intact. A reviewer three weeks later running `alpha-research provenance` can trace every experiment_analysis back to the design that motivated it.

---

## Case 6: `new skills have correct stage verdicts across all six stages`

**Result**: ✅ PASS
**Purpose**: Walk each new skill through every stage and confirm the verdict matches the plan. This is the definitive matrix check for Phase 4–6 stage wiring.

**Inputs**:
```
{
  "stages": [
    "significance",
    "formalization",
    "diagnose",
    "challenge",
    "approach",
    "validate"
  ]
}
```

**Expected**:
```
{
  "significance": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "out_of_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "out_of_stage"
  },
  "formalization": {
    "benchmark-survey": "in_stage",
    "experiment-design": "out_of_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "out_of_stage"
  },
  "diagnose": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "in_stage",
    "experiment-analyze": "in_stage",
    "project-understanding": "in_stage"
  },
  "challenge": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "out_of_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "out_of_stage"
  },
  "approach": {
    "benchmark-survey": "in_stage",
    "experiment-design": "in_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "in_stage"
  },
  "validate": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "in_stage",
    "experiment-analyze": "in_stage",
    "project-understanding": "out_of_stage"
  }
}
```

**Actual**:
```
{
  "significance": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "out_of_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "out_of_stage"
  },
  "formalization": {
    "benchmark-survey": "in_stage",
    "experiment-design": "out_of_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "out_of_stage"
  },
  "diagnose": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "in_stage",
    "experiment-analyze": "in_stage",
    "project-understanding": "in_stage"
  },
  "challenge": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "out_of_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "out_of_stage"
  },
  "approach": {
    "benchmark-survey": "in_stage",
    "experiment-design": "in_stage",
    "experiment-analyze": "out_of_stage",
    "project-understanding": "in_stage"
  },
  "validate": {
    "benchmark-survey": "out_of_stage",
    "experiment-design": "in_stage",
    "experiment-analyze": "in_stage",
    "project-understanding": "out_of_stage"
  }
}
```

**Conclusion**: The stage-awareness layer is correctly wired for every new skill. Runtime invocation from the wrong stage will warn, from the right stage will proceed silently.

---

## Summary

- **Total tests**: 6
- **Passed**: 6
- **Failed**: 0
- **Pass rate**: 100.0%
