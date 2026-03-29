# Review Agent — Implementation Plan

Companion to `review_guideline.md` (what the agent enforces) and `work_plan.md` (the research agent it critiques). This document specifies: (1) executable, quantifiable metrics for every review item; (2) optimal agent architecture; (3) the iterative research–review interaction protocol.

---

## Part I. Executable Metrics for Every Review Item

Each attack vector in `review_guideline.md` (Part III) must produce a **machine-evaluable signal** — a binary check, a numeric score, or a structured extraction that can be programmatically verified. Vague assessments ("novelty seems low") are not acceptable outputs. This section maps every review item to a concrete, quantifiable metric.

### 1.1 Logical Chain Completeness (review_guideline.md §2.1, §2.2)

The review agent's first task is extracting the logical chain. This is the foundation — everything else depends on it.

| Chain Link | Extraction Target | Metric | Threshold |
|---|---|---|---|
| **Task** | One sentence: what the robot does physically | `task_extracted: bool` — can the agent produce this sentence? | Must be extractable. If not → clarity failure. |
| **Problem** | Formal statement: objective, variables, constraints, information structure | `formalization_level: enum{formal_math, semi_formal, prose_only, absent}` | `formal_math` or `semi_formal` required for IJRR/T-RO/RSS. `prose_only` = serious weakness. `absent` = fatal at top venues. |
| **Challenge** | One sentence: the structural barrier | `challenge_type: enum{structural, resource_complaint, absent}` | Must be `structural`. `resource_complaint` = serious weakness (§3.3). |
| **Approach** | One sentence: the structural insight exploited | `approach_follows_from_challenge: bool` — does the approach logically derive from the challenge? | Must be `true`. If `false` → structural disconnect (§3.4). |
| **Contribution** | One sentence: the insight (not "we achieve SOTA on X") | `one_sentence_test: enum{insight, performance_claim, absent}` | Must be `insight`. `performance_claim` = weak contribution. `absent` = fatal. |
| **Chain coherence** | Do all links connect? Does approach follow from challenge follow from problem? | `chain_coherent: bool` + `broken_links: list[str]` | All links must connect. Each broken link maps to a backward transition trigger. |

**Quantification:** The chain extraction produces a `TaskChain` object (defined in `work_plan.md` SM-3). Chain completeness = number of non-null fields / 5. Chain coherence is a separate boolean. A paper with completeness < 0.6 (3+ missing links) has a fatal structural flaw.

### 1.2 Significance Metrics (review_guideline.md §3.1)

| Attack Vector | Metric | How to Measure | Threshold |
|---|---|---|---|
| **Hamming failure** | `hamming_score: int{1-5}` | Agent attempts to independently articulate why this problem matters. Score: 5 = compelling independent argument; 3 = paper's argument accepted but not independently reconstructable; 1 = cannot articulate importance. | ≥ 3 to proceed. < 3 = serious weakness. **Low-confidence assessment — flag for human.** |
| **Consequence failure** | `concrete_consequence: str \| null` | Agent extracts or constructs a concrete downstream consequence. Null if only vague claims ("advances the field"). | Must be non-null and specific (names a system, capability, or understanding that changes). |
| **Durability failure** | `durability_risk: enum{low, medium, high}` | Does a 10x bigger model / 10x more data / better hardware plausibly solve this? `high` = scaling will solve it within 24 months. | `high` = serious weakness. |
| **Compounding failure** | `compounding_value: enum{high, medium, low}` | Does solving this enable other research? `high` = framework/representation/infrastructure others build on. `low` = task-specific, dead-end. | `low` = note, not fatal by itself. |
| **Goal vs. idea driven** | `motivation_type: enum{goal_driven, idea_driven, unclear}` | Does the paper start from a problem or from a method? Detected by: does the introduction lead with the task/problem or with the method? | `idea_driven` = serious weakness at RSS/CoRL. Flag for human. |
| **Concurrent work** | `concurrent_coverage: bool` | Does the paper cite and compare against the most recent relevant work (within 12 months)? | `false` = serious weakness. Agent should search for missing concurrent work. |

### 1.3 Formalization Metrics (review_guideline.md §3.2)

| Attack Vector | Metric | How to Measure | Threshold |
|---|---|---|---|
| **Absent formalization** | `formalization_level` (from §1.1) | Detect presence of mathematical notation in problem statement: objective function, variables, constraints. | See §1.1 thresholds. |
| **Wrong framework** | `framework_mismatch: list[str]` | Agent checks: does the framework match the problem? (MDP for partially observable → mismatch. Deterministic for stochastic → mismatch.) | Any mismatch = serious weakness. **Moderate-confidence.** |
| **Missing structure** | `structure_exploited: list[str]` | Extract claimed structures (convexity, symmetry, decomposability, sparsity). Empty list when formalization exists = missed opportunity / dressing up. | Empty list with formalization present = weakness. |
| **Trivial special case** | `reduces_to_known: str \| null` | Agent checks: does this reduce to a well-known problem? If so, name it. | Non-null = fatal flaw (trigger t2). **Low-confidence — flag for human.** |
| **Assumption audit** | `assumptions_explicit: bool`, `assumptions_count: int` | Are assumptions stated? How many? | `false` = serious weakness. Low count for complex methods = suspicious. |
| **Formalization-reality gap** | `formal_impl_gap: enum{none, minor, major}` | Does the implemented loss/reward match the formal objective? | `major` = serious weakness. |

