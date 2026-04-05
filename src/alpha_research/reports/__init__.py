"""Report generation for alpha_research-specific rubric artifacts.

Templates for per-paper (``deep``) and multi-paper (``digest``) reports that
render :class:`Evaluation` records with full rubric scores, significance
assessments, and task chains.

The former ``survey`` template has been removed — alpha_review's
``run_write`` generates LaTeX surveys with BibTeX and compiled PDF, which
supersedes our hand-written markdown survey template.
"""

from alpha_research.reports.templates import generate_report

__all__ = ["generate_report"]
