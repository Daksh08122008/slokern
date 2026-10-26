"""
Purpose: Unit tests for core/search/grid: 2x2 Bounded GridSearchController and SearchResult emission.
Owner: Rajdeep (Historical design: Rohan)
"""

from pathlib import Path
from typing import Optional, List
import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
    RankingObjective,
)
from slokern.contracts.metrics import MetricSet, PercentileDistribution
from slokern.contracts.run import RunRecord
from slokern.contracts.search import SearchResult
from slokern.contracts.spec import SLOConstraint, SLOSpec, WorkloadSpec
from slokern.contracts.verdict import FeasibilityResult
from slokern.core.search.budget import BudgetLimiter
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.core.search.grid import (
    GridSearchController,
    SearchConfigurationError,
    extract_ranking_metric,
    run_grid_search,
)
from slokern.engine.runner.cancel import CancellationToken
from slokern.engine.runner.run_executor import SingleRunResult


def _create_test_metric_set(
    run_id: str,
    throughput_tps: float = 160.0,
    mean_e2e_ms: float = 100.0,
) -> MetricSet:
    return MetricSet(
        metric_version="1.0.0",
        run_id=run_id,
        sample_count=50,
        failed_request_count=0,
        offered_load_rps=10.0,
        achieved_load_rps=10.0,
        generator_saturated=False,
        ttft_ms=PercentileDistribution(p50=12.0, p95=15.0, mean=13.0),
        itl_ms=PercentileDistribution(p50=8.0, p95=10.0, mean=8.5),
        e2e_latency_ms=PercentileDistribution(p50=90.0, p95=120.0, mean=mean_e2e_ms),
        request_throughput_rps=10.0,
        token_throughput_tps=throughput_tps,
        error_rate=0.0,
        metadata={"cost_per_token": 0.00005, "cost_per_1k_requests": 0.02},
    )


class MockSingleRunExecutor:
    """Deterministic mock executor for offline unit testing without event loop dependencies."""

    def __init__(
        self,
        default_verdict: FeasibilityVerdict = FeasibilityVerdict.FEASIBLE,
        throughput_map: Optional[dict] = None,
    ) -> None:
        self.call_count = 0
        self.called_configs: List[CandidateConfig] = []
        self.default_verdict = default_verdict
        self.throughput_map = throughput_map or {}

    def execute(
        self,
        candidate_config: CandidateConfig,
        workload: WorkloadSpec,
        slo: SLOSpec,
        experiment_id: str,
        run_id: str,
        **kwargs,
    ) -> SingleRunResult:
        self.call_count += 1
        self.called_configs.append(candidate_config)

        tps = self.throughput_map.get(candidate_config.candidate_id, 100.0 + self.call_count * 10.0)
        ms = _create_test_metric_set(run_id, throughput_tps=tps)

        feasibility = FeasibilityResult(
            policy_version="1.0.0",
            run_id=run_id,
            overall_verdict=self.default_verdict,
            constraint_evaluations=[],
            validity_status=EvidenceValidity.VALID,
            audit_notes="Mock unit test verdict",
        )

        record = RunRecord(
            run_id=run_id,
            experiment_id=experiment_id,
            candidate_id=candidate_config.candidate_id,
            is_verification_run=kwargs.get("is_verification_run", False),
            execution_status=ExecutionStatus.COMPLETED,
            started_at="2026-10-23T00:00:00.000000+00:00",
            completed_at="2026-10-23T00:00:01.000000+00:00",
            raw_artifact_uri=None,
            execution_error=None,
        )

        return SingleRunResult(
            run_record=record,
            metric_set=ms,
            feasibility_result=feasibility,
            applied_config=candidate_config,
            raw_measurements_count=50,
            artifact_paths={},
        )


@pytest.fixture
def mock_workload() -> WorkloadSpec:
    return WorkloadSpec(
        schema_version="1.0.0",
        workload_name="test_grid_workload",
        fixture_id="test_fixture_01",
        arrival_mode=ArrivalMode.CONSTANT,
        target_offered_rate=10.0,
        concurrency_limit=4,
        warmup_duration_s=0,
        measurement_duration_s=1,
        max_input_tokens=32,
        max_output_tokens=16,
    )


@pytest.fixture
def mock_slo() -> SLOSpec:
    return SLOSpec(
        slo_id="slo_test",
        constraints=[
            SLOConstraint(
                metric_name="ttft_ms",
                statistic="p95",
                threshold=1000.0,
                unit="ms",
                operator="<=",
            )
        ],
        min_sample_count=1,
    )


