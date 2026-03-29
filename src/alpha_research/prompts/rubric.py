"""Shared rubric definitions as structured text strings.

These are the actual evaluation criteria extracted from:
  - research_guideline.md Appendix B (B.1-B.7)
  - review_guideline.md §6.1-6.5
  - research_guideline.md §2.2 (significance tests)
  - review_guideline.md §3.1-3.6 (attack vectors)

Used by both the research and review system prompts.
"""

# ---------------------------------------------------------------------------
# Research Rubric — Appendix B of research_guideline.md
# ---------------------------------------------------------------------------

RESEARCH_RUBRIC: str = """\
## Paper Evaluation Rubric (research_guideline.md Appendix B)

### B.1 Significance and Problem Definition (Weight: Highest)

| Score | Criteria |
|-------|----------|
| 5 | Problem is demonstrably important (passes Hamming test: important AND has a \
reasonable attack). Task is concrete and well-scoped. Problem is formally defined \
with explicit mathematical structure (objective, variables, constraints). Challenge \
identifies a structural barrier that logically constrains the solution class. The \
approach follows from the challenge. Claims match scope. The contribution can be \
stated as one sentence capturing a deep structural insight. |
| 4 | Task and problem are clear. Problem significance is argued but not fully \
compelling. Problem has some formal structure. Challenge is articulated but could be \
deeper -- the link from challenge to approach is present but not fully convincing. |
| 3 | Task is defined but significance is assumed rather than argued. Problem is \
described in prose without formalization ("X is challenging"). Challenge is asserted \
rather than analyzed. Approach is motivated but not by structural insight. |
| 2 | Task is clear but significance, problem definition, and challenge are confused \
or absent. Approach seems chosen for novelty rather than because the challenge \
demands it. No formal problem statement. |
| 1 | No clear significance argument. No formal problem definition. Paper solves a \
method looking for a problem. |

### B.2 Technical Approach (Weight: High)

| Score | Criteria |
|-------|----------|
| 5 | Key insight is deep and connects challenge to solution. Exploits problem \
structure (symmetry, decomposition, physics). Explains *why* the approach works. |
| 4 | Sound approach with clear insight. Good use of domain knowledge. |
| 3 | Technically correct but insight is thin. Works but unclear why. |
| 2 | Engineering contribution without conceptual insight. Applies trending method \
without understanding what the task needs. |
| 1 | Technically flawed or trivially combines existing methods. |

### B.3 Experimental Rigor (Weight: High)

| Score | Criteria |
|-------|----------|
| 5 | Real-robot, 20+ trials/condition, confidence intervals, strong baselines \
(including simple), ablations isolating contributions, failure analysis with taxonomy, \
perturbation tests. Transparent about setup effort. |
| 4 | Real-robot, 10+ trials, good baselines, meaningful ablations, some failure \
analysis. |
| 3 | Real-robot but <10 trials, or baselines not tuned, or ablations don't isolate \
contribution. No failure analysis. |
| 2 | Sim-only for a real-world problem. Or: real-robot but 3-5 trials, weak \
baselines, no ablations. |
| 1 | Evaluation doesn't support claims. Cherry-picked, no statistics, strawman \
baselines. |

### B.4 Representation and Sensing (Weight: Medium)

| Score | Criteria |
|-------|----------|
| 5 | Representation motivated by specific task/challenge requirements. Appropriate \
sensing modalities. Compared against alternatives. |
| 4 | Good choice with justification. Acknowledges sensing limitations. |
| 3 | Default choice (RGB for everything) without justification. |
| 2 | Clearly mismatched (no depth for 3D reasoning, no force for contact). |
| 1 | Actively harmful to method's goals. |

### B.5 Generalization and Compositionality (Weight: Medium)

| Score | Criteria |
|-------|----------|
| 5 | Generalization across objects, environments, conditions. Composes with other \
skills. Tested beyond training distribution. |
| 4 | Good generalization with clear scope. Some compositional capability. |
| 3 | Limited tests. Single environment or narrow objects. No compositionality. |
| 2 | Only training distribution. No generalization evidence. |
| 1 | Overfits to specific setup. |

### B.6 Practical Viability (Weight: Medium)

| Score | Criteria |
|-------|----------|
| 5 | Real-time, reasonable hardware, data-efficient, failure recovery, clear \
deployment path. |
| 4 | Practical with acknowledged limitations. |
| 3 | Impractical for deployment but reasonable for research. Limitations noted. |
| 2 | Impractical, limitations unacknowledged. |
| 1 | Cannot run in real-time, prohibitive requirements, no practical path. |

### B.7 Clarity and Reproducibility (Weight: Low-Medium)

| Score | Criteria |
|-------|----------|
| 5 | Clear writing. Reimplementable. Code + data released. Physical setup documented. |
| 4 | Clear. Most details present. Code released. |
| 3 | Understandable but missing key details. No code. |
| 2 | Confusing. Critical details missing. |
| 1 | Cannot understand the method from the paper. |
"""

