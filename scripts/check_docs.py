#!/usr/bin/env python3
"""Documentation-layout enforcer for Alpha Manager.

Checks two invariants before a commit is allowed:

1.  docs/ contains EXACTLY the five canonical files:
    PROJECT.md, PLAN.md, SURVEY.md, DISCUSSION.md, LOGS.md.
    No extras, none missing, no subdirectories. README.md lives at repo
    root, not in docs/.

2.  docs/LOGS.md is append-only. Every staged version of the file must
    begin with the full byte content of the HEAD version, optionally
    followed by more content. Insertions, deletions, and mid-file edits
    are all rejected.

Exit codes:
    0 — all invariants hold
    1 — at least one invariant violated (prints each violation)
    2 — internal error (e.g. git not available)

Usage:
    python3 scripts/check_docs.py              # check staged changes
    python3 scripts/check_docs.py --worktree   # check worktree vs HEAD
                                                  (no git staging needed)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

# ── Canonical layout ────────────────────────────────────────────────────────

REPO_ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = REPO_ROOT / "docs"
CANONICAL_DOC_FILES = frozenset(
    {"PROJECT.md", "PLAN.md", "SURVEY.md", "DISCUSSION.md", "LOGS.md"}
)
APPEND_ONLY_RELATIVE = "docs/LOGS.md"


# ── Helpers ─────────────────────────────────────────────────────────────────


def _run_git(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )


def _git_blob(revision: str, path: str) -> bytes | None:
    """Return the bytes of ``path`` at ``revision``, or None if it doesn't
    exist there yet (first commit creating the file)."""
    result = subprocess.run(
        ["git", "show", f"{revision}:{path}"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout


def _git_head_exists() -> bool:
    """Return True if HEAD resolves (repo has at least one commit)."""
    return _run_git(["rev-parse", "--verify", "HEAD"]).returncode == 0


# ── Rule 1: docs/ contents ──────────────────────────────────────────────────


def check_docs_layout() -> list[str]:
    """Return a list of human-readable violations; empty list means OK."""
    errors: list[str] = []

    if not DOCS_DIR.exists():
        return [f"docs/ directory missing at {DOCS_DIR}"]
    if not DOCS_DIR.is_dir():
        return [f"docs/ exists but is not a directory: {DOCS_DIR}"]

    # Gather everything directly inside docs/ (non-recursive — we do NOT
    # allow subdirectories).
    actual_entries = sorted(p.name for p in DOCS_DIR.iterdir())
    actual_files = {p.name for p in DOCS_DIR.iterdir() if p.is_file()}
    actual_dirs = [p.name for p in DOCS_DIR.iterdir() if p.is_dir()]

    if actual_dirs:
        errors.append(
            f"docs/ must be flat but contains subdirectories: "
            f"{sorted(actual_dirs)}"
        )

    missing = CANONICAL_DOC_FILES - actual_files
    extra = actual_files - CANONICAL_DOC_FILES
    if missing:
        errors.append(f"docs/ missing required files: {sorted(missing)}")
    if extra:
        errors.append(
            f"docs/ contains files outside the canonical set: "
            f"{sorted(extra)} (allowed: {sorted(CANONICAL_DOC_FILES)})"
        )

    return errors


# ── Rule 2: LOGS.md append-only ─────────────────────────────────────────────


def check_logs_append_only(source: str = "staged") -> list[str]:
    """Verify that docs/LOGS.md grows only at the end.

    ``source`` is 'staged' (compare HEAD → index) or 'worktree' (compare
    HEAD → working tree). For the initial commit creating LOGS.md there
    is nothing to compare against, so the check is vacuously satisfied.
    """
    errors: list[str] = []

    logs_path = REPO_ROOT / APPEND_ONLY_RELATIVE
    if not logs_path.exists():
        # If LOGS.md is missing entirely, Rule 1 already catches it.
        return errors

    if not _git_head_exists():
        # First commit ever; nothing to diff against.
        return errors

    head_bytes = _git_blob("HEAD", APPEND_ONLY_RELATIVE)
    if head_bytes is None:
        # LOGS.md is being added for the first time in this commit.
        return errors

    if source == "staged":
        # Compare against the blob that's about to be committed (index).
        staged = _run_git(["ls-files", "--stage", "--", APPEND_ONLY_RELATIVE])
        if staged.returncode != 0 or not staged.stdout.strip():
            # Not staged — read worktree instead so we still catch edits
            # that haven't been added.
            new_bytes = logs_path.read_bytes()
        else:
            # ls-files --stage output: "<mode> <sha> <stage>\t<path>"
            sha = staged.stdout.split()[1]
            show = subprocess.run(
                ["git", "cat-file", "blob", sha],
                cwd=str(REPO_ROOT),
                capture_output=True,
                check=False,
            )
            if show.returncode != 0:
                return [
                    f"git cat-file failed for staged {APPEND_ONLY_RELATIVE}: "
                    f"{show.stderr.decode(errors='replace')}"
                ]
            new_bytes = show.stdout
    elif source == "worktree":
        new_bytes = logs_path.read_bytes()
    else:
        return [f"unknown source {source!r}"]

    if not new_bytes.startswith(head_bytes):
        # Diagnose where the divergence starts.
        diverge = _first_diff_byte(head_bytes, new_bytes)
        errors.append(
            f"{APPEND_ONLY_RELATIVE} is append-only but its new content "
            f"does not start with the HEAD content.\n"
            f"  HEAD size:     {len(head_bytes)} bytes\n"
            f"  New size:      {len(new_bytes)} bytes\n"
            f"  First divergence at byte offset: {diverge}\n"
            f"  (Line ~{_byte_offset_to_line(head_bytes, diverge)})\n"
            f"  If you need to correct prior content, append a new "
            f"'Correction (<date>)' entry at the bottom instead."
        )
    return errors


def _first_diff_byte(a: bytes, b: bytes) -> int:
    limit = min(len(a), len(b))
    for i in range(limit):
        if a[i] != b[i]:
            return i
    return limit  # one is a prefix of the other


def _byte_offset_to_line(data: bytes, offset: int) -> int:
    return data[:offset].count(b"\n") + 1


# ── CLI ────────────────────────────────────────────────────────────────────


def main(argv: list[str]) -> int:
    source = "worktree" if "--worktree" in argv else "staged"

    all_errors: list[str] = []
    all_errors.extend(check_docs_layout())
    all_errors.extend(check_logs_append_only(source=source))

    if all_errors:
        print("docs/ layout check FAILED:", file=sys.stderr)
        for err in all_errors:
            print(f"  - {err}", file=sys.stderr)
        print(
            "\nTo bypass in an emergency, use `git commit --no-verify` "
            "(but please fix the issue in a follow-up).",
            file=sys.stderr,
        )
        return 1

    print("docs/ layout check OK")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv[1:]))
    except subprocess.SubprocessError as exc:
        print(f"check_docs.py: git error: {exc}", file=sys.stderr)
        sys.exit(2)
