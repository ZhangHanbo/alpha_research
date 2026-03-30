"""LLM client abstraction for the multi-agent system.

Provides a thin wrapper around the Anthropic Messages API so that:
  - All agents share the same calling convention
  - Tests can inject a mock/stub without touching agent code
  - Structured JSON output is requested via prefill

Usage::

    client = AnthropicLLM()                        # production
    client = AnthropicLLM(model="claude-sonnet-4-20250514")  # cheaper model
    response_text = await client.generate(system_prompt, user_message)

For testing::

    async def fake_generate(system, user):
        return '{"stage": "significance", ...}'

    agent = ResearchAgent(..., llm=fake_generate)
"""

from __future__ import annotations

import os
from typing import Protocol

import anthropic


# ---------------------------------------------------------------------------
# Protocol for dependency injection
# ---------------------------------------------------------------------------

class LLMCallable(Protocol):
    """Any async callable (system, user) -> str."""

    async def __call__(self, system: str, user: str) -> str: ...


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
