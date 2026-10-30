"""
Purpose: Unit tests for `slokern credentials` command logic (status, setup, validate).
Owner: Rajdeep
"""

from io import StringIO
import json
from unittest.mock import MagicMock, patch
import urllib.error
import pytest

from slokern.cli.commands.credentials import (
    credentials_setup_command,
    credentials_status_command,
    credentials_validate_command,
)


def test_credentials_status_missing(monkeypatch, capsys):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    ret = credentials_status_command()
    assert ret == 1
    err = capsys.readouterr().err
    assert "ACTION REQUIRED" in err


def test_credentials_status_available(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-api-key-12345")
    ret = credentials_status_command()
    assert ret == 0
    out = capsys.readouterr().out
    assert "AVAILABLE_FROM_PROCESS_ENV" in out
    # Verify no secret value printed
    assert "test-api-key-12345" not in out


def test_credentials_status_json(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-api-key-12345")
    ret = credentials_status_command(json_output=True)
    assert ret == 0
    out = capsys.readouterr().out
    data = json.loads(out)
    assert data["NEBIUS_API_KEY"]["is_available"] is True
    assert "AVAILABLE_FROM_PROCESS_ENV" in data["NEBIUS_API_KEY"]["status"]
    # Verify no secret value in json
    assert "test-api-key-12345" not in out


def test_credentials_setup(capsys):
    ret = credentials_setup_command()
    assert ret == 0
    out = capsys.readouterr().out
    assert "SLOKern Secure Credential Setup Instructions" in out


def test_credentials_validate_offline_success(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-api-key-12345")
    ret = credentials_validate_command(offline=True)
    assert ret == 0
    out = capsys.readouterr().out
    assert "Offline Validation Passed" in out


def test_credentials_validate_missing_fails(monkeypatch, capsys):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    ret = credentials_validate_command(offline=True)
    assert ret == 1
    err = capsys.readouterr().err
    assert "Missing Credentials" in err


def test_credentials_validate_online_success(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-api-key-12345")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp

    with patch("urllib.request.urlopen", return_value=mock_resp):
        ret = credentials_validate_command(offline=False)
        assert ret == 0
        out = capsys.readouterr().out
        assert "Authentication Successful" in out


def test_credentials_validate_online_401(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-api-key-12345")

    http_err = urllib.error.HTTPError(
        url="https://api.studio.nebius.ai/v1/models",
        code=401,
        msg="Unauthorized",
        hdrs={},
        fp=None,
    )

    with patch("urllib.request.urlopen", side_effect=http_err):
        ret = credentials_validate_command(offline=False)
        assert ret == 1
        err = capsys.readouterr().err
        assert "401 Unauthorized" in err


def test_credentials_validate_online_timeout(monkeypatch, capsys):
    monkeypatch.setenv("NEBIUS_API_KEY", "test-api-key-12345")

    with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
        ret = credentials_validate_command(offline=False)
        assert ret == 1
        err = capsys.readouterr().err
        assert "Timed Out" in err


def test_credentials_status_invalid_file(monkeypatch, capsys, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    # 1. Directory as secrets file -> INVALID_CONFIGURATION
    dir_path = tmp_path / "secrets_dir"
    dir_path.mkdir()
    ret = credentials_status_command(secrets_file=str(dir_path))
    assert ret == 1
    out = capsys.readouterr().out
    assert "INVALID_CONFIGURATION" in out

    # 2. File with placeholder -> INVALID_CONFIGURATION
    ph_file = tmp_path / "placeholder.env"
    ph_file.write_text("NEBIUS_API_KEY=your-nebius-api-key\n", encoding="utf-8")
    ret2 = credentials_status_command(secrets_file=str(ph_file))
    assert ret2 == 1
    out2 = capsys.readouterr().out
    assert "INVALID_CONFIGURATION" in out2


