"""JSONL-backed typed-record store.

Each record type lives in its own JSONL file under a project directory:
``{project_dir}/{record_type}.jsonl``. Records are append-only, newline-
delimited JSON objects, and each record gains an ``id`` and
``created_at`` timestamp if not already present.

This module is intentionally small and dependency-free so it can be
invoked from skill bash snippets via ``python -c``.
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


SUPPORTED_RECORD_TYPES: set[str] = {
    "evaluation",
    "finding",
    "review",
    "frontier",
    "significance_screen",
    "formalization_check",
    "diagnosis",
    "challenge",
    "method_survey",
    "audit",
    "concurrent_work",
    "gap_report",
}


def _validate_type(record_type: str) -> None:
    if record_type not in SUPPORTED_RECORD_TYPES:
        raise ValueError(
            f"Unsupported record_type {record_type!r}. "
            f"Supported types: {sorted(SUPPORTED_RECORD_TYPES)}"
        )


def _jsonl_path(project_dir: Path, record_type: str) -> Path:
    return Path(project_dir) / f"{record_type}.jsonl"


def _get_nested(obj: Any, dotted_path: str) -> Any:
    """Return the value at ``dotted_path`` inside ``obj`` or ``None``."""
    cur: Any = obj
    for part in dotted_path.split("."):
        if isinstance(cur, dict) and part in cur:
            cur = cur[part]
        else:
            return None
    return cur


def _matches(record: dict, filters: dict | None) -> bool:
    if not filters:
        return True
    for key, expected in filters.items():
        actual = _get_nested(record, key) if "." in key else record.get(key)
        if actual != expected:
            return False
    return True


def _iter_records(path: Path):
    """Yield parsed dict records from a JSONL file, skipping malformed lines."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as fp:
        for lineno, raw in enumerate(fp, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                logger.warning(
                    "Skipping malformed JSONL line %d in %s: %s",
                    lineno,
                    path,
                    exc,
                )
                continue
            if isinstance(obj, dict):
                yield obj
            else:
                logger.warning(
                    "Skipping non-object JSONL record on line %d in %s",
                    lineno,
                    path,
                )


def append_record(project_dir: Path, record_type: str, data: dict) -> str:
    """Append ``data`` as a new record of ``record_type``.

    Parameters
    ----------
    project_dir : Path
        Directory holding this project's JSONL stores. Created if missing.
    record_type : str
        One of :data:`SUPPORTED_RECORD_TYPES`.
    data : dict
        Record payload. An ``id`` and ``created_at`` field are added if
        not already present.

    Returns
    -------
    str
        The record id (either supplied in ``data`` or auto-generated).
    """
    _validate_type(record_type)

    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)

    record = dict(data)  # shallow copy — don't mutate caller's dict
    if "id" not in record or not record["id"]:
        record["id"] = f"{record_type[:4]}_{uuid.uuid4().hex[:10]}"
    if "created_at" not in record:
        record["created_at"] = time.time()

    path = _jsonl_path(project_dir, record_type)
    line = json.dumps(record, ensure_ascii=False, default=str)
    # 'a' mode append of a single line is atomic on POSIX for small writes.
    with path.open("a", encoding="utf-8") as fp:
        fp.write(line + "\n")

    return record["id"]


def read_records(
    project_dir: Path,
    record_type: str,
    filters: dict | None = None,
    limit: int | None = None,
) -> list[dict]:
    """Read records matching ``filters``.

    Filter values are matched exactly against the corresponding field.
    Nested fields may be accessed with dotted paths, e.g.
    ``"rubric_scores.B.1.score"``.

    Missing files return an empty list.
    """
    _validate_type(record_type)
    path = _jsonl_path(Path(project_dir), record_type)

    results: list[dict] = []
    for record in _iter_records(path):
        if _matches(record, filters):
            results.append(record)
            if limit is not None and len(results) >= limit:
                break
    return results


def count_records(
    project_dir: Path,
    record_type: str,
    filters: dict | None = None,
) -> int:
    """Count records matching ``filters`` without materializing them all."""
    _validate_type(record_type)
    path = _jsonl_path(Path(project_dir), record_type)

    count = 0
    for record in _iter_records(path):
        if _matches(record, filters):
            count += 1
    return count
