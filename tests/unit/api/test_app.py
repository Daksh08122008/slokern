"""
Purpose: Unit tests for slokern.api.app and control plane routes.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 10, 11 and DEC-0014
"""

import json
from pathlib import Path
import time
import pytest

from slokern.api.app import handle_api_request
from slokern.contracts.enums import ExecutionStatus, FeasibilityVerdict


def test_api_options_preflight():
    status, headers, body = handle_api_request("OPTIONS", "/api/health")
    assert status == 200
    assert headers["Access-Control-Allow-Origin"] == "*"
    assert "POST" in headers["Access-Control-Allow-Methods"]


def test_api_404_not_found():
    status, headers, body = handle_api_request("GET", "/api/nonexistent")
    assert status == 404
    data = json.loads(body.decode("utf-8"))
    assert "error" in data


def test_api_health_fake_adapter():
    status, headers, body = handle_api_request("GET", "/api/health?adapter=fake")
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["status"] == "ok"
    assert data["runtime"] == "vllm-fake"
    assert data["is_healthy"] is True
    assert data["fingerprint"]["is_simulated"] is True


def test_api_smoke_test_fake_adapter():
    payload = {"adapter": "fake", "prompt": "Test smoke probe"}
    status, headers, body = handle_api_request("POST", "/api/smoke-test", body=payload)
    assert status == 200
    data = json.loads(body.decode("utf-8"))
    assert data["status"] == "success"
    assert data["runtime"] == "vllm-fake"
    assert data["first_token_latency_ms"] is not None
    assert data["total_latency_ms"] > 0
    assert data["output_tokens"] > 0


def test_api_single_run_and_status(tmp_path: Path):
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


def test_api_verification_run(tmp_path: Path):
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
