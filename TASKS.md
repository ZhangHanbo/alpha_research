# Implementation Tasks — Multi-Agent Research & Review System

Compact task design for implementing both the research agent and the review agent as a multi-agent system. Each task is self-contained with explicit dependencies, source documents, and acceptance criteria so that an implementation agent can execute it without additional context.

**Source documents (agents MUST read these before implementing):**
- `work_plan.md` — Research agent architecture, state machines SM-1 through SM-6, data models, build order, project structure
- `research_guideline.md` — Evaluation rubric (Appendix B), thinking chain (Part II), significance tests (§2.2), formalization standards (§2.4)
- `review_guideline.md` — Attack vectors (Part III), review protocol (Part II), rubric (Part VI), venue calibration (Part IV), anti-patterns (§5.4)
- `review_plan.md` — Executable metrics (Part I), agent architecture (Part II), iteration protocol (Part III), package structure (Part IV)

---

## Task Dependency Graph

```
T1 (models) ──────────────────────────────────────────────────┐
  ├─► T2 (knowledge store)                                    │
  │     └─► T5 (research agent)                               │
  ├─► T3 (tools)                                              │
  │     ├─► T5 (research agent)                               │
  │     └─► T6 (review agent)                                 │
  ├─► T4 (prompts)                                            │
  │     ├─► T5 (research agent)                               │
  │     ├─► T6 (review agent)                                 │
  │     └─► T7 (meta-reviewer)                                │
  ├─► T6 (review agent) ─► T7 (meta-reviewer)                │
  │                          └─► T8 (orchestrator)            │
  └─► T5 + T6 + T7 ──────────────► T8 (orchestrator)         │
                                      └─► T9 (CLI + integration)
                                            └─► T10 (calibration tests)
```

**Parallelizable groups:**
- **Group A (parallel):** T2, T3, T4 — all depend only on T1
- **Group B (parallel):** T5, T6 — depend on T2+T3+T4
- **Group C (sequential):** T7 → T8 → T9 → T10

---

## T1: Data Models (Foundation)

**Read before implementing:** `work_plan.md` (SM-2 Paper model, SM-3 Evaluation/TaskChain/RubricScore models, SM-4 schema), `review_plan.md` §2.2 (Blackboard, Review, Finding, Verdict, RevisionResponse models)

**What to build:**
- `src/alpha_research/models/research.py` — All research-side Pydantic models:
  - `Paper`, `ExtractionQuality`, `PaperMetadata` (from `work_plan.md` SM-2)
  - `Evaluation`, `RubricScore`, `TaskChain`, `SignificanceAssessment` (from `work_plan.md` SM-3)
  - `SearchState`, `SearchQuery`, `PaperCandidate`, `CoverageReport` (from `work_plan.md` SM-1)
- `src/alpha_research/models/review.py` — All review-side Pydantic models:
  - `Review`, `Finding`, `Verdict`, `ReviewQualityMetrics`, `ReviewQualityReport` (from `review_plan.md` §2.2)
  - `RevisionResponse`, `FindingResponse`, `FindingDeferral`, `FindingDispute` (from `review_plan.md` §3.2)
  - Metric enums: `FormalizationLevel`, `ChallengeType`, `ValidationMode`, etc. (from `review_plan.md` §1.1-1.7)
- `src/alpha_research/models/blackboard.py` — Shared state model:
  - `Blackboard`, `ResearchArtifact`, `ConvergenceState`, `HumanDecision` (from `review_plan.md` §2.2)
  - Serialization to/from JSON for disk persistence
- `src/alpha_research/models/__init__.py` — Re-exports

**Acceptance criteria:**
- All models validate with Pydantic V2
- `Finding` requires all fields: `severity`, `attack_vector`, `what_is_wrong`, `why_it_matters`, `what_would_fix`, `falsification`, `grounding`, `fixable`, `maps_to_trigger`
- `Review` enforces: `fatal_flaws`, `serious_weaknesses`, `minor_issues` are lists of `Finding`
- `Blackboard` round-trips through JSON serialization without data loss
- Unit tests in `tests/test_models.py` covering validation, serialization, edge cases

