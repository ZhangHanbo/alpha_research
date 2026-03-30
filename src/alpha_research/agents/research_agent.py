"""Research agent implementation.

Wraps the research workflow as a testable Python class. Does NOT depend on
any LLM provider — tool orchestration is explicit and the LLM interaction
is isolated to _build_prompt / _parse_response methods that can be driven
by any backend or mocked in tests.
"""

from __future__ import annotations

import json
from typing import Any

from alpha_research.config import ConstitutionConfig
from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.blackboard import ResearchArtifact, ResearchStage
from alpha_research.models.research import (
    Evaluation,
    Paper,
    PaperCandidate,
    TaskChain,
)
from alpha_research.models.review import (
    Finding,
    FindingDeferral,
    FindingDispute,
    FindingResponse,
    Review,
    RevisionResponse,
)
from alpha_research.prompts.research_system import build_research_prompt
from alpha_research.tools.report import generate_report

# Type alias for LLM callable: async (system, user) -> str
LLMCallable = Any  # In practice: Callable[[str, str], Awaitable[str]]


# ---------------------------------------------------------------------------
# State machine transitions
# ---------------------------------------------------------------------------

# Valid forward/backward transitions keyed by current stage.
_TRANSITIONS: dict[str, list[str]] = {
    "significance": ["formalization"],
    "formalization": ["significance", "diagnose", "challenge"],
    "diagnose": ["formalization", "challenge"],
    "challenge": ["formalization", "diagnose", "approach"],
    "approach": ["challenge", "validate"],
    "validate": ["approach", "full_draft"],
    "full_draft": ["validate"],
}


