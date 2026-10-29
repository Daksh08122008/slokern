import pytest
from pydantic import ValidationError

from slokern.contracts import (
    ArrivalMode,
    EvidenceValidity,
    FeasibilityResult,
    FeasibilityVerdict,
    MetricSet,
    RawRequestMeasurement,
    ReasonCode,
    SLOSpec,
    WorkloadSpec,
)


def test_workload_spec_valid():
    spec = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="test_workload",
        fixture_id="hash_123",
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=10.0,
        concurrency_limit=50,
        warmup_duration_s=15,
        measurement_duration_s=60,
        max_input_tokens=512,
        max_output_tokens=128
    )
    assert spec.workload_name == "test_workload"
    assert spec.arrival_mode == ArrivalMode.POISSON

def test_workload_spec_invalid_mode():
    with pytest.raises(ValidationError):
        WorkloadSpec(
            schema_version="1.0.0",
            workload_name="test",
            fixture_id="123",
            arrival_mode="invalid",
            target_offered_rate=10.0,
            concurrency_limit=50,
            warmup_duration_s=15,
            measurement_duration_s=60,
            max_input_tokens=512,
            max_output_tokens=128
        )

def test_slo_spec_valid():
    slo = SLOSpec(
        slo_id="slo-1",
        constraints=[
            {
                "metric_name": "ttft",
                "statistic": "p95",
                "threshold": 200.0,
                "unit": "ms",
                "operator": "<="
            }
        ],
        min_sample_count=30
    )
    assert slo.slo_id == "slo-1"
    assert len(slo.constraints) == 1

def test_raw_request_measurement_valid():
    meas = RawRequestMeasurement(
        request_id="req-1",
        run_id="run-1",
        scheduled_at=1.0,
        sent_at=1.1,
        first_token_at=1.2,
        completed_at=1.5,
        http_status=200,
        input_tokens=100,
        output_tokens=50,
        is_warmup=False,
        is_valid=True
    )
    assert meas.request_id == "req-1"

def test_metric_set_serialization():
    m = MetricSet(
        metric_version="1.0.0",
        run_id="run-1",
        sample_count=100,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=9.9,
        generator_saturated=False,
        ttft_ms={"p50": 100.0, "p95": 200.0},
        itl_ms={"p50": 10.0, "p95": 20.0},
        e2e_latency_ms={"p50": 500.0},
        request_throughput_rps=9.9,
        token_throughput_tps=500.0,
        error_rate=0.0
    )
    data = m.model_dump()
    assert data["run_id"] == "run-1"
    assert data["ttft_ms"]["p50"] == 100.0

def test_feasibility_result_valid():
    res = FeasibilityResult(
        policy_version="1.0.0",
        run_id="run-1",
        overall_verdict=FeasibilityVerdict.INFEASIBLE,
        constraint_evaluations=[
            {
                "metric_name": "ttft",
                "statistic": "p95",
                "observed_value": 250.0,
                "required_threshold": 200.0,
                "operator": "<=",
                "passed": False,
                "reason_code": ReasonCode.TTFT_P95_EXCEEDED
            }
        ],
        validity_status=EvidenceValidity.VALID
    )
    assert res.overall_verdict == FeasibilityVerdict.INFEASIBLE
