# Tools & Skills — Implementation Plan

Detailed, executable specifications for implementing the tools and skills defined in `tools_and_skills.md`. This document is the work breakdown: every tool has a full schema, every skill has a complete `SKILL.md`, every phase has explicit acceptance criteria.

**Reading order:** Read `tools_and_skills.md` first for the architectural overview, then this document for the implementation details.

---

## Part 0. Prerequisites

### 0.1 Environment

- Python ≥ 3.12 (conda env `alpha_research`)
- `alpha_review` installed as editable dependency at `../alpha_review`
- `claude` CLI available in `PATH` (Claude Code)
- SQLite with WAL mode support

### 0.2 Repository layout after this plan

```
alpha_research/
├── .claude/
│   ├── .mcp.json                               # MCP server registration
│   └── skills/                                 # 12 skills (Phase 2)
│       ├── literature-survey/SKILL.md
│       ├── significance-screen/SKILL.md
│       ├── formalization-check/SKILL.md
│       ├── diagnose-system/SKILL.md
│       ├── challenge-articulate/SKILL.md
│       ├── method-survey/SKILL.md
│       ├── experiment-audit/SKILL.md
│       ├── adversarial-review/SKILL.md
│       ├── paper-evaluate/SKILL.md
│       ├── concurrent-work-check/SKILL.md
│       ├── gap-analysis/SKILL.md
│       └── frontier-mapping/SKILL.md
├── src/alpha_research/
│   ├── mcp_server/                             # NEW: MCP server (Phase 1)
│   │   ├── __init__.py
│   │   ├── server.py                           # stdio entry point
│   │   ├── _decorator.py                       # @mcp_tool helper
│   │   ├── schemas.py                          # shared Pydantic types (PaperCandidate, etc.)
│   │   └── tools/
│   │       ├── __init__.py                     # ALL_TOOLS registry (9 tools)
│   │       ├── search.py                       # paper_search, paper_graph, scholar_search (3 tools)
│   │       ├── content.py                      # paper_fetch (1 tool)
│   │       ├── survey.py                       # survey_start, survey_iterate, survey_finalize (3 tools)
│   │       ├── store.py                        # store_read, store_write (2 tools)
│   │       └── experiment.py                   # experiment_launch, experiment_query (Phase 3, 2 tools)
│   ├── adapters/                               # NEW: cross-LLM (Phase 4)
│   │   ├── claude.py
│   │   ├── openai.py
│   │   ├── gemini.py
│   │   ├── langchain.py
│   │   └── skill_translator.py
│   ├── agents/            # existing, kept
│   ├── knowledge/         # existing, shrunk
│   │   └── extension_schema.py                 # NEW: evaluations, findings, reviews, frontier_snapshots
│   ├── metrics/           # existing, kept
│   ├── models/            # existing, kept
│   ├── prompts/           # existing, migrates to skills over Phase 2
│   └── tools/             # existing — most files deleted/refactored
└── tests/
    ├── test_mcp_server/
    │   ├── test_search_tools.py                # paper_search, paper_graph, scholar_search
    │   ├── test_content_tools.py               # paper_fetch
    │   ├── test_survey_tools.py                # survey_start, survey_iterate, survey_finalize
    │   ├── test_store_tools.py                 # store_read, store_write
    │   └── test_server.py                      # server lifecycle, MCP protocol round-trips
    ├── test_skills/
    │   └── fixtures/                           # test papers for skill runs
    └── ...existing tests
```

### 0.3 Dependencies to add

```toml
# pyproject.toml additions
dependencies = [
    "alpha_review @ file:///${PROJECT_ROOT}/../alpha_review",
    "mcp>=1.0",                    # MCP Python SDK
    # existing deps kept
]

[project.scripts]
alpha-research-mcp = "alpha_research.mcp_server.server:main"
```

---

## Part I. Tool Specifications (MCP)

The minimal set is **9 tools** (11 with Phase 3 experiments). Every tool has the same structure: Pydantic input model, Pydantic output model, async handler, `@mcp_tool` decoration, and registration in `ALL_TOOLS`. Shared types (`PaperCandidate`, `ExtractionQuality`, `PaperContent`) live in `mcp_server/schemas.py` to avoid duplication.

### Shared types — `src/alpha_research/mcp_server/schemas.py`

```python
from pydantic import BaseModel, Field
from typing import Literal

class PaperCandidate(BaseModel):
    """Search result from any source. Same shape as alpha_review paper dicts."""
    paperId: str
    title: str
    abstract: str = ""
    authors: list[dict] = Field(default_factory=list)  # [{"name": "..."}]
    year: int = 0
    venue: str = ""
    url: str = ""
    doi: str = ""
    citationCount: int = 0
    source: str = ""                     # "openalex" | "s2" | "arxiv" | "scholar"

class ExtractionQuality(BaseModel):
    overall: Literal["high", "medium", "low", "abstract_only"]
    math_preserved: bool = False
    sections_detected: list[str] = Field(default_factory=list)
    flagged_issues: list[str] = Field(default_factory=list)

class PaperContent(BaseModel):
    """Full-text content + metadata for a single paper (paper_fetch output)."""
    paper_id: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    year: int = 0
    venue: str = ""
    abstract: str = ""
    full_text: str = ""
    sections: dict[str, str] = Field(default_factory=dict)
    extraction_source: Literal["arxiv_pdf", "ar5iv_html", "unpaywall_pdf", "abstract_only"]
    extraction_quality: ExtractionQuality
    doi: str = ""
    arxiv_id: str = ""
```

---

### T1. `paper_search`

**File:** `src/alpha_research/mcp_server/tools/search.py`
**Backs:** `alpha_review.apis.search_all` (all sources) + per-source dispatch
**Purpose:** Unified literature search. Single entry point for all query-based discovery.

```python
from pydantic import BaseModel, Field
from typing import Literal
from alpha_review.apis import search_all, openalex_search, s2_search, arxiv_search
from .._decorator import mcp_tool
from ..schemas import PaperCandidate

Source = Literal["openalex", "s2", "arxiv", "all"]

class PaperSearchInput(BaseModel):
    query: str = Field(..., description="Search query (keywords, phrases, author names)")
    sources: list[Source] = Field(
        default_factory=lambda: ["all"],
        description="Which sources to query. 'all' = unified dedup across OpenAlex, S2, ArXiv.",
    )
    limit_per_source: int = Field(15, ge=1, le=100)
    year_lo: int | None = Field(None, description="Earliest publication year")
    year_hi: int | None = Field(None, description="Latest publication year")

class PaperSearchOutput(BaseModel):
    results: list[PaperCandidate]
    source_counts: dict[str, int]

@mcp_tool(PaperSearchInput)
async def paper_search(input: PaperSearchInput) -> PaperSearchOutput:
    """Search for papers across OpenAlex, Semantic Scholar, and ArXiv. By
    default ('all') queries all three and deduplicates by title. Pass
    specific sources to narrow: ['openalex'] for citation-sorted, ['arxiv']
    for recency/preprints, ['s2'] for S2-only coverage. This is the primary
    literature discovery tool — prefer it over source-specific calls."""
    if "all" in input.sources:
        raw = search_all(
            query=input.query,
            limit_per_source=input.limit_per_source,
            year_lo=input.year_lo, year_hi=input.year_hi,
        )
    else:
        raw = []
        seen_titles = set()
        for src in input.sources:
            if src == "openalex":
                items = openalex_search(input.query, input.limit_per_source,
                                        input.year_lo, input.year_hi)
            elif src == "s2":
                yr = f"{input.year_lo or ''}-{input.year_hi or ''}" \
                     if (input.year_lo or input.year_hi) else None
                items = s2_search(input.query, input.limit_per_source, yr)
            elif src == "arxiv":
                items = arxiv_search(input.query, input.limit_per_source)
            else:
                continue
            for p in items:
                key = p.get("title", "").lower().strip()
                if key and key not in seen_titles:
                    seen_titles.add(key)
                    p["source"] = src
                    raw.append(p)
    counts = {}
    for p in raw:
        counts[p.get("source", "unknown")] = counts.get(p.get("source", "unknown"), 0) + 1
    return PaperSearchOutput(
        results=[PaperCandidate(**p) for p in raw],
        source_counts=counts,
    )
```