@pytest.fixture
def baseline_candidate() -> CandidateConfig:
    settings = {"max_num_seqs": 32, "max_num_batched_tokens": 2048}
    model = "meta-llama/Meta-Llama-3-8B-Instruct"
    runtime = "vllm-fake"
    return CandidateConfig(
        candidate_id=generate_candidate_id(model, runtime, settings),
        model_name=model,
        runtime_name=runtime,
        requested_settings=settings,
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )


def test_extract_ranking_metric():
    ms = _create_test_metric_set("run-test", throughput_tps=160.0, mean_e2e_ms=110.0)

    # Max throughput: should return token_throughput_tps (160.0)
    assert extract_ranking_metric(ms, RankingObjective.MAX_THROUGHPUT_UNDER_SLO) == 160.0

    # GPU seconds: mean e2e latency (110.0 ms) converted to seconds (0.11 s)
    assert extract_ranking_metric(ms, RankingObjective.GPU_SECONDS_PER_REQUEST) == 0.11

    # Monetary cost per token
    assert extract_ranking_metric(ms, RankingObjective.MONETARY_COST_PER_TOKEN) == 0.00005

    # Monetary cost per 1k requests
    assert extract_ranking_metric(ms, RankingObjective.MONETARY_COST_PER_1K_REQUESTS) == 0.02

    # None metric set
    assert extract_ranking_metric(None, RankingObjective.MAX_THROUGHPUT_UNDER_SLO) is None


def test_grid_search_full_2x2_execution(
    tmp_path: Path,
    mock_workload: WorkloadSpec,
    mock_slo: SLOSpec,
    baseline_candidate: CandidateConfig,
):
    mock_executor = MockSingleRunExecutor()
    controller = GridSearchController(
        single_run_executor=mock_executor,
        artifacts_root=tmp_path,
        default_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
    )

    budget = BudgetLimiter(max_total_runs=6, max_search_runs=5, max_verification_runs=1)

    result = controller.execute(
        baseline_config=baseline_candidate,
        workload=mock_workload,
        slo=mock_slo,
        experiment_id="exp-grid-test",
        budget_limiter=budget,
    )

    assert isinstance(result, SearchResult)
    assert result.experiment_id == "exp-grid-test"
    assert result.baseline_candidate_id == baseline_candidate.candidate_id

    # Exactly 5 runs executed: 1 baseline (Run 0) + 4 grid candidates (Runs 1-4)
    assert mock_executor.call_count == 5
    assert len(result.tested_candidates) == 5
    assert budget.search_runs_executed == 5
    assert budget.runs_executed == 5
    assert budget.remaining_verification_runs == 1

    # All 5 candidates mapped in candidate_summaries
    assert len(result.candidate_summaries) == 5
    for cand_id in result.tested_candidates:
        assert cand_id in result.candidate_summaries
        summary = result.candidate_summaries[cand_id]
        assert summary.verdict == FeasibilityVerdict.FEASIBLE
        assert summary.ranking_metric is not None
        assert summary.ranking_metric > 0

    # Winning candidate selected
    assert result.selected_candidate_id is not None
    assert result.selected_candidate_id in result.tested_candidates
    assert "Selected candidate" in result.selection_rationale
    assert result.stopping_reason == "space_exhausted"

    # Disk persistence verification
    persisted_path = tmp_path / "experiments" / "exp-grid-test" / "search_result.json"
    assert persisted_path.exists()
    loaded_result = SearchResult.model_validate_json(persisted_path.read_text(encoding="utf-8"))
    assert loaded_result.experiment_id == result.experiment_id
    assert loaded_result.selected_candidate_id == result.selected_candidate_id


def test_grid_search_budget_exhaustion(
    tmp_path: Path,
    mock_workload: WorkloadSpec,
    mock_slo: SLOSpec,
    baseline_candidate: CandidateConfig,
):
    mock_executor = MockSingleRunExecutor()
    controller = GridSearchController(
        single_run_executor=mock_executor,
        artifacts_root=tmp_path,
    )

    # Restrict budget to only 2 search runs (1 baseline + 1 search candidate)
    tight_budget = BudgetLimiter(max_total_runs=4, max_search_runs=2, max_verification_runs=1)

    result = controller.execute(
        baseline_config=baseline_candidate,
        workload=mock_workload,
        slo=mock_slo,
        experiment_id="exp-budget-stop",
        budget_limiter=tight_budget,
    )

    assert mock_executor.call_count == 2
    assert tight_budget.search_runs_executed == 2
    assert len(result.tested_candidates) == 2
    assert result.stopping_reason == "budget_exhausted"


