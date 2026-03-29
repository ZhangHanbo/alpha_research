"""SQLite schema for the knowledge store.

Tables:
  papers, evaluations, paper_relations, findings,
  frontier_snapshots, topic_clusters, questions, feedback
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS papers (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    arxiv_id        TEXT,
    s2_id           TEXT,
    doi             TEXT,
    title           TEXT NOT NULL,
    authors         TEXT DEFAULT '[]',          -- JSON list
    venue           TEXT,
    year            INTEGER,
    abstract        TEXT DEFAULT '',
    full_text       TEXT,
    sections        TEXT DEFAULT '{}',          -- JSON dict
    extraction_source TEXT DEFAULT 'abstract_only',
    extraction_quality TEXT,                    -- JSON (ExtractionQuality)
    metadata        TEXT DEFAULT '{}',          -- JSON (PaperMetadata)
    status          TEXT DEFAULT 'discovered',
    url             TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(arxiv_id),
    UNIQUE(s2_id),
    UNIQUE(doi)
);

CREATE INDEX IF NOT EXISTS idx_papers_arxiv_id ON papers(arxiv_id);
CREATE INDEX IF NOT EXISTS idx_papers_s2_id ON papers(s2_id);
CREATE INDEX IF NOT EXISTS idx_papers_doi ON papers(doi);
CREATE INDEX IF NOT EXISTS idx_papers_year ON papers(year);

CREATE TABLE IF NOT EXISTS evaluations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_id        TEXT NOT NULL,
    cycle_id        TEXT DEFAULT '',
    mode            TEXT DEFAULT '',
    status          TEXT DEFAULT 'skimmed',
    task_chain      TEXT,                       -- JSON (TaskChain)
    has_formal_problem_def INTEGER DEFAULT 0,
    formal_framework TEXT,
    structure_identified TEXT DEFAULT '[]',      -- JSON list
    rubric_scores   TEXT DEFAULT '{}',          -- JSON dict of RubricScore
    significance_assessment TEXT,               -- JSON (SignificanceAssessment)
    related_papers  TEXT DEFAULT '[]',          -- JSON list
    contradictions  TEXT DEFAULT '[]',          -- JSON list
    novelty_vs_store TEXT DEFAULT 'unknown',
    extraction_limitations TEXT DEFAULT '[]',   -- JSON list
    human_review_flags TEXT DEFAULT '[]',       -- JSON list
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_evaluations_paper_id ON evaluations(paper_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_cycle_id ON evaluations(cycle_id);

CREATE TABLE IF NOT EXISTS paper_relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    paper_a_id      TEXT NOT NULL,
    paper_b_id      TEXT NOT NULL,
    relation_type   TEXT NOT NULL,
    evidence        TEXT DEFAULT '',
    confidence      TEXT DEFAULT 'medium',
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_relations_paper_a ON paper_relations(paper_a_id);
CREATE INDEX IF NOT EXISTS idx_relations_paper_b ON paper_relations(paper_b_id);

CREATE TABLE IF NOT EXISTS findings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        TEXT DEFAULT '',
    finding_id      TEXT DEFAULT '',
    severity        TEXT,
    attack_vector   TEXT,
    what_is_wrong   TEXT,
    why_it_matters  TEXT,
    what_would_fix  TEXT,
    falsification   TEXT,
    grounding       TEXT,
    fixable         INTEGER DEFAULT 1,
    maps_to_trigger TEXT,
    data            TEXT DEFAULT '{}',          -- full JSON blob
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_findings_cycle_id ON findings(cycle_id);

CREATE TABLE IF NOT EXISTS frontier_snapshots (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        TEXT DEFAULT '',
    snapshot_data   TEXT DEFAULT '{}',          -- JSON blob
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS topic_clusters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    topic           TEXT NOT NULL,
    paper_ids       TEXT DEFAULT '[]',          -- JSON list
    centroid        TEXT DEFAULT '{}',          -- JSON
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS questions (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        TEXT DEFAULT '',
    paper_id        TEXT DEFAULT '',
    question        TEXT NOT NULL,
    answer          TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS feedback (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cycle_id        TEXT DEFAULT '',
    paper_id        TEXT DEFAULT '',
    source          TEXT DEFAULT '',
    content         TEXT DEFAULT '',
    created_at      TEXT DEFAULT (datetime('now'))
);
"""


def create_tables(db_path: str | Path) -> None:
    """Create all knowledge-store tables (idempotent).

    Parameters
    ----------
    db_path : str | Path
        Path to the SQLite database file. Parent directories are created
        automatically if they do not exist.
    """
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(_SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
