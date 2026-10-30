"""
Purpose: Unit tests for smoke-test CLI command.
Owner: Rajdeep
"""

from unittest.mock import MagicMock, patch

from slokern.cli.commands.smoke_test import smoke_test_command
from slokern.engine.serving.base import ConfigurationError, ServingResponse


def test_smoke_test_fake_adapter(capsys):
    ret = smoke_test_command(adapter="fake")
    assert ret == 0
    captured = capsys.readouterr()
    assert "[SLOKern Preflight Smoke Test]" in captured.out
    assert "DEMO DATA" in captured.out
    assert "[OK] Runtime is healthy" in captured.out
    assert "[OK] Probe request completed successfully" in captured.out


def test_smoke_test_invalid_backend(capsys):
    ret = smoke_test_command(adapter="nonexistent")
    assert ret == 1
    captured = capsys.readouterr()
    assert "[FAIL] Invalid Backend" in captured.err


def test_smoke_test_configuration_error(capsys):
    with patch("slokern.cli.commands.smoke_test.create_serving_adapter", side_effect=ConfigurationError("Missing auth")):
        ret = smoke_test_command(adapter="nebius")
        assert ret == 1
        captured = capsys.readouterr()
        assert "[FAIL] Configuration Error: Missing auth" in captured.err


def test_smoke_test_unhealthy_endpoint(capsys):
    mock_adapter = MagicMock()
    mock_adapter.runtime_name = "test-runtime"
    mock_adapter.model_name = "test-model"
    mock_adapter.get_environment_fingerprint.return_value = {"provider": "test"}
    mock_adapter.health_check.return_value = False

    with patch("slokern.cli.commands.smoke_test.create_serving_adapter", return_value=mock_adapter):
        ret = smoke_test_command(adapter="local")
        assert ret == 1
        captured = capsys.readouterr()
        assert "[FAIL] Health check failed" in captured.err


def test_smoke_test_probe_request_error(capsys):
    mock_adapter = MagicMock()
    mock_adapter.runtime_name = "test-runtime"
    mock_adapter.model_name = "test-model"
    mock_adapter.get_environment_fingerprint.return_value = {"provider": "test"}
    mock_adapter.health_check.return_value = True
    mock_adapter.generate.return_value = ServingResponse(
        request_id="req-1",
        run_id="run-1",
        input_tokens=0,
        output_tokens=0,
        text="",
        status_code=500,
        error="Internal Server Error",
    )

    with patch("slokern.cli.commands.smoke_test.create_serving_adapter", return_value=mock_adapter):
        ret = smoke_test_command(adapter="local")
        assert ret == 1
        captured = capsys.readouterr()
        assert "[FAIL] Request failed with HTTP 500: Internal Server Error" in captured.err


def test_smoke_test_artifact_persistence(tmp_path):
    artifact_file = tmp_path / "smoke_result.json"
    ret = smoke_test_command(adapter="fake", artifact_path=str(artifact_file), stream=True)
    assert ret == 0
    assert artifact_file.exists()

    import json
    data = json.loads(artifact_file.read_text(encoding="utf-8"))
    assert data["status"] == "PASSED"
    assert data["adapter"] == "vllm-fake"
    assert data["evidence_classification"] == "DEMO DATA"
    assert data["health_check"] is True
    assert data["probe_request"]["status_code"] == 200
    assert data["probe_request"]["ttft_ms"] > 0
    assert data["streaming_probe"]["stream_success"] is True


def test_smoke_test_one_request_enforcement():
    mock_adapter = MagicMock()
    mock_adapter.runtime_name = "test-runtime"
    mock_adapter.model_name = "test-model"
    mock_adapter.get_environment_fingerprint.return_value = {"provider": "test"}
    mock_adapter.health_check.return_value = True
    mock_adapter.generate.return_value = ServingResponse(
        request_id="smoke-test-probe-01",
        run_id="run-smoke",
        input_tokens=5,
        output_tokens=10,
        text="Sample output text",
        status_code=200,
        error=None,
    )

    with patch("slokern.cli.commands.smoke_test.create_serving_adapter", return_value=mock_adapter):
        ret = smoke_test_command(adapter="local", stream=False)
        assert ret == 0
        # Exactly one call to generate, zero calls to stream_generate
        assert mock_adapter.generate.call_count == 1
        assert mock_adapter.stream_generate.call_count == 0


def test_smoke_test_one_request_enforcement_streaming():
    from slokern.engine.serving.base import TokenChunk
    mock_adapter = MagicMock()
    mock_adapter.runtime_name = "test-runtime"
    mock_adapter.model_name = "test-model"
    mock_adapter.get_environment_fingerprint.return_value = {"provider": "test"}
    mock_adapter.health_check.return_value = True
    mock_adapter.stream_generate.return_value = [
        TokenChunk(token="VERIFIED", token_id=1, index=0, timestamp_ms=15.0, latency_ms=15.0, is_last=True)
    ]

    with patch("slokern.cli.commands.smoke_test.create_serving_adapter", return_value=mock_adapter):
        ret = smoke_test_command(adapter="local", stream=True)
        assert ret == 0
        # Exactly one call to stream_generate, zero calls to generate
        assert mock_adapter.stream_generate.call_count == 1
        assert mock_adapter.generate.call_count == 0
