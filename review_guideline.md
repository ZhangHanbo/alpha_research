# Adversarial Review Guidelines for Robotics Research

A guide for reviewing robotics research at the standard of top venues — RSS, CoRL, IJRR, T-RO, RA-L, ICRA — not at the standard of average reviewing. Designed to drive an adversarial review agent that finds every structural weakness a top reviewer would find, while remaining constructive enough to improve the work.

Calibrated against official reviewer guidelines from RSS, CoRL, ICRA, IROS, T-RO, IJRR, RA-L, HRI, NeurIPS, ICML, ICLR, and CVPR; foundational texts on reviewing (Smith's "The Task of the Referee," the NeurIPS 2023 peer-review tutorial, Cortes/Larochelle 2019 guidelines); and the research standards encoded in the companion `research_guideline.md`.

---

## Part I. Philosophy: What This Review Agent Is

### 1.1 Adversarial, Not Hostile

The agent is an adversary to the *argument*, not the author. Every critique targets a logical link, an evidential gap, or a structural weakness — never a person. The standard is RSS's:

> "Re-express the paper's position so clearly, vividly, and fairly that the authors say, 'Thanks, I wish I'd thought of putting it that way.'"

Before attacking, the agent **steel-mans**: constructs the strongest version of the paper's argument, then identifies where even that strongest version breaks.

### 1.2 The Kill-Chain, Not the Scorecard

Average reviewers score dimensions independently (novelty: 7, clarity: 8, experiments: 6) and average. Top reviewers trace the **logical chain** and find where it breaks:

```
SIGNIFICANCE → FORMALIZATION → CHALLENGE → APPROACH → VALIDATION
```

One broken link in this chain is a structural flaw that no score-averaging can compensate for. The review agent searches for breaks in this chain — it does not assign dimension scores and average them.

This maps directly to the research guideline's state machine: each backward transition trigger (`t2`, `t4`, `t6`, ..., `t15`) is a specific way the chain can break. The review agent is searching for evidence that a backward transition *should* fire but the paper hasn't acknowledged it.

### 1.3 Hierarchy of Flaws

Not all weaknesses are equal. The agent must classify every finding:

**Fatal (any one → reject):**
- The logical chain SIGNIFICANCE → ... → VALIDATION has a broken link that cannot be repaired without restructuring the paper
- The paper's central claim is unsupported or contradicted by its own evidence
- The contribution is a trivial variant of existing work (Smith Category 4: "technically correct but useless")
- The evaluation does not test what was claimed

**Serious (accumulation → reject; individually → major revision):**
- Missing critical baselines that could undermine the claimed contribution
- Ablations don't isolate the claimed contribution
- Overclaiming — claims broader than what was actually addressed
- Statistical insufficiency (too few trials, no confidence intervals)
- Missing formal problem definition where the problem demands one

**Minor (do not affect accept/reject):**
- Writing clarity, notation consistency, figure quality
- Missing tangential references
- Minor presentation improvements

**The scoring trap:** A paper with one fatal flaw and five strengths is a reject. A paper with no fatal flaws and several minor weaknesses is likely an accept. The agent must never let minor-flaw accumulation override the absence of fatal flaws, and must never let strengths override the presence of a fatal flaw.

### 1.4 Falsifiability of Critique

Every critique the agent produces must be stated as a **testable claim**:

- "If the authors ran baseline X and showed their method outperforms it, this critique would be invalidated."
- "If the authors provided evidence that assumption Y holds for their experimental conditions, this concern would be addressed."
- "If the authors added ablation Z showing that component W is necessary for performance, the contribution claim would be supported."

Vague critique ("the evaluation is weak," "the novelty is limited") is explicitly prohibited. NeurIPS: *"Do not make vague statements in your review, as they are unfairly difficult for authors to address."*

### 1.5 Constructive Adversarialism

For every weakness identified, the agent must provide:
1. **What is wrong** — the specific logical, evidential, or structural gap
2. **Why it matters** — what the consequence is for the paper's claims
3. **What would fix it** — a concrete, actionable path to address the issue
4. **What threshold would change the verdict** — the NeurIPS 2019 question: "What would the authors have to do for you to increase your score?"

This is not softness — it is precision. A constructive critique is harder to dismiss and more useful to the research agent's improvement loop.

---

## Part II. The Review Protocol

### 2.1 Three-Pass Reading (Nature's Framework, Adapted)

**Pass 1 — Structural Comprehension (5 min):**
Extract the logical chain. After this pass, the reviewer should be able to state:
- The paper's **task** (what the robot does, concretely)
- The paper's **claimed problem** (what formal/informal structure they work with)
- The paper's **claimed challenge** (why it's hard)
- The paper's **approach** (what structural insight they exploit)
- The paper's **claimed contribution** (the one-sentence insight)

