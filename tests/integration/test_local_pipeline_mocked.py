"""
Purpose: End-to-end local pipeline integration test with mocked Ollama HTTP backend and budget enforcement.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 6, 7, 10 and DEC-0014
"""

import io
import json
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.request
import pytest

from slokern.cli.commands.smoke_test import smoke_test_command
from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    ExecutionStatus,
    FeasibilityVerdict,
    VerificationState,
)
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.metrics import MetricSet
from slokern.contracts.report import BaselineSummary, SearchSummary
from slokern.contracts.spec import (
    ExperimentBudget,
    ExperimentSpec,
    ExperimentVerificationPolicy,
    SLOConstraint,
    SLOSpec,
    WorkloadSpec,
)
from slokern.contracts.verification import VerificationRecord
from slokern.core.search.budget import BudgetExhaustedError, BudgetLimiter
from slokern.core.verification.protocol import run_independent_verification
from slokern.engine.loadgen.runner import LoadGeneratorResult, LoadGeneratorRunner
from slokern.engine.reporting.report_builder import (
    build_report_artifact,
    write_report_artifacts,
)
from slokern.engine.runner.run_executor import SingleRunExecutor
from slokern.engine.serving.ollama import OllamaServingAdapter


class MockOllamaHTTPResponse:
    """Simulates HTTP response from Ollama daemon for /api/tags and /api/chat."""

    def __init__(self, endpoint_url: str):
        self.endpoint_url = endpoint_url
        self.status = 200

        if "/api/tags" in endpoint_url:
            self._body = json.dumps({
                "models": [
                    {
                        "name": "qwen3:4b-instruct-2507-q4_K_M:latest",
                        "model": "qwen3:4b-instruct-2507-q4_K_M",
                    }
                ]
            }).encode("utf-8")
            self._lines = [self._body]
        elif "/api/chat" in endpoint_url:
            self._body = json.dumps({
                "message": {"content": "Hello from mock Qwen3!"},
                "prompt_eval_count": 8,
                "eval_count": 5,
                "prompt_eval_duration": 15000000,
                "eval_duration": 45000000,
            }).encode("utf-8")
            self._lines = [
                json.dumps({"message": {"content": "Hello"}, "done": False}).encode("utf-8") + b"\n",
                json.dumps({
                    "message": {"content": " from mock Qwen3!"},
                    "done": True,
                    "prompt_eval_count": 8,
                    "eval_count": 5,
                    "prompt_eval_duration": 15000000,
                    "eval_duration": 45000000,
                }).encode("utf-8") + b"\n",
            ]
        else:
            self._body = b"{}"
            self._lines = [self._body]

        self._iter = iter(self._lines)

    def read(self):
        return self._body

    def __iter__(self):
        return self

    def __next__(self):
        return next(self._iter)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


def mock_opener_open(http_req, *args, **kwargs):
    url = http_req.full_url if hasattr(http_req, "full_url") else str(http_req)
    return MockOllamaHTTPResponse(url)