# ---------------------------------------------------------------------------
# Review Rubric — review_guideline.md §6.1-6.5
# ---------------------------------------------------------------------------

REVIEW_RUBRIC: str = """\
## Review Rubric (review_guideline.md §6.1-6.5)

### 6.1 Significance and Problem Definition (Gate Dimension)

This dimension GATES the review. A score of 1-2 here means the paper fails \
regardless of other dimensions.

| Score | Criteria | Verdict Implication |
|-------|----------|---------------------|
| 5 | Passes Hamming, Consequence, and Durability tests. Problem is formally defined \
with exploitable structure. Challenge is structural and constrains solution class. \
Contribution statable as one-sentence insight. | Proceed to full review |
| 4 | Significance argued but not fully compelling. Some formalization. Challenge \
present but could be sharper. | Proceed; flag significance as discussion point |
| 3 | Significance assumed, not argued. No formalization. Challenge asserted, not \
analyzed. | Serious weakness; likely reject at IJRR/RSS/CoRL. May survive at \
ICRA/IROS if execution is strong. |
| 2 | No clear significance. No formal problem. Approach chosen for novelty, not \
problem structure. | Fatal flaw at any venue. |
| 1 | Method looking for a problem. No task-problem-challenge chain. | Reject. |

### 6.2 Technical Approach

| Score | Criteria |
|-------|----------|
| 5 | Deep insight connecting challenge to solution. Exploits formal structure. \
Explains *why* it works, not just *that* it works. |
| 4 | Sound approach with clear insight. Good domain knowledge usage. |
| 3 | Technically correct but insight is thin. Works but unclear why. |
| 2 | Engineering contribution without conceptual insight. Trending method applied \
without understanding. |
| 1 | Technically flawed, or trivial combination of existing methods. |

### 6.3 Experimental Rigor

| Score | Criteria |
|-------|----------|
| 5 | Real-robot, 20+ trials/condition, confidence intervals, strong baselines \
(including simple and oracle), ablations isolating contribution, failure analysis with \
taxonomy, perturbation tests, human effort reported, cycle time reported. |
| 4 | Real-robot, 10+ trials, good baselines, meaningful ablations, some failure \
analysis. |
| 3 | Real-robot but insufficient trials (<10), or baselines not tuned, or ablations \
don't isolate contribution. No failure analysis. |
| 2 | Sim-only for a real-world problem without justification. Or: real-robot but 3-5 \
trials, weak baselines, no ablations. |
| 1 | Evaluation does not support claims. Cherry-picked results, no statistics, \
strawman baselines. |

### 6.4 Novelty and Positioning

| Score | Criteria |
|-------|----------|
| 5 | Clearly advances the field. Sharp differentiation from prior work. Novel insight, \
not just novel method. |
| 4 | Solid novelty. Good positioning. Some aspects overlap with prior work but clear \
delta. |
| 3 | Incremental advance. Novel combination but unclear if combination yields new \
insight. |
| 2 | Minor variant of existing work. Differentiation is cosmetic. |
| 1 | No novelty. Reproduces known results or applies known method to uninteresting \
new domain. |

### 6.5 Clarity and Reproducibility

| Score | Criteria |
|-------|----------|
| 5 | Crystal clear writing. Method reimplementable from paper. Code + data released. \
Physical setup fully documented. |
| 4 | Clear writing. Most details present. Code available. |
| 3 | Understandable but missing key details. No code release. |
| 2 | Confusing in places. Critical implementation details missing. |
| 1 | Cannot understand the method from the paper. Smith Category 7: "too poorly \
written for technical evaluation." |

### 6.6 Verdict Mapping

The verdict is NOT a function of averaged scores. It is determined by:
1. Are there any fatal flaws? -> If yes, Reject regardless of other scores.
2. Is Significance (6.1) >= 3? -> If no, Reject (the gate dimension).
3. How many serious weaknesses? -> 3+ serious weaknesses with no clear fix path -> Reject.
4. Do the strengths outweigh the weaknesses? -> Favor slightly flawed impactful work \
over perfectly executed low-impact work.
5. Venue calibration -> Apply venue-specific thresholds.
"""