**Tests:**
- `test_all_sources_default`: mock all three; verify dedup by title; verify source_counts sum matches len(results).
- `test_single_source_arxiv`: `sources=["arxiv"]`; only arxiv_search called.
- `test_year_range_propagates`: year_lo/year_hi passed to backends.
- `test_input_validation`: `limit_per_source=0` rejected; negative year rejected.

---

### T2. `paper_fetch`

**File:** `src/alpha_research/mcp_server/tools/content.py`
**Backs:** Existing `src/alpha_research/tools/paper_fetch.py` (kept, refactored) + `alpha_review.apis.unpaywall_pdf_url` inlined as fallback.
**Purpose:** The ONLY content-extraction tool. Given a paper identifier, download, extract structured sections, and return full text + metadata + quality assessment.

```python
from pydantic import BaseModel, Field
from alpha_research.tools.paper_fetch import fetch_and_extract as _base_fetch
from alpha_review.apis import unpaywall_pdf_url
from .._decorator import mcp_tool
from ..schemas import PaperContent, ExtractionQuality

class PaperFetchInput(BaseModel):
    paper_id: str = Field(
        ...,
        description="ArXiv ID (e.g., 2501.12345), DOI, or direct PDF URL",
    )
    doi_fallback: str | None = Field(
        None,
        description="DOI to try via Unpaywall if primary fetch fails or "
                    "returns abstract-only. Optional.",
    )
    extract_sections: bool = Field(True)

@mcp_tool(PaperFetchInput)
async def paper_fetch(input: PaperFetchInput) -> PaperContent:
    """Download a paper and extract structured full text (abstract, introduction,
    method, experiments, related work, conclusion) plus metadata (title, authors,
    year, venue, DOI). Tries ArXiv PDF → ar5iv HTML → Unpaywall (if doi_fallback
    provided) → abstract-only. Returns an ExtractionQuality flag — ALWAYS check
    extraction_quality.overall before trusting section content. Use this whenever
    you need to read method or experiment sections. This is the only tool that
    returns full text; `paper_search` returns only abstracts."""
    result = await _base_fetch(input.paper_id, extract_sections=input.extract_sections)

    # Fallback: Unpaywall for open-access PDF
    if result.extraction_quality.overall == "abstract_only" and input.doi_fallback:
        pdf_url = unpaywall_pdf_url(input.doi_fallback)
        if pdf_url:
            retry = await _base_fetch(pdf_url, extract_sections=input.extract_sections)
            if retry.extraction_quality.overall != "abstract_only":
                retry.extraction_source = "unpaywall_pdf"
                return retry
    return result
```

**Why Unpaywall is inlined, not a separate tool:** Unpaywall is a DOI→URL resolver, not a capability the LLM reasons about independently. It is an implementation detail of "get me the PDF." Exposing it as a separate tool just makes the LLM do extra orchestration.

**Tests:**
- `test_arxiv_happy_path`: mock ArXiv download, verify 5+ sections extracted.
- `test_unpaywall_fallback`: mock ArXiv failure, mock unpaywall success, verify `extraction_source="unpaywall_pdf"`.
- `test_abstract_only_graceful`: all sources fail, return abstract with `extraction_quality.overall="abstract_only"`.
- `test_math_preservation`: feed paper with LaTeX, verify `math_preserved=True`.
- `test_section_detection`: verify `sections_detected` includes `["abstract", "introduction", "method", "experiments", "conclusion"]`.

---

### T3. `paper_graph`

**File:** `src/alpha_research/mcp_server/tools/search.py` (co-located with paper_search)
**Backs:** `alpha_review.apis.s2_references` + `s2_citations`
**Purpose:** Citation graph traversal for a specific paper. Unifies backward (references) and forward (citations) directions under one tool.

```python
from pydantic import BaseModel, Field
from typing import Literal
from alpha_review.apis import s2_references, s2_citations
from .._decorator import mcp_tool
from ..schemas import PaperCandidate

Direction = Literal["references", "citations", "both"]

class PaperGraphInput(BaseModel):
    paper_id: str = Field(..., description="S2 paperId, arxiv:ID, or DOI")
    direction: Direction = Field(
        "both",
        description="'references' = papers this paper cites (backward). "
                    "'citations' = papers that cite this paper (forward). "
                    "'both' = return both sets.",
    )
    limit: int = Field(50, ge=1, le=1000)

class PaperGraphOutput(BaseModel):
    references: list[PaperCandidate] = Field(default_factory=list)
    citations: list[PaperCandidate] = Field(default_factory=list)

@mcp_tool(PaperGraphInput)
async def paper_graph(input: PaperGraphInput) -> PaperGraphOutput:
    """Get the citation-graph neighbors of a paper. Direction='references'
    returns what this paper cites (backward — find foundations). Direction=
    'citations' returns papers that cite this paper (forward — find extensions
    and check impact trajectory). Direction='both' returns both. Use for
    impact analysis, checking concurrent work, or building a literature tree
    from a seed paper."""
    refs, cites = [], []
    if input.direction in ("references", "both"):
        raw = s2_references(input.paper_id, input.limit)
        refs = [PaperCandidate(**p, source="s2") for p in raw]
    if input.direction in ("citations", "both"):
        raw = s2_citations(input.paper_id, input.limit)
        cites = [PaperCandidate(**p, source="s2") for p in raw]
    return PaperGraphOutput(references=refs, citations=cites)
```

**Tests:**
- `test_references_only`: direction="references"; only `s2_references` called; `citations` empty.
- `test_citations_only`: direction="citations"; only `s2_citations` called.
- `test_both`: both backends called; both lists populated.
- `test_limit_propagates`: limit passed to both backends.

---

### T4. `scholar_search`

**File:** `src/alpha_research/mcp_server/tools/search.py`
**Backs:** `alpha_review.scholar.scholar_search_papers`
**Purpose:** Google Scholar fallback with distinct rate-limit semantics (60 req/session, 8-15s delays). Kept separate from `paper_search` because the failure modes and cost profile differ fundamentally.

```python
from pydantic import BaseModel, Field
from alpha_review.scholar import scholar_search_papers
from .._decorator import mcp_tool
from ..schemas import PaperCandidate

class ScholarSearchInput(BaseModel):
    query: str
    max_pages: int = Field(
        1, ge=1, le=3,
        description="Pages of Scholar results (rate-limited, prefer 1)",
    )
    year_lo: int | None = None
    year_hi: int | None = None

class ScholarSearchOutput(BaseModel):
    results: list[PaperCandidate]
    avg_relevance: float       # page 1 title-stem overlap with query
    pages_fetched: int

@mcp_tool(ScholarSearchInput)
async def scholar_search(input: ScholarSearchInput) -> ScholarSearchOutput:
    """Search Google Scholar with adaptive pagination and human-paced delays
    (8-15s between requests, 60-request session cap). Use ONLY when
    paper_search cannot find what you need — typically for workshop papers,
    technical reports, or theses not indexed by ArXiv/OpenAlex/S2. Prefer
    max_pages=1 unless you specifically need broader coverage. This tool
    is SLOW and may fail under load."""
    raw, avg_rel = scholar_search_papers(
        input.query, max_pages=input.max_pages,
        year_lo=input.year_lo, year_hi=input.year_hi,
    )
    return ScholarSearchOutput(
        results=[PaperCandidate(**p, source="scholar") for p in raw],
        avg_relevance=avg_rel,
        pages_fetched=min(input.max_pages, max(1, len(raw) // 10)),
    )
```

**Tests:**
- `test_single_page`: mock Scholar, verify results and avg_relevance returned.
- `test_rate_limit_handling`: mock 429 response, verify graceful return (empty or partial).

