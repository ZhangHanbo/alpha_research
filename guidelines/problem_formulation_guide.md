# How to Write a High-Quality Problem Formulation for a Survey Paper

## A Guideline Synthesized from Top Researchers, Roboticists, and Mathematicians

---

## Why This Document Exists

A problem formulation is the backbone of any survey paper. It is the shared language that unifies the works being surveyed, the lens through which the reader interprets every subsequent section, and the contract between author and reader about what "solving the problem" means. A poor formulation alienates readers, obscures connections between works, and makes the survey's contribution unclear. A good one makes everything else easier.

This guideline synthesizes advice from:
- **Robotics (learning)**: Sutton & Barto, Sergey Levine (Berkeley), Chelsea Finn (Stanford), Pieter Abbeel (Berkeley), Kober/Bagnell/Peters (IJRR)
- **Robotics (planning)**: Kaelbling & Lozano-Perez (MIT TAMP), Garrett et al., Gerkey & Mataric (multi-robot), STRIPS/PDDL tradition
- **Mathematics and writing**: Terence Tao (UCLA), Donald Knuth (Stanford), Dimitri Bertsekas (MIT), John Tsitsiklis (MIT), Keith Conrad (UConn), Igor Pak (UCLA)
- **ML/AI venues**: ACM Computing Surveys, NeurIPS, ICML, JMLR guidelines
- **Optimization**: Boyd & Vandenberghe (Stanford), Bertsimas & Tsitsiklis (MIT)
- **Exemplary surveys**: Meta-RL (Beck et al.), MARL (comprehensive survey), HRL (ACM), TAMP (Garrett et al.), Multi-Robot Task Allocation (Gerkey & Mataric)

---

## Part I: Principles

### Principle 1: Motivate Before You Formalize

> "Just because you CAN write statements in purely mathematical notation doesn't mean you necessarily SHOULD." -- Terence Tao

Every exemplary survey formulation begins with **why** before **what**. The Meta-RL survey opens with a robot chef scenario. Levine's RL-as-inference tutorial opens with the question: "What if we treated optimal behavior as a probabilistic inference problem?" Garrett et al.'s TAMP survey opens with the challenge of robots needing to reason about both discrete symbolic choices and continuous physical motions simultaneously.

**The rule**: Before any tuple definition or equation, write 2-4 sentences that a graduate student outside your subfield can understand. State the challenge. State what makes it hard. State what a solution would look like. Then formalize.

**Anti-pattern**: Opening with "We define an MDP as a tuple (S, A, T, R, gamma)..." without any context. The reader has no idea why you chose this formalism or what you're trying to capture.

---

### Principle 2: Build from Familiar to Novel (Bottom-Up Scaffolding)

The dominant pattern across all surveyed works is **bottom-up scaffolding**:

1. **Start with the simplest, most well-known formalism** that captures the essential structure (e.g., MDP for sequential decision-making, LP for optimization)
2. **Show its limitations** for the setting you're surveying ("However, in multi-agent settings, the single-agent assumption breaks down because...")
3. **Extend precisely** to the formalism you need (e.g., MDP -> Stochastic Game, MDP -> POMDP, LP -> MILP)
4. **State the new objective** that captures the problem's distinctive challenge

This works because the reader anchors on familiar ground before being asked to absorb something new. Finn & Abbeel's MAML paper defines a standard MDP, then introduces a distribution over tasks, then states the meta-objective. Levine defines the standard RL objective, then introduces the optimality variable, then reformulates as inference. The reader is never lost.

**The rule**: If your survey's formalism is an extension of a well-known one, define the well-known one first, then extend. If it is not an extension, find the closest known formalism and explicitly contrast.

---

### Principle 3: The Formulation Is a Design Choice, Not a Discovery

> "The art is in recognizing the problem class." -- Boyd & Vandenberghe

A formulation is not "true" or "false" -- it is **useful** or **not useful**. The same real-world problem (e.g., "coordinate multiple robots to clean a building") can be formulated as a Dec-POMDP, a multi-agent MDP, a constraint satisfaction problem, a mixed-integer program, or a cooperative game. Each formulation highlights different aspects and enables different solution approaches.

For a survey, the formulation's job is to be **general enough to subsume the works being surveyed** while being **specific enough to be non-trivial**. Gerkey & Mataric's MRTA taxonomy is exemplary: they define three binary dimensions (ST/MT, SR/MR, IA/TA) that partition the space of multi-robot task allocation problems, then show how each cell maps to a known optimization problem class. The formulation itself IS the contribution.

