# Test Report — `test_project_cli`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 8 total — **8 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `project init creates directory + templates`

**Result**: ✅ PASS
**Purpose**: `alpha-research project init demo --question '...'` must create output/demo/ with state.json, every template in PROJECT_TEMPLATES (the three canonical docs PROJECT.md, DISCUSSION.md, LOGS.md plus the stage artifacts), an initial stage_history entry, and one provenance record.

**Inputs**:
```
{
  "argv": [
    "project",
    "init",
    "demo",
    "--question",
    "tactile insertion for peg-in-hole",
    "--venue",
    "RSS"
  ],
  "cwd": "/tmp/pytest-of-zhb/pytest-32/test_project_init_creates_scaf0"
}
```

**Expected**:
```
{
  "exit_code": 0,
  "state.json_exists": true,
  "templates_written": [
    "PROJECT.md",
    "DISCUSSION.md",
    "LOGS.md",
    "hamming.md",
    "formalization.md",
    "benchmarks.md",
    "one_sentence.md"
  ],
  "initial_stage": "significance",
  "target_venue": "RSS"
}
```

**Actual**:
```
{
  "exit_code": 0,
  "state.json_exists": true,
  "templates_written": [
    "PROJECT.md",
    "DISCUSSION.md",
    "LOGS.md",
    "hamming.md",
    "formalization.md",
    "benchmarks.md",
    "one_sentence.md"
  ],
  "initial_stage": "significance",
  "target_venue": "RSS",
  "stdout_preview": "Project initialized: output/demo\n  Stage:   significance\n  Venue:   RSS\n  Templates written: 7\n\nRequired docs: PROJECT.md, DISCUSSION.md, LOGS.md\nNext: edit PROJECT.md + hamming.md, then run skills to"
}
```

**Conclusion**: `project init` is the single onboarding command. One call produces a project that is ready for the researcher to start filling in markdown.

---

## Case 2: `project init refuses to clobber existing project`

**Result**: ✅ PASS
**Purpose**: Re-running init on an existing project must fail loudly so the researcher cannot accidentally reset their state.json and lose their stage history.

**Inputs**:
```
{
  "first_call": [
    "project",
    "init",
    "demo",
    "--question",
    "q1"
  ],
  "second_call": [
    "project",
    "init",
    "demo",
    "--question",
    "q2"
  ]
}
```

**Expected**:
```
{
  "second_exit_nonzero": true,
  "error_mentions_already_exists": true
}
```

**Actual**:
```
{
  "second_exit_code": 1,
  "error_mentions_already_exists": true,
  "stderr_preview": "Project already exists at output/demo"
}
```

**Conclusion**: Project init is idempotency-safe: a typo or a script retry won't clobber real work.

---

## Case 3: `project stage renders guard check`

**Result**: ✅ PASS
**Purpose**: `project stage` must read state.json + run the current stage's forward guard and render both in a readable format.

**Inputs**:
```
{
  "argv": [
    "project",
    "stage",
    "/tmp/pytest-of-zhb/pytest-32/test_project_stage_prints_guar0/output/stage_demo"
  ]
}
```

**Expected**:
```
{
  "exit_code": 0,
  "output_contains": [
    "stage_demo",
    "significance",
    "g1",
    "blocked"
  ]
}
```

**Actual**:
```
{
  "exit_code": 0,
  "output_contains": {
    "stage_demo": true,
    "significance": true,
    "g1": true,
    "blocked": true
  },
  "stdout_preview": "Project: stage_demo\nStage:   significance  (entered 2026-04-11T06:36:27+00:00, 0d ago)\n\nForward guard:\ng1 (significance): \u274c blocked\n  \u2713 PROJECT.md has content: found\n  \u2717 significance_screen with human_confirmed=true: none found\n  \u2717 concrete_consequence is non-empty: missing\n  \u2713 durability_risk is not 'high': risk=unknown\n\nOpen backward triggers: none\n\nRecent transitions (most recent last):\n  [2026"
}
```

**Conclusion**: The researcher's single go-to command for 'where am I and what's blocking me' renders correctly on a fresh project.

---

## Case 4: `project advance refuses on empty project`

**Result**: ✅ PASS
**Purpose**: Without the required artifacts g1 must block and the CLI must exit non-zero with a helpful 'refused' message.

**Inputs**:
```
{
  "argv": [
    "project",
    "advance",
    "/tmp/pytest-of-zhb/pytest-32/test_project_advance_blocks_wi0/output/advance_block"
  ]
}
```

**Expected**:
```
{
  "exit_code_nonzero": true,
  "output_has_refused": true
}
```

**Actual**:
```
{
  "exit_code": 1,
  "output_has_refused": true,
  "output_preview": "g1 (significance): \u274c blocked\n  \u2713 PROJECT.md has content: found\n  \u2717 significance_screen with human_confirmed=true: none found\n  \u2717 concrete_consequence is non-empty: missing\n  \u2713 durability_risk is not 'high': risk=unknown\n\nAdvance refused. Add the missing artifacts or pass --force (with a --note)."
}
```

