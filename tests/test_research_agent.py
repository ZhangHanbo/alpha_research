"""Tests for the ResearchAgent class."""

from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from alpha_research.agents.research_agent import ResearchAgent, _extract_json_block
from alpha_research.config import ConstitutionConfig
from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.blackboard import ResearchArtifact, ResearchStage
from alpha_research.models.research import (
    Paper,
    PaperCandidate,
    TaskChain,
)
from alpha_research.models.review import (
    Finding,
    Review,
    RevisionResponse,
    Severity,
    Verdict,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def knowledge_store(tmp_path):
    """Create a temporary knowledge store."""
    db_path = tmp_path / "test_knowledge.db"
    return KnowledgeStore(db_path)


@pytest.fixture
def config():
    """Standard test constitution config."""
    return ConstitutionConfig(
        name="Test Research",
        focus_areas=["mobile manipulation"],
        key_groups=["TestGroup"],
        domains=["robotics"],
        max_papers_per_cycle=10,
    )


@pytest.fixture
def agent(knowledge_store, config):
    """Create a ResearchAgent with test config."""
    return ResearchAgent(knowledge_store=knowledge_store, config=config)


@pytest.fixture
def sample_artifact():
    """A minimal research artifact for testing."""
    return ResearchArtifact(
        stage=ResearchStage.SIGNIFICANCE,
        content="# Significance\n\nThis problem matters because...",
        task_chain=TaskChain(
            task="Pick up objects from cluttered shelves",
            problem=None,
            challenge=None,
            approach=None,
            one_sentence=None,
        ),
        metadata={"confidence": "medium", "limitations": ["early stage"]},
        version=1,
    )


@pytest.fixture
def sample_review():
    """A minimal review with findings."""
    return Review(
        version=1,
        summary="The paper argues that mobile manipulation needs better grasping.",
        chain_extraction=TaskChain(
            task="Pick up objects from cluttered shelves",
        ),
        steel_man="The strongest version of this argument is...",
        fatal_flaws=[],
        serious_weaknesses=[
            Finding(
                id="f1",
                severity=Severity.SERIOUS,
                attack_vector="significance_gap",
                what_is_wrong="No concrete consequence given",
                why_it_matters="Cannot assess real-world impact",
                what_would_fix="Provide specific downstream task that benefits",
                falsification="Show a concrete application that needs this",
                grounding="Section 1, paragraph 2",
                fixable=True,
            )
        ],
        minor_issues=[
            Finding(
                id="f2",
                severity=Severity.MINOR,
                attack_vector="clarity",
                what_is_wrong="Notation inconsistent",
                why_it_matters="Reduces readability",
                what_would_fix="Unify notation in Section 3",
                falsification="Show notation is actually consistent",
                grounding="Section 3",
                fixable=True,
            )
        ],
        verdict=Verdict.WEAK_REJECT,
        confidence=3,
    )


def _make_artifact_json(
    stage: str = "significance",
    content: str = "# Test Content",
    task_chain: dict | None = None,
) -> str:
    """Helper to build a mock LLM JSON response for ResearchArtifact."""
    tc = task_chain or {
        "task": "Pick up objects from cluttered shelves",
        "problem": "Optimize grasp success under partial observability (POMDP)",
        "challenge": None,
        "approach": None,
        "one_sentence": None,
        "chain_complete": False,
        "chain_coherent": False,
    }
    return json.dumps({
        "stage": stage,
        "content": content,
        "task_chain": tc,
        "metadata": {
            "confidence": "medium",
            "limitations": ["test limitation"],
            "human_review_flags": [],
        },
    })


def _make_revision_json(
    stage: str = "significance",
    review_version: int = 1,
) -> str:
    """Helper to build a mock LLM JSON response for revision."""
    return json.dumps({
        "artifact": {
            "stage": stage,
            "content": "# Revised Content\n\nAddressed findings.",
            "task_chain": {
                "task": "Pick up objects from cluttered shelves",
                "problem": "POMDP-based grasp planning",
                "challenge": "Partial observability of object geometry",
                "approach": None,
                "one_sentence": None,
                "chain_complete": False,
                "chain_coherent": False,
            },
            "metadata": {
                "confidence": "medium",
                "limitations": ["still early"],
                "human_review_flags": [],
            },
        },
        "revision_response": {
            "review_version": review_version,
            "addressed": [
                {
                    "finding_id": "f1",
                    "action_taken": "Added concrete consequence in Section 1",
                    "evidence": "Section 1, paragraph 3",
                }
            ],
            "deferred": [],
            "disputed": [
                {
                    "finding_id": "f2",
                    "argument": "Notation is consistent; reviewer may have misread",
                    "evidence": "Section 3 uses x consistently for position",
                }
            ],
        },
    })


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

class TestConstruction:
    def test_default_config(self, knowledge_store):
        """Agent can be constructed with default config."""
        agent = ResearchAgent(knowledge_store=knowledge_store)
        assert agent.config.name == "Robotics Research"
        assert len(agent.config.focus_areas) > 0

    def test_custom_config(self, knowledge_store, config):
        """Agent can be constructed with custom config."""
        agent = ResearchAgent(knowledge_store=knowledge_store, config=config)
        assert agent.config.name == "Test Research"
        assert agent.config.focus_areas == ["mobile manipulation"]

    def test_knowledge_store_stored(self, agent, knowledge_store):
        """Knowledge store reference is stored."""
        assert agent.knowledge_store is knowledge_store


# ---------------------------------------------------------------------------
# Prompt building
# ---------------------------------------------------------------------------

class TestPromptBuilding:
    @pytest.mark.parametrize("stage", [
        "significance", "formalization", "challenge",
        "approach", "validate", "full_draft",
    ])
    def test_prompt_for_each_stage(self, agent, stage):
        """Prompt is built successfully for every stage."""
        prompt = agent._build_prompt(stage, "How to grasp in clutter?")
        assert isinstance(prompt, str)
        assert len(prompt) > 100
        # Should contain stage-specific content
        stage_check = stage.upper().replace("_", " ")
        assert stage_check in prompt.upper() or stage in prompt

    def test_prompt_includes_question(self, agent):
        """Prompt includes the research question."""
        question = "How to grasp objects in cluttered shelves?"
        prompt = agent._build_prompt("significance", question)
        assert question in prompt

    def test_prompt_includes_identity(self, agent):
        """Prompt includes agent identity from config."""
        prompt = agent._build_prompt("significance", "test question")
        assert "Test Research" in prompt
        assert "mobile manipulation" in prompt

    def test_prompt_includes_stage_context(self, agent):
        """Prompt includes stage-specific instructions."""
        prompt = agent._build_prompt("significance", "test")
        assert "SIGNIFICANCE" in prompt
        assert "Hamming" in prompt  # significance tests

        prompt = agent._build_prompt("formalization", "test")
        assert "FORMALIZATION" in prompt
        assert "optimization" in prompt.lower()

    def test_prompt_with_findings(self, agent):
        """Prompt in revision mode includes previous findings."""
        findings = [
            {
                "id": "f1",
                "severity": "serious",
                "what_is_wrong": "Missing consequence test",
                "why_it_matters": "Cannot assess impact",
                "what_would_fix": "Add concrete consequence",
            }
        ]
        prompt = agent._build_prompt("significance", "test", findings=findings)
        assert "Missing consequence test" in prompt
        assert "Previous Review Findings" in prompt

    def test_revision_prompt(self, agent, sample_artifact, sample_review):
        """Revision prompt includes artifact content and findings."""
        prompt = agent._build_revision_prompt(sample_artifact, sample_review)
        assert "This problem matters because" in prompt
        assert "No concrete consequence given" in prompt
        assert "Notation inconsistent" in prompt
        assert "Current Artifact" in prompt

    def test_revision_prompt_includes_all_findings(self, agent, sample_artifact, sample_review):
        """Revision prompt contains all finding IDs."""
        prompt = agent._build_revision_prompt(sample_artifact, sample_review)
        assert "f1" in prompt
        assert "f2" in prompt


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestResponseParsing:
    def test_parse_artifact_json(self, agent):
        """Parse a well-formed artifact JSON response."""
        response = _make_artifact_json(stage="significance")
        artifact = agent._parse_response(response)
        assert isinstance(artifact, ResearchArtifact)
        assert artifact.stage == ResearchStage.SIGNIFICANCE
        assert "Test Content" in artifact.content
        assert artifact.task_chain.task == "Pick up objects from cluttered shelves"

    def test_parse_artifact_in_code_fence(self, agent):
        """Parse artifact JSON wrapped in markdown code fence."""
        raw_json = _make_artifact_json(stage="formalization")
        response = f"Here is the artifact:\n\n```json\n{raw_json}\n```\n\nDone."
        artifact = agent._parse_response(response)
        assert artifact.stage == ResearchStage.FORMALIZATION

    def test_parse_artifact_with_surrounding_text(self, agent):
        """Parse artifact JSON embedded in prose."""
        raw_json = _make_artifact_json(stage="challenge")
        response = f"After analysis, I produced:\n{raw_json}\nEnd of response."
        artifact = agent._parse_response(response)
        assert artifact.stage == ResearchStage.CHALLENGE

    def test_parse_revision_response(self, agent):
        """Parse a combined artifact + revision response."""
        response = _make_revision_json()
        artifact, revision = agent._parse_revision_response(response)

        assert isinstance(artifact, ResearchArtifact)
        assert isinstance(revision, RevisionResponse)
        assert revision.review_version == 1
        assert len(revision.addressed) == 1
        assert revision.addressed[0].finding_id == "f1"
        assert len(revision.disputed) == 1
        assert revision.disputed[0].finding_id == "f2"

    def test_parse_revision_resolution_rate(self, agent):
        """Revision resolution rate is computed correctly."""
        response = _make_revision_json()
        _, revision = agent._parse_revision_response(response)
        # 1 addressed, 0 deferred, 1 disputed = 1/2 = 0.5
        assert revision.resolution_rate == 0.5

    def test_parse_bad_json_raises(self, agent):
        """Malformed JSON raises an error."""
        with pytest.raises((json.JSONDecodeError, ValueError)):
            agent._parse_response("this is not json at all {{{")

    def test_parse_revision_missing_keys_raises(self, agent):
        """Revision response without required keys raises ValueError."""
        response = json.dumps({"random": "data"})
        with pytest.raises(ValueError, match="Could not parse revision response"):
            agent._parse_revision_response(response)


# ---------------------------------------------------------------------------
# State machine transitions
# ---------------------------------------------------------------------------

class TestTransitions:
    def test_significance_transitions(self):
        """Significance can go to formalization."""
        transitions = ResearchAgent.get_valid_transitions("significance")
        assert "formalization" in transitions

    def test_formalization_transitions(self):
        """Formalization can go back to significance or forward."""
        transitions = ResearchAgent.get_valid_transitions("formalization")
        assert "significance" in transitions
        assert "challenge" in transitions

    def test_challenge_transitions(self):
        """Challenge can go to approach or back."""
        transitions = ResearchAgent.get_valid_transitions("challenge")
        assert "approach" in transitions
        assert "formalization" in transitions

    def test_approach_transitions(self):
        """Approach can go to validate or back to challenge."""
        transitions = ResearchAgent.get_valid_transitions("approach")
        assert "validate" in transitions
        assert "challenge" in transitions

    def test_validate_transitions(self):
        """Validate can go to full_draft or back."""
        transitions = ResearchAgent.get_valid_transitions("validate")
        assert "full_draft" in transitions
        assert "approach" in transitions

    def test_full_draft_transitions(self):
        """Full draft can go back to validate."""
        transitions = ResearchAgent.get_valid_transitions("full_draft")
        assert "validate" in transitions

    def test_unknown_stage_returns_empty(self):
        """Unknown stage returns empty transitions."""
        assert ResearchAgent.get_valid_transitions("nonexistent") == []

    @pytest.mark.parametrize("stage", [
        "significance", "formalization", "diagnose",
        "challenge", "approach", "validate", "full_draft",
    ])
    def test_all_stages_have_transitions(self, stage):
        """Every defined stage has at least one transition."""
        transitions = ResearchAgent.get_valid_transitions(stage)
        assert len(transitions) >= 1


# ---------------------------------------------------------------------------
# Generate workflow
# ---------------------------------------------------------------------------

class TestGenerate:
    def test_generate_with_response(self, agent):
        """Generate produces an artifact when given response_text."""
        response = _make_artifact_json(stage="significance")
        artifact = agent.generate(
            stage="significance",
            question="How to grasp in clutter?",
            response_text=response,
        )
        assert isinstance(artifact, ResearchArtifact)
        assert artifact.stage == ResearchStage.SIGNIFICANCE

    def test_generate_without_response_returns_stub(self, agent):
        """Generate without response_text returns a prompt stub."""
        artifact = agent.generate(
            stage="significance",
            question="How to grasp in clutter?",
        )
        assert "awaiting LLM response" in artifact.content
        assert "prompt_length" in artifact.metadata

    def test_generate_with_findings(self, agent):
        """Generate in revision mode passes findings through."""
        findings = [{"id": "f1", "severity": "serious", "what_is_wrong": "Test"}]
        response = _make_artifact_json(stage="significance")
        artifact = agent.generate(
            stage="significance",
            question="test",
            response_text=response,
            findings=findings,
        )
        assert isinstance(artifact, ResearchArtifact)


# ---------------------------------------------------------------------------
# Revise workflow
# ---------------------------------------------------------------------------

class TestRevise:
    def test_revise_with_response(self, agent, sample_artifact, sample_review):
        """Revise produces updated artifact + revision response."""
        response = _make_revision_json()
        artifact, revision = agent.revise(
            artifact=sample_artifact,
            review=sample_review,
            response_text=response,
        )
        assert isinstance(artifact, ResearchArtifact)
        assert isinstance(revision, RevisionResponse)
        assert artifact.version == 2  # incremented from 1
        assert "Revised Content" in artifact.content

    def test_revise_without_response_returns_stub(self, agent, sample_artifact, sample_review):
        """Revise without response_text returns stubs."""
        artifact, revision = agent.revise(
            artifact=sample_artifact,
            review=sample_review,
        )
        assert "awaiting LLM response" in artifact.content
        assert artifact.version == 2
        assert revision.review_version == 1


# ---------------------------------------------------------------------------
# run_digest (mocked tools)
# ---------------------------------------------------------------------------

class TestRunDigest:
    def test_run_digest_produces_report(self, agent):
        """run_digest returns a markdown digest report."""
        mock_candidates = [
            PaperCandidate(
                arxiv_id="2301.00001",
                title="Test Paper on Grasping",
                authors=["Alice", "Bob"],
                abstract="We study grasping in clutter.",
                year=2023,
                source="arxiv",
            ),
            PaperCandidate(
                arxiv_id="2301.00002",
                title="Another Paper on Manipulation",
                authors=["Carol"],
                abstract="Mobile manipulation approach.",
                year=2023,
                source="arxiv",
            ),
        ]

        mock_paper = Paper(
            arxiv_id="2301.00001",
            title="Test Paper on Grasping",
            authors=["Alice", "Bob"],
            abstract="We study grasping in clutter.",
            year=2023,
        )

        with patch(
            "alpha_research.tools.arxiv_search.search_arxiv",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ) as mock_search, patch(
            "alpha_research.tools.paper_fetch.fetch_and_extract",
            new_callable=AsyncMock,
            return_value=mock_paper,
        ) as mock_fetch:
            report = asyncio.run(
                agent.run_digest("grasping in clutter", max_papers=5)
            )

        assert isinstance(report, str)
        assert "Research Digest" in report
        assert "grasping in clutter" in report
        mock_search.assert_called_once()
        assert mock_fetch.call_count == 2  # two candidates

    def test_run_digest_handles_fetch_failure(self, agent):
        """run_digest continues when a fetch fails."""
        mock_candidates = [
            PaperCandidate(
                arxiv_id="2301.00001",
                title="Good Paper",
                authors=["Alice"],
                abstract="Works fine.",
                year=2023,
                source="arxiv",
            ),
        ]

        with patch(
            "alpha_research.tools.arxiv_search.search_arxiv",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ), patch(
            "alpha_research.tools.paper_fetch.fetch_and_extract",
            new_callable=AsyncMock,
            side_effect=Exception("Download failed"),
        ):
            report = asyncio.run(
                agent.run_digest("test query", max_papers=5)
            )

        assert isinstance(report, str)
        assert "Good Paper" in report

    def test_run_digest_stores_papers(self, agent, knowledge_store):
        """run_digest saves papers to the knowledge store."""
        mock_candidates = [
            PaperCandidate(
                arxiv_id="2301.99999",
                title="Stored Paper",
                authors=["Eve"],
                abstract="Test storage.",
                year=2024,
                source="arxiv",
            ),
        ]
        mock_paper = Paper(
            arxiv_id="2301.99999",
            title="Stored Paper",
            authors=["Eve"],
            abstract="Test storage.",
            year=2024,
        )

        with patch(
            "alpha_research.tools.arxiv_search.search_arxiv",
            new_callable=AsyncMock,
            return_value=mock_candidates,
        ), patch(
            "alpha_research.tools.paper_fetch.fetch_and_extract",
            new_callable=AsyncMock,
            return_value=mock_paper,
        ):
            asyncio.run(
                agent.run_digest("test", max_papers=5)
            )

        # Verify paper was stored
        paper = knowledge_store.get_paper("2301.99999")
        assert paper is not None
        assert paper.title == "Stored Paper"


# ---------------------------------------------------------------------------
# run_deep (mocked tools)
# ---------------------------------------------------------------------------

class TestRunDeep:
    def test_run_deep_produces_report(self, agent):
        """run_deep returns a deep analysis report."""
        mock_paper = Paper(
            arxiv_id="2301.12345",
            title="Deep Analysis Paper",
            authors=["Alice", "Bob"],
            abstract="A detailed study of manipulation.",
            year=2023,
            full_text="Full text of the paper...",
            sections={"introduction": "Intro text", "method": "Method text"},
        )

        with patch(
            "alpha_research.tools.paper_fetch.fetch_and_extract",
            new_callable=AsyncMock,
            return_value=mock_paper,
        ) as mock_fetch:
            report = asyncio.run(
                agent.run_deep("2301.12345")
            )

        assert isinstance(report, str)
        assert "Deep Analysis Paper" in report
        assert "Paper Evaluation" in report
        mock_fetch.assert_called_once_with("2301.12345")

    def test_run_deep_stores_paper(self, agent, knowledge_store):
        """run_deep saves the paper to the knowledge store."""
        mock_paper = Paper(
            arxiv_id="2301.54321",
            title="Stored Deep Paper",
            authors=["Carol"],
            abstract="Storage test.",
            year=2024,
        )

        with patch(
            "alpha_research.tools.paper_fetch.fetch_and_extract",
            new_callable=AsyncMock,
            return_value=mock_paper,
        ):
            asyncio.run(
                agent.run_deep("2301.54321")
            )

        paper = knowledge_store.get_paper("2301.54321")
        assert paper is not None
        assert paper.title == "Stored Deep Paper"


# ---------------------------------------------------------------------------
# JSON extraction helper
# ---------------------------------------------------------------------------

class TestExtractJsonBlock:
    def test_plain_json(self):
        data = '{"key": "value"}'
        assert json.loads(_extract_json_block(data)) == {"key": "value"}

    def test_code_fence(self):
        text = "Some text\n```json\n{\"key\": \"value\"}\n```\nMore text"
        assert json.loads(_extract_json_block(text)) == {"key": "value"}

    def test_bare_code_fence(self):
        text = "```\n{\"key\": \"value\"}\n```"
        assert json.loads(_extract_json_block(text)) == {"key": "value"}

    def test_json_with_surrounding_prose(self):
        text = 'Here is the output: {"stage": "significance"} end.'
        result = json.loads(_extract_json_block(text))
        assert result["stage"] == "significance"
