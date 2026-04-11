# Test Report — `test_reports_templates`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 5 total — **5 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `digest template renders multi-paper summary`

**Result**: ✅ PASS
**Purpose**: Produce a weekly digest with rubric rows for each paper.

**Inputs**:
```
{
  "papers": [
    "Paper A",
    "Paper B"
  ],
  "title": "Weekly Digest"
}
```

**Expected**:
```
{
  "header": "# Research Digest: Weekly Digest",
  "contains_both": true,
  "contains_rubric_row": true
}
```

**Actual**:
```
{
  "header": "# Research Digest: Weekly Digest",
  "contains_both": true,
  "contains_rubric_row": true
}
```

**Conclusion**: Digest mode is stable and renders all rubric dimensions in a table.

---

## Case 2: `deep template renders single-paper evaluation`

**Result**: ✅ PASS
**Purpose**: Deep mode renders rubric + significance + task chain for one paper.

**Inputs**:
```
{
  "paper": "Deep Eval Paper"
}
```

**Expected**:
```
{
  "header": "# Paper Evaluation: Deep Eval Paper",
  "contains_hamming": true,
  "contains_rubric": true
}
```

**Actual**:
```
{
  "header": "# Paper Evaluation: Deep Eval Paper",
  "contains_hamming": true,
  "contains_rubric": true
}
```

**Conclusion**: Deep mode is the canonical single-paper artefact used by the CLI evaluate verb.

---

## Case 3: `deep mode on empty list returns a no-op header`

**Result**: ✅ PASS
**Purpose**: An empty evaluations list in deep mode should return a friendly placeholder.

**Inputs**:
```
{
  "evaluations": []
}
```

**Expected**:
```
# No evaluations provided.
```

**Actual**:
```
# No evaluations provided.
```

**Conclusion**: The template never crashes on empty input — it degrades gracefully.

---

## Case 4: `survey mode raises a helpful ValueError`

**Result**: ✅ PASS
**Purpose**: The survey mode was removed in R3. Calls must point at alpha_review.sdk.run_write.

**Inputs**:
```
{
  "mode": "survey"
}
```

**Expected**:
```
{
  "raises": true,
  "mentions_run_write": true
}
```

**Actual**:
```
{
  "raises": true,
  "message": "mode='survey' was removed in the R3 refactor. For LaTeX literature surveys, use alpha_review.sdk.run_write or the `alpha-research survey` CLI, which delegate to alpha_review's run_write pipeline."
}
```

**Conclusion**: The error message guides the caller to the new API instead of silently failing.

---

## Case 5: `unknown mode raises ValueError`

**Result**: ✅ PASS
**Purpose**: generate_report should reject any mode other than digest/deep/survey.

**Inputs**:
```
{
  "mode": "foobar"
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

**Conclusion**: Unknown modes fail loudly rather than default to a lossy output.

---

## Summary

- **Total tests**: 5
- **Passed**: 5
- **Failed**: 0
- **Pass rate**: 100.0%
