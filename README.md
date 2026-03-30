# Alpha Research

A multi-agent system for automated research paper discovery, evaluation, and
adversarial review in robotics. Three LLM-powered agents collaborate through a
shared blackboard:

- **Research Agent** -- searches for papers, extracts structured evaluations,
  and produces research artifacts following a significance-first methodology.
- **Review Agent** -- adversarial reviewer calibrated to specific publication
  venues (RSS, IJRR, CoRL, etc.). Applies graduated pressure across iterations
  and produces structured, falsifiable findings.
- **Meta-Reviewer** -- area-chair role that checks review quality against
  quantitative thresholds (actionability >= 80%, grounding >= 90%, zero vague
  critiques, falsifiability >= 70%) and detects anti-patterns.

An **Orchestrator** runs the loop: the research agent produces an artifact, the
review agent attacks it, the meta-reviewer quality-checks the review, and the
cycle repeats until convergence (quality met, human approved, stagnation, or
iteration limit).

Human checkpoints are triggered at critical decision points (backward
transitions, final acceptance, low-confidence assessments).


## Project Structure

```
alpha_research/
|-- config/
|   |-- constitution.yaml        # Research agent domain focus
|   `-- review_config.yaml       # Review thresholds, pressure schedule, convergence
|
|-- src/alpha_research/
|   |-- models/                  # Pydantic V2 data models (foundation)
|   |   |-- research.py          #   Paper, Evaluation, TaskChain, SearchState, ...
|   |   |-- review.py            #   Finding, Review, Verdict, RevisionResponse, ...
|   |   `-- blackboard.py        #   Blackboard, ResearchArtifact, ConvergenceState, Venue
|   |
|   |-- knowledge/               # Persistent storage (SQLite)
|   |   |-- schema.py            #   8-table schema (papers, evaluations, findings, ...)
|   |   `-- store.py             #   KnowledgeStore CRUD with deduplication
|   |
|   |-- tools/                   # Shared toolset for agents
|   |   |-- arxiv_search.py      #   ArXiv search with category/date filtering
|   |   |-- paper_fetch.py       #   PDF download + pymupdf text extraction
|   |   |-- semantic_scholar.py  #   S2 API: metadata, citations, references
|   |   |-- knowledge.py         #   Agent-facing read/write interface to store
|   |   `-- report.py            #   Jinja2 markdown report generation
|   |
|   |-- prompts/                 # System prompt builders
|   |   |-- research_system.py   #   Research agent prompt (significance tests, rubric, ...)
|   |   |-- review_system.py     #   Review agent prompt (attack vectors, venue calibration, ...)
|   |   |-- meta_review_system.py#   Meta-reviewer prompt (quality metrics, anti-patterns)
|   |   `-- rubric.py            #   Shared rubric text (B.1-B.7, 6.1-6.5, attack vectors)
|   |
|   |-- agents/                  # Agent implementations
|   |   |-- research_agent.py    #   Generate/revise artifacts, run digest/deep modes
|   |   |-- review_agent.py      #   Three-pass review, verdict computation, chain extraction
|   |   |-- meta_reviewer.py     #   Programmatic + optional LLM quality checks
|   |   `-- orchestrator.py      #   Main loop: research -> review -> meta-review -> converge
|   |
|   |-- metrics/                 # Pure-Python metric computation
|   |   |-- review_quality.py    #   Actionability, grounding, falsifiability, anti-patterns
|   |   |-- convergence.py       #   Convergence detection, stagnation, resolution rate
|   |   `-- finding_tracker.py   #   Cross-iteration finding tracking, severity monotonicity
|   |
|   |-- config.py                # YAML config loaders (ConstitutionConfig, ReviewConfig)
|   |-- llm.py                   # AnthropicLLM async client wrapper
|   `-- main.py                  # Typer CLI entry point
|
`-- tests/                       # 409 tests
    |-- test_models.py
    |-- test_store.py
    |-- test_prompts.py
    |-- test_research_agent.py
    |-- test_review_agent.py
    |-- test_review_quality.py
    |-- test_orchestrator.py
    |-- test_cli.py
    |-- test_tools/
    `-- calibration/
```

### Module Dependency Graph

```
models (T1)
  |
  +---> knowledge (T2)
  |       |
  |       +---> tools/knowledge.py ----+
  |                                    |
  +---> tools (T3) -------------------+---> research_agent (T5)
  |       |                            |
  |       +----------------------------+---> review_agent (T6)
  |                                    |
  +---> prompts (T4) -----------------+---> meta_reviewer (T7)
  |       |                                      |
  |       +---> config.py                        v
  |                                      orchestrator (T8)
  +---> metrics                                  |
  |       |-- review_quality.py                  v
  |       |-- convergence.py              main.py / CLI (T9)
  |       `-- finding_tracker.py                 |
  |                                              v
  `---> llm.py                         calibration tests (T10)
```

