# Test Report — `test_project_state`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 14 total — **14 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `init_project creates state.json and logs provenance`

**Result**: ✅ PASS
**Purpose**: Verify init_project() creates a state.json with stage=SIGNIFICANCE, one init transition, and appends a provenance record.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_init_project_creates_stat0/test_init",
  "project_id": "test_init",
  "question": "tactile insertion for assembly"
}
```

**Expected**:
```
{
  "current_stage": "significance",
  "stage_history_length": 1,
  "init_trigger": "init",
  "provenance_count": 1,
  "init_provenance_action": "project.init"
}
```

**Actual**:
```
{
  "current_stage": "significance",
  "stage_history_length": 1,
  "init_trigger": "init",
  "provenance_count": 1,
  "init_provenance_action": "project.init"
}
```

**Conclusion**: Project initialization is the single entry point that creates state.json in a known-good state and makes the first provenance entry so every subsequent action has a lineage root.

---

## Case 2: `state.json round-trip`

**Result**: ✅ PASS
**Purpose**: save_state then load_state must be a lossless identity.

**Inputs**:
```
{
  "stage_history_count": 2,
  "open_triggers_count": 1,
  "code_dir": "/home/user/my-method"
}
```

**Expected**:
```
{
  "identity": true
}
```

**Actual**:
```
{
  "project_id_match": true,
  "stage_match": true,
  "history_length_match": true,
  "transition_trigger_preserved": "g1",
  "open_trigger_preserved": "t5",
  "code_dir_preserved": "/home/user/my-method"
}
```

**Conclusion**: State serialization is lossless for all fields including nested StageTransition and OpenTrigger objects. This is the foundation for every other state-machine operation.

---

## Case 3: `g1 blocks empty project`

**Result**: ✅ PASS
**Purpose**: A freshly-initialized project should NOT be able to advance from SIGNIFICANCE — the guard must report each missing artifact so the researcher knows what to add.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_g1_blocks_without_confirm0/g1_blocked",
  "artifacts_created": []
}
```

**Expected**:
```
{
  "guard": "g1",
  "passed": false,
  "num_failing_conditions": ">=3"
}
```

**Actual**:
```
{
  "guard": "g1",
  "passed": false,
  "num_failing_conditions": 3,
  "failing_condition_names": [
    "PROJECT.md has content",
    "significance_screen with human_confirmed=true",
    "concrete_consequence is non-empty"
  ]
}
```

**Conclusion**: g1 reads disk artifacts and fails loudly with a per-condition breakdown. This gives the CLI enough information to tell the researcher 'add a significance_screen record and fill in PROJECT.md'.

---

## Case 4: `g1 passes → advance to FORMALIZE`

**Result**: ✅ PASS
**Purpose**: With PROJECT.md + a confirmed significance_screen, g1 should pass and advance should transition SIGNIFICANCE → FORMALIZE.

**Inputs**:
```
{
  "artifacts_created": [
    "PROJECT.md",
    "significance_screen.jsonl"
  ],
  "significance_record": {
    "human_confirmed": true,
    "concrete_consequence": "Robots can handle deformable objects in warehouses, enabling automation of produce packing lines.",
    "durability_risk": "low",
    "hamming_test_score": 4
  }
}
```

**Expected**:
```
{
  "guard_passed": true,
  "advance_from": "significance",
  "advance_to": "formalization",
  "new_stage": "formalization",
  "history_length": 2
}
```

**Actual**:
```
{
  "guard_passed": true,
  "advance_from": "significance",
  "advance_to": "formalization",
  "new_stage": "formalization",
  "history_length": 2
}
```

**Conclusion**: The forward guard + advance path is a full-loop assertion: guard reads disk, advance writes disk, state is updated, provenance is logged. This is the happy path through g1.

---

## Case 5: `advance raises GuardBlocked without --force`

**Result**: ✅ PASS
**Purpose**: advance() must refuse to transition when the guard fails, with a structured error containing the full GuardCheck so callers can render it.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_advance_raises_guard_bloc0/g1_blocked_raise",
  "force": false
}
```

**Expected**:
```
{
  "raised_GuardBlocked": true,
  "summary_mentions_g1": true,
  "summary_mentions_blocked": true
}
```

**Actual**:
```
{
  "raised_GuardBlocked": true,
  "summary_mentions_g1": true,
  "summary_mentions_blocked": true,
  "summary_preview": "g1 (significance): \u274c blocked\n  \u2717 PROJECT.md has content: missing or empty\n  \u2717 significance_screen with human_confirmed=true: none found\n  \u2717 concrete_consequence is non-empty: missing\n  \u2713 durability_ri"
}
```

**Conclusion**: Without --force, advance enforces the guard strictly — this is the mechanism that prevents silent cheating through the state machine.

---

## Case 6: `advance --force records override in provenance`

**Result**: ✅ PASS
**Purpose**: An emergency override must transition the stage but leave a visible footprint in provenance (so reviewers can audit cheating after the fact).

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_advance_force_records_ove0/force_override",
  "force": true,
  "note": "emergency hackathon override"
}
```

