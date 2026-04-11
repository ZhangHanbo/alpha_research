"""Test-report infrastructure.

Every test module that wants to produce a human-readable report uses the
``report`` fixture from ``conftest.py`` (which wraps :class:`ReportWriter`)
and calls ``report.record(...)`` for each test case. When the module
finishes, the fixture writes a markdown file to ``tests/reports/<module>.md``
documenting inputs, expected outputs, actual outputs, and conclusions.

Usage::

    def test_example(report):
        input_data = {"x": 1}
        expected = 2
        actual = double(input_data["x"])
        report.record(
            name="doubles positive integer",
            purpose="verify double(1) == 2",
            inputs=input_data,
            expected=expected,
            actual=actual,
            passed=(actual == expected),
            conclusion="basic doubling works",
        )
        assert actual == expected

The fixture is module-scoped, so every test function in a module shares
a single report. The report is saved when the module teardown runs.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


REPORTS_DIR = Path(__file__).parent / "reports"


@dataclass
class TestRecord:
    """One row in a module report."""

    name: str
    purpose: str
    inputs: Any
    expected: Any
    actual: Any
    passed: bool
    conclusion: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))


class ReportWriter:
    """Accumulates test records and writes a markdown report when done.

    One instance per test module (via the module-scoped ``report`` fixture
    in ``conftest.py``). Safe to share across tests within the module.
    """

    def __init__(self, module_name: str) -> None:
        self.module_name = module_name
        self.records: list[TestRecord] = []
        self.started_at = datetime.now().isoformat(timespec="seconds")

    def record(
        self,
        name: str,
        purpose: str,
        inputs: Any,
        expected: Any,
        actual: Any,
        passed: bool,
        conclusion: str,
    ) -> None:
        """Append one test record to the report."""
        self.records.append(
            TestRecord(
                name=name,
                purpose=purpose,
                inputs=inputs,
                expected=expected,
                actual=actual,
                passed=passed,
                conclusion=conclusion,
            )
        )

    def save(self) -> Path:
        """Write the markdown report. Returns the file path."""
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        path = REPORTS_DIR / f"{self.module_name}.md"
        path.write_text(self._render())
        return path

    # -----------------------------------------------------------------
    # Rendering
    # -----------------------------------------------------------------

    def _render(self) -> str:
        total = len(self.records)
        passed = sum(1 for r in self.records if r.passed)
        failed = total - passed

        lines: list[str] = []
        lines.append(f"# Test Report — `{self.module_name}`")
        lines.append("")
        lines.append(f"**Started at**: {self.started_at}")
        lines.append(f"**Saved at**: {datetime.now().isoformat(timespec='seconds')}")
        lines.append(f"**Tests**: {total} total — **{passed} passed**, **{failed} failed**")
        lines.append("")

        if failed == 0 and total > 0:
            lines.append("> ✅ **All tests passed.**")
        elif total == 0:
            lines.append("> ⚠ **No records were logged for this module.**")
        else:
            lines.append(f"> ❌ **{failed} test(s) failed** — see details below.")
        lines.append("")
        lines.append("---")
        lines.append("")

        for idx, rec in enumerate(self.records, start=1):
            status = "✅ PASS" if rec.passed else "❌ FAIL"
            lines.append(f"## Case {idx}: `{rec.name}`")
            lines.append("")
            lines.append(f"**Result**: {status}")
            lines.append(f"**Purpose**: {rec.purpose}")
            lines.append("")
            lines.append("**Inputs**:")
            lines.append("```")
            lines.append(self._pretty(rec.inputs))
            lines.append("```")
            lines.append("")
            lines.append("**Expected**:")
            lines.append("```")
            lines.append(self._pretty(rec.expected))
            lines.append("```")
            lines.append("")
            lines.append("**Actual**:")
            lines.append("```")
            lines.append(self._pretty(rec.actual))
            lines.append("```")
            lines.append("")
            lines.append(f"**Conclusion**: {rec.conclusion}")
            lines.append("")
            lines.append("---")
            lines.append("")

        lines.append("## Summary")
        lines.append("")
        lines.append(f"- **Total tests**: {total}")
        lines.append(f"- **Passed**: {passed}")
        lines.append(f"- **Failed**: {failed}")
        if total > 0:
            lines.append(f"- **Pass rate**: {passed / total * 100:.1f}%")
        lines.append("")

        return "\n".join(lines)

    @staticmethod
    def _pretty(value: Any) -> str:
        """Render a Python value as a readable string for the report."""
        if value is None:
            return "None"
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, indent=2, default=str, sort_keys=False)
        except (TypeError, ValueError):
            return repr(value)
