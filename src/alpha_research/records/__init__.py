"""Typed-record JSONL store for project memory.

Provides a lightweight append-only persistence layer used by the
pipelines and skills to record evaluations, findings, reviews, etc.
"""

from alpha_research.records.jsonl import (
    SUPPORTED_RECORD_TYPES,
    append_record,
    count_records,
    read_records,
)

__all__ = [
    "SUPPORTED_RECORD_TYPES",
    "append_record",
    "read_records",
    "count_records",
]
