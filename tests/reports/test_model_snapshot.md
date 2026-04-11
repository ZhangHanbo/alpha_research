# Test Report — `test_model_snapshot`

**Started at**: 2026-04-11T14:36:26
**Saved at**: 2026-04-11T14:36:26
**Tests**: 5 total — **5 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `SourceSnapshot defaults are clean`

**Result**: ✅ PASS
**Purpose**: A freshly constructed SourceSnapshot should have a 12-char id, vcs=none, is_dirty=False.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "id_length": 12,
  "vcs": "none",
  "is_dirty": false
}
```

**Actual**:
```
{
  "id_length": 12,
  "vcs": "none",
  "is_dirty": false
}
```

**Conclusion**: IDs are deterministic-length hex — safe for filenames and record keys.

---

## Case 2: `SourceSnapshot JSON round-trip`

**Result**: ✅ PASS
**Purpose**: save/load must preserve vcs_type, commit_sha, dirty flag and selected paths.

**Inputs**:
```
{
  "source_snapshot_id": "5dd0fc6cce35",
  "binding_id": "",
  "captured_at": "2026-04-11T14:36:26.699217",
  "vcs_type": "git",
  "repo_root": "/tmp/proj",
  "branch_name": "master",
  "commit_sha": "abc123",
  "is_dirty": true,
  "patch_path": null,
  "untracked_manifest_path": null,
  "source_fingerprint": "fp_abc",
  "selected_paths": [
    "src/main.py"
  ]
}
```

**Expected**:
```
{
  "vcs_type": "git",
  "commit_sha": "abc123",
  "is_dirty": true,
  "selected_paths": [
    "src/main.py"
  ]
}
```

**Actual**:
```
{
  "vcs_type": "git",
  "commit_sha": "abc123",
  "is_dirty": true,
  "selected_paths": [
    "src/main.py"
  ]
}
```

**Conclusion**: Snapshots are an append-only audit trail — persistence fidelity is non-negotiable.

---

## Case 3: `UnderstandingSnapshot starts with low confidence and empty maps`

**Result**: ✅ PASS
**Purpose**: Derived interpretations default to low confidence so consumers know they are weak signals.

**Inputs**:
```
{}
```

**Expected**:
```
{
  "confidence": "low",
  "architecture_map": {},
  "artifact_refs": []
}
```

**Actual**:
```
{
  "confidence": "low",
  "architecture_map": {},
  "artifact_refs": []
}
```

**Conclusion**: Low confidence forces downstream code to treat the snapshot as a hypothesis, not fact.

---

## Case 4: `ProjectSnapshot JSON round-trip`

**Result**: ✅ PASS
**Purpose**: save/load must preserve kind, source id, and summary across disk.

**Inputs**:
```
{
  "snapshot_id": "fc6421180196",
  "project_id": "proj1",
  "created_at": "2026-04-11T14:36:26.703209",
  "snapshot_kind": "milestone",
  "parent_snapshot_id": null,
  "source_snapshot_id": "src1",
  "understanding_snapshot_id": "und1",
  "blackboard_path": null,
  "artifact_refs": [],
  "run_id": null,
  "summary": "Hit milestone M1",
  "note": "Ready for review"
}
```

**Expected**:
```
{
  "kind": "milestone",
  "source_id": "src1",
  "summary": "Hit milestone M1"
}
```

**Actual**:
```
{
  "kind": "milestone",
  "source_id": "src1",
  "summary": "Hit milestone M1"
}
```

**Conclusion**: ProjectSnapshot binds source+understanding together — the only reliable resume point.

---

## Case 5: `ResearchRun round-trips status and type`

**Result**: ✅ PASS
**Purpose**: A ResearchRun record should persist its run_type and initial RUNNING status.

**Inputs**:
```
{
  "run_id": "a4d3cbfe04af",
  "project_id": "proj1",
  "started_at": "2026-04-11T14:36:26.705569",
  "finished_at": null,
  "run_type": "digest",
  "question": "tactile insertion",
  "status": "running",
  "input_snapshot_id": null,
  "output_snapshot_id": null,
  "outputs": [],
  "summary": "",
  "error": ""
}
```

**Expected**:
```
{
  "run_type": "digest",
  "status": "running"
}
```

**Actual**:
```
{
  "run_type": "digest",
  "status": "running"
}
```

**Conclusion**: Runs can be cancelled / marked-complete out-of-process; persistence must be lossless.

---

## Summary

- **Total tests**: 5
- **Passed**: 5
- **Failed**: 0
- **Pass rate**: 100.0%
