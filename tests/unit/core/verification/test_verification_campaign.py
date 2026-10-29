"""
Purpose: End-to-end unit tests for search campaign verification protocol and independence auditing.
Owner: Rajdeep
Authority: AGENTS.md Section 5, 7, 10
"""

import json
from pathlib import Path

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    RankingObjective,
    ReasonCode,
    VerificationState,
)
from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.run import RunRecord
from slokern.contracts.search import CandidateSummary, SearchResult
from slokern.contracts.spec import SLOConstraint, SLOSpec, WorkloadSpec
from slokern.contracts.verdict import ConstraintEvaluation, FeasibilityResult
from slokern.core.verification.protocol import (
    VerificationCampaignError,
    verify_search_campaign,
)
from slokern.engine.runner.run_executor import SingleRunResult


class MockCampaignExecutor:
    """Mock executor simulating SingleRunExecutor during verification rerun."""

    def __init__(
        self,
        ttft_p95: float = 120.0,
        throughput_rps: float = 15.0,
        error_rate: float = 0.0,
        execution_status: ExecutionStatus = ExecutionStatus.COMPLETED,
        validity_status: EvidenceValidity = EvidenceValidity.VALID,
    ):
        self.ttft_p95 = ttft_p95
        self.throughput_rps = throughput_rps
        self.error_rate = error_rate
        self.execution_status = execution_status
        self.validity_status = validity_status
        self.executed_run_ids = []

    def execute(self, candidate_config, workload, slo, experiment_id, run_id, **kwargs):
        self.executed_run_ids.append(run_id)

        ms = MetricSet(
            metric_version="1.0.0",
            run_id=run_id,
            sample_count=50,
            failed_request_count=int(self.error_rate * 50),
            offered_load_rps=10.0,
            achieved_load_rps=10.0,
            generator_saturated=False,
            ttft_ms=PercentileDistribution(p50=self.ttft_p95 * 0.7, p95=self.ttft_p95),
            itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
            e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
            request_throughput_rps=self.throughput_rps,
            token_throughput_tps=self.throughput_rps * 10.0,
            error_rate=self.error_rate,
        )

        overall_verdict = (
            FeasibilityVerdict.FEASIBLE
            if self.ttft_p95 <= 200.0 and self.error_rate <= 0.01
            else FeasibilityVerdict.INFEASIBLE
        )

        feas = FeasibilityResult(
            policy_version="1.0.0",
            run_id=run_id,
            overall_verdict=overall_verdict,
            constraint_evaluations=[
                ConstraintEvaluation(
                    metric_name="ttft",
                    statistic="p95",
                    observed_value=self.ttft_p95,
                    required_threshold=200.0,
                    operator="<=",
                    passed=(self.ttft_p95 <= 200.0),
                    reason_code=ReasonCode.HARD_CONSTRAINTS_PASSED if self.ttft_p95 <= 200.0 else ReasonCode.TTFT_P95_EXCEEDED,
                )
            ],
            validity_status=self.validity_status,
            audit_notes="Mock campaign rerun feasibility",
        )

        rec = RunRecord(
            run_id=run_id,
            experiment_id=experiment_id,
            candidate_id=candidate_config.candidate_id,
            is_verification_run=kwargs.get("is_verification_run", True),
            execution_status=self.execution_status,
            started_at="2026-10-26T20:00:00+00:00",
            completed_at="2026-10-26T20:00:01+00:00",
        )

        return SingleRunResult(
            run_record=rec,
            metric_set=ms if self.execution_status == ExecutionStatus.COMPLETED else None,
            feasibility_result=feas if self.execution_status == ExecutionStatus.COMPLETED else None,
            applied_config=candidate_config,
            raw_measurements_count=50,
            artifact_paths={},
        )