### 1.4 Challenge Metrics (review_guideline.md §3.3)

| Attack Vector | Metric | How to Measure | Threshold |
|---|---|---|---|
| **Resource complaint** | `challenge_type` (from §1.1) | Is the challenge "need more X" or a structural barrier? | `resource_complaint` = serious weakness. |
| **Challenge-approach disconnect** | `challenge_constrains_solution: bool` | Given only the challenge statement, can the agent predict the method *class* (not the specific method)? | `false` = structural disconnect. Serious weakness or fatal depending on severity. |
| **Challenge misidentification** | `evidence_supports_challenge: enum{strong, weak, contradicted}` | Do the paper's own experiments support the claimed challenge? (e.g., if "sample complexity" is the challenge but 100 demos suffice → contradicted.) | `contradicted` = fatal. `weak` = serious weakness. |
| **Pre-solved challenge** | `prior_solution_exists: str \| null` | Agent searches for prior work that addresses the same structural barrier. | Non-null and unacknowledged = fatal. Non-null but acknowledged and differentiated = ok. |
| **Depth test** | `challenge_specificity: enum{constrains_class, vague, absent}` | Could any method claim to address this challenge? Or does it narrow to a specific family? | `vague` = serious weakness. `absent` = fatal. |

### 1.5 Approach Metrics (review_guideline.md §3.4)

| Attack Vector | Metric | How to Measure | Threshold |
|---|---|---|---|
| **Method-shopping** | `method_interchangeable: bool` | Could you swap this method for another trending method and the paper reads the same? | `true` = serious weakness. |
| **Trivial variant** | `nearest_prior_method: str`, `structural_delta: str \| null` | Name the closest prior method and the structural difference (not just application difference). Null delta = trivial variant. | Null `structural_delta` = fatal (trigger t5). |
| **Structure exploitation** | `uses_identified_structure: bool` | Does the approach actually use the mathematical structure the formalization revealed? | `false` = disconnect between formalization and approach. Serious weakness. |
| **Wrong mechanism** | `ablation_supports_claim: enum{yes, no, not_tested}` | Does removing the claimed contribution degrade performance? | `no` = fatal (trigger t15). `not_tested` = serious weakness. |

### 1.6 Validation Metrics (review_guideline.md §3.5)

#### 1.6.1 Experimental Design

| Attack Vector | Metric | How to Measure | Threshold (by venue) |
|---|---|---|---|
| **Baseline strength** | `baselines: list[str]`, `includes_simple: bool`, `includes_oracle: bool`, `includes_sota: bool` | Extract all baselines. Check for simple/scripted, oracle (perfect perception/dynamics), and strongest known prior. | Missing SOTA = serious. Missing simple = weakness. Missing oracle = note. |
| **Missing baseline** | `strongest_missing_baseline: str \| null` | Agent proposes the single most important missing comparison. | Non-null = serious weakness (degree depends on how damaging the omission is). |
| **Ablation isolation** | `ablation_isolates_contribution: enum{yes, partial, no, absent}` | Does removing the paper's claimed innovation show performance drop? | `absent` = serious weakness. `no` = fatal (trigger t15). |
| **Statistical sufficiency** | `trials_per_condition: int`, `has_confidence_intervals: bool`, `has_seeds: bool` | Count trials from experimental tables. Check for CI/std reporting. | IJRR/T-RO/RSS: ≥20, CI required. CoRL: ≥10, CI expected. ICRA/IROS: ≥10 preferred. <10 at any venue = serious. <5 = fatal. |
| **Evaluation-claim alignment** | `experiments_test_claim: enum{direct, indirect, misaligned}` | Do the experiments directly test the paper's stated contribution? | `misaligned` = fatal. `indirect` = serious weakness. |
| **Cherry-picking** | `failure_cases_shown: bool`, `failure_taxonomy: bool` | Are failures shown? Is there a systematic failure analysis? | `false` for both = serious weakness. |
| **Human effort** | `human_effort_reported: bool`, `demo_count: int \| null`, `calibration_reported: bool` | Is human effort (demos, calibration, tuning, resets) quantified? | `false` = serious weakness. |

#### 1.6.2 Robotics-Specific

