"""Tests for system prompts and config (T4).

Tests:
  - Config loading (with and without files)
  - Research prompt contains required elements
  - Review prompt changes based on venue
  - Review prompt changes based on iteration (graduated pressure)
  - Meta-review prompt contains all metric thresholds
  - All prompts specify JSON output formats
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from alpha_research.config import (
    ConstitutionConfig,
    ReviewConfig,
    load_constitution,
    load_review_config,
)
from alpha_research.models.blackboard import Venue
from alpha_research.prompts.meta_review_system import build_meta_review_prompt
from alpha_research.prompts.research_system import build_research_prompt
from alpha_research.prompts.review_system import build_review_prompt
from alpha_research.prompts.rubric import (
    ATTACK_VECTORS,
    RESEARCH_RUBRIC,
    REVIEW_RUBRIC,
    SIGNIFICANCE_TESTS,
)


# =====================================================================
# Config Loading Tests
# =====================================================================

class TestConfigLoading:
    """Test config loading with and without files."""

    def test_load_constitution_default_when_missing(self):
        """Provide sensible defaults when config file doesn't exist."""
        config = load_constitution("/nonexistent/path/constitution.yaml")
        assert isinstance(config, ConstitutionConfig)
        assert config.name == "Robotics Research"
        assert len(config.focus_areas) > 0
        assert len(config.key_groups) > 0
        assert config.max_papers_per_cycle == 50

    def test_load_review_config_default_when_missing(self):
        """Provide sensible defaults when config file doesn't exist."""
        config = load_review_config("/nonexistent/path/review_config.yaml")
        assert isinstance(config, ReviewConfig)
        assert config.target_venue == "RSS"
        assert config.max_iterations == 5
        assert config.meta_review_max_rounds == 2

    def test_load_constitution_from_yaml(self, tmp_path):
        """Load constitution from an actual YAML file."""
        data = {
            "name": "Test Research",
            "focus_areas": ["area1", "area2"],
            "key_groups": ["GroupA"],
            "domains": ["robotics"],
            "max_papers_per_cycle": 25,
        }
        path = tmp_path / "constitution.yaml"
        path.write_text(yaml.dump(data))

        config = load_constitution(str(path))
        assert config.name == "Test Research"
        assert config.focus_areas == ["area1", "area2"]
        assert config.key_groups == ["GroupA"]
        assert config.max_papers_per_cycle == 25

    def test_load_review_config_from_yaml(self, tmp_path):
        """Load review config from an actual YAML file."""
        data = {
            "target_venue": "CoRL",
            "max_iterations": 3,
            "meta_review_max_rounds": 1,
            "quality_threshold": {
                "max_fatal": 0,
                "max_serious": 2,
                "min_verdict": "weak_accept",
            },
        }
        path = tmp_path / "review_config.yaml"
        path.write_text(yaml.dump(data))

        config = load_review_config(str(path))
        assert config.target_venue == "CoRL"
        assert config.max_iterations == 3
        assert config.quality_threshold.max_serious == 2

    def test_load_actual_config_files(self):
        """Load the actual config files in config/."""
        base = Path(__file__).parent.parent / "config"

        const_path = base / "constitution.yaml"
        if const_path.exists():
            config = load_constitution(str(const_path))
            assert config.name == "Robotics Research"
            assert "Levine" in config.key_groups

        review_path = base / "review_config.yaml"
        if review_path.exists():
            config = load_review_config(str(review_path))
            assert config.target_venue == "RSS"
            assert config.review_quality_thresholds.min_actionability == 0.80

    def test_review_config_get_review_depth(self):
        """Test graduated pressure schedule."""
        config = ReviewConfig()
        assert config.get_review_depth(1) == "structural_scan"
        assert config.get_review_depth(2) == "full_review"
        assert config.get_review_depth(3) == "focused_rereview"
        assert config.get_review_depth(4) == "focused_rereview"
        assert config.get_review_depth(0) == "structural_scan"

    def test_review_config_resolve_venue(self):
        """Test venue string to enum resolution."""
        config = ReviewConfig(target_venue="RSS")
        assert config.resolve_venue() == Venue.RSS

        config2 = ReviewConfig(target_venue="CoRL")
        assert config2.resolve_venue() == Venue.CORL

    def test_constitution_defaults_non_empty(self):
        """Default constitution must have meaningful values."""
        config = ConstitutionConfig()
        assert len(config.focus_areas) >= 3
        assert len(config.key_groups) >= 10
        assert len(config.domains) >= 2

    def test_review_config_quality_thresholds(self):
        """Review quality thresholds must match review_plan.md §1.8."""
        config = ReviewConfig()
        t = config.review_quality_thresholds
        assert t.min_actionability == 0.80
        assert t.min_grounding == 0.90
        assert t.max_vague_critiques == 0
        assert t.min_falsifiability == 0.70
        assert t.min_steel_man_sentences == 3