**Conclusion**: The CLI enforces the guard strictly and gives the researcher a clear signal to add missing artifacts rather than silently advancing.

---

## Case 5: `project advance transitions SIGNIFICANCE → FORMALIZE`

**Result**: ✅ PASS
**Purpose**: With PROJECT.md filled in and a confirmed significance_screen record, the advance verb must transition the project and persist the new stage to state.json.

**Inputs**:
```
{
  "artifacts": [
    "PROJECT.md (real content)",
    "significance_screen (human_confirmed)"
  ],
  "argv": [
    "project",
    "advance",
    "/tmp/pytest-of-zhb/pytest-32/test_project_advance_succeeds_0/output/advance_ok"
  ]
}
```

**Expected**:
```
{
  "exit_code": 0,
  "stage_after": "formalization",
  "output_has_both_stages": true
}
```

**Actual**:
```
{
  "exit_code": 0,
  "stage_after": "formalization",
  "output_preview": "\u2713 advanced significance \u2192 formalization  (g1)"
}
```

**Conclusion**: The happy-path advance from SIGNIFICANCE → FORMALIZE runs end-to-end: CLI reads state.json, runs guard, logs transition + provenance, rewrites state.json.

---

## Case 6: `project backward requires --constraint`

**Result**: ✅ PASS
**Purpose**: Backward transition CLI must require --constraint (typer option marked as required) and produce a transition that records the constraint.

**Inputs**:
```
{
  "missing_constraint": [
    "project",
    "backward",
    "t2",
    "..."
  ],
  "with_constraint": [
    "project",
    "backward",
    "t2",
    "...",
    "--constraint",
    "..."
  ]
}
```

**Expected**:
```
{
  "missing_exit_nonzero": true,
  "with_exit_zero": true,
  "stage_after": "significance",
  "constraint_recorded_in_history": true
}
```

**Actual**:
```
{
  "missing_exit_code": 2,
  "with_exit_code": 0,
  "stage_after": "significance",
  "history_triggers": [
    "init",
    "g1",
    "t2"
  ],
  "last_constraint": "formalization reduced to a known POMDP that DESPOT already solves"
}
```

**Conclusion**: The CLI enforces the doctrine-level requirement that backward transitions MUST carry a learned constraint.

---

## Case 7: `project log appends a weekly template`

**Result**: ✅ PASS
**Purpose**: `project log` must append (not overwrite) a new weekly entry with the five-line Tried/Expected/Observed/Concluded/Next template.

**Inputs**:
```
{
  "argv": [
    "project",
    "log",
    "/tmp/pytest-of-zhb/pytest-32/test_project_log_appends_weekl0/output/log_demo"
  ]
}
```

**Expected**:
```
{
  "exit_code": 0,
  "log_length_increased": true,
  "has_week_header": true,
  "has_all_five_fields": true
}
```

**Actual**:
```
{
  "exit_code": 0,
  "before_length": 2025,
  "after_length": 2124,
  "has_week_header": true,
  "has_all_five_fields": true
}
```

**Conclusion**: Weekly logging is a research-guideline mandate (§9.2). The CLI makes it a one-line action so there's no friction to maintaining the log.

---

## Case 8: `project status summarizes record counts`

**Result**: ✅ PASS
**Purpose**: `project status` must print the project's stage AND the counts for every JSONL record stream with at least one entry.

**Inputs**:
```
{
  "records_added": {
    "significance_screen": 1,
    "evaluation": 2
  },
  "argv": [
    "project",
    "status",
    "/tmp/pytest-of-zhb/pytest-32/test_project_status_summarizes0/output/status_demo"
  ]
}
```

**Expected**:
```
{
  "exit_code": 0,
  "mentions_project_name": true,
  "mentions_significance": true,
  "mentions_evaluation": true
}
```

**Actual**:
```
{
  "exit_code": 0,
  "mentions_project_name": true,
  "mentions_significance": true,
  "mentions_evaluation": true,
  "output_preview": "Project: status_demo\nStage:   significance  (entered 2026-04-11T06:36:27+00:00, 0d ago)\n\nForward guard:\ng1 (significance): \u2705 passes\n  \u2713 PROJECT.md has content: found\n  \u2713 significance_screen with human_confirmed=true: 1 record(s)\n  \u2713 concrete_consequence is non-empty: robots handle thin deformable objects in packing lines\n  \u2713 durability_risk is not 'high': risk=low\n\nOpen backward triggers: none\n\nRe"
}
```

**Conclusion**: status gives the researcher a one-screen pulse check on their project without requiring them to remember which subcommands exist.

---

## Summary

- **Total tests**: 8
- **Passed**: 8
- **Failed**: 0
- **Pass rate**: 100.0%