| Attack Vector | Metric | Threshold |
|---|---|---|
| **Sim-only for real claims** | `validation_type: enum{real_robot, sim_and_real, sim_only}` | `sim_only` for manipulation/contact = serious weakness (fatal at IJRR/CoRL). |
| **Single-embodiment generality** | `robot_count: int`, `claims_generality: bool` | `robot_count == 1` AND `claims_generality == true` = overclaim. Serious weakness. |
| **Contact gap** | `contact_modeled: bool` (for contact-rich tasks) | `false` for contact-rich task = serious weakness. |
| **Sensing mismatch** | `sensing_appropriate: enum{appropriate, questionable, mismatched}` | `mismatched` = serious weakness. |
| **Environment simplification** | `environment_complexity: enum{real_world, semi_controlled, fully_controlled}` | `fully_controlled` with real-world generality claims = overclaim. |
| **Failure severity** | `severity_reported: bool` | `false` = weakness. |
| **Reproducibility** | `reproducibility_score: int{1-5}` — hardware described, code released, setup documented, URDF/calibration provided, data available. One point each. | < 3 = weakness. < 2 = serious weakness. |
| **Cycle time** | `cycle_time_reported: bool`, `real_time_capable: enum{yes, no, unclear}` | Not reported = weakness. Not real-time without acknowledgment = serious weakness. |

#### 1.6.3 Overclaiming Detection

| Pattern | Metric | Detection Rule |
|---|---|---|
| **Generality overclaim** | `claim_scope: str`, `test_scope: str` | If `claim_scope` is broader than `test_scope` by >1 level (e.g., "manipulation" claimed, 3 objects tested) → overclaim. |
| **Novelty overclaim** | `novelty_claim: str`, `actual_delta: str` | If `actual_delta` is "application to new domain" but `novelty_claim` is "novel framework" → overclaim. |
| **Comparison overclaim** | `claimed_superiority: str`, `tested_metrics: list[str]` | If paper claims "outperforms all" but only tests on subset of relevant metrics → overclaim. |

### 1.7 Novelty Metrics (review_guideline.md §3.6)

| Attack Vector | Metric | Threshold |
|---|---|---|
| **Prior work overlap** | `closest_prior: str`, `differentiation: str \| null` | Null differentiation = fatal. |
| **Incremental engineering** | `contribution_type: enum{structural_insight, incremental_engineering, application}` | `incremental_engineering` = serious weakness at RSS/CoRL/IJRR. May be acceptable at ICRA/IROS. |
| **Missing related work** | `missing_refs: list[str]` | Agent searches for papers the authors should have cited. ≥3 highly relevant missing = serious weakness. |

### 1.8 Review Quality Metrics (Meta-Review)

The review itself must be measurable. Based on the RevUtil framework (EMNLP 2025):

| Dimension | Metric | How to Measure | Target |
|---|---|---|---|
| **Actionability** | `actionable_points: int` | Count critiques with concrete "what would fix it" recommendations. | ≥ 80% of all critiques must be actionable. |
| **Grounding** | `grounded_points: int` | Count critiques that reference specific sections/figures/tables/equations. | ≥ 90% of serious+ critiques must be grounded. |
| **Specificity** | `vague_critiques: int` | Count critiques that are vague ("novelty is limited," "evaluation is weak"). | Must be 0. All vague critiques are rewritten to be specific. |
| **Falsifiability** | `falsifiable_points: int` | Count critiques with explicit falsification conditions. | ≥ 70% of serious+ critiques must be falsifiable. |
| **Steel-man quality** | `steel_man_length: int` (sentences) | Is the steel-man substantive? | ≥ 3 sentences. Must mention something non-obvious. |
| **Classification consistency** | `fatal_count + serious_count + minor_count == total_findings` | All findings classified. No unclassified findings. | 100% classified. |

### 1.9 Verdict Metrics

The final verdict must be derived mechanically from the findings, not from gestalt:

```python
def compute_verdict(findings: list[Finding], venue: Venue) -> Verdict:
    fatal = [f for f in findings if f.severity == "fatal"]
    serious = [f for f in findings if f.severity == "serious"]
    significance_score = extract_significance_score(findings)

    # Rule 1: Any fatal flaw → Reject
    if fatal:
        return Verdict.REJECT

    # Rule 2: Gate dimension
    if significance_score <= 2:
        return Verdict.REJECT

    # Rule 3: Serious weakness accumulation
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

---

## Part II. Agent Architecture

### 2.1 Multi-Agent Topology

The system uses a **centralized orchestrator with specialized sub-agents** — a layered topology where the orchestrator routes work and maintains shared state, and sub-agents are stateless specialists.

This choice is informed by: (1) the blackboard pattern for iterative review loops (shared state between research and review agents); (2) component-wise refinement being more stable than global optimization (IMPROVE framework); (3) Claude Agent SDK's native subagent support.

```
                          ┌─────────────────────────┐
                          │      ORCHESTRATOR        │
                          │                          │
                          │  Owns: shared blackboard │
                          │  Owns: convergence logic │
                          │  Owns: human checkpoint  │
                          │         routing          │
                          └────────┬────────────────┘
                                   │
               ┌───────────────────┼───────────────────┐
               │                   │                   │
        ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
        │  RESEARCH   │    │   REVIEW    │    │    META-    │
        │   AGENT     │    │   AGENT     │    │  REVIEWER   │
        │             │    │             │    │             │
        │ Produces    │    │ Attacks per │    │ Evaluates   │
        │ research    │    │ review_     │    │ review      │
        │ artifacts   │    │ guideline   │    │ quality     │
        │ per work_   │    │             │    │ per §1.8    │
        │ plan + res. │    │             │    │ metrics     │
        │ guideline   │    │             │    │             │
        └─────────────┘    └─────────────┘    └─────────────┘