# =====================================================================
# Research Prompt Tests
# =====================================================================

class TestResearchPrompt:
    """Test that the research prompt contains required elements."""

    @pytest.fixture
    def constitution(self):
        return ConstitutionConfig()

    def test_contains_significance_tests(self, constitution):
        """Research prompt must include the significance tests."""
        prompt = build_research_prompt(constitution, "significance")
        assert "Hamming Test" in prompt
        assert "Consequence Test" in prompt
        assert "Durability" in prompt or "48 months" in prompt
        assert "Compounding" in prompt or "Portfolio" in prompt
        assert "goal-driven" in prompt.lower() or "goal_driven" in prompt.lower()

    def test_contains_rubric(self, constitution):
        """Research prompt must include the evaluation rubric."""
        prompt = build_research_prompt(constitution, "full_draft")
        assert "B.1" in prompt or "Significance and Problem Definition" in prompt
        assert "B.2" in prompt or "Technical Approach" in prompt
        assert "B.3" in prompt or "Experimental Rigor" in prompt

    def test_contains_output_format(self, constitution):
        """Research prompt must specify JSON output format."""
        prompt = build_research_prompt(constitution, "significance")
        assert "JSON" in prompt or "json" in prompt
        assert "ResearchArtifact" in prompt
        assert "task_chain" in prompt

    def test_contains_formalization_standards(self, constitution):
        """Research prompt must include formalization guidance."""
        prompt = build_research_prompt(constitution, "formalization")
        assert "formalization" in prompt.lower() or "Formalization" in prompt
        assert "optimization" in prompt.lower()
        assert "constraints" in prompt.lower()

    def test_contains_honesty_protocol(self, constitution):
        """Research prompt must include honesty standards."""
        prompt = build_research_prompt(constitution, "significance")
        assert "confidence" in prompt.lower()
        assert "overclaim" in prompt.lower()
        assert "limitations" in prompt.lower()

    def test_contains_task_chain_instructions(self, constitution):
        """Research prompt must include task chain extraction."""
        prompt = build_research_prompt(constitution, "significance")
        assert "task_chain" in prompt or "task chain" in prompt.lower()
        assert "chain_complete" in prompt
        assert "chain_coherent" in prompt

    def test_stage_context_significance(self, constitution):
        """Prompt changes based on stage - significance."""
        prompt = build_research_prompt(constitution, "significance")
        assert "SIGNIFICANCE" in prompt
        assert "significance argument" in prompt.lower()

    def test_stage_context_formalization(self, constitution):
        """Prompt changes based on stage - formalization."""
        prompt = build_research_prompt(constitution, "formalization")
        assert "FORMALIZATION" in prompt
        assert "formal problem" in prompt.lower()

    def test_stage_context_full_draft(self, constitution):
        """Prompt changes based on stage - full_draft."""
        prompt = build_research_prompt(constitution, "full_draft")
        assert "FULL DRAFT" in prompt

    def test_revision_mode_with_findings(self, constitution):
        """When previous findings are provided, revision instructions appear."""
        findings = [
            {
                "id": "sig-1",
                "severity": "serious",
                "what_is_wrong": "Significance argument is vague",
                "why_it_matters": "Cannot assess importance",
                "what_would_fix": "Provide concrete consequence test",
            }
        ]
        prompt = build_research_prompt(constitution, "significance", findings)
        assert "Previous Review Findings" in prompt
        assert "sig-1" in prompt
        assert "Significance argument is vague" in prompt
        assert "RevisionResponse" in prompt

    def test_no_revision_without_findings(self, constitution):
        """Without findings, no revision section appears."""
        prompt = build_research_prompt(constitution, "significance")
        assert "Previous Review Findings" not in prompt

    def test_constitution_reflected_in_prompt(self, constitution):
        """Constitution values appear in the prompt."""
        prompt = build_research_prompt(constitution, "significance")
        assert constitution.name in prompt
        for area in constitution.focus_areas[:2]:
            assert area in prompt


