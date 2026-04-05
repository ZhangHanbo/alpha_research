#!/usr/bin/env python
"""Compute experiment audit statistics for a results directory.

Usage
-----
    python scripts/audit_stats.py <exp_dir> --venue RSS [--metric success_rate]

Reads experiment results from one of:

    <exp_dir>/results.json          # single-run dict
    <exp_dir>/trials.csv            # per-trial rows with a success column
    <exp_dir>/seed_*/metrics.json   # multi-seed structure

Emits a JSON object to stdout with fields::

    {
      "exp_dir": "...",
      "venue": "RSS",
      "metric": "success_rate",
      "trials_per_condition": int,
      "mean_success_rate": float,
      "std_across_seeds": float,
      "ci_95": [low, high],
      "venue_threshold_met": bool,
      "insufficient_trials": bool,
      "n_seeds": int,
    }

No numpy/scipy dependency — uses the stdlib ``statistics`` module plus
a small Student's-t critical-value table for 95% two-sided intervals.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Any


# Venue trial thresholds (review_plan.md §1.6)
VENUE_TRIAL_MINIMUMS = {
    "RSS": 20,
    "IJRR": 20,
    "T-RO": 20,
    "T_RO": 20,
    "CORL": 10,
    "CoRL": 10,
    "ICRA": 10,
    "IROS": 10,
    "RA-L": 10,
    "RA_L": 10,
}


# Two-sided t critical values for alpha=0.05 (95% CI).
# Indexed by degrees of freedom; values beyond the table fall back to 1.96.
_T_95 = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571,
    6: 2.447, 7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228,
    11: 2.201, 12: 2.179, 13: 2.160, 14: 2.145, 15: 2.131,
    16: 2.120, 17: 2.110, 18: 2.101, 19: 2.093, 20: 2.086,
    21: 2.080, 22: 2.074, 23: 2.069, 24: 2.064, 25: 2.060,
    26: 2.056, 27: 2.052, 28: 2.048, 29: 2.045, 30: 2.042,
    40: 2.021, 50: 2.009, 60: 2.000, 80: 1.990, 100: 1.984,
    120: 1.980, 200: 1.972, 500: 1.965, 1000: 1.962,
}


def _t_critical_95(df: int) -> float:
    """Return the two-sided 95% critical value for Student-t with ``df``."""
    if df <= 0:
        return float("nan")
    if df in _T_95:
        return _T_95[df]
    # Linear interpolation between the nearest tabulated df values
    keys = sorted(_T_95.keys())
    if df > keys[-1]:
        return 1.96
    lo = max(k for k in keys if k < df)
    hi = min(k for k in keys if k > df)
    frac = (df - lo) / (hi - lo)
    return _T_95[lo] + frac * (_T_95[hi] - _T_95[lo])


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def _load_results_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fp:
        return json.load(fp)


def _load_trials_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as fp:
        reader = csv.DictReader(fp)
        return list(reader)


def _find_success_column(row: dict[str, Any]) -> str | None:
    for candidate in ("success", "succeeded", "success_rate", "result"):
        if candidate in row:
            return candidate
    return None


def _coerce_success(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().lower()
    if s in {"true", "1", "yes", "success", "pass"}:
        return 1.0
    if s in {"false", "0", "no", "failure", "fail"}:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def load_experiment(exp_dir: Path, metric: str) -> dict[str, Any]:
    """Load trials and per-seed success rates from ``exp_dir``.

    Returns a dict with ``per_seed_rates`` (list[float]),
    ``total_trials`` (int), and ``source`` (str).
    """
    exp_dir = Path(exp_dir)
    if not exp_dir.exists():
        raise FileNotFoundError(f"Experiment directory not found: {exp_dir}")

    # 1) multi-seed: seed_*/metrics.json
    seed_dirs = sorted(
        d for d in exp_dir.glob("seed_*") if d.is_dir()
    )
    if seed_dirs:
        per_seed: list[float] = []
        total_trials = 0
        for seed_dir in seed_dirs:
            metrics_path = seed_dir / "metrics.json"
            if not metrics_path.exists():
                continue
            data = _load_results_json(metrics_path)
            rate = float(data.get(metric, data.get("success_rate", 0.0)))
            n = int(data.get("n_trials", data.get("trials", 1)))
            per_seed.append(rate)
            total_trials += n
        if per_seed:
            return {
                "per_seed_rates": per_seed,
                "total_trials": total_trials,
                "source": "seed_dirs",
            }

    # 2) single-run results.json
    results_path = exp_dir / "results.json"
    if results_path.exists():
        data = _load_results_json(results_path)
        # Accept either {success_rate, n_trials} or {per_seed: [...]}
        if "per_seed" in data and isinstance(data["per_seed"], list):
            per_seed = [float(x) for x in data["per_seed"]]
            total = int(data.get("n_trials", len(per_seed)))
            return {
                "per_seed_rates": per_seed,
                "total_trials": total,
                "source": "results.json",
            }
        rate = float(data.get(metric, data.get("success_rate", 0.0)))
        n = int(data.get("n_trials", data.get("trials", 1)))
        return {
            "per_seed_rates": [rate],
            "total_trials": n,
            "source": "results.json",
        }

    # 3) trials.csv
    trials_path = exp_dir / "trials.csv"
    if trials_path.exists():
        rows = _load_trials_csv(trials_path)
        if not rows:
            return {
                "per_seed_rates": [],
                "total_trials": 0,
                "source": "trials.csv",
            }
        col = _find_success_column(rows[0])
        if col is None:
            raise ValueError(
                f"trials.csv has no recognizable success column: {list(rows[0].keys())}"
            )
        # Group by seed if present, otherwise treat all as one seed
        by_seed: dict[str, list[float]] = {}
        for row in rows:
            seed = str(row.get("seed", "0"))
            by_seed.setdefault(seed, []).append(_coerce_success(row[col]))
        per_seed = [statistics.fmean(vals) for vals in by_seed.values()]
        total_trials = sum(len(v) for v in by_seed.values())
        return {
            "per_seed_rates": per_seed,
            "total_trials": total_trials,
            "source": "trials.csv",
        }

    raise FileNotFoundError(
        f"No recognized results file in {exp_dir} "
        "(expected results.json, trials.csv, or seed_*/metrics.json)"
    )


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

def compute_stats(
    per_seed_rates: list[float],
    total_trials: int,
    venue: str,
) -> dict[str, Any]:
    n = len(per_seed_rates)
    if n == 0:
        mean = 0.0
        std = 0.0
        ci = [0.0, 0.0]
    else:
        mean = statistics.fmean(per_seed_rates)
        if n >= 2:
            std = statistics.stdev(per_seed_rates)
            sem = std / math.sqrt(n)
            tcrit = _t_critical_95(n - 1)
            ci = [mean - tcrit * sem, mean + tcrit * sem]
        else:
            std = 0.0
            ci = [mean, mean]

    threshold = VENUE_TRIAL_MINIMUMS.get(venue, 10)
    threshold_met = total_trials >= threshold
    return {
        "trials_per_condition": total_trials,
        "mean_success_rate": mean,
        "std_across_seeds": std,
        "ci_95": ci,
        "venue_threshold_met": threshold_met,
        "insufficient_trials": not threshold_met,
        "n_seeds": n,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("exp_dir", help="Experiment directory")
    parser.add_argument("--venue", default="RSS", help="Target venue")
    parser.add_argument(
        "--metric", default="success_rate", help="Metric key to audit"
    )
    args = parser.parse_args(argv)

    exp_dir = Path(args.exp_dir)
    try:
        loaded = load_experiment(exp_dir, args.metric)
    except FileNotFoundError as exc:
        print(json.dumps({"error": str(exc), "exp_dir": str(exp_dir)}))
        return 2
    except ValueError as exc:
        print(json.dumps({"error": str(exc), "exp_dir": str(exp_dir)}))
        return 2

    stats = compute_stats(
        loaded["per_seed_rates"],
        loaded["total_trials"],
        args.venue,
    )
    output = {
        "exp_dir": str(exp_dir),
        "venue": args.venue,
        "metric": args.metric,
        "source": loaded["source"],
        **stats,
    }
    print(json.dumps(output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
