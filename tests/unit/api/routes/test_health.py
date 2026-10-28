"""
Purpose: Unit tests for api/routes/health.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 10 and DEC-0014
"""

from slokern.api.routes.health import get_health, run_smoke_probe


def test_get_health_fake() -> None:
    res = get_health(adapter_name="fake")
    assert res["status"] == "ok"
    assert res["runtime"] == "vllm-fake"
    assert res["is_healthy"] is True
    assert res["fingerprint"]["is_simulated"] is True


def test_run_smoke_probe_fake() -> None:
    res = run_smoke_probe(adapter_name="fake", prompt="Health test probe")
    assert res["status"] == "success"
    assert res["status_code"] == 200
    assert res["first_token_latency_ms"] is not None
    assert res["total_latency_ms"] > 0
    assert res["input_tokens"] > 0
    assert res["output_tokens"] > 0
    assert res["error"] is None


def test_get_health_invalid_adapter() -> None:
    res = get_health(adapter_name="nonexistent_runtime")
    assert res["status"] == "error"
    assert res["is_healthy"] is False
