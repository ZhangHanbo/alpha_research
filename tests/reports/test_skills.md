# Test Report — `test_skills`

**Started at**: 2026-04-11T14:36:27
**Saved at**: 2026-04-11T14:36:27
**Tests**: 7 total — **7 passed**, **0 failed**

> ✅ **All tests passed.**

---

## Case 1: `parse_frontmatter extracts all fields`

**Result**: ✅ PASS
**Purpose**: The frontmatter parser is a stdlib-only implementation (no PyYAML dependency) that extracts the five fields the runtime cares about: name, description, model, allowed-tools, research_stages.

**Inputs**:
```
{
  "text_preview": "---\nname: paper-evaluate\ndescription: Evaluate a robotics paper against the Appendix B rubric.\nallowed-tools: [Bash, Read, Write, Grep]\nmodel: claude-sonnet-4-6\nresearch_stages: [significance, approac"
}
```

**Expected**:
```
{
  "name": "paper-evaluate",
  "model": "claude-sonnet-4-6",
  "allowed_tools": [
    "Bash",
    "Read",
    "Write",
    "Grep"
  ],
  "research_stages": [
    "significance",
    "approach"
  ]
}
```

**Actual**:
```
{
  "name": "paper-evaluate",
  "model": "claude-sonnet-4-6",
  "allowed_tools": [
    "Bash",
    "Read",
    "Write",
    "Grep"
  ],
  "research_stages": [
    "significance",
    "approach"
  ]
}
```

**Conclusion**: Parsing SKILL.md frontmatter requires no external dependency. All bracketed-list fields are split correctly and plain strings are preserved verbatim.

---

## Case 2: `parse_frontmatter returns None on missing frontmatter`

**Result**: ✅ PASS
**Purpose**: Files without a ``---``-delimited frontmatter header are treated as 'not a skill file' and return None.