**Estimated scope:** ~400 lines of model code + ~200 lines of tests

---

## T2: Knowledge Store

**Read before implementing:** `work_plan.md` SM-4 (schema, INGEST/INDEX/CONNECT/EVOLVE states), `work_plan.md` Phase 1 step 4

**Depends on:** T1 (models)

**What to build:**
- `src/alpha_research/knowledge/schema.py` — SQLite schema creation from `work_plan.md` SM-4 (papers, evaluations, paper_relations, findings, frontier_snapshots, topic_clusters, questions, feedback tables)
- `src/alpha_research/knowledge/store.py` — CRUD operations:
  - `save_paper(paper: Paper)` — dedup by arxiv_id/s2_id/doi
  - `save_evaluation(eval: Evaluation)` — linked to paper + cycle
  - `query_papers(topic, date_range, min_score, limit)` — search with filters
  - `get_evaluations(paper_id)` — all evaluations for a paper
  - `save_finding(finding)` / `query_findings(cycle_id)`
  - `get_related_papers(paper_id)` — via paper_relations table
- `src/alpha_research/knowledge/__init__.py`

**Acceptance criteria:**
- SQLite database created at `data/knowledge.db` on first use
- All CRUD operations work with Pydantic models (serialize to JSON columns where needed)
- Deduplication: inserting same paper twice (by arxiv_id) updates rather than duplicates
- Query by topic uses LIKE matching on title + abstract
- Tests in `tests/test_store.py` covering CRUD, dedup, query, relations

**Estimated scope:** ~300 lines + ~150 lines tests

---

## T3: Tools (Shared Toolset)

**Read before implementing:** `work_plan.md` SM-1 (search), SM-2 (paper fetch/extract), tech stack table, Phase 1 steps 5-7 and 9-10

**Depends on:** T1 (models)

**What to build:**
- `src/alpha_research/tools/arxiv_search.py` — ArXiv search via `arxiv` library:
  - `search(query, category, date_range, max_results)` → `list[PaperCandidate]`
  - Category filtering (cs.RO, cs.AI, cs.LG, cs.CV)
  - Date range filtering
  - Rate limiting (1 req / 3s)
- `src/alpha_research/tools/paper_fetch.py` — PDF download + text extraction:
  - `fetch_and_extract(arxiv_id)` → `Paper`
  - PDF download from ArXiv
  - Text extraction via `pymupdf`
  - Section detection heuristic (abstract, intro, method, experiments, related work, conclusion)
  - Extraction quality validation (`ExtractionQuality` model)
- `src/alpha_research/tools/semantic_scholar.py` — S2 REST API via `httpx`:
  - `get_paper(s2_id or arxiv_id)` → metadata (citations, references, venue, TLDR)
  - `search(query, limit)` → `list[PaperCandidate]`
  - `get_references(paper_id)` / `get_citations(paper_id)`
  - Rate limiting
- `src/alpha_research/tools/knowledge.py` — Agent-facing interface to knowledge store:
  - `knowledge_read(query, filters)` → results from store
  - `knowledge_write(paper, evaluation)` → persist to store
- `src/alpha_research/tools/report.py` — Markdown report generation:
  - `generate_report(evaluations, mode, template)` → markdown string
  - Templates per mode (digest, deep, survey) via Jinja2
- `src/alpha_research/tools/__init__.py` — Tool registration for Claude Agent SDK

**Tool registration pattern** (for Claude Agent SDK):
```python
# Each tool is a Python function decorated for MCP registration.
# Tool descriptions must be precise enough for the agent to use
# them correctly in sequence. See work_plan.md SM-6 for orchestration.
```

**Acceptance criteria:**
- ArXiv search returns structured `PaperCandidate` objects
- Paper fetch handles PDF download + extraction + quality validation
- Semantic Scholar handles rate limits gracefully (backoff)
- All tools return Pydantic models, not raw dicts
- Tests in `tests/test_tools/` — mock external APIs for unit tests, plus one integration test per tool

**Estimated scope:** ~600 lines + ~300 lines tests