**Expected**:
```
{
  "new_stage": "formalization",
  "transition_trigger": "force",
  "note_has_FORCED": true,
  "override_logged_in_provenance": true
}
```

**Actual**:
```
{
  "new_stage": "formalization",
  "transition_trigger": "force",
  "note": "FORCED (g1 blocked): emergency hackathon override",
  "override_logged_in_provenance": true
}
```

**Conclusion**: Force override works and is auditable. Any reviewer running `alpha-research provenance` on the project sees exactly which transitions were forced and why.

---

## Case 7: `backward requires carried_constraint`

**Result**: ✅ PASS
**Purpose**: backward() must reject an empty carried_constraint and accept a non-empty one, recording the transition with the constraint and marking the open trigger as resolved.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_backward_requires_carried0/backward_constraint",
  "first_call": {
    "trigger": "t2",
    "carried_constraint": ""
  },
  "second_call": {
    "trigger": "t2",
    "carried_constraint": "formalization reduced to a known POMDP that DESPOT solves",
    "evidence": "formalization_check detected trivial reduction"
  }
}
```

**Expected**:
```
{
  "first_call_raises_ValueError": true,
  "second_call_transition": "formalization \u2192 significance via t2",
  "carried_constraint_preserved": true,
  "open_trigger_resolved": true
}
```

**Actual**:
```
{
  "first_call_raises_ValueError": true,
  "transition": "formalization \u2192 significance via t2",
  "carried_constraint_preserved": true,
  "open_trigger_resolved": true
}
```

**Conclusion**: Backward transitions enforce the research-guideline principle: backward motion is learning, and the learning must be explicitly captured as a constraint the re-entered stage will carry.

---

## Case 8: `backward rejects trigger invalid for current stage`

**Result**: ✅ PASS
**Purpose**: A trigger that's not allowed from the current stage must be rejected with a clear error naming both the trigger and stage.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_backward_rejects_invalid_0/backward_invalid",
  "current_stage": "significance",
  "requested_trigger": "t15"
}
```

**Expected**:
```
{
  "raises_ValueError_with_trigger_and_stage": true
}
```

**Actual**:
```
{
  "error_message": "Trigger 't15' is not a valid backward transition from stage 'significance'. Allowed: (none)",
  "mentions_t15": true,
  "mentions_significance": true
}
```

**Conclusion**: BACKWARD_TRANSITIONS is the authoritative graph; attempts to take an edge that doesn't exist are rejected with actionable errors rather than corrupting state.

---

## Case 9: `propose_backward_trigger appends open trigger`

**Result**: ✅ PASS
**Purpose**: Skills propose triggers; humans execute them. propose_backward_trigger must persist the proposal without moving the project.

**Inputs**:
```
{
  "trigger": "t15",
  "proposed_by": "experiment-analyze",
  "evidence": "ablation removing 'contact prior' doesn't hurt accuracy"
}
```

**Expected**:
```
{
  "open_triggers_count": 1,
  "trigger": "t15",
  "proposed_by": "experiment-analyze",
  "resolved": false,
  "stage_unchanged": "significance"
}
```

**Actual**:
```
{
  "open_triggers_count": 1,
  "trigger": "t15",
  "proposed_by": "experiment-analyze",
  "resolved": false,
  "stage_unchanged": "significance"
}
```

**Conclusion**: This keeps skills one layer removed from mutating control flow: they surface what they found, the human decides what to do with it.

---

## Case 10: `provenance accumulates across transitions`

**Result**: ✅ PASS
**Purpose**: Every state-changing action must append exactly one provenance record; the sequence of records reconstructs the full history.

**Inputs**:
```
{
  "actions": [
    "init",
    "advance (g1)",
    "backward (t2)"
  ]
}
```

**Expected**:
```
{
  "provenance_count": 3,
  "action_sequence": [
    "project.init",
    "project.advance",
    "project.backward"
  ]
}
```

**Actual**:
```
{
  "provenance_count": 3,
  "action_sequence": [
    "project.init",
    "project.advance",
    "project.backward"
  ]
}
```

**Conclusion**: Provenance is append-only and complete. A reviewer reading provenance.jsonl can reconstruct every transition in order.

---

## Case 11: `g2 requires benchmarks.md (the Phase-5 gap-fix)`

**Result**: ✅ PASS
**Purpose**: The user pointed out that benchmarks were missing from the state machine. g2 must block advancement from FORMALIZE until benchmarks.md contains at least one benchmark under '## In scope'.

**Inputs**:
```
{
  "before_benchmarks_md": {
    "formalization_md": true,
    "formalization_check_record": true,
    "benchmark_survey_record": true,
    "benchmarks_md": false
  },
  "after_benchmarks_md": {
    "benchmarks_md_with_in_scope": true
  }
}
```