# =====================================================================
# Review Prompt Tests
# =====================================================================

class TestReviewPrompt:
    """Test review prompt venue and iteration variation."""

    def test_changes_based_on_venue_rss(self):
        """RSS venue name and thresholds must appear."""
        prompt = build_review_prompt("RSS", iteration=2)
        assert "RSS" in prompt
        assert "30%" in prompt or "~30%" in prompt

    def test_changes_based_on_venue_ijrr(self):
        """IJRR venue name and thresholds must appear."""
        prompt = build_review_prompt("IJRR", iteration=2)
        assert "IJRR" in prompt
        assert "20%" in prompt or "~20%" in prompt
        assert "fatal" in prompt.lower()

    def test_changes_based_on_venue_corl(self):
        """CoRL venue name must appear."""
        prompt = build_review_prompt("CoRL", iteration=2)
        assert "CoRL" in prompt

    def test_changes_based_on_venue_icra(self):
        """ICRA venue name must appear."""
        prompt = build_review_prompt("ICRA", iteration=2)
        assert "ICRA" in prompt

    def test_different_venues_produce_different_prompts(self):
        """Different venue names produce materially different prompts."""
        rss_prompt = build_review_prompt("RSS", iteration=2)
        ijrr_prompt = build_review_prompt("IJRR", iteration=2)
        # They share common structure but differ in venue-specific sections
        assert rss_prompt != ijrr_prompt
        # RSS mentions sharp insight; IJRR mentions maximum depth
        assert "sharp" in rss_prompt.lower() or "insight" in rss_prompt.lower()
        assert "maximum" in ijrr_prompt.lower() or "comprehensive" in ijrr_prompt.lower()

    def test_graduated_pressure_iteration_1(self):
        """Iteration 1 should be structural scan only."""
        prompt = build_review_prompt("RSS", iteration=1)
        assert "STRUCTURAL SCAN" in prompt or "structural scan" in prompt.lower()
        assert "Five-Minute Fatal Flaw Scan" in prompt

    def test_graduated_pressure_iteration_2(self):
        """Iteration 2 should be full review with all attack vectors."""
        prompt = build_review_prompt("RSS", iteration=2)
        assert "FULL REVIEW" in prompt or "full review" in prompt.lower()
        assert "Three-Pass Protocol" in prompt
        # Full review should include attack vectors
        assert "3.1" in prompt or "Attacking Significance" in prompt

    def test_graduated_pressure_iteration_3_plus(self):
        """Iteration 3+ should be focused re-review."""
        prompt = build_review_prompt("RSS", iteration=3,
                                     review_mode="focused_rereview")
        assert "FOCUSED RE-REVIEW" in prompt or "focused re-review" in prompt.lower()
        assert "regression" in prompt.lower()

    def test_contains_anti_patterns(self):
        """Review prompt must warn against anti-patterns."""
        prompt = build_review_prompt("RSS", iteration=2)
        assert "Dimension averaging" in prompt or "dimension averaging" in prompt.lower()
        assert "False balance" in prompt or "false balance" in prompt.lower()
        assert "Novelty fetishism" in prompt or "novelty fetishism" in prompt.lower()

    def test_contains_json_output_format(self):
        """Review prompt must specify JSON output format."""
        prompt = build_review_prompt("RSS", iteration=2)
        assert "JSON" in prompt or "json" in prompt
        assert "Finding" in prompt
        assert "verdict" in prompt
        assert "steel_man" in prompt

    def test_contains_verdict_rules(self):
        """Review prompt must contain mechanical verdict rules."""
        prompt = build_review_prompt("RSS", iteration=2)
        assert "fatal" in prompt.lower() and "reject" in prompt.lower()
        assert "gate dimension" in prompt.lower() or "Gate Dimension" in prompt

    def test_contains_review_rubric(self):
        """Review prompt must include the review rubric."""
        prompt = build_review_prompt("RSS", iteration=2)
        assert "6.1" in prompt or "Significance and Problem Definition" in prompt
        assert "6.2" in prompt or "Technical Approach" in prompt

    def test_previous_findings_in_rereview(self):
        """Focused re-review includes previous findings context."""
        findings = [
            {
                "id": "val-1",
                "severity": "serious",
                "what_is_wrong": "Missing ablation study",
                "why_it_matters": "Cannot isolate contribution",
                "what_would_fix": "Add ablation removing key component",
                "falsification": "If ablation shows contribution matters",
            }
        ]
        prompt = build_review_prompt("RSS", iteration=3,
                                     previous_findings=findings,
                                     review_mode="focused_rereview")
        assert "val-1" in prompt
        assert "Missing ablation study" in prompt

    def test_full_review_includes_attack_vectors(self):
        """Full review mode must include all attack vectors."""
        prompt = build_review_prompt("RSS", iteration=2, review_mode="full_review")
        assert "Hamming failure" in prompt
        assert "Absent formalization" in prompt
        assert "Resource complaint" in prompt
        assert "Method-shopping" in prompt
        assert "Baseline strength" in prompt
        assert "Prior work overlap" in prompt

    def test_full_review_includes_significance_tests(self):
        """Full review mode must include significance tests."""
        prompt = build_review_prompt("RSS", iteration=2, review_mode="full_review")
        assert "Hamming Test" in prompt
        assert "Consequence Test" in prompt


