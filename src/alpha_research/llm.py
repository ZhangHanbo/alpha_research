"""LLM client abstraction for the multi-agent system.

Two ways to create an LLM client:

1. **llmutils config** (preferred) — uses the ``llmutils`` package for
   multi-provider support::

       from alpha_research.llm import make_llm
       llm = make_llm("config/llm.yaml")
       llm = make_llm("config/llm.yaml", model="deepseek-chat")

2. **Direct Anthropic** (legacy fallback) — if ``llmutils`` is not
   installed or no config file exists::

       from alpha_research.llm import AnthropicLLM
       llm = AnthropicLLM(api_key="sk-ant-...")

Both satisfy the ``LLMCallable`` protocol: ``async (system, user) -> str``.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol

import anthropic


# ---------------------------------------------------------------------------
# Protocol for dependency injection
# ---------------------------------------------------------------------------

class LLMCallable(Protocol):
    """Any async callable (system, user) -> str."""

    async def __call__(self, system: str, user: str) -> str: ...


# ---------------------------------------------------------------------------
# Factory using llmutils (preferred)
# ---------------------------------------------------------------------------

def make_llm(
    config: str | Path | None = None,
    model: str | None = None,
) -> LLMCallable:
    """Create an LLM client, preferring llmutils if available.

    Parameters
    ----------
    config : str | Path | None
        Path to an ``llmutils`` YAML config file.  If None, tries
        ``config/llm.yaml``, then falls back to ``AnthropicLLM``.
    model : str | None
        Model name override.

    Returns
    -------
    LLMCallable
        An async callable ``(system, user) -> str``.
    """
    # Try llmutils first
    cfg_path = Path(config) if config else Path("config/llm.yaml")
    if cfg_path.exists():
        try:
            from llmutils import LLM
            return LLM(cfg_path, model=model)
        except ImportError:
            pass  # llmutils not installed, fall through

    # Fallback to direct Anthropic
    return AnthropicLLM(model=model or DEFAULT_MODEL)


# ---------------------------------------------------------------------------
# Anthropic implementation
# ---------------------------------------------------------------------------

DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_MAX_TOKENS = 16384


class AnthropicLLM:
    """Async wrapper around the Anthropic Messages API.

    Parameters
    ----------
    model : str
        Model identifier.
    max_tokens : int
        Maximum tokens in the response.
    api_key : str | None
        Anthropic API key.  Falls back to ``ANTHROPIC_API_KEY`` env var.
    """

    def __init__(
        self,
        model: str = DEFAULT_MODEL,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        api_key: str | None = None,
    ) -> None:
        self.model = model
        self.max_tokens = max_tokens
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError(
                "No API key provided. Set ANTHROPIC_API_KEY or pass api_key=."
            )
        self._client = anthropic.AsyncAnthropic(api_key=key)

    async def __call__(self, system: str, user: str) -> str:
        """Send a system + user message pair and return the text response."""
        return await self.generate(system, user)

    async def generate(self, system: str, user: str) -> str:
        """Send a system + user message and return assistant text.

        The assistant is prefilled with ``{`` to encourage JSON output.
        """
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            system=system,
            messages=[
                {"role": "user", "content": user},
                {"role": "assistant", "content": "{"},
            ],
        )
        # Extract the text from the response
        text = ""
        for block in response.content:
            if block.type == "text":
                text += block.text

        # Prepend the '{' we used as prefill
        return "{" + text