**Expected**:
```
{
  "without_benchmarks_md": {
    "g2_passed": false,
    "benchmark_condition_failed": true
  },
  "with_benchmarks_md": {
    "g2_passed": true
  }
}
```

**Actual**:
```
{
  "without_benchmarks_md": {
    "g2_passed": false,
    "benchmark_condition_failed": true
  },
  "with_benchmarks_md": {
    "g2_passed": true
  }
}
```

**Conclusion**: Benchmark survey and selection is wired into the guard layer: FORMALIZE → DIAGNOSE cannot happen until the researcher has chosen at least one benchmark. This is the first enforcement point for the reproducibility floor.

---

## Case 12: `g3 requires reproduction experiment + diagnosis`

**Result**: ✅ PASS
**Purpose**: g3 is the reproducibility floor: DIAGNOSE cannot exit without a passing reproduction run AND at least one observed failure mapped to a formal term.

**Inputs**:
```
{
  "phase_1_records": {
    "experiment_analysis": 0,
    "diagnosis": 0
  },
  "phase_2_records": {
    "experiment_analysis": "mode=reproduction, reproducibility=pass",
    "diagnosis": "failure_mapped_to_formal_term set"
  }
}
```

**Expected**:
```
{
  "phase_1": {
    "g3_passed": false,
    "reproduction_condition_blocks": true
  },
  "phase_2": {
    "g3_passed": true
  }
}
```

**Actual**:
```
{
  "phase_1": {
    "g3_passed": false,
    "reproduction_condition_blocks": true
  },
  "phase_2": {
    "g3_passed": true
  }
}
```

**Conclusion**: The reproducibility floor is enforced: a failing or missing reproduction experiment blocks DIAGNOSE from exiting. Every subsequent failure observation stands on a verified measurement infrastructure.

---

## Case 13: `full forward walk SIGNIFICANCE → VALIDATE`

**Result**: ✅ PASS
**Purpose**: The end-to-end happy path: every guard passes and the project walks from SIGNIFICANCE to VALIDATE with each transition recorded in stage_history.

**Inputs**:
```
{
  "starting_stage": "significance",
  "records_added_per_stage": {
    "significance": [
      "PROJECT.md",
      "significance_screen"
    ],
    "formalization": [
      "formalization.md",
      "formalization_check",
      "benchmark_survey",
      "benchmarks.md (2 in scope)"
    ],
    "diagnose": [
      "experiment_analysis (reproduction=pass)",
      "diagnosis"
    ],
    "challenge": [
      "challenge (structural)"
    ],
    "approach": [
      "one_sentence.md (insight)",
      "experiment_design"
    ]
  }
}
```

**Expected**:
```
{
  "final_stage": "validate",
  "stage_sequence": [
    "significance",
    "formalization",
    "diagnose",
    "challenge",
    "approach",
    "validate"
  ],
  "all_forward_via_guards": true
}
```

**Actual**:
```
{
  "final_stage": "validate",
  "stage_sequence": [
    "significance",
    "formalization",
    "diagnose",
    "challenge",
    "approach",
    "validate"
  ],
  "transition_triggers": [
    "init",
    "g1",
    "g2",
    "g3",
    "g4",
    "g5"
  ],
  "all_forward_via_guards": true
}
```

**Conclusion**: Every stage transition is guard-gated and every artifact listed in implementation_plan.md Parts III.1–III.5 is actually read by the runtime. This is the load-bearing end-to-end test for the state machine proper.

---

## Case 14: `log_action writes a complete provenance record`

**Result**: ✅ PASS
**Purpose**: log_action is the one helper every skill/pipeline/CLI verb uses. It must persist every field faithfully so the provenance graph is intact.

**Inputs**:
```
{
  "action_type": "skill",
  "action_name": "paper-evaluate",
  "project_stage": "significance",
  "inputs": [
    "paper:arxiv:2501.12345"
  ],
  "outputs": [
    "evaluations.jsonl"
  ],
  "parent_ids": [
    "prov_init_001"
  ],
  "summary": "evaluated a test paper"
}
```

**Expected**:
```
{
  "records_count": 1,
  "id_matches_returned": true,
  "all_fields_preserved": true
}
```

**Actual**:
```
{
  "records_count": 1,
  "id_matches_returned": true,
  "action_type": "skill",
  "action_name": "paper-evaluate",
  "project_stage": "significance",
  "parent_ids": [
    "prov_init_001"
  ],
  "summary": "evaluated a test paper"
}
```

**Conclusion**: log_action is the canonical way to record work done. It works on an isolated project directory with no other state, proving it's a pure append operation that skills can call from bash.

---

## Summary

- **Total tests**: 14
- **Passed**: 14
- **Failed**: 0
- **Pass rate**: 100.0%