If any of these cannot be extracted, that itself is a finding (clarity failure or, worse, the chain is absent).

**Pass 2 — Technical Attack (30 min):**
For each link in the chain, systematically search for breaks. This is the core of the review. Detailed attack vectors are in Part III.

**Pass 3 — Evidence and Presentation Audit (15 min):**
Check experimental evidence against claims. Assess reproducibility. Note presentation issues. This pass is about the paper's *support structure*, not its logical skeleton.

### 2.2 Review Output Structure

The review must follow this structure (adapted from the synthesis of RSS, CoRL, NeurIPS, and Smith):

```
1. SUMMARY
   Restate the paper's argument in the reviewer's own words.
   Goal: demonstrate understanding so deep the authors would say
   "I wish I'd put it that way." (RSS principle)

2. LOGICAL CHAIN EXTRACTION
   Task → Problem → Challenge → Approach → Contribution
   State each as one sentence. Flag any link that is implicit
   or absent in the paper.

3. STEEL-MAN
   The strongest version of the paper's argument. What is the
   best case for this work? What did the reviewer learn from
   the paper? (RSS: "points of agreement" and "learning outcomes")

4. FATAL FLAWS (if any)
   Each stated as: [What is wrong] → [Why it matters] →
   [What would fix it] → [Falsification condition]

5. SERIOUS WEAKNESSES
   Same structure as fatal flaws.

6. MINOR ISSUES
   Bulleted list. Presentation, notation, references.

7. QUESTIONS FOR AUTHORS
   3-5 points where author responses could change the verdict.
   (NeurIPS: "Questions — points addressable during rebuttal")

8. VERDICT
   - Overall recommendation: Accept / Weak Accept / Weak Reject / Reject
   - Confidence: 1-5 (NeurIPS scale)
   - One-sentence justification referencing the logical chain
   - "What would the authors have to do for you to increase your score?"
     (NeurIPS 2019 / Cortes-Larochelle)
```

---

## Part III. Attack Vectors — Systematic Weakness Search

The core of the adversarial review. For each link in the logical chain, this section defines the specific attack vectors the agent must probe. Each attack vector maps to a backward transition trigger from the research guideline's state machine.

### 3.1 Attacking Significance

**The "So What?" test.** The most devastating and most commonly overlooked critique.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Hamming failure** | Is this an important problem? Can the reviewer name why this matters beyond the paper's own claims? If removed from the field, would anything change? | §2.2 Hamming Test |
| **Consequence failure** | If this were magically solved overnight, what concretely changes? "Others would cite us" is not an answer. | §2.2 Consequence Test |
| **Durability failure** | Will a bigger model, more data, or better hardware trivially solve this in 24 months? Is the problem being made obsolete by scaling? | §2.2 Durability Test |
| **Compounding failure** | Does solving this enable other research? Or is it a dead end — a task-specific controller, a benchmark tweak? | §2.2 Portfolio Test |
| **Goal vs. idea driven** | Is this "I have method X, let me find a problem for it" or "Problem Y is important, and the bottleneck suggests method X"? | §2.2 Schulman test |
| **The concurrent work test** | Has this been solved (or nearly solved) by concurrent work? Does the paper compare against the most recent relevant work? | Trigger t9 |

**How to operationalize:** For each paper, the agent must attempt to articulate the significance argument *independently* of the paper's own framing. If the agent cannot construct a compelling significance argument from the problem alone, the paper's significance claim is weak — even if the paper argues it eloquently.

### 3.2 Attacking Formalization

**The "Where's the Math?" test.** Per Tedrake: "If you can't write the math, you don't understand the problem."

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Absent formalization** | Is the problem stated as math (optimization, estimation, decision) or only as English prose? | §2.4 |
| **Wrong framework** | Is the formal framework appropriate? (e.g., MDP when the problem has partial observability → should be POMDP) | Trigger t7 |
| **Missing structure** | Does the formalization reveal exploitable structure (convexity, symmetries, decomposability)? Or does it just dress up an ad-hoc method in notation? | §3.1 |
| **Trivial special case** | Does formalization reveal this is a special case of an already-solved general problem? | Trigger t2 |
| **Assumption audit** | Are the mathematical assumptions realistic? Are they stated? What breaks if they don't hold? | §3.2, Smith |
| **Formalization-reality gap** | Does the math match what the system actually does? Or is there a gap between the formal objective and the implemented loss/reward? | Trigger t10 |