# ---------------------------------------------------------------------------
# Significance Tests — research_guideline.md §2.2
# ---------------------------------------------------------------------------

SIGNIFICANCE_TESTS: str = """\
## Significance Tests (research_guideline.md §2.2)

Apply ALL of the following as an executable checklist before committing to a problem.

### The Hamming Test (necessity)

1. **Can you name 10-20 important unsolved problems in your field?** If you can't, \
you don't know your field well enough to select a problem. Great researchers maintain \
a running list.

2. **Is there a reasonable attack?** Importance requires BOTH (a) the solution would \
matter AND (b) you can see a viable path. This filters out both trivial problems and \
grand-but-intractable ones.

3. **Would solving this generate MORE interest over time, not less?** (Patterson) \
Problems that become less interesting as the field evolves are bad bets.

### The Consequence Test (impact)

4. **If you magically solved this overnight, what changes?** Be concrete. "Other \
researchers would cite us" is NOT an answer. "Robots in warehouses could handle 3x \
more SKU diversity because they could grasp deformable objects" IS an answer.

5. **Would others consider this important?** Not just your advisor -- would \
researchers in adjacent areas care? Would industry practitioners care?

6. **Will it still be worthy in 48 months?** (Eisner) If a bigger model or more data \
will trivially solve it, don't work on it.

### The Portfolio Test (strategy)

7. **Does solving this enable other things?** (Compounding value.) High-value: \
representations that transfer, formal frameworks others build on, data infrastructure, \
safety guarantees. Low-value: task-specific controllers, benchmark tweaks, marginal \
accuracy improvements.

8. **Is this goal-driven or merely idea-driven?** (Schulman) Idea-driven: "I'll \
improve diffusion policies by adding X." Goal-driven: "I want robots to assemble \
furniture, and the bottleneck is Y, which suggests Z." Goal-driven research is more \
motivating, more differentiated, and more likely to produce genuine contributions.
"""

# ---------------------------------------------------------------------------
# Attack Vectors — review_guideline.md §3.1-3.6
# ---------------------------------------------------------------------------

