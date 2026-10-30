"""
Purpose: Unit tests for slokern.api.app and control plane routes.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 10, 11 and DEC-0014
"""

import json
import time
from pathlib import Path

from slokern.api.app import handle_api_request
from slokern.contracts.enums import ExecutionStatus, FeasibilityVerdict


def test_api_options_preflight() -> None:
    status, headers, body = handle_api_request("OPTIONS", "/api/health")
    assert status == 200
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert "POST" in headers["Access-Control-Allow-Methods"]


def test_api_404_not_found() -> None:
    status, headers, body = handle_api_request("GET", "/api/nonexistent")
    assert status == 404
    data = json.loads(body.decode("utf-8"))
    assert "error" in data


def test_api_health_fake_adapter() -> None:
    status, headers, body = handle_api_request("GET", "/api/health?adapter=fake")
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["status"] == "ok"
    assert data["runtime"] == "vllm-fake"
    assert data["is_healthy"] is True
    assert data["fingerprint"]["is_simulated"] is True


def test_api_smoke_test_fake_adapter(tmp_path: Path) -> None:
    payload = {"adapter": "fake", "prompt": "Test smoke probe"}
    status, headers, body = handle_api_request("POST", "/api/smoke-test", body=payload, artifacts_root=str(tmp_path))
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["status"] == "success"
    assert data["runtime"] == "vllm-fake"
    assert data["first_token_latency_ms"] is not None
    assert data["total_latency_ms"] > 0
    assert data["output_tokens"] > 0


def test_api_single_run_and_status(tmp_path: Path) -> None:
    payload = {
        "adapter": "fake",
        "workload": {
            "schema_version": "1.0.0",
            "workload_name": "test-api-workload",
            "fixture_id": "fix-api-01",
            "arrival_mode": "constant",
            "target_offered_rate": 5.0,
            "concurrency_limit": 2,
            "warmup_duration_s": 0,
            "measurement_duration_s": 1,
            "max_input_tokens": 32,
            "max_output_tokens": 16,
        },
        "slo": {
            "slo_id": "slo-api-01",
            "constraints": [
                {
                    "metric_name": "ttft_ms",
                    "statistic": "p95",
                    "threshold": 5000.0,
                    "unit": "ms",
                    "operator": "<=",
                }
            ],
            "min_sample_count": 2,
        },
    }

    status, headers, body = handle_api_request(
        "POST", "/api/runs/single", body=payload, artifacts_root=str(tmp_path)
    )
    assert status == 200
    dispatch_data = json.loads(body.decode("utf-8"))
    assert "run_id" in dispatch_data
    run_id = dispatch_data["run_id"]

    # Poll status until completed (timeout 10s)
    t_start = time.time()
    completed = False
    result_data = {}
    while time.time() - t_start < 10.0:
        s_status, _, s_body = handle_api_request(
            "GET", f"/api/runs/{run_id}", artifacts_root=str(tmp_path)
        )
        assert s_status == 200
        result_data = json.loads(s_body.decode("utf-8"))
        if result_data.get("is_completed"):
            completed = True
            break
        time.sleep(0.1)

    assert completed is True
    assert result_data["execution_status"] == ExecutionStatus.COMPLETED.value
    assert result_data["is_feasible"] is True
    assert result_data["metric_set"] is not None
    assert result_data["feasibility_result"]["overall_verdict"] == FeasibilityVerdict.FEASIBLE.value


def test_api_verification_run(tmp_path: Path) -> None:
    payload = {
        "adapter": "fake",
        "candidate_id": "cand-api-test-01",
        "original_run_id": "run-orig-01",
        "workload": {
            "schema_version": "1.0.0",
            "workload_name": "test-verify-workload",
            "fixture_id": "fix-verify-01",
            "arrival_mode": "constant",
            "target_offered_rate": 5.0,
            "concurrency_limit": 2,
            "warmup_duration_s": 0,
            "measurement_duration_s": 1,
            "max_input_tokens": 32,
            "max_output_tokens": 16,
        },
        "slo": {
            "slo_id": "slo-verify-01",
            "constraints": [
                {
                    "metric_name": "ttft_ms",
                    "statistic": "p95",
                    "threshold": 5000.0,
                    "unit": "ms",
                    "operator": "<=",
                }
            ],
            "min_sample_count": 2,
        },
    }

    status, headers, body = handle_api_request(
        "POST", "/api/runs/verify", body=payload, artifacts_root=str(tmp_path)
    )
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert "verification_id" in data
    assert "verification_run_id" in data
    assert data["verification_run_id"] != "run-orig-01"
    assert data["verification_verdict"] in ("VERIFIED", "VERIFICATION_FAILED")
    assert data.get("metric_set") is not None
    assert data.get("feasibility_result") is not None