---

### T5. `survey_start`

**File:** `src/alpha_research/mcp_server/tools/survey.py`
**Backs:** `alpha_review.sdk.run_plan` + `alpha_review.sdk.run_scope`
**Purpose:** Begin a literature survey: analyze topic, define research question and themes, run pilot search. Collapses `run_plan` + `run_scope` because they are always called together (plan's output feeds scope's input).

```python
from pydantic import BaseModel, Field
from alpha_review.sdk import run_plan, run_scope
from .._decorator import mcp_tool

class SurveyStartInput(BaseModel):
    query: str = Field(..., description="Research topic or question")
    output_dir: str = Field(..., description="Directory for survey artifacts (will be created)")

class SurveyStartOutput(BaseModel):
    output_dir: str
    field_maturity: str                  # "emerging" | "established" | "mature"
    estimated_papers: int
    research_question: str
    themes: list[dict]                   # [{"name": ..., "description": ..., "papers": N}]
    pilot_papers: int

@mcp_tool(SurveyStartInput)
async def survey_start(input: SurveyStartInput) -> SurveyStartOutput:
    """Begin a new literature survey. Analyzes the topic (field maturity, paper
    estimate, config), defines the research question and themes, and runs a
    pilot search. Creates review.db at output_dir. Call this FIRST when
    starting a survey, then call survey_iterate until saturated, then
    survey_finalize. This is step 1 of 3 in the survey lifecycle."""
    plan = run_plan(input.query)
    scope = run_scope(input.query, input.output_dir, plan=plan)
    return SurveyStartOutput(
        output_dir=str(scope.output_dir),
        field_maturity=plan.field_maturity,
        estimated_papers=plan.estimated_papers,
        research_question=scope.research_question,
        themes=scope.themes,
        pilot_papers=scope.pilot_papers,
    )
```

---

### T6. `survey_iterate`

**File:** `src/alpha_research/mcp_server/tools/survey.py`
**Backs:** `alpha_review.sdk.run_search` + `alpha_review.sdk.run_read`
**Purpose:** One survey iteration: search round + read round. Returns `saturated` flag so the caller knows when to stop. Collapses `run_search` + `run_read` because they are always alternated in the survey loop.

```python
from pydantic import BaseModel, Field
from alpha_review.sdk import run_search, run_read
from .._decorator import mcp_tool

class SurveyIterateInput(BaseModel):
    output_dir: str = Field(..., description="Survey directory from survey_start")

class SurveyIterateOutput(BaseModel):
    round_num: int
    papers_added: int
    papers_total: int
    papers_screened: int
    papers_included: int
    ideas_extracted: int
    themes_count: int
    saturated: bool                      # True = ready for survey_finalize

@mcp_tool(SurveyIterateInput)
async def survey_iterate(input: SurveyIterateInput) -> SurveyIterateOutput:
    """Run one iteration of a survey: generate new search queries, fetch papers,
    screen them, extract ideas, reflect on themes. Returns saturated=True when
    coverage is sufficient for writing. Call in a loop after survey_start
    until saturated=True, then call survey_finalize. Step 2 of 3 in the
    survey lifecycle."""
    search_result = run_search(input.output_dir)
    read_result = run_read(input.output_dir)
    return SurveyIterateOutput(
        round_num=search_result.round_num,
        papers_added=search_result.papers_added,
        papers_total=search_result.papers_total,
        papers_screened=read_result.papers_screened,
        papers_included=read_result.papers_included,
        ideas_extracted=read_result.ideas_extracted,
        themes_count=read_result.themes_count,
        saturated=read_result.saturated,
    )
```

---

### T7. `survey_finalize`

**File:** `src/alpha_research/mcp_server/tools/survey.py`
**Backs:** `alpha_review.sdk.run_write`
**Purpose:** Generate the final survey artifacts: LaTeX, BibTeX, PDF.

```python
from pydantic import BaseModel, Field
from alpha_review.sdk import run_write
from .._decorator import mcp_tool

class SurveyFinalizeInput(BaseModel):
    output_dir: str

class SurveyFinalizeOutput(BaseModel):
    tex_path: str | None
    bib_path: str | None
    pdf_path: str | None
    knowledge_tex_path: str | None
    papers_cited: int
    papers_in_bib: int

@mcp_tool(SurveyFinalizeInput)
async def survey_finalize(input: SurveyFinalizeInput) -> SurveyFinalizeOutput:
    """Generate the final survey: LaTeX, BibTeX, and compiled PDF. Call ONLY
    after survey_iterate returns saturated=True. Step 3 of 3 in the
    survey lifecycle."""
    result = run_write(input.output_dir)
    return SurveyFinalizeOutput(
        tex_path=str(result.tex_path) if result.tex_path else None,
        bib_path=str(result.bib_path) if result.bib_path else None,
        pdf_path=str(result.pdf_path) if result.pdf_path else None,
        knowledge_tex_path=str(result.knowledge_tex_path) if result.knowledge_tex_path else None,
        papers_cited=result.papers_cited,
        papers_in_bib=result.papers_in_bib,
    )
```

**Survey lifecycle tests:**
- `test_survey_full_lifecycle`: start → iterate (mocked to saturate on round 2) → finalize. Verify files created.
- `test_survey_iterate_not_saturated`: saturated=False after one round; caller should continue.

---

### T8. `store_read`

**File:** `src/alpha_research/mcp_server/tools/store.py`
**Backs:** `alpha_review.models.ReviewState.query_papers` (for papers/themes) + custom SQL on our extension tables (for evaluations/findings/reviews/frontier).
**Purpose:** Unified read over the hybrid knowledge store. One tool, `record_type` discriminates.

```python
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal
from alpha_review.models import ReviewState
from alpha_research.knowledge.extension_schema import query_extension
from .._decorator import mcp_tool

RecordType = Literal["paper", "theme", "evaluation", "finding", "review", "frontier"]

class StoreReadInput(BaseModel):
    output_dir: str = Field(..., description="Directory containing review.db")
    record_type: RecordType
    filters: dict = Field(
        default_factory=dict,
        description="Type-specific filters. For 'paper': {status, theme_id, "
                    "year_min, year_max, search}. For 'evaluation': {paper_id, "
                    "min_score, dimension}. For 'finding': {cycle_id, severity}. "
                    "For 'review': {paper_id, verdict}. For 'frontier': {domain, cycle_id}.",
    )
    limit: int = Field(50, ge=1, le=1000)

class StoreReadOutput(BaseModel):
    record_type: str
    records: list[dict]
    total: int

@mcp_tool(StoreReadInput)
async def store_read(input: StoreReadInput) -> StoreReadOutput:
    """Read records from the hybrid knowledge store. record_type selects which
    table: 'paper'/'theme' come from the alpha_review layer, while 'evaluation'
    /'finding'/'review'/'frontier' come from the alpha_research extension
    tables in the same SQLite file. Use filters appropriate to each type
    (see field description). Returns list of record dicts + total count."""
    db_path = Path(input.output_dir) / "review.db"

    if input.record_type in ("paper", "theme"):
        state = ReviewState(db_path)
        try:
            if input.record_type == "paper":
                papers, total = state.query_papers(
                    status=input.filters.get("status"),
                    theme_id=input.filters.get("theme_id"),
                    year_min=input.filters.get("year_min"),
                    year_max=input.filters.get("year_max"),
                    search=input.filters.get("search"),
                    limit=input.limit,
                )
                return StoreReadOutput(
                    record_type="paper",
                    records=[p.__dict__ for p in papers],
                    total=total,
                )
            else:  # theme
                themes = state.themes
                return StoreReadOutput(
                    record_type="theme",
                    records=[{"id": t.id, "name": t.name, "description": t.description,
                              "paper_ids": t.paper_ids, "ideas": [i.__dict__ for i in t.ideas]}
                             for t in themes[:input.limit]],
                    total=len(themes),
                )
        finally:
            state.close()
    else:
        # Extension tables
        records, total = query_extension(
            db_path,
            record_type=input.record_type,
            filters=input.filters,
            limit=input.limit,
        )
        return StoreReadOutput(
            record_type=input.record_type,
            records=records,
            total=total,
        )
```

