"""Report generation tool.

Generates structured markdown reports from evaluations using Jinja2 templates.
Supports three modes: digest, deep, and survey.
"""

from __future__ import annotations

from datetime import datetime

from jinja2 import Template

# ---------------------------------------------------------------------------
# Jinja2 Templates (inline)
# ---------------------------------------------------------------------------

DIGEST_TEMPLATE = Template("""\
# Research Digest: {{ title or "Weekly Papers" }}
**Date:** {{ date }}
**Papers reviewed:** {{ evaluations | length }}

{% for eval in evaluations %}
## {{ loop.index }}. {{ eval.title or "Untitled" }}
**Authors:** {{ eval.authors | join(", ") if eval.authors else "N/A" }} | \
**Year:** {{ eval.year or "N/A" }} | \
**Venue:** {{ eval.venue or "N/A" }}
{% if eval.arxiv_id %}**ArXiv:** https://arxiv.org/abs/{{ eval.arxiv_id }}{% endif %}

{% if eval.abstract %}> {{ eval.abstract[:300] }}{% if eval.abstract | length > 300 %}...{% endif %}{% endif %}

{% if eval.rubric_scores %}
| Dimension | Score | Confidence |
|-----------|-------|------------|
{% for dim, score_data in eval.rubric_scores.items() %}\
| {{ dim }} | {{ score_data.score }}/5 | {{ score_data.confidence }} |
{% endfor %}\
{% endif %}

{% if eval.significance_assessment %}\
**Significance:** Hamming={{ eval.significance_assessment.hamming_score }}/5 | \
Durability={{ eval.significance_assessment.durability_risk }} | \
Compounding={{ eval.significance_assessment.compounding_value }}
{% endif %}

{% if eval.human_review_flags %}\
**Flags for human review:**
{% for flag in eval.human_review_flags %}- {{ flag }}
{% endfor %}{% endif %}

---
{% endfor %}
""")


DEEP_TEMPLATE = Template("""\
# Paper Evaluation: {{ eval.title or "Untitled" }}
**Authors:** {{ eval.authors | join(", ") if eval.authors else "N/A" }} | \
**Venue:** {{ eval.venue or "N/A" }} | \
**Date:** {{ eval.year or "N/A" }}
{% if eval.arxiv_id %}**ArXiv:** https://arxiv.org/abs/{{ eval.arxiv_id }}{% endif %}\
{% if eval.code_url %} | **Code:** {{ eval.code_url }}{% endif %}

## Summary
{{ eval.abstract or "No abstract available." }}

{% if eval.task_chain %}\
## Task Chain
- **Task:** {{ eval.task_chain.task or "Not identified" }}
- **Problem:** {{ eval.task_chain.problem or "Not identified" }}
- **Challenge:** {{ eval.task_chain.challenge or "Not identified" }}
- **Approach:** {{ eval.task_chain.approach or "Not identified" }}
- **One-sentence insight:** {{ eval.task_chain.one_sentence or "Not identified" }}
- **Chain complete:** {{ "Yes" if eval.task_chain.chain_complete else "No" }} | \
**Chain coherent:** {{ "Yes" if eval.task_chain.chain_coherent else "No" }}
{% endif %}

## Rubric Evaluation

{% if eval.rubric_scores %}\
| Dimension | Score | Confidence | Key Evidence |
|-----------|-------|------------|--------------|
{% for dim, score_data in eval.rubric_scores.items() %}\
| **{{ dim }}** | {{ score_data.score }}/5 | {{ score_data.confidence }} | \
{{ score_data.evidence | join("; ") if score_data.evidence else "N/A" }} |
{% endfor %}\
{% else %}\
No rubric scores available.
{% endif %}

## Significance Assessment (§2.2 Tests)
{% if eval.significance_assessment %}\
- **Hamming test:** {{ eval.significance_assessment.hamming_score }}/5 — {{ eval.significance_assessment.hamming_reasoning or "No reasoning provided" }}
- **Consequence test:** {{ eval.significance_assessment.concrete_consequence or "Not assessed" }}
- **Durability test:** Risk={{ eval.significance_assessment.durability_risk }} — {{ eval.significance_assessment.durability_reasoning or "Not assessed" }}
- **Compounding value:** {{ eval.significance_assessment.compounding_value }} — {{ eval.significance_assessment.compounding_reasoning or "Not assessed" }}
- **Motivation type:** {{ eval.significance_assessment.motivation_type }}
- **HUMAN JUDGMENT REQUIRED:** Agent can detect significance *arguments* but cannot independently judge actual importance.
{% else %}\
Not assessed.
{% endif %}

## Problem Formalization Assessment (§2.4)
- **Formal statement present?** {{ "Yes" if eval.has_formal_problem_def else "No" }}
{% if eval.formal_framework %}\
- **Framework:** {{ eval.formal_framework }}
{% endif %}\
{% if eval.structure_identified %}\
- **Structure identified:** {{ eval.structure_identified | join(", ") }}
{% endif %}\
- **Formalization quality:** LOW CONFIDENCE — flagged for human review

## Strengths
{% if eval.strengths %}\
{% for s in eval.strengths %}\
- {{ s }}
{% endfor %}\
{% else %}\
No specific strengths noted.
{% endif %}

## Weaknesses (per research guidelines)
{% if eval.weaknesses %}\
{% for w in eval.weaknesses %}\
- {{ w }}
{% endfor %}\
{% else %}\
No specific weaknesses noted.
{% endif %}

## Connections to Prior Work
{% if eval.related_papers %}\
{% for rel in eval.related_papers %}\
- {{ rel.relation_type | capitalize }}: {{ rel.paper_id }}{% if rel.evidence %} — {{ rel.evidence }}{% endif %}

{% endfor %}\
{% else %}\
No connections identified.
{% endif %}

## Open Questions
{% if eval.open_questions %}\
{% for q in eval.open_questions %}\
- {{ q }}
{% endfor %}\
{% else %}\
None identified.
{% endif %}

{% if eval.human_review_flags %}\
## Flags for Human Review
{% for flag in eval.human_review_flags %}\
- {{ flag }}
{% endfor %}\
{% endif %}

{% if eval.extraction_limitations %}\
## Extraction Limitations
{% for lim in eval.extraction_limitations %}\
- {{ lim }}
{% endfor %}\
{% endif %}
""")


