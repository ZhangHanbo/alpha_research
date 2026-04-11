# Formalization

> Russ Tedrake: *"If you can't write the math, you don't understand the
> problem."* This file holds YOUR formalization, iterated until it reveals
> exploitable structure. The `formalization-check` skill reviews this
> file; it does not write it. See
> `guidelines/doctrine/problem_formulation_guide.md` for structure rules
> (motivate before formalize, five components, displayed objective
> equation, 90% rule).

## Motivation (plain English, 2–4 sentences)

<!-- What challenge are you capturing, and why does this formalization?
A graduate student outside your subfield should understand this section
without touching any math. -->

## The problem as math

### System definition
<!-- What are the entities and their relationships? State space, action
space, agents, objects. -->

### Dynamics
<!-- How does the system evolve? Transition function, physics model,
stochasticity. -->

### Information structure
<!-- Who knows what, and when? Full or partial observability,
communication constraints, observability at what latency. -->

### Objective
<!-- The single most important equation. Make it a displayed, numbered
equation. Precede it with one sentence of plain English explaining
what it says; follow it with one sentence connecting it to the
surveyed works. -->

$$
\text{objective}: \quad \min_{x \in \mathcal{X}} \; f(x)
\quad \text{subject to} \quad g_i(x) \leq 0
$$

### Constraints and assumptions
<!-- Every assumption the formalization depends on. Wrong or hidden
assumptions are exactly what backward trigger t10 is for. -->

## Structural claims

<!-- The `formalization-check` skill reads these and runs sympy verification
where possible. List each property you believe holds, and whether it is
proven, assumed, or conjectured.

Examples:
- Convex in action space under fixed state (to verify)
- SE(3) equivariant in observation (proven by construction)
- Effective dimensionality < 46 DoF (conjectured, based on manifold analysis)
-->

## What changes in the general case that isn't in this instance

<!-- A good formalization answers "what is special about MY problem vs the
general one". Sparsity, symmetry, decomposability, low effective
dimensionality — the specific structure that constrains the solution
class. -->
