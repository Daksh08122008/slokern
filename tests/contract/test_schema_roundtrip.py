"""
Purpose: Checks contract models serialize and validate round-trip, and reject unexpected fields.
Owner: Rajdeep
"""

import json
from typing import Any, Callable, Dict, List, Tuple, Type
import pytest
from pydantic import BaseModel, ValidationError

from slokern.contracts import (
    WorkloadSpec,
    SLOSpec,
    ExperimentSpec,
    CandidateConfig,
    RawRequestMeasurement,
    MetricSet,
    FeasibilityResult,
    RunRecord,
    SearchResult,
    VerificationRecord,
    ReportArtifact,
    SLOConstraint,
    ExperimentBudget,
    ExperimentVerificationPolicy,
    PercentileDistribution,
    ConstraintEvaluation,
    CandidateSummary,
    DriftAnalysis,
    BaselineSummary,
    SearchSummary,
    ArrivalMode,
    ExecutionStatus,
    EvidenceValidity,
    FeasibilityVerdict,
    VerificationState,
    RankingObjective,
    ParameterStatus,
    ReasonCode,
)


# ---------------------------------------------------------------------------
# Fixture factories for the 11 root models
# ---------------------------------------------------------------------------

def make_workload_spec() -> WorkloadSpec:
    return WorkloadSpec(
        schema_version="1.0.0",
        workload_name="llama-summarization",
        fixture_id="sha256_abcdef123456",
        arrival_mode=ArrivalMode.POISSON,
        target_offered_rate=15.5,
        concurrency_limit=32,
        warmup_duration_s=10,
        measurement_duration_s=60,
        max_input_tokens=1024,
        max_output_tokens=256,
    )


def make_slo_spec() -> SLOSpec:
    return SLOSpec(
        slo_id="slo-prod-summarize",
        constraints=[
            SLOConstraint(
                metric_name="ttft",
                statistic="p95",
                threshold=150.0,
                unit="ms",
                operator="<=",
            ),
            SLOConstraint(
                metric_name="request_throughput",
                statistic="mean",
                threshold=14.0,
                unit="requests/s",
                operator=">=",
            ),
        ],
        min_sample_count=100,
    )


def make_experiment_spec() -> ExperimentSpec:
    return ExperimentSpec(
        experiment_id="exp-20261021-001",
        workload=make_workload_spec(),
        slo=make_slo_spec(),
        search_space={
            "max_num_seqs": [16, 32, 64],
            "tensor_parallel_size": [1, 2],
        },
        budget=ExperimentBudget(
            max_candidates=4,
            max_wallclock_seconds=600,
            max_cost_limit=25.0,
        ),
        verification_policy=ExperimentVerificationPolicy(
            repetitions=2,
            duration_multiplier=1.5,
        ),
    )


def make_candidate_config() -> CandidateConfig:
    return CandidateConfig(
        candidate_id="cand-001a2b",
        model_name="meta-llama/Llama-3-8B-Instruct",
        runtime_name="vllm",
        requested_settings={"max_num_seqs": 32, "tensor_parallel_size": 1},
        effective_settings={"max_num_seqs": 32, "tensor_parallel_size": 1},
        parameter_status={
            "max_num_seqs": ParameterStatus.APPLIED,
            "tensor_parallel_size": ParameterStatus.APPLIED,
        },
        environment_fingerprint={
            "gpu_type": "NVIDIA-A100-SXM4-80GB",
            "driver_version": "535.104.05",
            "cuda_version": "12.2",
            "runtime_commit": "356c489",
        },
    )


def make_raw_request_measurement() -> RawRequestMeasurement:
    return RawRequestMeasurement(
        request_id="req-9876",
        run_id="run-exp1-c1",
        scheduled_at=1700000000.0,
        sent_at=1700000000.002,
        first_token_at=1700000000.045,
        completed_at=1700000000.220,
        http_status=200,
        input_tokens=512,
        output_tokens=128,
        itl_observations_ms=[1.2, 1.4, 1.3, 1.5],
        error_type=None,
        is_warmup=False,
        is_valid=True,
    )


