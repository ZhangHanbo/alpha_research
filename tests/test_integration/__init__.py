"""End-to-end integration tests for the alpha_research refactor (Phase R8).

These tests exercise the full pipeline + skill + CLI surface against real
external systems:

- ``alpha-review`` CLI subprocess (literature survey pipeline)
- ``claude -p`` CLI subprocess (skill invocations)
- Live Claude API (via claude_call fallback path, if enabled)

They are marked ``@pytest.mark.integration`` so they are OPT-IN:

    # Skipped by default (fast local test run):
    pytest -q

    # Run integration tests only:
    pytest -q -m integration

    # Run EVERYTHING:
    pytest -q -m ""

Most integration tests require:
- ``alpha_review`` installed and ``alpha-review`` on PATH
- ``claude`` CLI on PATH (Claude Code installed)
- ``ANTHROPIC_API_KEY`` env var for skill invocation fallback
- Network access to ArXiv / Semantic Scholar / OpenAlex / Unpaywall

Tests without those prerequisites are skipped cleanly with
``pytest.skip(..., allow_module_level=False)``.

See ``guidelines/refactor_plan.md`` Part V Phase R8 for the full test plan.
"""