SURVEY_TEMPLATE = Template("""\
# Landscape Survey: {{ title or "Research Survey" }}
**Scope:** {{ scope or "Not specified" }}
**Papers analyzed:** {{ evaluations | length }} | **Date:** {{ date }}

## Significance Screening
{% set sig_count = evaluations | selectattr("significance_assessment") | list | length %}\
Of {{ evaluations | length }} papers surveyed, {{ sig_count }} have significance assessments.
{% for eval in evaluations if eval.significance_assessment %}\
- **{{ eval.title }}** — Hamming={{ eval.significance_assessment.hamming_score }}/5, \
Durability={{ eval.significance_assessment.durability_risk }}, \
Compounding={{ eval.significance_assessment.compounding_value }}
{% endfor %}
**HUMAN CHECKPOINT:** Review the significance assessments. The agent flags patterns but cannot judge actual importance.

## Problem Formalization Landscape
{% set formal_count = evaluations | selectattr("has_formal_problem_def") | list | length %}\
{{ formal_count }} of {{ evaluations | length }} papers have formal problem statements.
{% for eval in evaluations if eval.has_formal_problem_def %}\
- **{{ eval.title }}**{% if eval.formal_framework %} — {{ eval.formal_framework }}{% endif %}\
{% if eval.structure_identified %} (structure: {{ eval.structure_identified | join(", ") }}){% endif %}

{% endfor %}
**HUMAN CHECKPOINT:** Assess formalization quality for papers flagged as having formal definitions.

## Approach Taxonomy
{% if approach_groups %}\
{% for approach, papers in approach_groups.items() %}\
### {{ approach }}
{% for p in papers %}\
- {{ p.title }} ({{ p.year or "N/A" }}){% if p.venue %} — {{ p.venue }}{% endif %}

{% endfor %}
{% endfor %}\
{% else %}\
No approach taxonomy available. Manual grouping needed.
{% endif %}

## Capability Frontier (current)
- **Reliable:** {{ frontier.reliable | join(", ") if frontier and frontier.reliable else "Not assessed" }}
- **Sometimes:** {{ frontier.sometimes | join(", ") if frontier and frontier.sometimes else "Not assessed" }}
- **Can't yet:** {{ frontier.cant_yet | join(", ") if frontier and frontier.cant_yet else "Not assessed" }}

## Key Groups and Directions
{% if groups %}\
| Group | Recent Focus | Notable Results | Formalization Quality |
|-------|-------------|-----------------|----------------------|
{% for g in groups %}\
| {{ g.name }} | {{ g.focus }} | {{ g.results }} | {{ g.formalization }} |
{% endfor %}\
{% else %}\
No group analysis available.
{% endif %}

## Identified Gaps
{% if gaps %}\
{% for gap in gaps %}\
- {{ gap }}
{% endfor %}\
{% else %}\
No gaps identified yet.
{% endif %}

## Trend Analysis
{% if trends %}\
{% for trend in trends %}\
- {{ trend }}
{% endfor %}\
{% else %}\
Not enough data for trend analysis.
{% endif %}

## Proposed Research Directions
{% if directions %}\
{% for d in directions %}\
### {{ d.title }}
{{ d.description }}
- **Significance test:** {{ d.significance or "Not assessed" }}
- **Formal problem statement:** {{ d.formalization or "Not yet formulated" }}
- **One-sentence insight:** {{ d.one_sentence or "Not formulated" }}
- **Confidence:** {{ d.confidence or "Low" }}
{% endfor %}\
{% else %}\
No directions proposed. Insufficient data for Phase 1.
{% endif %}
""")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_report(
    evaluations: list[dict],
    mode: str = "deep",
    title: str = "",
    **extra_context,
) -> str:
    """Generate a markdown report from evaluations.

    Args:
        evaluations: List of evaluation dicts. Each should contain
            paper data and evaluation results.
        mode: Report mode — "digest", "deep", or "survey".
        title: Report title.
        **extra_context: Additional template context (e.g. approach_groups,
            frontier, groups, gaps, trends, directions for survey mode).

    Returns:
        Rendered markdown string.
    """
    date = datetime.now().strftime("%Y-%m-%d")

    if mode == "digest":
        return DIGEST_TEMPLATE.render(
            evaluations=evaluations,
            title=title,
            date=date,
        ).strip()

    elif mode == "deep":
        if not evaluations:
            return "# No evaluations provided.\n"
        # Deep mode reports on a single paper
        eval_data = evaluations[0]
        return DEEP_TEMPLATE.render(
            eval=eval_data,
            date=date,
        ).strip()

    elif mode == "survey":
        return SURVEY_TEMPLATE.render(
            evaluations=evaluations,
            title=title,
            date=date,
            scope=extra_context.get("scope", ""),
            approach_groups=extra_context.get("approach_groups", {}),
            frontier=extra_context.get("frontier"),
            groups=extra_context.get("groups", []),
            gaps=extra_context.get("gaps", []),
            trends=extra_context.get("trends", []),
            directions=extra_context.get("directions", []),
        ).strip()

    else:
        raise ValueError(f"Unknown report mode: {mode!r}. Use 'digest', 'deep', or 'survey'.")
