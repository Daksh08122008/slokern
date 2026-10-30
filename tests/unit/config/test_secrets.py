"""
Purpose: Unit tests for automatic credential bootstrap and safe secret status reporting.
Owner: Rajdeep
"""

import json
import os
from pathlib import Path
import stat
import sys
import pytest

from slokern.config.secrets import (
    SecretSourceStatus,
    get_secret_status,
    is_placeholder_secret,
    load_runtime_secrets,
    setup_credentials_help,
    validate_endpoint_url,
    validate_required_secrets,
)


def test_placeholder_secret_detection():
    assert is_placeholder_secret("") is True
    assert is_placeholder_secret(None) is True
    assert is_placeholder_secret("   ") is True
    assert is_placeholder_secret("your-nebius-api-key") is True
    assert is_placeholder_secret("placeholder") is True
    assert is_placeholder_secret("<api_key>") is True
    assert is_placeholder_secret("valid_secret_token_12345") is False


def test_validate_endpoint_url():
    # HTTPS is valid
    ok, err = validate_endpoint_url("https://api.studio.nebius.ai/v1")
    assert ok is True
    assert err is None

    # Loopback HTTP is valid for testing
    ok, err = validate_endpoint_url("http://127.0.0.1:11434")
    assert ok is True
    assert err is None

    ok, err = validate_endpoint_url("http://localhost:8000")
    assert ok is True
    assert err is None

    # Remote HTTP is rejected
    ok, err = validate_endpoint_url("http://remote-api.nebius.ai/v1")
    assert ok is False
    assert "Insecure HTTP scheme rejected" in err

    # Userinfo in URL is rejected
    ok, err = validate_endpoint_url("https://user:pass@api.studio.nebius.ai/v1")
    assert ok is False
    assert "URL credentials (userinfo) are strictly prohibited" in err

    # Invalid scheme
    ok, err = validate_endpoint_url("ftp://api.studio.nebius.ai/v1")
    assert ok is False
    assert "Invalid scheme" in err


def test_env_var_precedence(monkeypatch, tmp_path):
    # Setup both env var and secrets file
    monkeypatch.setenv("NEBIUS_API_KEY", "env-key-value-12345")

    secrets_file = tmp_path / "secrets.env"
    secrets_file.touch(mode=0o600)
    secrets_file.write_text("NEBIUS_API_KEY=file-key-value-99999\n", encoding="utf-8")
    monkeypatch.setenv("SLOKERN_SECRETS_FILE", str(secrets_file))

    status = get_secret_status("NEBIUS_API_KEY", secrets_file=secrets_file)
    assert status.status == SecretSourceStatus.AVAILABLE_FROM_PROCESS_ENV
    assert status.is_available is True
    assert "Process environment" in status.source_description

    loaded = load_runtime_secrets(force_reload=True, secrets_file=secrets_file)
    assert loaded["NEBIUS_API_KEY"] == "env-key-value-12345"
    assert os.environ["NEBIUS_API_KEY"] == "env-key-value-12345"


def test_local_secrets_file_discovery(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)

    secrets_file = tmp_path / "my_secrets.env"
    secrets_file.touch(mode=0o600)
    secrets_file.write_text(
        "NEBIUS_API_KEY=file-key-from-custom-path-12345\n"
        "NEBIUS_BASE_URL=https://custom.endpoint.nebius.ai/v1\n",
        encoding="utf-8"
    )

    status = get_secret_status("NEBIUS_API_KEY", secrets_file=secrets_file)
    assert status.status == SecretSourceStatus.AVAILABLE_FROM_LOCAL_SECRET_FILE
    assert status.is_available is True
    assert secrets_file.name in status.source_description

    loaded = load_runtime_secrets(force_reload=True, secrets_file=secrets_file)
    assert loaded["NEBIUS_API_KEY"] == "file-key-from-custom-path-12345"
    assert os.environ["NEBIUS_API_KEY"] == "file-key-from-custom-path-12345"
    assert os.environ["NEBIUS_BASE_URL"] == "https://custom.endpoint.nebius.ai/v1"


