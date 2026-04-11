"""Shared pytest fixtures for the alpha_research test suite.

The most important fixture is ``report``: every test module that wants to
produce a human-readable test report receives a per-module
:class:`ReportWriter` instance. The report is automatically saved to
``tests/reports/<module_name>.md`` when the module teardown runs.
"""

from __future__ import annotations

import pytest

from tests.report_helpers import ReportWriter


@pytest.fixture(scope="module")
def report(request: pytest.FixtureRequest) -> ReportWriter:
    """Module-scoped report writer.

    Derives the module name from the pytest test file, creates a
    :class:`ReportWriter`, and writes the markdown report on teardown.
    """
    module_name = request.module.__name__.split(".")[-1]
    writer = ReportWriter(module_name)
    yield writer
    # Always save — even if some tests failed — so the user can inspect
    # the record of what happened.
    writer.save()