def make_metric_set() -> MetricSet:
    return MetricSet(
        metric_version="1.0.0",
        run_id="run-exp1-c1",
        sample_count=200,
        failed_request_count=0,
        offered_load_rps=15.5,
        achieved_load_rps=15.48,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(
            p50=35.0, p90=48.0, p95=55.0, p99=72.0, mean=38.5, min=18.0, max=88.0
        ),
        itl_ms=PercentileDistribution(
            p50=3.2, p90=4.0, p95=4.5, p99=5.1, mean=3.4
        ),
        e2e_latency_ms=PercentileDistribution(
            p50=210.0, p90=260.0, p95=280.0, p99=320.0, mean=215.0
        ),
        request_throughput_rps=15.48,
        token_throughput_tps=1980.5,
        error_rate=0.0,
        metadata={"notes": "nominal execution"},
    )


def make_feasibility_result() -> FeasibilityResult:
    return FeasibilityResult(
        policy_version="1.0.0",
        run_id="run-exp1-c1",
        overall_verdict=FeasibilityVerdict.FEASIBLE,
        constraint_evaluations=[
            ConstraintEvaluation(
                metric_name="ttft",
                statistic="p95",
                observed_value=55.0,
                required_threshold=150.0,
                operator="<=",
                passed=True,
                reason_code=ReasonCode.HARD_CONSTRAINTS_PASSED,
            ),
            ConstraintEvaluation(
                metric_name="request_throughput",
                statistic="mean",
                observed_value=15.48,
                required_threshold=14.0,
                operator=">=",
                passed=True,
                reason_code=ReasonCode.HARD_CONSTRAINTS_PASSED,
            ),
        ],
        validity_status=EvidenceValidity.VALID,
        audit_notes="All declared hard SLO constraints met.",
    )


def make_run_record() -> RunRecord:
    return RunRecord(
        run_id="run-exp1-c1",
        experiment_id="exp-20261021-001",
        candidate_id="cand-001a2b",
        is_verification_run=False,
        execution_status=ExecutionStatus.COMPLETED,
        started_at="2026-10-21T20:00:00.000000Z",
        completed_at="2026-10-21T20:01:10.000000Z",
        raw_artifact_uri="runs/run-exp1-c1/raw_requests.jsonl",
        execution_error=None,
    )


def make_search_result() -> SearchResult:
    return SearchResult(
        experiment_id="exp-20261021-001",
        baseline_candidate_id="cand-base",
        tested_candidates=["cand-base", "cand-001a2b", "cand-002c3d"],
        candidate_summaries={
            "cand-base": CandidateSummary(verdict=FeasibilityVerdict.FEASIBLE, ranking_metric=20.0),
            "cand-001a2b": CandidateSummary(verdict=FeasibilityVerdict.FEASIBLE, ranking_metric=12.5),
            "cand-002c3d": CandidateSummary(verdict=FeasibilityVerdict.INFEASIBLE, ranking_metric=8.0),
        },
        ranking_objective=RankingObjective.MONETARY_COST_PER_TOKEN,
        selected_candidate_id="cand-001a2b",
        selection_rationale="Lowest cost feasible candidate within tested configuration space.",
        stopping_reason="space_exhausted",
    )


def make_verification_record() -> VerificationRecord:
    return VerificationRecord(
        verification_id="ver-exp1-v1",
        experiment_id="exp-20261021-001",
        candidate_id="cand-001a2b",
        original_run_id="run-exp1-c1",
        verification_run_id="run-exp1-v1",
        verification_verdict=VerificationState.VERIFIED,
        drift_analysis=DriftAnalysis(
            metric_deltas={"ttft_p95": 0.018, "throughput": -0.005},
            slo_drift_detected=False,
        ),
        final_decision_notes="Verification confirmed candidate feasibility with minimal latency drift.",
    )


def make_report_artifact() -> ReportArtifact:
    return ReportArtifact(
        report_id="rep-exp1-final",
        created_at="2026-10-21T20:10:00Z",
        experiment_spec=make_experiment_spec(),
        environment_fingerprint={
            "gpu_type": "NVIDIA-A100-SXM4-80GB",
            "driver_version": "535.104.05",
            "cuda_version": "12.2",
            "runtime_commit": "356c489",
        },
        baseline_summary=BaselineSummary(
            baseline_candidate_id="cand-base",
            verdict=FeasibilityVerdict.FEASIBLE,
            metrics={"ttft_p95_ms": 65.0, "throughput_rps": 12.0},
        ),
        search_summary=SearchSummary(
            tested_candidates=["cand-base", "cand-001a2b", "cand-002c3d"],
            rejected_options=["cand-002c3d"],
            rankings=["cand-001a2b", "cand-base"],
        ),
        selected_candidate=make_candidate_config(),
        verification_record=make_verification_record(),
        limitations_disclosed={
            "tested_batch_sizes": [16, 32, 64],
            "single_node_only": True,
            "pricing_source": "Nebius cloud hourly standard GPU rate",
        },
        cost_accounting_basis="hourly GPU instance list price $2.50/hr",
        artifact_paths={
            "search_history": "runs/search.json",
            "raw_measurements": "runs/run-exp1-c1/raw_requests.jsonl",
            "verification_raw": "runs/run-exp1-v1/raw_requests.jsonl",
        },
    )


