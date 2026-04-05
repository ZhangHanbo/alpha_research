# Research Guidelines for Robotics

A guide for doing robotics research that actually moves the field — calibrated to the standard of top research, not average research. Written against how the field's best researchers (Levine, Tedrake, Abbeel, Finn, Kaelbling, Rus, Fox, Todorov, Goldberg, Bohg, Song, Pinto, Pavone, Agrawal, Zeng) actually think, and informed by the research philosophy of Hamming, Schulman, Patterson, Peyton Jones, and Olah on what separates great research from merely competent research.

---

## Part I. What Makes Robotics Research Uniquely Hard

### 1.1 The Embodiment Problem

The same algorithm behaves differently on different robots. A policy trained on a Franka Panda does not transfer to a UR5, even for the "same" task:

- **Kinematic structure changes the reachable set.** A 7-DOF arm has a null space; a 6-DOF arm does not. Your algorithm's null-space behavior may be load-bearing without you realizing it.
- **Actuator dynamics are part of the policy.** Position-controlled and torque-controlled arms respond to the same trajectory fundamentally differently. Joint friction, backlash, and cable stretch are features your algorithm implicitly learns to exploit.
- **Sensor configurations create different observation spaces.** A wrist-mounted camera and an external camera see different occlusion patterns. Your "visual policy" is a policy for *that specific viewpoint*.
- **Control frequency and latency are embodiment-specific.** A policy at 10Hz on a compliant arm may be dangerous at 10Hz on a stiff robot.

**What this means:** Never claim generality from a single robot. If your method works on one robot, the interesting question is *why* it doesn't work on another. Understand what transfers (semantic understanding) and what doesn't (motor commands). The Open X-Embodiment project showed cross-embodiment transfer is possible but requires careful action space normalization and observation alignment.

### 1.2 The Contact Problem and Multimodal Sensing

Contact is where robotics fundamentally diverges from ML and controls. Grasping, assembly, tool use, locomotion — all involve making and breaking contact.

**Why contact is so hard:**

- **Hybrid dynamics.** Contact introduces discontinuous constraint switches. Most optimization and learning methods assume smoothness; contact violates this.
- **The complementarity problem.** Contact forces and gaps are complementary (zero gap ↔ nonzero force). This mathematical structure (Todorov/MuJoCo, Posa/contact-implicit optimization) is fundamentally different from standard constrained optimization.
- **Friction is discontinuous and uncertain.** Static/kinetic transitions, stick-slip — poorly modeled, critically important.
- **Sim-real divergence is worst at contact.** Every simulator approximates contact differently. None are accurate for contact-rich tasks.

**The sensing gap at contact:**

Vision alone is insufficient for contact-rich manipulation:

- **Tactile sensing** (GelSight, DIGIT, ReSkin) provides contact geometry, force distribution, and slip — information cameras cannot observe. Agrawal's MIT work shows tactile feedback enables insertion, in-hand rotation, and texture discrimination that vision-only cannot achieve.
- **Force/torque sensing** provides aggregate contact wrench. Essential for compliant manipulation and assembly. Impedance/admittance control (Schaal, Billard) depend on force feedback.
- **Proprioception** — joint positions, velocities, currents — contains contact state information (unexpected resistance = contact) that complements external sensing.
- **Sensor fusion** is not "concatenate features." Different modalities have different latencies, noise, and information content. The right fusion depends on the task.

### 1.3 Physical Irreproducibility

Two "identical" runs differ: gripper wear, thermal expansion, calibration drift, object tolerances, environmental factors. Report confidence intervals. Describe setups in enough detail to diagnose reproduction failures. Include failure mode sections.

### 1.4 The Safety and Cost Constraint

Your bug can break a $100K robot or injure someone. Conservative behaviors dominate published research (systematic bias). Recovery matters as much as performance. Report failure *severity*, not just rate.

### 1.5 The Long Tail of the Physical World

