"""
Purpose: End-to-end integration test verifying the Frontend-to-Backend HTTP control plane lifecycle (FE-INT-11).
Authority: Aligned with AGENTS.md Section 3, 10, 11 and DEC-0014
"""

import json
import time
from pathlib import Path
from typing import Any, List, Optional

import pytest

from slokern.api.app import handle_api_request
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.engine.loadgen.runner import LoadGeneratorResult, LoadGeneratorRunner


@pytest.fixture(autouse=True)
def bypass_sandbox_socketpair_hang(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    In the Windows Codex sandbox environment, asyncio.ProactorEventLoop._make_self_pipe
    loopback socketpair accept blocks. This mock writes realistic unaggregated measurements
    to disk for metric and feasibility calculation while satisfying loadgen runner contracts.
    """
    def mock_loadgen_run(
        self: Any,
        workload: Any,
        adapter: Any,
        output_path: str,
        run_id: str = "run-001",
        seed: int = 42,
        stream: bool = True,
        prompts: Optional[List[str]] = None,
        artificial_dispatch_delay_ms: float = 0.0,
        *args: Any,
        **kwargs: Any,
    ) -> LoadGeneratorResult:
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)

        cb = kwargs.get("progress_callback")
        if cb and callable(cb):
            cb(25, 25, 12.0)

        if stream and hasattr(adapter, "stream_generate"):
            list(adapter.stream_generate("Benchmark test probe prompt."))
        elif hasattr(adapter, "generate"):
            adapter.generate("Benchmark test probe prompt.")

        measurements = []
        for i in range(25):
            t_base = 100.0 + i * 0.1
            m = RawRequestMeasurement(
                request_id=f"req-{run_id}-{i:06d}",
                run_id=run_id,
                scheduled_at=t_base,
                sent_at=t_base + 0.001,
                first_token_at=t_base + 0.012,
                completed_at=t_base + 0.045,
                http_status=200,
                input_tokens=16,
                output_tokens=16,
                itl_observations_ms=[2.0] * 15,
                error_type=None,
                is_warmup=(i < 5),
                is_valid=True,
            )
            measurements.append(m)

        with open(out, "w", encoding="utf-8") as f:
            for m in measurements:
                f.write(m.model_dump_json() + "\n")

        return LoadGeneratorResult(
            total_requests=25,
            warmup_requests=5,
            active_requests=20,
            completed_requests=20,
            failed_requests=0,
            target_offered_rate=float(workload.target_offered_rate),
            offered_load_rps=10.0,
            achieved_load_rps=10.0,
            generator_saturated=False,
            mean_dispatch_lag_ms=0.5,
            max_dispatch_lag_ms=1.2,
            output_path=str(out.resolve()),
            error=None,
        )

    monkeypatch.setattr(LoadGeneratorRunner, "run", mock_loadgen_run)


def test_full_frontend_api_lifecycle(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Executes the complete frontend workflow through the backend control plane:
    1. GET /api/health
    2. POST /api/smoke-test
    3. POST /api/runs/single
    4. GET /api/runs/{run_id} (polling until completed)
    5. POST /api/runs/verify (independent rerun with fresh ID)
    6. GET /api/reports/{experiment_id} (reproducibility markdown dossier)
    """
    # 1. Health Handshake
    status, _, body = handle_api_request("GET", "/api/health?adapter=fake")
    assert status == 200
    health = json.loads(body)
    assert health["status"] == "ok"
    assert health["runtime"] == "vllm-fake"
    assert health["is_healthy"] is True

    # 2. Preflight Smoke Test Probe
    probe_payload = json.dumps({"adapter": "fake", "prompt": "SLOKern preflight smoke check."})
    status, _, body = handle_api_request("POST", "/api/smoke-test", body=probe_payload)
    assert status == 200
    probe = json.loads(body)
    assert probe["status"] == "success"
    assert probe["status_code"] == 200
    assert probe["output_tokens"] > 0
    assert probe["total_latency_ms"] >= 0

    # 3. Single Run Benchmark Dispatch
    dispatch_payload = json.dumps({
        "adapter": "fake",
        "workload_name": "api-integration-workload",
        "target_offered_rate": 5.0,
        "concurrency_limit": 2,
        "measurement_duration_s": 2,
        "p95_ttft_threshold": 50.0,
        "max_error_rate": 0.05,
    })
    status, _, body = handle_api_request("POST", "/api/runs/single", body=dispatch_payload)
    assert status in (200, 202)
    dispatch = json.loads(body)
    run_id = dispatch["run_id"]
    experiment_id = dispatch["experiment_id"]
    assert run_id.startswith("run")
    assert experiment_id.startswith("exp")

    # 4. Status Polling until completion
    completed = False
    run_data = None
    for _ in range(30):
        status, _, body = handle_api_request("GET", f"/api/runs/{run_id}")
        assert status == 200
        run_data = json.loads(body)
        if run_data["is_completed"]:
            completed = True
            break
        time.sleep(0.15)

    assert completed is True, f"Run {run_id} did not complete in time"
    assert run_data is not None
    assert run_data["execution_status"] == "COMPLETED"
    assert run_data["is_feasible"] is True
    assert run_data["raw_measurements_count"] == 25
    assert run_data["metric_set"] is not None
    assert run_data["metric_set"]["sample_count"] == 20
    assert run_data["metric_set"]["failed_request_count"] == 0

    candidate_id = run_data["candidate_id"]

    # 5. Independent Verification Rerun
    verify_payload = json.dumps({
        "candidate_id": candidate_id,
        "original_run_id": run_id,
        "adapter": "fake",
    })
    status, _, body = handle_api_request("POST", "/api/runs/verify", body=verify_payload)
    assert status == 200
    verif = json.loads(body)
    assert verif["verification_verdict"] == "VERIFIED"
    assert verif["candidate_id"] == candidate_id
    assert verif["original_run_id"] == run_id
    assert verif["verification_run_id"] != run_id
    assert verif["drift_analysis"] is not None
    assert len(verif["drift_analysis"]["metric_comparisons"]) > 0

    # 6. Dossier Report Retrieval
    status, _, body = handle_api_request("GET", f"/api/reports/{experiment_id}")
    assert status == 200
    report = json.loads(body)
    assert report["experiment_id"] == experiment_id
    assert "# SLOKern Optimization & Verification" in report["markdown"]
    assert report["artifact"] is not None

    # 7. Raw JSONL Trace Retrieval
    status, headers, body = handle_api_request("GET", f"/api/runs/{run_id}/trace")
    assert status == 200
    assert "application/x-ndjson" in headers["Content-Type"]
    assert f"raw_measurements_{run_id}.jsonl" in headers["Content-Disposition"]
    assert len(body.strip().split(b"\n")) == 25

    # 8. Verification Run Trace Retrieval
    verif_run_id = verif["verification_run_id"]
    status, headers, body = handle_api_request("GET", f"/api/runs/{verif_run_id}/trace")
    assert status == 200
    assert "application/x-ndjson" in headers["Content-Type"]
    assert f"raw_measurements_{verif_run_id}.jsonl" in headers["Content-Disposition"]

    # 9. List Recent Runs
    status, _, body = handle_api_request("GET", "/api/runs")
    assert status == 200
    recent_runs = json.loads(body)
    assert any(r["run_id"] == run_id for r in recent_runs)

    # 10. Persistence check: Clear in-memory cache and retrieve run from disk
    from slokern.api.routes.runs import ACTIVE_RUNS, RUNS_LOCK
    with RUNS_LOCK:
        ACTIVE_RUNS.clear()

    status, _, body = handle_api_request("GET", f"/api/runs/{run_id}")
    assert status == 200
    disk_run = json.loads(body)
    assert disk_run["run_id"] == run_id
    assert disk_run["is_completed"] is True
    assert disk_run["execution_status"] == "COMPLETED"
    assert disk_run["raw_measurements_count"] == 25

    # 11. Nonexistent Run 404 Check
    status, _, body = handle_api_request("GET", "/api/runs/nonexistent-run-99999")
    assert status == 404
    assert json.loads(body).get("error") == "Run not found"

    # 12. Security: Path Traversal 400 Check
    status, _, body = handle_api_request("GET", "/api/runs/../../etc/passwd")
    assert status == 400
    assert "invalid run_id format" in json.loads(body).get("error", "").lower()