ROOT_MODEL_FACTORIES: List[Tuple[Type[BaseModel], Callable[[], BaseModel]]] = [
    (WorkloadSpec, make_workload_spec),
    (SLOSpec, make_slo_spec),
    (ExperimentSpec, make_experiment_spec),
    (CandidateConfig, make_candidate_config),
    (RawRequestMeasurement, make_raw_request_measurement),
    (MetricSet, make_metric_set),
    (FeasibilityResult, make_feasibility_result),
    (RunRecord, make_run_record),
    (SearchResult, make_search_result),
    (VerificationRecord, make_verification_record),
    (ReportArtifact, make_report_artifact),
]


# ---------------------------------------------------------------------------
# Tests: Roundtrip Serialization & Deserialization across all 11 Root Models
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model_cls,factory", ROOT_MODEL_FACTORIES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_model_json_string_roundtrip(model_cls: Type[BaseModel], factory: Callable[[], BaseModel]):
    """Assert model_dump_json() and model_validate_json() round-trip with full equality."""
    original = factory()
    json_str = original.model_dump_json()

    # Valid JSON string check
    parsed = json.loads(json_str)
    assert isinstance(parsed, dict)

    restored = model_cls.model_validate_json(json_str)
    assert restored == original
    assert hash(restored) == hash(original) if original.model_config.get("frozen", False) else True


