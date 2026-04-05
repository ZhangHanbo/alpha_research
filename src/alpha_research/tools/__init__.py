"""Shared toolset for research and review agents.

Note (R2 refactor): arxiv_search, semantic_scholar, and knowledge wrapper
have been removed; skills now call ``alpha_review.apis.*`` directly.
Only paper_fetch (PDF download + full-text extraction, unique to
alpha_research) and the legacy report generator remain here.
"""

from alpha_research.tools.paper_fetch import fetch_and_extract
from alpha_research.tools.report import generate_report

__all__ = [
    "fetch_and_extract",
    "generate_report",
]
