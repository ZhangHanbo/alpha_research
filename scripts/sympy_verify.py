#!/usr/bin/env python
"""Verify symbolic properties of a mathematical expression.

Usage
-----
    python scripts/sympy_verify.py \
        --expr "(x-2*y)**2 + exp(x)" \
        --property convex \
        --vars "x,y"

Supported properties: ``convex``, ``concave``, ``differentiable``.

Emits a single JSON object to stdout::

    {"expression": "...", "property": "convex", "vars": ["x", "y"],
     "result": true | false | "unknown",
     "reason": "Hessian PSD / not PSD / symbolic check failed"}

The script avoids any heavy numerics — pure sympy is used. When a
symbolic proof is not possible, we fall back to a few random numeric
samples before reporting ``"unknown"``.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from typing import Any

import sympy as sp


SUPPORTED_PROPERTIES = {"convex", "concave", "differentiable"}


def _parse_vars(vars_str: str) -> list[sp.Symbol]:
    names = [v.strip() for v in vars_str.split(",") if v.strip()]
    return [sp.Symbol(n, real=True) for n in names]


def _check_differentiable(
    expr: sp.Expr, variables: list[sp.Symbol]
) -> tuple[Any, str]:
    """Attempt to verify differentiability of ``expr`` w.r.t. ``variables``.

    For the purposes of this helper, we call an expression "differentiable"
    if every first-order partial derivative exists symbolically and is
    itself a sympy expression (no ``Piecewise`` or ``Derivative`` left
    unevaluated).
    """
    try:
        for var in variables:
            deriv = sp.diff(expr, var)
            if deriv.has(sp.Derivative):
                return False, f"partial derivative w.r.t. {var} did not evaluate"
            if deriv.has(sp.Abs) or deriv.has(sp.sign):
                return False, f"derivative w.r.t. {var} contains non-smooth functions"
    except Exception as exc:  # pragma: no cover — defensive
        return "unknown", f"symbolic differentiation failed: {exc}"
    return True, "all first-order partials evaluate symbolically"


def _hessian_psd(
    expr: sp.Expr,
    variables: list[sp.Symbol],
    negate: bool = False,
) -> tuple[Any, str]:
    """Check whether the Hessian of ``expr`` is positive-semidefinite.

    If ``negate`` is True, check negative-semidefiniteness (for concavity).
    """
    try:
        H = sp.hessian(expr, variables)
    except Exception as exc:
        return "unknown", f"hessian computation failed: {exc}"

    if negate:
        H = -H

    # Try symbolic eigenvalues
    try:
        eigs = list(H.eigenvals().keys())
    except Exception:
        eigs = None

    if eigs is not None:
        all_nonneg = True
        any_negative = False
        for e in eigs:
            e_simp = sp.simplify(e)
            # Try to prove >= 0
            try:
                nonneg = sp.ask(sp.Q.nonnegative(e_simp))
            except Exception:
                nonneg = None
            if nonneg is True:
                continue
            # Direct sign check for concrete numbers
            if e_simp.is_number:
                if e_simp >= 0:
                    continue
                else:
                    any_negative = True
                    all_nonneg = False
                    break
            all_nonneg = False
        if any_negative:
            return False, "Hessian has a strictly negative eigenvalue"
        if all_nonneg:
            return True, "Hessian PSD (all eigenvalues proved >= 0)"

    # Fallback: numeric sampling at a few points
    rng = random.Random(0)
    n = len(variables)
    negative_seen = False
    for _ in range(20):
        subs = {v: rng.uniform(-2.0, 2.0) for v in variables}
        try:
            H_num = H.subs(subs)
            # Compute numeric eigenvalues via sympy
            H_float = sp.Matrix(H_num).evalf()
            eigvals = list(H_float.eigenvals().keys())
        except Exception:
            continue
        for ev in eigvals:
            ev_f = sp.re(sp.N(ev))
            if float(ev_f) < -1e-9:
                negative_seen = True
                break
        if negative_seen:
            break

    if negative_seen:
        return False, "Hessian not PSD at sampled point"
    return "unknown", "symbolic PSD proof failed; numeric samples inconclusive"


def verify(expr_str: str, prop: str, vars_str: str) -> dict[str, Any]:
    if prop not in SUPPORTED_PROPERTIES:
        raise ValueError(
            f"Unsupported property {prop!r}. Supported: {sorted(SUPPORTED_PROPERTIES)}"
        )

    variables = _parse_vars(vars_str)
    local_dict = {v.name: v for v in variables}
    try:
        expr = sp.sympify(expr_str, locals=local_dict)
    except (sp.SympifyError, SyntaxError, TypeError) as exc:
        return {
            "expression": expr_str,
            "property": prop,
            "vars": [v.name for v in variables],
            "result": "unknown",
            "reason": f"could not parse expression: {exc}",
        }

    if prop == "convex":
        result, reason = _hessian_psd(expr, variables, negate=False)
    elif prop == "concave":
        result, reason = _hessian_psd(expr, variables, negate=True)
    elif prop == "differentiable":
        result, reason = _check_differentiable(expr, variables)
    else:  # pragma: no cover — guarded above
        raise ValueError(prop)

    return {
        "expression": expr_str,
        "property": prop,
        "vars": [v.name for v in variables],
        "result": result,
        "reason": reason,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expr", required=True, help="SymPy expression string")
    parser.add_argument(
        "--property",
        required=True,
        choices=sorted(SUPPORTED_PROPERTIES),
        help="Property to verify",
    )
    parser.add_argument(
        "--vars",
        default="x",
        help="Comma-separated variable names (default: 'x')",
    )
    args = parser.parse_args(argv)

    try:
        result = verify(args.expr, args.property, args.vars)
    except ValueError as exc:
        print(
            json.dumps({"error": str(exc)}),
            file=sys.stdout,
        )
        return 2

    print(json.dumps(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