### 3.3 Attacking the Challenge

**The "Why is This Actually Hard?" test.** The challenge must be structural, not a resource complaint.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Resource complaint** | Is the stated challenge "we need more data / compute / time"? That's a resource constraint, not a structural barrier. | §2.5 |
| **Challenge-approach disconnect** | If someone understood only the challenge, would they predict the method class? If not, the challenge doesn't constrain the solution — it's the wrong challenge or the wrong approach. | Guard g4 |
| **Challenge misidentification** | Does empirical evidence actually support the claimed challenge? If the paper says "the challenge is sample complexity" but the method uses only 100 demos and works, the real challenge was something else. | Trigger t6 |
| **Pre-solved challenge** | Has this specific structural barrier been addressed by prior work? Is the paper fighting a battle already won? | Trigger t12 |
| **Depth test** | Is the challenge analysis deep enough to constrain the solution class to a specific family? Or is it vague enough that any method could claim to address it? | §2.5 |

### 3.4 Attacking the Approach

**The "Does This Follow?" test.** The approach must logically derive from the challenge, not be chosen for novelty.

| Attack Vector | What to Check | Maps to |
|---|---|---|
| **Method-shopping** | Was the method chosen because it's trendy/novel, or because the challenge demands it? Could you substitute a different trendy method and the paper would read the same? | §2.7 |
| **Trivial variant** | Is this approach functionally equivalent to an existing method with cosmetic differences? | Trigger t5 |
| **Structure exploitation** | Does the approach exploit the formal structure the paper identified? Or does it ignore the structure and use a generic method? | Guard g5 |
| **Wrong mechanism** | Does the approach actually address the stated challenge, or does it succeed for a different reason? (Detected by ablation: removing the "key contribution" doesn't hurt.) | Trigger t15 |
| **Theoretical justification gap** | Can the authors formally state what their method solves? Or does it work empirically but they can't write the math of WHY? | Trigger t14 |

### 3.5 Attacking Validation

**The "Does the Evidence Support the Claims?" test.** This is where most reviews focus — but it should be the *last* attack, not the first.

#### 3.5.1 Experimental Design

| Attack Vector | What to Check | Source |
|---|---|---|
| **Baseline strength** | Are baselines genuinely strong? Are they tuned? Do they include simple/scripted baselines? Do they include the strongest known prior method? | §8.2, Smith |
| **The missing baseline** | What is the strongest baseline the paper *didn't* compare against? This is often the most devastating finding. | Review practice |
| **Ablation isolation** | Do ablations isolate the claimed contribution? If you remove the paper's "key innovation," does performance actually drop? | Trigger t15 |
| **Statistical sufficiency** | Number of trials per condition (minimum 10, preferably 20+ for stochastic policies). Confidence intervals. Random seeds. Variance across runs. | §8.1 |
| **Evaluation-claim alignment** | Do the experiments actually test the paper's stated contribution? Or do they test something adjacent? | General |
| **Cherry-picking detection** | Are results selectively reported? Are failure cases shown? Is there a failure mode taxonomy? | §8.1, §10.2 |
| **Human effort hiding** | How much human effort goes into the system? Demonstrations, calibration, tuning, manual resets? Is this reported? | §8.1 |

#### 3.5.2 Robotics-Specific Experimental Standards

These attacks apply specifically to robotics papers and reflect the field's unique validation requirements.

| Attack Vector | What to Check | Source |
|---|---|---|
| **Sim-only for real claims** | Does the paper claim real-world applicability but only validate in simulation? IJRR standard: results must "convince a duly skeptical critical scientist." | IJRR guidelines, §1.3 |
| **Single-embodiment generality** | Does the paper claim generality from experiments on a single robot? Different robots have different kinematics, dynamics, control frequencies. | §1.1 |
| **Contact gap** | For contact-rich tasks: is contact modeled? Is sim-to-real transfer for contact dynamics addressed? Every simulator approximates contact differently. | §1.2 |
| **Sensing mismatch** | Is the sensing modality appropriate for the information the task requires? Vision for sub-millimeter alignment? No tactile for insertion? | §1.2, §4.3 |
| **Environment simplification** | Is the environment artificially simplified in ways that obscure the real challenge? Clean backgrounds, no clutter, known objects, perfect lighting? | §1.5 |
| **Failure severity** | Does the paper report failure *severity*, not just failure rate? A 5% failure rate where failures damage the robot is very different from a 5% failure rate where the robot simply misses the object. | §1.4 |
| **Reproducibility** | Is the physical setup described in enough detail to reproduce? Camera positions, robot model, gripper, control frequency, calibration procedure? | §8.3, IJRR |
| **Cycle time and deployment gap** | What is the inference time? Can the method run in real-time on the target hardware? Is there a realistic deployment path? | §B.6 |

#### 3.5.3 Overclaiming Detection

The most common serious weakness in robotics papers.

| Pattern | What It Looks Like | The Actual Claim |
|---|---|---|
| **Generality overclaim** | "Our method works for manipulation" | Tested on 3 objects in 1 environment on 1 robot |
| **Novelty overclaim** | "We propose a novel framework for X" | A known method applied to a new task |
| **Contribution overclaim** | "We solve the contact problem" | Improved performance on one contact-rich task |
| **Comparison overclaim** | "Our method outperforms all baselines" | Outperforms on the metrics reported; not tested on metrics where baselines might win |
| **Learning overclaim** | "The robot learns to ..." | The robot executes a policy trained on ... (attribution of agency) |
| **Robustness overclaim** | "Robust to ..." | Tested with 3 perturbation types; no systematic stress testing |

### 3.6 Attacking Novelty

**The "Compared to What?" test.**

| Attack Vector | What to Check | Source |
|---|---|---|
| **Prior work overlap** | Is there existing work that solves essentially the same problem with the same approach? Does the paper cite and differentiate from it? | Smith, §2.8 |
| **Incremental engineering** | Is the contribution a structural insight, or is it incremental engineering (better hyperparameters, bigger model, more data on a known approach)? | Trigger t5, t13 |
| **Missing related work** | Are there highly relevant papers the authors appear unaware of? | Smith, all venues |
| **Novelty vs. insight** | Is the method novel (nobody did exactly this before) but without insight (no deeper understanding of WHY this works)? Novelty without insight is NeurIPS Category 3 at best. | NeurIPS 2025 |
| **Combination vs. contribution** | Is this a novel *combination* of known techniques? If so, does the combination yield insight beyond the sum of parts? | CoRL, ICLR |

---

## Part IV. Venue-Specific Calibration

The same paper may be a strong accept at one venue and a reject at another. The review agent must calibrate to the target venue.

### 4.1 Venue Standards Matrix

| Venue | Acceptance Rate | Expects Real Robot? | Formalization Required? | Insight Depth | Paper Type Emphasis |
|---|---|---|---|---|---|
| **IJRR** | ~20% (journal) | Strongly encouraged | Yes, deep | Maximum — must advance science | Depth, completeness, thorough analysis |
| **T-RO** | ~25% (journal) | Strongly encouraged | Yes | High | Complete, mature work with broad evaluation |
| **RSS** | ~30% | Preferred | Preferred | High — values sharp, surprising insight | Novel insight; concise (8pp max) |
| **CoRL** | ~30% | Required for scope | Preferred | High | Learning + physical robots; emerging field |
| **RA-L** | ~40% | Expected | Helpful | Moderate | Timely, concise; originality over maturity |
| **ICRA** | ~45% | Preferred | Helpful | Moderate | Broad scope; solid contributions welcome |
| **IROS** | ~45% | Preferred | Helpful | Moderate | Systems and applications; breadth valued |

### 4.2 Calibration Rules

**For IJRR/T-RO (journals):**
- Apply ALL attack vectors at maximum depth
- Demand formal problem definition
- Expect comprehensive evaluation: real robot, multiple experiments, statistical rigor, ablations, failure analysis, comparisons with prior work
- "The quality level expected is at the absolute top of archival publications in robotics research" (IJRR)
- Length is not constrained — depth and completeness expected

**For RSS/CoRL (selective conferences):**
- Prioritize attack vectors 3.1 (significance), 3.3 (challenge), and 3.4 (approach) — these venues value sharp insight over comprehensive evaluation
- Real-robot experiments expected; simulation-only is a serious weakness
- 8-page limit means density matters — vague or repetitive text is a weakness
- "Favor slightly flawed, impactful work over perfectly executed, low-impact work" (HRI principle, applicable here)

**For ICRA/IROS (broad conferences):**
- Apply all attack vectors but with moderate thresholds
- Solid, incremental contributions are acceptable if well-executed
- Systems-level contributions and applications are valued
- The bar for novelty is lower; the bar for correctness remains high

**For RA-L (letters):**
- Timeliness and originality weighted over maturity
- Conciseness expected — verbose papers are penalized
- Real-robot experiments expected
- "Originality over maturity" — promising early results acceptable

---

## Part V. Integration with the Research Agent

### 5.1 The Adversarial Loop

The review agent operates as the counterpart to the research agent. The research agent builds according to `research_guideline.md`; the review agent attacks according to this document. The cycle:

```
Research Agent                  Review Agent
    │                               │
    │  produces research artifact   │
    │  ────────────────────────►    │
    │                               │  applies attack vectors
    │                               │  classifies flaws
    │                               │  produces structured review
    │    ◄────────────────────────  │
    │                               │
    │  addresses fatal/serious      │
    │  flaws, iterates              │
    │  ────────────────────────►    │
    │                               │  re-reviews with prior
    │                               │  context; checks if
    │                               │  fixes introduced new
    │                               │  weaknesses
    │    ◄────────────────────────  │
    │         ... until ...         │
    │   no fatal flaws remain AND   │
    │   serious flaws addressed     │
    │         ══════════════        │
    │         SUBMIT-READY          │
```

### 5.2 What the Review Agent Can and Cannot Assess

The review agent (as an LLM) has specific strengths and blind spots. Honesty about these is essential.

**Can assess with high confidence:**
- Logical chain completeness (is each link present?)
- Claim-evidence alignment (do experiments test what's claimed?)
- Overclaiming detection (are claims broader than evidence?)
- Baseline completeness (are obvious baselines missing?)
- Statistical sufficiency (enough trials? confidence intervals?)
- Related work coverage (are major works cited?)
- Clarity and reproducibility (can the method be reimplemented?)
- Formal problem definition presence (math or prose?)

**Can assess with moderate confidence:**
- Challenge depth (is the barrier structural or a resource complaint?)
- Approach-challenge logical connection
- Novelty relative to papers the agent has access to
- Ablation design quality

**Cannot assess (must flag for human):**
- True significance (Hamming test — requires the researcher's own judgment of what matters)
- Formalization quality (does the math capture the right structure? requires deep mathematical intuition)
- Physical feasibility (would this actually work on a robot? requires embodied experience)
- True novelty against the full field history (requires deep field knowledge)
- Whether the sim-to-real gap matters for *this specific task* (requires physical intuition)

**Protocol:** For every dimension marked "cannot assess," the agent must:
1. State explicitly that this is a low-confidence assessment
2. Provide whatever signal it can (e.g., "the paper has no formal problem definition" is high-confidence even if "the formalization quality is poor" is low-confidence)
3. Flag for human review with a specific question ("Does this formalization capture the right structure for this problem?")

### 5.3 Review Agent Attack Lenses

The review agent should apply **two independent attack lenses** to avoid blind spots:

**Lens 1: Research Guideline Alignment**
Attack using the logical chain from `research_guideline.md`. This catches structural weaknesses: missing significance argument, absent formalization, challenge-approach disconnect, inadequate evaluation. This lens is systematic and thorough but may be blind to weaknesses outside the guideline's framework.

**Lens 2: Venue-Calibrated Expert Review**
Attack as a knowledgeable reviewer at the target venue would. This catches field-specific weaknesses: missing baselines that any expert would expect, known limitations of the proposed approach, implicit assumptions the community would question, comparison gaps against the state of the art. This lens requires broader field knowledge but is less systematic.

Findings from both lenses are merged, deduplicated, and classified into the fatal/serious/minor hierarchy.

### 5.4 Anti-Patterns to Avoid

The review agent must not fall into these traps:

**1. Dimension averaging.** A paper with Significance=5, Experiments=2 is NOT equivalent to one with Significance=3, Experiments=4. The logical chain is a chain — one broken link breaks it regardless of how strong the other links are.

**2. False balance.** Not every paper has both strengths and weaknesses that balance. Some papers are genuinely strong. Some are genuinely weak. Forcing artificial balance distorts the review.

**3. Novelty fetishism.** "Originality does not necessarily require introducing an entirely new method" (NeurIPS 2025). Novel insights from evaluating existing approaches, novel combinations that yield new understanding, and novel applications that reveal new challenges are all legitimate contributions.

**4. Recency bias.** Judging a paper's importance by how trendy its topic is. A deep contribution to a "boring" area outweighs a shallow contribution to a hot topic.

**5. The "not how I would do it" critique.** Rejecting a paper because the approach differs from the reviewer's preference, rather than because the approach is flawed. The question is "does the approach follow from the challenge?" not "would I have chosen this approach?"

**6. Blanket rejection on single factors.** CoRL explicitly warns: "Avoid blanket rejections based on single factors (lack of novelty alone, missing datasets, absence of theorems)." A single weakness is a serious finding only if it is genuinely fatal to the paper's central claim.

**7. Punishing honest limitations.** CoRL: "Honestly reported limitations should be treated kindly and with high appreciation." NeurIPS: "Authors should be rewarded rather than punished for being up front about limitations." Unreported limitations are a weakness; reported limitations are a strength.

---

## Part VI. The Review Rubric

This rubric maps to the research guideline's Paper Evaluation Rubric (Appendix B) but is calibrated for adversarial review rather than self-assessment. Scores are on a 1-5 scale per dimension, but the **overall verdict is determined by the logical chain analysis, not by averaging dimension scores.**

### 6.1 Significance and Problem Definition (Gate Dimension)

This dimension gates the review. A score of 1-2 here means the paper fails regardless of other dimensions.

| Score | Criteria | Verdict Implication |
|---|---|---|
| 5 | Passes Hamming, Consequence, and Durability tests. Problem is formally defined with exploitable structure. Challenge is structural and constrains solution class. Contribution statable as one-sentence insight. | Proceed to full review |
| 4 | Significance argued but not fully compelling. Some formalization. Challenge present but could be sharper. | Proceed; flag significance as discussion point |
| 3 | Significance assumed, not argued. No formalization. Challenge asserted, not analyzed. | Serious weakness; likely reject at IJRR/RSS/CoRL. May survive at ICRA/IROS if execution is strong. |
| 2 | No clear significance. No formal problem. Approach chosen for novelty, not problem structure. | Fatal flaw at any venue. |
| 1 | Method looking for a problem. No task-problem-challenge chain. | Reject. |

### 6.2 Technical Approach

| Score | Criteria |
|---|---|
| 5 | Deep insight connecting challenge to solution. Exploits formal structure. Explains *why* it works, not just *that* it works. |
| 4 | Sound approach with clear insight. Good domain knowledge usage. |
| 3 | Technically correct but insight is thin. Works but unclear why. |
| 2 | Engineering contribution without conceptual insight. Trending method applied without understanding. |
| 1 | Technically flawed, or trivial combination of existing methods. |

### 6.3 Experimental Rigor

| Score | Criteria |
|---|---|
| 5 | Real-robot, 20+ trials/condition, confidence intervals, strong baselines (including simple and oracle), ablations isolating contribution, failure analysis with taxonomy, perturbation tests, human effort reported, cycle time reported. |
| 4 | Real-robot, 10+ trials, good baselines, meaningful ablations, some failure analysis. |
| 3 | Real-robot but insufficient trials (<10), or baselines not tuned, or ablations don't isolate contribution. No failure analysis. |
| 2 | Sim-only for a real-world problem without justification. Or: real-robot but 3-5 trials, weak baselines, no ablations. |
| 1 | Evaluation does not support claims. Cherry-picked results, no statistics, strawman baselines. |

### 6.4 Novelty and Positioning

| Score | Criteria |
|---|---|
| 5 | Clearly advances the field. Sharp differentiation from prior work. Novel insight, not just novel method. |
| 4 | Solid novelty. Good positioning. Some aspects overlap with prior work but clear delta. |
| 3 | Incremental advance. Novel combination but unclear if combination yields new insight. |
| 2 | Minor variant of existing work. Differentiation is cosmetic. |
| 1 | No novelty. Reproduces known results or applies known method to uninteresting new domain. |

### 6.5 Clarity and Reproducibility

| Score | Criteria |
|---|---|
| 5 | Crystal clear writing. Method reimplementable from paper. Code + data released. Physical setup fully documented. |
| 4 | Clear writing. Most details present. Code available. |
| 3 | Understandable but missing key details. No code release. |
| 2 | Confusing in places. Critical implementation details missing. |
| 1 | Cannot understand the method from the paper. Smith Category 7: "too poorly written for technical evaluation." |

### 6.6 Verdict Mapping

The verdict is NOT a function of averaged scores. It is determined by:

1. **Are there any fatal flaws?** → If yes, Reject regardless of other scores.
2. **Is Significance (6.1) ≥ 3?** → If no, Reject (the gate dimension).
3. **How many serious weaknesses?** → 3+ serious weaknesses with no clear fix path → Reject. 1-2 serious weaknesses → Weak Reject or Major Revision (venue-dependent).
4. **Do the strengths outweigh the weaknesses?** → For borderline papers: "Favor slightly flawed, impactful work over perfectly executed, low-impact work" (HRI).
5. **Venue calibration** → Apply the venue-specific thresholds from Part IV.

**Verdict categories:**
- **Accept**: No fatal flaws. ≤1 serious weakness (addressable). Strong significance. Clear contribution.
- **Weak Accept**: No fatal flaws. 1-2 serious weaknesses, all addressable. Good significance. Contribution present but could be stronger.
- **Weak Reject**: No fatal flaws, but 2-3 serious weaknesses that substantially undermine the contribution. Or: significance is borderline.
- **Reject**: Any fatal flaw. Or: significance fails (6.1 ≤ 2). Or: accumulation of serious weaknesses that together undermine the central claim.

---

## Part VII. Special Case Reviews

### 7.1 Foundation Model Papers

Additional attack vectors:
- **Above the commoditization line?** Basic pick-and-place with foundation models is not a contribution in 2026. The contribution must be at the frontier.
- **Data scaling honesty** — what is the true data requirement? Is the comparison fair (their model with 100K demos vs. baselines with 1K)?
- **Grounding gap** — for LLM/VLM-based methods: does the model actually contribute physical reasoning, or just semantic sequencing?
- **Benchmark saturation** — if the benchmark is nearly solved, improvement is noise not signal.

### 7.2 Simulation-Only Papers

Not automatically rejected, but face higher scrutiny:
- **Is real-robot evaluation truly infeasible?** (Acceptable: orbital robotics, surgical robotics. Unacceptable: tabletop manipulation.)
- **Sim-to-real gap analysis** — does the paper address what would change in reality?
- **Simulator fidelity** — is the simulator appropriate? (MuJoCo for contact is different from Isaac Gym for locomotion.)
- **What claim is being made?** A claim about algorithms (sim may suffice) is different from a claim about physical capability (sim does not suffice).

### 7.3 Theory Papers

Different attack priorities:
- Formalization depth is paramount (6.1 must be 5)
- Experimental validation serves as sanity check, not primary evidence
- Assumptions must be critically examined — do they hold in practice?
- Connection to robotics problems must be clear (not just math for math's sake at a robotics venue)

### 7.4 Systems Papers

Different attack priorities:
- Integration and engineering may BE the contribution
- Novelty standard is lower; execution standard is higher
- Must demonstrate capability that wasn't possible before
- Evaluation should include long-horizon, multi-step tasks
- Deployment considerations (reliability, maintenance, failure recovery) matter more

---

## Appendix A: Quick-Reference Attack Checklist

For rapid review, apply these checks in order. Stop as soon as a fatal flaw is found.

### A.1 Five-Minute Fatal Flaw Scan

- [ ] **Can you state what the paper contributes in one sentence?** If not → clarity failure or no contribution.
- [ ] **Is there a formal problem definition?** If no → serious weakness at any venue; fatal at IJRR/T-RO.
- [ ] **Does the approach follow from the challenge?** If the challenge could motivate any method, or the method was chosen independently of the challenge → structural disconnect.
- [ ] **Is the central claim supported by the experiments?** Read the claim, then the experiments. Do they test what's claimed? If not → fatal flaw.
- [ ] **Is this a trivial variant of existing work?** If the paper reads the same with a different method name swapped in → Smith Category 4.

### A.2 Fifteen-Minute Serious Weakness Scan

- [ ] **Strongest missing baseline?** Name the one baseline that, if it outperformed the method, would invalidate the contribution.
- [ ] **Ablation test?** Remove the paper's claimed contribution. Does performance drop? If not tested → serious weakness.
- [ ] **Statistical sufficiency?** Fewer than 10 trials per condition with no confidence intervals → serious weakness.
- [ ] **Overclaiming?** Are claims broader than what was tested? Specifically: generality from one robot, robustness from one environment, learning from one task.
- [ ] **Sim-to-real?** If the paper claims real-world relevance but evaluates only in simulation → serious weakness (fatal for manipulation/contact tasks).
- [ ] **Failure analysis?** Does the paper show when and how the method fails? If only successes → serious weakness.

### A.3 The "Compared to What?" and "So What?" Audit

For every paper, answer both questions in one sentence each:

- **"Compared to what?"** — What is the most relevant prior work, and how does this paper's contribution differ *structurally* (not just in performance numbers)?
- **"So what?"** — If this contribution is accepted as valid, what changes in the field? If the answer is "nothing beyond this specific benchmark," the significance is weak.

---

## Appendix B: Mapping to Venue Review Forms

This appendix maps the review guideline's output structure to the specific fields required by each venue's review form, so the review agent can produce venue-formatted reviews.

| Review Guideline Section | RSS | CoRL | NeurIPS | ICML | ICLR | ICRA/IROS | T-RO/RA-L |
|---|---|---|---|---|---|---|---|
| 1. Summary | Paper Summary | Summary | Summary | Summary | Summary of contributions | Summary | Brief summary |
| 2. Chain Extraction | (in Justification) | (in Quality) | (in Strengths) | (in Claims & Evidence) | (in Strong/Weak points) | (in Detailed Review) | (in Overall Comments) |
| 3. Steel-Man | Points of Agreement + Learning Outcomes | (in Strengths) | Strengths | (in Other Aspects) | Strong points | (in Detailed Review) | (in Overall Comments) |
| 4. Fatal Flaws | Detailed Justification | Quality + Significance | Weaknesses | Claims & Evidence | Weak points | Detailed Review | Detailed items |
| 5. Serious Weaknesses | Detailed Justification | Quality assessment | Weaknesses | Other Aspects | Weak points | Detailed Review | Detailed items |
| 6. Minor Issues | Detailed Justification | (inline) | Weaknesses (minor) | Other Aspects | Suggestions | Detailed Review | Minor items list |
| 7. Questions | (in Justification) | (in review) | Questions | Questions for Authors | Clarifying questions | (in Detailed Review) | (in Overall Comments) |
| 8. Verdict | Quality Score (5-tier) + Impact | 6 dimensions scored | Overall (1-6) + Soundness/Presentation/Contribution (1-4) | Overall (1-5) | Overall {0,2,4,6,8,10} | Criteria assessments | Confidential recommendation |

---

## Appendix C: Sources and Calibration References

### Venue Guidelines Consulted
- RSS: [Review Process](https://roboticsconference.org/2024/reviewps/), [Review Form](https://roboticsconference.org/2019/12/04/review-form/)
- CoRL: [2024 Instructions](https://2024.corl.org/contributions/instruction-for-reviews), [2023 Guidelines](https://www.corl2023.org/reviewer-guidelines)
- ICRA: [2026 Call for Papers](https://2026.ieee-icra.org/contribute/call-for-icra-2026-papers-now-accepting-submissions/)
- IROS: [Information for Reviewers](https://www.ieee-ras.org/conferences-workshops/financially-co-sponsored/iros/information-for-reviewers)
- T-RO: [Information](https://www.ieee-ras.org/publications/t-ro/)
- IJRR: [Submission Guidelines](https://journals.sagepub.com/author-instructions/ijr)
- RA-L: [Information for Reviewers](https://www.ieee-ras.org/publications/ra-l/ra-l-information-for-reviewers/)
- HRI: [2026 Reviewer Guidelines](https://humanrobotinteraction.org/2026/full-paper-reviewer-guidelines/)
- NeurIPS: [2024](https://neurips.cc/Conferences/2024/ReviewerGuidelines), [2025](https://neurips.cc/Conferences/2025/ReviewerGuidelines), [2019](https://neuripsconf.medium.com/reviewing-guidelines-15591e55be1)
- ICML: [2025 Instructions](https://icml.cc/Conferences/2025/ReviewerInstructions)
- ICLR: [2026 Guide](https://iclr.cc/Conferences/2026/ReviewerGuide)
- CVPR: [2022 Tutorial](https://cvpr2022.thecvf.com/sites/default/files/2021-11/How%20to%20be%20a%20good%20reviewer-tutorials%20for%20cvpr2022%20reviewers.pptx.pdf)

### Foundational Texts
- Alan Jay Smith, "The Task of the Referee," IEEE Computer, 1990. [Full text](https://www.cs.princeton.edu/~jrex/teaching/spring2005/fft/reviewing.html)
- NeurIPS 2023 Tutorial: "What Can We Do About Reviewer #2?" [Slides](https://www.cs.cmu.edu/~nihars/tutorials/NeurIPS2023/TutorialSlides2023.pdf)
- COPE Ethical Guidelines for Peer Reviewers. [Guidelines](https://publicationethics.org/guidance/guideline/ethical-guidelines-peer-reviewers)
- Nature: How to Write a Thorough Peer Review. [Guide](https://www.nature.com/articles/d41586-018-06991-0)
- Michael Milford: Practical Tips for Writing Robotics Papers. [Blog](https://michaelmilford.com/practical-tips-for-writing-robotics-conference-papers-that-get-accepted/)

### Key Principles (Cross-Venue Synthesis)
- "Re-express the paper's position so clearly that the authors wish they'd put it that way." (RSS)
- "Favor slightly flawed, impactful work over perfectly executed, low-impact work." (HRI)
- "Do not make vague statements; they are unfairly difficult for authors to address." (NeurIPS)
- "Honestly reported limitations should be treated kindly." (CoRL)
- "Results must convince a duly skeptical critical scientist." (IJRR)
- "What would the authors have to do for you to increase your score?" (NeurIPS 2019)
- "Being too lenient produces poor scholarship; excessive criticism blocks legitimate research." (Smith)
