# Auto-Research Agent — Work Plan

## The Top-Research Loop — A Two-Layer State Machine

The research process is a **two-layer state machine**. The outer layer controls stage transitions — including backward transitions triggered by specific discoveries that invalidate earlier conclusions. The inner layer is a search process within each stage — iterating over candidate sub-states until one satisfies the forward transition guard. Most of the time in research is spent in the inner layer. The critical skill is recognizing when a backward transition is needed rather than continuing to search within a stage that was built on a flawed premise.

```
OUTER LAYER — stage transitions with backward edges
══════════════════════════════════════════════════════════════════════

                    ┌──────────────────────────────────────────────┐
                    │          BACKWARD TRANSITIONS                │
                    │  (each triggered by a specific discovery)    │
                    └──────────────────────────────────────────────┘

                          t2 ┌───────────────────── t7
                          │  │          t4 ┌──────── │ ── t10
                          │  │          │  │  t6 ┌── │ ─── │ ── t12
                          ▼  ▼          ▼  ▼  ▼  ▼  ▼     ▼     ▼

 ┌─────────────┐ g1  ┌─────────┐ g2  ┌─────────┐ g3  ┌─────────┐
 │ SIGNIFICANCE ├────►│FORMALIZE├────►│ DIAGNOSE├────►│CHALLENGE│
 └──────▲──────┘     └────▲────┘     └────▲────┘     └────┬────┘
        │                 │               │                │
        │                 │               │             g4 │
        │                 │               │                ▼
        │            t9   │          t11  │          ┌─────────┐
        │◄────────────────│◄──────────────│◄─────────┤APPROACH │
        │    t5           │    t8         │          └────┬────┘
        │                 │               │               │
        │                 │               │            g5  │
        │                 │               │               ▼
        │            t14  │               │          ┌─────────┐
        └─────────────────┘◄──────────────┘◄─────────┤VALIDATE │
              t13                  t15               └─────────┘


FORWARD GUARDS (must satisfy to advance)
──────────────────────────────────────────────────────────────────────
g1  SIGNIFICANCE → FORMALIZE
    Problem passes ≥1 significance test per category
    (Hamming + Consequence + Durability + Compounding)

g2  FORMALIZE → DIAGNOSE
    Have formal problem def. with math (objective, variables,
    constraints, info structure) that reveals exploitable structure

g3  DIAGNOSE → CHALLENGE
    Specific failure mapped to a term/assumption in the
    formal problem definition

g4  CHALLENGE → APPROACH
    Challenge is structural, constrains solution class,
    and someone who understood only the challenge would
    predict the method class

g5  APPROACH → VALIDATE
    Approach addresses challenge via formal structure;
    one-sentence insight test passes


BACKWARD TRIGGERS (specific discoveries that invalidate earlier stages)
──────────────────────────────────────────────────────────────────────

  Back to SIGNIFICANCE (re-evaluate "is this worth doing?")
  ─────────────────────────────────────────────────────────
  t2   FORMALIZE → SIGNIFICANCE
       Formalization reveals problem is a trivial special case
       of an already-solved problem. What you thought was novel
       is actually covered by existing framework X under
       substitution Y.
       Example: you formalize your "new" planning problem and
       realize it reduces to a standard POMDP that DESPOT
       already solves efficiently.

  t5   APPROACH → SIGNIFICANCE
       Implemented method is essentially a minor variant of
       prior work — the "contribution" is incremental engineering,
       not structural insight. You built a slightly different
       version of something that already exists.
       Example: your "novel" contact-aware policy is functionally
       equivalent to impedance control with learned gains.

  t9   APPROACH → SIGNIFICANCE
       Approach works, but during evaluation you discover a
       concurrent/recent publication solves the same problem
       with the same or better approach. (§9.3: "Problem solved
       by others.")

  t13  VALIDATE → SIGNIFICANCE
       The one-sentence test reveals the contribution is
       incremental: you can only state it as "we do X slightly
       better" not as a structural insight. The problem may not
       be significant enough to yield a deep contribution.

  Back to FORMALIZE (the math is wrong or incomplete)
  ───────────────────────────────────────────────────
  t4   DIAGNOSE → FORMALIZE
       Empirical failures don't map to any term in your formal
       structure. The system fails in ways your formalization
       cannot express. The math is missing something.
       Example: you formalized grasping as quasi-static force
       closure, but failures are dynamic (objects slip during
       acceleration). Need to add dynamics to formalization.

  t7   CHALLENGE → FORMALIZE
       Challenge analysis reveals your formalization used the
       wrong framework entirely. The challenge lives in a space
       your math doesn't capture.
       Example: you formalized as MDP but the real challenge
       is partial observability — need POMDP. Or you assumed
       continuous dynamics but the challenge is hybrid contact
       switching.

  t10  APPROACH → FORMALIZE
       Approach fails because structural assumptions are wrong.
       You assumed convexity, symmetry, or decomposability that
       doesn't hold. The approach is correct FOR the formalization
       but the formalization doesn't match reality.
       Example: your convex relaxation finds solutions that
       violate the original non-convex constraints in practice.

  t14  VALIDATE → FORMALIZE
       During writing, you cannot formally state what your method
       actually solves. The method works empirically but you can't
       write the math of WHY. (Tedrake: "If you can't write the
       math, you don't understand it." This applies to your own
       results too.)

  Back to DIAGNOSE (need to re-observe what actually fails)
  ─────────────────────────────────────────────────────────
  t6   CHALLENGE → DIAGNOSE
       Challenge hypothesis doesn't match empirical evidence.
       You proposed a structural barrier but experiments show
       the system fails for a different reason than predicted.
       Example: you hypothesized the challenge is sample
       complexity, but adding 10x more data doesn't help —
       the real failure is representation, not data.

  t8   APPROACH → DIAGNOSE
       Approach solves the diagnosed failure modes but exposes
       NEW failure modes you hadn't observed. The system now
       fails differently. Need to re-diagnose with the improved
       system as the new baseline.
       Example: your tactile policy fixes insertion failures,
       but now the system fails at pre-grasp alignment — a
       failure that was masked by the earlier, more severe one.

  t11  APPROACH → DIAGNOSE
       Approach doesn't work and you can't tell why from the
       formalization alone. Need to go back to the robot, run
       the system, and observe new failure modes.

  t15  VALIDATE → DIAGNOSE
       Evaluation/ablation reveals the method works for reasons
       different than hypothesized. The ablation that removes
       your "key contribution" doesn't hurt performance.
       Something else is doing the work. Re-diagnose.

  Back to CHALLENGE (the barrier was mis-identified)
  ──────────────────────────────────────────────────
  t12  APPROACH → CHALLENGE
       No method in the implied class works. The challenge
       doesn't actually constrain to a viable solution class —
       either the challenge is mis-specified, or it's deeper
       than you thought and the real barrier is elsewhere.
       Example: you identified "distribution shift" as the
       challenge and tried conservative methods, but the real
       challenge is that the action space itself is wrong for
       the task.


KEY PRINCIPLES OF BACKWARD TRANSITIONS
──────────────────────────────────────────────────────────────────────
· A backward transition is NOT failure — it is LEARNING.
  You now know something you didn't. (§9.3: "Failures are
  informative.")

· Every backward transition should produce an artifact:
  a written record of WHAT was wrong and WHY, which constrains
  the next search in the target stage. You don't re-enter
  FORMALIZE with a blank slate — you re-enter knowing which
  formalization was wrong and why.

· Backward transitions to SIGNIFICANCE are the most expensive
  (potentially discarding months of work) but also the most
  important to recognize early. The sunk cost fallacy kills
  research. (Hamming: "If what you are doing is not important,
  why are you working on it?" — even if you've been working on
  it for 6 months.)

· Multiple backward transitions to the same stage suggest a
  deeper problem one level further back. If you keep returning
  to FORMALIZE, maybe the problem itself (SIGNIFICANCE) isn't
  well-posed. If you keep returning to DIAGNOSE, maybe your
  formalization is fundamentally off.

· The guideline's "pivot vs. push through" test (§9.3) applies
  at every backward transition:
  PIVOT (accept the backward transition) when:
    - hypothesis disproven with no reformulation path
    - the evidence clearly invalidates the earlier stage
  PUSH THROUGH (stay in current stage) when:
    - failures are informative and you can articulate what's wrong
    - core hypothesis has partial evidence
    - the problem is important enough to warrant persistence


INNER LAYER — sub-state search within each stage
══════════════════════════════════════════════════════════════════════

Each stage searches over candidates to find one that satisfies
the forward transition guard. The search IS the work of research.
A backward transition re-enters a stage with new constraints from
what was learned downstream.

┌─ SIGNIFICANCE ──────────────────────────────────────────────────────┐
│  Search space: candidate problems from Hamming list, literature,   │
│                advisor input, observed failures                     │
│  Per candidate, test:                                              │
│    · Hamming: important AND reasonable attack?                      │
│    · Consequence: if solved overnight, what concretely changes?     │
│    · Durability: still matters in 48 months? Won't scaling kill it? │
│    · Compounding: does solving this enable other research?          │
│  Forward: ≥1 candidate passes all tests → advance with it          │
│  Re-entry (from t2/t5/t9/t13): previous problem failed downstream. │
│    Carry forward WHY it failed — this constrains the new search.   │
│    Don't pick a problem with the same structural deficiency.        │
│  Exhaustion: no candidate passes → expand search (new literature,  │
│    adjacent fields, advisor) or STOP                                │
│  Agent role: literature scan to surface candidates                  │
│  Human role: judgment on all tests (agent CANNOT do this)           │
└─────────────────────────────────────────────────────────────────────┘

┌─ FORMALIZE ─────────────────────────────────────────────────────────┐
│  Search space: formal framings of the selected problem              │
│    (e.g., as MDP, POMDP, constrained opt., Bayesian inference)     │
│  Per candidate formalization, test:                                 │
│    · Is it math? (objective, variables, constraints, info structure)│
│    · Does it reveal structure? (convexity, symmetries, decomp.)    │
│    · Does it capture what makes THIS problem different?             │
│    "If you can't write the math, you don't understand it." —Tedrake │
│  Forward: formalization reveals exploitable structure → advance     │
│  Re-entry (from t4/t7/t10/t14): previous formalization was wrong.  │
│    You now know WHICH assumptions broke. Try a different framework  │
│    or add the missing structure (e.g., add dynamics, add partial    │
│    observability, remove false symmetry assumption).                │
│  Exhaustion: can't formalize after multiple framings → retreat to   │
│    SIGNIFICANCE (you may not understand the problem well enough     │
│    to work on it yet) or acquire new mathematical tools             │
│  Agent role: check if existing papers formalize similar problems    │
│  Human role: write the math (agent CANNOT do this)                  │
└─────────────────────────────────────────────────────────────────────┘

┌─ DIAGNOSE ──────────────────────────────────────────────────────────┐
│  Search space: failure modes of a minimal end-to-end system         │
│  Per failure, test:                                                 │
│    · Is it specific? ("depth can't resolve <2mm" not "grasping     │
│      fails")                                                        │
│    · Can you map it to your formal structure? (which term breaks?)  │
│  Forward: failure mapped to specific term/assumption → advance      │
│  Re-entry (from t6/t8/t11/t15): previous diagnosis was incomplete  │
│    or wrong. You now have a better system (from APPROACH) or a     │
│    specific counter-hypothesis to test. Diagnose with updated       │
│    system and updated formal lens.                                  │
│  Exhaustion: failures don't map to formalization after multiple     │
│    attempts → retreat to FORMALIZE (t4)                             │
│  Agent role: literature search for known failure modes              │
│  Human role: run the system, observe, map to formalism              │
└─────────────────────────────────────────────────────────────────────┘

┌─ CHALLENGE ─────────────────────────────────────────────────────────┐
│  Search space: structural explanations for why the failure persists │
│  Per candidate challenge, test:                                    │
│    · Is it structural, not a resource complaint?                    │
│    · Does it CONSTRAIN the solution class?                         │
│    · If someone understood only this challenge, would they predict  │
│      the method class?                                              │
│  Forward: challenge implies approach class → advance               │
│  Re-entry (from t12): the approach class failed. The challenge was  │
│    either mis-specified or incomplete. You now know which solution  │
│    class DOESN'T work — this constrains the re-search.             │
│  Exhaustion: challenge too vague after multiple attempts →          │
│    retreat to DIAGNOSE (t6, need sharper failure characterization)  │
│    or FORMALIZE (t7, the barrier lives outside your formal frame)   │
│  Agent role: find how other groups articulate similar challenges    │
│  Human role: identify the structural barrier (taste)                │
└─────────────────────────────────────────────────────────────────────┘

┌─ APPROACH ──────────────────────────────────────────────────────────┐
│  Search space: methods within the class implied by the challenge    │
│  Per candidate approach, test:                                     │
│    · Does it follow from the challenge? (not chosen for novelty)   │
│    · Does it exploit the structure your formalization revealed?     │
│  Forward: approach addresses challenge via structure → advance      │
│  Exhaustion: no method in the class works → retreat to:            │
│    CHALLENGE (t12, if the class itself is wrong)                   │
│    FORMALIZE (t10, if structural assumptions are wrong)            │
│    DIAGNOSE (t8/t11, if new failures emerged or can't tell why)    │
│    SIGNIFICANCE (t5/t9, if method is a trivial variant or scooped) │
│  Agent role: survey existing methods in the implied class           │
│  Human role: design the specific method                             │
└─────────────────────────────────────────────────────────────────────┘

┌─ VALIDATE ──────────────────────────────────────────────────────────┐
│  Tests:                                                             │
│    · One-Sentence: state contribution as one sentence with a        │
│      structural insight (not "SOTA on X")                           │
│    · Ablation: does removing your contribution degrade performance? │
│    · Scope: do claims match what was actually addressed?            │
│  Forward: all tests pass → DONE (write the paper)                  │
│  Failure: retreat to:                                               │
│    SIGNIFICANCE (t13, if contribution is incremental)              │
│    FORMALIZE (t14, if can't formally state what was solved)        │
│    DIAGNOSE (t15, if ablation shows wrong mechanism)               │
└─────────────────────────────────────────────────────────────────────┘
```