**Tests:**
- `test_read_papers_by_status`: status="included", verify filter applied.
- `test_read_themes`: verify themes list shape.
- `test_read_evaluations_by_paper`: extension table query with paper_id filter.
- `test_invalid_record_type`: Pydantic catches before handler.
- `test_empty_filters`: returns all records up to limit.

---

### T9. `store_write`

**File:** `src/alpha_research/mcp_server/tools/store.py`
**Backs:** Custom INSERT on extension tables in `src/alpha_research/knowledge/extension_schema.py`.
**Purpose:** Write extension records (evaluation, finding, review, frontier). Papers and themes are written by `alpha_review.sdk` internals during survey runs — the LLM does not write papers directly.

```python
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Literal
from alpha_research.knowledge.extension_schema import insert_extension
from .._decorator import mcp_tool

WritableRecordType = Literal["evaluation", "finding", "review", "frontier"]

class StoreWriteInput(BaseModel):
    output_dir: str
    record_type: WritableRecordType
    data: dict = Field(
        ...,
        description="Serialized record. Required fields depend on record_type: "
                    "evaluation needs {paper_id, cycle_id, rubric_scores, "
                    "task_chain, significance_assessment}; finding needs "
                    "{cycle_id, type, content, evidence_paper_ids, severity}; "
                    "review needs {paper_id, version, findings, verdict}; "
                    "frontier needs {cycle_id, domain, reliable, sometimes, cant_yet}.",
    )

class StoreWriteOutput(BaseModel):
    record_id: str
    stored: bool

@mcp_tool(StoreWriteInput)
async def store_write(input: StoreWriteInput) -> StoreWriteOutput:
    """Write a record to the alpha_research extension tables (evaluations,
    findings, reviews, frontier snapshots). Papers are written by survey_*
    tools — do not use store_write for papers. Returns the assigned record_id.
    Validates required fields per record_type and will reject malformed data."""
    db_path = Path(input.output_dir) / "review.db"
    record_id = insert_extension(
        db_path,
        record_type=input.record_type,
        data=input.data,
    )
    return StoreWriteOutput(record_id=record_id, stored=bool(record_id))
```

**Extension schema — `src/alpha_research/knowledge/extension_schema.py`:**
```python
"""Extension tables that live in the same SQLite file as alpha_review.ReviewState."""
import json
import sqlite3
import uuid
from pathlib import Path
from typing import Any

_EXTENSION_DDL = """
CREATE TABLE IF NOT EXISTS ar_evaluations (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    cycle_id TEXT,
    rubric_scores TEXT,        -- JSON: {"B.1": {score, confidence, evidence}, ...}
    task_chain TEXT,           -- JSON: {task, problem, challenge, approach, one_sentence}
    significance_assessment TEXT,  -- JSON: significance_screen output
    human_flags TEXT,          -- JSON list
    created_at REAL
);
CREATE TABLE IF NOT EXISTS ar_findings (
    id TEXT PRIMARY KEY,
    cycle_id TEXT,
    type TEXT,                 -- "fatal" | "serious" | "minor"
    content TEXT,
    evidence_paper_ids TEXT,   -- JSON list
    severity TEXT,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS ar_reviews (
    id TEXT PRIMARY KEY,
    paper_id TEXT NOT NULL,
    version INTEGER DEFAULT 1,
    findings TEXT,             -- JSON list of finding IDs
    verdict TEXT,
    confidence TEXT,
    created_at REAL
);
CREATE TABLE IF NOT EXISTS ar_frontier (
    id TEXT PRIMARY KEY,
    cycle_id TEXT,
    domain TEXT,
    reliable TEXT,             -- JSON list
    sometimes TEXT,            -- JSON list
    cant_yet TEXT,             -- JSON list
    created_at REAL
);
CREATE INDEX IF NOT EXISTS idx_ar_eval_paper ON ar_evaluations(paper_id);
CREATE INDEX IF NOT EXISTS idx_ar_review_paper ON ar_reviews(paper_id);
CREATE INDEX IF NOT EXISTS idx_ar_frontier_domain ON ar_frontier(domain);
"""

_REQUIRED_FIELDS = {
    "evaluation": {"paper_id", "rubric_scores"},
    "finding": {"cycle_id", "type", "content", "severity"},
    "review": {"paper_id", "verdict"},
    "frontier": {"cycle_id", "domain"},
}

def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_EXTENSION_DDL)

def insert_extension(db_path: Path, record_type: str, data: dict) -> str:
    required = _REQUIRED_FIELDS[record_type]
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing required fields for {record_type}: {missing}")
    rid = f"{record_type[:3]}_{uuid.uuid4().hex[:10]}"
    import time
    conn = sqlite3.connect(db_path)
    try:
        _ensure_schema(conn)
        if record_type == "evaluation":
            conn.execute(
                "INSERT INTO ar_evaluations(id, paper_id, cycle_id, rubric_scores, "
                "task_chain, significance_assessment, human_flags, created_at) "
                "VALUES(?,?,?,?,?,?,?,?)",
                (rid, data["paper_id"], data.get("cycle_id", ""),
                 json.dumps(data["rubric_scores"]),
                 json.dumps(data.get("task_chain", {})),
                 json.dumps(data.get("significance_assessment", {})),
                 json.dumps(data.get("human_flags", [])),
                 time.time()),
            )
        elif record_type == "finding":
            conn.execute(
                "INSERT INTO ar_findings(id, cycle_id, type, content, "
                "evidence_paper_ids, severity, created_at) VALUES(?,?,?,?,?,?,?)",
                (rid, data["cycle_id"], data["type"], data["content"],
                 json.dumps(data.get("evidence_paper_ids", [])),
                 data["severity"], time.time()),
            )
        elif record_type == "review":
            conn.execute(
                "INSERT INTO ar_reviews(id, paper_id, version, findings, "
                "verdict, confidence, created_at) VALUES(?,?,?,?,?,?,?)",
                (rid, data["paper_id"], data.get("version", 1),
                 json.dumps(data.get("findings", [])),
                 data["verdict"], data.get("confidence", ""), time.time()),
            )
        elif record_type == "frontier":
            conn.execute(
                "INSERT INTO ar_frontier(id, cycle_id, domain, reliable, "
                "sometimes, cant_yet, created_at) VALUES(?,?,?,?,?,?,?)",
                (rid, data["cycle_id"], data["domain"],
                 json.dumps(data.get("reliable", [])),
                 json.dumps(data.get("sometimes", [])),
                 json.dumps(data.get("cant_yet", [])),
                 time.time()),
            )
        conn.commit()
        return rid
    finally:
        conn.close()

def query_extension(db_path: Path, record_type: str, filters: dict,
                    limit: int) -> tuple[list[dict], int]:
    """Query extension tables. Filters are record-type specific."""
    table_map = {
        "evaluation": "ar_evaluations",
        "finding": "ar_findings",
        "review": "ar_reviews",
        "frontier": "ar_frontier",
    }
    table = table_map[record_type]
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        _ensure_schema(conn)
        where_clauses = []
        params = []
        for k, v in filters.items():
            where_clauses.append(f"{k}=?")
            params.append(v)
        where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"
        total = conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE {where_sql}", params
        ).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {where_sql} LIMIT ?",
            params + [limit],
        ).fetchall()
        return [dict(row) for row in rows], total
    finally:
        conn.close()
```

**Tests:**
- `test_write_evaluation_happy`: insert evaluation, verify record returned, query round-trips.
- `test_write_missing_required`: missing `rubric_scores` → ValueError from handler.
- `test_write_all_four_types`: evaluation, finding, review, frontier each insertable.
- `test_query_extension_filters`: filter by paper_id on ar_evaluations.

---

### T10-T11. Experiment tools (Phase 3)