"Pick up a mug" has combinatorially many physical configurations. Be honest about your evaluation distribution. The most valuable research characterizes the *specific mechanisms* by which methods fail on distribution tails (Goldberg's Dex-Net approach).

---

## Part II. From Task to Approach: How Top Researchers Think

This is the most important part of this document. The single most valuable skill in research is the ability to move from "I want robots to do X" to "This matters because W, the precise problem structure is Y, the fundamental barrier is Z, which suggests solution class Q." Every strong paper from every top group follows this chain. Most weak papers skip steps — and the step most commonly skipped by average researchers is asking whether the problem is important at all, and whether they can formalize it precisely enough to reason about it.

### 2.1 The Thinking Chain

```
SIGNIFICANCE → TASK → PROBLEM DEFINITION → CHALLENGE → WHY NOW → APPROACH → SCOPE
     ↑                                                                        |
     └──────────────── failures reveal new tasks ────────────────────────────┘
```

**Significance:** Why does this matter? Who cares, and why should they?
**Task:** What should the robot do, concretely, in the physical world?
**Problem Definition:** What is the precise formal structure of the problem? Can you write it as math?
**Challenge:** Why does the problem resist current solutions — what is the fundamental structural barrier?
**Why Now:** What has changed that makes this solvable today?
**Approach:** What solution class does the challenge structure suggest?
**Scope:** What exactly are you claiming, and what are you not?

Each step is distinct. Confusing them is the most common source of weak research. But note the new first step: **Significance comes before everything.** The most common failure mode of average research is not technical weakness — it is working on problems that don't matter, no matter how well executed.

### 2.2 The Significance Test (Is this worth doing?)

This is the step most average researchers skip entirely. They jump to "what's the task?" without first asking "does this matter?" Richard Hamming, in his famous "You and Your Research" talk, put it bluntly:

> *"If what you are doing is not important, and if you don't think it is going to lead to something important, why are you working on it?"*

But "important" is not a feeling. It is testable. Here are **executable standards** — apply them as a checklist before committing to a problem:

#### The Hamming Test (necessity)

1. **Can you name 10-20 important unsolved problems in your field?** If you can't, you don't know your field well enough to select a problem. Great researchers maintain a running list of important problems and watch for when new tools or insights create an opening.

2. **Is there a reasonable attack?** Importance requires both (a) the solution would matter AND (b) you can see a viable path. "General manipulation in unstructured environments" would matter if solved, but it is not an "important problem" right now because there is no viable attack. This filters out both trivial problems and grand-but-intractable ones.

3. **Would solving this generate MORE interest over time, not less?** (Patterson) Problems that become less interesting as the field evolves are bad bets. Sim-to-real for rigid pick-and-place is becoming less interesting as foundation models improve. Contact-rich manipulation under uncertainty is becoming more interesting as we push toward harder tasks.

#### The Consequence Test (impact)

4. **If you magically solved this overnight, what changes?** Be concrete. "Other researchers would cite us" is not an answer. "Robots in warehouses could handle 3x more SKU diversity because they could grasp deformable objects" is an answer. If you can't name a concrete downstream consequence, the problem may not be important.

5. **Would others consider this important?** (Patterson, Eisner) Not just your advisor — would researchers in adjacent areas care? Would industry practitioners care? If the answer is only "people who work on exactly this sub-sub-field," the problem is likely too narrow.

6. **Will it still be worthy in 48 months?** (Eisner) If a bigger model or more data will trivially solve it, don't work on it. The most important problems are those that resist scaling and require structural insight.

#### The Portfolio Test (strategy)

7. **Does solving this enable other things?** (Compounding value from §5.1 Axis 4.) High-value: representations that transfer, formal frameworks others can build on, data infrastructure, safety guarantees. Low-value: task-specific controllers, benchmark tweaks, marginal accuracy improvements.

8. **Is this goal-driven or merely idea-driven?** (Schulman) Idea-driven: "I'll improve diffusion policies by adding X." Goal-driven: "I want robots to assemble furniture, and the bottleneck is Y, which suggests Z." Goal-driven research is more motivating, more differentiated, and more likely to produce genuine contributions. The goal provides a filter that idea-driven research lacks.

**The average researcher pattern** (Hamming): spends almost all their time on problems they believe will not be important and that will not lead to important problems. They are technically competent but strategically blind. **Great Thoughts Time:** Dedicate 10% of your time (e.g., Friday afternoons) to stepping back and asking: "What are the most important problems in my field? Am I working on one?"

### 2.3 Define the Task (What should the robot do?)

The task definition is itself a research decision. It determines your scope, your evaluation, and your audience.

**Too broad:** "Manipulation in unstructured environments." You cannot make progress on everything simultaneously. You cannot evaluate this — what counts as success?

**Too narrow:** "Picking up red mugs from white tables." You'll solve it, but no one will care because it doesn't generalize and the insights don't transfer.

**Right scope:** "Contact-rich assembly of rigid objects without CAD models." Specific enough to evaluate. Broad enough to matter. The constraints (contact-rich, no CAD) define the interesting challenge space.

**How top researchers define tasks:**
- Levine's lab consistently defines tasks as *capability classes* with clear physical grounding: "learning dexterous manipulation from human video," "offline RL for real-world robotics."
- Tedrake defines tasks by their *dynamical character*: "stabilization of underactuated systems," "manipulation through contact."
- Kaelbling defines tasks by their *planning structure*: "long-horizon manipulation under partial observability."
- Song defines tasks by their *physical interaction type*: "tool use," "deformable manipulation."

The task definition tells you what kind of researcher you are, what community you're contributing to, and what evaluation will be convincing.

### 2.4 Define the Problem (What is the precise structure?)

**This is not about "what fails." This is about understanding what the problem IS.**

The previous version of this section focused on diagnosis — watching things fail and identifying bottlenecks. That remains important (see §2.5), but it is the second step. The first step is **formal problem definition**: stating the problem with enough precision that you (and others) can reason about it mathematically.

Russ Tedrake's insight is sharp:

> *"What if Newton and Galileo had deep learning and they told the world, here's your weights of your neural network... I don't think we'd be as far as we are. There's something to be said about having the simplest explanation for a phenomenon."*

**If you cannot write the math, you do not understand the problem.** A neural network that "works" is not the same as understanding. A system that succeeds in the lab is not the same as knowing why. The formalization is not a post-hoc documentation step — it IS the research (Simon Peyton Jones: *"Using the paper to do your research"*).

#### Why formalization matters (not just aesthetics)

1. **The formalization constrains the solution class.** Kaelbling: *"There are different ways of framing and formalizing the problem which give you very different computational profiles and different learning strategies."* Choosing POMDP vs. MDP vs. TAMP is not a technical detail — it determines what solutions are even possible. The formalization IS often the contribution.

2. **Formalization reveals structure.** Is the problem convex? Does it have symmetries? What is the effective dimensionality? These properties are invisible without formal statement but determine everything about what methods will work.

3. **Formalization enables rigor at scale.** Tedrake: *"It's precisely because we're trying to build complex systems quickly that I advocate this more rigorous approach."* Counter-intuitive: rigor doesn't slow you down — it enables building more complex systems because components declare their states, parameters, and semantics consistently.

4. **Formalization separates understanding from curve-fitting.** Todorov's 2002 proposal that optimal control is the right framework for biological movement didn't build a better controller — it proposed the right *formalization*, and that became the field's organizing framework for a decade.

#### How to formalize (executable steps)

**Step 1: State the problem as an optimization, estimation, or decision problem.** Every robotics problem is one of these (or a composition). What is the objective? What are the variables? What are the constraints? What information is available?

Example — "robot grasping in clutter" is vague. Formalized: *Given a set of objects O with unknown poses, geometry, and physical properties, find a grasp g ∈ G that maximizes P(success | g, observation) subject to kinematic reachability, collision avoidance, and force closure constraints, where success is defined as stable hold under gravity and expected manipulation forces.* Now you can see the problem: the uncertainty is over object properties, the constraint set is complex, and the objective requires a probabilistic model of grasp success.

**Step 2: Identify what makes THIS problem different from the general case.** What specific structure does your problem instance have? Symmetries? Sparsity? Decomposability? Low effective dimensionality? This is where domain knowledge enters the math.

**Step 3: Check what existing formal frameworks apply — and where they break.** The problem may look like a POMDP, but with continuous observations and infinite horizon, standard POMDP solvers fail. The mismatch between the formal framework and your problem IS the research gap.

**Step 4: Write down what you don't know formally.** Where are the assumptions? What are you sweeping under the rug? The honest gaps in your formalization point directly to the real challenges.

#### The diagnosis step (what fails empirically)

AFTER formalization, build the simplest possible system and run it. Watch it fail. The formal problem definition tells you *what to look for* in the failures:

- Not "grasping fails" but "grasping fails on thin objects because the depth camera cannot resolve edge geometry at this scale" — which in your formalization means the observation model P(z|s) has insufficient information for the relevant state dimensions
- Not "the policy doesn't generalize" but "the visual encoder collapses objects with similar colors despite different shapes" — a representation failure where the learned features are not sufficient for the task
- Not "planning is too slow" but "collision checking dominates and each check requires full forward kinematics" — a computational bottleneck whose structure (repeated evaluation of a known function) suggests amortization

**The most common mistake:** Solving a problem you *assumed* exists rather than one you *observed*. You read that "sim-to-real transfer is a challenge" and work on it — without checking whether sim-to-real is actually the bottleneck for your task. Maybe the real bottleneck is perception.

**The deeper mistake:** Having no formal problem definition at all, so you cannot distinguish between different failure modes or reason about what class of solutions could work. If your "problem statement" is a paragraph of English prose with no math, you are not ready to do research on it.

### 2.5 Analyze the Challenge (Why is it fundamentally hard?)

The challenge is the deep structural reason the problem resists current solutions. This is where research taste lives. A well-articulated challenge should:

1. **Identify a structural barrier**, not just a difficulty. "We need more data" is not a challenge — it's a resource constraint. "The data distribution shifts when the policy changes, creating a non-stationary optimization problem" is a challenge.

2. **Suggest the class of solutions that could work.** If you understand the challenge deeply enough, the solution space narrows dramatically. This is the hallmark of top research: the challenge analysis is so sharp that the approach seems almost inevitable in retrospect.

3. **Distinguish your problem from related problems.** Challenges are specific. The challenge of offline RL (distributional shift) is different from the challenge of sim-to-real (domain gap) even though both involve training/deployment distribution mismatch.

**Examples of challenge → approach from top researchers:**

| Researcher | Challenge | Why it suggests the approach |
|---|---|---|
| Levine (CQL) | Offline RL suffers from value overestimation on out-of-distribution actions because the Q-function is never corrected by real returns for actions the behavior policy didn't take | → Conservative Q-learning: explicitly penalize Q-values for out-of-distribution actions |
| Tedrake (LQR Trees) | A single linear controller's region of verified stability doesn't cover the full nonlinear state space, and we need GUARANTEED coverage | → Grow a tree of linear controllers, each with a verified basin of attraction, until basins tile the space |
| Finn (MAML) | Few-shot adaptation needs fast learning, but gradient descent is inherently slow starting from a random initialization | → Learn the initialization itself, optimizing for the meta-objective that the initialization leads to fast adaptation |
| Kaelbling (TAMP) | Long-horizon planning in continuous state-action spaces is combinatorially intractable even for moderate horizons | → Decompose: plan at the symbolic (discrete) level, ground each step in continuous space, interleave to handle infeasibility |
| Song (tool affordances) | Tool function ≠ tool geometry — a spatula and a flat piece of cardboard can both flip a pancake, but they look nothing alike | → Represent tools by functional affordances (what actions they enable), not geometric features |
| Goldberg (Dex-Net) | Grasp success depends on physical properties (friction, mass, geometry) with high uncertainty, and you can't test every grasp candidate physically | → Analytic grasp quality metric (quasi-static force analysis) + learned grasp-quality CNN trained on massive simulated grasps |
| Pinto (in-the-wild) | Lab-trained policies fail in deployment because the training distribution is artificially narrow (clean backgrounds, consistent lighting, known objects) | → Train in diverse, messy conditions from the start; accept lower peak performance for robustness |
| Agrawal (tactile) | Precision insertion requires sub-millimeter alignment feedback, but vision cannot resolve misalignments below pixel resolution at working distance | → Use tactile sensing (GelSight) which directly measures contact geometry at the required resolution |
| Pavone (safe RL) | Exploration can violate safety constraints, and after-the-fact punishment (negative reward) is too late for irreversible damage | → Control barrier functions: project any proposed action onto the safe set in real-time, guaranteeing constraint satisfaction during learning |

**The pattern:** Each challenge contains a structural insight. The insight constrains the solution to a specific class. The researcher then builds the best instance of that class.

### 2.6 Why Now? (What enables this to be solved today?)

Every good research problem has a timing component. If the challenge could have been addressed 10 years ago, why wasn't it? What changed?

Enablers:
- **Compute:** GPU-accelerated simulation, large-scale policy training
- **Data:** Open X-Embodiment, internet-scale pretraining, shared benchmarks
- **Hardware:** Cheaper robots (low-cost arms), better sensors (commodity depth cameras, tactile sensors)
- **Algorithms:** Diffusion models, transformer architectures, foundation model features
- **Theory:** Contact-implicit optimization, CBF theory, equivariant learning theory

If you can't articulate why your problem is timely, you risk either working on something still intractable (the enablers aren't ready) or something already solved (you missed that someone used the enablers before you).

