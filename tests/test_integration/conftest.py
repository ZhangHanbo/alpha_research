"""pytest configuration for the integration test suite.

Registers the ``integration`` marker and provides fixtures for detecting
tool availability and skipping tests that require missing prerequisites.
"""

from __future__ import annotations

import os
import shutil

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: end-to-end tests that hit real CLIs / APIs "
        "(opt-in via `pytest -m integration`)",
    )


@pytest.fixture(scope="session")
def alpha_review_cli_available() -> bool:
    """True iff the `alpha-review` CLI is on PATH."""
    return shutil.which("alpha-review") is not None


@pytest.fixture(scope="session")
def claude_cli_available() -> bool:
    """True iff the `claude` CLI is on PATH (Claude Code installed)."""
    return shutil.which("claude") is not None


@pytest.fixture(scope="session")
def anthropic_api_key_set() -> bool:
    """True iff ANTHROPIC_API_KEY is set in the environment."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


@pytest.fixture
def skip_if_no_claude(claude_cli_available):
    if not claude_cli_available:
        pytest.skip("`claude` CLI not on PATH — install Claude Code to run this test")


@pytest.fixture
def skip_if_no_alpha_review(alpha_review_cli_available):
    if not alpha_review_cli_available:
        pytest.skip("`alpha-review` CLI not on PATH — install alpha_review to run this test")


@pytest.fixture
def skip_if_no_api_key(anthropic_api_key_set):
    if not anthropic_api_key_set:
        pytest.skip("ANTHROPIC_API_KEY not set")