# =====================================================================
# Meta-Review Prompt Tests
# =====================================================================

class TestMetaReviewPrompt:
    """Test meta-review prompt contains all required elements."""

    def test_contains_all_metric_thresholds(self):
        """Meta-review prompt must contain exact metric thresholds."""
        prompt = build_meta_review_prompt()
        # Actionability >= 80%
        assert "80%" in prompt or "0.80" in prompt
        # Grounding >= 90%
        assert "90%" in prompt or "0.90" in prompt
        # Zero vague critiques
        assert "0" in prompt and "vague" in prompt.lower()
        # Falsifiability >= 70%
        assert "70%" in prompt or "0.70" in prompt
        # Steel-man >= 3 sentences
        assert "3 sentence" in prompt.lower() or ">= 3" in prompt

    def test_contains_anti_pattern_checklist(self):
        """Meta-review prompt must list all anti-patterns."""
        prompt = build_meta_review_prompt()
        assert "Dimension Averaging" in prompt or "dimension averaging" in prompt.lower()
        assert "False Balance" in prompt or "false balance" in prompt.lower()
        assert "Novelty Fetishism" in prompt or "novelty fetishism" in prompt.lower()
        assert "Recency Bias" in prompt or "recency bias" in prompt.lower()
        assert "Blanket" in prompt or "blanket" in prompt.lower()
        assert "Punishing" in prompt or "honest limitations" in prompt.lower()

    def test_contains_json_output_format(self):
        """Meta-review prompt must specify JSON output format."""
        prompt = build_meta_review_prompt()
        assert "JSON" in prompt or "json" in prompt
        assert "ReviewQualityReport" in prompt
        assert "metric_checks" in prompt
        assert "anti_pattern_checks" in prompt
        assert "passes" in prompt

    def test_identity_as_area_chair(self):
        """Meta-reviewer must identify as area chair."""
        prompt = build_meta_review_prompt()
        assert "area chair" in prompt.lower()

    def test_contains_convergence_monitoring(self):
        """Meta-review prompt must include convergence monitoring."""
        prompt = build_meta_review_prompt()
        assert "mode collapse" in prompt.lower() or "Mode Collapse" in prompt
        assert "monotonic" in prompt.lower()


