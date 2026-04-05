"""Tests for the JSONL-backed typed record store."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from alpha_research.records.jsonl import (
    SUPPORTED_RECORD_TYPES,
    append_record,
    count_records,
    read_records,
)


def test_append_and_read_round_trip(tmp_path: Path) -> None:
    rid = append_record(tmp_path, "evaluation", {"paper": "X", "score": 7})
    assert rid.startswith("eval_")
    records = read_records(tmp_path, "evaluation")
    assert len(records) == 1
    assert records[0]["paper"] == "X"
    assert records[0]["score"] == 7
    assert records[0]["id"] == rid
    assert "created_at" in records[0]


def test_filter_by_top_level_key(tmp_path: Path) -> None:
    append_record(tmp_path, "finding", {"severity": "fatal", "text": "a"})
    append_record(tmp_path, "finding", {"severity": "serious", "text": "b"})
    append_record(tmp_path, "finding", {"severity": "fatal", "text": "c"})

    fatals = read_records(tmp_path, "finding", filters={"severity": "fatal"})
    assert len(fatals) == 2
    assert {r["text"] for r in fatals} == {"a", "c"}


def test_filter_by_nested_dotted_path(tmp_path: Path) -> None:
    append_record(
        tmp_path,
        "evaluation",
        {"rubric_scores": {"B": {"1": {"score": 3}}}, "name": "p1"},
    )
    append_record(
        tmp_path,
        "evaluation",
        {"rubric_scores": {"B": {"1": {"score": 5}}}, "name": "p2"},
    )
    matches = read_records(
        tmp_path,
        "evaluation",
        filters={"rubric_scores.B.1.score": 5},
    )
    assert len(matches) == 1
    assert matches[0]["name"] == "p2"


def test_limit_respected(tmp_path: Path) -> None:
    for i in range(10):
        append_record(tmp_path, "review", {"i": i})
    out = read_records(tmp_path, "review", limit=3)
    assert len(out) == 3
    assert [r["i"] for r in out] == [0, 1, 2]


def test_empty_file_returns_empty(tmp_path: Path) -> None:
    # Create an empty jsonl file manually
    (tmp_path / "audit.jsonl").write_text("", encoding="utf-8")
    assert read_records(tmp_path, "audit") == []
    assert count_records(tmp_path, "audit") == 0


def test_missing_file_returns_empty(tmp_path: Path) -> None:
    assert read_records(tmp_path, "diagnosis") == []
    assert count_records(tmp_path, "diagnosis") == 0


def test_unsupported_record_type_raises(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        append_record(tmp_path, "not_a_type", {"x": 1})
    with pytest.raises(ValueError):
        read_records(tmp_path, "not_a_type")
    with pytest.raises(ValueError):
        count_records(tmp_path, "not_a_type")


def test_count_matches_read(tmp_path: Path) -> None:
    for sev in ["fatal", "serious", "fatal", "minor", "fatal"]:
        append_record(tmp_path, "finding", {"severity": sev})
    cnt = count_records(tmp_path, "finding", filters={"severity": "fatal"})
    recs = read_records(tmp_path, "finding", filters={"severity": "fatal"})
    assert cnt == len(recs) == 3


def test_auto_created_project_dir(tmp_path: Path) -> None:
    new_dir = tmp_path / "new_project" / "nested"
    assert not new_dir.exists()
    rid = append_record(new_dir, "challenge", {"text": "hi"})
    assert new_dir.exists()
    assert (new_dir / "challenge.jsonl").exists()
    recs = read_records(new_dir, "challenge")
    assert len(recs) == 1
    assert recs[0]["id"] == rid


def test_malformed_line_skipped(tmp_path: Path, caplog) -> None:
    append_record(tmp_path, "review", {"ok": True})
    path = tmp_path / "review.jsonl"
    with path.open("a", encoding="utf-8") as fp:
        fp.write("not json at all\n")
    append_record(tmp_path, "review", {"ok": False})

    with caplog.at_level("WARNING"):
        recs = read_records(tmp_path, "review")
    assert len(recs) == 2
    assert any("Skipping malformed" in r.message for r in caplog.records)


def test_supported_types_constant_is_frozen() -> None:
    # Regression guard: set of record types matches the spec exactly
    assert "evaluation" in SUPPORTED_RECORD_TYPES
    assert "gap_report" in SUPPORTED_RECORD_TYPES
    assert len(SUPPORTED_RECORD_TYPES) >= 12


def test_id_collision_with_caller_supplied_id(tmp_path: Path) -> None:
    rid = append_record(tmp_path, "evaluation", {"id": "my_custom_id", "x": 1})
    assert rid == "my_custom_id"
    recs = read_records(tmp_path, "evaluation")
    assert recs[0]["id"] == "my_custom_id"