ATTACK_VECTORS: str = """\
## Attack Vectors for Adversarial Review (review_guideline.md §3.1-3.6)

### 3.1 Attacking Significance ("So What?" test)

| Attack Vector | What to Check |
|---------------|---------------|
| **Hamming failure** | Is this an important problem? Can you independently articulate \
why this matters beyond the paper's own claims? If removed from the field, would \
anything change? |
| **Consequence failure** | If this were magically solved overnight, what concretely \
changes? "Others would cite us" is NOT an answer. |
| **Durability failure** | Will a bigger model, more data, or better hardware \
trivially solve this in 24 months? Is the problem being made obsolete by scaling? |
| **Compounding failure** | Does solving this enable other research? Or is it a dead \
end -- a task-specific controller, a benchmark tweak? |
| **Goal vs. idea driven** | Is this "I have method X, let me find a problem for it" \
or "Problem Y is important, and the bottleneck suggests method X"? |
| **Concurrent work test** | Has this been solved (or nearly solved) by concurrent \
work? Does the paper compare against the most recent relevant work? |

### 3.2 Attacking Formalization ("Where's the Math?" test)

| Attack Vector | What to Check |
|---------------|---------------|
| **Absent formalization** | Is the problem stated as math (optimization, estimation, \
decision) or only as English prose? |
| **Wrong framework** | Is the formal framework appropriate? (e.g., MDP when the \
problem has partial observability -> should be POMDP) |
| **Missing structure** | Does the formalization reveal exploitable structure \
(convexity, symmetries, decomposability)? Or does it just dress up an ad-hoc method \
in notation? |
| **Trivial special case** | Does formalization reveal this is a special case of an \
already-solved general problem? |
| **Assumption audit** | Are the mathematical assumptions realistic? Are they stated? \
What breaks if they don't hold? |
| **Formalization-reality gap** | Does the math match what the system actually does? \
Or is there a gap between the formal objective and the implemented loss/reward? |

### 3.3 Attacking the Challenge ("Why is This Actually Hard?" test)

| Attack Vector | What to Check |
|---------------|---------------|
| **Resource complaint** | Is the stated challenge "we need more data / compute / \
time"? That's a resource constraint, not a structural barrier. |
| **Challenge-approach disconnect** | If someone understood only the challenge, would \
they predict the method class? If not, the challenge doesn't constrain the solution. |
| **Challenge misidentification** | Does empirical evidence actually support the \
claimed challenge? If the paper says "the challenge is sample complexity" but the \
method uses only 100 demos and works, the real challenge was something else. |
| **Pre-solved challenge** | Has this specific structural barrier been addressed by \
prior work? Is the paper fighting a battle already won? |
| **Depth test** | Is the challenge analysis deep enough to constrain the solution \
class to a specific family? Or is it vague enough that any method could claim to \
address it? |

### 3.4 Attacking the Approach ("Does This Follow?" test)

| Attack Vector | What to Check |
|---------------|---------------|
| **Method-shopping** | Was the method chosen because it's trendy/novel, or because \
the challenge demands it? Could you substitute a different trendy method and the paper \
would read the same? |
| **Trivial variant** | Is this approach functionally equivalent to an existing method \
with cosmetic differences? |
| **Structure exploitation** | Does the approach exploit the formal structure the \
paper identified? Or does it ignore the structure and use a generic method? |
| **Wrong mechanism** | Does the approach actually address the stated challenge, or \
does it succeed for a different reason? (Detected by ablation.) |
| **Theoretical justification gap** | Can the authors formally state what their method \
solves? Or does it work empirically but they can't write the math of WHY? |

### 3.5 Attacking Validation ("Does the Evidence Support the Claims?" test)

#### 3.5.1 Experimental Design

| Attack Vector | What to Check |
|---------------|---------------|
| **Baseline strength** | Are baselines genuinely strong? Tuned? Include \
simple/scripted baselines? Include the strongest known prior method? |
| **The missing baseline** | What is the strongest baseline the paper didn't compare \
against? This is often the most devastating finding. |
| **Ablation isolation** | Do ablations isolate the claimed contribution? If you \
remove the paper's "key innovation," does performance actually drop? |
| **Statistical sufficiency** | Number of trials per condition (minimum 10, preferably \
20+ for stochastic policies). Confidence intervals. Random seeds. Variance across \
runs. |
| **Evaluation-claim alignment** | Do the experiments actually test the paper's stated \
contribution? Or do they test something adjacent? |
| **Cherry-picking detection** | Are results selectively reported? Are failure cases \
shown? Is there a failure mode taxonomy? |
| **Human effort hiding** | How much human effort goes into the system? Demonstrations, \
calibration, tuning, manual resets? Is this reported? |

#### 3.5.2 Robotics-Specific Experimental Standards

| Attack Vector | What to Check |
|---------------|---------------|
| **Sim-only for real claims** | Does the paper claim real-world applicability but only \
validate in simulation? |
| **Single-embodiment generality** | Does the paper claim generality from experiments \
on a single robot? |
| **Contact gap** | For contact-rich tasks: is contact modeled? Is sim-to-real \
transfer for contact dynamics addressed? |
| **Sensing mismatch** | Is the sensing modality appropriate for the information the \
task requires? |
| **Environment simplification** | Is the environment artificially simplified in ways \
that obscure the real challenge? |
| **Failure severity** | Does the paper report failure severity, not just failure rate? |
| **Reproducibility** | Is the physical setup described in enough detail to reproduce? |
| **Cycle time and deployment gap** | Can the method run in real-time? Is there a \
realistic deployment path? |

#### 3.5.3 Overclaiming Detection

| Pattern | What It Looks Like |
|---------|--------------------|
| **Generality overclaim** | "Our method works for manipulation" -- tested on 3 \
objects in 1 environment on 1 robot. |
| **Novelty overclaim** | "We propose a novel framework for X" -- a known method \
applied to a new task. |
| **Contribution overclaim** | "We solve the contact problem" -- improved performance \
on one contact-rich task. |
| **Comparison overclaim** | "Our method outperforms all baselines" -- not tested on \
metrics where baselines might win. |
| **Learning overclaim** | "The robot learns to ..." -- the robot executes a policy \
trained on ... |
| **Robustness overclaim** | "Robust to ..." -- tested with 3 perturbation types. |

### 3.6 Attacking Novelty ("Compared to What?" test)

| Attack Vector | What to Check |
|---------------|---------------|
| **Prior work overlap** | Is there existing work that solves essentially the same \
problem with the same approach? |
| **Incremental engineering** | Is the contribution a structural insight, or is it \
incremental engineering (better hyperparams, bigger model, more data)? |
| **Missing related work** | Are there highly relevant papers the authors appear \
unaware of? |
| **Novelty vs. insight** | Is the method novel but without insight (no deeper \
understanding of WHY this works)? |
| **Combination vs. contribution** | Is this a novel combination of known techniques? \
If so, does the combination yield insight beyond the sum of parts? |
"""
