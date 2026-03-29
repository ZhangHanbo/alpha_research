"""Pure-Python review quality metric computation.

Implements the programmatic checks from review_plan.md 1.8:
  - Actionability, grounding, falsifiability (fraction-based)
  - Vague-critique detection (regex heuristic)
  - Steel-man sentence counting
  - Anti-pattern detection
  - Full evaluate_review pipeline

Source: review_plan.md 1.8, review_guideline.md 5.4
"""

from __future__ import annotations

import re

from alpha_research.models.review import (
    AntiPatternCheck,
    Finding,
    MetricCheck,
    Review,
    ReviewQualityMetrics,
    ReviewQualityReport,
    Severity,
    Verdict,
)

# ---------------------------------------------------------------------------
# Default thresholds
# ---------------------------------------------------------------------------

DEFAULT_THRESHOLDS: dict[str, float | int] = {
    "actionability": 0.80,
    "grounding": 0.90,
    "vague_critiques": 0,
    "falsifiability": 0.70,
    "steel_man_sentences": 3,
}

# ---------------------------------------------------------------------------
# Vague-phrase detection helpers
# ---------------------------------------------------------------------------

# Core vague phrases that, on their own, constitute a vague critique.
_VAGUE_PHRASES: list[str] = [
    "weak",
    "limited",
    "insufficient",
    "poor",
    "not convincing",
    "unconvincing",
    "inadequate",
    "not enough",
    "lacks novelty",
    "limited novelty",
    "not novel",
    "lacks rigor",
    "not rigorous",
]

# Evidence markers that rescue an otherwise-vague statement.
_EVIDENCE_PATTERN = re.compile(
    r"""
    (?:
        [Ss]ection\s+\d          # Section 3
      | [Ff]igure\s+\d           # Figure 2
      | [Ff]ig\.?\s*\d           # Fig 2, Fig. 2
      | [Tt]able\s+\d            # Table 1
      | [Ee]quation\s+\d        # Equation 4
      | [Ee]q\.?\s*\d            # Eq 4, Eq. 4
      | \(\d{4}\)                # (2023) — citation year
      | \d+\s*(?:trials?|runs?|samples?|episodes?)   # 5 trials
      | \d+\.\d+                 # concrete number like 0.85
      | (?:Appendix|App\.)\s+[A-Z]  # Appendix A
      | [A-Z][a-z]+\s+(?:et\s+al\.?|&)\s   # Author et al.
      | [A-Z][a-z]+\s+\d{4}     # Smith 2023
    )
    """,
    re.VERBOSE,
)


def _is_vague(text: str) -> bool:
    """Return True if *text* is a vague critique with no specific evidence."""
    lowered = text.lower()
    has_vague = any(phrase in lowered for phrase in _VAGUE_PHRASES)
    if not has_vague:
        return False
    # If the text also contains specific evidence, it is NOT vague.
    if _EVIDENCE_PATTERN.search(text):
        return False
    return True


# ---------------------------------------------------------------------------
# Individual metric functions
# ---------------------------------------------------------------------------

def compute_actionability(review: Review) -> float:
    """Fraction of all findings with non-empty ``what_would_fix``."""
    findings = review.all_findings
    if not findings:
        return 1.0
    actionable = sum(1 for f in findings if f.what_would_fix.strip())
    return actionable / len(findings)


def compute_grounding(review: Review) -> float:
    """Fraction of serious+fatal findings with non-empty ``grounding``."""
    serious = [
        f for f in review.all_findings
        if f.severity in (Severity.FATAL, Severity.SERIOUS)
    ]
    if not serious:
        return 1.0
    grounded = sum(1 for f in serious if f.grounding.strip())
    return grounded / len(serious)


def compute_falsifiability(review: Review) -> float:
    """Fraction of serious+fatal findings with non-empty ``falsification``."""
    serious = [
        f for f in review.all_findings
        if f.severity in (Severity.FATAL, Severity.SERIOUS)
    ]
    if not serious:
        return 1.0
    falsifiable = sum(1 for f in serious if f.falsification.strip())
    return falsifiable / len(serious)