**File:** `src/alpha_research/mcp_server/tools/experiment.py`

```python
class ExperimentLaunchInput(BaseModel):
    config_path: str                 # path to experiment config YAML/JSON
    env: Literal["sim", "real"] = "sim"
    seeds: list[int] = Field(default_factory=lambda: [0, 1, 2])
    dry_run: bool = False

class ExperimentHandle(BaseModel):
    job_id: str
    status: Literal["queued", "running", "failed", "completed"]
    log_path: str
    n_trials_planned: int

class ExperimentQueryInput(BaseModel):
    job_id: str | None = None
    experiment_dir: str | None = None
    metrics: list[str] | None = None

class ExperimentResults(BaseModel):
    status: str
    metrics: dict[str, float]        # aggregated
    per_trial: list[dict]
    raw_logs: str
    failure_cases: list[dict]
```

Phase 3 reference implementations:
- **MuJoCo**: subprocess launches, result files in `$EXP_DIR/results.json`
- **Isaac Gym**: WandB integration, pull from WandB API
- **ROS / real robot**: `rosbag` files + per-trial CSVs

---

### Tool registration — `src/alpha_research/mcp_server/tools/__init__.py`

```python
from .search import paper_search, paper_graph, scholar_search
from .content import paper_fetch
from .survey import survey_start, survey_iterate, survey_finalize
from .store import store_read, store_write
# from .experiment import experiment_launch, experiment_query  # Phase 3

ALL_TOOLS = [
    # Discovery (3)
    paper_search,
    paper_graph,
    scholar_search,
    # Content (1)
    paper_fetch,
    # Survey lifecycle (3)
    survey_start,
    survey_iterate,
    survey_finalize,
    # Hybrid store (2)
    store_read,
    store_write,
]
```

### MCP server entry point — `src/alpha_research/mcp_server/server.py`

```python
"""alpha_research MCP server — stdio transport for Claude Code."""
import asyncio
import logging
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from .tools import ALL_TOOLS

server = Server("alpha_research")
logger = logging.getLogger(__name__)

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name=t.__name__,
            description=t.__doc__ or f"{t.__name__} tool",
            inputSchema=t.__input_model__.model_json_schema(),
        )
        for t in ALL_TOOLS
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    tool = next((t for t in ALL_TOOLS if t.__name__ == name), None)
    if tool is None:
        raise ValueError(f"Unknown tool: {name}")
    input_obj = tool.__input_model__(**arguments)
    output = await tool(input_obj)
    return [TextContent(type="text", text=output.model_dump_json())]

def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.run(stdio_server(server))

if __name__ == "__main__":
    main()
```

### Decorator — `src/alpha_research/mcp_server/_decorator.py`

```python
from functools import wraps
from typing import Type
from pydantic import BaseModel

def mcp_tool(input_model: Type[BaseModel]):
    """Attach input schema to a tool function for MCP registration."""
    def decorator(func):
        @wraps(func)
        async def wrapper(arg):
            if isinstance(arg, dict):
                arg = input_model(**arg)
            return await func(arg)
        wrapper.__input_model__ = input_model
        return wrapper
    return decorator
```

---
## Part II. Skill Specifications

Each skill lives at `.claude/skills/<slug>/SKILL.md`. Below are complete frontmatter + body specifications for all 12 skills. Skills that need extended reference material get a companion `reference.md` in the same folder.

### S1. `literature-survey`

**Path:** `.claude/skills/literature-survey/SKILL.md`

```markdown
---
name: literature-survey
description: Conduct a systematic literature survey on a research topic — from
             topic planning through scope definition, iterative paper
             collection, screening, to final LaTeX survey generation. Use
             when the user asks for a "landscape survey", "literature review",
             or "what's out there on X".
allowed-tools: mcp__alpha_research__survey_start,
               mcp__alpha_research__survey_iterate,
               mcp__alpha_research__survey_finalize,
               mcp__alpha_research__paper_search,
               mcp__alpha_research__paper_fetch,
               mcp__alpha_research__store_read,
               mcp__alpha_research__store_write,
               Read, Write, Bash
model: claude-sonnet-4-6
---

# Literature Survey

## When to use
Invoked when the researcher needs a systematic map of a subfield: who's
publishing what, which approaches exist, claimed results, where groups are
heading. Maps to the SIGNIFICANCE stage of the research state machine and
supports all downstream stages.

## Your job
Produce a structured survey that goes beyond the `alpha_review` default by
layering our domain-specific rubric on top.

## Process

### Phase A — Delegate to `alpha_review` for coverage
1. Call `survey_start(query, output_dir)` to plan the topic and define the scope.
   Output_dir should be `output/<sanitized_topic>/`.
2. Loop:
   - Call `survey_iterate(output_dir)`
   - Stop when the result's `saturated=True` or after 5 rounds.

### Phase B — Apply alpha_research rubric
3. Use `store_read(output_dir, record_type="paper", filters={"status": "included"})`
   to get the papers alpha_review selected.
4. For each paper, invoke the `paper-evaluate` skill (via Task tool or direct
   prompt) to score B.1-B.7 rubric dimensions with evidence.
5. Persist evaluations via `store_write(output_dir, record_type="evaluation", data=...)`.

### Phase C — Synthesize
6. Call `survey_finalize(output_dir)` for the LaTeX survey.
8. Generate an additional alpha_research report with:
   - Approach taxonomy (grouped by challenge type from research_guideline §2.7)
   - Capability frontier (reliable / sometimes / can't-yet)
   - Recurring gaps (invoke `gap-analysis` skill)
   - Significance assessment (flag all as requiring human confirmation)

## Output
- `output/<topic>/review_grounded.tex` + `.bib` + `.pdf` (from alpha_review)
- `output/<topic>/alpha_research_report.md` (our rubric-based synthesis)
- Persisted evaluations in the extension tables

## Honesty protocol
You cannot independently judge significance, formalization quality, or physical
feasibility. Flag all such assessments as `human_flag=true`. Your added value
over alpha_review is the systematic rubric application and the adversarial
cross-check — not a new judgment layer.

## References
- `guidelines/research_guideline.md` Appendix B (evaluation rubric)
- `guidelines/research_plan.md` SM-1 through SM-5 (state machines)
- `../alpha_review/alpha_review/sdk.py` (SDK entry points)
```

---

### S2. `significance-screen`

**Path:** `.claude/skills/significance-screen/SKILL.md`