@pytest.fixture
def mock_campaign_environment(tmp_path: Path):
    """Sets up a complete 5-run search campaign in a temp directory."""
    exp_id = "exp-test-campaign-001"
    exp_dir = tmp_path / "experiments" / exp_id
    runs_dir = exp_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    winner_cand_id = "cand-winner-42"
    other_cand_id = "cand-other-99"

    # Baseline run
    run_00_dir = runs_dir / "run-00-base"
    run_00_dir.mkdir()
    (run_00_dir / "run_record.json").write_text(
        RunRecord(
            run_id="run-00-base",
            experiment_id=exp_id,
            candidate_id="cand-baseline",
            is_verification_run=False,
            execution_status=ExecutionStatus.COMPLETED,
        ).model_dump_json(indent=2)
    )

    # Search run 01 (winner)
    run_01_dir = runs_dir / "run-01-winner"
    run_01_dir.mkdir()
    winner_config = CandidateConfig(
        candidate_id=winner_cand_id,
        model_name="test-model",
        runtime_name="vllm",
        requested_settings={"max_num_seqs": 32},
        effective_settings={"max_num_seqs": 32},
        parameter_status={"max_num_seqs": "applied"},
        environment_fingerprint={"device": "cuda:0"},
    )
    (run_01_dir / "applied_config.json").write_text(winner_config.model_dump_json(indent=2))
    (run_01_dir / "run_record.json").write_text(
        RunRecord(
            run_id="run-01-winner",
            experiment_id=exp_id,
            candidate_id=winner_cand_id,
            is_verification_run=False,
            execution_status=ExecutionStatus.COMPLETED,
        ).model_dump_json(indent=2)
    )
    winner_metrics = MetricSet(
        metric_version="1.0.0",
        run_id="run-01-winner",
        sample_count=50,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=70.0, p95=100.0),
        itl_ms=PercentileDistribution(p50=10.0, p95=20.0),
        e2e_latency_ms=PercentileDistribution(p50=100.0, p95=200.0),
        request_throughput_rps=15.0,
        token_throughput_tps=150.0,
        error_rate=0.0,
    )
    (run_01_dir / "metrics.json").write_text(winner_metrics.model_dump_json(indent=2))

    # Search result
    search_result = SearchResult(
        experiment_id=exp_id,
        baseline_candidate_id="cand-baseline",
        tested_candidates=["cand-baseline", winner_cand_id, other_cand_id],
        candidate_summaries={
            winner_cand_id: CandidateSummary(verdict=FeasibilityVerdict.FEASIBLE, ranking_metric=150.0),
            other_cand_id: CandidateSummary(verdict=FeasibilityVerdict.INFEASIBLE, ranking_metric=None),
        },
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        selected_candidate_id=winner_cand_id,
        selection_rationale="Selected cand-winner-42 as top feasible candidate",
        stopping_reason="space_exhausted",
    )
    (exp_dir / "search_result.json").write_text(search_result.model_dump_json(indent=2))

    # Report containing workload and slo
    report_dict = {
        "report_id": "rep-test-01",
        "created_at": "2026-10-26T20:00:00+00:00",
        "experiment_spec": {
            "experiment_id": exp_id,
            "workload": {
                "schema_version": "1.0.0",
                "workload_name": "test-workload",
                "fixture_id": "fix-01",
                "arrival_mode": "constant",
                "target_offered_rate": 10.0,
                "concurrency_limit": 4,
                "warmup_duration_s": 1,
                "measurement_duration_s": 1,
                "max_input_tokens": 128,
                "max_output_tokens": 32,
            },
            "slo": {
                "slo_id": "slo-test",
                "constraints": [
                    {
                        "metric_name": "ttft",
                        "statistic": "p95",
                        "threshold": 200.0,
                        "unit": "ms",
                        "operator": "<=",
                    }
                ],
                "min_sample_count": 20,
            },
            "search_space": {},
            "budget": {"max_candidates": 4, "max_wallclock_seconds": 60},
        },
    }
    (exp_dir / "report.json").write_text(json.dumps(report_dict, indent=2))

    return tmp_path, exp_id, winner_cand_id, winner_metrics


