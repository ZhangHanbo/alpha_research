# Calibration Tests

Mechanical tests that verify the review system's rules produce correct outputs
for known inputs. No LLM calls or network access required.

## Running

```bash
# Run all calibration tests
/home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest tests/calibration/test_calibration.py -v

# Run a single section
/home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest tests/calibration/test_calibration.py -v -k "TestVenueCalibration"
/home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest tests/calibration/test_calibration.py -v -k "TestGraduatedPressure"
/home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest tests/calibration/test_calibration.py -v -k "TestAntiPatternDetection"
/home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest tests/calibration/test_calibration.py -v -k "TestVerdictComputation"
/home/zhb/anaconda3/envs/alpha_research/bin/python -m pytest tests/calibration/test_calibration.py -v -k "TestFindingStructure"
```

## Test Sections

### A. Venue Calibration (`TestVenueCalibration`)

Verifies that different target venues produce appropriately calibrated prompts
and that acceptance-rate ordering is monotonically non-decreasing from strict
(IJRR) to lenient (IROS).

### B. Graduated Pressure (`TestGraduatedPressure`)

Checks that the three-iteration graduated pressure schedule works:
- Iteration 1: structural scan (shorter, Five-Minute Fatal Flaw Scan)
- Iteration 2: full review (longer, all attack vectors from 3.1--3.6)
- Iteration 3+: focused re-review (previous findings, pairwise comparison)

### C. Anti-Pattern Detection (`TestAntiPatternDetection`)

Constructs adversarial review inputs to verify the meta-reviewer catches:
- Dimension averaging (accept verdict despite many serious findings)
- Severity regression (previous fatal downgraded to minor)
- Specificity violations (vague critiques with no evidence)
- Short steel-man (fewer than 3 sentences)
- Non-actionable findings (empty `what_would_fix`)
- Ungrounded findings (empty `grounding`)
- Also verifies a properly structured review passes all checks.

### D. Verdict Computation (`TestVerdictComputation`)

Tests the mechanical verdict rules from `ReviewAgent.compute_verdict`:
- 0 findings -> ACCEPT
- 1 fatal -> REJECT
- 1 fixable serious -> WEAK_ACCEPT
- 2 serious (mixed fixability) -> WEAK_REJECT
- 3+ serious -> WEAK_REJECT
- 3+ unresolvable serious -> REJECT
- All minor -> ACCEPT
- Mixed serious + minor -> driven by serious count

### E. Finding Structure (`TestFindingStructure`)

Validates that the `Finding` Pydantic model enforces required fields and that
the quality metric functions correctly detect missing or vague content in
`what_would_fix`, `grounding`, `falsification`, and `what_is_wrong`.

## Interpreting Failures

Each test targets a specific rule. A failure means either:
1. The rule implementation changed (check `review_agent.py`, `review_quality.py`,
   or `review_system.py` for regressions).
2. The test expectation is out of date with an intentional rule change (update
   the test to match the new rule).
