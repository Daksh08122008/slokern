"""
Purpose: Unit tests for engine/reporting/report_builder: ReportArtifact compilation and Markdown rendering.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with AGENTS.md Section 1, 3, 5, 8
"""

import json
from pathlib import Path

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    FeasibilityVerdict,
    VerificationState,
)
from slokern.contracts.report import BaselineSummary, ReportArtifact, SearchSummary
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOConstraint,
    SLOSpec,
    WorkloadSpec,
)
from slokern.contracts.verification import DriftAnalysis, VerificationRecord
from slokern.engine.reporting.report_builder import (
    build_report_artifact,
    render_markdown_report,
    write_report_artifacts,
)


@pytest.fixture
def mock_experiment_spec() -> ExperimentSpec:
    workload = WorkloadSpec(
        schema_version="1.0.0",
        workload_name="reporting-workload",
        fixture_id="fix-rep-01",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=4,
        warmup_duration_s=1,
        measurement_duration_s=1,
        max_input_tokens=128,
        max_output_tokens=32,
    )
    slo = SLOSpec(
        slo_id="slo-reporting",
        min_sample_count=2,
        constraints=[
            SLOConstraint(metric_name="ttft", statistic="p95", threshold=200.0, unit="ms", operator="<="),
            SLOConstraint(metric_name="error_rate", statistic="mean", threshold=0.01, unit="fraction", operator="<="),
        ],
    )
    budget = ExperimentBudget(
        max_candidates=4,
        max_wallclock_seconds=300,
        max_cost_limit=None,
    )
    policy = ExperimentVerificationPolicy(
        repetitions=1,
        duration_multiplier=1.0,
    )
    return ExperimentSpec(
        experiment_id="exp-reporting-test",
        workload=workload,
        slo=slo,
        budget=budget,
        verification_policy=policy,
        search_space={"max_num_batched_tokens": [1024, 2048], "max_num_seqs": [16, 64]},
    )


def test_build_report_artifact_and_render_markdown(mock_experiment_spec, tmp_path: Path):
    """Verifies complete ReportArtifact compilation, Markdown rendering, and disk persistence."""
    baseline = BaselineSummary(
        baseline_candidate_id="cand-baseline-01",
        verdict=FeasibilityVerdict.FEASIBLE,
        metrics={"ttft_p95": 140.0, "request_throughput": 10.0},
    )
    search_summary = SearchSummary(
        tested_candidates=["cand-baseline-01", "cand-grid-01", "cand-grid-02"],
        rejected_options=["cand-grid-02"],
        rankings=["cand-grid-01", "cand-baseline-01"],
    )
    selected_candidate = CandidateConfig(
        candidate_id="cand-grid-01",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 64},
        effective_settings={"max_num_seqs": 64},
        parameter_status={},
        environment_fingerprint={"mode": "DEMO DATA", "is_simulated": True},
    )
    verif = VerificationRecord(
        verification_id="verif-test-01",
        experiment_id=mock_experiment_spec.experiment_id,
        candidate_id="cand-grid-01",
        original_run_id="run-search-01",
        verification_run_id="run-verify-01",
        verification_verdict=VerificationState.VERIFIED,
        drift_analysis=DriftAnalysis(
            metric_deltas={"ttft_p95": 1.5, "error_rate": 0.0},
            slo_drift_detected=False,
        ),
        final_decision_notes="Passed independent verification test.",
    )

    env_fp = {"provider": "ollama", "is_simulated": False}
    limits = {"search_space": "2x2 grid", "process_startup_flags": "unverified dynamic readback"}
    cost_basis = "Mode B: GPU-seconds per request proxy (no authoritative cloud monetary pricing published)"
    artifacts = {"raw_trace": "artifacts/raw_measurements.jsonl"}

    report = build_report_artifact(
        experiment_spec=mock_experiment_spec,
        baseline_summary=baseline,
        search_summary=search_summary,
        selected_candidate=selected_candidate,
        verification_record=verif,
        environment_fingerprint=env_fp,
        limitations_disclosed=limits,
        cost_accounting_basis=cost_basis,
        artifact_paths=artifacts,
    )

    assert isinstance(report, ReportArtifact)
    assert report.report_id.startswith("rep-")
    assert report.selected_candidate.candidate_id == "cand-grid-01"

    # Markdown rendering check
    md_text = render_markdown_report(report)
    assert "# SLOKern Optimization & Verification Report" in md_text
    assert "INDEPENDENT VERIFICATION PASSED" in md_text
    assert "cand-grid-01" in md_text
    assert "Mode B: GPU-seconds per request proxy" in md_text
    assert "raw_trace" in md_text

    # Atomic write check
    json_path, md_path = write_report_artifacts(report, tmp_path)
    assert json_path.exists()
    assert md_path.exists()

    loaded = ReportArtifact.model_validate_json(json_path.read_text(encoding="utf-8"))
    assert loaded.report_id == report.report_id
    assert loaded.verification_record.verification_verdict == VerificationState.VERIFIED


def test_report_artifact_sanitization(tmp_path):
    report = ReportArtifact(
        report_id="rep-sec-01",
        created_at="2026-10-27T00:00:00Z",
        experiment_spec=ExperimentSpec(
            experiment_id="exp-1",
            workload=WorkloadSpec(
                schema_version="1.0.0",
                workload_name="sat-test",
                fixture_id="sat-001",
                arrival_mode="poisson",
                target_offered_rate=100.0,
                concurrency_limit=10,
                warmup_duration_s=0.0,
                measurement_duration_s=1,
                max_input_tokens=10,
                max_output_tokens=10
            ),
            slo=SLOSpec(
                slo_id="slo-1",
                min_sample_count=20,
                constraints=[SLOConstraint(metric_name="ttft_ms", statistic="p99", threshold=500.0, unit="ms", operator="<=")]
            ),
            search_space={"model": ["test"]},
            budget={"max_candidates": 4, "max_wallclock_seconds": 3600}
        ),
        environment_fingerprint={
            "api_key": "nvapi-12345678901234567890",
            "bearer_token": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
            "url": "http://user:password@localhost:11434"
        },
        baseline_summary=BaselineSummary(
            baseline_candidate_id="base-1",
            verdict=FeasibilityVerdict.FEASIBLE,
            metrics={"p99_latency_ms": 100.0}
        ),
        search_summary=SearchSummary(
            tested_candidates=["base-1"],
            rankings=["base-1"],
            rejected_options=[]
        ),
        selected_candidate=None,
        verification_record=None,
        limitations_disclosed={"note": "api_key='nvapi-fake1234567890'"},
        cost_accounting_basis="None",
        artifact_paths={"logs": "http://user:pass@127.0.0.1/logs"}
    )

    json_path, md_path = write_report_artifacts(report, tmp_path)

    json_text = json_path.read_text(encoding="utf-8")
    md_text = md_path.read_text(encoding="utf-8")

    assert "nvapi-" not in json_text
    assert "nvapi-" not in md_text

    assert "eyJhbGciOi" not in json_text
    assert "eyJhbGciOi" not in md_text

    assert "user:password" not in json_text
    assert "user:pass" not in md_text

    assert "***REDACTED***" in json_text
    assert "***REDACTED***" in md_text

    assert "http://***REDACTED***@localhost:11434" in json_text

    # False positive test: loopback IPs shouldn't be fully redacted, just the auth
    assert "127.0.0.1" in json_text
    assert "localhost" in json_text

    # Ensure it's valid JSON and parses back
    data = json.loads(json_text)
    ReportArtifact.model_validate(data)