@pytest.mark.parametrize("model_cls,factory", ROOT_MODEL_FACTORIES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_model_dict_json_mode_roundtrip(model_cls: Type[BaseModel], factory: Callable[[], BaseModel]):
    """Assert model_dump(mode='json') and model_validate() round-trip with full equality."""
    original = factory()
    data = original.model_dump(mode="json")
    restored = model_cls.model_validate(data)
    assert restored == original


@pytest.mark.parametrize("model_cls,factory", ROOT_MODEL_FACTORIES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_model_dict_python_mode_roundtrip(model_cls: Type[BaseModel], factory: Callable[[], BaseModel]):
    """Assert model_dump() and model_validate() in python mode round-trip with full equality."""
    original = factory()
    data = original.model_dump()
    restored = model_cls.model_validate(data)
    assert restored == original


# ---------------------------------------------------------------------------
# Tests: Extra Fields Rejection (ConfigDict(extra='forbid')) across Root Models
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("model_cls,factory", ROOT_MODEL_FACTORIES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_model_rejects_extra_fields_on_instantiation(model_cls: Type[BaseModel], factory: Callable[[], BaseModel]):
    """Assert passing unexpected kwargs directly to model constructor raises ValidationError."""
    instance = factory()
    data = instance.model_dump()
    data["unexpected_forbidden_field"] = "malicious_payload"

    with pytest.raises(ValidationError) as exc_info:
        model_cls(**data)

    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "unexpected_forbidden_field" in err.get("loc", ())
        for err in errors
    ), f"Expected extra_forbidden error for unexpected_forbidden_field, got: {errors}"


@pytest.mark.parametrize("model_cls,factory", ROOT_MODEL_FACTORIES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_model_rejects_extra_fields_on_model_validate(model_cls: Type[BaseModel], factory: Callable[[], BaseModel]):
    """Assert passing dict with unknown fields to model_validate raises ValidationError."""
    instance = factory()
    data = instance.model_dump(mode="json")
    data["bogus_extra_key"] = 99999

    with pytest.raises(ValidationError) as exc_info:
        model_cls.model_validate(data)

    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "bogus_extra_key" in err.get("loc", ())
        for err in errors
    ), f"Expected extra_forbidden error for bogus_extra_key, got: {errors}"


@pytest.mark.parametrize("model_cls,factory", ROOT_MODEL_FACTORIES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_model_rejects_extra_fields_on_model_validate_json(model_cls: Type[BaseModel], factory: Callable[[], BaseModel]):
    """Assert passing JSON string with unknown fields to model_validate_json raises ValidationError."""
    instance = factory()
    data = instance.model_dump(mode="json")
    data["unauthorized_injected_field"] = True
    bad_json = json.dumps(data)

    with pytest.raises(ValidationError) as exc_info:
        model_cls.model_validate_json(bad_json)

    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "unauthorized_injected_field" in err.get("loc", ())
        for err in errors
    ), f"Expected extra_forbidden error for unauthorized_injected_field, got: {errors}"


# ---------------------------------------------------------------------------
# Tests: Extra Fields Rejection in Nested Submodels
# ---------------------------------------------------------------------------

SUBMODEL_CASES: List[Tuple[Type[BaseModel], Dict[str, Any]]] = [
    (
        SLOConstraint,
        {"metric_name": "ttft", "statistic": "p95", "threshold": 100.0, "unit": "ms", "operator": "<="},
    ),
    (
        ExperimentBudget,
        {"max_candidates": 5, "max_wallclock_seconds": 300, "max_cost_limit": 10.0},
    ),
    (
        ExperimentVerificationPolicy,
        {"repetitions": 1, "duration_multiplier": 1.0},
    ),
    (
        PercentileDistribution,
        {"p50": 10.0, "p95": 20.0},
    ),
    (
        ConstraintEvaluation,
        {
            "metric_name": "ttft",
            "statistic": "p95",
            "observed_value": 50.0,
            "required_threshold": 100.0,
            "operator": "<=",
            "passed": True,
            "reason_code": ReasonCode.HARD_CONSTRAINTS_PASSED,
        },
    ),
    (
        CandidateSummary,
        {"verdict": FeasibilityVerdict.FEASIBLE, "ranking_metric": 5.0},
    ),
    (
        DriftAnalysis,
        {"metric_deltas": {"ttft": 0.05}, "slo_drift_detected": False},
    ),
    (
        BaselineSummary,
        {"baseline_candidate_id": "c0", "verdict": FeasibilityVerdict.FEASIBLE, "metrics": {}},
    ),
    (
        SearchSummary,
        {"tested_candidates": ["c0"], "rejected_options": [], "rankings": ["c0"]},
    ),
]


@pytest.mark.parametrize("submodel_cls,valid_dict", SUBMODEL_CASES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_submodel_json_string_roundtrip(submodel_cls: Type[BaseModel], valid_dict: Dict[str, Any]):
    """Assert all 9 submodels round-trip via model_dump_json and model_validate_json."""
    original = submodel_cls(**valid_dict)
    json_str = original.model_dump_json()
    restored = submodel_cls.model_validate_json(json_str)
    assert restored == original


@pytest.mark.parametrize("submodel_cls,valid_dict", SUBMODEL_CASES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_submodel_dict_roundtrip(submodel_cls: Type[BaseModel], valid_dict: Dict[str, Any]):
    """Assert all 9 submodels round-trip via model_dump and model_validate."""
    original = submodel_cls(**valid_dict)
    dumped = original.model_dump(mode="json")
    restored = submodel_cls.model_validate(dumped)
    assert restored == original


@pytest.mark.parametrize("submodel_cls,valid_dict", SUBMODEL_CASES, ids=lambda pair: pair[0].__name__ if isinstance(pair, tuple) else str(pair))
def test_submodel_rejects_extra_fields(submodel_cls: Type[BaseModel], valid_dict: Dict[str, Any]):
    """Assert all helper/nested contract submodels strictly forbid extra fields on instantiation and validation."""
    bad_dict = dict(valid_dict)
    bad_dict["unknown_submodel_attr"] = "invalid"

    # Test constructor instantiation rejection
    with pytest.raises(ValidationError) as exc_info:
        submodel_cls(**bad_dict)
    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "unknown_submodel_attr" in err.get("loc", ())
        for err in errors
    ), f"Expected extra_forbidden error on constructor in {submodel_cls.__name__}, got: {errors}"

    # Test model_validate rejection
    with pytest.raises(ValidationError) as exc_info:
        submodel_cls.model_validate(bad_dict)
    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "unknown_submodel_attr" in err.get("loc", ())
        for err in errors
    ), f"Expected extra_forbidden error on validate in {submodel_cls.__name__}, got: {errors}"


def test_nested_extra_field_rejected_in_experiment_spec():
    """Injecting unknown field into nested WorkloadSpec within ExperimentSpec must fail validation."""
    exp = make_experiment_spec()
    data = exp.model_dump(mode="json")
    data["workload"]["injected_workload_field"] = "bad"

    with pytest.raises(ValidationError) as exc_info:
        ExperimentSpec.model_validate(data)

    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "injected_workload_field" in err.get("loc", ())
        for err in errors
    )


def test_nested_extra_field_rejected_in_metric_set():
    """Injecting unknown field into nested PercentileDistribution within MetricSet must fail."""
    metrics = make_metric_set()
    data = metrics.model_dump(mode="json")
    data["ttft_ms"]["p999"] = 999.0

    with pytest.raises(ValidationError) as exc_info:
        MetricSet.model_validate(data)

    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "p999" in err.get("loc", ())
        for err in errors
    )


