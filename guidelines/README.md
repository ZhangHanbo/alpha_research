# Guidelines — Index

This directory holds every doctrinal, specification, architecture, and
historical document that shapes `alpha_research`. It is organized into four
clusters so a reader can find the right layer without scanning every file.

```
guidelines/
├── doctrine/        — stable standards the system encodes
├── spec/            — operational specs (state machines, metrics, plans)
├── architecture/    — current implementation map
└── history/         — superseded plans retained for lineage
```

**Navigation rule of thumb:**
- *"What does good research look like?"* → `doctrine/`
- *"What does the system do, step by step?"* → `spec/`
- *"What is the code actually doing today?"* → `architecture/`
- *"Why is the codebase shaped the way it is?"* → `history/`

---

## `doctrine/` — the standards

Stable. Change rarely. Treated as the ground truth the skills encode.

| File | Role |
|---|---|
| [`doctrine/research_guideline.md`](doctrine/research_guideline.md) | How to do top-tier robotics research. Hamming/Consequence/Durability/Compounding tests, the task→problem→challenge→approach chain, Appendix B rubric (B.1–B.7). |
| [`doctrine/review_guideline.md`](doctrine/review_guideline.md) | Adversarial review at top-venue standard. Six attack vectors, steel-man protocol, fatal/serious/minor hierarchy, falsifiability rule. |
| [`doctrine/review_standards_reference.md`](doctrine/review_standards_reference.md) | Venue-specific calibration data (RSS, CoRL, NeurIPS, ICML, ICLR, IJRR, T-RO, RA-L, HRI, ICRA, IROS, CVPR) plus foundational texts on reviewing. |
| [`doctrine/problem_formulation_guide.md`](doctrine/problem_formulation_guide.md) | How to write a survey problem formulation: motivate before formalize, five components, displayed objective equation, 90% rule, anti-patterns. |

## `spec/` — the operational specifications

The machine-executable half of the doctrine. State machines, metrics,
iteration protocols, and the active implementation plan.

| File | Role |
|---|---|
| [`spec/research_plan.md`](spec/research_plan.md) | The two-layer state machine: outer stages **SIGNIFICANCE → FORMALIZE → DIAGNOSE → CHALLENGE → APPROACH → VALIDATE** with forward guards `g1..g5` and backward triggers `t2..t15`; SM-1..SM-6 sub-state-machine specs for each component. |
| [`spec/review_plan.md`](spec/review_plan.md) | Machine-evaluable metrics for every review attack vector (§1), three-agent architecture with meta-reviewer (§2), research–review iteration protocol (§3), graduated pressure + anti-collapse mechanisms. |
| `spec/implementation_plan.md` *(to be written)* | The compact, state-machine-integrated plan for the real research loop — artifacts, skills, pipelines, CLI verbs, and how they transition. |

## `architecture/` — what the code does today

| File | Role |
|---|---|
| [`architecture/tools_and_skills.md`](architecture/tools_and_skills.md) | The current skills-first architecture: 11 Claude Code skills, 5 Python pipelines, JSONL record types, `alpha_review` integration, progressive-disclosure invocation patterns. |

## `history/` — superseded plans retained for lineage

Useful for *why* decisions were made; not a source of truth for what exists.

| File | Role |
|---|---|
| [`history/refactor_plan.md`](history/refactor_plan.md) | R0–R9 migration plan from the T1–T10 agent-centric codebase to the skills-first layout. Phases complete per git log. |
| [`history/TASKS.md`](history/TASKS.md) | Task breakdown that operationalized `refactor_plan.md`. |
| [`history/project_lifecycle_revision_plan.md`](history/project_lifecycle_revision_plan.md) | Ambitious project-lifecycle design (`ProjectManifest`/`ProjectState`/`ProjectSnapshot`, git-worktree resume, source fingerprinting). Mostly superseded by the simpler "a project is a directory" model in `spec/implementation_plan.md`. |
| [`history/FRONTEND.md`](history/FRONTEND.md) | Plan for the Next.js + CopilotKit + three-view dashboard. Deferred in favor of CLI-first simplicity. |
| [`history/vibe_research_survey.md`](history/vibe_research_survey.md) | Open-source landscape review that informed `FRONTEND.md`. |

---

## Relationships

```
doctrine ──encodes─▶ skills (.claude/skills/*/SKILL.md)
                     │
                     │ invoked by
                     ▼
spec ─────drives───▶ pipelines (src/alpha_research/pipelines/)
                     │
                     │ orchestrated by
                     ▼
architecture ──maps─▶ src/alpha_research/ (the actual code)
                     │
                     │ lineage from
                     ▼
history ──explains──▶ why the code is shaped this way
```

When a reader lands here for the first time, the fastest path to
understanding is:
1. `doctrine/research_guideline.md` Parts II–III  *(what research IS)*
2. `spec/research_plan.md` §1 *(the state machine)*
3. `architecture/tools_and_skills.md` Parts I–II *(what we built)*
4. `spec/implementation_plan.md` *(what we're building next)*
