"""Tests for scripts/sympy_verify.py."""

from __future__ import annotations

import json

import pytest

import sympy_verify


def test_known_convex_x2_plus_y2() -> None:
    result = sympy_verify.verify("x**2 + y**2", "convex", "x,y")
    assert result["result"] is True
    assert "PSD" in result["reason"]


def test_non_convex_negative_quadratic() -> None:
    # -x**2 - y**2 has a negative definite Hessian -> not convex
    result = sympy_verify.verify("-x**2 - y**2", "convex", "x,y")
    assert result["result"] is False


def test_differentiable_sin_x() -> None:
    result = sympy_verify.verify("sin(x)", "differentiable", "x")
    assert result["result"] is True


def test_non_differentiable_abs() -> None:
    result = sympy_verify.verify("Abs(x)", "differentiable", "x")
    assert result["result"] is False


def test_unknown_property_raises() -> None:
    with pytest.raises(ValueError):
        sympy_verify.verify("x**2", "bogus_property", "x")


def test_cli_main_outputs_json(capsys) -> None:
    rc = sympy_verify.main(["--expr", "x**2", "--property", "convex", "--vars", "x"])
    assert rc == 0
    out = capsys.readouterr().out.strip()
    data = json.loads(out)
    assert data["result"] is True
    assert data["expression"] == "x**2"
    assert data["vars"] == ["x"]


def test_concave_negative_quadratic() -> None:
    result = sympy_verify.verify("-(x**2 + y**2)", "concave", "x,y")
    assert result["result"] is True