def test_nested_extra_field_rejected_in_report_artifact():
    """Injecting unknown field into nested BaselineSummary within ReportArtifact must fail."""
    report = make_report_artifact()
    data = report.model_dump(mode="json")
    data["baseline_summary"]["unexpected_metric_audit"] = 123.45

    with pytest.raises(ValidationError) as exc_info:
        ReportArtifact.model_validate(data)

    errors = exc_info.value.errors()
    assert any(
        err.get("type") == "extra_forbidden" and "unexpected_metric_audit" in err.get("loc", ())
        for err in errors
    )


def test_nullable_and_edge_case_roundtrip():
    """Assert models with nullable optional fields (nulls vs populated) round-trip cleanly."""
    # SearchResult with no winning feasible candidate (selected_candidate_id=None)
    sr_none = SearchResult(
        experiment_id="exp-infeasible",
        baseline_candidate_id="cand-base",
        tested_candidates=["cand-base"],
        candidate_summaries={"cand-base": CandidateSummary(verdict=FeasibilityVerdict.INFEASIBLE, ranking_metric=None)},
        ranking_objective=RankingObjective.MONETARY_COST_PER_TOKEN,
        selected_candidate_id=None,
        selection_rationale="No candidates met required hard SLO constraints.",
        stopping_reason="budget_exhausted",
    )
    sr_restored = SearchResult.model_validate_json(sr_none.model_dump_json())
    assert sr_restored == sr_none
    assert sr_restored.selected_candidate_id is None

    # ReportArtifact with no winning candidate and no verification
    report_none = ReportArtifact(
        report_id="rep-infeasible-final",
        created_at="2026-10-21T20:10:00Z",
        experiment_spec=make_experiment_spec(),
        environment_fingerprint={"gpu": "A100"},
        baseline_summary=BaselineSummary(
            baseline_candidate_id="cand-base",
            verdict=FeasibilityVerdict.INFEASIBLE,
            metrics={},
        ),
        search_summary=SearchSummary(
            tested_candidates=["cand-base"],
            rejected_options=["cand-base"],
            rankings=[],
        ),
        selected_candidate=None,
        verification_record=None,
        limitations_disclosed={"bounds": "single-node"},
        cost_accounting_basis="hourly GPU list price",
        artifact_paths={},
    )
    rep_restored = ReportArtifact.model_validate_json(report_none.model_dump_json())
    assert rep_restored == report_none
    assert rep_restored.selected_candidate is None
    assert rep_restored.verification_record is None

    # RawRequestMeasurement with nulls and error type (e.g. failed request)
    meas_failed = RawRequestMeasurement(
        request_id="req-err-01",
        run_id="run-err",
        scheduled_at=1700000000.0,
        sent_at=1700000000.01,
        first_token_at=None,
        completed_at=1700000000.5,
        http_status=500,
        input_tokens=100,
        output_tokens=0,
        itl_observations_ms=None,
        error_type="OOM",
        is_warmup=True,
        is_valid=False,
    )
    meas_restored = RawRequestMeasurement.model_validate_json(meas_failed.model_dump_json())
    assert meas_restored == meas_failed
    assert meas_restored.first_token_at is None
    assert meas_restored.itl_observations_ms is None
    assert meas_restored.error_type == "OOM"
    assert meas_restored.is_valid is False
