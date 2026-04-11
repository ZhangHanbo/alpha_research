# Test Report — `test_full_loop`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 2 total — **2 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `full loop: six stages + backward transition + reproduction fail→pass`

**Result**: ✅ PASS
**Purpose**: End-to-end validation of Phases 1-6 combined: init a project, walk it through all six stages, fire a backward transition (t4) with a carried constraint, exercise both reproduction fail and pass paths, and verify provenance reconstructs the full history.

**Inputs**:
```
{
  "stages_walked": [
    "significance",
    "formalization",
    "diagnose",
    "[backward t4 \u2192 formalization]",
    "diagnose",
    "challenge",
    "approach",
    "validate"
  ],
  "reproduction_experiments": [
    "FAIL \u2014 observed 0.20 vs target 0.62",
    "PASS \u2014 observed 0.60 vs target 0.62"
  ],
  "backward_trigger": {
    "trigger": "t4",
    "carried_constraint": "failure doesn't map to current formalization \u2014 need dynamics"
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
    "formalization",
    "diagnose",
    "challenge",
    "approach",
    "validate"
  ],
  "n_experiment_analysis_records": 2,
  "provenance_action_sequence": [
    "project.init",
    "project.advance",
    "project.advance",
    "project.backward",
    "project.advance",
    "project.advance",
    "project.advance",
    "project.advance"
  ],
  "t4_backward_has_constraint": true
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
    "formalization",
    "diagnose",
    "challenge",
    "approach",
    "validate"
  ],
  "n_experiment_analysis_records": 2,
  "provenance_action_sequence": [
    "project.init",
    "project.advance",
    "project.advance",
    "project.backward",
    "project.advance",
    "project.advance",
    "project.advance",
    "project.advance"
  ],
  "t4_transitions": [
    {
      "from": "diagnose",
      "to": "formalization",
      "carried": "the observed failure mode (contact slip) does not map to the current formalization objective \u2014 we need to add dynamics to the math"
    }
  ]
}
```

**Conclusion**: The integrated state machine is coherent end-to-end. A project can walk the full six-stage research loop, survive a backward transition with a learned constraint, handle both reproduction fail and pass paths, and produce a complete provenance trail. This is the load-bearing integration assertion that ties every phase together.

---

## Case 2: `skill → open trigger → human executes`

**Result**: ✅ PASS
**Purpose**: A skill proposes a trigger (propose_backward_trigger). stage_summary renders it. The human executes backward(). The OpenTrigger is marked resolved.

**Inputs**:
```
{
  "propose_call": {
    "trigger": "t2",
    "proposed_by": "formalization-check",
    "evidence": "reduces to standard POMDP that DESPOT solves"
  },
  "human_call": {
    "trigger": "t2",
    "carried_constraint": "reframe to avoid trivial reduction"
  }
}
```

**Expected**:
```
{
  "stage_summary_mentions_trigger": true,
  "stage_summary_mentions_proposer": true,
  "final_stage_after_backward": "significance",
  "trigger_resolved_with_note": true
}
```

**Actual**:
```
{
  "stage_summary_mentions_trigger": true,
  "stage_summary_mentions_proposer": true,
  "final_stage_after_backward": "significance",
  "trigger_resolved_with_note": true,
  "rendered_preview": "Project: proposed\nStage:   formalization  (entered 2026-04-11T06:36:26+00:00, 0d ago)\n\nForward guard:\ng2 (formalization): \u274c blocked\n  \u2717 formalization.md has content: missing or empty\n  \u2717 formalization_check with level in {formal_math, semi_formal}: 0 of 0 qualify\n  \u2717 structure_exploited is non-empty: 0 entries\n  \u2717 benchmarks.md has \u22651 benchmark under '## In scope': 0 benchmark(s) found\n  \u2717 benchma"
}
```

**Conclusion**: The skill → human → transition pipeline is intact. Skills surface what they found, the human reads it in `project stage`, and `project backward` turns the proposal into a real transition with a learned constraint.

---

## Summary

- **Total tests**: 2
- **Passed**: 2
- **Failed**: 0
- **Pass rate**: 100.0%
