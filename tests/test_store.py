"""Tests for the knowledge store (schema + CRUD)."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from alpha_research.knowledge.schema import create_tables
from alpha_research.knowledge.store import KnowledgeStore
from alpha_research.models.research import (
    Evaluation,
    EvaluationStatus,
    ExtractionQuality,
    Paper,
    PaperMetadata,
    PaperStatus,
    RubricScore,
    SignificanceAssessment,
    TaskChain,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_knowledge.db"


@pytest.fixture()
def store(db_path: Path) -> KnowledgeStore:
    return KnowledgeStore(db_path)


def _make_paper(**overrides) -> Paper:
    defaults = dict(
        arxiv_id="2401.00001",
        title="Test Paper: Mobile Manipulation with RL",
        authors=["Alice", "Bob"],
        venue="ICRA",
        year=2024,
        abstract="We present a mobile manipulation approach using reinforcement learning.",
        status=PaperStatus.STORED,
    )
    defaults.update(overrides)
    return Paper(**defaults)


def _make_evaluation(paper_id: str = "2401.00001", **overrides) -> Evaluation:
    defaults = dict(
        paper_id=paper_id,
        cycle_id="cycle-001",
        mode="deep",
        status=EvaluationStatus.EVALUATED,
        task_chain=TaskChain(
            task="mobile manipulation",
            problem="grasping in clutter",
            challenge="collision avoidance",
            approach="RL-based planner",
            one_sentence="RL planner avoids collisions in clutter.",
        ),
        rubric_scores={
            "novelty": RubricScore(score=4, confidence="high", evidence=["new method"]),
            "significance": RubricScore(score=3, confidence="medium"),
        },
        significance_assessment=SignificanceAssessment(hamming_score=4),
    )
    defaults.update(overrides)
    return Evaluation(**defaults)


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------

class TestSchema:
    def test_create_tables(self, db_path: Path) -> None:
        create_tables(db_path)
        assert db_path.exists()

        conn = sqlite3.connect(str(db_path))
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        conn.close()

        expected = {
            "papers",
            "evaluations",
            "paper_relations",
            "findings",
            "frontier_snapshots",
            "topic_clusters",
            "questions",
            "feedback",
        }
        assert expected.issubset(tables)

    def test_create_tables_idempotent(self, db_path: Path) -> None:
        create_tables(db_path)
        create_tables(db_path)  # second call should not raise

    def test_creates_parent_dirs(self, tmp_path: Path) -> None:
        deep = tmp_path / "a" / "b" / "c" / "test.db"
        create_tables(deep)
        assert deep.exists()


# ---------------------------------------------------------------------------
# Paper CRUD
# ---------------------------------------------------------------------------

class TestPaperCRUD:
    def test_save_and_get(self, store: KnowledgeStore) -> None:
        paper = _make_paper()
        row_id = store.save_paper(paper)
        assert isinstance(row_id, int)

        retrieved = store.get_paper("2401.00001")
        assert retrieved is not None
        assert retrieved.title == paper.title
        assert retrieved.authors == ["Alice", "Bob"]
        assert retrieved.year == 2024

    def test_get_by_s2_id(self, store: KnowledgeStore) -> None:
        paper = _make_paper(arxiv_id=None, s2_id="S2_123")
        store.save_paper(paper)
        assert store.get_paper("S2_123") is not None

    def test_get_by_doi(self, store: KnowledgeStore) -> None:
        paper = _make_paper(arxiv_id=None, doi="10.1234/test")
        store.save_paper(paper)
        assert store.get_paper("10.1234/test") is not None

    def test_get_missing_paper(self, store: KnowledgeStore) -> None:
        assert store.get_paper("nonexistent") is None

    def test_dedup_by_arxiv_id(self, store: KnowledgeStore) -> None:
        """Saving the same paper twice by arxiv_id should update, not duplicate."""
        paper1 = _make_paper(title="Version 1")
        paper2 = _make_paper(title="Version 2")  # same arxiv_id

        id1 = store.save_paper(paper1)
        id2 = store.save_paper(paper2)

        assert id1 == id2  # same row

        retrieved = store.get_paper("2401.00001")
        assert retrieved is not None
        assert retrieved.title == "Version 2"

        # Verify only one row
        all_papers = store.query_papers(limit=100)
        assert len(all_papers) == 1

    def test_dedup_by_s2_id(self, store: KnowledgeStore) -> None:
        paper1 = _make_paper(arxiv_id=None, s2_id="S2_999", title="V1")
        paper2 = _make_paper(arxiv_id=None, s2_id="S2_999", title="V2")
        store.save_paper(paper1)
        store.save_paper(paper2)

        retrieved = store.get_paper("S2_999")
        assert retrieved is not None
        assert retrieved.title == "V2"

    def test_dedup_by_doi(self, store: KnowledgeStore) -> None:
        paper1 = _make_paper(arxiv_id=None, doi="10.0/abc", title="V1")
        paper2 = _make_paper(arxiv_id=None, doi="10.0/abc", title="V2")
        store.save_paper(paper1)
        store.save_paper(paper2)

        retrieved = store.get_paper("10.0/abc")
        assert retrieved is not None
        assert retrieved.title == "V2"

    def test_paper_with_extraction_quality(self, store: KnowledgeStore) -> None:
        paper = _make_paper(
            extraction_quality=ExtractionQuality(
                overall="high", math_preserved=True, sections_detected=["intro", "method"]
            )
        )
        store.save_paper(paper)
        retrieved = store.get_paper("2401.00001")
        assert retrieved is not None
        assert retrieved.extraction_quality is not None
        assert retrieved.extraction_quality.overall == "high"

    def test_paper_with_metadata(self, store: KnowledgeStore) -> None:
        paper = _make_paper(
            metadata=PaperMetadata(citation_count=42, tldr="A cool paper")
        )
        store.save_paper(paper)
        retrieved = store.get_paper("2401.00001")
        assert retrieved is not None
        assert retrieved.metadata.citation_count == 42
        assert retrieved.metadata.tldr == "A cool paper"

    def test_paper_sections_roundtrip(self, store: KnowledgeStore) -> None:
        paper = _make_paper(sections={"intro": "Hello", "method": "We do X"})
        store.save_paper(paper)
        retrieved = store.get_paper("2401.00001")
        assert retrieved is not None
        assert retrieved.sections == {"intro": "Hello", "method": "We do X"}


# ---------------------------------------------------------------------------
# Paper queries
# ---------------------------------------------------------------------------

class TestQueryPapers:
    def test_query_by_topic(self, store: KnowledgeStore) -> None:
        store.save_paper(_make_paper(arxiv_id="a1", title="Mobile Manipulation with RL"))
        store.save_paper(_make_paper(arxiv_id="a2", title="Vision Transformers for NLP", abstract="A study on attention mechanisms."))
        store.save_paper(
            _make_paper(arxiv_id="a3", title="Grasping", abstract="mobile manipulation approach")
        )

        results = store.query_papers(topic="mobile manipulation")
        titles = {p.title for p in results}
        assert "Mobile Manipulation with RL" in titles
        assert "Grasping" in titles  # matched on abstract
        assert "Vision Transformers for NLP" not in titles

    def test_query_by_date_range(self, store: KnowledgeStore) -> None:
        store.save_paper(_make_paper(arxiv_id="a1", year=2022))
        store.save_paper(_make_paper(arxiv_id="a2", year=2023))
        store.save_paper(_make_paper(arxiv_id="a3", year=2024))

        results = store.query_papers(date_range=("2023", "2024"))
        years = {p.year for p in results}
        assert years == {2023, 2024}

    def test_query_limit(self, store: KnowledgeStore) -> None:
        for i in range(10):
            store.save_paper(_make_paper(arxiv_id=f"a{i}"))
        results = store.query_papers(limit=3)
        assert len(results) == 3

    def test_query_empty_db(self, store: KnowledgeStore) -> None:
        results = store.query_papers()
        assert results == []

    def test_query_combined_filters(self, store: KnowledgeStore) -> None:
        store.save_paper(_make_paper(arxiv_id="a1", title="RL Grasping", year=2023))
        store.save_paper(_make_paper(arxiv_id="a2", title="RL Grasping", year=2021))
        store.save_paper(_make_paper(arxiv_id="a3", title="Vision Model", year=2023))

        results = store.query_papers(topic="RL Grasping", date_range=("2023", "2024"))
        assert len(results) == 1
        assert results[0].arxiv_id == "a1"


# ---------------------------------------------------------------------------
# Evaluation CRUD
# ---------------------------------------------------------------------------

class TestEvaluationCRUD:
    def test_save_and_get(self, store: KnowledgeStore) -> None:
        store.save_paper(_make_paper())
        ev = _make_evaluation()
        row_id = store.save_evaluation(ev)
        assert isinstance(row_id, int)

        evals = store.get_evaluations("2401.00001")
        assert len(evals) == 1
        assert evals[0].cycle_id == "cycle-001"
        assert evals[0].task_chain is not None
        assert evals[0].task_chain.task == "mobile manipulation"

    def test_multiple_evaluations(self, store: KnowledgeStore) -> None:
        store.save_paper(_make_paper())
        store.save_evaluation(_make_evaluation(cycle_id="c1"))
        store.save_evaluation(_make_evaluation(cycle_id="c2"))

        evals = store.get_evaluations("2401.00001")
        assert len(evals) == 2
        cycles = {e.cycle_id for e in evals}
        assert cycles == {"c1", "c2"}

    def test_evaluations_for_missing_paper(self, store: KnowledgeStore) -> None:
        evals = store.get_evaluations("nonexistent")
        assert evals == []

    def test_rubric_scores_roundtrip(self, store: KnowledgeStore) -> None:
        ev = _make_evaluation()
        store.save_evaluation(ev)
        evals = store.get_evaluations("2401.00001")
        assert "novelty" in evals[0].rubric_scores
        score = evals[0].rubric_scores["novelty"]
        assert score.score == 4

    def test_significance_roundtrip(self, store: KnowledgeStore) -> None:
        ev = _make_evaluation()
        store.save_evaluation(ev)
        evals = store.get_evaluations("2401.00001")
        assert evals[0].significance_assessment is not None
        assert evals[0].significance_assessment.hamming_score == 4


# ---------------------------------------------------------------------------
# Paper Relations
# ---------------------------------------------------------------------------

class TestPaperRelations:
    def test_save_and_get_relations(self, store: KnowledgeStore) -> None:
        store.save_relation("a1", "a2", "extends", "paper A extends B", "high")
        rels = store.get_related_papers("a1")
        assert len(rels) == 1
        assert rels[0]["paper_b_id"] == "a2"
        assert rels[0]["relation_type"] == "extends"
        assert rels[0]["confidence"] == "high"

    def test_bidirectional_lookup(self, store: KnowledgeStore) -> None:
        store.save_relation("a1", "a2", "cites")
        # Should be found from either side
        assert len(store.get_related_papers("a1")) == 1
        assert len(store.get_related_papers("a2")) == 1

    def test_multiple_relations(self, store: KnowledgeStore) -> None:
        store.save_relation("a1", "a2", "extends")
        store.save_relation("a1", "a3", "same_task")
        store.save_relation("a4", "a1", "contradicts")

        rels = store.get_related_papers("a1")
        assert len(rels) == 3

    def test_no_relations(self, store: KnowledgeStore) -> None:
        assert store.get_related_papers("lonely_paper") == []


# ---------------------------------------------------------------------------
# Findings
# ---------------------------------------------------------------------------

class TestFindings:
    def test_save_and_query(self, store: KnowledgeStore) -> None:
        finding = {
            "cycle_id": "cycle-001",
            "finding_id": "f1",
            "severity": "serious",
            "attack_vector": "missing_ablation",
            "what_is_wrong": "No ablation study",
            "why_it_matters": "Cannot attribute gains to proposed method",
            "what_would_fix": "Add ablation removing key component",
            "falsification": "If ablation shows same result, critique invalid",
            "grounding": "Section 5, Table 2",
            "fixable": True,
        }
        row_id = store.save_finding(finding)
        assert isinstance(row_id, int)

        findings = store.query_findings("cycle-001")
        assert len(findings) == 1
        assert findings[0]["severity"] == "serious"
        assert findings[0]["what_is_wrong"] == "No ablation study"

    def test_multiple_findings_per_cycle(self, store: KnowledgeStore) -> None:
        for i in range(3):
            store.save_finding({"cycle_id": "c1", "finding_id": f"f{i}", "severity": "minor"})
        assert len(store.query_findings("c1")) == 3

    def test_findings_empty_cycle(self, store: KnowledgeStore) -> None:
        assert store.query_findings("nonexistent") == []

    def test_findings_different_cycles(self, store: KnowledgeStore) -> None:
        store.save_finding({"cycle_id": "c1", "severity": "fatal"})
        store.save_finding({"cycle_id": "c2", "severity": "minor"})
        assert len(store.query_findings("c1")) == 1
        assert len(store.query_findings("c2")) == 1


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_empty_db_queries(self, store: KnowledgeStore) -> None:
        assert store.get_paper("anything") is None
        assert store.get_evaluations("anything") == []
        assert store.get_related_papers("anything") == []
        assert store.query_findings("anything") == []
        assert store.query_papers() == []

    def test_paper_no_identifiers(self, store: KnowledgeStore) -> None:
        """A paper with no arxiv_id/s2_id/doi should still be insertable."""
        paper = _make_paper(arxiv_id=None, s2_id=None, doi=None, title="Orphan Paper")
        row_id = store.save_paper(paper)
        assert isinstance(row_id, int)

    def test_paper_empty_fields(self, store: KnowledgeStore) -> None:
        paper = Paper(title="Minimal Paper")
        store.save_paper(paper)
        results = store.query_papers(topic="Minimal")
        assert len(results) == 1
        assert results[0].title == "Minimal Paper"

    def test_special_characters_in_topic(self, store: KnowledgeStore) -> None:
        store.save_paper(_make_paper(title="RL: A (New) Approach [v2]"))
        results = store.query_papers(topic="(New)")
        assert len(results) == 1

    def test_concurrent_store_instances(self, db_path: Path) -> None:
        """Two store instances pointing at the same DB should not conflict."""
        s1 = KnowledgeStore(db_path)
        s2 = KnowledgeStore(db_path)
        s1.save_paper(_make_paper(arxiv_id="a1"))
        assert s2.get_paper("a1") is not None