---

## T4: System Prompts

**Read before implementing:** `work_plan.md` "The System Prompt (The Critical Piece)" section (what the research agent prompt must encode), `review_guideline.md` (full — this IS the review agent's prompt source), `review_plan.md` §4.2 (prompt design specifications for all three agents)

**Depends on:** T1 (models — for output format specifications)

**What to build:**
- `src/alpha_research/prompts/research_system.py`:
  - Build research agent system prompt from `research_guideline.md` + constitution
  - Encode: significance tests (§2.2), formalization standards (§2.4), evaluation rubric (Appendix B), honesty protocol, task chain extraction instructions
  - Inject current stage context and previous review findings
  - Output format instructions: produce `ResearchArtifact` + `RevisionResponse` as structured JSON
- `src/alpha_research/prompts/review_system.py`:
  - Build review agent system prompt from `review_guideline.md`
  - Encode: three-pass protocol (§2.1), all attack vectors (§3.1-3.6), venue calibration (§4.2), anti-patterns (§5.4)
  - Parameterize by: target venue, current iteration (for graduated pressure per `review_plan.md` §2.6), review mode
  - Output format instructions: produce `Review` as structured JSON with all `Finding` fields required
  - Include venue-specific thresholds from `review_guideline.md` §4.1
- `src/alpha_research/prompts/meta_review_system.py`:
  - Build meta-reviewer prompt from `review_plan.md` §1.8 metrics
  - Include exact thresholds: actionability ≥ 80%, grounding ≥ 90%, vague critiques = 0, falsifiability ≥ 70%
  - Include anti-pattern checklist from `review_guideline.md` §5.4
  - Output format: `ReviewQualityReport` with pass/fail per metric
- `src/alpha_research/prompts/rubric.py`:
  - Shared rubric definitions used by both research and review agents
  - Research guideline Appendix B rubric (B.1-B.7) as structured prompt text
  - Review guideline rubric (§6.1-6.5) as structured prompt text
- `src/alpha_research/config.py`:
  - Constitution YAML loader (from `work_plan.md`)
  - Review config YAML loader (from `review_plan.md` §4.4)
  - Venue enum with thresholds

**Acceptance criteria:**
- Research agent prompt encodes all items listed in `work_plan.md` "The System Prompt" section
- Review agent prompt encodes all attack vectors from `review_guideline.md` §3.1-3.6 as executable checks
- Review agent prompt changes based on venue (different thresholds) and iteration (graduated pressure)
- Meta-reviewer prompt includes all §1.8 metrics with numeric thresholds
- All prompts specify structured JSON output formats matching Pydantic models from T1
- Prompt builder functions are parameterized (venue, stage, iteration, previous findings) — not hardcoded

**Estimated scope:** ~800 lines (prompts are the highest-leverage code; invest heavily here)

---

## T5: Research Agent

**Read before implementing:** `work_plan.md` (full — especially SM-6 orchestration per mode, Phase 1 steps 8+11+12), `research_guideline.md` (the agent's "constitution")

**Depends on:** T1 (models), T2 (knowledge store), T3 (tools), T4 (prompts)

**What to build:**
- `src/alpha_research/agents/research_agent.py`:
  - Claude Agent SDK agent setup with tools from T3
  - System prompt built by T4's `research_system.py`
  - Two modes of operation:
    1. **Generate:** Produce a new `ResearchArtifact` at the current stage (SIGNIFICANCE through VALIDATE)
    2. **Revise:** Given a `Review` from the blackboard, produce a revised artifact + `RevisionResponse`
  - State machine awareness: the agent knows its current stage and which backward transitions are possible
  - Tool use orchestration per `work_plan.md` SM-6 (mode-specific sequences)
  - Knowledge store integration: reads prior evaluations, writes new findings

**Key behaviors to implement:**
- On `generate`: follow the state machine inner layer (search over candidates within current stage, per `work_plan.md` inner layer descriptions)
- On `revise`: map each `Finding` to an action (address/defer/dispute), produce `RevisionResponse`, update artifact
- Backward transitions: when a review finding maps to a trigger (t2-t15), the agent must acknowledge it and either accept (transition back) or dispute with evidence

**Acceptance criteria:**
- Agent can produce artifacts for each stage (significance argument, formalization, challenge statement, approach description, experimental plan, full draft)
- Agent produces valid `RevisionResponse` when given a `Review`
- Agent uses tools in the correct sequence for each mode (per `work_plan.md` SM-6)
- Integration test: `digest` mode produces a ranked list of evaluated papers for a given query
- Integration test: `deep` mode produces a full evaluation matching the output format in `work_plan.md` "Phase 1 Output Format"

**Estimated scope:** ~500 lines + ~200 lines tests

---

## T6: Review Agent

**Read before implementing:** `review_guideline.md` (full — this is the agent's behavior specification), `review_plan.md` Part I (executable metrics) + Part II §2.3 (agent specification) + Part II §2.6 (graduated pressure)

**Depends on:** T1 (models), T3 (tools — read-only subset), T4 (prompts)

**What to build:**
- `src/alpha_research/agents/review_agent.py`:
  - Claude Agent SDK agent with read-only tool access (`arxiv_search`, `semantic_scholar`, `knowledge_read`, `paper_fetch`)
  - System prompt built by T4's `review_system.py`, parameterized by venue and iteration
  - Two modes:
    1. **Review:** Given a `ResearchArtifact`, produce a `Review`
    2. **Re-review:** Given an updated artifact + previous review, produce a pairwise comparison review (per `review_plan.md` §3.4)
  - Three-pass protocol implementation (`review_guideline.md` §2.1):
    - Pass 1: Extract `TaskChain` and check completeness
    - Pass 2: Apply attack vectors §3.1-3.6, produce `Finding` objects
    - Pass 3: Evidence audit, check experimental claims
  - Graduated pressure (`review_plan.md` §2.6):
    - Iteration 1: structural scan only (Appendix A.1 checklist)
    - Iteration 2: full review (all attack vectors)
    - Iteration 3+: focused re-review (previous findings only + regression check)

**Key behaviors to implement:**
- Every `Finding` must have all fields populated (enforced by Pydantic validation)
- Venue calibration: different thresholds based on `target_venue` config
- Pairwise comparison on re-review: explicit status for each previous finding (addressed/partially/not/regressed)
- Concurrent work search: on iteration 2+, agent uses `arxiv_search` and `semantic_scholar` to check for papers the research artifact should cite
- Verdict computation: follow the mechanical rule in `review_plan.md` §1.9 (not gestalt)
- Anti-pattern avoidance: system prompt includes explicit "DO NOT" rules from `review_guideline.md` §5.4

**Acceptance criteria:**
- Review output is valid `Review` object with all `Finding` fields populated
- Every finding is classified fatal/serious/minor — no unclassified findings
- Venue calibration produces different verdicts for same artifact at different venues (test with borderline artifact)
- Graduated pressure: iteration 1 review is shorter and focuses on chain extraction; iteration 2 is comprehensive
- No vague critiques (test: grep output for phrases like "the evaluation is weak" without specific evidence)
- Pairwise comparison mode produces per-finding status tracking

**Estimated scope:** ~500 lines + ~300 lines tests

---

## T7: Meta-Reviewer

**Read before implementing:** `review_plan.md` §1.8 (review quality metrics), §2.3 (meta-reviewer specification), `review_guideline.md` §5.4 (anti-patterns)

**Depends on:** T1 (models), T4 (prompts), T6 (review agent — to understand review output format)

**What to build:**
- `src/alpha_research/agents/meta_reviewer.py`:
  - Lightweight agent (no tools — operates only on blackboard content)
  - System prompt from T4's `meta_review_system.py`
  - Input: `Review` + review history
  - Output: `ReviewQualityReport`
- `src/alpha_research/metrics/review_quality.py`:
  - Programmatic metric computation (complement to LLM judgment):
    - `compute_actionability(review)` → fraction of findings with non-empty `what_would_fix`
    - `compute_grounding(review)` → fraction of serious+ findings with non-empty `grounding`
    - `compute_falsifiability(review)` → fraction of serious+ findings with non-empty `falsification`
    - `count_vague_critiques(review)` → heuristic: findings where `what_is_wrong` contains flagged phrases ("weak", "limited", "insufficient" without specific evidence)
    - `check_steel_man(review)` → sentence count of `steel_man` field
  - `check_anti_patterns(review, review_history)`:
    - Dimension averaging: detected if verdict doesn't match finding severity distribution
    - Severity regression: findings downgraded without evidence
    - Declining specificity: average `grounding` length decreasing across iterations

**Acceptance criteria:**
- All §1.8 metrics computed correctly with known test inputs
- Anti-pattern detection catches: (a) review with all "serious" findings but "Accept" verdict (dimension averaging), (b) review where a previous "fatal" became "minor" without justification (severity regression), (c) review with >0 vague critiques
- `ReviewQualityReport` includes pass/fail per metric + specific issues to fix
- Tests in `tests/test_review_quality.py`

**Estimated scope:** ~250 lines + ~200 lines tests

---

## T8: Orchestrator

**Read before implementing:** `review_plan.md` §2.4 (iteration protocol), §2.5 (convergence criteria), §2.7 (anti-collapse), §3.3 (backward transition protocol), §3.5 (full interaction timeline)

**Depends on:** T1 (models), T5 (research agent), T6 (review agent), T7 (meta-reviewer)

**What to build:**
- `src/alpha_research/agents/orchestrator.py`:
  - Main loop implementing `review_plan.md` §2.4 protocol:
    ```
    Phase 1: Research agent generates/revises artifact
    Phase 2: Review agent reviews → meta-reviewer checks quality
    Phase 3: Human checkpoint (conditional)
    Phase 4: Convergence check
    ```
  - Blackboard management: load/save from disk, version tracking
  - Convergence logic (`review_plan.md` §2.5):
    - Quality threshold check
    - Iteration limit (max 5)
    - Stagnation detection (same findings + verdict for 2 consecutive iterations)
  - Human checkpoint routing (`review_plan.md` §2.4 Phase 3):
    - Trigger on: low-confidence significance/formalization, backward to SIGNIFICANCE, max iterations - 1, final ACCEPT
    - Human interface: display current state, accept input (override/approve/add findings/force iteration)
  - Backward transition protocol (`review_plan.md` §3.3):
    - Detect when review findings map to backward triggers
    - Route to human for approval before executing expensive backward transitions
  - Anti-collapse monitoring (`review_plan.md` §2.7):
    - Monotonic severity enforcement
    - Finding resolution rate tracking (≥50%)
    - Fresh-eyes final iteration
- `src/alpha_research/metrics/convergence.py`:
  - `check_convergence(blackboard)` → `ConvergenceState`
  - `detect_stagnation(review_history)` → `bool`
  - `compute_finding_resolution_rate(prev_review, revision_response)` → `float`
- `src/alpha_research/metrics/finding_tracker.py`:
  - Track findings across iterations: which were addressed, deferred, disputed, new
  - Produce cross-iteration summary for human checkpoints

**Acceptance criteria:**
- Full loop executes: research → review → meta-review → convergence check
- Convergence correctly stops at: (a) quality threshold met, (b) iteration 5, (c) stagnation after 2 identical rounds
- Human checkpoints trigger at the right times (test each trigger condition)
- Backward transition protocol: review finding with `maps_to_trigger = "t2"` triggers human checkpoint
- Anti-collapse: a review that silently downgrades a "fatal" finding is caught and rejected
- Blackboard persists to disk and survives process restart
- Tests in `tests/test_orchestrator.py`

**Estimated scope:** ~600 lines + ~300 lines tests

---

## T9: CLI & Integration

**Read before implementing:** `work_plan.md` Phase 1 step 13 (CLI entry point), `review_plan.md` §4.1 (package structure)

**Depends on:** T8 (orchestrator)

**What to build:**
- `src/alpha_research/main.py` — Typer CLI:
  - `alpha-research research --question "..." --mode [digest|deep|survey|gap|frontier|direction]`
    - Runs research agent in standalone mode (no review loop)
    - Output: markdown report to `output/reports/`
  - `alpha-research review --artifact <path> --venue [RSS|CoRL|IJRR|T-RO|RA-L|ICRA|IROS]`
    - Runs review agent on a provided artifact (single-shot, no loop)
    - Output: structured review to stdout
  - `alpha-research loop --question "..." --venue <venue> --max-iterations <n>`
    - Runs full research → review loop via orchestrator
    - Interactive: prompts human at checkpoints
    - Output: final artifact + review history to `output/`
  - `alpha-research status`
    - Shows current blackboard state if a loop is in progress
- `pyproject.toml` — Package configuration:
  - Dependencies: `claude-agent-sdk`, `arxiv`, `httpx`, `pymupdf`, `pydantic`, `typer`, `jinja2`, `sqlite3` (stdlib)
  - Entry point: `alpha-research` CLI
- `config/constitution.yaml` — Default constitution (from `work_plan.md`)
- `config/review_config.yaml` — Default review config (from `review_plan.md` §4.4)

**Acceptance criteria:**
- `alpha-research research --question "tactile manipulation" --mode digest` produces a digest report
- `alpha-research review --artifact output/test.md --venue RSS` produces a structured review
- `alpha-research loop` runs the full multi-agent loop with human prompts
- CLI handles errors gracefully (API failures, missing config, empty results)
- Integration test: end-to-end `digest` mode with mocked APIs

**Estimated scope:** ~300 lines + ~100 lines tests

---

## T10: Calibration Tests

**Read before implementing:** `review_plan.md` §1.8 (review quality metrics), `review_guideline.md` Part VI (rubric), `review_standards_reference.md` (venue-specific standards)

**Depends on:** T9 (full system running)

**What to build:**
- `tests/calibration/test_calibration.py`:
  - **Review quality calibration:** Run review agent on 3-5 known papers (already reviewed by humans at top venues) and compare:
    - Does the agent identify the same fatal/serious flaws?
    - Does the verdict correlate with the venue's accept/reject decision?
    - Are the metrics (§1.8) within thresholds?
  - **Venue calibration:** Run the same artifact through different venue configurations and verify the verdict differs appropriately (stricter at IJRR than ICRA)
  - **Graduated pressure calibration:** Verify iteration 1 produces shorter, structural-only review vs. iteration 2 comprehensive review
  - **Anti-pattern tests:** Construct adversarial review inputs that exhibit each anti-pattern from `review_guideline.md` §5.4 and verify the meta-reviewer catches them
- `tests/calibration/known_papers/` — 3-5 papers with known human reviews for calibration
- `tests/calibration/README.md` — How to run calibration, how to interpret results, how to add new calibration papers

**Acceptance criteria:**
- Agent review verdict matches human venue decision ≥ 60% of the time (Spearman correlation ~0.4, matching the Stanford Agentic Reviewer benchmark)
- All anti-pattern tests pass
- Venue calibration produces monotonically stricter verdicts: IJRR > T-RO > RSS/CoRL > RA-L > ICRA/IROS
- Results documented with analysis of where the agent agrees/disagrees with humans

**Estimated scope:** ~400 lines tests + calibration data

---

## Build Order Summary

```
Week 1:  T1 (models)               ← foundation, parallelize nothing
Week 2:  T2 + T3 + T4 (parallel)   ← all depend only on T1
Week 3:  T5 + T6 (parallel)        ← research + review agents
Week 4:  T7 → T8                   ← meta-reviewer → orchestrator
Week 5:  T9 → T10                  ← CLI + calibration
```

**Critical path:** T1 → T4 → T6 → T8 → T9. The review agent's system prompt (T4) is the highest-leverage piece — invest the most iteration time there.

**What to build first for validation:** T1 + T3 (partial: arxiv_search + paper_fetch) + T4 (research prompt only) + T5 (research agent, digest mode only). This gives a minimal system that searches, fetches, evaluates, and reports — matching `work_plan.md` Phase 1. Then add the review loop (T4 review prompt + T6 + T7 + T8) on top.
