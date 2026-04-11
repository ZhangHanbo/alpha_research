# Benchmarks

> The benchmarks in this file pin down half of the problem statement:
> observation/action spaces, success criterion, and evaluation
> distribution. They gate forward guard `g2` (FORMALIZE → DIAGNOSE).
>
> Workflow: run the `benchmark-survey` skill first; it writes a ranked
> proposal at `benchmark_proposal.md`. Read it, decide which benchmarks
> to include, and fill in the sections below. The `g2` guard requires at
> least one benchmark under `## In scope` with a rationale, a success
> criterion, ≥1 published baseline with its number, and a saturation
> assessment.

## In scope

<!-- Add one subsection per chosen benchmark using the template below. -->

<!--
### Benchmark 1: <benchmark name>

- **Why chosen**: <one sentence — relevance to the formalization, community adoption, non-saturation>
- **Variant / configuration**: <specific sub-task if the benchmark has multiple>
- **Standard metrics**:
  - <metric 1>
  - <metric 2>
- **Success criterion**: <the exact condition this benchmark calls "success">
- **Published baselines** (the ones the reproduction check will target):
  - Paper A (YEAR) <method name>: <number> on <metric>
  - Paper B (YEAR) <method name>: <number> on <metric>
  - Paper C (YEAR) <method name>: <number> on <metric>  ← strongest prior
- **Install recipe**: <pip / docker / git clone command, any URDF / asset pointer>
- **Reproducibility status**: pending | pass | partial | fail
- **Saturation risk**: LOW | MEDIUM | HIGH | SATURATED
  <one sentence explaining — e.g. "top score is 0.78 with room", "top score is 0.99, saturated">
- **Why not this one as the primary**: <if not primary, why; otherwise "primary">
-->

## Considered but rejected

<!-- Benchmarks you considered and decided against. Each entry: one sentence
"why not". Helps future reviewers understand your choices. -->

<!--
### RLBench insertion
- Rejected because: sim-only, no contact model, published leaderboard saturated at 0.99.
-->

## Notes

<!-- Anything else relevant: version pins, dataset licenses, compute
budget for reproduction runs, hardware required. -->
