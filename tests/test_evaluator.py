import pytest
from evaluator.core import evaluate_run
from evaluator.schemas import VerdictState, ReasonCode


def test_evaluate_run_feasible():
    """Test a run that successfully meets all SLO targets."""
    metrics = {
        "sample_count": 50,
        "ttft_p90": 150.0,
        "error_rate": 0.0,
        "oom_occurred": False
    }
    slo_spec = {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0
    }

    verdict = evaluate_run("run_001", "cand_01", metrics, slo_spec)

    assert verdict.state == VerdictState.FEASIBLE
    assert len(verdict.reasons) == 0


def test_evaluate_run_exact_boundary():
    """Test an exact boundary match (actual == target) which should pass."""
    metrics = {
        "sample_count": 50,
        "ttft_p90": 200.0,  # Exactly equals target max
        "error_rate": 0.0,
        "oom_occurred": False
    }
    slo_spec = {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0
    }

    verdict = evaluate_run("run_bound", "cand_01", metrics, slo_spec)

    assert verdict.state == VerdictState.FEASIBLE


def test_evaluate_run_infeasible_ttft():
    """Test a run that fails because TTFT exceeds the target."""
    metrics = {
        "sample_count": 50,
        "ttft_p90": 250.0,  # Exceeds max 200.0
        "error_rate": 0.0,
        "oom_occurred": False
    }
    slo_spec = {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0
    }

    verdict = evaluate_run("run_002", "cand_01", metrics, slo_spec)

    assert verdict.state == VerdictState.INFEASIBLE
    assert ReasonCode.TTFT_EXCEEDED in verdict.reasons


def test_evaluate_run_oom_crash():
    """Test that a GPU Out-Of-Memory flag immediately triggers INFEASIBLE."""
    metrics = {
        "sample_count": 50,
        "ttft_p90": 120.0,
        "error_rate": 0.0,
        "oom_occurred": True  # Crash flag triggered
    }
    slo_spec = {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0
    }

    verdict = evaluate_run("run_oom", "cand_01", metrics, slo_spec)

    assert verdict.state == VerdictState.INFEASIBLE
    assert ReasonCode.OOM_CRASH in verdict.reasons


def test_evaluate_run_inconclusive_low_samples():
    """Test a run that becomes inconclusive due to insufficient data samples."""
    metrics = {
        "sample_count": 3,  # Too low (min is 10)
        "ttft_p90": 120.0,
        "error_rate": 0.0,
        "oom_occurred": False
    }
    slo_spec = {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0
    }

    verdict = evaluate_run("run_003", "cand_01", metrics, slo_spec)

    assert verdict.state == VerdictState.INCONCLUSIVE
    assert ReasonCode.INSUFFICIENT_SAMPLES in verdict.reasons


def test_evaluate_run_missing_metrics():
    """Test that missing required metrics result in an INCONCLUSIVE state."""
    metrics = {
        "sample_count": 50,
        # "ttft_p90" is missing entirely!
        "error_rate": 0.0,
        "oom_occurred": False
    }
    slo_spec = {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0
    }

    verdict = evaluate_run("run_missing", "cand_01", metrics, slo_spec)

    assert verdict.state == VerdictState.INCONCLUSIVE
    assert ReasonCode.MISSING_METRICS in verdict.reasons

    