```markdown
---
name: significance-screen
description: Evaluate whether a research problem is worth pursuing. Apply the
             Hamming, Consequence, Durability, and Compounding tests from
             research_guideline §2.2. Use when the user asks "is this problem
             worth working on" or "should I work on X?"
allowed-tools: mcp__alpha_research__paper_search,
               mcp__alpha_research__paper_fetch,
               mcp__alpha_research__paper_graph,
               mcp__alpha_research__store_read,
               Read
model: claude-opus-4-6
---

# Significance Screen

## When to use
User proposes a candidate problem and asks whether it's worth committing to.
Maps to SIGNIFICANCE stage of the research state machine. This is the most
commonly-skipped step in average research — your job is to ensure it doesn't
get skipped.

## The four tests (from research_guideline.md §2.2)

### 1. Hamming Test (necessity)
- Is the problem on the researcher's Hamming list of important unsolved problems?
- Is there a reasonable attack (solution would matter AND viable path exists)?
- Would solving it generate MORE interest over time, not less?
  (Sim-to-real for rigid pick-and-place is becoming LESS interesting as
  foundation models improve. Contact-rich manipulation under uncertainty is
  becoming MORE interesting.)

### 2. Consequence Test (impact)
- If magically solved overnight, what concretely changes?
- Name a specific downstream system, capability, or understanding that improves.
- REJECT "others would cite us" as not-an-answer. Demand concreteness.

### 3. Durability Test
- Will a 10x bigger model or 10x more data trivially solve this in 24 months?
- Does it require structural insight that resists scaling?

### 4. Compounding Test (portfolio)
- Does solving this enable OTHER research?
  - High-value: representations that transfer, formal frameworks, data infra, safety guarantees
  - Low-value: task-specific controllers, benchmark tweaks, marginal accuracy

## Process

1. `paper_search(query=<problem>, limit_per_source=15, year_lo=2023)` — find
   recent work on this problem.
2. For the top 5 hits, call `paper_fetch` to get full text.
3. For 2-3 seminal prior papers, call `paper_graph(direction="citations")` to
   check impact trajectory (is the field moving toward or away from this area?).
4. Call `store_read(record_type="evaluation", filters={"search": "<keywords>"})`
   to see if we have prior evaluations of related work.
5. For EACH of the four tests, produce:
   - `score: int` (1-5)
   - `evidence: list[str]` (specific quotes / citation counts / trend data)
   - `confidence: "high" | "medium" | "low"`
   - `human_flag: bool` — TRUE if you cannot independently verify

## Output format

```json
{
  "problem": "...",
  "hamming": {"score": 4, "evidence": [...], "confidence": "medium", "human_flag": true},
  "consequence": {"score": 5, "evidence": [...], "confidence": "high", "human_flag": false},
  "durability": {"score": 3, "evidence": [...], "confidence": "medium", "human_flag": true},
  "compounding": {"score": 4, "evidence": [...], "confidence": "medium", "human_flag": true},
  "overall_recommendation": "proceed with caveats" | "proceed" | "do not proceed",
  "human_checkpoint_required": true,
  "notes": "..."
}
```

## Honesty protocol
You CANNOT judge actual significance — that requires the researcher's Hamming
list and field taste. Your job is to verify that significance ARGUMENTS exist
and are plausible, and to FLAG assessments that require human judgment.
ALWAYS set `human_flag=true` for the Hamming test. Concrete, falsifiable
consequence claims CAN be verified (set `human_flag=false` when you find a
specific downstream system named).

## References
- `guidelines/research_guideline.md` §2.2 (significance tests)
- `guidelines/review_guideline.md` §3.1 (significance attack vectors)
- `guidelines/review_plan.md` §1.2 (significance metrics)
```

---

### S3. `formalization-check`

```markdown
---
name: formalization-check
description: Assess whether a research problem has a proper formal mathematical
             definition. Detects formalization level, identifies framework,
             optionally verifies math with sympy. Use when user asks "is this
             well-formalized?" or to check a paper's problem statement.
allowed-tools: mcp__alpha_research__paper_fetch,
               mcp__alpha_research__paper_search,
               mcp__alpha_research__store_read,
               Bash, Read
model: claude-opus-4-6
---

# Formalization Check

## When to use
Applied to a paper or a proposed problem. Maps to FORMALIZE stage of the
research state machine and to review attack vectors §3.2.

Per Tedrake: "If you can't write the math, you don't understand the problem."

## Process

1. If input is a paper: `paper_fetch(paper_id)`. If input is a problem statement,
   request that the user provide it.
2. Classify formalization level:
   - `formal_math` — explicit objective, variables, constraints, information structure
   - `semi_formal` — some math but key pieces are prose
   - `prose_only` — English description only
   - `absent` — no attempt at formal statement
3. If `formal_math` or `semi_formal`:
   - Identify framework: MDP / POMDP / constrained optimization / Bayesian inference / etc.
   - Extract: objective function, decision variables, constraints, information structure (what's observable).
   - Identify exploited structure: convexity / symmetries / decomposability / sparsity / low-dimensional manifolds.
4. Optionally verify mathematical consistency:
   - Use `Bash` to run a Python/sympy script that checks equation consistency.
   - Example: if the paper claims convexity, verify the Hessian is PSD.
5. Check fit against the problem: does the framework match reality? Common mismatches:
   - MDP for partially-observable problem → should be POMDP
   - Deterministic for stochastic dynamics
   - Continuous for hybrid (contact-switching) problems
6. Search for similar formalizations: `paper_search(<framework> <problem keywords>)`
   to compare.

## Output format

```json
{
  "level": "formal_math" | "semi_formal" | "prose_only" | "absent",
  "framework": "MDP" | "POMDP" | "constrained_opt" | ...,
  "objective": "...",
  "variables": [...],
  "constraints": [...],
  "info_structure": "...",
  "exploited_structure": ["convexity", "SE(3) symmetry", ...],
  "assumptions": [...],
  "framework_mismatch": "none" | "minor" | "major",
  "mismatch_details": "...",
  "sympy_verification": {"run": true, "passed": true, "notes": "..."},
  "confidence": "high" | "medium" | "low",
  "human_flag": true   // formalization quality requires human math intuition
}
```

## Honesty protocol
You can detect PRESENCE or ABSENCE of formal statements with high confidence.
You CANNOT deeply judge whether a formalization captures the RIGHT structure
— that requires mathematical intuition the researcher must provide. ALWAYS
set `human_flag=true`. Provide strong signal but defer judgment.

## References
- `guidelines/research_guideline.md` §2.4, §3.1 (formalization standards)
- `guidelines/review_guideline.md` §3.2 (formalization attack vectors)
- `guidelines/review_plan.md` §1.3 (formalization metrics)
```

---

### S4-S12. Remaining skills (condensed)

Full frontmatter + key sections for each. Each skill follows the same structure as S1-S3.

#### S4. `diagnose-system`
- **Trigger:** "Run minimal system, observe failures, map to formal structure"
- **Stage:** DIAGNOSE
- **Tools:** `experiment_launch`, `experiment_query`, `Bash` (for data analysis), `Read`
- **Model:** Sonnet
- **Key instruction:** Produce SPECIFIC failure descriptions ("depth can't resolve <2mm") not vague ones ("grasping fails"). Map each failure to a term in the formal problem structure. Classify failures into: perception / planning / execution / physics.
- **Output:** `DiagnosisReport` with `failure_taxonomy`, `failure_to_formalism_map`, `dominant_failure_mode`, `suggested_next_stage` (one of: proceed to CHALLENGE, backward to FORMALIZE via t4, etc.)

#### S5. `challenge-articulate`
- **Trigger:** "From diagnosed failures, identify the structural barrier"
- **Stage:** CHALLENGE
- **Tools:** `paper_search`, `paper_fetch`, `store_read`, `Read`
- **Model:** Opus
- **Key instruction:** Challenge must be STRUCTURAL (not a resource complaint), must CONSTRAIN the solution class (if someone understood only the challenge, they should predict the method class). Apply the challenge-type → method-class table from research_guideline.md §2.7.
- **Output:** `ChallengeReport` with `challenge_statement`, `challenge_type` (sample_complexity / distribution_shift / combinatorial_explosion / model_uncertainty / sensing_limitation / hardware_limitation / discontinuity / long_horizon_credit / grounding_gap), `implied_solution_class`, `prior_work_addressing_it`.

#### S6. `method-survey`
- **Trigger:** "Survey existing methods within the implied solution class"
- **Stage:** APPROACH
- **Tools:** `paper_search`, `paper_graph`, `paper_fetch`, `store_read`
- **Model:** Sonnet
- **Key instruction:** Focus search WITHIN the solution class implied by the challenge. For each method extract: performance claims, assumptions, complexity, practical viability. Build a comparison table.
- **Output:** `MethodSurveyReport` with `methods_in_class[]`, `comparison_table`, `gaps_in_class`, `suggested_approach_direction`.

#### S7. `experiment-audit`
- **Trigger:** "Check statistical sufficiency, baselines, ablations, venue thresholds"
- **Stage:** VALIDATE
- **Tools:** `experiment_query`, `Bash` (statistical tests), `paper_search`, `Read`
- **Model:** Sonnet
- **Key instruction:** Apply venue-specific thresholds from review_plan.md §1.6. Name the strongest MISSING baseline. Use Bash to run statistical tests (scipy for CI, power analysis). Check ablation isolation: does removing the claimed contribution actually degrade performance?
- **Output:** `AuditReport` with per-check pass/fail, `missing_baselines[]`, `statistical_issues[]`, `overclaiming_flags[]`, `venue_threshold_assessment`.