def test_api_verification_run_preserves_experiment_id(tmp_path: Path) -> None:
    payload = {
        "adapter": "fake",
        "experiment_id": "exp-custom-verification-99",
        "candidate_id": "cand-api-test-02",
        "original_run_id": "run-orig-02",
        "workload": {
            "schema_version": "1.0.0",
            "workload_name": "test-verify-workload",
            "fixture_id": "fix-verify-02",
            "arrival_mode": "constant",
            "target_offered_rate": 5.0,
            "concurrency_limit": 2,
            "warmup_duration_s": 0,
            "measurement_duration_s": 1,
            "max_input_tokens": 32,
            "max_output_tokens": 16,
        },
        "slo": {
            "slo_id": "slo-verify-02",
            "constraints": [
                {
                    "metric_name": "ttft_ms",
                    "statistic": "p95",
                    "threshold": 5000.0,
                    "unit": "ms",
                    "operator": "<=",
                }
            ],
            "min_sample_count": 2,
        },
    }

    status, headers, body = handle_api_request(
        "POST", "/api/runs/verify", body=payload, artifacts_root=str(tmp_path)
    )
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["experiment_id"] == "exp-custom-verification-99"


def test_api_run_trace_success(tmp_path: Path) -> None:
    """GET /api/runs/<run_id>/trace returns 200 with application/x-ndjson content."""
    run_id = "run-trace-test-01"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    trace_file = run_dir / "raw_measurements.jsonl"
    line1 = json.dumps({"request_id": "req-1", "ttft_ms": 12.5}) + "\n"
    line2 = json.dumps({"request_id": "req-2", "ttft_ms": 14.1}) + "\n"
    trace_file.write_bytes((line1 + line2).encode("utf-8"))

    status, headers, body = handle_api_request(
        "GET", f"/api/runs/{run_id}/trace", artifacts_root=str(tmp_path)
    )
    assert status == 200
    assert "application/x-ndjson" in headers["Content-Type"]
    assert f"raw_measurements_{run_id}.jsonl" in headers["Content-Disposition"]
    assert body.decode("utf-8").replace("\r\n", "\n") == line1 + line2


def test_api_run_trace_not_found(tmp_path: Path) -> None:
    """GET /api/runs/<run_id>/trace returns 404 when trace file does not exist."""
    status, headers, body = handle_api_request(
        "GET", "/api/runs/nonexistent-run-999/trace", artifacts_root=str(tmp_path)
    )
    assert status == 404
    data = json.loads(body.decode("utf-8"))
    assert "not found" in data["error"].lower()


def test_api_run_trace_invalid_run_id(tmp_path: Path) -> None:
    """GET /api/runs/<run_id>/trace returns 400 for invalid/malicious run_id characters."""
    status, headers, body = handle_api_request(
        "GET", "/api/runs/../../etc/passwd/trace", artifacts_root=str(tmp_path)
    )
    assert status == 400
    data = json.loads(body.decode("utf-8"))
    assert "invalid run_id" in data["error"].lower()


def test_api_run_trace_empty_file_returns_404(tmp_path: Path) -> None:
    """GET /api/runs/<run_id>/trace returns 404 when file exists but is 0 bytes."""
    run_id = "run-trace-empty"
    run_dir = tmp_path / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    empty_file = run_dir / "raw_measurements.jsonl"
    empty_file.touch()

    status, headers, body = handle_api_request(
        "GET", f"/api/runs/{run_id}/trace", artifacts_root=str(tmp_path)
    )
    assert status == 404
    data = json.loads(body.decode("utf-8"))
    assert "not found" in data["error"].lower()


def test_api_get_run_not_found_returns_404(tmp_path: Path) -> None:
    """GET /api/runs/<run_id> returns 404 when run does not exist."""
    status, headers, body = handle_api_request(
        "GET", "/api/runs/run-nonexistent-12345", artifacts_root=str(tmp_path)
    )
    assert status == 404
    data = json.loads(body.decode("utf-8"))
    assert data.get("error") == "Run not found"