All agents depend on **models** (the foundation). The **orchestrator** depends
on all three agents. The **CLI** depends on the orchestrator. The **LLM client**
(`llm.py`) is injected into agents at construction time and is not a hard
dependency -- agents work without it for testing.


## Installation

Requires Python >= 3.10.

```bash
# Create a conda environment (recommended)
conda create -n alpha_research python=3.11 -y
conda activate alpha_research

# Install the package with dev dependencies
pip install -e ".[dev]"

# Verify installation
alpha-research --help
python -m pytest tests/ -q
```

### API Key

LLM-powered features (the review agent, the full research-review loop, and
LLM-enhanced research evaluation) require an Anthropic API key. Set it as an
environment variable:

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

Or pass it per-command with `--api-key`. Commands that do not require an LLM
(digest search, deep paper extraction, status) work without a key.


## Usage

The CLI provides four commands. All output goes to `output/reports/`.

### 1. Research (standalone)

Search ArXiv, fetch papers, and produce a structured report. Works without an
API key (tool-only mode: search + fetch + report). With an API key, the agent
also evaluates papers against the research rubric.

```bash
# Digest mode: search and summarize recent papers on a topic
alpha-research research "tactile manipulation for deformable objects" --mode digest

# Deep mode: fetch and analyze a single paper by ArXiv ID
alpha-research research "2401.12345" --mode deep
```

Output is printed to stdout and saved to `output/reports/digest_<timestamp>.md`
or `output/reports/deep_<timestamp>.md`.

### 2. Review (single-shot)

Run the adversarial review agent on an existing research artifact (a markdown
file). Requires an API key for LLM review; without one, outputs the constructed
prompt for manual use.

```bash
# Review a paper/artifact targeting RSS standards
alpha-research review path/to/artifact.md --venue RSS

# Review targeting a stricter venue
alpha-research review path/to/artifact.md --venue IJRR

# Use a specific model
alpha-research review path/to/artifact.md --venue CoRL --model claude-sonnet-4-20250514
```

Supported venues (strictest to most lenient): `IJRR`, `T-RO`, `RSS`, `CoRL`,
`RA-L`, `ICRA`, `IROS`.

Output is structured JSON matching the `Review` model (summary, chain
extraction, steel-man, findings with severity/grounding/falsification, verdict).

### 3. Loop (full multi-agent cycle)

Run the complete research-review-revise loop. Requires an API key. The
orchestrator will prompt for human input at checkpoints.

```bash
# Run the loop targeting RSS with up to 5 iterations
alpha-research loop "contact-rich manipulation under uncertainty" --venue RSS

# Fewer iterations, different venue
alpha-research loop "sim-to-real transfer for locomotion" --venue ICRA --max-iterations 3
```

At human checkpoints, you will be prompted to `approve`, `force` (another
iteration), or `skip` (auto-continue). The blackboard state is saved to
`data/blackboard.json` after the loop completes.

### 4. Status

Check the state of an in-progress or completed loop.

```bash
alpha-research status
```

Prints the current iteration, verdict, review count, and convergence status.


## Configuration

### `config/constitution.yaml`

Defines the research agent's domain focus:

```yaml
name: "Robotics Research"
focus_areas:
  - "mobile manipulation"
  - "contact-rich manipulation"
  - "tactile sensing and feedback"
key_groups:
  - "Levine"
  - "Tedrake"
  - "Abbeel"
  # ...
max_papers_per_cycle: 50
```

### `config/review_config.yaml`

Controls the review loop behavior:

```yaml
target_venue: "RSS"
max_iterations: 5
stagnation_threshold: 2

quality_threshold:
  max_fatal: 0
  max_serious: 1
  min_verdict: "weak_accept"

graduated_pressure:
  iteration_1: "structural_scan"
  iteration_2: "full_review"
  iteration_3_plus: "focused_rereview"

review_quality_thresholds:
  min_actionability: 0.80
  min_grounding: 0.90
  max_vague_critiques: 0
  min_falsifiability: 0.70
  min_steel_man_sentences: 3
```


## Testing

```bash
# Run all 409 tests
python -m pytest tests/ -q

# Run a specific test module
python -m pytest tests/test_models.py -v
python -m pytest tests/test_orchestrator.py -v
python -m pytest tests/calibration/ -v

# Run with coverage
python -m pytest tests/ --cov=alpha_research --cov-report=term-missing
```

All tests run without network access or API keys. External APIs (ArXiv,
Semantic Scholar, Anthropic) are mocked in tests.


## Design Documents

The system is built from four source documents (in the repository root):

- `work_plan.md` -- Research agent architecture, state machines, build order
- `research_guideline.md` -- Evaluation rubric, significance tests, formalization standards
- `review_guideline.md` -- Attack vectors, review protocol, anti-patterns
- `review_plan.md` -- Executable metrics, agent architecture, iteration protocol