**The rule**: Choose the formulation that creates the most illuminating taxonomy of the surveyed works. If a more general formulation (e.g., Dec-POMDP) subsumes a simpler one (e.g., multi-agent MDP) but most surveyed works assume the simpler setting, present both -- the general one for completeness, the simpler one as the "default" that most works operate in.

---

### Principle 4: Separate the Five Components

Across all fields -- robotics, OR, ML, planning -- the same five components recur in every problem formulation:

| Component | What It Answers | Examples |
|-----------|----------------|----------|
| **1. System definition** | What are the entities and their relationships? | State space S, action space A, agent set N, object set O |
| **2. Dynamics** | How does the system evolve? | Transition T(s'|s,a), physics model s' = f(s,a) + noise |
| **3. Information structure** | Who knows what, and when? | Full observability, partial observability, communication constraints |
| **4. Objective** | What are we optimizing? | Cumulative reward, goal satisfaction, cost minimization |
| **5. Constraints and assumptions** | What are the boundaries? | Finite horizon, deterministic transitions, known dynamics |

The ordering matters. Readers need to know what exists (system) before how it changes (dynamics), what agents can see (information) before what they're trying to do (objective), and the general problem before its simplifications (constraints).

**The rule**: Present these five components in order. Each should be identifiable as a distinct paragraph or block. A reader should be able to point to "where the objective is defined" without scanning the entire section.

---

### Principle 5: One General Formulation, Then Instantiate

For a survey paper specifically, the ideal structure is:

1. **One general formulation** that covers (or nearly covers) all surveyed works
2. **Explicit instantiations** showing how important special cases fall out by fixing parameters or removing components

For example, a survey on multi-agent sequential decision-making might define the general Partially Observable Stochastic Game (POSG), then show:
- Set all agents' observations = full state -> Multi-Agent MDP
- Set N=1 -> POMDP
- Set N=1 and observations = full state -> MDP
- Add communication channel -> Dec-POMDP with communication
- Set rewards to be identical for all agents -> Cooperative setting

This gives the reader a **map** of the problem landscape. They can locate any cited work by asking "which assumptions does this work make?"

**The rule**: Define the general formulation once. Then provide a table or figure showing how special cases relate to it. Don't re-derive each special case from scratch.

---

### Principle 6: The Objective Must Be a Displayed Equation

The single most important equation in the formulation is the objective -- the thing being optimized, the criterion for success, the goal condition. It deserves to be:

- A **numbered, displayed equation** (not inline)
- **Immediately preceded** by a sentence explaining what it means in plain English
- **Immediately followed** by a sentence connecting it to the works being surveyed

From Boyd & Vandenberghe's canonical form:

```
minimize    f_0(x)
subject to  f_i(x) <= 0,   i = 1, ..., m
            h_j(x) = 0,    j = 1, ..., p
```

From the RL tradition:

```
maximize    J(pi) = E_{tau ~ pi} [ sum_{t=0}^{T} gamma^t r(s_t, a_t) ]
```

**The rule**: If a reader takes away only one equation from your formulation, it should be the objective. Make it prominent, clear, and self-contained.

---

## Part II: Notation

### Rule N1: Follow Field Conventions

Do not invent notation when conventions exist. The reader's cognitive budget is limited; every unfamiliar symbol is a tax on comprehension.

**Standard ML/RL notation** (widely adopted):
- Scalars: lowercase italic (d, n, m, t, gamma)
- Vectors: boldface lowercase (**x**, **a**, **w**)
- Matrices: boldface uppercase (**W**, **P**)
- Sets/spaces: calligraphic uppercase (S, A, O) or blackboard bold (R, Z)
- Distributions: calligraphic D, or specific (N for Gaussian, Cat for categorical)
- Parameters: theta for complete parameter set, phi for auxiliary
- Policy: pi (deterministic) or pi(a|s) (stochastic)
- Transition: T(s'|s,a) or P(s'|s,a)
- Reward: r(s,a) or R(s,a,s')
- Discount factor: gamma
- Time index: subscript t
- Agent index: superscript i or subscript i

Sources: Sutton & Barto, Suggested Notation for ML (GitHub), Levine's tutorials

### Rule N2: The Three-Use Rule (Tao)

> "Introduce notation for expressions appearing three or more times; one-time expressions usually don't warrant special symbols."

If a quantity appears only once, write it out. If it appears twice, consider writing it out. If it appears three or more times, give it a symbol. This keeps the notation minimal.

**Anti-pattern**: "Let xi_{i,j,k}^{(t)} denote the auxiliary variable for agent i at level j in component k at time t" -- used exactly once in the paper.

### Rule N3: Keep a Consistency Sheet (Tsitsiklis)

Before submitting, maintain a separate document listing every symbol, its definition, and where it first appears. Check for:
- **Conflicts**: Same symbol used for different things (common: T for both time horizon and transition function)
- **Redundancy**: Different symbols for the same thing
- **Simplicity**: Can any subscript/superscript be eliminated?

### Rule N4: Never Begin a Sentence with a Symbol (Conrad)

Write "The state space S is finite" not "S is finite." Write "The discount factor gamma in (0,1) controls..." not "gamma in (0,1) controls..."

### Rule N5: Use English for Context, Math for Precision (Tao, Knuth)

- Words like "however," "unfortunately," "in particular," and "crucially" convey information that symbols cannot.
- Use prose to explain **why** a definition is chosen, **what** it captures, and **how** it relates to the reader's existing knowledge.
- Use equations to state **precise** relationships that prose would make ambiguous.

**Good**: "Unfortunately, this problem is NP-hard in general (Theorem 3). However, under the assumption of additive rewards, it decomposes into n independent subproblems, each solvable in polynomial time."

**Bad**: "Since the problem is in NPC (see Thm. 3), but for additive R it decomposes into n sub-problems in P."

---

## Part III: Structure Template

### Recommended Section Structure for a Survey Formulation

```
Section N: Problem Formulation
  
  N.1 Motivation and Setting          (1/2 page)
       - Concrete scenario or challenge statement
       - Why existing formalisms are insufficient or need adaptation
       - Preview of what the formulation will capture
  
  N.2 Base Formalism                   (1/2 - 1 page)
       - Standard, well-known framework (e.g., MDP)
       - Tuple definition
       - Standard objective
       - Brief note on what it cannot capture for this survey's scope
  
  N.3 Extended Formulation             (1 - 1.5 pages)
       - The general formulation that covers the survey's scope
       - System definition (tuple or component list)
       - Dynamics
       - Information structure
       - Objective (displayed, numbered equation)
       - Key assumptions stated explicitly
  
  N.4 Problem Landscape / Taxonomy     (1/2 - 1 page)
       - Table or figure showing how special cases relate to the general formulation
       - Which assumptions each class of surveyed works makes
       - Mapping to known problem classes from other fields (if applicable)
  
  N.5 Running Example (optional)       (1/2 page)
       - Instantiate the formulation on a concrete scenario
       - Show what S, A, T, R look like for one specific problem
       - Reference this example throughout later sections
```

Total: **3-4 pages** for a comprehensive survey. Can be compressed to 1.5-2 pages by merging N.2 into N.3 and making N.4 a single table.

---

## Part IV: Common Patterns from Exemplary Surveys

### Pattern A: The Tuple-First Pattern (Most Common in RL/Robotics)

Used by: Sutton & Barto, Kober/Bagnell/Peters, MARL surveys, HRL surveys

```
Define the system as a tuple M = (S, A, T, R, gamma) where:
  - S is the state space
  - A is the action space
  - T: S x A x S -> [0,1] is the transition function
  - R: S x A -> R is the reward function
  - gamma in [0,1) is the discount factor
  
The agent's goal is to find a policy pi: S -> A that maximizes:
  J(pi) = E [sum_{t=0}^{inf} gamma^t R(s_t, a_t)]
```

**When to use**: When the formalism is well-established and the novelty is in the solution methods, not the problem definition.

### Pattern B: The Taxonomy-First Pattern (Common in Multi-Robot/MRTA)

Used by: Gerkey & Mataric, multi-robot surveys

```
The problem space is characterized by three dimensions:
  Dimension 1: [option A] vs [option B]
  Dimension 2: [option A] vs [option B]
  Dimension 3: [option A] vs [option B]
  
Each combination defines a distinct problem class:
  [Table mapping combinations to known problem classes]
  
The general problem subsumes all classes: ...
```

**When to use**: When the survey covers a heterogeneous space of problems that share structural similarities but differ in specific assumptions.

### Pattern C: The Extension Pattern (Common in Advanced RL)

Used by: Levine (RL as inference), Finn (MAML), Meta-RL surveys

```
Standard MDP: M = (S, A, T, R, gamma)
  [brief definition]
  
Limitation: [what the standard MDP cannot capture]

Extension: We introduce [new component] to obtain M' = (S, A, T, R, gamma, [new]):
  [definition of extension]
  
The new objective becomes:
  J'(pi) = [modified objective incorporating the extension]
```

**When to use**: When the survey's core formalism is a strict extension of a well-known one.

### Pattern D: The Optimization Pattern (Common in OR/Planning)

Used by: Boyd & Vandenberghe, Bertsimas, TAMP surveys

```
Decision variables: x in X (what we choose)
  
Objective:
  minimize  f(x)

Subject to:
  g_i(x) <= 0,  i = 1,...,m   (inequality constraints)
  h_j(x) = 0,   j = 1,...,p   (equality constraints)
  
Special structure: [what makes this instance tractable or hard]
```

**When to use**: When the problem is naturally expressed as an optimization and the surveyed works differ in how they handle the objective, constraints, or solution methods.

---

## Part V: The Quality Checklist

Before finalizing your problem formulation, verify:

### Completeness
- [ ] Every symbol is defined before (or immediately when) first used
- [ ] The objective is stated as a numbered, displayed equation
- [ ] All five components are present: system, dynamics, information, objective, assumptions
- [ ] Special cases are explicitly mapped to the general formulation

### Clarity
- [ ] A graduate student outside your subfield can follow the motivation (N.1) without equations
- [ ] No sentence begins with a symbol
- [ ] No two adjacent symbols without intervening words (unless part of one expression)
- [ ] English words convey context, importance, and relationships; math conveys precision
- [ ] The formulation section is self-contained -- a reader need not jump to later sections

### Economy
- [ ] The three-use rule is satisfied (no symbol used fewer than 3 times)
- [ ] No subscript-of-subscript-of-superscript towers
- [ ] Standard notation from the field is used (not reinvented)
- [ ] The consistency sheet has no conflicts or redundancies
- [ ] Derivations available in textbooks are cited, not re-derived

### Usefulness for the Survey
- [ ] The formulation creates a taxonomy that organizes the surveyed works
- [ ] A reader can locate any cited work by asking "which assumptions does it make?"
- [ ] The general formulation is general enough to cover >90% of surveyed works
- [ ] The rare exceptions are acknowledged ("Some works operate outside this framework; see Section X")
- [ ] The formulation enables meaningful comparison across works (same notation, same objective)

### Presentation
- [ ] Motivation before formalism (2-4 sentences of plain English first)
- [ ] Familiar before novel (base formalism, then extension)
- [ ] The section is 3-4 pages (comprehensive survey) or 1.5-2 pages (focused survey)
- [ ] A figure or table shows the problem landscape / taxonomy
- [ ] At least one concrete example instantiates the abstract formulation

---

## Part VI: Trade-offs for Survey Papers Specifically

### Generality vs. Simplicity

The eternal tension: a formulation general enough to cover all surveyed works may be so abstract that it obscures the specific challenges each work addresses.

**Resolution**: Present the general formulation (Section N.3), but designate a "default setting" -- the most common set of assumptions across surveyed works. Write: "Unless otherwise noted, we assume [default setting] throughout. Works that relax these assumptions are discussed in Section X." This lets the reader carry a simple mental model while knowing the general framework exists.

### Inclusivity vs. Elegance

Some surveyed works use formalisms that don't cleanly fit the general formulation. Including them adds completeness but may require inelegant patches to the formulation.

**Resolution**: Use the 90% rule. If a formulation covers 90%+ of surveyed works cleanly, it is good enough. Acknowledge the remaining works with a brief note: "Works such as [X, Y] formulate the problem differently as [brief description]; we discuss these in Section Z." Do not contort the main formulation to accommodate outliers.

### Mathematical Rigor vs. Accessibility

A fully rigorous formulation (measure-theoretic probability, formal logic) may be correct but impenetrable. A fully informal one is accessible but imprecise.

**Resolution**: Use the "rigorous but readable" standard from NeurIPS/ICML. State definitions precisely (tuple notation, explicit domains for functions), but use prose to explain them. Reserve full rigor (epsilon-delta arguments, formal proofs of well-definedness) for the appendix.

### Depth of Formulation vs. Paper Length

A formulation section that is too long bores the expert reader; too short leaves the non-expert lost.

**Resolution**: The formulation section should be **proportional to the novelty of the formalism**. If the survey uses standard MDP notation that every reader knows, 1 page suffices. If the survey introduces a novel unified framework, 3-4 pages are justified. Never more than 4 pages for the formulation in a survey paper -- the surveyed works are the main content, not the formulation.

---

## Part VII: Anti-Patterns to Avoid

1. **The notation dump**: A full page of symbol definitions with no motivation or context. The reader has no idea why these symbols matter.

2. **The reinvention**: Using non-standard notation for standard concepts (calling the discount factor "beta" when the entire field uses "gamma"). Every deviation from convention must earn its place.

3. **The kitchen sink**: Including every possible extension, special case, and variant in the general formulation. This produces a 7-tuple that becomes a 15-tuple and is unusable.

4. **The phantom assumption**: Relying on an assumption (e.g., finite state space, deterministic transitions) without stating it. The reader discovers it three sections later when a cited work violates it.

5. **The orphan equation**: A displayed equation with no preceding motivation and no following interpretation. Every equation needs a "why" before and a "so what" after.

6. **The appendix reference**: "We define our notation in Appendix A." No. The main text must be self-contained (Tsitsiklis). Supplementary notation may go in the appendix; core notation must be in the body.

7. **The false generality**: A formulation that appears general but actually assumes one specific setting (e.g., claiming to cover "multi-agent systems" but implicitly assuming cooperative, fully-observable, homogeneous agents throughout).

---

## Summary: The 10 Commandments

1. **Motivate before you formalize.** Plain English first, then math.
2. **Build from familiar to novel.** Start with the known formalism, then extend.
3. **Separate the five components.** System, dynamics, information, objective, assumptions -- in that order.
4. **Make the objective a displayed equation.** It is the most important equation in the section.
5. **Follow field conventions.** Do not reinvent notation.
6. **Apply the three-use rule.** If a symbol appears fewer than three times, write it out.
7. **Present the general case, then instantiate.** One formulation, many special cases.
8. **Use the 90% rule.** Cover the majority cleanly; acknowledge outliers briefly.
9. **Keep English for context, math for precision.** Words like "unfortunately" and "crucially" carry information.
10. **Check your work.** Consistency sheet, completeness checklist, one concrete example.

---

## Appendix: Key References

### On Mathematical Writing
- Tao, T. "Use Good Notation." https://terrytao.wordpress.com/advice-on-writing-papers/use-good-notation/
- Tao, T. "Take Advantage of the English Language." https://terrytao.wordpress.com/advice-on-writing-papers/take-advantage-of-the-english-language/
- Tsitsiklis, J. "A Few Tips on Writing Papers with Mathematical Content." https://www.mit.edu/~jnt/Papers/R-20-write-v5.pdf
- Bertsekas, D. "Ten Simple Rules for Mathematical Writing." https://www.mit.edu/~dimitrib/Ten_Rules.html
- Knuth, D. "Mathematical Writing." https://jmlr.csail.mit.edu/reviewing-papers/knuth_mathematical_writing.pdf
- Conrad, K. "Advice on Mathematical Writing." https://kconrad.math.uconn.edu/blurbs/proofs/writingtips.pdf
- Pak, I. "How to Write a Clear Math Paper." https://www.math.ucla.edu/~pak/papers/how-to-write1.pdf

### On CS/ML Paper Writing
- Nowozin, S. "Ten Tips for Writing CS Papers." https://www.nowozin.net/sebastian/blog/ten-tips-for-writing-cs-papers-part-1.html
- ACM Computing Surveys Author Guidelines. https://dl.acm.org/journal/csur/author-guidelines
- NeurIPS Paper Checklist. https://neurips.cc/public/guides/PaperChecklist
- Suggested Notation for Machine Learning. https://github.com/mazhengcn/suggested-notation-for-machine-learning

### On Problem Formulation in Specific Fields
- Boyd, S. & Vandenberghe, L. "Convex Optimization." https://stanford.edu/~boyd/cvxbook/
- Sutton, R. & Barto, A. "Reinforcement Learning: An Introduction." http://incompleteideas.net/book/the-book-2nd.html
- Levine, S. "Reinforcement Learning and Control as Probabilistic Inference." https://arxiv.org/abs/1805.00909
- Garrett, C. et al. "Integrated Task and Motion Planning." https://arxiv.org/abs/2010.01083
- Gerkey, B. & Mataric, M. "Multi-Robot Task Allocation." IJRR 2004.
- Beck, J. et al. "A Survey of Meta-Reinforcement Learning." https://arxiv.org/abs/2301.08028