def test_json_secrets_file(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    secrets_file = tmp_path / "secrets.json"
    secrets_file.touch(mode=0o600)
    secrets_file.write_text(
        json.dumps({"NEBIUS_API_KEY": "json-secret-key-12345"}),
        encoding="utf-8"
    )

    status = get_secret_status("NEBIUS_API_KEY", secrets_file=secrets_file)
    assert status.status == SecretSourceStatus.AVAILABLE_FROM_LOCAL_SECRET_FILE
    assert status.is_available is True

    loaded = load_runtime_secrets(force_reload=True, secrets_file=secrets_file)
    assert loaded["NEBIUS_API_KEY"] == "json-secret-key-12345"


def test_missing_credentials(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    empty_file = tmp_path / "empty.env"
    empty_file.touch(mode=0o600)
    empty_file.write_text("", encoding="utf-8")

    status = get_secret_status("NEBIUS_API_KEY", secrets_file=empty_file)
    assert status.status == SecretSourceStatus.MISSING
    assert status.is_available is False


def test_placeholder_in_env_var(monkeypatch):
    monkeypatch.setenv("NEBIUS_API_KEY", "your-nebius-api-key")

    status = get_secret_status("NEBIUS_API_KEY")
    assert status.status == SecretSourceStatus.INVALID_CONFIGURATION
    assert status.is_available is False
    assert "placeholder" in status.warning.lower()


def test_validate_required_secrets(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    all_ok, res = validate_required_secrets(secrets_file=tmp_path / "nonexistent")
    assert all_ok is False
    assert res["NEBIUS_API_KEY"].is_available is False

    monkeypatch.setenv("NEBIUS_API_KEY", "valid-key-12345")
    all_ok, res = validate_required_secrets()
    assert all_ok is True
    assert res["NEBIUS_API_KEY"].is_available is True


def test_keyring_fallback(monkeypatch):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    class MockKeyring:
        @staticmethod
        def get_password(service, username):
            if service == "slokern" and username == "nebius_api_key":
                return "keyring-stored-secret-12345"
            return None

    monkeypatch.setattr("slokern.config.secrets.sys.modules", {**sys.modules, "keyring": MockKeyring})
    import slokern.config.secrets as s_mod
    monkeypatch.setattr(s_mod, "_read_from_keyring", lambda service, user: "keyring-stored-secret-12345")

    status = get_secret_status("NEBIUS_API_KEY", secrets_file=Path("nonexistent"))
    assert status.status == SecretSourceStatus.AVAILABLE_FROM_CREDENTIAL_STORE
    assert status.is_available is True


def test_posix_permissions_rejected(monkeypatch, tmp_path):
    if os.name != "posix":
        pytest.skip("POSIX permissions test only applies to POSIX platforms")

    secrets_file = tmp_path / "permissive.env"
    secrets_file.touch(mode=0o600)
    secrets_file.write_text("NEBIUS_API_KEY=test-posix-key\n")
    # Set 0o666 (group/world readable)
    secrets_file.chmod(0o666)

    from slokern.config.secrets import _check_file_permissions
    is_valid, warning = _check_file_permissions(secrets_file)
    assert is_valid is False
    assert warning is not None
    assert "chmod 600" in warning


def test_default_discovery_does_not_read_implicit_dotenv(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("SLOKERN_SECRETS_FILE", raising=False)
    (tmp_path / ".env").write_text("NEBIUS_API_KEY=unrequested-local-secret\n", encoding="utf-8")

    assert get_secret_status("NEBIUS_API_KEY").status == SecretSourceStatus.MISSING


def test_validate_endpoint_url_extended():
    # Empty / whitespace
    ok, err = validate_endpoint_url("")
    assert ok is False
    ok, err = validate_endpoint_url("   ")
    assert ok is False

    # Missing host / domain
    ok, err = validate_endpoint_url("https://")
    assert ok is False
    assert "must contain a valid host" in err

    ok, err = validate_endpoint_url("https:///path")
    assert ok is False
    assert "must contain a valid host" in err

    # Invalid port
    ok, err = validate_endpoint_url("https://api.studio.nebius.ai:invalidport")
    assert ok is False
    assert "invalid port" in err.lower()


def test_explicit_secrets_file_errors(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    # Directory as secrets file -> rejected as INVALID_CONFIGURATION
    dir_path = tmp_path / "secrets_dir"
    dir_path.mkdir()
    status = get_secret_status("NEBIUS_API_KEY", secrets_file=dir_path)
    assert status.status == SecretSourceStatus.INVALID_CONFIGURATION
    assert "is a directory" in status.warning


def test_secrets_file_placeholder_detection(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    f = tmp_path / "placeholder.env"
    f.touch(mode=0o600)
    f.write_text("NEBIUS_API_KEY=your-nebius-api-key\n", encoding="utf-8")
    status = get_secret_status("NEBIUS_API_KEY", secrets_file=f)
    assert status.status == SecretSourceStatus.INVALID_CONFIGURATION
    assert "placeholder" in status.warning.lower()


def test_secrets_file_shell_syntax_and_comments(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)

    f = tmp_path / "shell_syntax.env"
    f.touch(mode=0o600)
    f.write_text(
        'export NEBIUS_API_KEY="shell-parsed-key-12345"\n'
        'NEBIUS_BASE_URL=https://custom.endpoint.ai/v1 # inline comment\n',
        encoding="utf-8"
    )
    loaded = load_runtime_secrets(force_reload=True, secrets_file=f)
    assert loaded["NEBIUS_API_KEY"] == "shell-parsed-key-12345"
    assert loaded["NEBIUS_BASE_URL"] == "https://custom.endpoint.ai/v1"


def test_runtime_secrets_caching(monkeypatch, tmp_path):
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)

    f = tmp_path / "cached_secrets.env"
    f.touch(mode=0o600)
    f.write_text("NEBIUS_API_KEY=first-key-value\n", encoding="utf-8")

    loaded1 = load_runtime_secrets(force_reload=True, secrets_file=f)
    assert loaded1["NEBIUS_API_KEY"] == "first-key-value"

    # Modify file on disk; without force_reload, cached value is returned
    f.touch(mode=0o600)
    f.write_text("NEBIUS_API_KEY=second-key-value\n", encoding="utf-8")
    loaded2 = load_runtime_secrets(force_reload=False, secrets_file=f)
    assert loaded2["NEBIUS_API_KEY"] == "first-key-value"

    # With force_reload, cache is invalidated
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    loaded3 = load_runtime_secrets(force_reload=True, secrets_file=f)
    assert loaded3["NEBIUS_API_KEY"] == "second-key-value"