class ResearchAgent:
    """Orchestrates the research workflow.

    The agent is a plain Python object — it builds prompts, parses LLM
    responses, and sequences tool calls, but does *not* call an LLM itself.
    This makes it fully testable with mock responses.

    Parameters
    ----------
    knowledge_store : KnowledgeStore
        Persistent paper/evaluation store.
    config : ConstitutionConfig | None
        Domain focus configuration.  Defaults to standard robotics focus.
    """

    def __init__(
        self,
        knowledge_store: KnowledgeStore,
        config: ConstitutionConfig | None = None,
        llm: LLMCallable | None = None,
    ) -> None:
        self.knowledge_store = knowledge_store
        self.config = config or ConstitutionConfig()
        self.llm = llm

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    @staticmethod
    def get_valid_transitions(stage: str) -> list[str]:
        """Return valid next stages from the given stage."""
        return list(_TRANSITIONS.get(stage, []))

    # ------------------------------------------------------------------
    # Prompt building
    # ------------------------------------------------------------------

    def _build_prompt(
        self,
        stage: str,
        question: str,
        findings: list[dict] | None = None,
    ) -> str:
        """Build the system prompt for a generation request.

        Parameters
        ----------
        stage : str
            Current research stage (e.g. ``"significance"``).
        question : str
            The research question being addressed.
        findings : list[dict] | None
            Previous review findings to address (revision mode).

        Returns
        -------
        str
            Full system prompt ready to send to an LLM.
        """
        system = build_research_prompt(
            constitution=self.config,
            stage=stage,
            previous_findings=findings,
        )
        # Append the concrete research question as user context
        system += f"\n\n# Research Question\n\n{question}"
        return system

    def _build_revision_prompt(
        self,
        artifact: ResearchArtifact,
        review: Review,
    ) -> str:
        """Build a prompt for revising an artifact in response to a review.

        The prompt includes the current artifact content and all findings
        from the review that must be addressed.
        """
        findings_dicts = [f.model_dump() for f in review.all_findings]
        system = build_research_prompt(
            constitution=self.config,
            stage=artifact.stage.value if isinstance(artifact.stage, ResearchStage) else artifact.stage,
            previous_findings=findings_dicts,
        )
        # Include the current artifact for context
        system += (
            f"\n\n# Current Artifact (version {artifact.version})\n\n"
            f"{artifact.content}"
        )
        return system

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(response_text: str) -> ResearchArtifact:
        """Parse an LLM response into a ResearchArtifact.

        Expects a JSON object matching the ResearchArtifact schema.
        Handles both raw JSON and JSON embedded in markdown code fences.
        """
        text = _extract_json_block(response_text)
        data = json.loads(text)
        # Normalise stage to enum
        stage_val = data.get("stage", "significance")
        data["stage"] = stage_val
        return ResearchArtifact.model_validate(data)

    @staticmethod
    def _parse_revision_response(
        response_text: str,
    ) -> tuple[ResearchArtifact, RevisionResponse]:
        """Parse an LLM revision response.

        Expects JSON containing both a ResearchArtifact and a
        RevisionResponse.  The response may be a single JSON object
        with top-level keys ``"artifact"`` and ``"revision_response"``,
        or two consecutive JSON blocks.
        """
        text = _extract_json_block(response_text)
        data = json.loads(text)

        # Case 1: combined object with "artifact" and "revision_response"
        if "artifact" in data and "revision_response" in data:
            artifact = ResearchArtifact.model_validate(data["artifact"])
            revision = RevisionResponse.model_validate(data["revision_response"])
            return artifact, revision

        # Case 2: top-level IS the artifact, plus revision fields
        if "stage" in data and "review_version" in data:
            revision_data = {
                "review_version": data.pop("review_version"),
                "addressed": data.pop("addressed", []),
                "deferred": data.pop("deferred", []),
                "disputed": data.pop("disputed", []),
            }
            artifact = ResearchArtifact.model_validate(data)
            revision = RevisionResponse.model_validate(revision_data)
            return artifact, revision

        raise ValueError(
            "Could not parse revision response: expected 'artifact' + "
            "'revision_response' keys or a combined object."
        )

    # ------------------------------------------------------------------
    # Core workflow: generate
    # ------------------------------------------------------------------

    def generate(
        self,
        stage: str,
        question: str,
        *,
        response_text: str | None = None,
        **kwargs: Any,
    ) -> ResearchArtifact:
        """Produce a research artifact for the given stage.

        In production use the caller obtains ``response_text`` from an LLM
        using the prompt from :meth:`_build_prompt`.  For testing, pass
        ``response_text`` directly.

        Parameters
        ----------
        stage : str
            Research stage.
        question : str
            Research question.
        response_text : str | None
            Raw LLM output.  If ``None`` the method returns a prompt-only
            stub (useful for dry-run / inspection).
        **kwargs
            Extra keyword arguments forwarded to ``_build_prompt`` via
            ``findings``.
        """
        findings = kwargs.get("findings")
        prompt = self._build_prompt(stage, question, findings=findings)

        if response_text is None:
            # Return a minimal stub so the caller knows to get an LLM response
            return ResearchArtifact(
                stage=stage,
                content=f"[PROMPT BUILT — awaiting LLM response]\n\n{prompt[:200]}...",
                metadata={"prompt_length": len(prompt)},
            )

        artifact = self._parse_response(response_text)
        return artifact

    # ------------------------------------------------------------------
    # Core workflow: revise
    # ------------------------------------------------------------------

    def revise(
        self,
        artifact: ResearchArtifact,
        review: Review,
        *,
        response_text: str | None = None,
    ) -> tuple[ResearchArtifact, RevisionResponse]:
        """Revise an artifact in response to a review.

        Parameters
        ----------
        artifact : ResearchArtifact
            Current artifact to revise.
        review : Review
            Review containing findings to address.
        response_text : str | None
            Raw LLM output.  If ``None``, builds prompt only.
        """
        prompt = self._build_revision_prompt(artifact, review)

        if response_text is None:
            stub_artifact = ResearchArtifact(
                stage=artifact.stage,
                content="[PROMPT BUILT — awaiting LLM response]",
                version=artifact.version + 1,
                metadata={"prompt_length": len(prompt)},
            )
            stub_revision = RevisionResponse(review_version=review.version)
            return stub_artifact, stub_revision

        new_artifact, revision = self._parse_revision_response(response_text)
        new_artifact.version = artifact.version + 1
        return new_artifact, revision

    # ------------------------------------------------------------------
    # Async LLM-backed variants
    # ------------------------------------------------------------------

    async def agenerate(
        self,
        stage: str,
        question: str,
        *,
        findings: list[dict] | None = None,
    ) -> ResearchArtifact:
        """Produce a research artifact using the LLM.

        Requires ``self.llm`` to be set. Builds the prompt, calls the LLM,
        and parses the response into a :class:`ResearchArtifact`.
        """
        if self.llm is None:
            raise RuntimeError("agenerate() requires an LLM client (self.llm)")
        prompt = self._build_prompt(stage, question, findings=findings)
        user_msg = f"Produce a {stage} artifact for the research question above."
        response_text = await self.llm(prompt, user_msg)
        return self._parse_response(response_text)

    async def arevise(
        self,
        artifact: ResearchArtifact,
        review: Review,
    ) -> tuple[ResearchArtifact, RevisionResponse]:
        """Revise an artifact using the LLM.

        Requires ``self.llm`` to be set.
        """
        if self.llm is None:
            raise RuntimeError("arevise() requires an LLM client (self.llm)")
        prompt = self._build_revision_prompt(artifact, review)
        user_msg = (
            "Revise the artifact to address ALL findings from the review. "
            "Produce both a ResearchArtifact and a RevisionResponse."
        )
        response_text = await self.llm(prompt, user_msg)
        new_artifact, revision = self._parse_revision_response(response_text)
        new_artifact.version = artifact.version + 1
        return new_artifact, revision

    # ------------------------------------------------------------------
    # High-level modes
    # ------------------------------------------------------------------

    async def run_digest(
        self,
        question: str,
        max_papers: int = 10,
    ) -> str:
        """Search, fetch, evaluate, and produce a digest report.

        Orchestrates tools in sequence:
        ``search_arxiv`` -> ``fetch_and_extract`` -> evaluate -> ``generate_report``

        Parameters
        ----------
        question : str
            Research topic / search query.
        max_papers : int
            Maximum number of papers to include.

        Returns
        -------
        str
            Rendered markdown digest report.
        """
        from alpha_research.tools.arxiv_search import search_arxiv
        from alpha_research.tools.paper_fetch import fetch_and_extract

        # 1. Search
        candidates = await search_arxiv(query=question, max_results=max_papers)

        # 2. Fetch top candidates
        papers: list[Paper] = []
        for candidate in candidates[:max_papers]:
            if candidate.arxiv_id:
                try:
                    paper = await fetch_and_extract(candidate.arxiv_id)
                    # Carry over metadata from candidate
                    paper.authors = candidate.authors or paper.authors
                    paper.year = candidate.year or paper.year
                    paper.venue = candidate.venue or paper.venue
                    if not paper.abstract and candidate.abstract:
                        paper.abstract = candidate.abstract
                    papers.append(paper)
                except Exception:
                    # If fetch fails, create a minimal paper from candidate
                    papers.append(Paper(
                        arxiv_id=candidate.arxiv_id,
                        title=candidate.title,
                        authors=candidate.authors,
                        abstract=candidate.abstract,
                        year=candidate.year,
                        venue=candidate.venue,
                        url=candidate.url,
                    ))

        # 3. Build evaluation dicts for the report template
        eval_dicts: list[dict] = []
        for paper in papers:
            eval_dict: dict[str, Any] = {
                "title": paper.title,
                "authors": paper.authors,
                "year": paper.year,
                "venue": paper.venue,
                "arxiv_id": paper.arxiv_id,
                "abstract": paper.abstract,
                "rubric_scores": {},
                "significance_assessment": None,
                "human_review_flags": [],
            }
            eval_dicts.append(eval_dict)

            # 4. Store paper in knowledge store
            self.knowledge_store.save_paper(paper)

        # 5. Generate digest report
        report = generate_report(
            evaluations=eval_dicts,
            mode="digest",
            title=question,
        )
        return report

    async def run_deep(self, arxiv_id: str) -> str:
        """Fetch a single paper and produce a deep analysis report.

        Orchestrates: ``fetch_and_extract`` -> evaluate -> ``generate_report``

        Parameters
        ----------
        arxiv_id : str
            ArXiv paper identifier.

        Returns
        -------
        str
            Rendered markdown deep-analysis report.
        """
        from alpha_research.tools.paper_fetch import fetch_and_extract

        # 1. Fetch paper
        paper = await fetch_and_extract(arxiv_id)

        # 2. Store in knowledge store
        self.knowledge_store.save_paper(paper)

        # 3. Build evaluation dict for report
        eval_dict: dict[str, Any] = {
            "title": paper.title,
            "authors": paper.authors,
            "year": paper.year,
            "venue": paper.venue,
            "arxiv_id": paper.arxiv_id,
            "abstract": paper.abstract,
            "full_text": paper.full_text,
            "sections": paper.sections,
            "task_chain": None,
            "has_formal_problem_def": False,
            "formal_framework": None,
            "structure_identified": [],
            "rubric_scores": {},
            "significance_assessment": None,
            "related_papers": [],
            "human_review_flags": [
                "Deep analysis requires LLM evaluation — "
                "only extraction and report structure provided here."
            ],
            "extraction_limitations": (
                paper.extraction_quality.flagged_issues
                if paper.extraction_quality
                else []
            ),
            "strengths": [],
            "weaknesses": [],
            "open_questions": [],
            "code_url": None,
        }

        # 4. Generate deep report
        report = generate_report(
            evaluations=[eval_dict],
            mode="deep",
            title=paper.title,
        )
        return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_json_block(text: str) -> str:
    """Extract JSON from text, handling optional markdown code fences."""
    stripped = text.strip()

    # Try to find ```json ... ``` block
    if "```json" in stripped:
        start = stripped.index("```json") + len("```json")
        end = stripped.index("```", start)
        return stripped[start:end].strip()

    # Try to find ``` ... ``` block
    if stripped.startswith("```"):
        start = stripped.index("\n") + 1
        end = stripped.rindex("```")
        return stripped[start:end].strip()

    # Assume the whole thing is JSON — find the outermost { }
    first_brace = stripped.find("{")
    if first_brace != -1:
        # Find matching closing brace
        depth = 0
        for i in range(first_brace, len(stripped)):
            if stripped[i] == "{":
                depth += 1
            elif stripped[i] == "}":
                depth -= 1
                if depth == 0:
                    return stripped[first_brace : i + 1]

    return stripped
