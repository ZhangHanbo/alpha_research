"""Meta-reviewer agent — lightweight wrapper around review quality metrics.

Provides a ``MetaReviewer`` class that:
  1. Runs programmatic quality checks (metrics + anti-patterns)
  2. Optionally uses an LLM for complementary qualitative assessment

Source: review_plan.md 2.3, 4.2
"""

from __future__ import annotations

import json
from typing import Any

from alpha_research.metrics.review_quality import (
    evaluate_review,
)
from alpha_research.models.review import (
    AntiPatternCheck,
    MetricCheck,
    Review,
    ReviewQualityReport,
)
from alpha_research.prompts.meta_review_system import build_meta_review_prompt

# Type alias for LLM callable: async (system, user) -> str
LLMCallable = Any


class MetaReviewer:
    """Evaluates the quality of reviews produced by the review agent.

    Parameters
    ----------
    thresholds:
        Optional overrides for default quality thresholds.
    llm:
        Optional async LLM callable for qualitative assessment.
    """

    def __init__(
        self,
        thresholds: dict | None = None,
        llm: LLMCallable | None = None,
    ) -> None:
        self.thresholds = thresholds
        self.llm = llm

    def check(
        self,
        review: Review,
        review_history: list[Review] | None = None,
    ) -> ReviewQualityReport:
        """Run all programmatic quality checks on *review*.

        Parameters
        ----------
        review:
            The review to evaluate.
        review_history:
            Previous review iterations (for cross-iteration checks).

        Returns
        -------
        ReviewQualityReport
            Structured pass/fail report with metric and anti-pattern checks.
        """
        return evaluate_review(
            review,
            review_history=review_history,
            thresholds=self.thresholds,
        )

    async def acheck(
        self,
        review: Review,
        review_history: list[Review] | None = None,
    ) -> ReviewQualityReport:
        """Run programmatic checks, optionally enhanced by LLM assessment.

        If ``self.llm`` is set, the LLM is called to provide qualitative
        feedback that supplements the programmatic metrics. The programmatic
        checks are authoritative for pass/fail; the LLM adds detail to the
        ``issues`` list.
        """
        report = self.check(review, review_history)

        if self.llm is not None:
            try:
                llm_issues = await self._llm_assess(review, review_history)
                report.issues.extend(llm_issues)
            except Exception:
                report.issues.append(
                    "[meta-reviewer LLM assessment failed — "
                    "relying on programmatic checks only]"
                )

        return report

    async def _llm_assess(
        self,
        review: Review,
        review_history: list[Review] | None = None,
    ) -> list[str]:
        """Call the LLM for qualitative review quality assessment.

        Returns a list of issue strings to append to the report.
        """
        prompt = self._build_prompt(review, review_history)
        user_msg = (
            "Evaluate the quality of this review. Return a JSON object with "
            "an 'issues' list of specific problems found."
        )
        response_text = await self.llm(prompt, user_msg)
        try:
            data = json.loads(response_text)
            return data.get("issues", [])
        except (json.JSONDecodeError, AttributeError):
            return []

    def _build_prompt(
        self,
        review: Review,
        review_history: list[Review] | None = None,
    ) -> str:
        """Build an LLM system prompt for qualitative meta-review."""
        system = build_meta_review_prompt()

        parts = [system, "\n# Review Under Evaluation\n"]
        parts.append(review.model_dump_json(indent=2))

        if review_history:
            parts.append("\n# Previous Review Iterations\n")
            for i, prev in enumerate(review_history):
                parts.append(f"\n## Iteration {i + 1}\n")
                parts.append(prev.model_dump_json(indent=2))

        return "\n".join(parts)
