"""Unit tests for ``alpha_research.llm`` + a live smoke test via claude CLI.

Two parts:

1. **Pure unit tests** — exercise the ``AnthropicLLM`` constructor guard
   and the ``make_llm`` factory without any network traffic.
2. **Live smoke test** — runs ``claude -p`` with ``claude-haiku-4-5-20251001``
   to confirm the CLI path works. Skipped automatically when the
   ``claude`` binary is not on PATH, so local environments without it
   still pass. The test uses a minimal prompt to keep latency and cost low.

Writes ``tests/reports/test_llm.md``.
"""

from __future__ import annotations

import os
import shutil
import subprocess

import pytest

from alpha_research.llm import DEFAULT_MODEL, AnthropicLLM, make_llm


HAIKU_MODEL = "claude-haiku-4-5-20251001"


def test_anthropic_llm_missing_api_key(monkeypatch, report) -> None:
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    raised = False
    message = ""
    try:
        AnthropicLLM(api_key=None)
    except ValueError as e:
        raised = True
        message = str(e)
    passed = raised and "API key" in message
    report.record(
        name="AnthropicLLM rejects empty credentials",
        purpose="Constructor must raise ValueError if no api_key and no ANTHROPIC_API_KEY env var.",
        inputs={"api_key": None, "ANTHROPIC_API_KEY": "unset"},
        expected={"raises": True, "mentions_api_key": True},
        actual={"raises": raised, "message": message},
        passed=passed,
        conclusion="Fail-fast avoids silent no-op calls when credentials are missing.",
    )
    assert passed


def test_anthropic_llm_defaults(monkeypatch, report) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    llm = AnthropicLLM()
    passed = llm.model == DEFAULT_MODEL and llm.max_tokens == 16384
    report.record(
        name="AnthropicLLM default model and max_tokens",
        purpose="Defaults should be DEFAULT_MODEL and max_tokens=16384.",
        inputs={"api_key": "sk-ant-test-not-real (env)"},
        expected={"model": DEFAULT_MODEL, "max_tokens": 16384},
        actual={"model": llm.model, "max_tokens": llm.max_tokens},
        passed=passed,
        conclusion="Sensible defaults so callers just need an API key.",
    )
    assert passed


def test_make_llm_falls_back_to_anthropic(monkeypatch, tmp_path, report) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-not-real")
    # Point config at a path that doesn't exist — should hit AnthropicLLM fallback.
    llm = make_llm(config=tmp_path / "nope.yaml", model=None)
    passed = isinstance(llm, AnthropicLLM) and llm.model == DEFAULT_MODEL
    report.record(
        name="make_llm falls back to AnthropicLLM when no llmutils config exists",
        purpose="A missing config file should not raise; the factory should fall back to Anthropic directly.",
        inputs={"config": "nonexistent.yaml"},
        expected={"is_anthropic_llm": True, "model": DEFAULT_MODEL},
        actual={"is_anthropic_llm": isinstance(llm, AnthropicLLM), "model": llm.model},
        passed=passed,
        conclusion="Graceful fallback keeps production paths resilient to missing configs.",
    )
    assert passed


# ---------------------------------------------------------------------------
# Live smoke test via `claude -p` + Haiku
# ---------------------------------------------------------------------------

def test_claude_cli_haiku_smoke(report) -> None:
    """Send a tiny prompt to ``claude -p --model claude-haiku-4-5-20251001``.

    Skipped automatically when:
      - ``claude`` is not on PATH, or
      - the environment variable ``ALPHA_RESEARCH_SKIP_LIVE_LLM=1`` is set.

    Pass condition: the subprocess exits 0 and prints non-empty stdout
    containing at least one alpha character.
    """
    if os.environ.get("ALPHA_RESEARCH_SKIP_LIVE_LLM") == "1":
        report.record(
            name="claude-cli haiku smoke (skipped)",
            purpose="Optional live test — skipped because ALPHA_RESEARCH_SKIP_LIVE_LLM=1.",
            inputs={"model": HAIKU_MODEL, "skipped_reason": "env var"},
            expected="skipped",
            actual="skipped",
            passed=True,
            conclusion="Live LLM test intentionally skipped in this environment.",
        )
        pytest.skip("ALPHA_RESEARCH_SKIP_LIVE_LLM=1")

    if shutil.which("claude") is None:
        report.record(
            name="claude-cli haiku smoke (skipped)",
            purpose="Optional live test — skipped because `claude` binary is not on PATH.",
            inputs={"model": HAIKU_MODEL, "skipped_reason": "claude CLI missing"},
            expected="skipped",
            actual="skipped",
            passed=True,
            conclusion="Install the Claude Code CLI to enable this live smoke test.",
        )
        pytest.skip("claude CLI not installed")

    prompt = "Respond with exactly the single word: pong."
    try:
        completed = subprocess.run(
            [
                "claude", "-p", prompt,
                "--model", HAIKU_MODEL,
                "--output-format", "text",
                "--max-turns", "1",
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        report.record(
            name="claude-cli haiku smoke",
            purpose="Send a short prompt through the claude CLI using the Haiku model.",
            inputs={"prompt": prompt, "model": HAIKU_MODEL},
            expected={"returncode": 0, "output": "non-empty"},
            actual={"timeout": True},
            passed=False,
            conclusion="Subprocess timed out after 120s — network issue or CLI hang.",
        )
        pytest.fail("claude CLI timed out")

    stdout = (completed.stdout or "").strip()
    passed = completed.returncode == 0 and any(ch.isalpha() for ch in stdout)
    report.record(
        name="claude-cli haiku smoke",
        purpose="Send a minimal prompt via `claude -p --model claude-haiku-4-5-20251001` and verify non-empty output.",
        inputs={"prompt": prompt, "model": HAIKU_MODEL},
        expected={"returncode": 0, "output_has_text": True},
        actual={"returncode": completed.returncode, "stdout": stdout[:200], "stderr": (completed.stderr or "")[:200]},
        passed=passed,
        conclusion="Live Haiku round-trip confirms the CLI path is functional for downstream skill invocation.",
    )
    assert passed