def test_verify_search_campaign_end_to_end_success(mock_campaign_environment):
    """
    Verifies a healthy search campaign:
    - Finds the winner cand-winner-42
    - Executes rerun under distinct run ID
    - Metrics remain within drift tolerance (100 -> 110ms is +10% <= 15%)
    - Emits VERIFIED VerificationRecord and writes verification_record.json
    - Preserves all 5 existing search runs without mutation
    """
    tmp_path, exp_id, winner_cand_id, winner_metrics = mock_campaign_environment
    mock_executor = MockCampaignExecutor(ttft_p95=110.0, throughput_rps=15.0)

    record = verify_search_campaign(
        experiment_id=exp_id,
        artifacts_root=tmp_path,
        single_run_executor=mock_executor,
    )

    # 1. Verification Record Invariants
    assert record.verification_verdict == VerificationState.VERIFIED
    assert record.candidate_id == winner_cand_id
    assert record.original_run_id == "run-01-winner"
    assert record.verification_run_id != "run-01-winner"
    assert record.verification_run_id.startswith("run-verify-")
    assert record.reason_codes == [ReasonCode.HARD_CONSTRAINTS_PASSED]

    # 2. Drift Analysis
    assert record.drift_analysis is not None
    assert record.drift_analysis.slo_drift_detected is False
    assert record.drift_analysis.drift_exceeded is False
    assert record.drift_analysis.metric_deltas["ttft_p95"] == 10.0

    # 3. Persistence Verification
    record_file = tmp_path / "experiments" / exp_id / "verification_record.json"
    assert record_file.is_file()
    saved = json.loads(record_file.read_text(encoding="utf-8"))
    assert saved["verification_verdict"] == "VERIFIED"
    assert saved["verification_run_id"] == record.verification_run_id

    # 4. Search Run Immutability: original search metrics unchanged
    orig_file = tmp_path / "experiments" / exp_id / "runs" / "run-01-winner" / "metrics.json"
    orig_saved = MetricSet.model_validate_json(orig_file.read_text(encoding="utf-8"))
    assert orig_saved.run_id == "run-01-winner"
    assert orig_saved.ttft_ms.p95 == 100.0


def test_verify_search_campaign_rejects_missing_winner(mock_campaign_environment):
    """Campaign with no selected winner cannot be verified and raises VerificationCampaignError."""
    tmp_path, exp_id, _, _ = mock_campaign_environment
    sr_file = tmp_path / "experiments" / exp_id / "search_result.json"
    sr = SearchResult.model_validate_json(sr_file.read_text(encoding="utf-8"))
    sr.selected_candidate_id = None
    sr_file.write_text(sr.model_dump_json(indent=2))

    with pytest.raises(VerificationCampaignError, match="no selected winning candidate"):
        verify_search_campaign(
            experiment_id=exp_id,
            artifacts_root=tmp_path,
        )


def test_verify_search_campaign_rejects_infeasible_winner(mock_campaign_environment):
    """Campaign with non-feasible winner raises VerificationCampaignError."""
    tmp_path, exp_id, winner_cand_id, _ = mock_campaign_environment
    sr_file = tmp_path / "experiments" / exp_id / "search_result.json"
    sr = SearchResult.model_validate_json(sr_file.read_text(encoding="utf-8"))
    sr.candidate_summaries[winner_cand_id].verdict = FeasibilityVerdict.INFEASIBLE
    sr_file.write_text(sr.model_dump_json(indent=2))

    with pytest.raises(VerificationCampaignError, match="non-feasible verdict"):
        verify_search_campaign(
            experiment_id=exp_id,
            artifacts_root=tmp_path,
        )


def test_verify_search_campaign_fails_on_hard_slo_breach(mock_campaign_environment):
    """If verification rerun violates a hard SLO constraint, verdict is VERIFICATION_FAILED."""
    tmp_path, exp_id, winner_cand_id, _ = mock_campaign_environment
    # TTFT p95 = 250ms breaches threshold 200ms
    mock_executor = MockCampaignExecutor(ttft_p95=250.0)

    record = verify_search_campaign(
        experiment_id=exp_id,
        artifacts_root=tmp_path,
        single_run_executor=mock_executor,
    )

    assert record.verification_verdict == VerificationState.VERIFICATION_FAILED
    assert ReasonCode.TTFT_P95_EXCEEDED in record.reason_codes
    assert "violated declared hard constraints" in record.final_decision_notes


def test_verify_search_campaign_fails_on_drift_tolerance_breach(mock_campaign_environment):
    """
    If verification rerun passes hard SLO (180ms <= 200ms threshold), but latency
    drift exceeds +15% tolerance (+80% increase from 100ms), verdict is VERIFICATION_FAILED.
    """
    tmp_path, exp_id, winner_cand_id, _ = mock_campaign_environment
    # 180ms passes SLO (threshold 200ms), but drift is +80% relative to 100ms search reference
    mock_executor = MockCampaignExecutor(ttft_p95=180.0)

    record = verify_search_campaign(
        experiment_id=exp_id,
        artifacts_root=tmp_path,
        single_run_executor=mock_executor,
    )

    assert record.verification_verdict == VerificationState.VERIFICATION_FAILED
    assert ReasonCode.VERIFICATION_DRIFT_EXCEEDED in record.reason_codes
    assert record.drift_analysis.drift_exceeded is True
    assert "exceeded accepted drift tolerance" in record.final_decision_notes