#### S8. `adversarial-review`
- **Trigger:** "Full adversarial review at top-venue standard"
- **Stage:** VALIDATE (self-review)
- **Tools:** `paper_fetch`, `paper_search`, `paper_graph`, `Bash`, `Read`, Task (to invoke sub-skills)
- **Model:** Opus
- **Key instruction:** Graduated pressure per review_plan.md §3:
  - **Iteration 1**: structural scan only (5 min). Extract the logical chain. Quick fatal-flaw scan per Appendix A.1.
  - **Iteration 2**: full review with all six attack vectors §3.1-§3.6. Call `concurrent-work-check` skill. Call `experiment-audit` skill.
  - **Iteration 3+**: focused re-review. Check each previous finding: addressed/partially/not/regressed.
  - Compute verdict MECHANICALLY from findings (not gestalt) per review_plan.md §1.9.
- **Output:** `Review` with chain_extraction, steel_man (≥3 sentences), findings (classified fatal/serious/minor), verdict, confidence, questions_for_authors.

#### S9. `paper-evaluate`
- **Trigger:** "Evaluate a single paper against Appendix B rubric"
- **Stage:** per-paper, used throughout
- **Tools:** `paper_fetch`, `paper_graph`, `store_read`, `store_write`
- **Model:** Haiku (skim) → Sonnet (deep). Two-pass invocation.
- **Key instruction:** First pass = skim (title + abstract + conclusion) to score relevance 0-1 and decide whether to proceed. Second pass = full rubric B.1-B.7 with evidence quotes, confidence per dimension, task chain extraction. Cross-check novelty via `store_read(record_type="paper")` and `store_read(record_type="evaluation")`. Metadata (title, authors, venue, year) comes from `paper_fetch` directly — no separate details call needed.
- **Output:** `Evaluation` with rubric_scores (B.1-B.7), task_chain, significance_assessment, human_flags, cross_check_notes.

#### S10. `concurrent-work-check`
- **Trigger:** "Detect if problem already solved by concurrent/recent work"
- **Stage:** APPROACH (before commitment), VALIDATE (before submission)
- **Tools:** `paper_search`, `paper_graph`, `scholar_search`, `paper_fetch`
- **Model:** Sonnet
- **Key instruction:** Search with multiple query formulations (problem, approach, key terms). For high-overlap hits, fetch full text for detailed comparison. Use `scholar_search` as last resort for workshop/technical reports. Output differentiation plan if overlap is significant.
- **Output:** `ConcurrentWorkReport` with `overlapping_papers[]`, `overlap_degree` (none/minor/significant/scooped), `differentiation_needed`.

#### S11. `gap-analysis`
- **Trigger:** "Identify recurring limitations across a body of work"
- **Stage:** SIGNIFICANCE, CHALLENGE
- **Tools:** `store_read`, `paper_search`
- **Model:** Opus
- **Key instruction:** Aggregate limitations appearing in ≥3 papers. For each candidate gap, search to verify it's a REAL gap (not just missed papers). Cross-reference with research_guideline.md's Hamming list concepts. Propose directions with significance test applied.
- **Output:** `GapReport` with `recurring_limitations[]`, `unsolved_failures[]`, `proposed_directions[]` (each with significance score).

#### S12. `frontier-mapping`
- **Trigger:** "Map capability frontier: reliable / sometimes / can't-yet"
- **Stage:** SIGNIFICANCE (strategic planning)
- **Tools:** `store_read`, `paper_search`, `store_write`
- **Model:** Sonnet
- **Key instruction:** Classify capabilities for a specific domain into reliable / sometimes / can't-yet. Use the three-tier structure from research_guideline.md §5.1 Axis 3. If a previous snapshot exists, compute the diff (what moved between tiers).
- **Output:** `FrontierReport` with `reliable[]`, `sometimes[]`, `cant_yet[]`, `shifts_since_last[]`.

---

## Part III. Test Strategy

### Test levels

1. **Unit tests** — each tool with mocked external APIs
2. **Integration tests** — tool chains (e.g., search → fetch → store)
3. **Skill fixture tests** — invoke each skill with a known input, verify output schema + key assertions
4. **End-to-end tests** — full pipeline on a small topic (takes ~5 min per run)
5. **Calibration tests** — compare skill outputs against human-graded ground truth (existing T10)

### Mocking strategy

`alpha_review` functions get mocked at the boundary. We don't test `alpha_review` itself — it has its own test suite.

```python
# tests/test_mcp_server/test_search_tools.py
import pytest
from unittest.mock import patch
from alpha_research.mcp_server.tools.search import paper_search, PaperSearchInput

@pytest.mark.asyncio
@patch("alpha_research.mcp_server.tools.search.search_all")
async def test_paper_search_basic(mock_search_all):
    mock_search_all.return_value = [
        {"paperId": "1", "title": "Test", "abstract": "a", "authors": [],
         "year": 2025, "venue": "RSS", "url": "", "doi": "", "citationCount": 10}
    ]
    result = await paper_search(PaperSearchInput(query="test"))
    assert len(result.results) == 1
    assert result.results[0].title == "Test"
```

### Skill fixture tests

```python
# tests/test_skills/test_significance_screen.py
import subprocess
import json

def test_significance_screen_output_schema():
    result = subprocess.run(
        ["claude", "-p", "Use the significance-screen skill on the problem: "
         "'task-oriented grasping of deformable objects'"],
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0
    # Parse the JSON output from claude's response
    output = extract_json(result.stdout)
    assert "hamming" in output
    assert "consequence" in output
    assert "durability" in output
    assert "compounding" in output
    assert output["hamming"]["human_flag"] is True  # always flagged
```

### Coverage targets

| Layer | Target |
|---|---|
| MCP tool handlers | 100% line, 95% branch |
| Skill fixtures (happy path per skill) | 12/12 skills |
| End-to-end pipeline | 1 full run in CI (cached) |

---

## Part IV. Phased Delivery

### Phase 1 — Foundation (Week 1-2)

**Goal:** MCP server runs, wraps all `alpha_review` tools, replaces our duplicated code.

| Task | File(s) | Acceptance |
|---|---|---|
| P1.1 Add `alpha_review` dependency | `pyproject.toml` | `import alpha_review` works in alpha_research env |
| P1.2 Scaffold MCP server structure | `src/alpha_research/mcp_server/` | Empty server starts via `alpha-research-mcp` |
| P1.3 Implement 3 search tools (paper_search, paper_graph, scholar_search) | `mcp_server/tools/search.py` | 3 tools exposed; all unit tests pass |
| P1.4 Migrate `paper_fetch` with Unpaywall fallback | `mcp_server/tools/content.py` | Extraction quality preserved; fallback test passes; metadata included in response |
| P1.5 Implement 3 survey lifecycle tools | `mcp_server/tools/survey.py` | survey_start → survey_iterate (loop) → survey_finalize integration test runs on small topic |
| P1.6 Implement 2 store tools + extension schema | `mcp_server/tools/store.py`, `knowledge/extension_schema.py` | store_read handles all 6 record types; store_write handles 4 writable types; extension tables created alongside ReviewState |
| P1.7 Delete superseded tool files | `tools/arxiv_search.py`, `tools/semantic_scholar.py` | Tests still pass (those testing the deleted code are removed/ported) |
| P1.8 Refactor knowledge store into hybrid schema | `knowledge/store.py`, `knowledge/extension_schema.py` | Papers table comes from alpha_review; extensions from us |
| P1.9 Register MCP server in project config | `.claude/.mcp.json` | Claude Code sees all tools |
| P1.10 End-to-end smoke test | `tests/test_mcp_server/test_server.py` | All tools callable via MCP protocol |

**Exit criteria:** `pytest` passes. `claude -p "search for recent tactile manipulation papers"` works and returns results via MCP.

