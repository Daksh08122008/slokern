import pytest

from evaluator.schemas import ReasonCode, VerdictState
from verification.runner import IndependentVerificationRunner


@pytest.fixture
def valid_metrics():
    return {
        "sample_count": 50,
        "ttft_p90": 100.0,
        "error_rate": 0.0,
        "oom_occurred": False,
    }


@pytest.fixture
def slo_spec():
    return {
        "min_samples": 10,
        "max_ttft_ms": 200.0,
        "max_error_rate": 0.0,
    }


@pytest.mark.parametrize(
    "original_metrics",
    [
        {"sample_count": 50, "error_rate": 0.0},
        {"sample_count": 50, "ttft_p90": None, "error_rate": 0.0},
    ],
)
def test_missing_original_ttft_is_inconclusive(valid_metrics, slo_spec, original_metrics):
    runner = IndependentVerificationRunner(lambda config: valid_metrics)

    verdict = runner.verify_winner(
        "candidate-1", {}, slo_spec, original_metrics
    )

    assert verdict.state == VerdictState.INCONCLUSIVE
    assert ReasonCode.MISSING_METRICS in verdict.reasons


@pytest.mark.parametrize("ttft", [0.0, -1.0, float("nan"), "100"])
def test_invalid_original_ttft_is_inconclusive(valid_metrics, slo_spec, ttft):
    runner = IndependentVerificationRunner(lambda config: valid_metrics)

    verdict = runner.verify_winner(
        "candidate-1",
        {},
        slo_spec,
        {"sample_count": 50, "ttft_p90": ttft},
    )

    assert verdict.state == VerdictState.INCONCLUSIVE
    assert ReasonCode.INVALID_METRICS in verdict.reasons


def test_benchmark_exception_is_not_misreported_as_slo_failure(slo_spec, valid_metrics):
    def fail_benchmark(config):
        raise RuntimeError("benchmark unavailable")

    runner = IndependentVerificationRunner(fail_benchmark)

    with pytest.raises(RuntimeError, match="benchmark unavailable"):
        runner.verify_winner("candidate-1", {}, slo_spec, valid_metrics)


def test_excessive_ttft_drift_has_an_explicit_reason(slo_spec):
    fresh_metrics = {
        "sample_count": 50,
        "ttft_p90": 106.0,
        "error_rate": 0.0,
        "oom_occurred": False,
    }
    runner = IndependentVerificationRunner(lambda config: fresh_metrics)

    verdict = runner.verify_winner(
        "candidate-1",
        {},
        slo_spec,
        {"sample_count": 50, "ttft_p90": 100.0},
    )

    assert verdict.state == VerdictState.INFEASIBLE
    assert ReasonCode.TTFT_DRIFT_EXCEEDED in verdict.reasons


@pytest.mark.parametrize("tolerance", [-1.0, float("inf"), float("nan")])
def test_invalid_drift_tolerance_is_rejected(slo_spec, valid_metrics, tolerance):
    runner = IndependentVerificationRunner(lambda config: valid_metrics)

    with pytest.raises(ValueError, match="drift_tolerance_pct"):
        runner.verify_winner(
            "candidate-1", {}, slo_spec, valid_metrics, tolerance
        )