def test_api_get_run_invalid_run_id_returns_400(tmp_path: Path) -> None:
    """GET /api/runs/<run_id> returns 400 for path traversal or invalid characters."""
    status, headers, body = handle_api_request(
        "GET", "/api/runs/../../etc/passwd", artifacts_root=str(tmp_path)
    )
    assert status == 400
    data = json.loads(body.decode("utf-8"))
    assert "invalid run_id" in data["error"].lower()


def test_api_get_report_invalid_experiment_id_returns_400(tmp_path: Path) -> None:
    """GET /api/reports/<experiment_id> returns 400 for invalid characters."""
    status, headers, body = handle_api_request(
        "GET", "/api/reports/../../etc/shadow", artifacts_root=str(tmp_path)
    )
    assert status == 400
    data = json.loads(body.decode("utf-8"))
    assert "invalid experiment_id" in data["error"].lower()


def test_api_get_run_persisted_in_experiments_dir(tmp_path: Path) -> None:
    """GET /api/runs/<run_id> retrieves runs from experiments/*/runs/<run_id>."""
    run_id = "run-persisted-disk-01"
    exp_id = "exp-persisted-disk-01"
    run_dir = tmp_path / "experiments" / exp_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    record_data = {
        "run_id": run_id,
        "experiment_id": exp_id,
        "candidate_id": "cand-test-01",
        "is_verification_run": False,
        "execution_status": "COMPLETED",
        "started_at": "2026-10-28T00:00:00Z",
        "completed_at": "2026-10-28T00:00:05Z",
        "raw_artifact_uri": str(run_dir / "raw_measurements.jsonl"),
        "execution_error": None,
    }
    (run_dir / "run_record.json").write_text(json.dumps(record_data), encoding="utf-8")

    metrics_data = {
        "run_id": run_id,
        "sample_count": 10,
        "valid_count": 10,
        "warmup_count": 2,
        "error_count": 0,
        "failed_request_count": 0,
    }
    (run_dir / "metrics.json").write_text(json.dumps(metrics_data), encoding="utf-8")

    feas_data = {
        "run_id": run_id,
        "slo_id": "slo-01",
        "evaluator_version": "1.0.0",
        "policy_version": "1.0.0",
        "overall_verdict": "FEASIBLE",
        "validity_status": "VALID",
        "constraint_evaluations": [],
        "reasons": [],
    }
    (run_dir / "feasibility.json").write_text(json.dumps(feas_data), encoding="utf-8")

    raw_line = json.dumps({"request_id": "req-1", "is_valid": True}) + "\n"
    (run_dir / "raw_measurements.jsonl").write_text(raw_line, encoding="utf-8")

    status, headers, body = handle_api_request(
        "GET", f"/api/runs/{run_id}", artifacts_root=str(tmp_path)
    )
    assert status == 200
    res = json.loads(body.decode("utf-8"))
    assert res["run_id"] == run_id
    assert res["experiment_id"] == exp_id
    assert res["execution_status"] == "COMPLETED"
    assert res["is_completed"] is True
    assert res["is_feasible"] is True
    assert res["raw_measurements_count"] == 1
    assert res["artifact_paths"]["raw_measurements"] == str(run_dir / "raw_measurements.jsonl")


def test_api_list_recent_runs_from_experiments_dir(tmp_path: Path) -> None:
    """list_recent_runs discovers runs persisted under experiments/*/runs/*."""
    from slokern.api.routes.runs import list_recent_runs

    run_id = "run-recent-exp-01"
    exp_id = "exp-recent-01"
    run_dir = tmp_path / "experiments" / exp_id / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    record_data = {
        "run_id": run_id,
        "experiment_id": exp_id,
        "candidate_id": "cand-recent-01",
        "is_verification_run": False,
        "execution_status": "COMPLETED",
        "started_at": "2026-10-28T00:00:00Z",
        "completed_at": "2026-10-28T00:00:05Z",
        "raw_artifact_uri": str(run_dir / "raw_measurements.jsonl"),
        "execution_error": None,
    }
    (run_dir / "run_record.json").write_text(json.dumps(record_data), encoding="utf-8")

    recent = list_recent_runs(artifacts_root=str(tmp_path))
    assert any(r["run_id"] == run_id for r in recent)