**Inputs**:
```
{
  "text": "# Just a markdown file\n\nNo frontmatter here.\n"
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

**Conclusion**: The parser degrades cleanly: any non-skill markdown file returns None rather than raising. Callers can treat None as 'not a skill'.

---

## Case 3: `all 11 skills declare research_stages`

**Result**: ✅ PASS
**Purpose**: Phase 3 adds a research_stages frontmatter field to every SKILL.md so the runtime can warn on out-of-stage invocation. This test ensures the migration is complete.

**Inputs**:
```
{
  "skills_dir": "/home/zhb/projects/alpha_research/skills"
}
```

**Expected**:
```
{
  "discovered_slugs_superset_of": [
    "adversarial-review",
    "challenge-articulate",
    "classify-capability",
    "concurrent-work-check",
    "diagnose-system",
    "experiment-audit",
    "formalization-check",
    "gap-analysis",
    "identify-method-gaps",
    "paper-evaluate",
    "significance-screen"
  ],
  "all_have_research_stages": true
}
```

**Actual**:
```
{
  "discovered_slugs": [
    "adversarial-review",
    "benchmark-survey",
    "challenge-articulate",
    "classify-capability",
    "concurrent-work-check",
    "diagnose-system",
    "experiment-analyze",
    "experiment-audit",
    "experiment-design",
    "formalization-check",
    "gap-analysis",
    "identify-method-gaps",
    "paper-evaluate",
    "project-understanding",
    "significance-screen"
  ],
  "missing_expected": [],
  "slugs_without_research_stages": [],
  "stages_per_skill": {
    "adversarial-review": [
      "validate"
    ],
    "benchmark-survey": [
      "formalization",
      "approach"
    ],
    "challenge-articulate": [
      "challenge"
    ],
    "classify-capability": [
      "significance",
      "validate"
    ],
    "concurrent-work-check": [
      "challenge",
      "approach",
      "validate"
    ],
    "diagnose-system": [
      "diagnose"
    ],
    "experiment-analyze": [
      "diagnose",
      "validate"
    ],
    "experiment-audit": [
      "validate"
    ],
    "experiment-design": [
      "diagnose",
      "approach",
      "validate"
    ],
    "formalization-check": [
      "formalization",
      "approach"
    ],
    "gap-analysis": [
      "significance"
    ],
    "identify-method-gaps": [
      "approach"
    ],
    "paper-evaluate": [
      "significance",
      "approach"
    ],
    "project-understanding": [
      "diagnose",
      "approach"
    ],
    "significance-screen": [
      "significance"
    ]
  }
}
```

**Conclusion**: Every skill now knows which research stage(s) it's valid in. The check_skill_stage function can give a meaningful verdict for every skill, with no 'unknown_stage' fallback.

---

## Case 4: `check_skill_stage returns in_stage`

**Result**: ✅ PASS
**Purpose**: Invoking significance-screen while the project is in the SIGNIFICANCE stage must return verdict='in_stage'.

**Inputs**:
```
{
  "skill_name": "significance-screen",
  "project_stage": "significance"
}
```

**Expected**:
```
{
  "verdict": "in_stage"
}
```

**Actual**:
```
{
  "verdict": "in_stage",
  "valid_stages": [
    "significance"
  ],
  "message": "significance-screen is valid in significance"
}
```

**Conclusion**: The happy path: a stage-bound skill in its declared stage reports in_stage and the CLI proceeds without warning.

---

## Case 5: `check_skill_stage returns out_of_stage with force-override hint`

**Result**: ✅ PASS
**Purpose**: Invoking adversarial-review (valid in VALIDATE only) from SIGNIFICANCE must return out_of_stage AND include a hint about the --force override path.

**Inputs**:
```
{
  "skill_name": "adversarial-review",
  "project_stage": "significance"
}
```

**Expected**:
```
{
  "verdict": "out_of_stage",
  "valid_stages_include": "validate",
  "message_mentions_force": true
}
```

**Actual**:
```
{
  "verdict": "out_of_stage",
  "valid_stages": [
    "validate"
  ],
  "message": "\u26a0 adversarial-review is declared valid in stages ['validate'] but the project is currently in 'significance'. Pass --force to invoke anyway; the override will be logged."
}
```

**Conclusion**: Out-of-stage invocation is warned, not blocked. The CLI surfaces the warning and explains how to override — the researcher keeps full control.

---

## Case 6: `check_skill_stage flags unknown skill`

**Result**: ✅ PASS
**Purpose**: A typo'd skill name must return unknown_skill so the CLI can surface a typo-style error rather than silently doing nothing.

**Inputs**:
```
{
  "skill_name": "nonexistent-skill",
  "project_stage": "significance"
}
```

**Expected**:
```
{
  "verdict": "unknown_skill"
}
```

**Actual**:
```
{
  "verdict": "unknown_skill",
  "message": "Unknown skill 'nonexistent-skill'; did you mean one of ['adversarial-review', 'benchmark-survey', 'challenge-articulate', 'classify-capability', 'concurrent-work-check', 'diagnose-system', 'experiment-analyze', 'experiment-audit', 'experiment-design', 'formalization-check', 'gap-analysis', 'identify-method-gaps', 'paper-evaluate', 'project-understanding', 'significance-screen']?"
}
```

**Conclusion**: Unknown skills are flagged with the available set, so the researcher can see at a glance what they could have meant.

---

## Case 7: `skill stage assignments match implementation_plan.md Part VI`

**Result**: ✅ PASS
**Purpose**: Each of the 11 skills must declare exactly the stages the plan assigns them. This is the single-source-of-truth check.

**Inputs**:
```
{
  "expected_stage_map": {
    "significance-screen": [
      "significance"
    ],
    "gap-analysis": [
      "significance"
    ],
    "paper-evaluate": [
      "significance",
      "approach"
    ],
    "formalization-check": [
      "formalization",
      "approach"
    ],
    "diagnose-system": [
      "diagnose"
    ],
    "challenge-articulate": [
      "challenge"
    ],
    "concurrent-work-check": [
      "challenge",
      "approach",
      "validate"
    ],
    "identify-method-gaps": [
      "approach"
    ],
    "experiment-audit": [
      "validate"
    ],
    "adversarial-review": [
      "validate"
    ],
    "classify-capability": [
      "significance",
      "validate"
    ]
  }
}
```

**Expected**:
```
{
  "significance-screen": [
    "significance"
  ],
  "gap-analysis": [
    "significance"
  ],
  "paper-evaluate": [
    "significance",
    "approach"
  ],
  "formalization-check": [
    "formalization",
    "approach"
  ],
  "diagnose-system": [
    "diagnose"
  ],
  "challenge-articulate": [
    "challenge"
  ],
  "concurrent-work-check": [
    "challenge",
    "approach",
    "validate"
  ],
  "identify-method-gaps": [
    "approach"
  ],
  "experiment-audit": [
    "validate"
  ],
  "adversarial-review": [
    "validate"
  ],
  "classify-capability": [
    "significance",
    "validate"
  ]
}
```

**Actual**:
```
{
  "significance-screen": [
    "significance"
  ],
  "gap-analysis": [
    "significance"
  ],
  "paper-evaluate": [
    "significance",
    "approach"
  ],
  "formalization-check": [
    "formalization",
    "approach"
  ],
  "diagnose-system": [
    "diagnose"
  ],
  "challenge-articulate": [
    "challenge"
  ],
  "concurrent-work-check": [
    "challenge",
    "approach",
    "validate"
  ],
  "identify-method-gaps": [
    "approach"
  ],
  "experiment-audit": [
    "validate"
  ],
  "adversarial-review": [
    "validate"
  ],
  "classify-capability": [
    "significance",
    "validate"
  ]
}
```

**Conclusion**: Stage bindings are faithful to the plan — invoking adversarial-review from SIGNIFICANCE will warn, invoking paper-evaluate from SIGNIFICANCE will not, etc.

---

## Summary

- **Total tests**: 7
- **Passed**: 7
- **Failed**: 0
- **Pass rate**: 100.0%