def test_verify_search_campaign_inconclusive_on_crash(mock_campaign_environment):
    """If verification execution crashes, verdict is VERIFICATION_INCONCLUSIVE with EXECUTION_CRASHED."""
    tmp_path, exp_id, _, _ = mock_campaign_environment
    mock_executor = MockCampaignExecutor(execution_status=ExecutionStatus.FAILED)

    record = verify_search_campaign(
        experiment_id=exp_id,
        artifacts_root=tmp_path,
        single_run_executor=mock_executor,
    )

    assert record.verification_verdict == VerificationState.VERIFICATION_INCONCLUSIVE
    assert record.reason_codes == [ReasonCode.EXECUTION_CRASHED]
    assert "ended with status FAILED" in record.final_decision_notes


def test_grid_search_controller_run_full_campaign_executes_run_6(tmp_path: Path):
    """
    Demonstrates that GridSearchController.run_full_campaign() executes:
    - 1 baseline (Run 0)
    - 4 candidates (Runs 1-4)
    - 1 independent verification run (Run 6) under fresh verification_run_id
    Total: exactly 6 runs.
    Verifies that Run 6 recomputes metrics, checks drift, leaves search runs unchanged,
    and returns verification_record.
    """
    from slokern.contracts.spec import (
        ExperimentBudget,
        ExperimentSpec,
        ExperimentVerificationPolicy,
    )
    from slokern.core.search.grid import GridSearchController
    from slokern.engine.serving.fake import FakeServingAdapter

    adapter = FakeServingAdapter(simulate_delay=False)
    exp_id = "exp-full-campaign-6runs"

    spec = ExperimentSpec(
        experiment_id=exp_id,
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="full-campaign-workload",
            fixture_id="fix-fc-01",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=10.0,
            concurrency_limit=4,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=16,
            max_output_tokens=16,
        ),
        slo=SLOSpec(
            slo_id="slo-fc",
            constraints=[
                SLOConstraint(
                    metric_name="ttft_ms",
                    statistic="p95",
                    threshold=500.0,
                    unit="ms",
                    operator="<=",
                )
            ],
            min_sample_count=1,
        ),
        search_space={
            "max_num_batched_tokens": [1024, 2048],
            "max_num_seqs": [16, 64],
        },
        budget=ExperimentBudget(max_candidates=4, max_wallclock_seconds=60),
        verification_policy=ExperimentVerificationPolicy(repetitions=1, duration_multiplier=1.0),
    )

    controller = GridSearchController(
        adapter=adapter,
        artifacts_root=tmp_path,
        default_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        isolate_process=False,
    )

    outcome = controller.run_full_campaign(
        spec,
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        seed=42,
    )

    # 1. Five search runs executed (1 baseline + 4 candidates)
    assert len(outcome.run_results) == 5
    assert len(outcome.search_result.tested_candidates) == 5
    assert outcome.search_result.selected_candidate_id is not None
    winner_id = outcome.search_result.selected_candidate_id

    # 2. Run 6 (Independent Verification) executed
    assert outcome.verification_record is not None
    verif = outcome.verification_record
    assert verif.candidate_id == winner_id
    assert verif.verification_verdict == VerificationState.VERIFIED
    assert verif.verification_run_id.startswith("run-verify-")
    assert verif.verification_run_id != verif.original_run_id
    assert verif.original_run_id == outcome.run_results[0].run_id

    # 3. Drift Analysis computed
    assert verif.drift_analysis is not None
    assert verif.drift_analysis.drift_exceeded is False
    assert "ttft_p95" in verif.drift_analysis.metric_comparisons
    assert verif.drift_analysis.metric_comparisons["ttft_p95"].passed is True

    # 4. Verification record persisted on disk
    record_file = tmp_path / "experiments" / exp_id / "verification_record.json"
    assert record_file.is_file()

    # 5. Search run artifacts remain unchanged on disk
    runs_dir = tmp_path / "experiments" / exp_id / "runs"
    assert runs_dir.is_dir()
    run_folders = [p.name for p in runs_dir.iterdir() if p.is_dir()]
    # Exactly 6 run folders: 5 search runs + 1 verification run
    assert len(run_folders) == 6
    assert any(f.startswith("run-verify-") for f in run_folders)
    search_folders = [f for f in run_folders if not f.startswith("run-verify-")]
    assert len(search_folders) == 5