### Phase 2 — Skills (Week 3-4)

**Goal:** 12 skills implemented as `SKILL.md` files, tested end-to-end.

| Task | File(s) | Acceptance |
|---|---|---|
| P2.1 Write S1 `literature-survey` SKILL.md | `.claude/skills/literature-survey/` | Invoked via `/literature-survey`, delegates to alpha_review SDK, adds rubric layer |
| P2.2 Write S2 `significance-screen` SKILL.md | `.claude/skills/significance-screen/` | Produces structured JSON output; human_flag set correctly |
| P2.3 Write S3 `formalization-check` SKILL.md | `.claude/skills/formalization-check/` | Detects level; sympy verification works via Bash |
| P2.4 Write S5 `challenge-articulate` SKILL.md | `.claude/skills/challenge-articulate/` | Produces challenge_type from §2.7 table |
| P2.5 Write S6 `method-survey` SKILL.md | `.claude/skills/method-survey/` | Comparison table produced; gaps identified |
| P2.6 Write S8 `adversarial-review` SKILL.md | `.claude/skills/adversarial-review/` | Graduated pressure works; verdict computed mechanically |
| P2.7 Write S9 `paper-evaluate` SKILL.md | `.claude/skills/paper-evaluate/` | Rubric B.1-B.7 scored; two-pass (Haiku skim → Sonnet deep) |
| P2.8 Write S10 `concurrent-work-check` SKILL.md | `.claude/skills/concurrent-work-check/` | Overlap degree classified |
| P2.9 Write S11 `gap-analysis` SKILL.md | `.claude/skills/gap-analysis/` | ≥3 paper aggregation verified |
| P2.10 Write S12 `frontier-mapping` SKILL.md | `.claude/skills/frontier-mapping/` | Three-tier classification produced |
| P2.11 Skill fixture tests | `tests/test_skills/` | 12 skills, 1 happy-path test each |
| P2.12 Migrate existing prompts | delete content from `prompts/*.py`, reference skills instead | Agents still work |

**Exit criteria:** `/significance-screen "contact-rich manipulation"` produces a valid JSON report. All 12 skill fixture tests pass.

### Phase 3 — Experiment interface (Week 5-6, optional)

Only if lab infrastructure is available.

| Task | File(s) | Acceptance |
|---|---|---|
| P3.1 Implement `experiment_launch` reference (MuJoCo) | `mcp_server/tools/experiment.py` | Launches a MuJoCo sim, returns job_id |
| P3.2 Implement `experiment_query` (WandB + CSV) | `mcp_server/tools/experiment.py` | Reads metrics from WandB API and local CSV |
| P3.3 Write S4 `diagnose-system` SKILL.md | `.claude/skills/diagnose-system/` | End-to-end: launch sim → collect results → classify failures |
| P3.4 Write S7 `experiment-audit` SKILL.md | `.claude/skills/experiment-audit/` | Statistical tests pass; venue thresholds applied |

### Phase 4 — Cross-LLM (Week 7-8)

| Task | File(s) | Acceptance |
|---|---|---|
| P4.1 Implement `skill_translator.py` | `adapters/skill_translator.py` | SKILL.md → system prompt conversion; unit tests |
| P4.2 `ClaudeAdapter` | `adapters/claude.py` | Passes through (native) |
| P4.3 `OpenAIAdapter` | `adapters/openai.py` | Wires MCP tools via OpenAI Agents SDK; translates skills to `instructions` |
| P4.4 `GeminiAdapter` | `adapters/gemini.py` | MCP via adapter; system_instruction from skills |
| P4.5 `LangChainAdapter` | `adapters/langchain.py` | `MCPToolkit` + `ChatPromptTemplate` |
| P4.6 Cross-provider skill test matrix | `tests/test_adapters/` | `significance-screen` works on Claude + GPT-4o + Gemini Pro + Llama 3.3 |

---

## Part V. Open questions

Decisions to make before Phase 1 starts:

1. **Hybrid schema ownership.** Extension tables (`evaluations`, `findings`, `reviews`, `frontier_snapshots`) — do they live in the same `review.db` as `alpha_review.ReviewState`, or a separate `alpha_research.db` in the same project directory? **Tentative:** same file, separate connections, for simpler FK semantics.
2. **Skill/agent boundary.** Today our agents (ResearchAgent, ReviewAgent) have big system prompts. Should they become thin wrappers that just invoke skills, or keep their prompts and *reference* skills? **Tentative:** migrate incrementally — agents keep orchestration logic, system prompts shrink as skills absorb the domain knowledge.
3. **SKILL.md as single source of truth vs. parity with `prompts/*.py`.** During transition, both exist. Risk of drift. **Tentative:** delete `prompts/*.py` content in P2.12 once skills are proven.
4. **MCP server lifecycle in tests.** Spawn a real server for integration tests, or mock the MCP layer? **Tentative:** mock MCP layer for unit tests, spawn real server in one end-to-end test.
5. **Model pinning.** Should each skill pin a specific model version (e.g., `claude-opus-4-6`) or be flexible? **Tentative:** pin in frontmatter; override at invocation time via `--model`.
6. **alpha_review updates.** Since `alpha_review` is a file-path dependency at `../alpha_review`, version drift is a risk. **Mitigation:** pin to a git SHA in pyproject.toml once both projects stabilize.

---

## Part VI. Acceptance checklist

A tool is **done** when:
- [ ] Pydantic input and output models defined
- [ ] Async handler implemented
- [ ] `@mcp_tool` decorator applied
- [ ] Registered in `ALL_TOOLS`
- [ ] Description string written (LLM-facing, 3-4 sentences)
- [ ] Unit test with mocked backend
- [ ] Integration test (if it calls real APIs — cached)
- [ ] Appears in `/mcp` list in Claude Code

A skill is **done** when:
- [ ] `SKILL.md` at `.claude/skills/<slug>/SKILL.md`
- [ ] Frontmatter validates: `name`, `description`, `allowed-tools`, optional `model`
- [ ] Body has: When to use / Your job / Process / Output format / Honesty protocol / References
- [ ] Body references specific sections of `guidelines/*.md`
- [ ] Fixture test: `/slug <input>` produces valid JSON matching the declared output format
- [ ] If skill delegates to other skills, Task tool is in `allowed-tools`

The system is **done** when:
- [ ] All 9 Phase-1/2 tools implemented (11 with Phase 3 experiments)
- [ ] All 12 skills implemented
- [ ] 494 existing tests still pass (no regression)
- [ ] New test suite for MCP tools passes
- [ ] New test suite for skills passes
- [ ] End-to-end: `claude -p "survey tactile manipulation for deformable objects"` produces a LaTeX survey + rubric report
- [ ] Cross-LLM (Phase 4): same skill works on at least 2 non-Claude providers

---

## Part VII. Source mapping

Where each component lives after implementation:

| Component | File |
|---|---|
| MCP server entry | `src/alpha_research/mcp_server/server.py` |
| Tool decorator | `src/alpha_research/mcp_server/_decorator.py` |
| Search tools | `src/alpha_research/mcp_server/tools/search.py` |
| Content tools | `src/alpha_research/mcp_server/tools/content.py` |
| Survey tools | `src/alpha_research/mcp_server/tools/survey.py` |
| Store tools | `src/alpha_research/mcp_server/tools/store.py` |
| Experiment tools (P3) | `src/alpha_research/mcp_server/tools/experiment.py` |
| Extension schema | `src/alpha_research/knowledge/extension_schema.py` |
| Skill translator (P4) | `src/alpha_research/adapters/skill_translator.py` |
| Provider adapters (P4) | `src/alpha_research/adapters/{claude,openai,gemini,langchain}.py` |
| Skills | `.claude/skills/<slug>/SKILL.md` |
| MCP registration | `.claude/.mcp.json` |
| Tool tests | `tests/test_mcp_server/` |
| Skill tests | `tests/test_skills/` |
| Adapter tests (P4) | `tests/test_adapters/` |
