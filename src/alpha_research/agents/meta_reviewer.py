"""Meta-reviewer agent — lightweight wrapper around review quality metrics.

Provides a ``MetaReviewer`` class that:
  1. Runs programmatic quality checks (metrics + anti-patterns)
  2. Builds an LLM prompt for complementary qualitative assessment

Source: review_plan.md 2.3, 4.2
"""

from __future__ import annotations

from alpha_research.metrics.review_quality import (
    evaluate_review,
)
from alpha_research.models.review import (
    Review,
    ReviewQualityReport,
)
from alpha_research.prompts.meta_review_system import build_meta_review_prompt


class MetaReviewer:
    """Evaluates the quality of reviews produced by the review agent.

    Parameters
    ----------
    thresholds:
        Optional overrides for default quality thresholds.  Keys are
        ``actionability``, ``grounding``, ``vague_critiques``,
        ``falsifiability``, ``steel_man_sentences``.
    """

    def __init__(self, thresholds: dict | None = None) -> None:
        self.thresholds = thresholds

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

    def _build_prompt(
        self,
        review: Review,
        review_history: list[Review] | None = None,
    ) -> str:
        """Build an LLM system prompt for qualitative meta-review.

        This is complementary to the programmatic checks in :meth:`check`.
        The caller would send this prompt along with the serialized review
        to an LLM for a richer qualitative assessment.
        """
        system = build_meta_review_prompt()

        # Append the review data as context for the LLM
        parts = [system, "\n# Review Under Evaluation\n"]
        parts.append(review.model_dump_json(indent=2))

        if review_history:
            parts.append("\n# Previous Review Iterations\n")
            for i, prev in enumerate(review_history):
                parts.append(f"\n## Iteration {i + 1}\n")
                parts.append(prev.model_dump_json(indent=2))

        return "\n".join(parts)
