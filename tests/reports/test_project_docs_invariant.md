# Test Report — `test_project_docs_invariant`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 5 total — **5 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `project init scaffolds PROJECT.md + DISCUSSION.md + LOGS.md`

**Result**: ✅ PASS
**Purpose**: Every research project must carry the three canonical docs so agents always have a stable place to record technical details, discussions, and revision history.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_init_creates_three_canoni0/canonical_docs_demo",
  "required_docs": [
    "PROJECT.md",
    "DISCUSSION.md",
    "LOGS.md"
  ]
}
```

**Expected**:
```
{
  "PROJECT.md": true,
  "DISCUSSION.md": true,
  "LOGS.md": true
}
```

**Actual**:
```
{
  "PROJECT.md": true,
  "DISCUSSION.md": true,
  "LOGS.md": true
}
```

**Conclusion**: Three-doc invariant is enforced at init time. REQUIRED_DOCS is the single source of truth and the test asserts both the exact set of names and their presence on disk.

---

## Case 2: `canonical docs are populated from the templates`

**Result**: ✅ PASS
**Purpose**: After init, each required doc must be non-trivial and templated with the project id.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_canonical_docs_have_meani0/content_demo"
}
```

**Expected**:
```
{
  "PROJECT.md length > 200": true,
  "DISCUSSION.md length > 200": true,
  "LOGS.md length > 200": true,
  "LOGS.md has AGENT_REVISIONS_END marker": true
}
```

**Actual**:
```
{
  "PROJECT.md length": 1664,
  "DISCUSSION.md length": 1299,
  "LOGS.md length": 2025,
  "LOGS.md has AGENT_REVISIONS_END marker": true
}
```

**Conclusion**: Templates are non-empty and interpolated with the project id. LOGS.md carries the anchor that append_revision_log relies on.

---

## Case 3: `append_revision_log injects entry above AGENT_REVISIONS_END`

**Result**: ✅ PASS
**Purpose**: append_revision_log should insert the structured revision entry directly before the AGENT_REVISIONS_END marker so subsequent entries remain chronological and nested under the '## Agent revisions' section.

**Inputs**:
```
{
  "agent": "adversarial-review",
  "stage": "significance",
  "target": "PROJECT.md \u00a7 Scope",
  "revision": "Narrowed scope to rigid pegs only."
}
```

**Expected**:
```
{
  "entry_before_marker": true,
  "contains_agent_name": true,
  "contains_revision_text": true,
  "contains_feedback": true
}
```

**Actual**:
```
{
  "entry_before_marker": true,
  "contains_agent_name": true,
  "contains_revision_text": true,
  "contains_feedback": true,
  "timestamp": "2026-04-11T06:36:27Z"
}
```

**Conclusion**: Agents can now append a human-readable audit entry to LOGS.md that sits next to — and never displaces — the weekly log section.

---

## Case 4: `append_revision_log also appends a provenance record`

**Result**: ✅ PASS
**Purpose**: Every revision entry in LOGS.md should have a matching provenance.jsonl record so the audit trail stays synchronized across the markdown log and the structured store.

**Inputs**:
```
{
  "agent": "paper-evaluate",
  "stage": "formalization"
}
```

**Expected**:
```
{
  "provenance_records_for_agent": 1,
  "stage": "formalization"
}
```

**Actual**:
```
{
  "provenance_records_for_agent": 1,
  "stage": "formalization"
}
```

**Conclusion**: Dual-write keeps markdown and JSONL in lockstep so a reviewer can follow either representation without drift.

---

## Case 5: `append_revision_log refuses to create LOGS.md implicitly`

**Result**: ✅ PASS
**Purpose**: The helper must raise FileNotFoundError when LOGS.md is missing — callers should run `project init` first instead of the helper silently auto-creating a stub.

**Inputs**:
```
{
  "project_dir": "/tmp/pytest-of-zhb/pytest-32/test_append_revision_log_missi0/not_a_project"
}
```

**Expected**:
```
{
  "raises_FileNotFoundError": true
}
```

**Actual**:
```
{
  "raises_FileNotFoundError": true
}
```

**Conclusion**: Fail-fast makes the three-doc invariant load-bearing — every agent that revises a project can trust LOGS.md exists or learn immediately that it does not.

---

## Summary

- **Total tests**: 5
- **Passed**: 5
- **Failed**: 0
- **Pass rate**: 100.0%
