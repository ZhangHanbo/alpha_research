"""Configuration models and loaders for alpha_research.

Provides YAML-backed configuration for:
  - Constitution: defines the research agent's domain focus
  - ReviewConfig: defines review thresholds, iteration limits, pressure schedule

Sources:
  - work_plan.md (constitution concept)
  - review_plan.md §4.4 (review_config.yaml spec)
  - review_plan.md §2.5-2.6 (convergence, graduated pressure)
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field

from alpha_research.models.blackboard import Venue


# ---------------------------------------------------------------------------
# Constitution Config
# ---------------------------------------------------------------------------

class ConstitutionConfig(BaseModel):
    """Research agent's domain constitution — loaded from YAML.

    Defines what the research agent focuses on, which communities
    it tracks, and operational limits per cycle.
    """

    name: str = "Robotics Research"
    focus_areas: list[str] = Field(default_factory=lambda: [
        "mobile manipulation",
        "contact-rich manipulation",
        "tactile sensing and feedback",
        "learning for manipulation",
        "task and motion planning",
    ])
    key_groups: list[str] = Field(default_factory=lambda: [
        "Levine", "Tedrake", "Abbeel", "Finn", "Kaelbling",
        "Rus", "Fox", "Todorov", "Goldberg", "Bohg",
        "Song", "Pinto", "Pavone", "Agrawal", "Zeng",
    ])
    domains: list[str] = Field(default_factory=lambda: [
        "robotics",
        "computer vision for robotics",
        "reinforcement learning for robotics",
        "planning and control",
    ])
    max_papers_per_cycle: int = 50


# ---------------------------------------------------------------------------
# Review Config
# ---------------------------------------------------------------------------

class QualityThreshold(BaseModel):
    """Convergence quality thresholds (review_plan.md §2.5)."""
    max_fatal: int = 0
    max_serious: int = 1
    min_verdict: str = "weak_accept"


class GraduatedPressure(BaseModel):
    """Graduated adversarial pressure schedule (review_plan.md §2.6)."""
    iteration_1: str = "structural_scan"
    iteration_2: str = "full_review"
    iteration_3_plus: str = "focused_rereview"


class HumanCheckpoints(BaseModel):
    """When to trigger human review (review_plan.md §2.4)."""
    on_backward_to_significance: bool = True
    on_low_confidence_significance: bool = True
    on_low_confidence_formalization: bool = True
    on_final_accept: bool = True
    periodic: int = 3


class ReviewQualityThresholds(BaseModel):
    """Thresholds for meta-reviewer quality checks (review_plan.md §1.8)."""
    min_actionability: float = 0.80
    min_grounding: float = 0.90
    max_vague_critiques: int = 0
    min_falsifiability: float = 0.70
    min_steel_man_sentences: int = 3


class AntiCollapseSettings(BaseModel):
    """Anti-collapse mechanisms (review_plan.md §2.7)."""
    monotonic_severity: bool = True
    min_finding_resolution: float = 0.50
    fresh_eyes_final: bool = True


class ReviewConfig(BaseModel):
    """Full review agent configuration — loaded from YAML.

    Covers venue targeting, iteration limits, convergence criteria,
    graduated pressure, human checkpoints, and quality thresholds.
    Source: review_plan.md §4.4
    """

    target_venue: str = "RSS"
    max_iterations: int = 5
    meta_review_max_rounds: int = 2
    stagnation_threshold: int = 2

    quality_threshold: QualityThreshold = Field(
        default_factory=QualityThreshold,
    )
    graduated_pressure: GraduatedPressure = Field(
        default_factory=GraduatedPressure,
    )
    human_checkpoints: HumanCheckpoints = Field(
        default_factory=HumanCheckpoints,
    )
    review_quality_thresholds: ReviewQualityThresholds = Field(
        default_factory=ReviewQualityThresholds,
    )
    anti_collapse: AntiCollapseSettings = Field(
        default_factory=AntiCollapseSettings,
    )

    def get_review_depth(self, iteration: int) -> str:
        """Return the review depth for a given iteration number."""
        if iteration <= 0:
            iteration = 1
        if iteration == 1:
            return self.graduated_pressure.iteration_1
        elif iteration == 2:
            return self.graduated_pressure.iteration_2
        else:
            return self.graduated_pressure.iteration_3_plus

    def resolve_venue(self) -> Venue:
        """Resolve the target_venue string to a Venue enum member."""
        normalized = self.target_venue.upper().replace("-", "_")
        for v in Venue:
            if v.name == normalized or v.value.upper().replace("-", "_") == normalized:
                return v
        # Fallback: try direct value match
        return Venue(self.target_venue)


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_yaml(path: str) -> dict[str, Any]:
    """Load a YAML file and return its contents as a dict."""
    p = Path(path)
    if not p.exists():
        return {}
    with p.open("r") as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


def load_constitution(path: str) -> ConstitutionConfig:
    """Load a ConstitutionConfig from a YAML file.

    Returns sensible defaults when the file does not exist.
    """
    data = _load_yaml(path)
    return ConstitutionConfig(**data) if data else ConstitutionConfig()


def load_review_config(path: str) -> ReviewConfig:
    """Load a ReviewConfig from a YAML file.

    Returns sensible defaults when the file does not exist.
    """
    data = _load_yaml(path)
    return ReviewConfig(**data) if data else ReviewConfig()