---

## The Problem

Keeping up with robotics/AI literature is a bottleneck for every researcher. The volume is overwhelming, and the critical task — identifying what matters, why it matters, and how it connects to your work — requires deep domain understanding that keyword search doesn't provide.

**The hypothesis:** An LLM agent equipped with domain-specific tools (paper search, PDF parsing, structured storage), a researcher-authored constitution, and the research guidelines as its evaluation framework can conduct autonomous literature research cycles that surface genuinely useful insights — significance assessments, formal problem structure analyses, bottleneck diagnoses, trend analyses, gap identification, and research direction proposals — not just paper summaries.

**What this is NOT:** Not a replacement for research thinking. The agent cannot assess problem significance (Hamming test), write formal problem definitions (Tedrake's point), or develop research taste. The human provides significance judgments, formalizations, and taste at checkpoints. The agent provides breadth, structure, consistency, and the ability to systematically screen large volumes of literature against the guideline's standards.

---

## Bottleneck Diagnosis

Following the guidelines: build the simplest mental model of the system, identify what actually fails.

### What LLMs do well for research
- Summarizing individual papers (given full text)
- Applying structured evaluation rubrics consistently across many papers
- Identifying surface and moderate-depth connections between papers
- Structuring information into readable, organized reports
- Exhaustive coverage — reading more papers than a human has time for

### Where LLMs will fail (the real bottlenecks, ordered by severity)

1. **Assessing problem significance.** The revised guidelines (§2.2) require the Hamming test, consequence test, and durability test. An LLM can check whether a paper *argues* significance but cannot independently judge whether a problem is truly important — this requires the researcher's own Hamming list, domain intuition, and strategic judgment about where the field is heading.

2. **Evaluating formal problem definitions.** The guidelines now stress (§2.4) that if you can't write the math, you don't understand the problem. An LLM can check whether a paper *has* a formal problem statement, but cannot deeply assess whether the formalization captures the right structure, exploits the right symmetries, or reveals the right decomposition. It can detect *absence* of formalization (which is itself valuable screening).

3. **Evaluating mathematical rigor and structural insight.** The guidelines stress knowing convexity, symmetries, stability (Part III). LLMs can parse equations but cannot deeply assess whether a formulation exploits the right structure.

4. **Physical intuition.** The guidelines emphasize that understanding failure modes requires hands-on experience (§1.2, 1.5). An LLM has never watched a robot crumple a cloth bag.

5. **Judging true novelty.** Is this genuinely new or a minor variant? Requires deep familiarity with the field's history.

6. **Detecting overclaiming.** Papers oversell. The guidelines list specific overclaiming patterns. An LLM can check for these *if explicitly instructed*, but its default is to accept claims at face value.

7. **Cross-modal reasoning.** Understanding figures, tables, mathematical derivations, and architecture diagrams requires multimodal reasoning that text extraction partially destroys.

**Design implication:** The agent should be *transparent about confidence* and explicitly flag what requires human judgment. The agent CAN: screen for formal problem statements (present/absent), check experimental rigor against specific criteria, detect overclaiming patterns, map papers to the capability frontier. The agent CANNOT: judge significance (Hamming test), assess formalization quality, evaluate physical feasibility, or determine true novelty. Human checkpoints should focus on these high-judgment assessments.

---

## How the Agent Maps to the Research Guidelines

The agent is a tool for executing the guidelines' methodology. Each analysis mode corresponds to a guideline phase:

| Guideline Phase | Agent Analysis Mode | What the Agent Does |
|---|---|---|
| **Significance screening** (§2.2) | **Significance Screen** | For each paper: does it argue importance? Does it pass the consequence test? The durability test? Flag papers that skip significance entirely. **Human must judge**: actual importance (Hamming test) |
| **Problem definition check** (§2.4) | **Formalization Check** | Does the paper have a formal problem statement? Is it math or prose? Does it identify structure (convexity, symmetry, decomposition)? **Human must judge**: quality of the formalization |
| **Week 1-2: Survey the landscape** (§5.2) | **Landscape Survey** | Map a subfield: who's publishing what, which approaches exist, what the claimed results are, where groups are heading |
| **Bottleneck diagnosis** (§5.1 Axis 1) | **Gap Analysis** | Across surveyed papers, identify recurring limitations, unsolved failure modes, bottlenecks cited by multiple groups |
| **Capability frontier mapping** (§5.1 Axis 3) | **Frontier Report** | Classify current capabilities into reliable/sometimes/can't-yet for a specific sub-area, with evidence |
| **Hypothesis formation** (§5.2 Week 5-6) | **Direction Proposal** | Based on gaps and frontier, propose specific testable hypotheses with supporting evidence. Apply the One-Sentence Test. |
| **Ongoing monitoring** | **Paper Digest** | Weekly/on-demand: new papers evaluated against the rubric, flagged by relevance, quality, and significance |
| **Related work for writing** (§9.1) | **Deep Analysis** | Single paper evaluated against the full Appendix B rubric (now including §B.1 significance and formalization) |
| **Trend detection** | **Trend Report** | How a subfield's methods, benchmarks, and results are shifting over 6-12 months |

Each mode uses the Paper Evaluation Rubric (Appendix B) as its core evaluation framework. The rubric is not optional — it's what prevents the agent from producing shallow summaries.

---

## Design Decisions

| Decision | Choice | Why |
|---|---|---|
| LLM backbone | Claude Agent SDK | Agent loop + tool use built in; avoids reimplementing orchestration |
| Language | Python 3.12+ | Standard for AI/ML |
| Primary sources | ArXiv + Semantic Scholar | ArXiv for recency, S2 for citation/influence metadata |
| Storage | SQLite + local files | Zero-config, sufficient for single-user |
| Execution model | **CLI only (MVP)** | One mode that works. Daemon/REPL only after core cycle proves useful |
| Evaluation framework | Research guidelines Appendix B rubric | Structured, consistent, operationalizable |

---

## Architecture

```
Human                         Research Guidelines
(constitution.yaml)           (embedded in system prompt as evaluation framework)
        │                                │
        ▼                                ▼
┌──────────────────────────────────────────────────────────┐
│              Claude Agent SDK Agent                       │
│                                                          │
│  System Prompt:                                          │
│  ├─ Identity + domain focus (from constitution)          │
│  ├─ Evaluation rubric (from guidelines Appendix B)       │
│  ├─ Quality criteria (from guidelines Parts I-VII)       │
│  ├─ Analysis mode instructions (survey/gap/deep/etc.)    │
│  └─ Honesty protocol (flag confidence, don't overclaim)  │
│                                                          │
│  Tools:                                                  │
│  ├─ arxiv_search    (query + category + date filters)    │
│  ├─ paper_fetch     (PDF download + text extraction)     │
│  ├─ semantic_scholar (citations, influence, refs, graph)  │
│  ├─ knowledge_read  (query prior papers, analyses, Qs)   │
│  ├─ knowledge_write (persist papers, scores, findings)   │
│  └─ report          (generate structured markdown)       │
│                                                          │
│  Knowledge Store (SQLite):                               │
│  ├─ papers (metadata, text, source)                      │
│  ├─ evaluations (per-paper rubric scores + evidence)     │
│  ├─ findings (cross-paper synthesis, per cycle)          │
│  ├─ questions (pending, explored, follow-up)             │
│  └─ feedback (human corrections, steering)               │
└──────────────────────────────────────────────────────────┘
        │
        ▼
   Structured Report → Human Review → Feedback → Next Cycle
```

### The System Prompt (The Critical Piece)

The system prompt translates the research guidelines into operational instructions. This is the highest-leverage design decision. It must encode:

**From Part II — Significance (§2.2, NEW — highest priority):**
- For each paper: does it argue why the problem is important? Can you identify a concrete downstream consequence of solving it? Would this still matter in 48 months, or will scaling solve it? Does it have compounding value (enables other research)?
- Flag papers that skip significance entirely — they may be "method looking for a problem."
- Note: the agent can detect *absence* of significance arguments but CANNOT independently judge actual importance. Flag for human.

**From Part II — Problem Definition (§2.4, NEW — critical):**
- Does the paper have a formal problem statement (math, not just prose)? Is the problem stated as optimization, estimation, or decision problem with explicit objective, variables, constraints?
- Does the paper identify mathematical structure (convexity, symmetries, dimensionality, decomposability)?
- Does the formalization reveal what makes THIS problem different from the general case?
- Flag papers with no formalization — per Tedrake, "if you can't write the math, you don't understand the problem."
- Note: the agent can detect *presence/absence* of formalization but CANNOT deeply judge its quality. Flag for human.

**From Part I (What makes robotics hard):**
- When evaluating a paper, check: does it acknowledge embodiment specificity? Does it discuss contact modeling? Is the physical setup reproducible? Does it address safety?

**From Part III (Mathematical foundations):**
- Flag papers that exploit mathematical structure (equivariance, convexity, decomposition) — these are often higher quality. Flag papers that ignore available structure — this is a weakness.
- Note: this is a LOW-CONFIDENCE assessment for the agent. Flag for human review rather than asserting judgment.

**From Part IV (Representations):**
- For each paper: what representation is used? Is it justified for the task? What sensing modalities? Does it address the affordance/interactive perception question?

**From Part VI (Core tensions):**
- Position each paper on the structure-vs-learning spectrum. On the specialist-vs-generalist spectrum. On the sim-vs-real spectrum.
- For LLM-in-the-loop papers: does the paper address the grounding gap? Does the LLM actually contribute physical reasoning or just semantic sequencing?
- For foundation model papers: what's the data requirement? Is the contribution above the commoditization line?
- For compositional/long-horizon papers: does the method compose? Is error compounding addressed?

**From Part VII (Learning dynamics):**
- Check for: reward design justification, distribution shift analysis, multimodality handling in imitation learning, safe exploration mechanisms.

**From Part VIII (Evaluation):**
- Apply the Appendix B rubric systematically (now including B.1 significance and formalization). Check for: sufficient trials, strong baselines, failure analysis, generalization tests, reported human effort, perturbation robustness.

**Honesty protocol:**
- For each rubric dimension, report: score (1-5), evidence (quotes/sections from paper), confidence (high/medium/low).
- Never assert novelty without comparing to knowledge store contents.
- Flag when PDF extraction may have missed critical content (equations, figures, tables).
- Explicitly state what the agent CANNOT assess (physical feasibility, true novelty against full field history).

---

## Implementation Plan

Following the guidelines: minimal system → run → observe failure → iterate.

The system is not a simple pipeline. It is a hierarchy of state machines: the outer research loop (§top), the agent orchestration per mode, and several sub-components (search, paper processing, evaluation, knowledge management, report generation) that are each stateful processes with their own transitions. This section details each layer.

---

### Sub-State-Machines: The Components

Before the build order, we need to understand what each component actually IS — because "ArXiv search tool" and "knowledge store" are not simple functions. They are stateful processes.

#### SM-1: Search & Discovery

Search is not "query → results." It is iterative convergence toward coverage of a topic space.

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

**QUERY** — Generate search queries from the user's question.
  - Not just keywords. The agent must generate multiple query
    formulations: synonyms, related concepts, author names, method
    names. A question about "tactile manipulation" should also
    search "GelSight grasping," "contact-rich insertion," etc.
  - Sources: ArXiv API (keyword + category + date), Semantic Scholar
    (keyword, paper-by-ID, author-by-ID, recommendations).

**FILTER** — Relevance screening of raw results.
  - Two-tier: fast filter (title + abstract vs. constitution focus
    areas) then slow filter (fetch full text, check if the paper
    actually addresses the question).
  - Must handle: duplicates (same paper on ArXiv and S2), preprints
    vs. published versions (prefer published), retracted papers.
  - Output: candidate paper set with relevance scores.

**ASSESS COVERAGE** — Are we missing important papers/groups/approaches?
  - Check: are all `key_groups` from the constitution represented?
    If Berkeley (Levine) has no papers in results for a manipulation
    survey, something is wrong.
  - Check: are there obvious approach categories with no papers?
    (e.g., survey covers RL approaches but no imitation learning)
  - Check: citation graph — do the found papers cite important papers
    we haven't found? (high-cited references not in our set = gap)

**EXPAND** — Fill coverage gaps.
  - Citation graph traversal: follow references of high-scoring papers.
    Follow citing-papers of seminal papers.
  - Query reformulation: generate new queries targeting gaps.
  - Adjacent field search: broaden ArXiv categories if needed.
  - Author search: query recent papers by key researchers.

**CONVERGE** — Diminishing returns on new relevant papers.
  - Criterion: last expansion round added <10% new relevant papers.
  - Or: budget exhausted (max_papers_per_cycle from constitution).

**Backward transitions:**
  - ASSESS → QUERY: coverage gaps reveal we need entirely different
    search terms (not just expanded queries).
  - FILTER was too aggressive: relaxing relevance threshold reveals
    important tangential papers.

**Implementation:** This is NOT a single tool call. The `arxiv_search`
and `semantic_scholar` tools are primitive operations. Search & Discovery
is orchestrated by the agent's reasoning loop — the system prompt must
instruct the agent to iterate through these stages rather than doing a
single search. The tools provide the primitives; the agent provides the
state machine logic via its tool-use loop.

**Data model:**
```python
class SearchState(BaseModel):
    queries_executed: list[SearchQuery]       # history of all queries
    papers_found: dict[str, PaperCandidate]  # arxiv_id → candidate
    coverage_assessment: CoverageReport | None
    expansion_rounds: int
    status: Literal["querying", "filtering", "assessing",
                     "expanding", "converged"]
```

#### SM-2: Paper Processing Pipeline

Paper processing is not "download PDF → extract text." It is a quality-aware pipeline that must handle degraded extraction gracefully.

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

**DISCOVER** — Paper reference identified (from search or citation graph).
  - Input: arxiv_id, DOI, or title+authors.
  - Check knowledge store: already have this paper? Skip or update.

**FETCH** — Acquire the full text.
  - Primary: ArXiv PDF download.
  - Fallback 1: ArXiv HTML (ar5iv) — better for math extraction.
  - Fallback 2: Semantic Scholar abstract + metadata only.
  - Fallback 3: Paper's own hosted PDF (if DOI resolves).
  - Must handle: rate limiting (ArXiv: max 1 req/3s), timeouts,
    403s, paywalls.
  - Track: which source succeeded, for quality metadata.

**EXTRACT** — Convert document to structured text.
  - PDF: pymupdf text extraction.
  - HTML: parse ar5iv HTML, preserve math as LaTeX.
  - Output: structured sections (abstract, intro, method, experiments,
    related work, conclusion) + raw text.
  - Section detection is heuristic — papers don't follow a single format.

**VALIDATE** — Assess extraction quality.
  - Check: is extracted text coherent? (not mojibake, not just figure
    captions)
  - Check: are mathematical expressions preserved or mangled?
    (heuristic: ratio of valid LaTeX-like tokens to garbled symbols)
  - Check: are all expected sections present? (a paper with no method
    section extracted likely had extraction failure)
  - Output: quality score per section + list of flagged issues.

**ENRICH** — Add metadata beyond the paper text.
  - From Semantic Scholar: citation count, influential citation count,
    references, citing papers, venue, TLDR.
  - Code availability: check Papers With Code, GitHub links in paper.
  - Related papers: S2 recommendations.

**STORE** — Persist with quality metadata.
  - Paper text + metadata + extraction quality flags + source info.
  - If extraction quality is low for certain sections: those sections
    are marked as unreliable in the knowledge store, and the agent
    should NOT score rubric dimensions that depend on them.

**Data model:**
```python
class Paper(BaseModel):
    arxiv_id: str | None
    s2_id: str | None
    doi: str | None
    title: str
    authors: list[str]
    venue: str | None
    year: int
    abstract: str
    full_text: str | None
    sections: dict[str, str]           # section_name → text
    extraction_source: Literal["pdf", "html", "abstract_only"]
    extraction_quality: ExtractionQuality
    metadata: PaperMetadata            # citations, code, etc.
    status: Literal["discovered", "fetched", "extracted",
                     "validated", "enriched", "stored"]

class ExtractionQuality(BaseModel):
    overall: Literal["high", "medium", "low", "abstract_only"]
    math_preserved: bool
    sections_detected: list[str]
    flagged_issues: list[str]          # "math garbled in §3",
                                       # "figures not extracted", etc.
```

#### SM-3: Paper Evaluation

Evaluation is not "apply rubric." It is a multi-pass analysis that builds up understanding progressively, cross-references against prior knowledge, and must be honest about what it can and cannot assess.

```
┌──────┐     ┌───────────┐     ┌──────────┐     ┌─────────────┐
│ SKIM ├────►│ DEEP READ ├────►│ EVALUATE ├────►│ CROSS-CHECK │
└──┬───┘     └─────┬─────┘     └────┬─────┘     └──────┬──────┘
   │               │                │                   │
   │skip           │re-read         │revise             │
   │(irrelevant)   │section         │scores             │
   ▼               ▼                ▼                   ▼
┌──────┐     ┌───────────┐     ┌──────────┐     ┌──────────┐
│DISCARD│    │(loop back)│     │(loop back)│    │ FINALIZE │
└──────┘     └───────────┘     └──────────┘     └──────────┘
```

**SKIM** — Quick relevance and quality estimate.
  - Read: title, abstract, figures/tables (if available), conclusion.
  - Output: relevance score (0-1), estimated quality tier (high/med/low),
    whether to proceed to deep read.
  - Decision: if relevance < min_relevance from constitution → DISCARD
    (store as "skimmed, not relevant" to avoid re-processing).
  - This pass is cheap — use faster model (Haiku) if multi-model
    pipeline is available.

**DEEP READ** — Full paper analysis.
  - Read method section: what is the technical approach?
  - Read experiments: what was tested, how many trials, what baselines?
  - Read related work: how does the paper position itself?
  - Extract: task→problem→challenge→approach chain (the most important
    extraction — this is what the guideline demands).
  - Extract: formal problem statement (if present — detect presence
    of mathematical formalization, not just prose).
  - Note sections where extraction quality is low → flag those
    dimensions as LOW CONFIDENCE.

**EVALUATE** — Apply rubric with evidence.
  - For each rubric dimension (B.1-B.7):
    - Score (1-5)
    - Evidence (quotes from paper, with section references)
    - Confidence (high/medium/low) — driven by both the agent's
      inherent limitation for that dimension AND extraction quality.
  - Significance assessment (§2.2 tests): not just "does it argue
    importance" but structured checks per test.
  - Formalization check (§2.4): is there math? What kind? Does it
    identify structure?
  - May loop back to DEEP READ if evaluation reveals need for more
    careful reading of a specific section (e.g., the ablation table
    needs closer inspection).

**CROSS-CHECK** — Compare against knowledge store.
  - Novelty: is this contribution novel vs. papers already in the store?
    (Not absolute novelty — just relative to what the store knows.)
  - Contradictions: does this paper's finding contradict a prior
    evaluation? If yes, flag for human review.
  - Connections: what does this paper extend, improve on, or relate to?
  - Method comparison: other papers use the same benchmark/task —
    how do results compare?
  - May revise evaluation scores: if cross-checking reveals the
    paper's baselines are weaker than what another paper achieved on
    the same task, the evaluation score for "baselines" drops.

**FINALIZE** — Produce evaluation with all flags.
  - Package: rubric scores + evidence + confidence + cross-check notes
    + human-review flags.
  - Persist to knowledge store.

**Data model:**
```python
class Evaluation(BaseModel):
    paper_id: str
    cycle_id: str                      # which research cycle
    mode: str                          # which analysis mode produced this
    status: Literal["skimmed", "deep_read", "evaluated",
                     "cross_checked", "finalized"]

    # The core chain (guideline §2.1-2.8)
    task_chain: TaskChain | None       # extracted task→problem→challenge→approach
    has_formal_problem_def: bool
    formal_framework: str | None       # "MDP", "POMDP", "constrained opt", etc.
    structure_identified: list[str]    # ["convexity", "SE(3) symmetry", ...]

    # Rubric scores (Appendix B)
    rubric_scores: dict[str, RubricScore]  # dimension → score
    significance_assessment: SignificanceAssessment

    # Cross-check results
    related_papers: list[PaperRelation]
    contradictions: list[Contradiction]
    novelty_vs_store: Literal["novel", "incremental", "duplicate",
                               "unknown"]

    # Quality flags
    extraction_limitations: list[str]  # dimensions affected by bad extraction
    human_review_flags: list[str]      # what the human should look at

class RubricScore(BaseModel):
    score: int                         # 1-5
    confidence: Literal["high", "medium", "low"]
    evidence: list[str]                # quotes with section refs
    reasoning: str                     # why this score

class TaskChain(BaseModel):
    task: str | None
    problem: str | None
    challenge: str | None
    approach: str | None
    one_sentence: str | None           # the one-sentence insight test
    chain_complete: bool               # are all steps filled?
    chain_coherent: bool               # does approach follow from challenge?
```

#### SM-4: Knowledge Store (Living Knowledge Graph)

The knowledge store is not a database with CRUD operations. It is an evolving representation of the field's state that grows across cycles, detects shifts, and may require re-evaluation of old entries.

```
┌────────┐     ┌───────┐     ┌─────────┐     ┌────────┐
│ INGEST ├────►│ INDEX ├────►│ CONNECT ├────►│ EVOLVE │
└────────┘     └───────┘     └─────────┘     └───┬────┘
                                                  │
                                   triggers re-evaluation
                                   of related entries
                                                  │
                                                  ▼
                                             ┌─────────┐
                                             │RE-ASSESS│
                                             └─────────┘
```

**INGEST** — New paper + evaluation enters the store.
  - Deduplication: same paper from different search cycles.
  - Version management: preprint → camera-ready update.
  - Conflict resolution: if a paper was evaluated in a previous cycle
    with different scores, keep both with cycle timestamps.

**INDEX** — Make the entry searchable and classifiable.
  - Topic clustering: assign to topic clusters (which may evolve).
  - Approach tagging: which method class (§2.7 table)?
  - Capability frontier position: reliable/sometimes/can't-yet.
  - Author/group mapping: link to key_groups from constitution.

**CONNECT** — Find relationships between papers.
  - Citation-based: paper A cites paper B (from S2 data).
  - Content-based: papers addressing the same task/challenge.
  - Methodological: papers using the same approach class.
  - Contradictory: papers with conflicting findings on same question.
  - Evolutionary: paper B extends/improves/supersedes paper A.
  - These connections are what enable cross-paper synthesis in reports.

**EVOLVE** — The store's understanding changes over time.
  - New papers can change the significance assessment of old papers:
    if a new paper solves a problem, papers working on the same
    problem become less significant (durability test failed).
  - New papers can change novelty assessments: what seemed novel in
    cycle 1 may be incremental after cycle 5 reveals related work.
  - Capability frontier shifts: what was "can't yet" in January may
    be "sometimes" by June.
  - Trend detection: tracking how approach distributions shift.

**RE-ASSESS** — Triggered when new information invalidates old evaluations.
  - A new highly-cited paper in the same area → re-check novelty of
    related papers in the store.
  - Human feedback corrects a score → propagate to similar papers
    (if paper A was scored too high and paper B is similar, check B).
  - Not automatic for every ingestion — triggered by specific signals:
    high-impact paper, human correction, contradiction detected.

**Schema (SQLite):**
```sql
-- Core entities
papers           (id, arxiv_id, s2_id, doi, title, authors_json,
                  venue, year, abstract, full_text, sections_json,
                  extraction_source, extraction_quality_json,
                  metadata_json, first_seen_cycle, last_updated)

evaluations      (id, paper_id, cycle_id, mode, status,
                  task_chain_json, has_formal_problem_def,
                  formal_framework, structure_identified_json,
                  rubric_scores_json, significance_json,
                  related_papers_json, contradictions_json,
                  novelty_vs_store, extraction_limitations_json,
                  human_review_flags_json, created_at)

-- Cross-paper structure
paper_relations  (id, paper_a_id, paper_b_id,
                  relation_type,     -- extends|contradicts|supersedes
                                     -- |same_task|same_method|cites
                  evidence, confidence, cycle_id)

-- Synthesis artifacts
findings         (id, cycle_id, mode, finding_type,
                  content, evidence_paper_ids_json,
                  confidence, human_validated)

-- Evolution tracking
frontier_snapshots (id, cycle_id, domain,
                    reliable_json, sometimes_json, cant_yet_json)

topic_clusters     (id, name, description, paper_ids_json,
                    cycle_id, parent_cluster_id)

-- Human interaction
questions        (id, cycle_id, question, status,
                  answer, source_paper_ids_json)

feedback         (id, cycle_id, target_type, target_id,
                  correction, applied)
```

#### SM-5: Report Generation (Synthesis Engine)

Report generation is not "fill template." It is multi-pass synthesis that must aggregate, cluster, synthesize, verify consistency, and produce output appropriate to the mode.

```
┌───────────┐    ┌─────────┐    ┌────────────┐    ┌────────┐
│ AGGREGATE ├───►│ CLUSTER ├───►│ SYNTHESIZE ├───►│ VERIFY │
└───────────┘    └─────────┘    └─────┬──────┘    └───┬────┘
                                      │               │
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

**AGGREGATE** — Collect all relevant evaluations and knowledge.
  - From knowledge store: evaluations matching the query/mode.
  - From prior cycles: findings that are still valid.
  - From human feedback: corrections that should inform this report.

**CLUSTER** — Group papers by meaningful structure.
  - By approach type (not chronology — guideline §10.1 related work).
  - By task/challenge addressed.
  - By research group (track who is moving where).
  - By capability frontier position.
  - The clustering itself is informative — it reveals the structure
    of the subfield.

**SYNTHESIZE** — Identify cross-paper patterns.
  - Gaps: what recurring limitations appear across multiple papers?
  - Trends: how has the approach distribution shifted?
  - Contradictions: where do papers disagree? (valuable signal)
  - Frontier shifts: what moved from "can't yet" to "sometimes"?
  - Convergence: are multiple groups independently arriving at the
    same approach? (strong signal that an approach is right)
  - Divergence: are established approaches being abandoned? Why?

**VERIFY** — Check synthesis consistency.
  - Does each synthesis claim have supporting evidence from ≥2 papers?
  - Are there synthesis claims that contradict individual evaluations?
  - Are confidence levels appropriately propagated? (synthesis of
    low-confidence evaluations = low-confidence synthesis)
  - If inconsistencies found → RE-SYNTHESIZE with corrections.

**FORMAT** — Produce mode-specific output.
  - Each mode (digest, deep, survey, gap, frontier, direction) has
    a different template and different required sections.
  - Insert human-review flags at appropriate points.
  - Include evidence quotes (required by constitution).

**Gap-triggered re-search:** If synthesis reveals an obvious gap
(e.g., "all papers use RL but none use TAMP for this task" — is that
because TAMP doesn't work here, or because no one has tried?), the
agent should search specifically for the missing approach before
concluding it's a gap. This triggers a backward transition to SM-1
(Search & Discovery).

#### SM-6: Agent Orchestration Per Mode

Each analysis mode has its own orchestration logic — a sequence of
SM-1 through SM-5 invocations with mode-specific parameters. This is
what the agent's reasoning loop implements.

**Mode: `digest` (weekly screening)**
```
SM-1(QUERY: recent papers, date filter: last 7 days)
  → SM-2(FETCH+EXTRACT each paper)
    → SM-3(SKIM all → DEEP READ top-K → EVALUATE)
      → SM-5(FORMAT as digest)
```
Light-weight. No deep cross-checking. Focus on surfacing signal.

**Mode: `deep` (single paper analysis)**
```
SM-2(FETCH+EXTRACT the target paper)
  → SM-3(full pipeline: SKIM → DEEP READ → EVALUATE → CROSS-CHECK)
    → SM-5(FORMAT as deep analysis report)
```
No search needed (paper specified). Heavy evaluation. Full cross-check
against knowledge store.

**Mode: `survey` (landscape mapping)**
```
SM-1(QUERY: broad, multiple formulations, iterate to CONVERGE)
  → SM-2(FETCH+EXTRACT all discovered papers)
    → SM-3(SKIM all → DEEP READ high-relevance → EVALUATE)
      → SM-4(CONNECT: build relation graph across papers)
        → SM-5(full synthesis: CLUSTER → SYNTHESIZE → VERIFY)
          → SM-5(FORMAT as survey report)
            → SM-1(EXPAND if synthesis reveals gaps)  ← backward!
```
The most complex mode. Iterates between search and synthesis until
coverage is sufficient. This is the mode most likely to trigger
gap-driven re-search.

**Mode: `gap` (bottleneck identification)**
```
SM-4(QUERY knowledge store for existing papers in area)
  → SM-1(SEARCH for papers specifically about limitations/failures)
    → SM-3(EVALUATE with focus on weaknesses + failure analysis)
      → SM-5(SYNTHESIZE: aggregate failure modes, find commonalities)
        → SM-5(FORMAT as gap report with proposed directions)
```
Requires existing knowledge in the store (prior survey or digests).
Specifically looks for failure modes and limitations.

**Mode: `frontier` (capability frontier mapping)**
```
SM-4(QUERY knowledge store for frontier_snapshots)
  → SM-1(SEARCH for papers claiming new capabilities)
    → SM-3(EVALUATE: focus on experimental evidence for capabilities)
      → SM-4(UPDATE frontier snapshot)
        → SM-5(FORMAT: diff current vs. previous frontier)
```
Requires temporal knowledge — comparing against prior frontier snapshots.

**Mode: `direction` (research direction proposal)**
```
SM-4(READ: latest gap report + frontier report + human's Hamming list)
  → SM-5(SYNTHESIZE: cross-reference gaps with frontier with Hamming)
    → SM-1(SEARCH: specifically for enabling work — new tools, methods,
            datasets that create "why now" openings)
      → SM-5(FORMAT: proposed directions with significance tests +
              formalization prompts + one-sentence test)
```
The most judgment-heavy mode. The agent proposes, the human judges.
Each proposed direction should prompt the human to attempt formalization.

---

### Phase 1: Minimal End-to-End System (Weeks 1-2)

**Goal:** `alpha-research run --question "..."` produces useful output
for `digest` and `deep` modes. Survey/gap/frontier/direction are Phase 2.

**Why these modes first:** `digest` exercises SM-1→SM-2→SM-3→SM-5 as a
single forward pass (simplest orchestration). `deep` exercises SM-2→SM-3
with full evaluation depth (most important quality test). Together they
validate every sub-state-machine except SM-4's evolution logic and SM-5's
cross-cycle synthesis — those are Phase 2.

**Build order** (each step builds on the previous):

1. **Project skeleton** — `pyproject.toml`, package structure, dependencies
2. **Data models** — Pydantic models for all entities (Paper,
   ExtractionQuality, Evaluation, RubricScore, TaskChain,
   SignificanceAssessment, SearchState, etc.). These are the vocabulary
   of the system — get them right before writing any logic.
3. **Constitution loader** — Pydantic models for constitution YAML,
   validation, defaults for missing fields.
4. **Knowledge store schema + basic CRUD** — SQLite tables per SM-4
   schema. CRUD for papers, evaluations, findings. No relation graph
   or evolution logic yet (Phase 2).
5. **Paper fetch + extract (SM-2, forward path only)** — PDF download
   from ArXiv, text extraction via pymupdf, extraction quality
   validation. HTML fallback and S2-only fallback deferred to Phase 2.
6. **ArXiv search tool (SM-1, single query only)** — Query by keywords
   + category + date range. No coverage assessment or expansion yet
   (Phase 2). Returns structured metadata.
7. **Semantic Scholar tool (basic)** — Query by paper ID for metadata:
   citations, references, venue, TLDR. Citation graph traversal
   deferred to Phase 2.
8. **Evaluation logic (SM-3, SKIM + EVALUATE)** — This is the hardest
   step. The agent must apply the rubric, extract the task chain,
   check for formalization, assess significance arguments. Implemented
   as system prompt instructions — the LLM does the evaluation, the
   tool provides structure.
9. **Knowledge read/write tools** — Agent interface: save paper +
   evaluation, query papers by topic/score/date, get prior evaluations.
   No cross-checking or relation detection yet (Phase 2).
10. **Report tool (SM-5, FORMAT only)** — Generate structured markdown
    from evaluations. Template-based per mode. No synthesis step yet
    (Phase 2: for digest, the "report" is just a ranked list of
    evaluated papers).
11. **System prompt builder** — Constitution + research guidelines rubric
    → system prompt. This is the highest-leverage step. It must
    encode the evaluation rubric (Appendix B with significance and
    formalization), the honesty protocol, and the task chain extraction
    instructions. **← hardest step, iterate multiple times**
12. **Agent setup** — Agent SDK agent with tools registered. Tool
    descriptions must be precise enough for the agent to use them
    correctly in sequence.
13. **CLI entry point** — `alpha-research run --question "..." --mode
    [digest|deep]`. Other modes return "not yet implemented."

**Project structure:**
```
alpha_research/
├── pyproject.toml
├── config/
│   └── constitution.yaml
├── src/alpha_research/
│   ├── __init__.py
│   ├── main.py              # CLI (typer)
│   ├── config.py            # Constitution models + loader
│   ├── agent.py             # Agent SDK setup + system prompt
│   ├── models.py            # ALL data models (Paper, Evaluation,
│   │                        # SearchState, TaskChain, etc.)
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── arxiv_search.py  # SM-1 primitives
│   │   ├── paper_fetch.py   # SM-2 primitives
│   │   ├── semantic_scholar.py
│   │   ├── knowledge.py     # SM-4 read/write interface
│   │   └── report.py        # SM-5 formatting
│   ├── knowledge/
│   │   ├── __init__.py
│   │   ├── schema.py        # SQLite schema (SM-4)
│   │   └── store.py         # SQLite operations
│   └── prompts/
│       ├── __init__.py
│       ├── system.py        # Constitution + rubric → system prompt
│       └── rubric.py        # Appendix B rubric as structured prompt
├── data/                    # Runtime (gitignored)
│   ├── papers/              # Downloaded PDFs + extracted text
│   └── knowledge.db
├── output/reports/          # Generated reports (gitignored)
└── tests/
    ├── test_models.py
    ├── test_store.py
    ├── test_paper_fetch.py
    └── test_evaluation.py   # Calibration tests (agent vs. human)
```

**Tech stack:**

| Component | Choice |
|---|---|
| Agent framework | `claude-agent-sdk` |
| ArXiv | `arxiv` library |
| Semantic Scholar | `httpx` + S2 REST API |
| PDF parsing | `pymupdf` |
| Storage | `sqlite3` |
| Data models | `pydantic` |
| CLI | `typer` |
| Templates | `jinja2` |

### Phase 1 Output Format

A report from `--mode deep` for a single paper should look like:

```markdown
# Paper Evaluation: [Title]
**Authors:** ... | **Venue:** ... | **Date:** ...
**ArXiv:** [link] | **Code:** [link or N/A]

## Summary
[2-3 paragraph summary of the paper's contribution]

## Rubric Evaluation

| Dimension | Score | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
| **Significance & Problem Definition** | 4/5 | Medium | Argues importance: contact-rich assembly without CAD is a "sometimes" capability at the frontier. Has formal problem statement (constrained optimization). BUT: agent CANNOT judge whether formalization captures the right structure — FLAGGED FOR HUMAN |
| Technical Approach | 3/5 | Medium | Uses diffusion policy but unclear why diffusion is needed vs. simpler BC |
| Experimental Rigor | 2/5 | High | Only 5 trials per condition, no confidence intervals, baselines not tuned |
| Representation | 4/5 | Medium | Point cloud + tactile input justified for contact task |
| Generalization | 2/5 | High | Tested on 3 objects in single environment |
| Practical Viability | 3/5 | Low | Claims real-time but inference details missing |
| Reproducibility | 3/5 | High | Code promised but not yet released |

## Significance Assessment (§2.2 Tests)
- **Hamming test:** [Does the paper address a problem on the field's "important problems" list? Is there a reasonable attack?]
- **Consequence test:** [If solved, what concretely changes?]
- **Durability test:** [Will this matter in 48 months? Would a bigger model trivially solve it?]
- **Compounding value:** [Does solving this enable other research?]
- **HUMAN JUDGMENT REQUIRED:** Agent can detect significance *arguments* but cannot independently judge actual importance.

## Problem Formalization Assessment (§2.4)
- **Formal statement present?** [Yes/No — is the problem stated as math?]
- **Structure identified?** [Convexity, symmetries, dimensionality, decomposability?]
- **Formalization quality:** LOW CONFIDENCE — flagged for human review
- [If no formalization: "Paper lacks formal problem definition. Per guidelines §2.4: 'if you can't write the math, you don't understand the problem.'"]

## Strengths
- [Specific strengths with evidence]

## Weaknesses (per research guidelines)
- Experimental rigor: 5 trials insufficient (guidelines say 10 minimum, 20+ preferred)
- No failure analysis section (guidelines: "the most undervalued section")
- Baselines: only compared against BC, not scripted/simple policy
- [Flag] Mathematical structure assessment: LOW CONFIDENCE — paper uses optimization formulation but agent cannot fully assess whether the formulation exploits the right structure

## Connections to Prior Work
- Extends [Paper X] by adding tactile input
- Contradicts [Paper Y]'s finding that vision alone suffices for this task class
- Uses same benchmark as [Paper Z], enabling direct comparison

## Open Questions
- Would this method compose with a pick-and-place skill for longer-horizon tasks?
- What happens when contact dynamics differ significantly from training?
```

A report from `--mode survey` should produce:

```markdown
# Landscape Survey: [Topic]
**Scope:** [time range, venues, query terms]
**Papers analyzed:** N | **Date:** ...

## Significance Screening
[Of N papers surveyed, how many argue significance convincingly? How many skip it entirely?]
[Which problems pass the Durability Test — will they still matter in 48 months?]
[Which problems have compounding value — solving them enables other research?]
**HUMAN CHECKPOINT:** Review the significance assessments. The agent flags patterns but cannot judge actual importance.

## Problem Formalization Landscape
[How many papers have formal problem statements (math, not prose)?]
[What formal frameworks are being used (MDP, POMDP, constrained optimization, etc.)?]
[Which papers identify and exploit mathematical structure?]
**HUMAN CHECKPOINT:** Assess formalization quality for papers flagged as having formal definitions.

## Approach Taxonomy
[Map of approaches organized by type, not chronology]

## Capability Frontier (current)
- Reliable: [...]
- Sometimes: [...]
- Can't yet: [...]

## Key Groups and Directions
| Group | Recent Focus | Notable Results | Formalization Quality |
|-------|-------------|-----------------|----------------------|
| Berkeley (Levine) | ... | ... | ... |
| Stanford (Finn) | ... | ... | ... |

## Identified Gaps
[What recurring limitations appear? What's nobody working on?]
[Which important problems (from Hamming list) have no reasonable attack yet? What would create an opening?]

## Trend Analysis
[How has the approach distribution shifted over the survey period?]

## Proposed Research Directions
[Based on gaps and frontier, with supporting evidence]
[For each: apply the Significance Test — is it important? Is there a reasonable attack? Will it still matter in 48 months?]
[For each: can you write a formal problem statement? If not, the direction is not ready.]
[For each: state the One-Sentence insight]
[Explicit confidence assessment for each proposal]
```

### Phase 1 Evaluation

**The agent's output must meet the research guidelines' own standard.** Evaluate:

| Criterion | Method | Pass threshold |
|---|---|---|
| **Significance screening** | Agent evaluates 10 papers for significance (§2.2 tests). Compare against your Hamming-test assessment. | Correctly identifies papers that skip significance arguments. Does NOT over-assert importance (flags for human). |
| **Formalization detection** | Agent checks 10 papers for formal problem statements. Compare against your assessment. | Correctly identifies presence/absence of formal math in 80%+ of papers. Does NOT judge formalization quality (flags for human). |
| **Rubric discrimination** | Agent evaluates 10 papers you've already read. Compare agent scores to yours. | Agreement within ±1 on 70%+ of dimensions |
| **Bottleneck identification** | Agent does gap analysis on a subfield you know. Does it find the real bottlenecks? | Identifies at least 2 of 3 bottlenecks you'd identify |
| **Overclaiming detection** | Feed agent 5 papers with known overclaiming. Does it flag them? | Flags 3+ of 5 |
| **Honest uncertainty** | Does agent flag low-confidence assessments rather than confabulating? | ≥80% of significance/mathematical/novelty assessments flagged as needing human judgment |
| **Actionable output** | After reading report, do you know something you didn't? | Honest self-assessment |
| **Factual accuracy** | Spot-check 20 claims against paper contents. | ≥90% accurate |

**Expected failure modes:**
- Agent summarizes abstracts rather than analyzing deeply → Fix: more specific system prompt rubric instructions, possibly multi-pass (summarize first, then evaluate)
- Agent scores generously (doesn't flag weak baselines, insufficient trials) → Fix: calibrate with examples of papers at each score level in the system prompt
- Agent hallucinates connections between papers → Fix: require the agent to quote specific sections as evidence
- Agent applies rubric mechanically (checkbox evaluation without reasoning) → Fix: require written justification for each score, not just scores
- Agent misses papers due to narrow search queries → Fix: add citation graph traversal, multiple query reformulations
- Agent can't handle mathematical content from PDF extraction → Fix: flag papers with heavy math for human review, don't pretend to assess

### Phase 2: Complete Sub-State-Machines + Survey Mode (Weeks 3-5)

Phase 2 extends every sub-state-machine to its full specification and
enables the `survey` mode — the most complex and most valuable mode.

**Priority determined by Phase 1 failures**, but the expected build order:

**SM-1 completion (Search & Discovery):**
- [ ] Coverage assessment: check key_groups representation, approach
      category coverage, missing high-cited references
- [ ] Query expansion: generate reformulated queries targeting gaps
- [ ] Citation graph traversal: follow references of high-scoring
      papers (via S2 API `references` and `citations` endpoints)
- [ ] Author search: query recent papers by key researchers
- [ ] Convergence detection: stop when expansion adds <10% new papers

**SM-2 completion (Paper Processing):**
- [ ] ArXiv HTML fallback (ar5iv) for better math extraction
- [ ] S2 abstract-only fallback for papers behind paywalls
- [ ] Extraction quality scoring: math preservation heuristic,
      section completeness check, coherence check
- [ ] Quality flags propagated to evaluation (don't score dimensions
      that depend on badly-extracted sections)

**SM-3 completion (Evaluation):**
- [ ] Multi-pass evaluation: SKIM (fast model) → DEEP READ (full
      model) → EVALUATE → CROSS-CHECK against knowledge store
- [ ] Cross-checking: novelty vs. store, contradiction detection,
      method comparison on shared benchmarks
- [ ] Score revision triggered by cross-check findings
- [ ] Calibration: few-shot examples in system prompt for each score
      level (paper that scores 5 vs. 2 on experimental rigor)

**SM-4 completion (Knowledge Store):**
- [ ] Relation detection: extends/contradicts/supersedes/same_task/
      same_method between papers
- [ ] Topic clustering: auto-assign papers to topic clusters
- [ ] Frontier snapshots: store reliable/sometimes/can't-yet per
      domain per cycle, enable diff across cycles
- [ ] Evolution triggers: when a high-impact paper is ingested,
      flag related papers for potential re-assessment

**SM-5 completion (Report Generation):**
- [ ] Aggregation from knowledge store (not just current cycle)
- [ ] Clustering by approach type, task, and research group
- [ ] Cross-paper synthesis: gap identification, trend detection,
      contradiction flagging, convergence/divergence signals
- [ ] Consistency verification: synthesis claims supported by ≥2
      evaluations, confidence propagation
- [ ] Gap-triggered re-search: if synthesis reveals obvious gap,
      trigger SM-1 expansion before finalizing report

**SM-6: Survey mode orchestration:**
- [ ] Implement the SM-1→SM-2→SM-3→SM-4→SM-5→SM-1 loop with
      convergence detection
- [ ] Survey-specific report template with all sections (significance
      screening, formalization landscape, approach taxonomy, frontier,
      groups, gaps, trends, proposed directions)

**Additional Phase 2 work (from Phase 1 failure observations):**
- If analysis is shallow → refine system prompt rubric instructions,
  add structured evaluation steps
- If rubric calibration is off → add few-shot calibration examples
- If mathematical assessment is hopeless → accept limitation, focus
  agent on reliable dimensions, flag math-heavy papers for human
- If reports aren't actionable → restructure based on what the human
  actually reads. Cut unused sections. Expand useful ones.

### Phase 3: Remaining Modes + Cross-Cycle Intelligence (Weeks 6-8)

Contingent on Phase 2 producing useful survey output.

**Remaining modes:**
- [ ] `gap` mode: SM-4→SM-1→SM-3→SM-5 with failure-mode focus
- [ ] `frontier` mode: SM-4→SM-1→SM-3→SM-4→SM-5 with temporal diff
- [ ] `direction` mode: SM-4→SM-5→SM-1→SM-5 with significance prompts

**Cross-cycle intelligence (SM-4 evolution):**
- [ ] Automatic re-assessment triggers when new high-impact paper
      invalidates prior novelty/significance assessments
- [ ] Human feedback propagation: correcting one evaluation adjusts
      similar papers' scores
- [ ] Calibration drift detection: periodic re-score of calibration
      papers to detect scoring drift
- [ ] Trend detection across frontier snapshots: what moved between
      reliable/sometimes/can't-yet over multiple cycles?

**Multi-model pipeline:**
- [ ] Haiku for SM-3 SKIM pass (fast, cheap screening)
- [ ] Sonnet for SM-3 EVALUATE (standard analysis)
- [ ] Opus for SM-5 SYNTHESIZE (deep cross-paper synthesis)

### Phase 4: Interactive + Scheduled Modes (Contingent on Phase 1-3)

Only if the core cycle produces reliably useful output:

- **REPL mode** — interactive steering ("tell me more about the tactile
  sensing papers", "compare approaches X and Y", "what contradicts
  paper Z?"). Requires rich SM-4 relation graph.
- **Daemon mode** — scheduled daily/weekly cycles with auto-generated
  follow-up questions. Requires robust SM-4 evolution logic.
- **Comparative tables** — auto-generate method comparison tables
  across papers sharing a benchmark. Requires SM-4 same_task relations.

---

## Constitution (Revised)

```yaml
research:
  domain: "mobile manipulation systems"
  focus_areas:
    - "navigation and mapping (SLAM, visual nav, semantic mapping)"
    - "manipulation and grasping (dexterous, mobile manipulators, contact-rich)"
    - "perception (object detection, scene understanding, 3D vision, tactile)"
    - "planning (task planning, motion planning, TAMP, belief-space)"
    - "control (whole-body, compliant, impedance, force control)"
    - "policy learning (RL, imitation, sim-to-real, diffusion policies)"
    - "representations (affordances, foundation features, equivariant, 3D)"
    - "foundation models for robotics (VLAs, LLM-as-planner, VLM grounding)"
    - "long-horizon and compositional manipulation (skill composition, error recovery)"
    - "safety and robustness (safe exploration, CBFs, deployment reliability)"
  time_horizon: "last 6 months"
  key_groups:
    - "Berkeley (Levine, Abbeel, Goldberg)"
    - "Stanford (Finn, Bohg, Pavone)"
    - "MIT (Kaelbling, Lozano-Pérez, Agrawal, Kim)"
    - "CMU (Kroemer, Gupta)"
    - "Columbia/Stanford (Song)"
    - "NYU (Pinto)"
    - "UW (Fox)"
    - "TRI (Tedrake)"
    - "Google DeepMind (Zeng, Florence, Brohan)"
    - "Physical Intelligence (pi0 team)"

quality:
  min_relevance: 0.7
  evaluation_framework: "research_guidelines_appendix_b"
  rigor: "conference-level"

sources:
  primary:
    - arxiv
    - semantic_scholar
  arxiv_categories:
    - cs.RO
    - cs.AI
    - cs.CV
    - cs.LG
    - cs.SY

output:
  format: "markdown"
  include_rubric_scores: true
  include_confidence_flags: true
  include_citations: true
  include_code_links: true
  require_evidence_quotes: true

autonomy:
  max_papers_per_cycle: 20
  auto_follow_up: true
  checkpoint_frequency: "per_cycle"
  max_api_calls_per_cycle: 100

llm:
  model: "claude-sonnet-4-6"
  model_deep: "claude-opus-4-6"
```

---

## What Success Looks Like

**Minimum viable success:** The agent produces a weekly research digest that:
- Covers papers you would have missed (breadth > human)
- Evaluates them consistently against the rubric (structure > ad hoc reading)
- Flags genuinely interesting work with justified scores (signal > noise)
- Is honest about what it can and can't assess (trust > false confidence)

**Real success:** The agent produces landscape surveys and gap analyses that:
- Surface research directions you wouldn't have found from your reading alone
- Identify cross-subfield connections (e.g., a controls paper solving a learning problem's bottleneck)
- Track how the capability frontier is shifting over months
- Propose specific, testable hypotheses grounded in evidence
- Accelerate your problem selection (guideline §4.2) from 6 weeks to 2

**Failure:** The agent produces:
- Summaries achievable by reading abstracts (no depth beyond surface)
- Plausible-sounding analysis that's wrong (requires more verification effort than manual reading)
- Rubric scores that don't discriminate (everything gets 3/5)
- No actionable research directions (just restates known open problems)

---

## Risks and Honest Limitations

Per the guidelines: "Be honest about your evaluation distribution."

1. **LLM hallucination.** Agent may state that a paper does X when it does Y. Mitigation: require evidence quotes; human verifies flagged claims.
2. **Mathematical assessment ceiling.** The agent will not reliably evaluate theoretical depth. Mitigation: flag as low-confidence; the rubric separates this from dimensions the agent CAN assess.
3. **Novelty assessment requires field history.** The knowledge store accumulates over cycles but starts empty. First cycles will miss novelty; later cycles improve. Mitigation: seed with known landmark papers.
4. **PDF extraction quality.** Math, tables, figures are often mangled. Mitigation: flag content with extraction artifacts; use ArXiv HTML when available.
5. **Source limitations.** ArXiv/S2 don't cover all venues. Workshop papers, technical reports may be missed. Mitigation: accept this scope limitation explicitly.
6. **Cost.** Each cycle involves many API calls. Mitigation: monitor cost per cycle; use cheaper models for screening.
7. **The constitution is only as good as the human writes it.** Garbage in, garbage out. The constitution must be specific enough to be useful but flexible enough to not miss important tangential work.
8. **Calibration drift.** The rubric scoring may drift without regular human feedback. Mitigation: periodic calibration checks (agent re-scores papers the human has rated).

---

## How a Junior PhD Student Uses This (Step-by-Step)

This section translates the system into concrete, executable steps for someone who has never done a research literature review at this level.

### Step 0: Prerequisites (do once, before first run)

1. **Build your Hamming list.** Write down 10-20 important unsolved problems in mobile manipulation. Can't think of 10? Read the "Future Work" sections of the 20 most-cited papers in your area from the last 3 years. Ask your advisor. Ask senior students. This list is YOUR significance filter — the agent cannot do this for you.

2. **Set up your constitution.** Copy `constitution.yaml` and customize `focus_areas` and `key_groups` to YOUR specific research interests. Be specific — "deformable manipulation with tactile sensing" is better than "manipulation."

3. **Install and test.** `pip install -e .` then run `alpha-research run --question "What are the latest approaches to [your area]?" --mode digest` on a topic you already know well. This calibrates your expectations for what the agent can and cannot do.

### Step 1: Weekly Literature Screening (30 min/week)

**What you do:**
```bash
alpha-research run --question "New papers on [your topic] this week" --mode digest
```

**What the agent does:** Searches ArXiv, retrieves papers, applies the rubric, produces a scored report with significance flags and formalization checks.

**What YOU do with the output (this is the part that matters):**
1. Read the agent's significance screening. For papers it flags as "significance not argued," quickly check — is the problem actually on your Hamming list? If yes, the paper may still be important despite poor writing.
2. Read the agent's formalization check. Papers with formal problem statements are more likely to contain structural insights. Papers without formalization may still be useful but treat their claims more skeptically.
3. For papers scoring 4+ on the rubric: read the abstract and introduction yourself. Takes 5 min per paper. Decide: read fully, bookmark, or skip.
4. **Update your Hamming list** based on what you've seen. Are new problems becoming important? Are old ones being solved?

### Step 2: Monthly Deep Dive (half day/month)

**What you do:**
```bash
alpha-research run --question "Landscape survey of [your subfield]" --mode survey
```

**What YOU do with the output:**
1. Review the **Significance Screening** section. The agent flags papers that skip significance. But YOU must judge: which problems are actually important? Apply your Hamming list.
2. Review the **Problem Formalization Landscape**. How many papers in your area have formal problem definitions? If most don't, this is an opportunity — you can differentiate your work by formalizing the problem properly.
3. Review **Identified Gaps**. Cross-reference with your Hamming list. A gap that aligns with an important unsolved problem = a research opportunity.
4. For each **Proposed Research Direction** the agent suggests: apply the Significance Test yourself. Can YOU write a formal problem statement for it? If you can't, the direction isn't ready — either formalize it (that's research!) or move on.

### Step 3: Problem Selection (when starting a new project)

**What you do:**
```bash
alpha-research run --question "Gap analysis: [candidate problem area]" --mode gap
```

**Then, on your own (the agent CANNOT do this for you):**

1. **Significance Test** (§2.2): Apply the 8-point checklist. Write down your answers. Discuss with your advisor.
2. **Formal Problem Definition** (§2.4): Write the problem as math. Objective, variables, constraints, information structure. If you can't, you don't understand the problem yet — that's OK, but you need to get there before proposing a solution.
3. **One-Sentence Test**: State your potential contribution in one sentence that captures a structural insight. "We achieve SOTA on X" is not an insight. If you can't pass this test, your problem definition needs more work.
4. **Five-Axis Evaluation** (§5.1): Score your candidate on all five axes. Axis 0 (significance) gates everything — if it fails, stop.

### Step 4: Research Execution (ongoing)

During active research, use the agent for:
- **Deep Analysis** of papers related to your specific approach (know your baselines)
- **Trend Reports** to ensure you're not about to be scooped
- **Gap Analysis** when you hit a wall (maybe someone in a different sub-area has solved your bottleneck)

But always apply your own judgment on:
- Is the formalization right? (Tedrake test)
- Is this still important? (Hamming test)
- Can I state my contribution in one sentence? (One-Sentence test)
- Would my approach follow logically from my challenge analysis? (Challenge→Approach test)

### What "Executable" Means Here

Each step above specifies:
1. **What command to run** (literal CLI command)
2. **What the agent produces** (report with specific sections)
3. **What YOU do with it** (specific human actions, with time estimates)
4. **What decisions only YOU can make** (significance, formalization quality, taste)

The agent handles breadth and structure. You handle depth and judgment. Neither works alone.

---

## Implementation Checklist

### Phase 1 — Minimal end-to-end (`digest` + `deep` modes)

Data models + storage:
- [ ] `models.py` — all Pydantic models (Paper, ExtractionQuality, Evaluation, RubricScore, TaskChain, SignificanceAssessment, SearchState)
- [ ] `config.py` + `constitution.yaml` (Pydantic models, YAML loading, validation)
- [ ] `knowledge/schema.py` — SQLite schema (papers, evaluations, findings, questions, feedback)
- [ ] `knowledge/store.py` — basic CRUD (insert/query papers, evaluations)

SM-2 (Paper Processing, forward path):
- [ ] `tools/paper_fetch.py` — ArXiv PDF download + pymupdf extraction + extraction quality validation

SM-1 (Search, single query):
- [ ] `tools/arxiv_search.py` — keyword + category + date range search
- [ ] `tools/semantic_scholar.py` — paper metadata query (citations, venue, TLDR)

SM-3 (Evaluation, SKIM + EVALUATE):
- [ ] `prompts/rubric.py` — Appendix B rubric as structured prompt with §2.2 significance tests and §2.4 formalization checks
- [ ] `prompts/system.py` — constitution + rubric + honesty protocol → system prompt **← hardest step, iterate**

SM-4 (Knowledge Store, basic):
- [ ] `tools/knowledge.py` — agent read/write interface (save paper + evaluation, query by topic/score/date)

SM-5 (Report, FORMAT only):
- [ ] `tools/report.py` — structured markdown from evaluations, per-mode templates

Agent + CLI:
- [ ] `agent.py` — Agent SDK agent with tools registered, tool descriptions
- [ ] `main.py` — typer CLI: `run --question "..." --mode [digest|deep]`

Validation:
- [ ] End-to-end test: `digest` on known topic, verify report structure
- [ ] End-to-end test: `deep` on paper you've read, compare evaluation
- [ ] Calibration test: evaluate 10 papers, compare agent vs. human scores
- [ ] Iterate system prompt based on calibration results

### Phase 2 — Complete sub-state-machines + `survey` mode

(Checklist items listed in Phase 2 section above)

### Phase 3 — Remaining modes + cross-cycle intelligence

(Checklist items listed in Phase 3 section above)
