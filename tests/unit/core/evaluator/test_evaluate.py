"""
Purpose: Unit tests for core/evaluator/evaluate.
Owner: Rajdeep (Historical design: Daksh)
"""

import math

from slokern.core.evaluator.evaluate import evaluate_constraint


def test_evaluate_constraint_valid_operators() -> None:
    """Test evaluate_constraint with valid values and operators."""
    # <=
    assert evaluate_constraint(10.0, 15.0, "<=") is True
    assert evaluate_constraint(15.0, 15.0, "<=") is True
    assert evaluate_constraint(20.0, 15.0, "<=") is False

    # <
    assert evaluate_constraint(10.0, 15.0, "<") is True
    assert evaluate_constraint(15.0, 15.0, "<") is False
    assert evaluate_constraint(20.0, 15.0, "<") is False

    # >=
    assert evaluate_constraint(20.0, 15.0, ">=") is True
    assert evaluate_constraint(15.0, 15.0, ">=") is True
    assert evaluate_constraint(10.0, 15.0, ">=") is False

    # >
    assert evaluate_constraint(20.0, 15.0, ">") is True
    assert evaluate_constraint(15.0, 15.0, ">") is False
    assert evaluate_constraint(10.0, 15.0, ">") is False

def test_evaluate_constraint_none_values() -> None:
    """Test evaluate_constraint with None values."""
    assert evaluate_constraint(None, 10.0, "<=") is None
    assert evaluate_constraint(10.0, None, "<=") is None  # type: ignore[arg-type]
    assert evaluate_constraint(None, None, "<=") is None  # type: ignore[arg-type]

def test_evaluate_constraint_boolean_values() -> None:
    """Test evaluate_constraint with boolean values."""
    assert evaluate_constraint(True, 10.0, "<=") is None
    assert evaluate_constraint(False, 10.0, "<=") is None
    assert evaluate_constraint(10.0, True, "<=") is None
    assert evaluate_constraint(10.0, False, "<=") is None

def test_evaluate_constraint_negative_values() -> None:
    """Test evaluate_constraint with negative values."""
    assert evaluate_constraint(-1.0, 10.0, "<=") is None
    assert evaluate_constraint(10.0, -1.0, "<=") is None
    assert evaluate_constraint(-1.0, -1.0, "<=") is None

def test_evaluate_constraint_non_finite_values() -> None:
    """Test evaluate_constraint with non-finite values (NaN, Inf)."""
    assert evaluate_constraint(math.nan, 10.0, "<=") is None
    assert evaluate_constraint(10.0, math.nan, "<=") is None

    assert evaluate_constraint(math.inf, 10.0, "<=") is None
    assert evaluate_constraint(10.0, math.inf, "<=") is None

    assert evaluate_constraint(-math.inf, 10.0, "<=") is None
    assert evaluate_constraint(10.0, -math.inf, "<=") is None

def test_evaluate_constraint_unsupported_operators() -> None:
    """Test evaluate_constraint with unsupported operators."""
    assert evaluate_constraint(10.0, 15.0, "==") is None
    assert evaluate_constraint(10.0, 15.0, "!=") is None
    assert evaluate_constraint(10.0, 15.0, "abc") is None
    assert evaluate_constraint(10.0, 15.0, "") is None