def count_vague_critiques(review: Review) -> int:
    """Count findings whose ``what_is_wrong`` contains ONLY vague phrasing."""
    return sum(1 for f in review.all_findings if _is_vague(f.what_is_wrong))


def check_steel_man(review: Review) -> int:
    """Count sentences in the ``steel_man`` field (split by '. ')."""
    text = review.steel_man.strip()
    if not text:
        return 0
    # Split on '. ' and also count the last sentence (which may not end with '. ')
    sentences = [s.strip() for s in text.split(". ") if s.strip()]
    return len(sentences)


def compute_all_metrics(review: Review) -> ReviewQualityMetrics:
    """Compute all quality metrics for a review."""
    return ReviewQualityMetrics(
        actionability=compute_actionability(review),
        grounding=compute_grounding(review),
        specificity_violations=count_vague_critiques(review),
        falsifiability=compute_falsifiability(review),
        steel_man_sentences=check_steel_man(review),
        all_classified=True,  # Pydantic enforces severity on Finding
    )


# ---------------------------------------------------------------------------
# Anti-pattern detection
# ---------------------------------------------------------------------------

def check_anti_patterns(
    review: Review,
    review_history: list[Review] | None = None,
) -> list[AntiPatternCheck]:
    """Detect anti-patterns in *review*, optionally using *review_history*."""
    checks: list[AntiPatternCheck] = []
    history = review_history or []

    # 1. Dimension averaging — verdict doesn't match finding severity
    checks.append(_check_dimension_averaging(review))

    # 2. Severity regression — previous fatal/serious downgraded
    checks.append(_check_severity_regression(review, history))

    # 3. Declining specificity — grounding length decreasing
    checks.append(_check_declining_specificity(review, history))

    # 4. False balance — equal strengths & weaknesses when unwarranted
    checks.append(_check_false_balance(review))

    # 5. Novelty fetishism — rejection solely on novelty
    checks.append(_check_novelty_fetishism(review))

    # 6. Punishing honest limitations
    checks.append(_check_punishing_limitations(review))

    return checks


def _check_dimension_averaging(review: Review) -> AntiPatternCheck:
    """Detect verdict that doesn't match severity distribution."""
    serious_or_fatal = len(review.fatal_flaws) + len(review.serious_weaknesses)
    accepting = review.verdict in (Verdict.ACCEPT, Verdict.WEAK_ACCEPT)

    if serious_or_fatal >= 2 and accepting:
        return AntiPatternCheck(
            pattern="dimension_averaging",
            detected=True,
            evidence=(
                f"Verdict is {review.verdict.value} despite "
                f"{len(review.fatal_flaws)} fatal and "
                f"{len(review.serious_weaknesses)} serious findings."
            ),
        )
    return AntiPatternCheck(pattern="dimension_averaging", detected=False)


def _check_severity_regression(
    review: Review,
    history: list[Review],
) -> AntiPatternCheck:
    """Detect downgrades of previous fatal/serious findings."""
    if not history:
        return AntiPatternCheck(pattern="severity_regression", detected=False)

    prev = history[-1]
    prev_severe: dict[str, Severity] = {}
    for f in prev.all_findings:
        if f.id and f.severity in (Severity.FATAL, Severity.SERIOUS):
            prev_severe[f.id] = f.severity

    if not prev_severe:
        return AntiPatternCheck(pattern="severity_regression", detected=False)

    current_map: dict[str, Severity] = {
        f.id: f.severity for f in review.all_findings if f.id
    }

    downgraded: list[str] = []
    for fid, prev_sev in prev_severe.items():
        cur_sev = current_map.get(fid)
        if cur_sev is None:
            continue  # finding disappeared — separate concern
        severity_rank = {Severity.FATAL: 3, Severity.SERIOUS: 2, Severity.MINOR: 1}
        if severity_rank[cur_sev] < severity_rank[prev_sev]:
            downgraded.append(fid)

    if downgraded:
        return AntiPatternCheck(
            pattern="severity_regression",
            detected=True,
            evidence=f"Findings downgraded without justification: {downgraded}",
        )
    return AntiPatternCheck(pattern="severity_regression", detected=False)


