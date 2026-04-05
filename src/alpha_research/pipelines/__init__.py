"""Pipelines: deterministic Python orchestration over skills.

Pipelines extract the non-LLM orchestration logic from the old ``agents/``
package into reusable, testable functions. Each pipeline takes a
``skill_invoker`` dependency so tests can inject mocks; production code
defaults to invoking skills via :mod:`alpha_research.llm` /
:mod:`alpha_review.llm`.
"""

from alpha_research.pipelines.state_machine import (
    BACKWARD_TRANSITIONS,
    FORWARD_TRANSITIONS,
    BackwardTrigger,
    backward_trigger_from_finding,
    stage_guard_satisfied,
    valid_transitions,
)

# The heavier pipelines are imported lazily to avoid mandatory dependency
# on the alpha_review package at import time (tests may patch it).
from alpha_research.pipelines.literature_survey import (
    LiteratureSurveyResult,
    run_literature_survey,
)
from alpha_research.pipelines.method_survey import (
    MethodSurveyResult,
    run_method_survey,
)
from alpha_research.pipelines.frontier_mapping import (
    FrontierReport,
    run_frontier_mapping,
)
from alpha_research.pipelines.research_review_loop import (
    LoopResult,
    run_research_review_loop,
)

__all__ = [
    "BACKWARD_TRANSITIONS",
    "FORWARD_TRANSITIONS",
    "BackwardTrigger",
    "backward_trigger_from_finding",
    "stage_guard_satisfied",
    "valid_transitions",
    "LiteratureSurveyResult",
    "run_literature_survey",
    "MethodSurveyResult",
    "run_method_survey",
    "FrontierReport",
    "run_frontier_mapping",
    "LoopResult",
    "run_research_review_loop",
]