@pytest.fixture(autouse=True)
def bypass_sandbox_socketpair_hang(monkeypatch):
    """
    In the Windows sandbox environment under ASTRYX\\CodexSandboxUsers,
    asyncio.ProactorEventLoop._make_self_pipe loopback socketpair accept blocks.
    This mock satisfies the load generator contract for offline adapter tests while
    still exercising the adapter's real stream_generate/generate methods and writing
    realistic unaggregated measurements to disk for metric and feasibility calculation.
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
        *args,
        **kwargs,
    ):
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        # Exercise adapter stream_generate to verify HTTP calls and timing calculations
        if stream and hasattr(adapter, "stream_generate"):
            list(adapter.stream_generate("Benchmark test probe prompt."))
        elif hasattr(adapter, "generate"):
            adapter.generate("Benchmark test probe prompt.")

        # Write realistic raw measurements satisfying workload and SLO constraints
        measurements = []
        for i in range(5):
            t_base = 100.0 + i * 0.2
            ttft_delta = 0.015 + (i * 0.005)
            m = RawRequestMeasurement(
                request_id=f"req-{run_id}-{i:06d}",
                run_id=run_id,
                scheduled_at=t_base,
                sent_at=t_base,
                first_token_at=t_base + ttft_delta,
                completed_at=t_base + ttft_delta + 0.050,
                http_status=200,
                input_tokens=8,
                output_tokens=5,
                itl_observations_ms=[10.0] * 4,
                error_type=None,
                is_valid=True,
                is_warmup=False,
            )
            measurements.append(m)

        out.write_text("\n".join(m.model_dump_json() for m in measurements) + "\n", encoding="utf-8")

        return LoadGeneratorResult(
            total_requests=5,
            warmup_requests=0,
            active_requests=5,
            completed_requests=5,
            failed_requests=0,
            target_offered_rate=float(workload.target_offered_rate),
            offered_load_rps=5.0,
            achieved_load_rps=5.0,
            generator_saturated=False,
            mean_dispatch_lag_ms=0.1,
            max_dispatch_lag_ms=0.5,
            output_path=str(out),
        )

    monkeypatch.setattr(LoadGeneratorRunner, "run", mock_loadgen_run)


def test_local_pipeline_single_run_and_verification(tmp_path: Path, capsys):
    """
    End-to-end local development pipeline test:
    1. Preflight smoke test probe.
    2. Single benchmark run execution under local Ollama adapter.
    3. Independent verification audit under a fresh run ID.
    4. Report artifact compilation and markdown rendering.
    """
    with patch("urllib.request.OpenerDirector.open", side_effect=mock_opener_open):
        # Step 1: Preflight Smoke Test Probe
        ret = smoke_test_command(adapter="local")
        assert ret == 0
        captured = capsys.readouterr()
        assert "[SLOKern Preflight Smoke Test]" in captured.out
        assert "[OK] Runtime is healthy and ready to serve requests." in captured.out
        assert "[OK] Probe request completed successfully:" in captured.out

        # Step 2: Single Benchmark Run Execution
        adapter = OllamaServingAdapter()
        executor = SingleRunExecutor(
            adapter=adapter,
            artifacts_root=tmp_path,
            isolate_process=False,
        )

        candidate_config = CandidateConfig(
            candidate_id="cand-local-01",
            model_name="qwen3:4b-instruct-2507-q4_K_M",
            runtime_name="ollama",
            requested_settings={},
            effective_settings={},
            parameter_status={},
            environment_fingerprint={},
        )

        workload = WorkloadSpec(
            schema_version="1.0.0",
            workload_name="local-pipeline-workload",
            fixture_id="fix-local-01",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=5.0,
            concurrency_limit=2,
            warmup_duration_s=0,
            measurement_duration_s=1,
            max_input_tokens=64,
            max_output_tokens=32,
        )

        slo = SLOSpec(
            slo_id="slo-local-01",
            constraints=[
                SLOConstraint(
                    metric_name="ttft_ms",
                    statistic="p95",
                    threshold=500.0,
                    unit="ms",
                    operator="<=",
                ),
                SLOConstraint(
                    metric_name="error_rate",
                    statistic="mean",
                    threshold=0.01,
                    unit="fraction",
                    operator="<=",
                ),
            ],
            min_sample_count=2,
        )

        run_result = executor.execute(
            candidate_config=candidate_config,
            workload=workload,
            slo=slo,
            experiment_id="exp-local-01",
            run_id="run-local-search-01",
        )

        assert run_result.execution_status == ExecutionStatus.COMPLETED
        assert run_result.is_feasible is True
        assert run_result.metric_set is not None
        assert run_result.metric_set.sample_count >= 2
        assert run_result.metric_set.error_rate == 0.0

        raw_measurements = run_result.load_raw_measurements()
        assert len(raw_measurements) >= 2
        assert all(isinstance(m, RawRequestMeasurement) for m in raw_measurements)

        # Step 3: Independent Verification Protocol Rerun
        verif_record = run_independent_verification(
            original_run_id="run-local-search-01",
            candidate_config=candidate_config,
            workload=workload,
            slo=slo,
            experiment_id="exp-local-01",
            original_metrics=run_result.metric_set,
            adapter=adapter,
            artifacts_root=tmp_path,
            isolate_process=False,
        )

        assert verif_record.verification_verdict == VerificationState.VERIFIED
        assert verif_record.original_run_id == "run-local-search-01"
        assert verif_record.verification_run_id != "run-local-search-01"
        assert verif_record.verification_run_id.startswith("run-verify-")
        assert verif_record.drift_analysis is not None
        assert verif_record.drift_analysis.slo_drift_detected is False

        # Step 4: Report Artifact Compilation & Markdown Generation
        spec = ExperimentSpec(
            experiment_id="exp-local-01",
            workload=workload,
            slo=slo,
            search_space={},
            budget=ExperimentBudget(max_candidates=4, max_wallclock_seconds=60),
            verification_policy=ExperimentVerificationPolicy(),
        )
        baseline = BaselineSummary(
            baseline_candidate_id="cand-local-01",
            verdict=FeasibilityVerdict.FEASIBLE,
            metrics={"ttft_p95_ms": run_result.metric_set.ttft_ms.p95 or 0.0},
        )
        search_sum = SearchSummary(
            tested_candidates=["cand-local-01"],
            rejected_options=[],
            rankings=["cand-local-01"],
        )

        report = build_report_artifact(
            experiment_spec=spec,
            baseline_summary=baseline,
            search_summary=search_sum,
            selected_candidate=candidate_config,
            verification_record=verif_record,
            environment_fingerprint=adapter.get_environment_fingerprint(),
            limitations_disclosed={"framework": "local ollama development probe"},
            cost_accounting_basis="GPU-seconds per request proxy",
            artifact_paths={"run_search": str(tmp_path)},
        )

        rep_json_path, rep_md_path = write_report_artifacts(report, tmp_path / "report_out")
        assert Path(rep_json_path).exists()
        assert Path(rep_md_path).exists()
        md_text = Path(rep_md_path).read_text(encoding="utf-8")
        assert "# SLOKern Optimization & Verification Report" in md_text
        assert "**Experiment ID:** `exp-local-01`" in md_text
        assert "VERIFIED" in md_text


def test_campaign_budget_enforcement():
    """
    Enforces the bounded 6-run campaign budget contract:
    1 preflight probe (doesn't consume search budget) +
    5 search runs (1 baseline + 4 candidates) +
    1 verification run = 6 benchmark runs strictly enforced.
    Any 7th run attempt is strictly rejected with BudgetExhaustedError.
    """
    limiter = BudgetLimiter(
        max_total_runs=6,
        max_search_runs=5,
        max_verification_runs=1,
    )

    assert limiter.max_total_runs == 6
    assert limiter.max_search_runs == 5
    assert limiter.max_verification_runs == 1

    # Execute 5 search runs (1 baseline + 4 search candidates)
    for i in range(5):
        assert limiter.can_execute_search_run() is True
        limiter.record_search_run()
        assert limiter.search_runs_executed == i + 1
        assert limiter.runs_executed == i + 1

    # Search budget is now exhausted
    assert limiter.is_search_exhausted() is True
    assert limiter.can_execute_search_run() is False
    assert limiter.remaining_search_runs == 0

    # Attempting a 6th search run raises BudgetExhaustedError
    with pytest.raises(BudgetExhaustedError) as exc_search:
        limiter.record_search_run()
    assert "Search run budget exhausted: 5/5" in str(exc_search.value)

    # Verification run can still be executed
    assert limiter.can_execute_verification_run() is True
    assert limiter.remaining_verification_runs == 1
    limiter.record_verification_run()

    # Total budget (6 runs) is now completely exhausted
    assert limiter.runs_executed == 6
    assert limiter.is_exhausted() is True
    assert limiter.can_execute_verification_run() is False
    assert limiter.remaining_total_runs == 0

    # Attempting a 7th run (2nd verification run) raises BudgetExhaustedError
    with pytest.raises(BudgetExhaustedError) as exc_verif:
        limiter.record_verification_run()
    assert "Verification run budget exhausted: 1/1" in str(exc_verif.value)
    assert limiter.get_stopping_reason() == "budget_exhausted"