def _check_declining_specificity(
    review: Review,
    history: list[Review],
) -> AntiPatternCheck:
    """Detect decreasing average grounding length across reviews."""
    if not history:
        return AntiPatternCheck(pattern="declining_specificity", detected=False)

    def _avg_grounding_len(r: Review) -> float:
        serious = [
            f for f in r.all_findings
            if f.severity in (Severity.FATAL, Severity.SERIOUS)
        ]
        if not serious:
            return 0.0
        return sum(len(f.grounding) for f in serious) / len(serious)

    all_reviews = history + [review]
    if len(all_reviews) < 2:
        return AntiPatternCheck(pattern="declining_specificity", detected=False)

    lengths = [_avg_grounding_len(r) for r in all_reviews]

    # Check if strictly decreasing for the last 2+ reviews
    declining = all(lengths[i] > lengths[i + 1] for i in range(len(lengths) - 1))

    if declining and len(lengths) >= 2:
        return AntiPatternCheck(
            pattern="declining_specificity",
            detected=True,
            evidence=(
                f"Average grounding length declining: "
                f"{[round(l, 1) for l in lengths]}"
            ),
        )
    return AntiPatternCheck(pattern="declining_specificity", detected=False)


def _check_false_balance(review: Review) -> AntiPatternCheck:
    """Detect forced equal strengths/weaknesses when clearly unbalanced."""
    # Heuristic: if all findings are serious/fatal but minor_issues is padded
    # to match, or vice versa.
    serious_count = len(review.fatal_flaws) + len(review.serious_weaknesses)
    minor_count = len(review.minor_issues)

    # Only flag when there are findings and they are suspiciously balanced
    if serious_count > 0 and minor_count > 0 and serious_count == minor_count:
        # Check if verdict is inconsistent — a balanced review with reject
        # or accept might indicate forced balance.
        if serious_count >= 3:
            return AntiPatternCheck(
                pattern="false_balance",
                detected=True,
                evidence=(
                    f"Review has exactly {serious_count} serious/fatal and "
                    f"{minor_count} minor findings, which may indicate forced balance."
                ),
            )
    return AntiPatternCheck(pattern="false_balance", detected=False)


def _check_novelty_fetishism(review: Review) -> AntiPatternCheck:
    """Detect rejection based solely on novelty concerns."""
    if review.verdict not in (Verdict.REJECT, Verdict.WEAK_REJECT):
        return AntiPatternCheck(pattern="novelty_fetishism", detected=False)

    novelty_keywords = ["novel", "novelty", "incremental", "originality"]
    all_findings = review.all_findings

    if not all_findings:
        return AntiPatternCheck(pattern="novelty_fetishism", detected=False)

    novelty_findings = []
    for f in all_findings:
        text = (f.what_is_wrong + " " + f.why_it_matters).lower()
        if any(kw in text for kw in novelty_keywords):
            novelty_findings.append(f)

    non_novelty = len(all_findings) - len(novelty_findings)

    # If all or almost all serious findings are novelty-based
    if len(novelty_findings) > 0 and non_novelty == 0:
        return AntiPatternCheck(
            pattern="novelty_fetishism",
            detected=True,
            evidence=(
                f"All {len(novelty_findings)} findings concern novelty. "
                f"Rejection appears solely novelty-based."
            ),
        )
    return AntiPatternCheck(pattern="novelty_fetishism", detected=False)