```

**Why three agents, not two:**
- The **meta-reviewer** prevents mode collapse between research and review agents. If the review agent produces vague or toothless critiques, the meta-reviewer catches it. If the review agent is unfairly harsh, the meta-reviewer catches that too.
- This mirrors the area chair role at RSS/NeurIPS — someone who reviews the reviews.
- The meta-reviewer applies the review quality metrics from §1.8 and can send the review back for revision before it reaches the research agent.

### 2.2 The Shared Blackboard

All agents read from and write to a shared state object. This is the "blackboard" — a structured document that evolves through the review cycle.

```python
class Blackboard(BaseModel):
    """Shared state between research and review agents.
    Persisted to disk between iterations. The single source of truth."""

    # Research artifact (written by research agent)
    artifact: ResearchArtifact          # The current paper/proposal/analysis
    artifact_version: int               # Increments on each revision
    artifact_history: list[ArtifactDiff]  # What changed per version

    # Review state (written by review agent)
    current_review: Review | None       # Latest review
    review_history: list[Review]        # All prior reviews

    # Meta-review state (written by meta-reviewer)
    review_quality: ReviewQualityReport | None

    # Convergence tracking (written by orchestrator)
    iteration: int
    convergence_state: ConvergenceState

    # Human checkpoints (written by human)
    human_decisions: list[HumanDecision]

    # Configuration
    target_venue: Venue
    review_mode: Literal["full", "focused", "quick"]

class ResearchArtifact(BaseModel):
    """What the research agent produces. Could be a paper draft,
    a significance argument, a formalization, etc."""
    stage: Literal["significance", "formalization", "challenge",
                   "approach", "validation", "full_draft"]
    content: str                        # Markdown content
    task_chain: TaskChain               # Current logical chain
    metadata: dict                      # Stage-specific metadata

class Review(BaseModel):
    """Structured review output per review_guideline.md §2.2."""
    version: int                        # Which artifact version was reviewed
    summary: str
    chain_extraction: TaskChain
    steel_man: str
    fatal_flaws: list[Finding]
    serious_weaknesses: list[Finding]
    minor_issues: list[Finding]
    questions: list[str]
    verdict: Verdict
    confidence: int                     # 1-5
    improvement_path: str               # "What would increase your score?"

    # Meta-metrics (computed, not written by review agent)
    quality_metrics: ReviewQualityMetrics | None

class Finding(BaseModel):
    """A single review finding — the atomic unit of critique."""
    severity: Literal["fatal", "serious", "minor"]
    attack_vector: str                  # Which attack vector (§3.1-3.6)
    what_is_wrong: str                  # The specific gap
    why_it_matters: str                 # Consequence for claims
    what_would_fix: str                 # Actionable recommendation
    falsification: str                  # What would invalidate this critique
    grounding: str                      # Specific section/figure/table
    fixable: bool                       # Can this be addressed in revision?
    maps_to_trigger: str | None         # Which backward trigger (t2-t15)
```

### 2.3 Agent Specifications

#### Research Agent

- **System prompt source:** `research_guideline.md` (full) + `work_plan.md` (state machine, evaluation rubric)
- **Tools:** `arxiv_search`, `paper_fetch`, `semantic_scholar`, `knowledge_read`, `knowledge_write`, `report` (from `work_plan.md` architecture)
- **Input:** Blackboard (reads previous review findings to address)
- **Output:** Updated `ResearchArtifact` on the blackboard
- **Key behavior:** When receiving a review, the agent maps each finding to a backward transition trigger. Fatal flaws trigger backward transitions in the state machine. Serious weaknesses are addressed within the current stage. The agent must explicitly state which findings it addressed and how.

#### Review Agent

- **System prompt source:** `review_guideline.md` (full) — the attack vectors, protocol, rubric, venue calibration
- **Tools:** `arxiv_search`, `semantic_scholar`, `knowledge_read` (for searching prior work to check novelty claims), `paper_fetch` (to read papers cited by the artifact)
- **Input:** Blackboard (reads current research artifact)
- **Output:** Updated `Review` on the blackboard
- **Key behaviors:**
  - Three-pass protocol (`review_guideline.md` §2.1): structural comprehension → technical attack → evidence audit
  - Produces findings with full structure (what/why/fix/falsification/grounding)
  - Classifies all findings into fatal/serious/minor hierarchy
  - Applies venue-specific calibration (`review_guideline.md` §4.2)
  - On re-review: focuses on whether previous findings were addressed, checks for regression (new weaknesses introduced by fixes), and provides a **pairwise comparison** — explicit diff between current and previous version quality

#### Meta-Reviewer

- **System prompt source:** `review_guideline.md` §1.8 (review quality metrics) + §5.4 (anti-patterns)
- **Tools:** None (operates only on blackboard content)
- **Input:** Current review + review history
- **Output:** `ReviewQualityReport` with pass/fail + specific issues
- **Key behaviors:**
  - Checks all §1.8 metrics: actionability ≥ 80%, grounding ≥ 90%, zero vague critiques, falsifiability ≥ 70%
  - Checks for anti-patterns (`review_guideline.md` §5.4): dimension averaging, false balance, novelty fetishism, recency bias, blanket rejection, punishing honest limitations
  - If review fails quality checks → sent back to review agent for revision BEFORE it reaches the research agent
  - Prevents mode collapse: if reviews become progressively weaker (less specific, fewer findings) across iterations, flags this as convergence-to-mediocrity

### 2.4 The Iteration Protocol

```
ORCHESTRATOR MAIN LOOP
═══════════════════════════════════════════════════

