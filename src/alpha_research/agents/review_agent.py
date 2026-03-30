"""Review agent: adversarial review workflow.

Wraps the three-pass review protocol (chain extraction, attack vectors,
evidence audit) into a clean Python class.  LLM interaction is isolated
to ``_build_prompt`` / ``_parse_response`` so the verdict logic and chain
extraction can be tested without any external dependencies.

Sources:
  - review_plan.md §1.9 (verdict computation)
  - review_guideline.md §2.1 (three-pass protocol)
  - review_guideline.md §3.1-3.6 (attack vectors)
"""

from __future__ import annotations

import json
import re
from typing import Any

from alpha_research.models.blackboard import ResearchArtifact
from alpha_research.models.research import TaskChain
from alpha_research.models.review import Finding, Review, Severity, Verdict
from alpha_research.prompts.review_system import build_review_prompt

# Type alias for LLM callable: async (system, user) -> str
LLMCallable = Any  # In practice: Callable[[str, str], Awaitable[str]]


class ReviewAgent:
    """Adversarial reviewer that produces structured :class:`Review` objects.

    The agent is venue-calibrated and applies graduated pressure across
    iterations (structural scan -> full review -> focused re-review).

    Parameters
    ----------
    venue : str
        Target publication venue (e.g. ``"RSS"``, ``"IJRR"``, ``"ICRA"``).
    """

    def __init__(self, venue: str = "RSS", llm: LLMCallable | None = None) -> None:
        self.venue = venue
        self.llm = llm

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def review(
        self,
        artifact: ResearchArtifact,
        iteration: int = 1,
        *,
        response_text: str | None = None,
    ) -> Review:
        """Run the full review workflow on *artifact*.

        Parameters
        ----------
        artifact : ResearchArtifact
            The artifact to review.
        iteration : int
            Current review iteration (controls graduated pressure).
        response_text : str | None
            Pre-computed LLM response for testing.  If ``None`` and no
            ``self.llm`` is set, raises ``NotImplementedError``.
        """
        if response_text is not None:
            return self._parse_response(response_text)

        raise NotImplementedError(
            "review() requires an LLM backend or response_text.  "
            "Use areview() for async LLM calls, or pass response_text for testing."
        )

    def rereview(
        self,
        artifact: ResearchArtifact,
        previous_review: Review,
        iteration: int,
        *,
        response_text: str | None = None,
    ) -> Review:
        """Focused re-review with pairwise comparison against *previous_review*.

        Parameters
        ----------
        response_text : str | None
            Pre-computed LLM response for testing.
        """
        if response_text is not None:
            return self._parse_response(response_text)

        raise NotImplementedError(
            "rereview() requires an LLM backend or response_text.  "
            "Use arereview() for async LLM calls, or pass response_text for testing."
        )

    # ------------------------------------------------------------------
    # Async LLM-backed variants
    # ------------------------------------------------------------------

    async def areview(
        self,
        artifact: ResearchArtifact,
        iteration: int = 1,
    ) -> Review:
        """Review an artifact using the LLM.

        Requires ``self.llm`` to be set.
        """
        if self.llm is None:
            raise RuntimeError("areview() requires an LLM client (self.llm)")
        prompt = self._build_prompt(artifact, iteration)
        user_msg = (
            f"Review the artifact above (version {artifact.version}, "
            f"stage {artifact.stage.value if hasattr(artifact.stage, 'value') else artifact.stage}). "
            f"This is review iteration {iteration}."
        )
        response_text = await self.llm(prompt, user_msg)
        return self._parse_response(response_text)

    async def arereview(
        self,
        artifact: ResearchArtifact,
        previous_review: Review,
        iteration: int,
    ) -> Review:
        """Focused re-review using the LLM.

        Requires ``self.llm`` to be set.
        """
        if self.llm is None:
            raise RuntimeError("arereview() requires an LLM client (self.llm)")
        prompt = self._build_prompt(
            artifact, iteration, previous_review=previous_review,
        )
        user_msg = (
            f"Re-review the artifact (version {artifact.version}). "
            f"Focus on whether previous findings have been addressed."
        )
        response_text = await self.llm(prompt, user_msg)
        return self._parse_response(response_text)

    # ------------------------------------------------------------------
    # Verdict computation — pure logic, no LLM
    # ------------------------------------------------------------------

    @staticmethod
    def compute_verdict(findings: list[Finding]) -> Verdict:
        """Mechanically compute a verdict from a list of findings.

        Rules (review_plan.md §1.9):
        1. Any fatal finding                        -> REJECT
        2. (Significance ≤ 2 is handled at finding level as fatal)
        3. 3+ unresolvable serious findings          -> REJECT
        4. 0 serious findings                        -> ACCEPT
        5. ≤1 *fixable* serious finding              -> WEAK_ACCEPT
        6. ≤2 serious findings (borderline)          -> WEAK_ACCEPT / WEAK_REJECT
        7. 3+ serious findings                       -> WEAK_REJECT
        """
        fatals = [f for f in findings if f.severity == Severity.FATAL]
        serious = [f for f in findings if f.severity == Severity.SERIOUS]

        # Rule 1: any fatal -> REJECT
        if fatals:
            return Verdict.REJECT

        serious_count = len(serious)

        # Rule 3: 3+ unresolvable (not fixable) serious -> REJECT
        unresolvable = [f for f in serious if not f.fixable]
        if len(unresolvable) >= 3:
            return Verdict.REJECT

        # Rule 4: 0 serious -> ACCEPT
        if serious_count == 0:
            return Verdict.ACCEPT

        # Rule 5: ≤1 fixable serious (and that's all serious findings)
        if serious_count <= 1 and all(f.fixable for f in serious):
            return Verdict.WEAK_ACCEPT

        # Rule 7: 3+ serious -> WEAK_REJECT
        if serious_count >= 3:
            return Verdict.WEAK_REJECT

        # Rule 6: ≤2 serious -> borderline
        # Heuristic: if all fixable -> WEAK_ACCEPT, else WEAK_REJECT
        if all(f.fixable for f in serious):
            return Verdict.WEAK_ACCEPT
        return Verdict.WEAK_REJECT

    # ------------------------------------------------------------------
    # Chain extraction — heuristic text parsing
    # ------------------------------------------------------------------

    @staticmethod
    def extract_chain(text: str) -> TaskChain:
        """Best-effort extraction of the task chain from artifact text.

        Looks for labelled sections (``Task:``, ``Problem:``, etc.) or
        common heading patterns.  Returns a :class:`TaskChain` with
        ``chain_complete`` and ``chain_coherent`` computed.
        """
        chain = TaskChain()

        # --- helper: try labelled patterns first, then heading sections ---
        def _extract(labels: list[str]) -> str | None:
            # Pattern 1: "Label: some text" on one line
            for label in labels:
                pattern = rf"(?:^|\n)\s*\**{label}\s*\**\s*[:：]\s*(.+)"
                m = re.search(pattern, text, re.IGNORECASE)
                if m:
                    return m.group(1).strip()

            # Pattern 2: markdown heading "## Label\n content"
            for label in labels:
                pattern = rf"(?:^|\n)#+\s*{label}\s*\n+(.+?)(?:\n#|\n\n|\Z)"
                m = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
                if m:
                    # Take first meaningful line
                    for line in m.group(1).strip().splitlines():
                        line = line.strip()
                        if line and not line.startswith("#"):
                            return line
            return None

        chain.task = _extract(["task"])
        chain.problem = _extract(["problem", "problem definition",
                                  "problem statement"])
        chain.challenge = _extract(["challenge", "key challenge",
                                    "structural challenge"])
        chain.approach = _extract(["approach", "method", "proposed approach",
                                   "proposed method"])
        chain.one_sentence = _extract(["contribution", "one.sentence",
                                       "one sentence", "insight"])

        # Compute completeness flags
        completeness = chain.compute_completeness()
        chain.chain_complete = completeness == 1.0
        # Coherence heuristic: complete chain is deemed coherent
        chain.chain_coherent = chain.chain_complete

        return chain

    # ------------------------------------------------------------------
    # Prompt building — testable without LLM
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        artifact: ResearchArtifact,
        iteration: int,
        previous_review: Review | None = None,
    ) -> str:
        """Build the full prompt for the review agent.

        Combines the system prompt (venue-calibrated, graduated pressure)
        with the artifact content and optional previous review findings.
        """
        previous_findings: list[dict] | None = None
        review_mode = "auto"

        if previous_review is not None:
            review_mode = "focused_rereview"
            previous_findings = [
                f.model_dump() for f in previous_review.all_findings
            ]

        system_prompt = build_review_prompt(
            venue=self.venue,
            iteration=iteration,
            previous_findings=previous_findings,
            review_mode=review_mode,
        )

        # Assemble user message with artifact content
        parts: list[str] = [system_prompt]
        parts.append("\n\n---\n\n# Artifact to Review\n")
        parts.append(f"**Stage:** {artifact.stage.value}\n")
        parts.append(f"**Version:** {artifact.version}\n\n")
        parts.append(artifact.content)

        if previous_review is not None:
            parts.append("\n\n---\n\n# Previous Review (for pairwise comparison)\n")
            parts.append(f"**Previous verdict:** {previous_review.verdict.value}\n")
            parts.append(f"**Fatal flaws:** {len(previous_review.fatal_flaws)}\n")
            parts.append(
                f"**Serious weaknesses:** {len(previous_review.serious_weaknesses)}\n"
            )
            parts.append(f"**Minor issues:** {len(previous_review.minor_issues)}\n")

        return "".join(parts)

    # ------------------------------------------------------------------
    # Response parsing — structured extraction from LLM output
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response_text: str) -> Review:
        """Parse an LLM response (JSON) into a :class:`Review`.

        Extracts the JSON object from *response_text*, which may contain
        markdown fences or surrounding prose.
        """
        # Strip markdown code fences if present
        json_str = response_text.strip()

        # Try to find JSON block inside markdown fences
        fence_match = re.search(
            r"```(?:json)?\s*\n?(.*?)\n?\s*```",
            json_str,
            re.DOTALL,
        )
        if fence_match:
            json_str = fence_match.group(1).strip()
        else:
            # Try to find a bare JSON object
            brace_match = re.search(r"\{.*\}", json_str, re.DOTALL)
            if brace_match:
                json_str = brace_match.group(0)

        data: dict[str, Any] = json.loads(json_str)
        return Review.model_validate(data)