def _check_punishing_limitations(review: Review) -> AntiPatternCheck:
    """Detect findings that penalize the paper for reporting limitations."""
    limitation_keywords = [
        "limitation", "limitations", "honestly reported",
        "self-reported", "authors acknowledge",
    ]

    for f in review.all_findings:
        text = (f.what_is_wrong + " " + f.why_it_matters).lower()
        if any(kw in text for kw in limitation_keywords):
            if f.severity in (Severity.FATAL, Severity.SERIOUS):
                return AntiPatternCheck(
                    pattern="punishing_honest_limitations",
                    detected=True,
                    evidence=(
                        f"Finding '{f.id or f.what_is_wrong[:50]}' penalizes "
                        f"reported limitations as {f.severity.value}."
                    ),
                )
    return AntiPatternCheck(pattern="punishing_honest_limitations", detected=False)


# ---------------------------------------------------------------------------
# Full evaluation
# ---------------------------------------------------------------------------

def evaluate_review(
    review: Review,
    review_history: list[Review] | None = None,
    thresholds: dict | None = None,
) -> ReviewQualityReport:
    """Run all metric checks and anti-pattern detection.

    Returns a :class:`ReviewQualityReport` with pass/fail per metric.
    """
    t = {**DEFAULT_THRESHOLDS, **(thresholds or {})}

    metrics = compute_all_metrics(review)
    anti_patterns = check_anti_patterns(review, review_history)

    checks: list[MetricCheck] = []

    # Actionability
    act_pass = metrics.actionability >= t["actionability"]
    checks.append(MetricCheck(
        name="actionability",
        passed=act_pass,
        actual=metrics.actionability,
        threshold=t["actionability"],
        message="" if act_pass else (
            f"Actionability {metrics.actionability:.2f} < {t['actionability']}"
        ),
    ))

    # Grounding
    grd_pass = metrics.grounding >= t["grounding"]
    checks.append(MetricCheck(
        name="grounding",
        passed=grd_pass,
        actual=metrics.grounding,
        threshold=t["grounding"],
        message="" if grd_pass else (
            f"Grounding {metrics.grounding:.2f} < {t['grounding']}"
        ),
    ))

    # Specificity (vague critiques)
    spec_pass = metrics.specificity_violations <= t["vague_critiques"]
    checks.append(MetricCheck(
        name="specificity",
        passed=spec_pass,
        actual=metrics.specificity_violations,
        threshold=t["vague_critiques"],
        message="" if spec_pass else (
            f"{metrics.specificity_violations} vague critique(s) found"
        ),
    ))

    # Falsifiability
    fals_pass = metrics.falsifiability >= t["falsifiability"]
    checks.append(MetricCheck(
        name="falsifiability",
        passed=fals_pass,
        actual=metrics.falsifiability,
        threshold=t["falsifiability"],
        message="" if fals_pass else (
            f"Falsifiability {metrics.falsifiability:.2f} < {t['falsifiability']}"
        ),
    ))

    # Steel-man quality
    sm_pass = metrics.steel_man_sentences >= t["steel_man_sentences"]
    checks.append(MetricCheck(
        name="steel_man_quality",
        passed=sm_pass,
        actual=metrics.steel_man_sentences,
        threshold=t["steel_man_sentences"],
        message="" if sm_pass else (
            f"Steel-man has {metrics.steel_man_sentences} sentences, "
            f"need >= {t['steel_man_sentences']}"
        ),
    ))

    # Aggregate
    all_metrics_pass = all(c.passed for c in checks)
    any_anti_pattern = any(ap.detected for ap in anti_patterns)
    passes = all_metrics_pass and not any_anti_pattern

    issues: list[str] = []
    for c in checks:
        if not c.passed:
            issues.append(c.message)
    for ap in anti_patterns:
        if ap.detected:
            issues.append(f"Anti-pattern '{ap.pattern}': {ap.evidence}")

    return ReviewQualityReport(
        passes=passes,
        metric_checks=checks,
        anti_pattern_checks=anti_patterns,
        issues=issues,
        recommendation="pass" if passes else "revise_and_resubmit",
    )