iteration = 0
while not converged(blackboard):
    iteration += 1

    ┌─── PHASE 1: RESEARCH ────────────────────────┐
    │                                               │
    │  if iteration == 1:                           │
    │    research_agent.generate(blackboard)         │
    │  else:                                        │
    │    research_agent.revise(blackboard,           │
    │      focus=previous_review.findings)           │
    │                                               │
    │  blackboard.artifact_version += 1             │
    └───────────────────────────────────────────────┘
                        │
                        ▼
    ┌─── PHASE 2: REVIEW ──────────────────────────┐
    │                                               │
    │  review = review_agent.review(blackboard)     │
    │                                               │
    │  ┌── PHASE 2a: META-REVIEW ───────────────┐  │
    │  │                                         │  │
    │  │  quality = meta_reviewer.check(review)  │  │
    │  │  if not quality.passes:                 │  │
    │  │    review = review_agent.revise_review( │  │
    │  │      review, quality.issues)            │  │
    │  │    (max 2 meta-review rounds)           │  │
    │  │                                         │  │
    │  └─────────────────────────────────────────┘  │
    │                                               │
    │  blackboard.current_review = review           │
    │  blackboard.review_history.append(review)     │
    └───────────────────────────────────────────────┘
                        │
                        ▼
    ┌─── PHASE 3: HUMAN CHECKPOINT ────────────────┐
    │  (conditional — not every iteration)          │
    │                                               │
    │  Trigger human checkpoint when:               │
    │  - Review contains ≥1 finding marked          │
    │    "low-confidence" on significance or         │
    │    formalization quality                       │
    │  - Research agent triggers a backward          │
    │    transition to SIGNIFICANCE (expensive)      │
    │  - iteration ≥ max_iterations - 1             │
    │  - Review verdict is ACCEPT (final check)     │
    │                                               │
    │  Human can:                                   │
    │  - Override any finding (upgrade/downgrade)    │
    │  - Add findings the agents missed              │
    │  - Approve convergence                         │
    │  - Force additional iteration                  │
    └───────────────────────────────────────────────┘
                        │
                        ▼
    ┌─── PHASE 4: CONVERGENCE CHECK ───────────────┐
    │                                               │
    │  converged = check_convergence(blackboard)    │
    │  (see §2.5 for convergence criteria)          │
    │                                               │
    └───────────────────────────────────────────────┘
```

### 2.5 Convergence Criteria

The loop must terminate. Four independent stopping conditions (from AWS Evaluator-Reflect-Refine, validated by the multi-agent literature showing 3-5 iterations typical):

**Condition 1: Quality Threshold Met**
```python
def quality_met(review: Review) -> bool:
    return (
        len(review.fatal_flaws) == 0 and
        len(review.serious_weaknesses) <= 1 and
        all(w.fixable for w in review.serious_weaknesses) and
        review.verdict in [Verdict.ACCEPT, Verdict.WEAK_ACCEPT]
    )
```

**Condition 2: Human Approval**
Human explicitly approves the current state ("good enough, submit").

**Condition 3: Iteration Limit**
Hard cap at 5 iterations. If not converged by iteration 5, the orchestrator produces a final status report summarizing remaining issues and asks the human for a decision.

**Rationale for 5:** Multi-agent debate literature shows 94.2% convergence within 5 iterations. Self-Refine shows diminishing returns after 2-3. MART red-teaming converges in 4 rounds. 5 is a safe upper bound.

**Condition 4: Stagnation Detection**
```python
def stagnated(blackboard: Blackboard) -> bool:
    if len(blackboard.review_history) < 2:
        return False
    prev = blackboard.review_history[-2]
    curr = blackboard.review_history[-1]
    # Same findings, same severity, same verdict
    return (
        set_of_attack_vectors(prev) == set_of_attack_vectors(curr) and
        prev.verdict == curr.verdict
    )
