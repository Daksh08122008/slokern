"""Bounded grid search integration tests using explicitly synthetic DEMO DATA."""

from pathlib import Path
import threading
from types import SimpleNamespace

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    ExecutionStatus,
    FeasibilityVerdict,
    RankingObjective,
)
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOSpec,
    WorkloadSpec,
)
from slokern.core.search.budget import BudgetValidationError
from slokern.core.search.grid import GridSearchController, SearchExecutionError
from slokern.engine.loadgen.runner import LoadGeneratorResult, LoadGeneratorRunner
from slokern.engine.runner.run_executor import SingleRunExecutor
from slokern.engine.serving.fake import FakeServingAdapter


@pytest.fixture(autouse=True)
def bypass_sandbox_socketpair_hang(monkeypatch):
    """
    In the Windows Codex sandbox environment under ASTRYX\\CodexSandboxUsers,
    asyncio.ProactorEventLoop._make_self_pipe loopback socketpair accept blocks.
    This mock satisfies the load generator contract for offline fake adapter search tests.
    """
    def mock_loadgen_run(
        self,
        workload,
        adapter,
        output_path,
        run_id="run-001",
        seed=42,
        stream=True,
        prompts=None,
        artificial_dispatch_delay_ms=0.0,
    ):
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        measurement = RawRequestMeasurement(
            request_id=f"req-{run_id}-000000",
            run_id=run_id,
            scheduled_at=100.0,
            sent_at=100.0,
            first_token_at=100.012,
            completed_at=100.080,
            http_status=200,
            input_tokens=8,
            output_tokens=8,
            itl_observations_ms=[8.5] * 7,
            error_type=None,
            is_valid=True,
            is_warmup=False,
        )
        out.write_text(measurement.model_dump_json() + "\n", encoding="utf-8")
        if hasattr(adapter, "stream_generate"):
            list(adapter.stream_generate("prompt"))
        return LoadGeneratorResult(
            total_requests=1,
            warmup_requests=0,
            active_requests=1,
            completed_requests=1,
            failed_requests=0,
            target_offered_rate=float(workload.target_offered_rate),
            offered_load_rps=1.0,
            achieved_load_rps=1.0,
            generator_saturated=False,
            mean_dispatch_lag_ms=0.0,
            max_dispatch_lag_ms=0.0,
            output_path=str(out),
        )

    monkeypatch.setattr(LoadGeneratorRunner, "run", mock_loadgen_run)


def make_spec(*, max_candidates=4, max_wallclock_seconds=30, max_cost_limit=None):
    return ExperimentSpec(
        experiment_id="grid-search-test",
        workload=WorkloadSpec(
            schema_version="1.0.0",
            workload_name="grid-search-demo",
            fixture_id="demo-fixture",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=1.0,
            concurrency_limit=1,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=8,
            max_output_tokens=8,
        ),
        slo=SLOSpec(slo_id="demo-slo", constraints=[], min_sample_count=1),
        search_space={},
        budget=ExperimentBudget(
            max_candidates=max_candidates,
            max_wallclock_seconds=max_wallclock_seconds,
            max_cost_limit=max_cost_limit,
        ),
        verification_policy=ExperimentVerificationPolicy(
            repetitions=1,
            duration_multiplier=1.0,
        ),
    )


class CountingFakeAdapter(FakeServingAdapter):
    def __init__(self):
        super().__init__(simulate_delay=False)
        self.run_side_effects = 0

    def apply_config(self, candidate_config, strict=False):
        self.run_side_effects += 1
        return super().apply_config(candidate_config, strict=strict)

    def generate(self, request):
        self.run_side_effects += 1
        return super().generate(request)

    def stream_generate(self, request):
        self.run_side_effects += 1
        yield from super().stream_generate(request)


def make_controller(tmp_path: Path, adapter: CountingFakeAdapter):
    executor = SingleRunExecutor(
        adapter=adapter,
        artifacts_root=tmp_path,
        isolate_process=False,
    )
    return GridSearchController(
        executor=executor,
        adapter=adapter,
        model_name=adapter.model_name,
    )


@pytest.mark.parametrize(
    "spec",
    [
        make_spec(max_candidates=0),
        make_spec(max_wallclock_seconds=0),
    ],
)
def test_invalid_budget_is_rejected_before_adapter_side_effects(tmp_path, spec):
    adapter = CountingFakeAdapter()
    controller = make_controller(tmp_path, adapter)

    with pytest.raises(BudgetValidationError):
        controller.run(
            spec,
            ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        )

    assert adapter.run_side_effects == 0


def test_unenforceable_cost_cap_is_rejected_before_adapter_side_effects(tmp_path):
    adapter = CountingFakeAdapter()
    controller = make_controller(tmp_path, adapter)

    with pytest.raises(BudgetValidationError, match="authoritative pricing source"):
        controller.run(
            make_spec(max_cost_limit=10.0),
            ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        )

    assert adapter.run_side_effects == 0


def test_grid_search_executes_one_baseline_and_four_candidates(tmp_path):
    adapter = CountingFakeAdapter()
    controller = make_controller(tmp_path, adapter)

    outcome = controller.run(
        make_spec(),
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        seed=7,
    )

    assert len(outcome.run_results) == 5
    assert all(result.execution_status == ExecutionStatus.COMPLETED for result in outcome.run_results)
    assert len(outcome.search_result.tested_candidates) == 5
    assert len(outcome.search_result.candidate_summaries) == 5
    assert outcome.search_result.tested_candidates[0] == outcome.search_result.baseline_candidate_id
    assert outcome.search_result.stopping_reason == "space_exhausted"
    assert outcome.search_result.ranking_objective == RankingObjective.MAX_THROUGHPUT_UNDER_SLO
    assert outcome.search_result.selected_candidate_id is not None
    assert (
        outcome.search_result.candidate_summaries[
            outcome.search_result.selected_candidate_id
        ].verdict
        == FeasibilityVerdict.FEASIBLE
    )
    assert adapter.run_side_effects >= 5
    requested_grids = {
        (
            result.applied_config.requested_settings["max_num_batched_tokens"],
            result.applied_config.requested_settings["max_num_seqs"],
        )
        for result in outcome.run_results[1:]
    }
    assert requested_grids == {
        (1024, 16),
        (1024, 64),
        (2048, 16),
        (2048, 64),
    }


def test_candidate_limit_bounds_runs(tmp_path):
    adapter = CountingFakeAdapter()
    controller = make_controller(tmp_path, adapter)

    outcome = controller.run(
        make_spec(max_candidates=2),
        ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
    )

    assert len(outcome.run_results) == 3  # baseline plus two candidates
    assert outcome.search_result.stopping_reason == "budget_exhausted"


def test_wallclock_budget_cancels_active_run(tmp_path):
    adapter = CountingFakeAdapter()
    cancelled = threading.Event()

    class BlockingExecutor:
        def execute(self, **kwargs):
            token = kwargs["cancellation_token"]
            token.register_callback(cancelled.set)
            cancelled.wait(timeout=2)
            return SimpleNamespace(
                run_id="run-timeout",
                execution_status=ExecutionStatus.CANCELLED,
            )

    controller = GridSearchController(
        executor=BlockingExecutor(),
        adapter=adapter,
        model_name=adapter.model_name,
    )
    spec = make_spec(max_wallclock_seconds=1)

    with pytest.raises(SearchExecutionError, match="CANCELLED"):
        controller.run(
            spec,
            ranking_objective=RankingObjective.MAX_THROUGHPUT_UNDER_SLO,
        )

    assert cancelled.is_set()