### 2.7 From Challenge to Approach: The Decision Procedure

Once you understand the challenge, the appropriate method class narrows:

| Challenge type | Suggests method class | Example |
|---|---|---|
| **Sample complexity** (not enough real data) | Better priors: equivariance, physics, sim pretraining, data augmentation | Equivariant grasping (Wang/Platt) |
| **Distribution shift** (train/deploy mismatch) | Robust methods, online adaptation, domain randomization, conservative estimation | CQL (Levine), DR (Tobin) |
| **Combinatorial explosion** (too many possibilities) | Abstraction, decomposition, hierarchy, guided search | TAMP (Kaelbling), skill composition (Konidaris) |
| **Model uncertainty** (physics unknown) | Bayesian methods, ensembles, robust optimization, learning residuals | GP dynamics (Deisenroth), residual RL |
| **Sensing limitation** (can't observe what matters) | New sensors, multi-modal fusion, active/interactive perception | Tactile (Agrawal), interactive perception (Bohg) |
| **Hardware limitation** (mechanism can't do it) | Co-design, compliance, mechanism design | Soft robotics (Rus), leg design (Kim) |
| **Discontinuity** (non-smooth dynamics) | Contact-implicit methods, hybrid system formulations, smoothing | Contact optimization (Posa/Tedrake) |
| **Long-horizon credit** (can't attribute distant failures) | Hierarchical policies, skill primitives, causal reasoning | Options framework (Konidaris), primitives (Schaal) |
| **Grounding gap** (semantic ≠ physical) | Grounded representations, affordances, physics simulators as verifiers | SayCan (Zeng), affordances (Song) |

This table is not exhaustive, and real problems often involve multiple challenge types. But it captures the core decision: **the challenge type determines the method class; within the class, you innovate.**

### 2.8 Scope Your Claims

Top researchers carefully align claims with the specific challenge addressed. They don't claim to solve "manipulation" — they claim to address "the distributional shift problem in offline imitation learning for contact-rich assembly." The specificity of the claim matches the specificity of the challenge.

**Overclaiming** = claims broader than the challenge you addressed.
**Underselling** = claims narrower than the challenge you actually resolved.

Both are errors, but overclaiming is the more common and more damaging one. The checklist at the end of this document starts here: can you state your task, problem, challenge, and contribution scope in one sentence each?

---

## Part III. Mathematical and Theoretical Foundations

The best robotics researchers have deep mathematical intuition. You don't need theorems for every paper, but you *must* understand the mathematical landscape.

### 3.1 Know the Structure of Your Problem

**Is your problem convex?** Many robotics problems are convex or reformulable as convex. If so, you have global optimality guarantees. Using RL to solve a convex problem is wasteful. If non-convex, understand *where* non-convexity comes from — it tells you where to expect local minima.

**What are the symmetries?** SE(3) equivariance in manipulation means a grasp policy should be frame-invariant. Wang, Walters, and Platt show equivariant networks dramatically improve data efficiency. Before training a general network, ask: does this problem have structure I'm forcing it to rediscover?

**What is the dimensionality?** A 7-DOF arm + 16-DOF hand = 46D state. But effective dimensionality is often much lower — tasks constrain the robot to low-dimensional manifolds. Motion primitives (Schaal's DMPs, ProMPs), task-space control, and hand synergies exploit this.

**What are the stability properties?** Lyapunov analysis, force/form closure for grasps. These tell you what your method can guarantee and where it will fail.

**Is there a useful decomposition?** TAMP decomposes into symbolic planning + continuous motion planning. The art is knowing when decomposition is natural vs. forced (Kaelbling, Garrett, Lozano-Pérez).

### 3.2 When Theory Helps and When It Doesn't

Theory helps for guarantees, exploiting structure, debugging, and representation design. Theory hurts when assumptions don't hold, when it substitutes for empirical validation, or when optimizing a theorem diverges from solving the real problem.

**The Tedrake principle:** Theory to understand the landscape. Computation to solve the problem. Experiments to validate. Complementary, not competing.

### 3.3 Optimization as a Unifying Lens

Most robotics problems are optimization. Deep understanding gives you: algorithm selection (smooth → gradient; sparse → ADMM; small → SQP), constraint formulation (dramatically affects solver performance), warm starting (orders-of-magnitude speedups for sequential problems), and cost function design (the cost IS the specification — misspecify it and everything fails).

---

## Part IV. The Representation Question

Representation quality determines the ceiling for everything downstream.

### 4.1 What Makes a Good Representation?

Sufficient (retains task-relevant information), compressive (discards irrelevant), structured (encodes geometric/physical relationships), generalizable (transfers across objects/scenes), and temporally coherent (supports tracking and prediction).

### 4.2 The Landscape in 2026

**Engineered:** Point clouds, pose estimates, keypoints, task-space representations, tactile images.

**Learned:** Foundation model features (CLIP, DINOv2, SigLIP) — rich semantics but encode *what*, not *how to interact*. Action-conditioned (R3M, VIP). 3D-aware (NeRF features). Language-conditioned (CLIP-style grounding). Tactile (learned from touch data, early but critical).

### 4.3 The Representation-Algorithm Interface

Representation and algorithm are coupled. MPC needs prediction-supporting representations. Imitation learning needs smooth demonstration distributions. Grasp planning needs geometric affordances. Don't default to end-to-end from pixels — it pushes all representational burden onto learning.

### 4.4 Foundation Model Features vs. Task-Specific

Use foundation features for broad semantics, zero-shot generalization, limited data. Use task-specific for precision (sub-mm), dynamics, and modalities foundation models lack. The hybrid approach — foundation semantics + task-specific geometry/tactile — is where the field is heading.

### 4.5 Affordances and Interactive Perception

**Affordances** = representations of what actions an object *permits*. Not "this is a mug" but "this rim can be grasped from above; this handle affords a lateral grasp." (Song, Zeng's spatial action maps.) Affordances bridge perception and action at the representation level.

**Interactive perception** = perception and action are interleaved, not sequential. Robots often must act to perceive: push to reveal occluded objects, grasp to estimate mass. Bohg's formalization: choose actions maximizing both task progress and information gain. If your pipeline assumes full observability from one viewpoint, it's wrong for cluttered/occluded scenes.

---

## Part V. Problem Selection — A Decision Framework

This operationalizes the thinking chain from Part II.

### 5.1 The Five-Axis Evaluation

After you have a candidate problem (a significance-task-problem-challenge chain), evaluate it:

**Axis 0: Significance.** Apply the Hamming/Consequence/Durability tests from §2.2. Is this important? Does it have a reasonable attack? Would solving it change something concrete? Will it still matter in 48 months? *This axis gates all others — if the answer is no, stop here.*

**Axis 1: Bottleneck Diagnosis.** Is this the *actual* bottleneck? If you magically solved this, would the system improve? Build the simplest system and watch what actually fails.

**Axis 2: Decomposability.** Can you isolate a testable hypothesis? Hold most constant, vary one thing, have a clear metric.

**Axis 3: Capability Frontier.** Is this at the edge?
- **Reliable:** Pick-and-place of rigid objects. Language-conditioned foundation model manipulation.
- **Sometimes:** Deformable manipulation. Tool use. Multi-step with recovery. In-hand dexterity. Bimanual. Tactile-guided insertion.
- **Can't yet:** General unstructured manipulation. Transparent/reflective objects. Contact-rich with force reasoning at scale. Long-horizon physical causal reasoning. Human-level dexterity.

**Axis 4: Compounding Value.** Does solving this enable other things? High: formal frameworks others build on, representations that transfer, data infrastructure, safety guarantees. Low: task-specific controllers, benchmark tweaks, marginal accuracy improvements.

### 5.2 The Process

**Week 1-2: Survey + Significance Screen.** Read 2 years of best papers from CoRL, RSS, ICRA, IROS. For each: "Task X, Problem Y, Challenge Z, Contribution W." Track what the strongest groups are moving toward. Simultaneously: apply the Significance Test (§2.2) to your candidate problems. Maintain your Hamming list (10-20 important unsolved problems). Eliminate candidates that fail Axes 0 of the Five-Axis Evaluation.

**Week 3-4: Formalize + Minimal system.** For surviving candidates: write formal problem definitions (§2.4). State the problem as math — objective, variables, constraints, information structure. Identify mathematical structure. Build the simplest possible end-to-end system and run it. Watch it fail. The formal definition tells you what to look for in the failures.

**Week 5-6: Hypotheses.** 2-3 specific, testable claims about *why* current approaches fail and *what* would fix them. Each hypothesis must reference the formal problem structure — e.g., "failure occurs because the optimization landscape is non-convex in region X, and local minima correspond to Y." Each testable in 2-4 weeks.

**Week 7-10: Test.** Run experiments. Analyze honestly. Apply the One-Sentence Test: can you state what you found as one sentence capturing a deep structural insight?

---

## Part VI. The Core Tensions

### 6.1 Structure vs. Learning

**How to decide** (this flows from challenge analysis):
- If the challenge is *sample complexity* → inject structure (equivariance, kinematics, physics)
- If the challenge is *model accuracy* → learn (the analytical model's errors may be worse than learning from scratch)
- If the challenge is *generalization across tasks* → use structure for what's invariant (physics), learn what varies (task specifics)
- If the challenge is *safety/guarantees* → structure is non-negotiable (CBFs, Lyapunov, constrained optimization)

**Skill primitives** (Schaal's DMPs, Kroemer's manipulation primitives, Konidaris's options) are the principled middle ground. Each primitive is simple enough to learn reliably; composition provides complexity. Movement primitives with impedance profiles (Billard) encode interaction strategies — how to respond to contact forces during execution.

### 6.2 Simulation vs. Reality

Sim for development/debugging, not final claims. Sim for hypothesis testing — can you reproduce real failures in sim? The sim-real gap is data: characterizing which tasks transfer and why is high-value research. Domain randomization helps visual transfer; can hurt physics transfer if unrealistic.

### 6.3 The Foundation Model Shift and LLMs in Robotics

**Foundation models for control (RT-2, Octo, pi0, OpenVLA):** Basic pick-and-place is commoditized. Zero-shot generalization is a baseline, not a contribution. The frontier is what foundation models can't do: contact-rich tasks, force control, deformable manipulation, long-horizon physical reasoning.

**LLMs/VLMs as robot reasoning engines — a distinct paradigm:**

- **LLM-as-planner** (SayCan, Inner Monologue): LLM provides semantic reasoning; skills provide physical grounding. Limitation: LLM has no physical intuition — doesn't know whether "slide the plate" is feasible or what forces it needs.
- **Code-as-policy** (Zeng): LLM generates executable robot code. Powerful for compositional tasks. Limitation: assumes clean API to reliable primitives.
- **VLM-as-reward**: VLMs evaluate task completion for autonomous improvement. Promising but noisy — VLMs hallucinate success.
- **LLM-as-world-model**: Most speculative. LLMs capture correlational physical knowledge ("glass breaks when dropped") but lack causal physical reasoning (fracture mechanics).

**Critical assessment:** LLMs provide *semantic* reasoning (what to do, in what order) but not *physical* reasoning (how, with what forces, along what trajectory). The research opportunity: characterize exactly what physical reasoning LLMs have and lack, build grounding mechanisms, design interfaces between semantic planning and physical execution.

### 6.4 Hardware-Software Co-Design

Morphology is computation. Kim's Cheetah runs because the hardware stores/releases energy. Compliant grippers grasp without sensing. Over-actuated hands make learning hard; simpler hands with compliance can perform better. If different hardware makes your problem trivial, the insight is hardware, not algorithm.

### 6.5 Data and the Scaling Question

Data efficiency is a first-class constraint. The scaling hypothesis (more data → better) has evidence (RT-2, Open X, pi0) but also reasons for caution: physical interaction data has different structure than text, actions are embodiment-specific, long-tail scenarios may need exponential data, and unit economics are 1000x worse than web data.

Investigate which sources carry which information: internet video has semantics but no forces; sim has state but wrong physics; teleoperation has correct physics but limited diversity. Contribute datasets.

### 6.6 Compositionality and Long-Horizon Reasoning

Most real tasks are sequences where intermediate states matter and errors compound. 95% per-step accuracy = 36% over 20 steps.

**Why it's qualitatively harder:**
- Credit assignment over time (was the error at step 15 or step 3?)
- Compounding errors
- Need for abstraction (can't plan 20 steps in joint-space — Kaelbling's TAMP)
- Belief-space planning (Kaelbling): reason about actions that are *informative* alongside actions that are *productive*

**The compositionality principle:** Compose known skills into novel combinations rather than train on every combination. Skill libraries + task planning + the interface problem (how does the planner know which skills are feasible? how do termination conditions feed into preconditions?). Garrett's PDDLStream and Konidaris's learned abstractions address the interface.

---

## Part VII. Learning Dynamics and Policy Design

### 7.1 Reward and Objective Design

Reward is the specification — and specifications are wrong the first time. Sparse rewards are "correct" but create exploration problems. Dense rewards speed learning but inject assumptions. Watch for physical reward hacking. Start sparse + good resets; add curriculum; add shaping last and verify.

### 7.2 Distribution Shift and the Deployment Gap

Your policy changes its data distribution. At deployment: objects differ, conditions drift, errors compound.

**What changes between 100 lab trials and 10,000 production executions** (per Pinto, Goldberg): rare failures become weekly at scale; resets are free in the lab, expensive in deployment; environmental variation is controlled in the lab, not in production; monitoring (detecting degradation) becomes critical.

Design for graceful degradation. Closed-loop execution is not optional.

### 7.3 Imitation Learning Design

- **Action representation:** Relative task-space generalizes better; absolute joint-space is more precise. Diffusion policies and action chunking handle multimodal distributions.
- **Demonstration quality:** 50 diverse > 500 narrow. Diversity in conditions and strategies matters more than volume.
- **Multimodality:** If demos contain multiple strategies for the same situation, MSE loss averages them (→ fails). Diffusion policies, mixture models address this. If you're using BC without thinking about multimodality, you have a hidden bug.

### 7.4 Safe Exploration

Beyond kill switches — formal frameworks:
- **Control Barrier Functions (CBFs):** Define safe set, guarantee the system stays in it. Compose with learned controllers. (Pavone, Ames)
- **Constrained MDPs:** RL with explicit safety constraints via Lagrangian or constrained policy optimization.
- **Reachability-based safety:** Only explore states from which safe recovery is possible.
- **Curriculum as safety:** Start safe and simple, gradually increase difficulty.

---

## Part VIII. Evaluation

### 8.1 What Metrics Matter

Success rate is necessary, not sufficient. Also: task completion time, failure severity, generalization scope (list objects/environments), inference time/compute, human effort (demos, calibration, tuning), perturbation robustness, and failure mode taxonomy (categorize as perception/planning/execution/physics error).

### 8.2 Baselines

Always include simple baselines (scripted, PID). Make them strong — tune hyperparameters, use best implementations. Include oracle baselines (perfect perception, perfect dynamics) to identify bottlenecks.

### 8.3 Reproducibility

Sim evaluation as reproducibility floor. Release code (full pipeline), data (demos, evaluations, objects), and documentation (cameras, mounting, calibration, URDF, gripper). Report variance across seeds and runs.

---

## Part IX. Research Execution

### 9.1 Monthly Cycle

**Months 1-2:** Survey → minimal system → hypotheses. Deliverable: 1-page task/problem/challenge/hypothesis/evaluation statement.

**Months 3-5:** Core experimentation. Transfer to real hardware early. Update hypotheses weekly.

**Months 6-8:** Strong baselines, ablations, expanded evaluation, address failure modes.

**Months 9-10:** Write. Writing clarifies thinking. Fill gaps writing reveals.

### 9.2 Weekly Rhythms

Velocity = experiments per week, not lines of code.

Monday: review, update hypotheses, plan. Tue-Thu: run experiments (40%+ at the robot). Friday: analyze, write research log.

The log is non-negotiable: what you tried, expected, observed, concluded, what's next.

### 9.3 Pivot vs. Push Through

**Pivot:** Hypothesis disproven (no reformulation). Problem solved by others. 6+ weeks stuck, no new insight. Bottleneck shifted.

**Push through:** Failures are informative. You can articulate specifically what's not working. Core hypothesis has partial evidence. Others working on it (important problem).

---

## Part X. Writing Papers

### 10.1 Structure

**Intro:** Why the task matters (for outsiders) → why it's hard (the specific challenge, not vague hand-waving) → your approach (the insight connecting challenge to solution) → results (concrete numbers).

The intro should make the task→problem→challenge→approach chain crystal clear. A reader should know after the intro: what task, what fails today, what the fundamental barrier is, and what structural insight your approach exploits.

**Related work:** By approach type. What each approach gets right and wrong. Where yours fits.

**Method:** Reimplementable from this section. Non-obvious choices explained (WHY, not just WHAT).

**Experiments:** Structure as questions: main comparison, ablations, failure analysis, generalization. **Failure analysis separates good papers from great papers.**

### 10.2 Common Mistakes

- Overclaiming generality (claims broader than your challenge scope)
- Insufficient trials (<10 per condition)
- Hiding human effort
- Weak baselines
- Ignoring cycle time
- Cherry-picked demos
- No ablation on the claimed contribution
- Confusing the task with the challenge (solving "manipulation" ≠ addressing a specific structural barrier)

---

## Part XI. The Mindset

### 11.1 Systems Thinking

Levine thinks about how data collection shapes learning shapes policy shapes data distribution. Tedrake thinks about optimization landscapes. Finn thinks about task distribution structure. Kaelbling thinks about what abstractions make problems tractable. Trace decisions through the full system.

### 11.2 Taste — The Trainable Skill That Separates Top from Average

Research taste is not innate. It is trainable through deliberate practice (Schulman, Chris Olah). But it requires *active* cultivation, not passive exposure.

**What taste IS:** The ability to distinguish:
- Genuine insight vs. lucky hyperparameters
- Fundamental limitation vs. engineering problem
- 5-year result vs. 6-month result
- A formalization that reveals structure vs. one that just dresses up an ad-hoc method

**The deepest form of taste:** Seeing a challenge and knowing what class of solutions it admits. This comes from understanding many challenge→approach mappings (§2.5-2.7) and recognizing when a new problem shares structure with a solved one.

#### Executable exercises for developing taste (do these regularly)

1. **The Hamming Exercise (weekly).** Maintain a list of 10-20 important unsolved problems in your field. Update it monthly. For each, note what "reasonable attack" would look like. Watch for when new tools/insights create an opening. Dedicate Friday afternoons to this.

2. **The Prediction Exercise (per paper).** Before reading a paper's method section, read only the problem statement and challenge analysis. Predict what class of solution they'll propose. If your prediction is wrong, understand why — either your understanding of the challenge was incomplete, or the authors made a non-obvious connection.

3. **The Survival Exercise (monthly).** Read papers from 10 years ago in your area. What survived? Structural truths (convexity, symmetry, decomposition principles) survive. Specific algorithms don't. Train yourself to recognize which parts of today's papers are structural and which are ephemeral.

4. **The Formalization Exercise (per project).** Take a problem you're working on. Write three different formal problem definitions (e.g., as MDP, as constrained optimization, as Bayesian inference). Each yields a different solution landscape. Which formalization makes the problem most tractable while preserving the essential difficulty? This IS the research decision.

5. **The Breaking Exercise (per paper/project).** Try to break your own method. Find the simplest case where it fails. Diagnose whether the failure is fundamental (structural limitation of the approach) or incidental (fixable engineering). If fundamental, the failure points to the next research problem.

6. **Chris Olah's Calibration Exercise.** Write down your research ideas. Have a mentor rate them 1-10. Discuss disagreements in detail. Pay attention when others try ideas you've had — did reality match your prediction? Track your batting average over time.

7. **The One-Sentence Test (per project).** State your contribution as one sentence that captures a deep insight. If you can't, the work may lack a core contribution. "We achieve state-of-the-art on benchmark X" is not an insight. "We show that equivariance in the action space, not just the observation space, is what enables few-shot transfer" is an insight.

### 11.3 Compound Infrastructure

Sustained output comes from: reusable codebases, reliable hardware, data pipelines, evaluation protocols, shared lab knowledge. Fix infrastructure on Mondays.

### 11.4 Research Programs, Not Paper Collections

Compounding expertise in one problem class. Reusable infrastructure. Visible narrative across papers. Each paper's limitations seed the next. The worst pattern: hopping between trendy topics.

---

## Appendix A: Self-Diagnostic Checklist

### Before you start (most important)

- [ ] **Significance (Hamming Test):** Can I name the 10-20 most important unsolved problems in my area? Is this one of them? If not, why am I working on it?
- [ ] **Significance (Consequence Test):** If I solved this overnight, what concretely changes? Can I name a specific downstream capability, system, or understanding that improves? Would others (not just my sub-sub-field) consider this important?
- [ ] **Significance (Durability Test):** Will this problem still matter in 48 months? Will a bigger model or more data trivially solve it?
- [ ] **Task:** Can I state concretely what the robot should do in the physical world? (Not abstractly — what specific physical behavior, with what objects, in what environment?)
- [ ] **Problem Definition (Formalization):** Can I write this problem as math — as an optimization, estimation, or decision problem with explicit objective, variables, constraints, and information structure? If I can't write the math, I don't understand the problem.
- [ ] **Problem Definition (Structure):** Have I identified the mathematical structure — convexity, symmetries, dimensionality, decomposability? Does my formalization reveal what makes THIS problem different from the general case?
- [ ] **Problem (Empirical):** Have I built and run a minimal system and watched it fail? Can I state specifically what fails, at what stage, under what conditions?
- [ ] **Challenge:** Can I articulate the fundamental structural barrier? (Not a resource complaint — what mathematical, physical, or computational structure makes this resist current solutions?)
- [ ] **Why now:** What has changed that makes this solvable today but not 5 years ago?
- [ ] **Challenge → Approach:** Does my approach logically follow from my challenge analysis? If someone understood only my challenge, would they predict my approach class?
- [ ] **Scope:** Are my claims precisely aligned with the challenge I address? Not broader, not narrower?
- [ ] **One-Sentence Test:** Can I state my contribution as one sentence that captures a deep structural insight (not just "we achieve SOTA on X")?

### Before you design

- [ ] Have I built and run a minimal end-to-end system? Have I experienced the failure modes firsthand?
- [ ] Do I understand the mathematical structure? (Convexity, symmetries, dimensionality, stability, decomposability)
- [ ] Is my representation choice justified for MY SPECIFIC challenge?
- [ ] Am I using the right sensing modalities for the information I need?
- [ ] Have I checked: would different hardware make this problem trivially easier?

### Before you evaluate

- [ ] Do my baselines represent genuine effort? Do they include simple/scripted baselines?
- [ ] Do my experiments directly test whether I've addressed my stated challenge?
- [ ] Have I run enough trials for statistical significance? (10 minimum, 20+ for stochastic policies)
- [ ] Have I tested on enough variation to support my claim scope?
- [ ] Do I report failure modes, severity, and taxonomy?
- [ ] Do I report human effort (demos, calibration, tuning)?
- [ ] Does this compose / scale to longer horizons?

### Before you submit

- [ ] Can I state my contribution in one sentence a non-expert understands?
- [ ] Is the task→problem→challenge→approach chain clear in my introduction?
- [ ] Is my method section reimplementable?
- [ ] Have I released code, data, and evaluation protocols?
- [ ] Would this still matter if foundation models improved 10x?
- [ ] Have I tried to break my own method?
- [ ] Am I honest about the lab-deployment gap?

---

## Appendix B: Paper Evaluation Rubric

Structured rubric for evaluating robotics papers. Designed to be applied consistently — by a human or an LLM agent.

### B.1 Significance and Problem Definition (Weight: Highest)

| Score | Criteria |
|-------|----------|
| 5 | Problem is demonstrably important (passes Hamming test: important AND has a reasonable attack). Task is concrete and well-scoped. Problem is formally defined with explicit mathematical structure (objective, variables, constraints). Challenge identifies a structural barrier that logically constrains the solution class. The approach follows from the challenge. Claims match scope. The contribution can be stated as one sentence capturing a deep structural insight. |
| 4 | Task and problem are clear. Problem significance is argued but not fully compelling. Problem has some formal structure. Challenge is articulated but could be deeper — the link from challenge to approach is present but not fully convincing. |
| 3 | Task is defined but significance is assumed rather than argued. Problem is described in prose without formalization ("X is challenging"). Challenge is asserted rather than analyzed. Approach is motivated but not by structural insight. |
| 2 | Task is clear but significance, problem definition, and challenge are confused or absent. Approach seems chosen for novelty rather than because the challenge demands it. No formal problem statement. |
| 1 | No clear significance argument. No formal problem definition. Paper solves a method looking for a problem. |

### B.2 Technical Approach (Weight: High)

| Score | Criteria |
|-------|----------|
| 5 | Key insight is deep and connects challenge to solution. Exploits problem structure (symmetry, decomposition, physics). Explains *why* the approach works. |
| 4 | Sound approach with clear insight. Good use of domain knowledge. |
| 3 | Technically correct but insight is thin. Works but unclear why. |
| 2 | Engineering contribution without conceptual insight. Applies trending method without understanding what the task needs. |
| 1 | Technically flawed or trivially combines existing methods. |

### B.3 Experimental Rigor (Weight: High)

| Score | Criteria |
|-------|----------|
| 5 | Real-robot, 20+ trials/condition, confidence intervals, strong baselines (including simple), ablations isolating contributions, failure analysis with taxonomy, perturbation tests. Transparent about setup effort. |
| 4 | Real-robot, 10+ trials, good baselines, meaningful ablations, some failure analysis. |
| 3 | Real-robot but <10 trials, or baselines not tuned, or ablations don't isolate contribution. No failure analysis. |
| 2 | Sim-only for a real-world problem. Or: real-robot but 3-5 trials, weak baselines, no ablations. |
| 1 | Evaluation doesn't support claims. Cherry-picked, no statistics, strawman baselines. |

### B.4 Representation and Sensing (Weight: Medium)

| Score | Criteria |
|-------|----------|
| 5 | Representation motivated by specific task/challenge requirements. Appropriate sensing modalities. Compared against alternatives. |
| 4 | Good choice with justification. Acknowledges sensing limitations. |
| 3 | Default choice (RGB for everything) without justification. |
| 2 | Clearly mismatched (no depth for 3D reasoning, no force for contact). |
| 1 | Actively harmful to method's goals. |

### B.5 Generalization and Compositionality (Weight: Medium)

| Score | Criteria |
|-------|----------|
| 5 | Generalization across objects, environments, conditions. Composes with other skills. Tested beyond training distribution. |
| 4 | Good generalization with clear scope. Some compositional capability. |
| 3 | Limited tests. Single environment or narrow objects. No compositionality. |
| 2 | Only training distribution. No generalization evidence. |
| 1 | Overfits to specific setup. |

### B.6 Practical Viability (Weight: Medium)

| Score | Criteria |
|-------|----------|
| 5 | Real-time, reasonable hardware, data-efficient, failure recovery, clear deployment path. |
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

### Using This Rubric

**For your own papers:** Score yourself before submitting. Any dimension below 3 is a weakness reviewers will find. B.1 below 4 means your research thinking chain is incomplete.

**For evaluating others:** Start with B.1 — if the task-problem-challenge chain is weak, the paper's foundation is shaky regardless of other scores.

**For an LLM research agent:** The agent should score each dimension with evidence (quotes/sections), confidence level (high/medium/low), and explicit flagging when it cannot assess a dimension (mathematical depth, physical feasibility). The agent should extract the task→problem→challenge→approach chain as its FIRST analysis step for every paper.