# =====================================================================
# Rubric String Tests
# =====================================================================

class TestRubricStrings:
    """Test that rubric strings contain actual criteria from guideline docs."""

    def test_research_rubric_dimensions(self):
        """Research rubric must contain all 7 dimensions."""
        assert "B.1" in RESEARCH_RUBRIC
        assert "B.2" in RESEARCH_RUBRIC
        assert "B.3" in RESEARCH_RUBRIC
        assert "B.4" in RESEARCH_RUBRIC
        assert "B.5" in RESEARCH_RUBRIC
        assert "B.6" in RESEARCH_RUBRIC
        assert "B.7" in RESEARCH_RUBRIC

    def test_research_rubric_scoring(self):
        """Research rubric must contain 1-5 scoring criteria."""
        for score in ["| 5 |", "| 4 |", "| 3 |", "| 2 |", "| 1 |"]:
            assert score in RESEARCH_RUBRIC

    def test_review_rubric_dimensions(self):
        """Review rubric must contain all §6 dimensions."""
        assert "6.1" in REVIEW_RUBRIC
        assert "6.2" in REVIEW_RUBRIC
        assert "6.3" in REVIEW_RUBRIC
        assert "6.4" in REVIEW_RUBRIC
        assert "6.5" in REVIEW_RUBRIC

    def test_significance_tests_complete(self):
        """Significance tests must contain all four test categories."""
        assert "Hamming" in SIGNIFICANCE_TESTS
        assert "Consequence" in SIGNIFICANCE_TESTS
        assert "Portfolio" in SIGNIFICANCE_TESTS or "Compounding" in SIGNIFICANCE_TESTS
        assert "48 months" in SIGNIFICANCE_TESTS or "Durability" in SIGNIFICANCE_TESTS

    def test_attack_vectors_complete(self):
        """Attack vectors must cover all 6 sections."""
        assert "3.1" in ATTACK_VECTORS
        assert "3.2" in ATTACK_VECTORS
        assert "3.3" in ATTACK_VECTORS
        assert "3.4" in ATTACK_VECTORS
        assert "3.5" in ATTACK_VECTORS
        assert "3.6" in ATTACK_VECTORS

    def test_attack_vectors_specific_checks(self):
        """Attack vectors must contain specific named checks."""
        assert "Hamming failure" in ATTACK_VECTORS
        assert "Consequence failure" in ATTACK_VECTORS
        assert "Absent formalization" in ATTACK_VECTORS
        assert "Resource complaint" in ATTACK_VECTORS
        assert "Method-shopping" in ATTACK_VECTORS
        assert "Baseline strength" in ATTACK_VECTORS
        assert "Overclaiming" in ATTACK_VECTORS or "overclaim" in ATTACK_VECTORS.lower()
        assert "Prior work overlap" in ATTACK_VECTORS


# =====================================================================
# Cross-Cutting Tests
# =====================================================================

class TestAllPromptsJSONOutput:
    """Verify all prompts instruct agents to produce JSON output."""

    def test_research_prompt_json(self):
        prompt = build_research_prompt(ConstitutionConfig(), "significance")
        assert "json" in prompt.lower()

    def test_review_prompt_json(self):
        prompt = build_review_prompt("RSS", iteration=2)
        assert "json" in prompt.lower()

    def test_meta_review_prompt_json(self):
        prompt = build_meta_review_prompt()
        assert "json" in prompt.lower()