```

If stagnated (same findings persist after revision), the orchestrator either escalates to human or stops — the research agent cannot fix these issues without external input.

### 2.6 Graduated Adversarial Pressure

Inspired by MART (Multi-round Automatic Red-Teaming), the review agent should increase its scrutiny across iterations, not start at maximum:

| Iteration | Review Depth | Attack Focus | Rationale |
|---|---|---|---|
| 1 | **Structural scan** | Chain completeness, significance gate, formalization presence. Quick-reference checklist only (`review_guideline.md` Appendix A.1). | Catch fatal structural flaws before investing in detailed analysis. |
| 2 | **Full review** | All attack vectors from §3.1-3.6. Complete three-pass protocol. | The core adversarial review. |
| 3 | **Focused re-review** | Only the findings from iteration 2 that the research agent claimed to address. Plus: regression check — did fixes introduce new weaknesses? | Verification pass. |
| 4+ | **Residual scan** | Only unresolved findings. Pairwise comparison of current vs. previous version. | Diminishing returns — focus narrowly. |

### 2.7 Anti-Collapse Mechanisms

The literature identifies mode collapse as the primary risk when generator and critic are the same model. Mitigations:

1. **The meta-reviewer** is the structural defense. It measures review quality independently and rejects declining reviews.

2. **Quantified findings vs. gestalt.** The review agent must produce `Finding` objects with all fields filled, not prose reviews. This forces specificity and prevents drift toward vague acceptance.

3. **Monotonic severity rule.** A finding classified as "fatal" or "serious" in iteration N cannot be downgraded in iteration N+1 unless the research agent provides specific evidence addressing it. The review agent must explicitly justify any downgrade.

4. **Cross-iteration tracking.** The orchestrator tracks `finding_resolution_rate` — the fraction of previous findings marked as addressed. If this drops below 50% (the research agent is ignoring findings rather than addressing them), the orchestrator flags this.

5. **Fresh-eyes pass.** On the final iteration, the review agent re-reviews from scratch (not incrementally), without seeing its own prior reviews. This catches issues that were masked by iterative tunnel vision.

---

## Part III. Iterative Research–Review Interaction

### 3.1 What Gets Reviewed (Artifact Types)

The review agent doesn't only review full paper drafts. It reviews artifacts at every stage of the research state machine (`work_plan.md` §top):

| Research Stage | Artifact | Review Focus | Primary Attack Vectors |
|---|---|---|---|
| **SIGNIFICANCE** | Significance argument: why this problem matters | §3.1 only. Is this worth working on? | Hamming, Consequence, Durability, Compounding |
| **FORMALIZE** | Formal problem definition with math | §3.1 + §3.2. Is the formalization sound? Does it reveal structure? | Absent formalization, wrong framework, missing structure, trivial special case |
| **DIAGNOSE** | Failure analysis of minimal system | §3.3. Is the failure diagnosis specific and mapped to formalization? | Resource complaint, challenge-approach disconnect |
| **CHALLENGE** | Challenge statement: the structural barrier | §3.3 + §3.4 (partial). Does the challenge constrain the solution class? | All §3.3 vectors |
| **APPROACH** | Method description with justification | §3.4. Does the approach follow from the challenge? | All §3.4 vectors |
| **VALIDATE** | Experimental results + analysis | §3.5 + §3.6. Does the evidence support the claims? | All §3.5 + §3.6 vectors |
| **full_draft** | Complete paper | ALL attack vectors. Full three-pass protocol. | Everything |

**Why stage-level review matters:** Catching a significance failure at the SIGNIFICANCE stage saves months of wasted work on formalization, approach, and experiments. The earlier a flaw is caught, the cheaper the fix. This maps directly to the research guideline's principle: "backward transitions to SIGNIFICANCE are the most expensive... but also the most important to recognize early."

### 3.2 The Response Protocol

When the research agent receives a review, it must produce a structured response — not just a revised artifact:

```python
class RevisionResponse(BaseModel):
    """Research agent's response to a review.
    Explicit mapping from findings to actions."""

    addressed: list[FindingResponse]
    deferred: list[FindingDeferral]
    disputed: list[FindingDispute]

class FindingResponse(BaseModel):
    finding_id: str
    action_taken: str           # What was changed
    evidence: str               # Where in the artifact the change is

class FindingDeferral(BaseModel):
    finding_id: str
    reason: str                 # Why this is deferred (e.g., needs experiments)
    plan: str                   # When/how it will be addressed

class FindingDispute(BaseModel):
    finding_id: str
    argument: str               # Why the finding is incorrect
    evidence: str               # Supporting evidence for the dispute
```

The review agent must then evaluate each response:
- **Addressed findings:** Check if the fix is adequate. Check for regression.
- **Deferred findings:** Accept if the deferral reason is valid and the plan is concrete. Track for follow-up.
- **Disputed findings:** Re-evaluate the finding in light of the dispute. May upgrade, downgrade, or maintain.

This structured interaction prevents the common failure mode where the research agent makes superficial changes that don't actually address the critique.

### 3.3 Backward Transition Protocol

When a review finding maps to a backward transition trigger in the research state machine (`work_plan.md` §top), the interaction follows a specific protocol:

```
Review Agent finds: "This formalization reduces to standard POMDP
that DESPOT solves" → maps to trigger t2 (FORMALIZE → SIGNIFICANCE)

