"""Backward-compatibility shim for the report-generation module.

This file re-exports :func:`generate_report` from its new location at
:mod:`alpha_research.reports.templates`. The move was part of the R3
refactor phase (see ``guidelines/refactor_plan.md`` Part I.1).

.. deprecated::
    Import from :mod:`alpha_research.reports.templates` directly. This
    shim will be removed in R6 when the ``agents/`` package is deleted.
"""

from alpha_research.reports.templates import DEEP_TEMPLATE, DIGEST_TEMPLATE, generate_report

__all__ = ["generate_report", "DIGEST_TEMPLATE", "DEEP_TEMPLATE"]
