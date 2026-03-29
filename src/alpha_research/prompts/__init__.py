"""System prompt builders for all agents."""

from alpha_research.prompts.meta_review_system import build_meta_review_prompt
from alpha_research.prompts.research_system import build_research_prompt
from alpha_research.prompts.review_system import build_review_prompt
from alpha_research.prompts.rubric import (
    ATTACK_VECTORS,
    RESEARCH_RUBRIC,
    REVIEW_RUBRIC,
    SIGNIFICANCE_TESTS,
)

__all__ = [
    "build_meta_review_prompt",
    "build_research_prompt",
    "build_review_prompt",
    "ATTACK_VECTORS",
    "RESEARCH_RUBRIC",
    "REVIEW_RUBRIC",
    "SIGNIFICANCE_TESTS",
]