Orchestrator:
  1. Classify the transition: FORMALIZE → SIGNIFICANCE (expensive)
  2. Trigger human checkpoint (backward to SIGNIFICANCE always
     requires human approval)
  3. If human approves backward transition:
     - Research agent re-enters SIGNIFICANCE stage with constraint:
       "previous formalization reduced to known POMDP; next problem
       must not be a trivial special case"
     - Review agent resets: next review is a SIGNIFICANCE-stage review
  4. If human overrides (the finding is wrong):
     - Research agent provides evidence for why it's not a trivial case
     - Review agent re-evaluates
```

**Critical principle:** The review agent proposes backward transitions but does not execute them. The orchestrator + human decide whether to accept them. This prevents the review agent from being destructively conservative.

### 3.4 Pairwise Comparison Mode

On re-review (iterations 2+), the review agent applies a **pairwise comparison** (inspired by aiXiv's "Pairwise Review" mode):

```
PAIRWISE REVIEW TEMPLATE
═══════════════════════════════════════════════════

For each finding from the previous review:

FINDING: [previous finding text]
STATUS: [addressed | partially_addressed | not_addressed | regressed]

If ADDRESSED:
  - What changed: [specific diff in the artifact]
  - Is the fix adequate? [yes/no + reasoning]
  - Did the fix introduce new weaknesses? [yes/no + details]

If NOT_ADDRESSED:
  - Was there a dispute? [yes/no]
  - If disputed, is the dispute valid? [reasoning]
  - If no dispute, why wasn't this addressed? [flag for orchestrator]

NEW FINDINGS (not in previous review):
  - [Any new weaknesses introduced by revisions]
  - [Any new weaknesses discovered on deeper reading]

DELTA SUMMARY:
  - Previous verdict: [X] → Current verdict: [Y]
  - Findings resolved: N/M
  - New findings: K
  - Net improvement: [better | same | worse]
```

### 3.5 The Full Interaction Timeline

For a full research cycle (SIGNIFICANCE through VALIDATE), the interaction looks like:

```
                    Research Agent         Review Agent          Human
                         │                     │                  │
SIGNIFICANCE stage:      │                     │                  │
  Produce significance   │────────►            │                  │
  argument               │         Review §3.1  │                  │
                         │    ◄────────────────│                  │
  If fatal: pivot        │                     │                  │
  If ok: proceed         │                     │                  │
                         │                     │            ◄─────│ checkpoint:
                         │                     │              approve topic
FORMALIZE stage:         │                     │                  │
  Produce formalization  │────────►            │                  │
                         │         Review §3.2  │                  │
                         │    ◄────────────────│                  │
  If t2/t7: backward     │                     │            ◄─────│ approve/deny
  Iterate formalization  │────────►            │                  │ backward
                         │    ◄────────────────│                  │
                         │                     │                  │
  ... (DIAGNOSE, CHALLENGE, APPROACH similar pattern) ...        │
                         │                     │                  │
VALIDATE (full draft):   │                     │                  │
  Produce full draft     │────────►            │                  │
                         │         Full review  │                  │
                         │    ◄────────────────│                  │
                         │         Meta-review  │                  │
  Revise                 │────────►            │                  │
                         │         Re-review    │                  │
                         │    ◄────────────────│                  │
  ... (max 5 iterations at full-draft stage) ...                 │
                         │                     │            ◄─────│ final
  CONVERGED              │                     │              approval
```

### 3.6 Interaction Data Model Summary

The complete data flow ties together the models from `work_plan.md` and this plan:

```
work_plan.md models          review_plan.md models
════════════════             ═════════════════════
Paper ─────────────┐
Evaluation ────────┤
TaskChain ─────────┤         Blackboard
SearchState ───────┤◄───────►  ├─ ResearchArtifact
RubricScore ───────┤           ├─ Review
                   │           │   ├─ Finding (per §1.1-1.7 metrics)
                   │           │   └─ ReviewQualityMetrics (§1.8)
                   │           ├─ RevisionResponse
                   │           └─ ConvergenceState
                   │
