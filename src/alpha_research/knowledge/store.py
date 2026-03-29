"""CRUD operations for the knowledge store."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any

from alpha_research.knowledge.schema import create_tables
from alpha_research.models.research import Evaluation, Paper


class KnowledgeStore:
    """Persistent knowledge store backed by SQLite.

    Parameters
    ----------
    db_path : str | Path
        Path to the SQLite database file.  Tables are created automatically
        on first use.
    """

    def __init__(self, db_path: str | Path) -> None:
        self.db_path = Path(db_path)
        create_tables(self.db_path)

    # ------------------------------------------------------------------
    # helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    @staticmethod
    def _json(obj: Any) -> str:
        """Serialize an object to a JSON string."""
        if obj is None:
            return "null"
        if hasattr(obj, "model_dump"):
            return json.dumps(obj.model_dump(mode="json"), default=str)
        return json.dumps(obj, default=str)

    @staticmethod
    def _json_list(items: list) -> str:
        dumped = []
        for item in items:
            if hasattr(item, "model_dump"):
                dumped.append(item.model_dump(mode="json"))
            else:
                dumped.append(item)
        return json.dumps(dumped, default=str)

    @staticmethod
    def _json_dict(mapping: dict) -> str:
        dumped = {}
        for k, v in mapping.items():
            if hasattr(v, "model_dump"):
                dumped[k] = v.model_dump(mode="json")
            else:
                dumped[k] = v
        return json.dumps(dumped, default=str)

    # ------------------------------------------------------------------
    # Paper CRUD
    # ------------------------------------------------------------------

    def save_paper(self, paper: Paper) -> int:
        """Upsert a paper.  Deduplicates on arxiv_id, s2_id, or doi.

        Returns the database row id.
        """
        conn = self._connect()
        try:
            # Check for existing paper by any of the three identifiers
            existing_id = self._find_existing_paper(conn, paper)

            values = {
                "arxiv_id": paper.arxiv_id,
                "s2_id": paper.s2_id,
                "doi": paper.doi,
                "title": paper.title,
                "authors": json.dumps(paper.authors),
                "venue": paper.venue,
                "year": paper.year,
                "abstract": paper.abstract,
                "full_text": paper.full_text,
                "sections": json.dumps(paper.sections),
                "extraction_source": paper.extraction_source,
                "extraction_quality": self._json(paper.extraction_quality),
                "metadata": self._json(paper.metadata),
                "status": paper.status.value if hasattr(paper.status, "value") else paper.status,
                "url": paper.url,
            }

            if existing_id is not None:
                # UPDATE
                set_clause = ", ".join(f"{k} = ?" for k in values)
                set_clause += ", updated_at = datetime('now')"
                conn.execute(
                    f"UPDATE papers SET {set_clause} WHERE id = ?",
                    [*values.values(), existing_id],
                )
                conn.commit()
                return existing_id
            else:
                # INSERT
                cols = ", ".join(values.keys())
                placeholders = ", ".join("?" for _ in values)
                cur = conn.execute(
                    f"INSERT INTO papers ({cols}) VALUES ({placeholders})",
                    list(values.values()),
                )
                conn.commit()
                return cur.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()

    def _find_existing_paper(
        self, conn: sqlite3.Connection, paper: Paper
    ) -> int | None:
        """Return the row id of an existing paper that matches any identifier."""
        conditions = []
        params: list[str] = []
        if paper.arxiv_id:
            conditions.append("arxiv_id = ?")
            params.append(paper.arxiv_id)
        if paper.s2_id:
            conditions.append("s2_id = ?")
            params.append(paper.s2_id)
        if paper.doi:
            conditions.append("doi = ?")
            params.append(paper.doi)
        if not conditions:
            return None
        where = " OR ".join(conditions)
        row = conn.execute(
            f"SELECT id FROM papers WHERE {where} LIMIT 1", params
        ).fetchone()
        return row["id"] if row else None

    def get_paper(self, paper_id: str) -> Paper | None:
        """Retrieve a paper by arxiv_id, s2_id, doi, or row id."""
        conn = self._connect()
        try:
            row = conn.execute(
                "SELECT * FROM papers WHERE arxiv_id = ? OR s2_id = ? OR doi = ? OR CAST(id AS TEXT) = ? LIMIT 1",
                (paper_id, paper_id, paper_id, paper_id),
            ).fetchone()
            if row is None:
                return None
            return self._row_to_paper(row)
        finally:
            conn.close()

    def query_papers(
        self,
        topic: str | None = None,
        date_range: tuple[str, str] | None = None,
        min_score: float | None = None,
        limit: int = 50,
    ) -> list[Paper]:
        """Query papers with optional filters.

        Parameters
        ----------
        topic : str, optional
            LIKE search on title and abstract.
        date_range : tuple[str, str], optional
            (start_year, end_year) inclusive.
        min_score : float, optional
            Minimum average rubric score (requires a join to evaluations).
        limit : int
            Maximum number of results.
        """
        conn = self._connect()
        try:
            clauses: list[str] = []
            params: list[Any] = []

            if topic:
                clauses.append("(title LIKE ? OR abstract LIKE ?)")
                pattern = f"%{topic}%"
                params.extend([pattern, pattern])

            if date_range:
                clauses.append("year >= ? AND year <= ?")
                params.extend([int(date_range[0]), int(date_range[1])])

            where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

            if min_score is not None:
                # Join with evaluations to filter by average rubric score
                sql = f"""
                    SELECT p.* FROM papers p
                    INNER JOIN evaluations e ON (
                        p.arxiv_id = e.paper_id OR p.s2_id = e.paper_id
                        OR p.doi = e.paper_id
                    )
                    {where}
                    GROUP BY p.id
                    HAVING AVG(
                        CAST(json_extract(e.rubric_scores, '$') AS REAL)
                    ) >= ?
                    ORDER BY p.updated_at DESC
                    LIMIT ?
                """
                params.extend([min_score, limit])
            else:
                sql = f"SELECT * FROM papers{where} ORDER BY updated_at DESC LIMIT ?"
                params.append(limit)

            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_paper(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _row_to_paper(row: sqlite3.Row) -> Paper:
        """Convert a database row to a Paper model."""
        d = dict(row)
        # Parse JSON columns
        d["authors"] = json.loads(d.get("authors") or "[]")
        d["sections"] = json.loads(d.get("sections") or "{}")
        eq_raw = d.pop("extraction_quality", None)
        d["extraction_quality"] = json.loads(eq_raw) if eq_raw and eq_raw != "null" else None
        meta_raw = d.pop("metadata", None)
        d["metadata"] = json.loads(meta_raw) if meta_raw else {}
        # Remove DB-only columns
        d.pop("id", None)
        d.pop("created_at", None)
        d.pop("updated_at", None)
        return Paper.model_validate(d)

    # ------------------------------------------------------------------
    # Evaluation CRUD
    # ------------------------------------------------------------------

    def save_evaluation(self, evaluation: Evaluation) -> int:
        """Insert an evaluation record linked to a paper and cycle.

        Returns the database row id.
        """
        conn = self._connect()
        try:
            values = {
                "paper_id": evaluation.paper_id,
                "cycle_id": evaluation.cycle_id,
                "mode": evaluation.mode,
                "status": evaluation.status.value if hasattr(evaluation.status, "value") else evaluation.status,
                "task_chain": self._json(evaluation.task_chain),
                "has_formal_problem_def": int(evaluation.has_formal_problem_def),
                "formal_framework": evaluation.formal_framework,
                "structure_identified": json.dumps(evaluation.structure_identified),
                "rubric_scores": self._json_dict(evaluation.rubric_scores),
                "significance_assessment": self._json(evaluation.significance_assessment),
                "related_papers": self._json_list(evaluation.related_papers),
                "contradictions": self._json_list(evaluation.contradictions),
                "novelty_vs_store": evaluation.novelty_vs_store,
                "extraction_limitations": json.dumps(evaluation.extraction_limitations),
                "human_review_flags": json.dumps(evaluation.human_review_flags),
                "created_at": evaluation.created_at.isoformat() if evaluation.created_at else None,
            }
            cols = ", ".join(values.keys())
            placeholders = ", ".join("?" for _ in values)
            cur = conn.execute(
                f"INSERT INTO evaluations ({cols}) VALUES ({placeholders})",
                list(values.values()),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()

    def get_evaluations(self, paper_id: str) -> list[Evaluation]:
        """Get all evaluations for a given paper_id."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM evaluations WHERE paper_id = ? ORDER BY created_at",
                (paper_id,),
            ).fetchall()
            return [self._row_to_evaluation(r) for r in rows]
        finally:
            conn.close()

    @staticmethod
    def _row_to_evaluation(row: sqlite3.Row) -> Evaluation:
        d = dict(row)
        d.pop("id", None)

        # Parse JSON columns
        tc_raw = d.pop("task_chain", None)
        d["task_chain"] = json.loads(tc_raw) if tc_raw and tc_raw != "null" else None

        d["has_formal_problem_def"] = bool(d.get("has_formal_problem_def", 0))
        d["structure_identified"] = json.loads(d.get("structure_identified") or "[]")
        d["rubric_scores"] = json.loads(d.get("rubric_scores") or "{}")

        sa_raw = d.pop("significance_assessment", None)
        d["significance_assessment"] = json.loads(sa_raw) if sa_raw and sa_raw != "null" else None

        d["related_papers"] = json.loads(d.get("related_papers") or "[]")
        d["contradictions"] = json.loads(d.get("contradictions") or "[]")
        d["extraction_limitations"] = json.loads(d.get("extraction_limitations") or "[]")
        d["human_review_flags"] = json.loads(d.get("human_review_flags") or "[]")

        return Evaluation.model_validate(d)

    # ------------------------------------------------------------------
    # Findings
    # ------------------------------------------------------------------

    def save_finding(self, finding_data: dict) -> int:
        """Save a finding record.

        Parameters
        ----------
        finding_data : dict
            Must contain at least ``cycle_id``.  Other keys are stored
            both as individual columns (when present) and as a full JSON
            blob in the ``data`` column.
        """
        conn = self._connect()
        try:
            values = {
                "cycle_id": finding_data.get("cycle_id", ""),
                "finding_id": finding_data.get("finding_id", finding_data.get("id", "")),
                "severity": finding_data.get("severity"),
                "attack_vector": finding_data.get("attack_vector"),
                "what_is_wrong": finding_data.get("what_is_wrong"),
                "why_it_matters": finding_data.get("why_it_matters"),
                "what_would_fix": finding_data.get("what_would_fix"),
                "falsification": finding_data.get("falsification"),
                "grounding": finding_data.get("grounding"),
                "fixable": int(finding_data.get("fixable", True)),
                "maps_to_trigger": finding_data.get("maps_to_trigger"),
                "data": json.dumps(finding_data, default=str),
            }
            cols = ", ".join(values.keys())
            placeholders = ", ".join("?" for _ in values)
            cur = conn.execute(
                f"INSERT INTO findings ({cols}) VALUES ({placeholders})",
                list(values.values()),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()

    def query_findings(self, cycle_id: str) -> list[dict]:
        """Return all findings for a given cycle_id."""
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT * FROM findings WHERE cycle_id = ? ORDER BY id",
                (cycle_id,),
            ).fetchall()
            results = []
            for row in rows:
                d = dict(row)
                # Parse the full JSON blob
                data = json.loads(d.get("data") or "{}")
                # Merge DB columns into the dict for convenience
                data["db_id"] = d["id"]
                data["created_at"] = d["created_at"]
                results.append(data)
            return results
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # Paper Relations
    # ------------------------------------------------------------------

    def save_relation(
        self,
        paper_a_id: str,
        paper_b_id: str,
        relation_type: str,
        evidence: str = "",
        confidence: str = "medium",
    ) -> int:
        """Save a relationship between two papers.

        Returns the database row id.
        """
        conn = self._connect()
        try:
            cur = conn.execute(
                "INSERT INTO paper_relations (paper_a_id, paper_b_id, relation_type, evidence, confidence) VALUES (?, ?, ?, ?, ?)",
                (paper_a_id, paper_b_id, relation_type, evidence, confidence),
            )
            conn.commit()
            return cur.lastrowid  # type: ignore[return-value]
        finally:
            conn.close()

    def get_related_papers(self, paper_id: str) -> list[dict]:
        """Get all relations where paper_id is either side."""
        conn = self._connect()
        try:
            rows = conn.execute(
                """SELECT * FROM paper_relations
                   WHERE paper_a_id = ? OR paper_b_id = ?
                   ORDER BY id""",
                (paper_id, paper_id),
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
