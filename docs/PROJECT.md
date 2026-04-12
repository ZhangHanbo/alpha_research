# Alpha Research — Project Overview

**A skills-first robotics research system.** Encodes doctoral-level
research judgment into Claude Code Agent Skills paired with Python
pipelines and the `alpha_review` API dependency. Drives a two-layer
state machine (SIGNIFICANCE → FORMALIZE → DIAGNOSE → CHALLENGE →
APPROACH → VALIDATE) with backward error detection, and runs an
adversarial research-review convergence loop at top-venue standard.

This document is the authoritative design reference. For how to
**install and run** Alpha Research, see the root `README.md`. For the
**active implementation plan** and roadmap, see `docs/PLAN.md`. For
the **venue calibration surveys** that grounded the review standards,
see `docs/SURVEY.md`. For **design decisions and migration history**,
see `docs/DISCUSSION.md`. For the **append-only development log**,
see `docs/LOGS.md`.

---

## Table of Contents

1. [Purpose and Philosophy](#1-purpose-and-philosophy)
2. [Architecture at a Glance](#2-architecture-at-a-glance)
3. [The Two-Layer State Machine](#3-the-two-layer-state-machine)
4. [Research Doctrine](#4-research-doctrine)
5. [Review Doctrine](#5-review-doctrine)
6. [Problem Formulation Methodology](#6-problem-formulation-methodology)
7. [Skills-First Architecture](#7-skills-first-architecture)
8. [Module Layout](#8-module-layout)
9. [Public API — The CLI Verbs](#9-public-api--the-cli-verbs)
10. [Per-Project Artifacts](#10-per-project-artifacts)
11. [The Experiment Interface](#11-the-experiment-interface)
12. [Takeaways from the R0-R9 Refactor](#12-takeaways-from-the-r0-r9-refactor)

---

## 1. Purpose and Philosophy

### 1.1 The problem

Keeping up with robotics/AI literature is a bottleneck for every
researcher. Volume is overwhelming. The critical task — identifying
what matters, why it matters, and how it connects to your work —
requires deep domain understanding that keyword search doesn't
provide. And *doing* research is harder still: formalizing problems
precisely, diagnosing minimal-system failures, articulating
structural barriers, designing experiments that actually test
contributions, surviving adversarial review at top venues.

### 1.2 The hypothesis

An LLM agent equipped with domain-specific tools (paper search,
PDF parsing, persistent records), a researcher-authored constitution,
and the research guidelines as its evaluation framework can conduct
autonomous research cycles that surface genuinely useful insights —
significance assessments, formal problem structure analyses,
bottleneck diagnoses, trend analyses, gap identification, and
research direction proposals — not just paper summaries. Paired with
a reviewer agent that applies venue-calibrated attack vectors and a
meta-reviewer that catches toothless critiques, it can drive an
adversarial convergence loop that produces submission-ready work.

### 1.3 What this is NOT

Not a replacement for research thinking. The agent **cannot** assess
problem significance (the Hamming test), write formal problem
definitions (Tedrake's point), develop research taste, or run the
robot. The human provides significance judgments, formalizations,
taste, and execution at checkpoints. The agent provides breadth,
structure, consistency, and the ability to systematically screen
large volumes of literature — and of evidence — against the
guidelines' standards.

### 1.4 Design invariants

1. **Zero new tools.** Every capability reachable through Claude
   Code's built-ins (`Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`,
   `Task`) plus the `alpha_review` Python module. No MCP server.
2. **Skills encode doctrine.** 15 `SKILL.md` files under `skills/`
   are the entire deliverable for domain knowledge. Pipelines are
   deterministic orchestration that invokes skills.
3. **JSONL is the persistence model.** Per-record-type append-only
   files under the project directory. No new database. The global
   `alpha_review.ReviewState` SQLite store holds only the
   `alpha_review`-owned papers/themes.
4. **Bash is the bridge.** Any Python function in `alpha_review` or
   `alpha_research` is one `bash python -c "..."` away from a skill.
5. **Project-as-directory.** `tar czf project.tgz output/<name>/`
   is a complete backup. No registry. No implicit state.
6. **The human is always the outermost controller.** The agent never
   advances research stages on its own; every transition goes
   through a CLI verb that checks a forward guard or through an
   explicit human `project backward` command.

### 1.5 The three-canonical-docs invariant (per project)

Every research project — not just `alpha_research` itself — must
include and maintain three docs at its root:

- `PROJECT.md` — technical details, kept up to date
- `DISCUSSION.md` — records discussions between the user and agents
- `LOGS.md` — append-only log with two sections: `## Agent revisions`
  (automated entries above an `<!-- AGENT_REVISIONS_END -->` anchor)
  and `## Weekly log` (human `### Week of YYYY-MM-DD` entries)

This is enforced in `src/alpha_research/templates/__init__.py` via
`REQUIRED_DOCS = ("PROJECT.md", "DISCUSSION.md", "LOGS.md")`, and
`src/alpha_research/project.py` provides `append_revision_log()`
that inserts entries at the marker and dual-writes a
`provenance.jsonl` record. See `docs/DISCUSSION.md` three-canonical-docs
invariant entry for the motivation.

---

## 2. Architecture at a Glance

```
┌─────────────────────────────────────────────────────────────────────┐
│  Claude Code                                                        │
│    reads skills/*/SKILL.md when description matches                 │
│    invokes tools: Bash, Read, Write, Edit, Grep, Glob, Task         │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alpha_research                                                     │
│                                                                     │
│   Skills (markdown)          Pipelines (Python)                     │
│   ├─ paper-evaluate          ├─ literature_survey  ─┐               │
│   ├─ significance-screen     ├─ method_survey       │               │
│   ├─ formalization-check     ├─ frontier_mapping    │ call skills   │
│   ├─ adversarial-review  ◀───┤  research_review_loop│ via claude -p │
│   └─ ... (11 more)           └─ state_machine (pure)                │
│                                                                     │
│   Helpers                    Records                                │
│   ├─ metrics/verdict.py      └─ JSONL project memory                │
│   ├─ scripts/sympy_verify       (evaluation/finding/review/         │
│   └─ scripts/audit_stats          frontier/...)                     │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│  alpha_review (editable dependency at ../alpha_review)              │
│    apis.search_all, s2_*, openalex_search, unpaywall_pdf_url, ...   │
│    scholar.scholar_search_papers                                    │
│    models.ReviewState (SQLite-backed papers/themes store)           │
│    sdk.run_plan/scope/search/read/write (the survey pipeline)       │
│    alpha-review CLI (entry point used by literature_survey pipe)    │
└─────────────────────────────────────────────────────────────────────┘
```

### 2.1 Artifacts are the state; skills and verbs are the transitions

The state machine is **executable** because it is bound to files on
disk. A project's full state at any instant = the contents of its
directory. The CLI and skills are deterministic transformations over
that state.

```
                      state.json (current stage + history)
                             ▲
                             │ reads/writes
                             │
  ┌──────────┐   invokes   ┌─┴────────────┐   writes   ┌──────────────┐
  │ human    │────────────▶│  CLI verbs   │───────────▶│ artifacts    │
  │ (author) │             │  / pipelines │            │ (md + jsonl) │
  └──────────┘             │  / skills    │            └──────────────┘
      ▲                    └──────────────┘                    │
      │                            │                            │
      │   reads                    │ invokes                    │ read by
      │                            ▼                            │
      │                     ┌──────────────┐                    │
      └─────────────────────│ skills       │◀───────────────────┘
                            │ (SKILL.md)   │
                            └──────────────┘
```

### 2.2 Three-layer model

| Layer | Content | Example |
|---|---|---|
| **Doctrine** | Stable standards encoded as skills | `research_guideline.md` Appendix B rubric → `paper-evaluate` skill |
| **Spec** | Operational machine-executable specifications | state machine `g1..g5`, `t2..t15`; review metrics §1.1-1.8 |
| **Architecture** | Current code layout + experiment interface convention | `pipelines/` + `records/` + `skills/` + `<code_dir>/experiments/` |

Doctrine informs spec; spec drives architecture; architecture executes
doctrine. The three layers stay in lockstep via the skills-first
invariant (every skill cites the doctrine sections it encodes).

---

## 3. The Two-Layer State Machine

The research process is a two-layer state machine. The outer layer
controls stage transitions — including backward transitions
triggered by specific discoveries that invalidate earlier
conclusions. The inner layer is a search process within each stage —
iterating over candidate sub-states until one satisfies the forward
transition guard. Most of the time in research is spent in the inner
layer. The critical skill is recognizing when a backward transition
is needed rather than continuing to search within a stage that was
built on a flawed premise.

```
OUTER LAYER — stage transitions with backward edges

                    ┌──────────────────────────────────────────────┐
                    │          BACKWARD TRANSITIONS                │
                    │  (each triggered by a specific discovery)    │
                    └──────────────────────────────────────────────┘

                          t2 ┌───────────────────── t7
                          │  │          t4 ┌──────── │ ── t10
                          │  │          │  │  t6 ┌── │ ─── │ ── t12
                          ▼  ▼          ▼  ▼  ▼  ▼  ▼     ▼     ▼

 ┌─────────────┐ g1  ┌─────────┐ g2  ┌─────────┐ g3  ┌─────────┐
 │ SIGNIFICANCE├────►│FORMALIZE├────►│ DIAGNOSE├────►│CHALLENGE│
 └──────▲──────┘     └────▲────┘     └────▲────┘     └────┬────┘
        │                 │               │                │
        │                 │               │             g4 │
        │                 │               │                ▼
        │            t9   │          t11  │          ┌─────────┐
        │◄────────────────│◄──────────────│◄─────────┤APPROACH │
        │    t5           │    t8         │          └────┬────┘
        │                 │               │               │
        │                 │               │            g5 │
        │                 │               │               ▼
        │            t14  │               │          ┌─────────┐
        └─────────────────┘◄──────────────┘◄─────────┤VALIDATE │
              t13                  t15               └─────────┘
```

### 3.1 Forward guards `g1..g5` (verbatim from research_plan.md §1)

| Guard | Transition | Condition |
|---|---|---|
| **g1** | SIGNIFICANCE → FORMALIZE | Problem passes ≥1 significance test per category (Hamming + Consequence + Durability + Compounding); at least one `significance_screen` record with concrete `consequence: str`; `durability_risk != "high"`; human has explicitly confirmed the Hamming test (`human_confirmed: true`). |
| **g2** | FORMALIZE → DIAGNOSE | `formalization.md` exists and is non-empty; latest `formalization_check` has `formalization_level ∈ {formal_math, semi_formal}`; at least one `structure_exploited` entry; sympy verification of any claimed structural property passed (or explicitly flagged unverifiable); `benchmarks.md` exists with ≥1 chosen benchmark under "In scope" carrying rationale, success criterion, ≥1 published baseline number, saturation assessment; latest `benchmark_survey` record has `human_confirmed: true`. |
| **g3** | DIAGNOSE → CHALLENGE | For every in-scope benchmark, ≥1 `experiment_analysis` record with `reproduction_of` set and `reproducibility ∈ {pass, partial}`; ≥1 `diagnosis` record with `failure_mapped_to_formal_term: str` non-null; the mapped failure references a non-stale `experiments/<exp_id>/` — code, results, and `source.md` are aligned. |
| **g4** | CHALLENGE → APPROACH | Latest `challenge` record has `challenge_type == "structural"` (not `"resource_complaint"`); `implied_method_class: str` non-null; challenge passes the "predict the method class" test; no unresolved `t12` in `open_triggers`. |
| **g5** | APPROACH → VALIDATE | `one_sentence.md` states a structural insight (not "SOTA on X"); `formalization-check` `one_sentence_test` metric is `"insight"`; ≥1 `experiment_design` record for this approach; latest `formalization-check` re-run shows `formal_impl_gap: "none"` or `"minor"`; no unresolved backward triggers in `open_triggers`. |

### 3.2 Backward triggers `t2..t15` (verbatim from research_plan.md §1)

| Trigger | From → To | Discovery |
|---|---|---|
| **t2** | FORMALIZE → SIGNIFICANCE | Formalization reveals problem is a trivial special case of an already-solved problem. What you thought was novel is covered by framework X under substitution Y. *Example*: your "new" planning problem reduces to a standard POMDP that DESPOT already solves efficiently. |
| **t4** | DIAGNOSE → FORMALIZE | Empirical failures don't map to any term in your formal structure. The system fails in ways your formalization cannot express. *Example*: you formalized grasping as quasi-static force closure, but failures are dynamic (objects slip during acceleration). |
| **t5** | APPROACH → SIGNIFICANCE | Implemented method is a minor variant of prior work — the "contribution" is incremental engineering, not structural insight. *Example*: your "novel" contact-aware policy is functionally equivalent to impedance control with learned gains. |
| **t6** | CHALLENGE → DIAGNOSE | Challenge hypothesis doesn't match empirical evidence. You proposed a structural barrier but experiments show the system fails for a different reason. *Example*: you hypothesized "sample complexity," but 10x more data doesn't help — the real failure is representation. |
| **t7** | CHALLENGE → FORMALIZE | Challenge analysis reveals your formalization used the wrong framework entirely. *Example*: you formalized as MDP but the real challenge is partial observability — need POMDP. |
| **t8** | APPROACH → DIAGNOSE | Approach solves the diagnosed failure modes but exposes NEW failure modes you hadn't observed. Re-diagnose with the improved system. *Example*: tactile policy fixes insertion but now fails at pre-grasp alignment. |
| **t9** | APPROACH → SIGNIFICANCE | Approach works, but during evaluation you discover a concurrent/recent publication solves the same problem with the same or better approach. |
| **t10** | APPROACH → FORMALIZE | Approach fails because structural assumptions are wrong. You assumed convexity, symmetry, or decomposability that doesn't hold. *Example*: your convex relaxation finds solutions that violate the non-convex constraints. |
| **t11** | APPROACH → DIAGNOSE | Approach doesn't work and you can't tell why from the formalization alone. Go back to the robot, run the system, observe new failure modes. |
| **t12** | APPROACH → CHALLENGE | No method in the implied class works. The challenge doesn't constrain to a viable solution class — mis-specified, or the real barrier is elsewhere. *Example*: you identified "distribution shift" but the action space itself is wrong. |
| **t13** | VALIDATE → SIGNIFICANCE | One-sentence test reveals the contribution is incremental: you can only state it as "we do X slightly better" not as a structural insight. |
| **t14** | VALIDATE → FORMALIZE | During writing, you cannot formally state what your method actually solves. The method works empirically but you can't write the math of WHY. |
| **t15** | VALIDATE → DIAGNOSE | Evaluation/ablation reveals the method works for reasons different than hypothesized. Removing your "key contribution" doesn't hurt performance. |

### 3.3 Key principles of backward transitions

- A backward transition is **NOT failure** — it is **learning**. You
  now know something you didn't.
- Every backward transition produces an **artifact**: a written record
  of *what* was wrong and *why*, which constrains the next search in
  the target stage. You don't re-enter FORMALIZE with a blank slate —
  you re-enter knowing which formalization was wrong and why. The
  CLI stores this as `StageTransition.carried_constraint`.
- Backward transitions to **SIGNIFICANCE are the most expensive**
  (potentially discarding months of work) but also the most important
  to recognize early. The sunk cost fallacy kills research.
- **Multiple backward transitions to the same stage** suggest a
  deeper problem one level further back. If you keep returning to
  FORMALIZE, maybe the problem itself (SIGNIFICANCE) isn't well-posed.
- The "pivot vs. push through" test applies at every backward
  transition: PIVOT when hypothesis is disproven with no reformulation
  path; PUSH THROUGH when failures are informative and you can
  articulate what's wrong.

### 3.4 Inner layer — sub-state search per stage

Each stage searches over candidates to find one that satisfies the
forward guard. Skills and pipelines implement the agent role;
humans provide the judgment the agent can't.

**SIGNIFICANCE** — search space: candidate problems from Hamming
list, literature, advisor input, observed failures. Per candidate:
Hamming (important AND reasonable attack?), Consequence (if solved,
what concretely changes?), Durability (still matters in 48 months?),
Compounding (does solving this enable other research?). Forward: ≥1
candidate passes all tests. Re-entry (from t2/t5/t9/t13): previous
problem failed downstream — carry forward WHY to constrain the new
search. **Agent role**: literature scan via `significance-screen`,
`literature-survey`, `frontier-mapping`, `gap-analysis`,
`paper-evaluate` skills. **Human role**: Hamming judgment (cannot be
automated).

**FORMALIZE** — search space: formal framings (MDP, POMDP,
constrained opt, Bayesian inference) of the selected problem. Per
candidate: is it math? does it reveal structure? does it capture
what makes THIS problem different? Re-entry (from t4/t7/t10/t14):
previous formalization was wrong — try a different framework or add
missing structure. **Agent role**: `formalization-check` (detects
level + framework + structure, runs `scripts/sympy_verify.py`),
`method_survey` (check for trivial special-case reduction),
`benchmark-survey` (produces ranked benchmark proposal).
**Human role**: write the math; select benchmarks.

**DIAGNOSE** — search space: failure modes of a minimal end-to-end
system. Per failure: is it specific? Can you map it to a specific
term/assumption in your formalization? **Sub-phases enforced by
g3**: (1) Setup — install the benchmark(s), wire to `code_dir`;
(2) Reproduce — hit a published baseline within tolerance on every
in-scope benchmark; (3) Diagnose — run the minimal system, observe
failures, map each to a formal term. **Agent role**:
`project-understanding` (reads `code_dir` → `source.md`),
`experiment-design` (reproduction + diagnostic modes),
`experiment-analyze` (stats audit, reproducibility verdict),
`diagnose-system` (maps failures to formalism). **Human role**: run
the robot; write `experiments/<exp_id>/notes.md`.

**CHALLENGE** — search space: structural explanations. Per
candidate: structural (not resource complaint)? Does it CONSTRAIN
the solution class? **Agent role**: `challenge-articulate`,
`concurrent-work-check`, `method_survey`. **Human role**: identify
the structural barrier (taste).

**APPROACH** — search space: methods within the class implied by
the challenge. Per candidate: does it follow from the challenge
(not chosen for novelty)? Does it exploit the structure the
formalization revealed? **Agent role**: `method_survey`,
`identify-method-gaps`, `concurrent-work-check`, `experiment-design`
(approach mode), `project-understanding` (re-reads `code_dir` after
code changes), `formalization-check` (re-run to detect
formalization↔implementation drift). **Human role**: design the
specific method.

**VALIDATE** — tests: One-Sentence (state the contribution as a
structural insight), Ablation (does removing your contribution
degrade performance?), Scope (do claims match what was addressed?).
**Agent role**: `experiment-analyze`, `experiment-audit`
(applies venue thresholds from `review_plan §1.6`), `adversarial-review`,
`research_review_loop` pipeline (drives convergence), `classify-capability`,
`concurrent-work-check`. **Exit to DONE**: no fatal findings,
≤1 fixable serious finding, one-sentence test passes, ablations
isolate the claimed contribution, explicit human approval.

### 3.5 SM-1..SM-6 sub-state-machine specifications

The architecture describes six component state machines whose
composition implements the outer loop. These remain valid as
architectural specs of each component's inner state machine; the
pipelines and skills execute them.

**SM-1 — Search & Discovery**. Not "query → results." Iterative
convergence toward coverage of a topic space.

```
                  ┌──────────────────────────────────┐
                  ▼                                  │
┌───────┐     ┌────────┐     ┌──────────┐     ┌─────┴─────┐
│ QUERY ├────►│ FILTER ├────►│ ASSESS   ├────►│  EXPAND   │
└───────┘     └────────┘     │ COVERAGE │     └───────────┘
                             └─────┬────┘
                                   │ coverage sufficient
                                   ▼
                             ┌──────────┐
                             │ CONVERGE │
                             └──────────┘
```

Implemented by the `literature_survey` and `method_survey` pipelines
(wrapping `alpha_review.apis.search_all`, `s2_references`,
`s2_citations`, Google Scholar fallback). Convergence: last expansion
round added <10% new relevant papers, or budget exhausted.

**SM-2 — Paper Processing Pipeline**. Quality-aware pipeline that
handles degraded extraction gracefully.

```
┌──────────┐     ┌─────────┐     ┌──────────┐     ┌────────┐
│ DISCOVER ├────►│  FETCH  ├────►│ EXTRACT  ├────►│VALIDATE│
└──────────┘     └────┬────┘     └────┬─────┘     └───┬────┘
                      │               │                │
                      │fail           │low quality     │
                      ▼               ▼                ▼
                 ┌─────────┐    ┌──────────┐     ┌────────┐
                 │FALLBACK │    │TRY ALTER-│     │ ENRICH │
                 │(S2 abs) │    │NATE SRC  │     └───┬────┘
                 └─────────┘    └──────────┘         │
                                                     ▼
                                                ┌────────┐
                                                │ STORE  │
                                                └────────┘
```

Implemented by `src/alpha_research/tools/paper_fetch.py::fetch_and_extract`
(PDF → structured sections via pymupdf, Unpaywall fallback,
extraction quality flagging). Quality flags propagate to evaluation
(don't score dimensions that depend on badly-extracted sections).

**SM-3 — Paper Evaluation**. Multi-pass analysis that builds up
understanding progressively.

```
┌──────┐     ┌───────────┐     ┌──────────┐     ┌─────────────┐
│ SKIM ├────►│ DEEP READ ├────►│ EVALUATE ├────►│ CROSS-CHECK │
└──┬───┘     └─────┬─────┘     └────┬─────┘     └──────┬──────┘
   │               │                │                   │
   │skip           │re-read         │revise             │
   ▼               ▼                ▼                   ▼
┌──────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│DISCARD│    │(loop back)│     │(loop back)│    │ FINALIZE │
└──────┘     └───────────┘     └──────────┘     └──────────┘
```

Implemented by the `paper-evaluate` skill. SKIM uses Haiku where
available (fast, cheap screening). DEEP READ uses Sonnet/Opus.
Outputs `Evaluation` records with rubric scores B.1-B.7, evidence
quotes, confidence flags, task chain extraction, and novelty
cross-check against the JSONL store.

**SM-4 — Living Knowledge Graph**. The project memory evolves
across cycles, detects shifts, may require re-evaluation of old
entries. Implemented as append-only JSONL files:

```
output/<project>/
├── evaluations.jsonl          # SM-3 outputs
├── findings.jsonl             # cross-paper findings
├── reviews.jsonl              # adversarial reviews
├── frontier.jsonl             # capability-frontier snapshots
└── ... (12 more record types)
```

Previously specified as a SQLite schema with 8 tables; replaced by
JSONL per the skills-first refactor. At research scale (hundreds of
records, not millions), O(N) full scans are instant; no schema
migrations; the researcher can inspect and edit files by hand. See
`docs/DISCUSSION.md` project lifecycle debate for why.

**SM-5 — Report Generation**. Multi-pass synthesis: aggregate →
cluster → synthesize → verify → format.

```
┌───────────┐    ┌─────────┐    ┌────────────┐    ┌────────┐
│ AGGREGATE ├───►│ CLUSTER ├───►│ SYNTHESIZE ├───►│ VERIFY │
└───────────┘    └─────────┘    └─────┬──────┘    └───┬────┘
                                      │gaps found     │inconsistency
                                      ▼               ▼
                                 ┌─────────┐    ┌──────────┐
                                 │RE-SEARCH│    │RE-SYNTH. │
                                 └─────────┘    └──────────┘
                                                      │
                                                      ▼
                                                ┌──────────┐
                                                │  FORMAT  │
                                                └──────────┘
```

Implemented by `src/alpha_research/reports/templates.py` (Jinja2
templates for DIGEST and DEEP modes) plus the `gap-analysis`,
`classify-capability`, `identify-method-gaps` skills. Gap-triggered
re-search: if synthesis reveals an obvious gap, trigger SM-1 (via
`method_survey`) expansion before finalizing.

**SM-6 — Agent Orchestration Per Mode**. Each analysis mode is a
composition of SM-1 through SM-5 invocations:

| Mode | Composition |
|---|---|
| `digest` (weekly screening) | SM-1(recent, 7d) → SM-2 → SM-3(SKIM+DEEP_READ top-K) → SM-5(digest) |
| `deep` (single paper) | SM-2 → SM-3(full pipeline) → SM-5(deep) |
| `survey` (landscape) | SM-1(broad, converge) → SM-2 → SM-3 → SM-4(relation graph) → SM-5(full synth) → SM-1(EXPAND if gaps) |
| `gap` (bottlenecks) | SM-4(query store) → SM-1(limitations) → SM-3(weaknesses) → SM-5(gap report) |
| `frontier` (capability) | SM-4(frontier_snapshots) → SM-1(new capabilities) → SM-3 → SM-4(update) → SM-5(diff) |
| `direction` (proposals) | SM-4(gap + frontier + Hamming) → SM-5(synth) → SM-1(enabling work) → SM-5(formatted proposals) |

---

## 4. Research Doctrine

Condensed from `doctrine/research_guideline.md`. The standards skills
encode for how to do top-tier robotics research — calibrated against
how Levine, Tedrake, Abbeel, Finn, Kaelbling, Rus, Fox, Todorov,
Goldberg, Bohg, Song, Pinto, Pavone, and Agrawal actually think.

### 4.1 What makes robotics research uniquely hard

**The embodiment problem.** The same algorithm behaves differently
on different robots. Kinematic structure changes the reachable set.
Actuator dynamics are part of the policy. Sensor configurations
create different observation spaces. Control frequency and latency
are embodiment-specific. **Never claim generality from a single
robot.** If your method works on one robot, the interesting question
is *why* it doesn't work on another.

**The contact problem and multimodal sensing.** Contact is where
robotics fundamentally diverges from ML. Hybrid dynamics,
complementarity, discontinuous friction, sim-real divergence is
worst at contact. Vision alone is insufficient for contact-rich
manipulation — tactile sensing (GelSight, DIGIT, ReSkin) provides
contact geometry and force distribution that cameras cannot observe.
Force/torque sensing provides aggregate contact wrench;
proprioception complements external sensing. Sensor fusion is not
"concatenate features" — the right fusion depends on the task.

**Physical irreproducibility, safety, and cost.** Two "identical"
runs differ. Report confidence intervals. Your bug can break a $100K
robot or injure someone. Conservative behaviors dominate published
research (systematic bias). Recovery matters as much as performance.
Report failure **severity**, not just rate.

**The long tail of the physical world.** Combinatorially many
configurations. Be honest about your evaluation distribution. The
most valuable research characterizes the *specific mechanisms* by
which methods fail on distribution tails.

### 4.2 The thinking chain

```
SIGNIFICANCE → TASK → PROBLEM DEFINITION → CHALLENGE → WHY NOW → APPROACH → SCOPE
     ↑                                                                        │
     └──────────────── failures reveal new tasks ────────────────────────────┘
```

Each step is distinct. Confusing them is the most common source of
weak research. The most common failure mode of average research is
not technical weakness — it is working on problems that don't
matter. **Significance comes before everything.**

### 4.3 The significance test (§2.2)

"Important" is not a feeling. It is testable. Apply as a checklist
before committing to a problem.

**Hamming Test (necessity)**:
1. **Can you name 10-20 important unsolved problems in your field?**
   If you can't, you don't know your field well enough to select a
   problem. Great researchers maintain a running list.
2. **Is there a reasonable attack?** Importance requires both (a)
   the solution would matter AND (b) you can see a viable path.
   Filters out both trivial problems and grand-but-intractable ones.
3. **Would solving this generate MORE interest over time, not
   less?** (Patterson) Problems that become less interesting as the
   field evolves are bad bets.

**Consequence Test (impact)**:
4. **If you magically solved this overnight, what changes?** Be
   concrete. "Other researchers would cite us" is not an answer.
5. **Would others consider this important?** (Patterson, Eisner)
   Not just your advisor — would researchers in adjacent areas care?
6. **Will it still be worthy in 48 months?** (Eisner) If a bigger
   model or more data will trivially solve it, don't work on it.

**Portfolio Test (strategy)**:
7. **Does solving this enable other things?** High-value:
   representations that transfer, formal frameworks, data
   infrastructure. Low-value: task-specific controllers, benchmark
   tweaks, marginal accuracy improvements.
8. **Is this goal-driven or merely idea-driven?** (Schulman)
   Goal-driven research is more motivating, more differentiated, and
   more likely to produce genuine contributions.

**The average researcher pattern** (Hamming): spends almost all
their time on problems they believe will not be important. They are
technically competent but strategically blind. **Great Thoughts
Time**: 10% of your time (Friday afternoons) asking "What are the
most important problems in my field? Am I working on one?"

### 4.4 The formalization imperative (§2.4)

Tedrake: *"If you cannot write the math, you do not understand the
problem."* A neural network that "works" is not the same as
understanding. The formalization is not post-hoc documentation —
it IS the research (Simon Peyton Jones: *"Using the paper to do
your research"*).

**Why formalization matters**:
1. The formalization **constrains the solution class**. Kaelbling:
   choosing POMDP vs MDP vs TAMP determines what solutions are even
   possible. The formalization IS often the contribution.
2. Formalization **reveals structure**. Convexity, symmetries,
   effective dimensionality.
3. Formalization **enables rigor at scale**. Counter-intuitively,
   rigor doesn't slow you down — it enables complex systems because
   components declare their states, parameters, and semantics
   consistently.
4. Formalization **separates understanding from curve-fitting**.

**How to formalize (executable)**:

1. State the problem as an **optimization, estimation, or decision
   problem**. What is the objective? Variables? Constraints?
   Information structure?
2. Identify what makes **THIS problem different** from the general
   case — symmetries, sparsity, decomposability.
3. Check what existing formal frameworks apply — and where they break.
4. Write down what you don't know formally — the honest gaps point
   directly to the real challenges.

**Example** — "robot grasping in clutter" is vague. Formalized:
*Given a set of objects O with unknown poses, geometry, and physical
properties, find a grasp g ∈ G that maximizes P(success | g, z) subject
to kinematic reachability, collision avoidance, and force closure
constraints, where success is stable hold under gravity and expected
manipulation forces.* Now you can see: uncertainty over object
properties, constraint set is complex, objective requires a
probabilistic model.

### 4.5 The challenge analysis (§2.5)

The challenge is the **deep structural reason** the problem resists
current solutions. A well-articulated challenge should:

1. Identify a **structural barrier**, not just a difficulty.
   "We need more data" is not a challenge — it's a resource constraint.
2. Suggest the **class of solutions** that could work.
3. **Distinguish your problem** from related problems.

**Challenge → approach table** (§2.7):

| Challenge type | Suggests method class | Example |
|---|---|---|
| **Sample complexity** | Better priors: equivariance, physics, sim pretraining | Equivariant grasping |
| **Distribution shift** | Robust methods, online adaptation, DR, conservative estimation | CQL (Levine), DR (Tobin) |
| **Combinatorial explosion** | Abstraction, decomposition, hierarchy, guided search | TAMP (Kaelbling), skills (Konidaris) |
| **Model uncertainty** | Bayesian methods, ensembles, robust optimization, residuals | GP dynamics, residual RL |
| **Sensing limitation** | New sensors, multi-modal fusion, active/interactive perception | Tactile (Agrawal), interactive perception (Bohg) |
| **Hardware limitation** | Co-design, compliance, mechanism design | Soft robotics (Rus), leg design (Kim) |
| **Discontinuity** | Contact-implicit methods, hybrid formulations, smoothing | Contact optimization (Posa/Tedrake) |
| **Long-horizon credit** | Hierarchical policies, skill primitives, causal reasoning | Options, DMPs (Schaal) |
| **Grounding gap** | Grounded representations, affordances, physics simulators as verifiers | SayCan, affordances (Song) |

The challenge type determines the method class; within the class,
you innovate.

### 4.6 Appendix B — Paper Evaluation Rubric (verbatim)

Structured rubric for evaluating robotics papers. Designed to be
applied consistently — by a human or an LLM agent. This is the
contract the `paper-evaluate` skill implements.

**B.1 Significance and Problem Definition (Weight: Highest)**

| Score | Criteria |
|-------|----------|
| 5 | Problem is demonstrably important (passes Hamming test). Task is concrete and well-scoped. Problem is formally defined with explicit mathematical structure (objective, variables, constraints). Challenge identifies a structural barrier that logically constrains the solution class. Approach follows from the challenge. Claims match scope. Contribution stateable as one sentence capturing a deep structural insight. |
| 4 | Task and problem clear. Significance argued but not fully compelling. Some formal structure. Challenge articulated but could be deeper. |
| 3 | Task defined but significance assumed. Problem described in prose without formalization. Challenge asserted, not analyzed. |
| 2 | Task clear but significance, problem definition, and challenge confused or absent. Approach chosen for novelty. No formal problem statement. |
| 1 | No significance argument. No formal problem definition. Method looking for a problem. |

**B.2 Technical Approach (Weight: High)**

| Score | Criteria |
|-------|----------|
| 5 | Key insight is deep and connects challenge to solution. Exploits problem structure (symmetry, decomposition, physics). Explains *why* it works. |
| 4 | Sound approach with clear insight. Good use of domain knowledge. |
| 3 | Technically correct but insight is thin. Works but unclear why. |
| 2 | Engineering contribution without conceptual insight. Trending method without understanding. |
| 1 | Technically flawed or trivially combines existing methods. |

**B.3 Experimental Rigor (Weight: High)**

| Score | Criteria |
|-------|----------|
| 5 | Real-robot, 20+ trials/condition, confidence intervals, strong baselines (including simple), ablations isolating contributions, failure analysis with taxonomy, perturbation tests. Transparent about setup effort. |
| 4 | Real-robot, 10+ trials, good baselines, meaningful ablations, some failure analysis. |
| 3 | Real-robot but <10 trials, or baselines not tuned, or ablations don't isolate contribution. No failure analysis. |
| 2 | Sim-only for a real-world problem. Or: real-robot but 3-5 trials, weak baselines, no ablations. |
| 1 | Evaluation doesn't support claims. Cherry-picked, no statistics, strawman baselines. |

**B.4 Representation and Sensing (Weight: Medium)**

| Score | Criteria |
|-------|----------|
| 5 | Representation motivated by specific task/challenge requirements. Appropriate sensing modalities. Compared against alternatives. |
| 4 | Good choice with justification. Acknowledges sensing limitations. |
| 3 | Default choice (RGB for everything) without justification. |
| 2 | Clearly mismatched (no depth for 3D reasoning, no force for contact). |
| 1 | Actively harmful to method's goals. |

**B.5 Generalization and Compositionality (Weight: Medium)**

| Score | Criteria |
|-------|----------|
| 5 | Generalization across objects, environments, conditions. Composes with other skills. Tested beyond training distribution. |
| 4 | Good generalization with clear scope. Some compositional capability. |
| 3 | Limited tests. Single environment or narrow objects. No compositionality. |
| 2 | Only training distribution. No generalization evidence. |
| 1 | Overfits to specific setup. |

**B.6 Practical Viability (Weight: Medium)**

| Score | Criteria |
|-------|----------|
| 5 | Real-time, reasonable hardware, data-efficient, failure recovery, clear deployment path. |
| 4 | Practical with acknowledged limitations. |
| 3 | Impractical for deployment but reasonable for research. Limitations noted. |
| 2 | Impractical, limitations unacknowledged. |
| 1 | Cannot run in real-time, prohibitive requirements, no practical path. |

**B.7 Clarity and Reproducibility (Weight: Low-Medium)**

| Score | Criteria |
|-------|----------|
| 5 | Clear writing. Reimplementable. Code + data released. Physical setup documented. |
| 4 | Clear. Most details present. Code released. |
| 3 | Understandable but missing key details. No code. |
| 2 | Confusing. Critical details missing. |
| 1 | Cannot understand the method from the paper. |

**For an LLM research agent**: score each dimension with evidence
(quotes/sections), confidence level (high/medium/low), and explicit
flagging when it cannot assess a dimension (mathematical depth,
physical feasibility). The agent should extract the
task→problem→challenge→approach chain as its **FIRST analysis step**
for every paper.

### 4.7 Core tensions the doctrine handles

- **Structure vs. learning.** Inject structure when challenge is
  sample complexity; learn when challenge is model accuracy; use
  structure for invariants and learning for variants; structure is
  non-negotiable for safety/guarantees.
- **Simulation vs. reality.** Sim for development/debugging, not
  final claims. The sim-real gap is data — characterizing which
  tasks transfer and why is high-value research.
- **Foundation models / LLMs in robotics.** Basic pick-and-place is
  commoditized. Zero-shot generalization is a baseline, not a
  contribution. LLMs provide *semantic* reasoning but not *physical*
  reasoning. The research opportunity: characterize what physical
  reasoning LLMs have and lack.
- **Hardware-software co-design.** Morphology is computation. If
  different hardware makes your problem trivially easier, the
  insight is hardware, not algorithm.
- **Compositionality and long-horizon reasoning.** 95% per-step =
  36% over 20 steps. Compose known skills into novel combinations
  rather than train on every combination.

---

## 5. Review Doctrine

Condensed from `doctrine/review_guideline.md`. Adversarial review at
the standard of top venues — RSS, CoRL, IJRR, T-RO, RA-L, ICRA —
not at the standard of average reviewing.

### 5.1 Philosophy

**Adversarial, not hostile.** The agent is an adversary to the
*argument*, not the author. Every critique targets a logical link,
an evidential gap, or a structural weakness — never a person.
Before attacking, the agent **steel-mans**: constructs the strongest
version of the paper's argument, then identifies where even that
strongest version breaks. RSS standard:

> *"Re-express the paper's position so clearly, vividly, and fairly
> that the authors say, 'Thanks, I wish I'd thought of putting it
> that way.'"*

**The kill-chain, not the scorecard.** Average reviewers score
dimensions independently (novelty: 7, clarity: 8, experiments: 6)
and average. Top reviewers trace the logical chain
`SIGNIFICANCE → FORMALIZATION → CHALLENGE → APPROACH → VALIDATION`
and find where it breaks. **One broken link is a structural flaw
that no score-averaging can compensate for.** This maps directly
to the state machine: each backward transition trigger (`t2`, `t4`,
..., `t15`) is a specific way the chain can break. The review agent
searches for evidence that a backward transition *should* fire but
the paper hasn't acknowledged it.

### 5.2 Hierarchy of flaws

**Fatal (any one → reject):**
- Logical chain has a broken link that cannot be repaired without restructuring
- Central claim is unsupported or contradicted by its own evidence
- Contribution is a trivial variant of existing work (Smith Category 4: "technically correct but useless")
- Evaluation does not test what was claimed

**Serious (accumulation → reject; individually → major revision):**
- Missing critical baselines that could undermine the contribution
- Ablations don't isolate the claimed contribution
- Overclaiming — claims broader than what was addressed
- Statistical insufficiency (too few trials, no CI)
- Missing formal problem definition where the problem demands one

**Minor (do not affect accept/reject):**
- Writing clarity, notation consistency, figure quality
- Missing tangential references
- Minor presentation improvements

**The scoring trap**: A paper with one fatal flaw and five strengths
is a reject. A paper with no fatal flaws and several minor weaknesses
is likely an accept. Never let minor-flaw accumulation override the
absence of fatal flaws.

### 5.3 Falsifiability of critique

Every critique must be stated as a **testable claim**:

- *"If the authors ran baseline X and showed their method outperforms it, this critique would be invalidated."*
- *"If the authors provided evidence that assumption Y holds for their experimental conditions, this concern would be addressed."*
- *"If the authors added ablation Z showing that component W is necessary for performance, the contribution claim would be supported."*

Vague critique ("the evaluation is weak," "the novelty is limited")
is **explicitly prohibited**. NeurIPS: *"Do not make vague statements
in your review, as they are unfairly difficult for authors to
address."*

### 5.4 Constructive adversarialism

For every weakness identified, the agent must provide:

1. **What is wrong** — the specific logical, evidential, or structural gap
2. **Why it matters** — what the consequence is for the paper's claims
3. **What would fix it** — a concrete, actionable path to address the issue
4. **What threshold would change the verdict** — the NeurIPS 2019 question: *"What would the authors have to do for you to increase your score?"*

### 5.5 The six attack vectors (verbatim from review_guideline.md Part III)

**3.1 Attacking Significance.** The "So What?" test.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Hamming failure** | Is this an important problem? Can the reviewer name why this matters beyond the paper's own claims? If removed from the field, would anything change? | §2.2 Hamming Test |
| **Consequence failure** | If magically solved overnight, what concretely changes? "Others would cite us" is not an answer. | §2.2 Consequence Test |
| **Durability failure** | Will a bigger model, more data, or better hardware trivially solve this in 24 months? Is the problem being made obsolete by scaling? | §2.2 Durability Test |
| **Compounding failure** | Does solving this enable other research? Or is it a dead end — a task-specific controller, a benchmark tweak? | §2.2 Portfolio Test |
| **Goal vs. idea driven** | Is this "I have method X, let me find a problem for it" or "Problem Y is important, and the bottleneck suggests method X"? | §2.2 Schulman test |
| **Concurrent work** | Has this been solved (or nearly solved) by concurrent work? Does the paper compare against the most recent relevant work? | Trigger t9 |

**3.2 Attacking Formalization.** The "Where's the Math?" test.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Absent formalization** | Is the problem stated as math (optimization, estimation, decision) or only as English prose? | §2.4 |
| **Wrong framework** | Is the formal framework appropriate? (MDP when the problem has partial observability → should be POMDP) | Trigger t7 |
| **Missing structure** | Does the formalization reveal exploitable structure (convexity, symmetries, decomposability)? | §3.1 |
| **Trivial special case** | Does formalization reveal this is a special case of an already-solved general problem? | Trigger t2 |
| **Assumption audit** | Are the mathematical assumptions realistic? Stated? What breaks if they don't hold? | §3.2, Smith |
| **Formalization-reality gap** | Does the math match what the system actually does? | Trigger t10 |

**3.3 Attacking the Challenge.** The "Why is This Actually Hard?" test.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Resource complaint** | Is the stated challenge "we need more data / compute / time"? That's a resource constraint, not a structural barrier. | §2.5 |
| **Challenge-approach disconnect** | If someone understood only the challenge, would they predict the method class? | Guard g4 |
| **Challenge misidentification** | Does empirical evidence actually support the claimed challenge? | Trigger t6 |
| **Pre-solved challenge** | Has this specific structural barrier been addressed by prior work? | Trigger t12 |
| **Depth test** | Is the challenge analysis deep enough to constrain the solution class? | §2.5 |

**3.4 Attacking the Approach.** The "Does This Follow?" test.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Method-shopping** | Was the method chosen because it's trendy/novel, or because the challenge demands it? | §2.7 |
| **Trivial variant** | Is this approach functionally equivalent to an existing method with cosmetic differences? | Trigger t5 |
| **Structure exploitation** | Does the approach exploit the formal structure the paper identified? | Guard g5 |
| **Wrong mechanism** | Does the approach actually address the stated challenge, or does it succeed for a different reason? (Detected by ablation: removing the "key contribution" doesn't hurt.) | Trigger t15 |
| **Theoretical justification gap** | Can the authors formally state what their method solves? | Trigger t14 |

**3.5 Attacking Validation.** The "Does the Evidence Support the
Claims?" test.

*Experimental Design* — baseline strength, the missing baseline
(often the most devastating finding), ablation isolation, statistical
sufficiency (≥20 trials at IJRR/RSS, ≥10 at CoRL, ≥10 at ICRA/IROS;
CI required everywhere), evaluation-claim alignment, cherry-picking
detection, human effort hiding.

*Robotics-Specific Standards* — sim-only for real claims (fatal at
IJRR/CoRL for contact tasks), single-embodiment generality, contact
gap, sensing mismatch, environment simplification, failure severity,
reproducibility, cycle time / real-time deployability.

*Overclaiming Detection* — generality overclaim ("Our method works
for manipulation" when tested on 3 objects in 1 environment), novelty
overclaim ("novel framework" for a known method in a new domain),
contribution overclaim ("we solve the contact problem"), comparison
overclaim ("outperforms all baselines"), learning overclaim ("the
robot learns to ..."), robustness overclaim.

**3.6 Attacking Novelty.** The "Compared to What?" test. Prior work
overlap, incremental engineering vs structural insight, missing
related work, novelty vs. insight (novelty without insight is NeurIPS
Category 3 at best), combination vs. contribution.

### 5.6 Venue calibration (see docs/SURVEY.md for full rubric)

The same paper may be a strong accept at one venue and a reject at
another. The review agent calibrates to the target venue.

| Venue | Acceptance | Real Robot? | Formalization | Insight Depth | Emphasis |
|---|---|---|---|---|---|
| **IJRR** | ~20% | Strongly encouraged | Required, deep | Maximum | Depth, completeness |
| **T-RO** | ~25% | Strongly encouraged | Required | High | Mature work, broad eval |
| **RSS** | ~30% | Preferred | Preferred | High — values sharp insight | Novel insight; 8pp max |
| **CoRL** | ~30% | Required | Preferred | High | Learning + physical robots |
| **RA-L** | ~40% | Expected | Helpful | Moderate | Timeliness > maturity |
| **ICRA** | ~45% | Preferred | Helpful | Moderate | Broad scope; solid work welcome |
| **IROS** | ~45% | Preferred | Helpful | Moderate | Systems + applications |

### 5.7 Anti-patterns the review agent must avoid

1. **Dimension averaging** — a paper with Significance=5, Experiments=2 is NOT equivalent to Significance=3, Experiments=4.
2. **False balance** — not every paper has strengths and weaknesses that balance.
3. **Novelty fetishism** — NeurIPS 2025: *"Originality does not necessarily require introducing an entirely new method."*
4. **Recency bias** — a deep contribution to a "boring" area outweighs a shallow contribution to a hot topic.
5. **The "not how I would do it" critique** — reject because approach is flawed, not because it differs from reviewer preference.
6. **Blanket rejection on single factors** — CoRL: *"Avoid blanket rejections based on single factors (lack of novelty alone, missing datasets, absence of theorems)."*
7. **Punishing honest limitations** — CoRL: *"Honestly reported limitations should be treated kindly and with high appreciation."*

### 5.8 What the review agent can and cannot assess

**Can assess with high confidence**: logical chain completeness,
claim-evidence alignment, overclaiming detection, baseline
completeness, statistical sufficiency, related work coverage,
clarity, formal problem definition presence.

**Can assess with moderate confidence**: challenge depth,
approach-challenge logical connection, novelty relative to papers
the agent has access to, ablation design quality.

**Cannot assess (must flag for human)**: true significance (Hamming
test — requires the researcher's own judgment), formalization
quality (requires deep mathematical intuition), physical feasibility
(requires embodied experience), true novelty against the full field
history, whether the sim-to-real gap matters for *this specific
task*.

For every dimension marked "cannot assess," the agent must:
1. State explicitly that this is a low-confidence assessment
2. Provide whatever signal it can (presence vs. absence is
   high-confidence even if quality is low-confidence)
3. Flag for human review with a specific question

### 5.9 Review output structure

Per `review_guideline.md` §2.2. Every adversarial review record follows:

```
1. SUMMARY — Restate the paper's argument in the reviewer's own words.
2. LOGICAL CHAIN EXTRACTION — Task → Problem → Challenge → Approach → Contribution
3. STEEL-MAN — The strongest version of the paper's argument (≥3 sentences)
4. FATAL FLAWS (if any) — [What is wrong] → [Why it matters] → [Fix] → [Falsification]
5. SERIOUS WEAKNESSES — Same structure
6. MINOR ISSUES — Bulleted list
7. QUESTIONS FOR AUTHORS — 3-5 points where responses could change the verdict
8. VERDICT — Accept / Weak Accept / Weak Reject / Reject + confidence 1-5
         + one-sentence justification + "What would increase your score?"
```

### 5.10 Mechanical verdict computation (review_plan.md §1.9)

Verdict is derived **mechanically** from findings, not from gestalt:

```python
def compute_verdict(findings, venue):
    fatal = [f for f in findings if f.severity == "fatal"]
    serious = [f for f in findings if f.severity == "serious"]
    significance_score = extract_significance_score(findings)

    # Rule 1: Any fatal flaw → Reject
    if fatal:
        return Verdict.REJECT

    # Rule 2: Gate dimension
    if significance_score <= 2:
        return Verdict.REJECT

    # Rule 3: Unresolvable serious accumulation
    unresolvable_serious = [s for s in serious if not s.fixable]
    if len(unresolvable_serious) >= 3:
        return Verdict.REJECT

    # Rule 4: Venue-calibrated thresholds
    if len(serious) == 0:
        return Verdict.ACCEPT
    elif len(serious) <= 1 and all(s.fixable for s in serious):
        return Verdict.WEAK_ACCEPT
    elif len(serious) <= 2:
        return venue.borderline_verdict(significance_score, serious)
    else:
        return Verdict.WEAK_REJECT
```

Implemented in `src/alpha_research/metrics/verdict.py`.

---

## 6. Problem Formulation Methodology

Condensed from `doctrine/problem_formulation_guide.md`. How to write
a high-quality problem formulation for a survey paper — synthesized
from top researchers, roboticists, and mathematicians (Tao, Knuth,
Bertsekas, Tsitsiklis, Conrad, Pak, Boyd, Sutton, Levine, Finn,
Kaelbling, Garrett, Gerkey).

### 6.1 The 10 commandments

1. **Motivate before you formalize.** Plain English first, then math. Every exemplary formulation begins with **why** before **what**.
2. **Build from familiar to novel.** Start with the known formalism, then extend. Bottom-up scaffolding: base formalism → limitations → extension → new objective.
3. **Separate the five components.** System, dynamics, information, objective, assumptions — in that order.
4. **Make the objective a displayed equation.** It is the most important equation in the section. Numbered, displayed, preceded by plain-English motivation, followed by connection to surveyed works.
5. **Follow field conventions.** Do not reinvent notation. Every deviation must earn its place.
6. **Apply the three-use rule (Tao).** If a symbol appears fewer than three times, write it out.
7. **Present the general case, then instantiate.** One formulation, many special cases. Give the reader a **map** of the problem landscape.
8. **Use the 90% rule.** A formulation covering 90%+ of surveyed works cleanly is good enough. Acknowledge outliers briefly; don't contort the main formulation.
9. **Keep English for context, math for precision.** Words like "unfortunately" and "crucially" carry information symbols cannot.
10. **Check your work.** Consistency sheet, completeness checklist, one concrete example.

### 6.2 The five components

| Component | What It Answers | Examples |
|-----------|----------------|----------|
| **1. System definition** | What are the entities and their relationships? | State space S, action space A, agent set N, object set O |
| **2. Dynamics** | How does the system evolve? | Transition T(s'|s,a), physics model s' = f(s,a) + noise |
| **3. Information structure** | Who knows what, and when? | Full observability, partial observability, communication constraints |
| **4. Objective** | What are we optimizing? | Cumulative reward, goal satisfaction, cost minimization |
| **5. Constraints and assumptions** | What are the boundaries? | Finite horizon, deterministic transitions, known dynamics |

Ordering matters: entities before dynamics, information before
objective, general problem before simplifications.

### 6.3 Recommended section structure

```
Section N: Problem Formulation

  N.1 Motivation and Setting          (1/2 page)
       - Concrete scenario or challenge statement
       - Why existing formalisms are insufficient
       - Preview of what the formulation will capture

  N.2 Base Formalism                   (1/2 - 1 page)
       - Standard, well-known framework (e.g., MDP)
       - Tuple definition, standard objective
       - Brief note on what it cannot capture

  N.3 Extended Formulation             (1 - 1.5 pages)
       - The general formulation that covers the survey's scope
       - Five components in order
       - Objective as displayed, numbered equation
       - Key assumptions stated explicitly

  N.4 Problem Landscape / Taxonomy     (1/2 - 1 page)
       - Table or figure showing how special cases relate
       - Which assumptions each class of surveyed works makes

  N.5 Running Example (optional)       (1/2 page)
       - Instantiate the formulation on a concrete scenario
```

Total: 3-4 pages for a comprehensive survey.

### 6.4 Anti-patterns

1. **The notation dump** — a full page of symbol definitions with no motivation or context.
2. **The reinvention** — using non-standard notation for standard concepts (calling γ "β").
3. **The kitchen sink** — every extension crammed into a 15-tuple.
4. **The phantom assumption** — relying on an assumption without stating it.
5. **The orphan equation** — a displayed equation with no preceding motivation and no following interpretation.
6. **The appendix reference** — "We define our notation in Appendix A." No. The main text must be self-contained.
7. **The false generality** — a formulation that claims to cover "multi-agent systems" but implicitly assumes cooperative, fully-observable, homogeneous agents throughout.

---

## 7. Skills-First Architecture

**This is the philosophical core of the project.** Condensed from
`architecture/tools_and_skills.md`.

### 7.1 The realization: zero new tools

Earlier drafts proposed an MCP server with 5, 9, 11, or 19 custom
tools. After repeated minimality passes, the right answer turned out
to be **zero new tools**. Here is why.

**Everything a researcher does is already reachable.** A robotics
researcher's day consists of activities that fall cleanly into two
buckets:

*Bucket 1 — activities the platform already handles*: reading
papers, writing code, running training scripts, launching simulators,
querying wandb, running sympy checks, making plots, compiling LaTeX,
git operations, searching the codebase, fetching web documentation.
All of these are `Bash`, `Read`, `Write`, `Edit`, `Grep`, `Glob`,
`WebSearch`, `WebFetch`.

*Bucket 2 — activities that need structured scholarly data or
persistent memory*: searching ArXiv / S2 / OpenAlex / Google Scholar
for papers, traversing citation graphs, extracting full-text sections
from PDFs with quality flags, persisting rubric evaluations and
findings across sessions.

The first bucket is solved by Claude Code directly. The second
bucket is solved by **`alpha_review`** — a Python module at
`../alpha_review` that already has `apis.search_all`,
`apis.s2_references/s2_citations`, `apis.unpaywall_pdf_url`,
`scholar.scholar_search_papers`, `models.ReviewState`,
`sdk.run_plan/scope/search/read/write`, and the `alpha-review` CLI.
And the existing alpha_research codebase already has
`tools/paper_fetch.py::fetch_and_extract` for PDF → structured
sections with quality flagging.

**The Python is already written.** Building an MCP server to wrap
these functions is pure indirection — it adds schemas, adapters, and
maintenance burden without expanding capability.

### 7.2 Bash is the bridge

Any Python function in `alpha_review` or `alpha_research` is
reachable from a skill via one `Bash` call:

```bash
python -c "from alpha_review.apis import search_all; import json; print(json.dumps(search_all('tactile manipulation', limit_per_source=15), indent=2))"
```

or via a helper script the skill writes with `Write` and runs with
`Bash`:

```bash
python scripts/_tmp_search.py
```

or via the existing CLI:

```bash
alpha-review "scene representations for mobile manipulation" -o output/scene_repr
```

**`Bash` is the universal tool.** A skill's instruction text tells
Claude exactly what Python to run; `Bash` executes it; stdout
(structured as JSON) comes back as tool output. No MCP server, no
JSON Schema duplication, no adapter layers.

### 7.3 JSONL for project memory, not a new database

The one genuine gap from the earlier analysis — "project-scoped
structured memory for evaluations, findings, reviews, frontier
snapshots" — is solved by **one JSONL file per record type** in the
project's output directory:

```
output/<project>/
├── review.db                    # alpha_review's papers + themes (existing, global)
├── evaluations.jsonl            # our rubric scores (one line per evaluation)
├── findings.jsonl               # our cross-paper findings
├── reviews.jsonl                # our adversarial reviews
├── frontier.jsonl               # our capability-frontier snapshots
├── significance_screens.jsonl   # our §2.2 test outputs
├── formalization_checks.jsonl   # our §2.4 check outputs
├── diagnoses.jsonl              # our failure-mapping outputs
├── challenges.jsonl             # our challenge articulations
├── concurrent_work.jsonl        # our scoop checks
└── research_log.md              # human-authored daily log
```

**Writing**:
```bash
python -c "import json; open('output/x/evaluations.jsonl','a').write(json.dumps(rec)+'\n')"
```

**Reading with filters**:
```bash
python -c "import json; recs = [json.loads(l) for l in open('...')]; print([r for r in recs if r['B.3']['score']>=4])"
```

At research scale (hundreds of records, not millions), O(N) full
scans are instant. No schema migrations. No SQLite extension
tables. No database libraries beyond what Python ships with. The
researcher can inspect and edit files by hand. The `read/write`
helpers live in `src/alpha_research/records/jsonl.py`.

### 7.4 The skill-bash-python pattern

Every skill follows the same composition pattern.

**Pattern 1 — Inline Python via `bash python -c`** for short operations.

**Pattern 2 — Helper script via `Write` + `Bash`** for multi-step
operations; the script stays on disk (recoverable, debuggable).

**Pattern 3 — Existing CLI via `Bash`** when `alpha_review`'s CLI
covers the whole operation (literature surveys).

**Pattern 4 — JSONL append for persistent records** — the skill
writes structured records directly to `<project_dir>/<record_type>.jsonl`.

### 7.5 The 15-skill inventory

Each skill lives at `skills/<slug>/SKILL.md` with YAML frontmatter
specifying `name`, `description`, `allowed-tools`, `model`, and
(new) `research_stages`. The 11 core skills existed pre-refactor;
the four new skills (`benchmark-survey`, `project-understanding`,
`experiment-design`, `experiment-analyze`) are scheduled in the
active implementation plan.

| # | Skill | Model | Primary built-ins | Research stages |
|---|---|---|---|---|
| 1 | `paper-evaluate` | Haiku → Sonnet | Bash, Read, Write | SIGNIFICANCE, APPROACH |
| 2 | `significance-screen` | Opus | Bash, Read, Write | SIGNIFICANCE |
| 3 | `formalization-check` | Opus | Bash, Read, Write | FORMALIZE, APPROACH |
| 4 | `benchmark-survey` (new) | Sonnet | Bash, Read, Write | FORMALIZE, APPROACH |
| 5 | `project-understanding` (new) | Sonnet | Bash, Read, Write, Edit | DIAGNOSE, APPROACH |
| 6 | `diagnose-system` | Sonnet | Bash, Read, Write, Edit, NotebookEdit | DIAGNOSE |
| 7 | `experiment-design` (new) | Opus | Bash, Read, Write | DIAGNOSE, APPROACH, VALIDATE |
| 8 | `experiment-analyze` (new) | Sonnet | Bash, Read, Write | DIAGNOSE, VALIDATE |
| 9 | `challenge-articulate` | Opus | Bash, Read, Write | CHALLENGE |
| 10 | `concurrent-work-check` | Sonnet | Bash, Read, Write | CHALLENGE, APPROACH, VALIDATE |
| 11 | `identify-method-gaps` | Sonnet | Bash, Read, Write | APPROACH |
| 12 | `experiment-audit` | Sonnet | Bash, Read, Write, Grep | VALIDATE |
| 13 | `adversarial-review` | Opus | Bash, Read, Write, Edit, Task | VALIDATE |
| 14 | `gap-analysis` | Opus | Bash, Read, Write | SIGNIFICANCE, CHALLENGE |
| 15 | `classify-capability` | Sonnet | Bash, Read, Write | SIGNIFICANCE, VALIDATE |

**One-line summaries**:

- **`paper-evaluate`**: per-paper evaluation against the full
  Appendix B rubric (B.1–B.7). Fetches paper via `paper_fetch`, runs
  SKIM → DEEP → EVALUATE → CROSS-CHECK, writes an `Evaluation` record.
- **`significance-screen`**: applies the four significance tests
  (Hamming, Consequence, Durability, Compounding) from
  `research_guideline §2.2` to a candidate problem. Reads the
  researcher's `hamming.md`. Always flags for human.
- **`formalization-check`**: detects formalization level
  (`formal_math | semi_formal | prose_only | absent`), framework
  mismatches, claimed structure; invokes `scripts/sympy_verify.py`
  to check claimed properties (convexity, continuity).
- **`benchmark-survey`** (new): reads `formalization.md`, surveys
  literature for benchmarks covering the problem class, extracts
  per-benchmark metadata + published baselines + saturation
  assessment, produces a ranked proposal the human reads to write
  `benchmarks.md`.
- **`project-understanding`** (new): walks `code_dir`, identifies
  entry points, extracts loss functions, compares to
  `formalization.md`, flags any mismatch as a formalization↔code
  gap. Writes `source.md`.
- **`diagnose-system`**: reads `source.md` + `formalization.md` +
  latest `experiments/<exp_id>/results.jsonl` + `notes.md`, maps
  each observed failure to a specific term or assumption in the
  formalization. Writes `diagnoses.jsonl`.
- **`experiment-design`** (new): three modes. `reproduction` targets
  a specific published baseline from `benchmarks.md`; `diagnostic`
  targets a specific formalization term suspected of causing
  failure; `approach` isolates a claim about the method. Emits a
  `config.yaml` into `<code_dir>/experiments/<exp_id>/`.
- **`experiment-analyze`** (new): mode-aware. `reproduction` mode
  compares measured aggregate against `benchmarks.md`'s
  `published_baselines` and emits a `reproducibility:
  pass|partial|fail` field (the hard guard for `g3`). `diagnostic`
  and `approach` modes propose backward triggers (`t4 / t5 / t7 /
  t8 / t15`) based on observed patterns.
- **`challenge-articulate`**: tests the proposed challenge against
  structural-vs-resource, solution-narrowing, and analogous
  challenges in literature. Writes `challenges.jsonl`.
- **`concurrent-work-check`**: detects scooping. Multi-query search
  via `search_all`, citation-graph expansion via `s2_citations`,
  Google Scholar last-resort. Writes `concurrent_work.jsonl` with
  `overlap_degree ∈ {none, minor, significant, scooped}`.
- **`identify-method-gaps`**: given a list of evaluated methods in
  a solution class, identifies what hasn't been tried.
- **`experiment-audit`**: stats sufficiency per venue thresholds
  (`review_plan §1.6`), baseline strength, ablation isolation,
  overclaiming patterns (`review_guideline §3.5.3`).
- **`adversarial-review`**: the biggest skill. Full six-attack-vector
  review with graduated pressure (structural scan → full review →
  focused re-review), steel-man ≥3 sentences, Finding objects with
  `what_is_wrong / why_it_matters / what_would_fix / falsification_condition`,
  mechanical verdict via `metrics/verdict.py`. Composes
  `concurrent-work-check`, `formalization-check`, `experiment-audit`
  via `Task`.
- **`gap-analysis`**: aggregates weaknesses across evaluations,
  identifies limitations appearing in ≥3 papers, verifies each gap
  is real (not just missed papers), cross-references with the
  researcher's Hamming list.
- **`classify-capability`**: places a paper's demonstrated
  capability on the frontier (reliable / sometimes / can't-yet).
  Pure input-to-output classification with no tool calls.

**Total custom infrastructure: 15 markdown files. Zero tools. Zero
schemas. Zero new Python modules** for the skill layer itself.

### 7.6 Explicit non-goals (what we are NOT building)

| Non-goal | Why not |
|---|---|
| MCP server | No capability gap that MCP fills. `Bash` reaches everything. |
| Custom tool definitions | Same reason. |
| Extension SQLite tables | JSONL files serve the same purpose with zero schema management. |
| Wrapper classes around `alpha_review` APIs | The Python functions are already cleanly callable. |
| Cross-provider tool registry | Tools don't exist in this architecture. |
| Framework for skill composition | `Task` + JSONL records handle it. |
| New search CLI commands | `alpha-review` already provides one. `Bash` runs everything else. |
| Experiment launch/query abstractions | Lab-specific. Use `Bash` + the experiment-interface convention. |
| Math verification tool | `bash python -c "import sympy; ..."` is one line. |
| Plot generation tool | `bash python plot.py`. |
| Statistical test tool | `bash python -c "from scipy.stats import ..."`. |

**Everything the project needs is a skill.** That is the entire
architectural thesis.

### 7.7 Cross-LLM portability

SKILL.md files are native to Claude Code. Porting to other models is
a ~20-line adapter:

- **OpenAI / Gemini**: translate each SKILL.md body into the
  `instructions` / `system_instruction` field. Provide
  `code_interpreter` or `code_execution` as the `Bash` equivalent.
- **Open-source (LLaMA 3.1+, Qwen 2.5+, DeepSeek V3)**: wrap via
  LangChain. Each SKILL.md body becomes a `SystemMessage`; `Bash`
  becomes a `PythonREPLTool`.

The adapter is 20 lines, not a framework.

---

## 8. Module Layout

```
src/alpha_research/
├── main.py                     # Typer CLI entry point
├── config.py                   # Constitution + Venue loaders (YAML → Pydantic)
├── llm.py                      # LLMCallable protocol + Anthropic SDK client
│                               # (fallback for standalone; inside Claude Code, skills run natively)
├── project.py                  # ProjectState dataclass + init_project + append_revision_log
├── skills.py                   # Skill invoker + stage-check helper
│
├── pipelines/                  # Deterministic Python orchestration
│   ├── state_machine.py        #   Pure functions: g1..g5, t2..t15 (no LLM)
│   ├── literature_survey.py    #   alpha-review CLI + paper-evaluate loop + gap-analysis + frontier
│   ├── method_survey.py        #   search + s2_refs/citations + paper-evaluate + identify-method-gaps
│   ├── frontier_mapping.py     #   classify-capability loop + frontier diff
│   └── research_review_loop.py #   adversarial convergence (graduated pressure + meta-review)
│
├── records/
│   └── jsonl.py                # append_record, read_records, count_records
│                               # record types: evaluation, finding, review, frontier,
│                               # significance_screen, formalization_check, diagnosis,
│                               # challenge, method_survey, audit, concurrent_work, gap_report
│
├── metrics/                    # Python helpers (called by skills via Bash)
│   ├── verdict.py              #   compute_verdict per review_plan §1.9 — pure function
│   ├── review_quality.py       #   actionability / grounding / falsifiability per §1.8
│   ├── convergence.py          #   research_review_loop stopping conditions
│   └── finding_tracker.py      #   cross-iteration finding resolution rate
│
├── reports/
│   └── templates.py            # DIGEST + DEEP Jinja2 templates (survey template deleted)
│
├── models/
│   ├── research.py             # Evaluation, RubricScore, TaskChain, SignificanceAssessment,
│   │                           #   ExtractionQuality, SearchState, PaperCandidate, CoverageReport
│   ├── review.py               # Review, Finding, Verdict, Severity, ReviewQualityMetrics,
│   │                           #   RevisionResponse, FindingResponse, FindingDispute
│   ├── blackboard.py           # Blackboard, ResearchArtifact, ConvergenceState, HumanDecision, Venue
│   ├── project.py              # ProjectManifest, ProjectState (legacy lifecycle layer — being collapsed)
│   └── snapshot.py             # SourceSnapshot, UnderstandingSnapshot, ProjectSnapshot, ResearchRun
│
├── tools/
│   └── paper_fetch.py          # fetch_and_extract (PDF → sections with quality flags + Unpaywall fallback)
│
├── templates/
│   └── project/                # Project-scaffold markdown templates
│       ├── PROJECT.md.j2       #   technical details
│       ├── DISCUSSION.md.j2    #   user/agent discussions
│       ├── LOGS.md.j2          #   append-only log (2 sections)
│       ├── hamming.md.j2       #   10-slot template
│       ├── formalization.md.j2 #   five-component structure
│       ├── benchmarks.md.j2    #   in-scope / rejected sections
│       └── one_sentence.md.j2  #   placeholder + anti-examples
│
├── projects/                   # Legacy project lifecycle (being collapsed in Phase 0 — see PLAN)
│   ├── orchestrator.py, registry.py, resume.py, service.py,
│   ├── snapshots.py, git_state.py, understanding.py, _understanding_prompt.py
│
├── api/                        # Legacy FastAPI backend (deferred per Phase 0 — frontend plan)
│   ├── app.py, models.py
│   └── routers/                #   papers, evaluations, graph, agent, projects
│
└── knowledge/                  # Legacy SQLite store (deferred deletion — still consumed by api/ + projects/)
```

**Status**: Phase 0 of the integrated state-machine plan collapses
`projects/` into a ~100-line `project.py`, deletes `api/` and
`knowledge/`, and creates a `.claude/skills` symlink pointing at
`skills/`. See `docs/PLAN.md` §Phase 0 for the detailed cut list.

### 8.1 Relationship to `alpha_review`

`alpha_review` is a sibling project at `../alpha_review` installed as
an editable dependency. It provides:

| `alpha_review` symbol | Used by |
|---|---|
| `alpha_review.apis.search_all` | Skills (via `bash python -c`) + `pipelines/literature_survey.py` + `pipelines/method_survey.py` |
| `alpha_review.apis.s2_paper_details` | `paper-evaluate` skill |
| `alpha_review.apis.s2_references` | `method-survey`, `adversarial-review` skills |
| `alpha_review.apis.s2_citations` | `significance-screen`, `adversarial-review`, `concurrent-work-check` skills |
| `alpha_review.apis.unpaywall_pdf_url` | `tools/paper_fetch.py` (fallback) |
| `alpha_review.scholar.scholar_search_papers` | `concurrent-work-check` skill (last-resort) |
| `alpha_review.models.ReviewState` | `pipelines/literature_survey.py` + skills |
| `alpha_review.sdk.run_plan / run_scope / run_search / run_read / run_write` | Used via `alpha-review` CLI (not imported directly) |
| `alpha-review` CLI | `pipelines/literature_survey.py` (subprocess) |

No MCP wrappers. No adapter classes. Direct Python imports from
pipelines; `bash python -c "..."` from skills.

---

## 9. Public API — The CLI Verbs

The CLI is the only way the state machine transitions. Skills and
pipelines are invoked via the CLI or via Claude Code directly; in
both cases they write to the project directory through the shared
record helpers. See `docs/PLAN.md` §Phase 2 for the full CLI surface
that Phase 2 builds; this section documents what exists today plus
the target surface.

### 9.1 Current (pre-Phase-0) CLI

```bash
alpha-research survey       <query> -o <dir>                    # literature_survey pipeline
alpha-research evaluate     <paper_id> -o <dir>                 # paper-evaluate skill
alpha-research review       <artifact.md> --venue RSS -o <dir>  # adversarial-review skill
alpha-research significance <problem>                           # significance-screen skill
alpha-research loop         <project_dir> --venue RSS           # research_review_loop pipeline
alpha-research status       [<project_dir>]                     # summarize JSONL records

alpha-research project create|list|show|status|snapshot|resume  # legacy lifecycle layer
```

### 9.2 Target post-Phase-2 CLI

The legacy `project create|list|show|snapshot|resume` verbs are
replaced by the lifecycle verbs that operate on state.json and
provenance.jsonl:

```bash
# ─── Project lifecycle ─────────────────────────────────────────────────
alpha-research project init <name>
    [--code <absolute_path>]
    [--question "..."]
    [--venue RSS|CoRL|IJRR|T-RO|RA-L|ICRA|IROS]
    [-o <parent_dir>]             # default: output/

alpha-research project stage [<project_dir>]
    # Current stage, forward-guard status (pass/fail per condition),
    # next recommended skill, open backward triggers, last 5 transitions.

alpha-research project advance [<project_dir>] [--force] [--note "..."]
    # Runs the current stage's forward guard. If it passes, transitions
    # forward and records the transition in state.json + provenance.jsonl.
    # --force allows override with mandatory --note.

alpha-research project backward <trigger> [<project_dir>]
    [--evidence <record_id>] [--note "..."]
    # <trigger> is one of t2..t15. Updates current_stage, appends to
    # stage_history with the trigger + carried_constraint, marks the
    # open_trigger as resolved.

alpha-research project log [<project_dir>]
    # Opens $EDITOR on LOGS.md with a weekly template appended.

alpha-research project status [<project_dir>]
    # One-screen summary.

# ─── Stage-bound actions ───────────────────────────────────────────────
alpha-research observe <exp_id> [<project_dir>]
    # Opens $EDITOR on a failure-note template, appends to findings.jsonl.

alpha-research calibrate <project_dir> --papers <id1,id2,...>
    # Monthly ritual: compare agent scores against human gold labels.

alpha-research provenance [<project_dir>]
    [--since <stage>] [--action <type>] [--limit N]
    # Prints the provenance tree with parent_ids.

alpha-research skill <skill_name> [--project <dir>] [args...]
    # Invoke a skill; checks research_stages frontmatter against current
    # stage; warns (not errors) if out-of-stage; logs to provenance.jsonl.
```

**Guard semantics**: `project advance` NEVER transitions without the
forward guard passing, except with `--force + --note`. The `--force`
path records an `override_reason` field in the stage transition —
the cheating is visible in provenance.

**Backward semantics**: `project backward` can be invoked by the
human directly (after reading a review finding) OR proposed by a
skill (written to `state.open_triggers`). The skill never executes
the backward transition itself; only the CLI verb does, and the
human must confirm.

---

## 10. Per-Project Artifacts

A project is its directory. Every file in the project directory is
part of the project's state.

### 10.1 Three canonical documentation files (invariant)

Every research project — not just alpha_research itself — must
include and maintain:

- **`PROJECT.md`** — technical details, kept up to date
- **`DISCUSSION.md`** — records discussions between the user and agents
- **`LOGS.md`** — append-only log with two sections:
  - `## Agent revisions` — automated entries above an
    `<!-- AGENT_REVISIONS_END -->` anchor comment
  - `## Weekly log` — researcher's `### Week of YYYY-MM-DD` blocks
    following a Tried/Expected/Observed/Concluded/Next template

Enforcement: `src/alpha_research/templates/__init__.py` defines
`REQUIRED_DOCS = ("PROJECT.md", "DISCUSSION.md", "LOGS.md")`.
`PROJECT_TEMPLATES` extends this with the stage-specific artifacts
(`hamming.md`, `formalization.md`, `benchmarks.md`, `one_sentence.md`).
Tests reference `REQUIRED_DOCS` directly so they stay in sync.

### 10.2 Human-owned markdown

| File | Owner | Purpose |
|---|---|---|
| `PROJECT.md` | Human | The three-canonical-docs invariant (above). |
| `DISCUSSION.md` | Human | Same. |
| `LOGS.md` | Human (weekly) + Agent (revisions) | Append-only. |
| `hamming.md` | Human (monthly) | Running list of 10-20 important unsolved problems. **The agent cannot produce this.** |
| `formalization.md` | Human | The problem as math: objective, variables, constraints, information structure. Agent reviews via `formalization-check`. |
| `benchmarks.md` | Human (after reading agent's proposal) | Chosen benchmarks with rationale, success criterion, published baselines, saturation assessment. |
| `one_sentence.md` | Human | Evolving contribution statement — must be a structural insight, not "SOTA on X." |

### 10.3 Agent-written markdown

| File | Producer | Purpose |
|---|---|---|
| `source.md` | `project-understanding` skill | Where the method lives, entry points, config files, training loop, eval harness, formalization↔code correspondence, open questions. |
| `benchmark_proposal.md` | `benchmark-survey` skill | Ranked benchmark candidates with metadata. A recommendation, not a decision — the human reads it to write `benchmarks.md`. |

### 10.4 CLI-owned state

`state.json` — one schema, always-present:

```python
@dataclass
class ProjectState:
    project_id: str                          # = directory basename
    created_at: str                          # ISO 8601
    current_stage: ResearchStage             # SIGNIFICANCE / FORMALIZE / DIAGNOSE / CHALLENGE / APPROACH / VALIDATE / DONE
    stage_entered_at: str
    stage_history: list[StageTransition]     # append-only
    open_triggers: list[OpenTrigger]         # backward triggers proposed but not resolved
    forward_guard_status: dict[str, GuardCheck]  # per-guard last check
    code_dir: str | None                     # absolute path to the method code
    target_venue: str                        # default "RSS"
    notes: str                               # free-form researcher notes
```

Every transition carries a `trigger` (`g1..g5` or `t2..t15` or
`init`), a `note`, and (for backward transitions) a `carried_constraint`
recording what was learned.

### 10.5 Append-only provenance

`provenance.jsonl` — every CLI verb, every skill invocation, every
pipeline run appends one record:

```python
@dataclass
class ProvenanceRecord:
    id: str                                  # uuid
    created_at: str
    action_type: str                         # "skill"|"pipeline"|"cli"|"human"|"transition"
    action_name: str                         # e.g. "significance-screen", "project advance"
    project_stage: ResearchStage             # stage at time of action
    inputs: list[str]                        # artifact refs read (paths or record ids)
    outputs: list[str]                       # artifact refs written
    parent_ids: list[str]                    # prior provenance ids this action built on
    summary: str                             # one-line human description
```

This is the single source of truth for "what happened and in what
order." `alpha-research provenance` reads and renders this, letting
a human trace any finding back to the formalization version that
motivated the experiment that produced it.

### 10.6 JSONL record streams

One file per record type; append-only; read via
`src/alpha_research/records/jsonl.py::read_records` with dict-based
filters. Full list per stage:

**SIGNIFICANCE stage**:
- `significance_screens.jsonl` — `significance-screen` outputs (four tests)
- `frontier.jsonl` — `frontier_mapping` snapshots
- `gap_reports.jsonl` — `gap-analysis` outputs
- `evaluations.jsonl` — `paper-evaluate` (reads by many stages)

**FORMALIZE stage**:
- `formalization_checks.jsonl` — `formalization-check` outputs
- `benchmark_surveys.jsonl` — `benchmark-survey` outputs
- `method_surveys.jsonl` — `method_survey` pipeline outputs

**DIAGNOSE stage**:
- `experiment_designs.jsonl` — `experiment-design` outputs (reproduction + diagnostic modes)
- `experiment_analyses.jsonl` — `experiment-analyze` outputs with `reproducibility` field
- `findings.jsonl` — structured findings from analyses and diagnoses
- `diagnoses.jsonl` — `diagnose-system` outputs

**CHALLENGE stage**:
- `challenges.jsonl` — `challenge-articulate` outputs
- `concurrent_work.jsonl` — `concurrent-work-check` outputs

**APPROACH stage**:
- `method_surveys.jsonl` (re-read)
- `experiment_designs.jsonl` (re-written — approach mode)
- `concurrent_work.jsonl` (re-written)

**VALIDATE stage**:
- `experiment_analyses.jsonl` (approach mode)
- `findings.jsonl` (re-append)
- `reviews.jsonl` — `adversarial-review` outputs
- `frontier.jsonl` (re-written)

### 10.7 Exit to DONE

From VALIDATE:
1. Most recent `review` record has `verdict ∈ {ACCEPT, WEAK_ACCEPT}`
2. No `fatal` findings in the latest review
3. ≤1 `serious` finding, and it is `fixable: true`
4. `one-sentence test` passes (record includes an insight, not a performance claim)
5. All ablations isolate the claimed contribution
6. Human has given explicit final approval

---

## 11. The Experiment Interface

A **convention**, not a framework. `alpha_research` does not install
benchmarks, launch training runs, or ship data collection tools. It
reads and writes a documented directory layout that any lab's
existing launcher can be adapted to in ~30 minutes.

### 11.1 Directory layout

Each experiment lives in its own directory **under the method code
tree** — next to the code it produced, not inside the project
directory:

```
<code_dir>/experiments/<exp_id>/
├── config.yaml              # the experiment definition
├── results.jsonl            # one record per trial — THE hard contract
├── logs/                    # whatever the launcher writes (wandb export, stdout, csv)
├── checkpoints/             # optional model checkpoints
├── notes.md                 # researcher's post-hoc observations
└── provenance_ref.txt       # id of the experiment_design record that motivated this run
```

`<exp_id>` should be stable and meaningful. Recommended format:
`<mode>_<benchmark_short>_<YYYYMMDD>` — e.g.
`reproduction_nistatb_20260415`.

### 11.2 `config.yaml` — written by `experiment-design`

```yaml
exp_id: reproduction_nistatb_20260415
mode: reproduction | diagnostic | approach
design_provenance_id: prov_9b2e4f1a
benchmark_id: NIST ATB

hypothesis: |
  The tactile+vision fusion baseline from Paper A (2024) should reach
  0.62 success on single-peg-in-hole insertion under default conditions.

formal_terms_tested:
  - "A3 (observation resolution)"

# Reproduction mode only:
reproduction_of: "paperA_2024"
target_metric: 0.62    # the published number this run targets

conditions:
  - id: reproduce_paperA
    description: "Paper A impedance baseline, reproduced on our hardware"

baselines_required:
  - scripted       # doctrine §8.2
  - strongest_prior
  - oracle         # optional but recommended

trials_per_condition: 20
seeds: [0, 1, 2, 3, 4]

metrics:
  - success_rate
  - mean_insertion_time
  - failure_mode_taxonomy    # required by doctrine §8.1

pre_registered_failure_modes:
  - "slip at contact initiation"
  - "overshoot from compliance mismatch"

cycle_time_target_s: 5.0
human_effort_estimate_hours: 2.0
```

### 11.3 `results.jsonl` — the one hard contract

One JSON object per line, one object per trial:

```json
{
  "exp_id": "reproduction_nistatb_20260415",
  "trial_id": 0,
  "seed": 0,
  "condition": "reproduce_paperA",
  "started_at": "2026-04-15T10:00:00Z",
  "finished_at": "2026-04-15T10:00:07Z",
  "metrics": {
    "success": true,
    "insertion_time_s": 4.2,
    "final_error_mm": 0.3
  },
  "outcome": "success",
  "failure_mode": null,
  "notes": ""
}
```

**Required fields per trial**: `exp_id` (matches config),
`trial_id`, `seed`, `condition` (matches one from config),
`outcome`, `metrics` (per config).
**Optional**: `started_at`, `finished_at`, `failure_mode` (must be
one of `config.pre_registered_failure_modes` or `"new:<description>"`),
`notes`.

### 11.4 Adapting an existing launcher

Whatever launcher you use (bash + Hydra, wandb sweep, SLURM), write
a small post-processor that emits `results.jsonl` from the launcher's
native log format. ~10 lines of Python. See
`guidelines/architecture/experiment_interface.md` for a worked
example.

### 11.5 Reproducibility floor (g3 hard guard)

At DIAGNOSE entry, the researcher must produce one `reproduction`
mode experiment per in-scope benchmark, run it, and let
`experiment-analyze` record a `reproducibility: pass | partial`
result. The forward guard `g3` checks for this before allowing
DIAGNOSE → CHALLENGE.

A `reproducibility: fail` result is the **first** thing to check for
setup bugs: wrong install, wrong version pin, wrong hyperparameters,
wrong hardware. Only after setup is confirmed should a failing
reproduction be treated as a formal mismatch (trigger `t4` or `t7`).

### 11.6 What `experiment-analyze` does NOT do

- It does not run your code.
- It does not compute new metrics beyond what's already in `results.jsonl`.
- It does not re-analyze old experiments unless you pass `--exp <id>` explicitly.
- It does not auto-execute backward triggers — it only proposes them.

---

## 12. Takeaways from the R0-R9 Refactor

Key insights from the R0-R9 migration that took the project from the
T1-T10 agent-centric codebase (494 tests passing) to the skills-first
layout. See `docs/DISCUSSION.md` for the full journey; the insights
that shaped the architecture are distilled here.

### 12.1 Takeaway 1 — Zero new tools is not a cut, it's a realization

Earlier drafts proposed an MCP server with 5, 9, 11, or 19 custom
tools. Every minimality pass cut the count. The *right* count turned
out to be zero: Claude Code's built-ins plus `alpha_review`'s Python
functions already reach every capability a researcher needs. Building
an MCP wrapper over `alpha_review.apis` is pure indirection. The
skill writes `bash python -c "..."`; Bash runs it; stdout returns
structured JSON; the LLM reasons over it. No MCP server, no schema
duplication, no adapter layer.

### 12.2 Takeaway 2 — Skills are the deliverable, not the code

The project's domain value lives in 15 SKILL.md files (~3,300 lines
of prompt-engineered markdown). The Python pipelines are
deterministic orchestration — hundreds of lines, not thousands.
Moving the 1,904 lines of `prompts/*.py` content into SKILL.md files
freed the code to become smaller and more focused: pure functions
for state transitions, pure Jinja templates for reports, pure JSONL
append/read for records.

### 12.3 Takeaway 3 — JSONL beats SQLite for agent memory

Earlier designs had an 8-table SQLite schema (evaluations,
paper_relations, findings, frontier_snapshots, topic_clusters,
questions, feedback, audits). At research scale (hundreds of
records, not millions), this was all ceremony. Replacing it with
one JSONL file per record type removed ~600 lines of schema +
store code, eliminated migrations, and let the researcher inspect
and edit records by hand. The only SQLite that remains is
`alpha_review`'s global papers/themes store, which is owned by
`alpha_review`, not `alpha_research`.

### 12.4 Takeaway 4 — A project is a directory

The alternative was an ambitious project-lifecycle layer
(`ProjectManifest`, `ProjectState`, `SourceSnapshot`,
`UnderstandingSnapshot`, `ProjectSnapshot`, `ResearchRun`, git-backed
checkpointing, `git worktree`-based resume, source fingerprinting,
understanding agents that diff-aware re-understand on resume). 1,654
lines of plan, 1,300+ lines of Python across `projects/orchestrator.py`,
`registry.py`, `resume.py`, `service.py`, `snapshots.py`,
`git_state.py`, `understanding.py`. All of it modeled a problem we
didn't have yet.

The simpler model: `cd output/<project>` is resume. `git init` in
the directory is versioning. `tar czf` is backup. `state.json`
tracks stage transitions; `provenance.jsonl` tracks action lineage;
the researcher's own `git` in the project directory handles
snapshots when they want them. Phase 0 of the integrated plan
replaces all of the lifecycle code with a 100-line `project.py`.

### 12.5 Takeaway 5 — The state machine was theory until bound to disk

`pipelines/state_machine.py` had pure functions for `g1..g5` and
`t2..t15` from the start, but nothing consulted them at runtime and
nothing persisted "which stage am I in." The Phase 1 wiring is the
change that makes the state machine **executable**: binding
`stage_guard_check` and `advance_transition` / `backward_transition`
to `state.json`, adding `append_open_trigger` / `resolve_open_trigger`
for the backward-trigger lifecycle, and making every CLI verb and
skill log to `provenance.jsonl` as a side effect.

### 12.6 Takeaway 6 — Benchmarks are first-class

Earlier versions of FORMALIZE only checked "is the math present?"
This misses half the research cycle: *how will we measure progress?*
A benchmark choice is itself a formalization decision — it pins down
the observation space, action space, success criterion, and
evaluation distribution. Phase 5 of the integrated plan adds:
- The `benchmark-survey` skill that surfaces candidates from
  Papers With Code + literature surveys with per-benchmark metadata
  (task scope, standard metrics, success criterion, published
  baselines with numbers, recent-year score trend, install pointer,
  hardware requirements, community usage)
- A tightened `g2` requiring `benchmarks.md` to exist with ≥1 chosen
  benchmark carrying rationale, success criterion, ≥1 published
  baseline with its number, saturation assessment
- A tightened `g3` requiring at least one **successfully reproduced**
  published baseline per in-scope benchmark before leaving DIAGNOSE
  (the reproducibility floor)

Reproducibility is a hard guard, not a suggestion.

### 12.7 Takeaway 7 — The researcher runs the robot; we don't

Phase 6 adds three skills — `experiment-design`, `experiment-analyze`,
`project-understanding` — but none of them launch experiments, run
training, or install benchmarks. They read and write a documented
directory convention (`<code_dir>/experiments/<exp_id>/`). Any lab's
existing launcher can be adapted in 30 minutes with a ~10-line
post-processor that emits `results.jsonl` from the launcher's native
log format. This keeps the project compact and portable, and it
keeps the researcher's method code outside the project directory
where it belongs.

### 12.8 Takeaway 8 — The human is the outermost controller

Every forward transition goes through a CLI verb that checks a
forward guard. Every backward transition goes through the human
reading a finding and running `alpha-research project backward`
with a mandatory note. The agent never advances stages on its own.
The `--force` path exists for emergencies, but it records an
`override_reason` in the stage transition — the cheating is visible
in provenance. This is an instance of the broader principle from
`docs/DISCUSSION.md` user principles: **make mistakes recoverable
and reviewable by humans**.

### 12.9 Takeaway 9 — Append-only provenance makes audits trivial

Every CLI verb, every skill invocation, every pipeline run appends
one record to `provenance.jsonl` with `parent_ids` linking to prior
records that motivated it. A researcher can trace any finding back
through the experiment that produced it → the experiment_design that
motivated it → the challenge that called for that experiment → the
diagnosis that revealed that challenge → the formalization version
under which the diagnosis was run. `alpha-research provenance`
renders this as a tree. Three weeks later, the researcher can answer
"why did I run this experiment?" without guessing.

### 12.10 Takeaway 10 — Minimum-first beats maximum-useful

The cleanest illustration of this principle: the refactor deleted
~4,550 lines of redundant Python (R2-R6) and added ~1,100 lines of
new Python plus ~2,500 lines of markdown. **Net code delta:
-3,450 lines of Python**. The project got smaller while gaining the
entire skills layer. Every module that survived earned its place
against concrete doctrine/spec line-items.

The same principle applies to the skill catalog itself: earlier
drafts had 12, 11, and 10 skills before settling on 11 + 4 planned =
15. Two skills (`classify-capability`, `identify-method-gaps`) were
factored *out* of larger skills during the audit to keep each skill
focused on a single attack vector / rubric dimension.

### 12.11 Takeaway 11 — The three-canonical-docs invariant is load-bearing

From the 2026-04-11 entry in `LOG.md`: every research project must
include `PROJECT.md` + `DISCUSSION.md` + `LOGS.md` at its root.
`REQUIRED_DOCS` is the single source of truth; `PROJECT_TEMPLATES`
extends it with stage artifacts; the `g1` forward guard reads
`PROJECT.md` for the problem statement; `append_revision_log()`
writes above an HTML-comment anchor (`<!-- AGENT_REVISIONS_END -->`)
and dual-writes a `provenance.jsonl` record. The invariant
propagates cleanly through every downstream component because the
`REQUIRED_DOCS` tuple is imported rather than stringified.

### 12.12 Takeaway 12 — Test reports as a first-class artifact

The 24 per-module reports in `tests/reports/` are not just a
test-results summary — they're a human-readable audit of what the
suite verifies. A reviewer can understand what
`alpha_research.metrics.verdict` guarantees by reading `verdict.md`
without running pytest. Pattern: every test calls
`report.record(name, purpose, inputs, expected, actual, passed,
conclusion)`. Verbose but self-documenting. Worth replicating at
the per-skill level once the skill fixture tests mature.

### 12.13 Takeaway 13 — `skill_invoker` as a test seam

All four LLM-calling pipelines accept a `skill_invoker` parameter
for dependency injection. This makes pipeline tests pure
deterministic function calls with a one-line mock. Worth copying
this shape for any new pipeline: every place that invokes an LLM
goes through an injectable callable, not a module-level `claude_call`
singleton.

---

*This document is rewriteable. The append-only log lives in
`docs/LOGS.md`.*
