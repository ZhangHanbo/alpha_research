"""Cross-iteration finding tracker.

Tracks findings by ``id`` across review iterations, monitors severity
monotonicity, and computes resolution histories.

Source: review_plan.md §2.4, §3.2
"""

from __future__ import annotations

from alpha_research.metrics.convergence import compute_finding_resolution_rate
from alpha_research.models.review import (
    Review,
    RevisionResponse,
    Severity,
)


# Severity ordering for monotonicity checks
_SEVERITY_RANK: dict[Severity, int] = {
    Severity.FATAL: 3,
    Severity.SERIOUS: 2,
    Severity.MINOR: 1,
}


class FindingTracker:
    """Track findings across review iterations.

    Call :meth:`track` after each review/response pair. Use :meth:`get_summary`
    to inspect finding statuses and :meth:`get_resolution_history` for
    per-iteration resolution rates.
    """

    def __init__(self) -> None:
        # Each entry: (review, optional response)
        self._iterations: list[tuple[Review, RevisionResponse | None]] = []

    def track(
        self,
        review: Review,
        response: RevisionResponse | None = None,
    ) -> None:
        """Record a review and its optional revision response."""
        self._iterations.append((review, response))

    def get_summary(self) -> dict[str, str]:
        """Summarize each finding's status across all tracked iterations.

        Returns a dict mapping finding ``id`` to one of:
        ``"addressed"``, ``"deferred"``, ``"disputed"``, ``"persistent"``, ``"new"``.

        A finding is "persistent" if it appeared in multiple reviews and was
        never addressed, deferred, or disputed.
        """
        # Collect all finding IDs across all reviews
        finding_first_seen: dict[str, int] = {}
        finding_last_seen: dict[str, int] = {}

        for idx, (review, _) in enumerate(self._iterations):
            for f in review.all_findings:
                if f.id:
                    if f.id not in finding_first_seen:
                        finding_first_seen[f.id] = idx
                    finding_last_seen[f.id] = idx

        # Collect response actions
        addressed_ids: set[str] = set()
        deferred_ids: set[str] = set()
        disputed_ids: set[str] = set()

        for _, response in self._iterations:
            if response is None:
                continue
            for fr in response.addressed:
                addressed_ids.add(fr.finding_id)
            for fd in response.deferred:
                deferred_ids.add(fd.finding_id)
            for fd in response.disputed:
                disputed_ids.add(fd.finding_id)

        # Build summary
        all_ids = set(finding_first_seen.keys())
        summary: dict[str, str] = {}

        for fid in all_ids:
            if fid in addressed_ids:
                summary[fid] = "addressed"
            elif fid in deferred_ids:
                summary[fid] = "deferred"
            elif fid in disputed_ids:
                summary[fid] = "disputed"
            elif finding_first_seen[fid] != finding_last_seen[fid]:
                # Appeared in multiple iterations without any response action
                summary[fid] = "persistent"
            else:
                summary[fid] = "new"

        return summary

    def check_monotonic_severity(
        self,
        current: Review,
        previous: Review,
    ) -> list[str]:
        """Return finding IDs that were downgraded without justification.

        A downgrade is when a finding's severity decreased between
        *previous* and *current* (e.g. serious → minor) without
        the finding having been addressed in a revision response.
        """
        prev_map: dict[str, Severity] = {
            f.id: f.severity for f in previous.all_findings if f.id
        }
        curr_map: dict[str, Severity] = {
            f.id: f.severity for f in current.all_findings if f.id
        }

        # Collect addressed finding IDs from all tracked responses
        addressed_ids: set[str] = set()
        for _, response in self._iterations:
            if response is not None:
                for fr in response.addressed:
                    addressed_ids.add(fr.finding_id)

        downgrades: list[str] = []
        for fid, prev_sev in prev_map.items():
            if fid not in curr_map:
                continue
            curr_sev = curr_map[fid]
            if _SEVERITY_RANK[curr_sev] < _SEVERITY_RANK[prev_sev]:
                if fid not in addressed_ids:
                    downgrades.append(fid)

        return downgrades

    def get_resolution_history(self) -> list[float]:
        """Return resolution rates for each iteration that has a response.

        An iteration without a response is skipped (no rate computed).
        """
        rates: list[float] = []
        for review, response in self._iterations:
            if response is not None:
                rate = compute_finding_resolution_rate(review, response)
                rates.append(rate)
        return rates
