"""Tests for scripts/audit_stats.py."""

from __future__ import annotations

import csv
import json
import math
from pathlib import Path

import audit_stats


def _write_trials_csv(path: Path, n: int, seeds: int = 1, rate: float = 1.0) -> None:
    with path.open("w", newline="", encoding="utf-8") as fp:
        writer = csv.writer(fp)
        writer.writerow(["seed", "trial", "success"])
        per_seed = n // seeds
        for s in range(seeds):
            successes = int(round(per_seed * rate))
            for t in range(per_seed):
                writer.writerow([s, t, 1 if t < successes else 0])


def test_rss_25_trials_threshold_met(tmp_path: Path) -> None:
    _write_trials_csv(tmp_path / "trials.csv", n=25, seeds=5, rate=0.8)
    loaded = audit_stats.load_experiment(tmp_path, "success_rate")
    stats = audit_stats.compute_stats(
        loaded["per_seed_rates"], loaded["total_trials"], "RSS"
    )
    assert stats["venue_threshold_met"] is True
    assert stats["insufficient_trials"] is False
    assert stats["trials_per_condition"] == 25
    assert stats["n_seeds"] == 5
    assert stats["mean_success_rate"] == 0.8


def test_ijrr_5_trials_insufficient(tmp_path: Path) -> None:
    results = {"success_rate": 1.0, "n_trials": 5}
    (tmp_path / "results.json").write_text(json.dumps(results))
    loaded = audit_stats.load_experiment(tmp_path, "success_rate")
    stats = audit_stats.compute_stats(
        loaded["per_seed_rates"], loaded["total_trials"], "IJRR"
    )
    assert stats["venue_threshold_met"] is False
    assert stats["insufficient_trials"] is True
    assert stats["trials_per_condition"] == 5


def test_missing_exp_dir_error_output(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "does_not_exist"
    rc = audit_stats.main([str(missing), "--venue", "RSS"])
    assert rc == 2
    data = json.loads(capsys.readouterr().out.strip())
    assert "error" in data


def test_ci_computation_known_variance(tmp_path: Path) -> None:
    # Five seeds with values [0.5, 0.6, 0.7, 0.8, 0.9]
    # mean = 0.7, stdev (sample) = 0.158113883...
    # sem = 0.070710678... ; t(0.975, df=4) = 2.776
    # CI half-width = 2.776 * 0.070710678 = 0.196292
    for i, rate in enumerate([0.5, 0.6, 0.7, 0.8, 0.9]):
        seed_dir = tmp_path / f"seed_{i}"
        seed_dir.mkdir()
        (seed_dir / "metrics.json").write_text(
            json.dumps({"success_rate": rate, "n_trials": 20})
        )
    loaded = audit_stats.load_experiment(tmp_path, "success_rate")
    stats = audit_stats.compute_stats(
        loaded["per_seed_rates"], loaded["total_trials"], "RSS"
    )
    assert math.isclose(stats["mean_success_rate"], 0.7, abs_tol=1e-9)
    assert math.isclose(stats["std_across_seeds"], 0.158113883, abs_tol=1e-6)
    low, high = stats["ci_95"]
    assert math.isclose(low, 0.7 - 0.196292, abs_tol=1e-3)
    assert math.isclose(high, 0.7 + 0.196292, abs_tol=1e-3)
    assert stats["trials_per_condition"] == 100
    assert stats["venue_threshold_met"] is True


def test_seed_dirs_loader(tmp_path: Path) -> None:
    for i in range(3):
        d = tmp_path / f"seed_{i}"
        d.mkdir()
        (d / "metrics.json").write_text(
            json.dumps({"success_rate": 0.6 + 0.1 * i, "n_trials": 10})
        )
    loaded = audit_stats.load_experiment(tmp_path, "success_rate")
    assert loaded["source"] == "seed_dirs"
    assert loaded["total_trials"] == 30
    assert len(loaded["per_seed_rates"]) == 3


def test_cli_main_with_results_json(tmp_path: Path, capsys) -> None:
    (tmp_path / "results.json").write_text(
        json.dumps({"success_rate": 0.9, "n_trials": 30})
    )
    rc = audit_stats.main([str(tmp_path), "--venue", "RSS"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out.strip())
    assert data["venue_threshold_met"] is True
    assert data["trials_per_condition"] == 30
    assert data["venue"] == "RSS"