knowledge.db ◄─────┘         Both agents read/write knowledge.db
(work_plan.md SM-4)          via knowledge_read/knowledge_write tools
```

---

## Part IV. Implementation Architecture

### 4.1 Package Structure Extension

The review agent extends the project structure from `work_plan.md`:

```
alpha_research/
├── src/alpha_research/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── orchestrator.py      # Main loop, convergence, routing
│   │   ├── research_agent.py    # Research agent (work_plan.md)
│   │   ├── review_agent.py      # Review agent (review_guideline.md)
│   │   └── meta_reviewer.py     # Review quality checker
│   ├── models/
│   │   ├── __init__.py
│   │   ├── research.py          # Paper, Evaluation, TaskChain, etc.
│   │   │                        # (from work_plan.md)
│   │   ├── review.py            # Review, Finding, Verdict, etc.
│   │   │                        # (from review_plan.md §2.2)
│   │   └── blackboard.py        # Blackboard, ConvergenceState, etc.
│   ├── prompts/
│   │   ├── research_system.py   # research_guideline.md → system prompt
│   │   ├── review_system.py     # review_guideline.md → system prompt
│   │   ├── meta_review_system.py
│   │   └── rubric.py            # Shared rubric definitions
│   ├── tools/                   # (from work_plan.md, shared)
│   ├── knowledge/               # (from work_plan.md, shared)
│   └── metrics/
│       ├── __init__.py
│       ├── review_quality.py    # §1.8 metrics computation
│       ├── convergence.py       # §2.5 convergence checks
│       └── finding_tracker.py   # Cross-iteration finding resolution
├── config/
│   ├── constitution.yaml        # (from work_plan.md)
│   └── review_config.yaml       # Venue thresholds, iteration limits
└── tests/
    ├── test_review_metrics.py   # §1.1-1.7 metric extraction tests
    ├── test_review_quality.py   # §1.8 meta-review tests
    ├── test_convergence.py      # §2.5 convergence logic tests
    ├── test_interaction.py      # §3.2-3.4 protocol tests
    └── calibration/
        └── test_calibration.py  # Agent vs. human review agreement
```

### 4.2 System Prompt Design

Each agent's system prompt is the highest-leverage design decision. The prompts encode behavior, not just instructions.

**Research Agent system prompt** (built from):
- Identity: "You are a robotics researcher following the methodology in the research guidelines."
- Full text of `research_guideline.md` (evaluation rubric, thinking chain, significance tests)
- State machine context from `work_plan.md` (current stage, backward transition rules)
- Previous review findings to address (from blackboard)
- Output format: `ResearchArtifact` + `RevisionResponse` as structured JSON

**Review Agent system prompt** (built from):
- Identity: "You are an adversarial reviewer calibrated to [venue] standards."
- Full text of `review_guideline.md` (attack vectors, protocol, rubric, venue calibration)
- Current venue-specific thresholds from `review_guideline.md` §4.2
- Output format: `Review` as structured JSON with all `Finding` fields required
- Anti-patterns list from `review_guideline.md` §5.4 as explicit "DO NOT" rules
- Graduated pressure instructions based on current iteration (§2.6)

**Meta-Reviewer system prompt** (built from):
- Identity: "You are an area chair evaluating review quality."
- Review quality metrics from §1.8 with exact thresholds
- Anti-patterns from `review_guideline.md` §5.4
- Output format: `ReviewQualityReport` with pass/fail per metric

### 4.3 Tool Sharing and Access Control

| Tool | Research Agent | Review Agent | Meta-Reviewer |
|---|---|---|---|
| `arxiv_search` | Yes | Yes (for concurrent work check) | No |
| `paper_fetch` | Yes | Yes (to verify citations) | No |
| `semantic_scholar` | Yes | Yes (for novelty check) | No |
| `knowledge_read` | Yes | Yes | No |
| `knowledge_write` | Yes | No (read-only) | No |
| `report` | Yes | No | No |
| `blackboard_read` | Yes | Yes | Yes |
| `blackboard_write` | Yes (artifact) | Yes (review) | Yes (quality report) |

The review agent has **read-only** access to the knowledge store. It can search for prior work to check novelty claims but cannot modify the research agent's data. This prevents accidental corruption of the knowledge graph.

### 4.4 Configuration

```yaml
# review_config.yaml

target_venue: "RSS"  # or CoRL, IJRR, T-RO, RA-L, ICRA, IROS

iteration:
  max_iterations: 5
  meta_review_max_rounds: 2
  stagnation_threshold: 2  # consecutive identical verdicts → stop

convergence:
  quality_threshold:
    max_fatal: 0
    max_serious: 1
    min_verdict: "weak_accept"

graduated_pressure:
  iteration_1: "structural_scan"    # Appendix A.1 only
  iteration_2: "full_review"        # All attack vectors
  iteration_3_plus: "focused_rereview"  # Previous findings only

human_checkpoints:
  on_backward_to_significance: true  # Always
  on_low_confidence_significance: true
  on_low_confidence_formalization: true
  on_final_accept: true
  periodic: 3  # Every N iterations if not triggered otherwise

review_quality_thresholds:
  min_actionability: 0.80
  min_grounding: 0.90
  max_vague_critiques: 0
  min_falsifiability: 0.70
  min_steel_man_sentences: 3

anti_collapse:
  monotonic_severity: true     # Findings can't be silently downgraded
  min_finding_resolution: 0.50  # Research agent must address ≥50%
  fresh_eyes_final: true        # Last iteration reviews from scratch
```
