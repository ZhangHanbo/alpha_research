"""Shared toolset for research and review agents."""

from alpha_research.tools.arxiv_search import search_arxiv
from alpha_research.tools.paper_fetch import fetch_and_extract
from alpha_research.tools.semantic_scholar import (
    get_citations,
    get_paper_metadata,
    get_references,
    search_papers,
)
from alpha_research.tools.knowledge import (
    init_store,
    knowledge_read,
    knowledge_write,
)
from alpha_research.tools.report import generate_report

__all__ = [
    # ArXiv
    "search_arxiv",
    # Paper fetch
    "fetch_and_extract",
    # Semantic Scholar
    "get_paper_metadata",
    "search_papers",
    "get_references",
    "get_citations",
    # Knowledge store
    "init_store",
    "knowledge_read",
    "knowledge_write",
    # Reports
    "generate_report",
]
