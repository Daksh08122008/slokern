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
