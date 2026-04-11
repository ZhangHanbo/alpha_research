"""Report-emitting tests for ``alpha_research.records.jsonl``.

Complements the existing ``test_records.py`` by routing the critical
behaviours through the ``report`` fixture so a human-readable record
lands at ``tests/reports/test_records_jsonl.md``.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alpha_research.records.jsonl import (
    SUPPORTED_RECORD_TYPES,
    append_record,
    count_records,
    log_action,
    read_records,
)


def test_append_and_read_roundtrip(tmp_path: Path, report) -> None:
    rid = append_record(tmp_path, "evaluation", {"paper": "X", "score": 7})
    records = read_records(tmp_path, "evaluation")

    passed = (
        len(records) == 1
        and records[0]["paper"] == "X"
        and records[0]["score"] == 7
        and records[0]["id"] == rid
        and rid.startswith("eval_")
        and "created_at" in records[0]
    )
    report.record(
        name="append_record → read_records round-trip",
        purpose="Appending a record then reading it back should return the same payload plus auto-stamped id and created_at.",
        inputs={"record_type": "evaluation", "data": {"paper": "X", "score": 7}},
        expected={"count": 1, "paper": "X", "score": 7, "id_prefix": "eval_"},
        actual={"count": len(records), "paper": records[0]["paper"], "score": records[0]["score"], "id": records[0]["id"]},
        passed=passed,
        conclusion="This is the canonical write-read path for every skill that persists to JSONL.",
    )
    assert passed


def test_filter_by_nested_dotted_path(tmp_path: Path, report) -> None:
    append_record(tmp_path, "evaluation", {"rubric_scores": {"B": {"1": {"score": 3}}}, "name": "p1"})
    append_record(tmp_path, "evaluation", {"rubric_scores": {"B": {"1": {"score": 5}}}, "name": "p2"})

    matches = read_records(tmp_path, "evaluation", filters={"rubric_scores.B.1.score": 5})
    passed = len(matches) == 1 and matches[0]["name"] == "p2"
    report.record(
        name="nested dotted-path filter finds matching records",
        purpose="Filters support dotted paths so callers can query rubric scores directly.",
        inputs={"filter": "rubric_scores.B.1.score == 5"},
        expected={"count": 1, "name": "p2"},
        actual={"count": len(matches), "name": matches[0]["name"] if matches else None},
        passed=passed,
        conclusion="Dotted filters are how downstream skills query deeply nested rubric records.",
    )
    assert passed


def test_count_records_matches_read(tmp_path: Path, report) -> None:
    for sev in ["fatal", "serious", "fatal", "minor", "fatal"]:
        append_record(tmp_path, "finding", {"severity": sev})

    cnt = count_records(tmp_path, "finding", filters={"severity": "fatal"})
    recs = read_records(tmp_path, "finding", filters={"severity": "fatal"})

    passed = cnt == len(recs) == 3
    report.record(
        name="count_records agrees with read_records",
        purpose="count_records should match the length of the equivalent read_records output.",
        inputs={"records": [{"severity": s} for s in ["fatal", "serious", "fatal", "minor", "fatal"]], "filter": {"severity": "fatal"}},
        expected={"count": 3},
        actual={"count": cnt, "read_length": len(recs)},
        passed=passed,
        conclusion="Disagreement between count and read would signal a filter-logic bug; staying in sync is load-bearing.",
    )
    assert passed


def test_unsupported_record_type_raises(tmp_path: Path, report) -> None:
    raised = False
    try:
        append_record(tmp_path, "not_a_type", {"x": 1})
    except ValueError:
        raised = True
    report.record(
        name="unsupported record_type raises ValueError",
        purpose="append_record must reject record types not in SUPPORTED_RECORD_TYPES.",
        inputs={"record_type": "not_a_type"},
        expected={"raises": True},
        actual={"raises": raised},
        passed=raised,
        conclusion="Guard protects the JSONL store schema so records remain queryable.",
    )
    assert raised


def test_malformed_line_is_skipped(tmp_path: Path, report, caplog) -> None:
    append_record(tmp_path, "review", {"ok": True})
    path = tmp_path / "review.jsonl"
    with path.open("a", encoding="utf-8") as fp:
        fp.write("not json at all\n")
    append_record(tmp_path, "review", {"ok": False})

    with caplog.at_level("WARNING"):
        recs = read_records(tmp_path, "review")

    passed = len(recs) == 2 and any("Skipping malformed" in r.message for r in caplog.records)
    report.record(
        name="malformed JSONL line is skipped with a warning",
        purpose="Corrupt lines should not halt reading — they should be skipped and logged.",
        inputs={"inject": "not json at all"},
        expected={"records": 2, "warning_logged": True},
        actual={
            "records": len(recs),
            "warning_logged": any("Skipping malformed" in r.message for r in caplog.records),
        },
        passed=passed,
        conclusion="Resilience matters because JSONL files are edited by humans and crashed processes.",
    )
    assert passed


def test_log_action_writes_provenance(tmp_path: Path, report) -> None:
    pid = log_action(
        tmp_path,
        action_type="skill",
        action_name="paper-evaluate",
        project_stage="formalization",
        inputs=["project.md"],
        outputs=["evaluation.jsonl"],
        parent_ids=["root"],
        summary="evaluated one paper",
    )

    recs = read_records(tmp_path, "provenance")
    passed = (
        len(recs) == 1
        and recs[0]["id"] == pid
        and recs[0]["action_name"] == "paper-evaluate"
        and recs[0]["project_stage"] == "formalization"
        and recs[0]["parent_ids"] == ["root"]
    )
    report.record(
        name="log_action persists provenance correctly",
        purpose="log_action is the canonical API every skill/pipeline uses to record its run.",
        inputs={
            "action_type": "skill",
            "action_name": "paper-evaluate",
            "project_stage": "formalization",
            "parent_ids": ["root"],
        },
        expected={"records": 1, "action_name": "paper-evaluate", "parent_ids": ["root"]},
        actual={
            "records": len(recs),
            "action_name": recs[0]["action_name"] if recs else None,
            "parent_ids": recs[0]["parent_ids"] if recs else None,
        },
        passed=passed,
        conclusion="Provenance lineage is the audit trail for every research action.",
    )
    assert passed


def test_supported_record_types_frozen(report) -> None:
    must_have = {"evaluation", "finding", "review", "frontier", "provenance", "method_survey"}
    passed = must_have.issubset(SUPPORTED_RECORD_TYPES)
    report.record(
        name="SUPPORTED_RECORD_TYPES contains the canonical 6+",
        purpose="Regression guard: the core record types must not be removed.",
        inputs={},
        expected={"required_subset": sorted(must_have)},
        actual={"present": sorted(SUPPORTED_RECORD_TYPES)},
        passed=passed,
        conclusion="Removing one of these types would silently break historical JSONL reads in active projects.",
    )
    assert passed
