"""Shared toolset.

Post Phase 0 of the integrated-state-machine plan: only ``paper_fetch``
remains here. arxiv_search, semantic_scholar, the knowledge-store wrapper,
and the legacy report shim have all been removed — skills now call
``alpha_review.apis.*`` directly, and report generation moved to
``alpha_research.reports.templates``.
"""

from alpha_research.tools.paper_fetch import fetch_and_extract

__all__ = ["fetch_and_extract"]
