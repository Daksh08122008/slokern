import pytest
from typing import Any
from pydantic import ValidationError
from slokern.contracts.report import BaselineSummary, SearchSummary, ReportArtifact
from slokern.contracts.enums import FeasibilityVerdict
from slokern.contracts.spec import ExperimentSpec, WorkloadSpec, SLOSpec, ExperimentBudget, ExperimentVerificationPolicy
from slokern.contracts.enums import ArrivalMode

def make_workload_spec() -> WorkloadSpec:
    return WorkloadSpec(
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

def make_slo_spec() -> SLOSpec:
    return SLOSpec(
        slo_id="slo-1",
        constraints=[],
        min_sample_count=30
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


def test_baseline_summary_valid() -> None:
    summary = BaselineSummary(
        baseline_candidate_id="cand-base",
        verdict=FeasibilityVerdict.FEASIBLE,
        metrics={"ttft_p95": 100.0}
    )
    assert summary.baseline_candidate_id == "cand-base"
    assert summary.verdict == FeasibilityVerdict.FEASIBLE
    assert summary.metrics == {"ttft_p95": 100.0}

def test_baseline_summary_extra_fields() -> None:
    with pytest.raises(ValidationError):
        BaselineSummary(
            baseline_candidate_id="cand-base",
            verdict=FeasibilityVerdict.FEASIBLE,
            metrics={},
            extra_field="should fail"  # type: ignore[call-arg]
        )

def test_search_summary_valid() -> None:
    summary = SearchSummary(
        tested_candidates=["cand-1", "cand-2"],
        rejected_options=["cand-3"],
        rankings=["cand-2", "cand-1"]
    )
    assert summary.tested_candidates == ["cand-1", "cand-2"]
    assert summary.rejected_options == ["cand-3"]
    assert summary.rankings == ["cand-2", "cand-1"]

def test_search_summary_extra_fields() -> None:
    with pytest.raises(ValidationError):
        SearchSummary(
            tested_candidates=[],
            rejected_options=[],
            rankings=[],
            extra_field="should fail"  # type: ignore[call-arg]
        )

def test_report_artifact_valid() -> None:
    report = ReportArtifact(
        report_id="rep-123",
        created_at="2023-10-27T10:00:00Z",
        experiment_spec=make_experiment_spec(),
        environment_fingerprint={"gpu": "H100"},
        baseline_summary=BaselineSummary(
            baseline_candidate_id="cand-base",
            verdict=FeasibilityVerdict.FEASIBLE,
            metrics={}
        ),
        search_summary=SearchSummary(
            tested_candidates=[],
            rejected_options=[],
            rankings=[]
        ),
        limitations_disclosed={"bounds": "tested"},
        cost_accounting_basis="aws-on-demand",
        artifact_paths={"logs": "/path/to/logs"}
    )
    assert report.report_id == "rep-123"

def test_report_artifact_extra_fields() -> None:
    with pytest.raises(ValidationError):
        ReportArtifact(
            report_id="rep-123",
            created_at="2023-10-27T10:00:00Z",
            experiment_spec=make_experiment_spec(),
            environment_fingerprint={"gpu": "H100"},
            baseline_summary=BaselineSummary(
                baseline_candidate_id="cand-base",
                verdict=FeasibilityVerdict.FEASIBLE,
                metrics={}
            ),
            search_summary=SearchSummary(
                tested_candidates=[],
                rejected_options=[],
                rankings=[]
            ),
            limitations_disclosed={"bounds": "tested"},
            cost_accounting_basis="aws-on-demand",
            artifact_paths={"logs": "/path/to/logs"},
            extra_field="should fail"  # type: ignore[call-arg]
        )