def test_grid_search_zero_feasible_candidates(
    tmp_path: Path,
    mock_workload: WorkloadSpec,
    mock_slo: SLOSpec,
    baseline_candidate: CandidateConfig,
):
    mock_executor = MockSingleRunExecutor(default_verdict=FeasibilityVerdict.INFEASIBLE)
    controller = GridSearchController(
        single_run_executor=mock_executor,
        artifacts_root=tmp_path,
    )

    result = controller.execute(
        baseline_config=baseline_candidate,
        workload=mock_workload,
        slo=mock_slo,
        experiment_id="exp-zero-feasible",
    )

    assert mock_executor.call_count == 5
    assert result.selected_candidate_id is None
    assert "No candidate among" in result.selection_rationale
    assert result.stopping_reason == "space_exhausted"
    for summary in result.candidate_summaries.values():
        assert summary.verdict == FeasibilityVerdict.INFEASIBLE


def test_grid_search_cancellation(
    tmp_path: Path,
    mock_workload: WorkloadSpec,
    mock_slo: SLOSpec,
    baseline_candidate: CandidateConfig,
):
    token = CancellationToken()
    token.cancel()  # Pre-cancelled

    mock_executor = MockSingleRunExecutor()
    controller = GridSearchController(
        single_run_executor=mock_executor,
        artifacts_root=tmp_path,
    )

    result = controller.execute(
        baseline_config=baseline_candidate,
        workload=mock_workload,
        slo=mock_slo,
        experiment_id="exp-cancelled",
        cancellation_token=token,
    )

    assert mock_executor.call_count == 0
    assert result.stopping_reason == "cancelled"
    assert result.selected_candidate_id is None


def test_grid_search_halts_on_unverified_capabilities(
    tmp_path: Path,
    mock_workload: WorkloadSpec,
    mock_slo: SLOSpec,
    baseline_candidate: CandidateConfig,
):
    """Invoking run_grid_search with Ollama raises SearchConfigurationError citing BLK-17."""
    from slokern.engine.serving.ollama import OllamaServingAdapter

    ollama_adapter = OllamaServingAdapter()
    controller = GridSearchController(
        adapter=ollama_adapter,
        artifacts_root=tmp_path,
    )

    with pytest.raises(SearchConfigurationError) as exc_info:
        controller.run_grid_search(
            baseline_config=baseline_candidate,
            workload=mock_workload,
            slo=mock_slo,
        )

    assert "BLK-17" in str(exc_info.value)

    # Standalone function invocation also halts citing BLK-17
    with pytest.raises(SearchConfigurationError) as exc_info2:
        run_grid_search(
            adapter=ollama_adapter,
            baseline_config=baseline_candidate,
            workload=mock_workload,
            slo=mock_slo,
        )

    assert "BLK-17" in str(exc_info2.value)


def test_grid_search_controller_run_halts_on_ollama_and_nebius(tmp_path: Path):
    """GridSearchController.run() halts immediately citing BLK-17 for both Ollama and Nebius."""
    from slokern.contracts.enums import ArrivalMode
    from slokern.contracts.spec import ExperimentBudget, ExperimentSpec, ExperimentVerificationPolicy
    from slokern.engine.serving.nebius import NebiusServingAdapter
    from slokern.engine.serving.ollama import OllamaServingAdapter

    spec = ExperimentSpec(
        experiment_id="exp-blk17-test",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="w",
            fixture_id="f",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=10,
            concurrency_limit=2,
            warmup_duration_s=1,
            measurement_duration_s=1,
            max_input_tokens=10,
            max_output_tokens=10,
        ),
        slo=SLOSpec(slo_id="s", constraints=[], min_sample_count=1),
        search_space={},
        budget=ExperimentBudget(max_candidates=5, max_wallclock_seconds=60),
        verification_policy=ExperimentVerificationPolicy(),
    )

    # Ollama halts citing BLK-17
    ollama_ctrl = GridSearchController(adapter=OllamaServingAdapter(), artifacts_root=tmp_path)
    with pytest.raises(SearchConfigurationError) as exc_info:
        ollama_ctrl.run(spec, ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO)
    assert "BLK-17" in str(exc_info.value)

    # Nebius halts citing BLK-17
    nebius_ctrl = GridSearchController(adapter=NebiusServingAdapter(api_key="test-key"), artifacts_root=tmp_path)
    with pytest.raises(SearchConfigurationError) as exc_info2:
        nebius_ctrl.run(spec, ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO)
    assert "BLK-17" in str(exc_info2.value)
