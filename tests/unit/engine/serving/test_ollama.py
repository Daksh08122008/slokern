"""
Purpose: Unit tests for OllamaServingAdapter, loopback redirect boundaries, and timing.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with DEC-0014 and AGENTS.md Section 1, 3, 9, 12
"""

import io
import json
import os
import urllib.error
import urllib.request
from unittest.mock import MagicMock, patch
import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ParameterStatus
from slokern.engine.serving.base import ConfigurationError, ServingRequest
from slokern.engine.serving.ollama import (
    OllamaServingAdapter,
    StrictLoopbackRedirectHandler,
    sanitize_secret_message,
)


def test_ollama_default_endpoint_and_model():
    """Verifies default endpoint is http://127.0.0.1:11434 and model is qwen3:4b-instruct-2507-q4_K_M."""
    adapter = OllamaServingAdapter()
    assert adapter.base_url == "http://127.0.0.1:11434"
    assert adapter.model_name == "qwen3:4b-instruct-2507-q4_K_M"
    assert adapter.runtime_name == "ollama"

    fp = adapter.get_environment_fingerprint()
    assert fp["provider"] == "ollama"
    assert fp["endpoint_host"] == "127.0.0.1:11434"
    assert fp["is_simulated"] is False
    assert fp["security_boundary"] == "strict_loopback"


def test_ollama_rejects_non_loopback():
    """Non-loopback host raises ConfigurationError unless allow_remote is declared."""
    with pytest.raises(ConfigurationError) as exc_info:
        OllamaServingAdapter(base_url="http://192.168.1.50:11434")
    assert "not a permitted loopback address" in str(exc_info.value)

    with pytest.raises(ConfigurationError) as exc_info:
        OllamaServingAdapter(base_url="http://api.remote-ollama.internal:11434")
    assert "not a permitted loopback address" in str(exc_info.value)

    # When allow_remote is True, it succeeds
    adapter = OllamaServingAdapter(base_url="http://api.remote-ollama.internal:11434", allow_remote=True)
    assert adapter.base_url == "http://api.remote-ollama.internal:11434"


def test_ollama_rejects_url_credentials():
    """Userinfo in URL credentials raises ConfigurationError."""
    with pytest.raises(ConfigurationError) as exc_info:
        OllamaServingAdapter(base_url="http://admin:password@127.0.0.1:11434")
    assert "URL credentials (userinfo) are prohibited" in str(exc_info.value)


def test_ollama_redirect_prohibited():
    """StrictLoopbackRedirectHandler intercepts and raises ConfigurationError on 3xx redirect."""
    handler = StrictLoopbackRedirectHandler()
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat")
    with pytest.raises(ConfigurationError) as exc_info:
        handler.redirect_request(req, None, 302, "Found", {}, "http://127.0.0.1:8080/evil")
    assert "HTTP redirect (302) prohibited" in str(exc_info.value)

    with pytest.raises(ConfigurationError):
        handler.http_error_301(req, None, 301, "Moved Permanently", {"Location": "http://other"})


def test_ollama_credential_isolation(monkeypatch):
    """Verifies no Authorization header is sent, even if NEBIUS_API_KEY is set in environment."""
    monkeypatch.setenv("NEBIUS_API_KEY", "nebius-super-secret-key-12345")
    adapter = OllamaServingAdapter()
    headers = adapter._build_headers()
    assert "Authorization" not in headers
    assert "Authorization".lower() not in [k.lower() for k in headers.keys()]


def test_ollama_health_check_success():
    """GET /api/tags returning model list with target model returns True."""
    adapter = OllamaServingAdapter(model_name="qwen3:4b-instruct-2507-q4_K_M")
    tags_response = json.dumps({
        "models": [
            {"name": "qwen3:4b-instruct-2507-q4_K_M:latest", "model": "qwen3:4b-instruct-2507-q4_K_M"},
            {"name": "llama3:8b", "model": "llama3:8b"},
        ]
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = tags_response
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        assert adapter.health_check() is True


def test_ollama_health_check_missing_model():
    """GET /api/tags returning models without the target model returns False without silent downloads."""
    adapter = OllamaServingAdapter(model_name="qwen3:4b-instruct-2507-q4_K_M")
    tags_response = json.dumps({
        "models": [
            {"name": "llama3:8b", "model": "llama3:8b"},
            {"name": "mistral:7b", "model": "mistral:7b"},
        ]
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = tags_response
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        assert adapter.health_check() is False


def test_ollama_health_check_connection_error():
    """Daemon down / connection refused returns False."""
    adapter = OllamaServingAdapter()
    with patch.object(adapter._opener, "open", side_effect=urllib.error.URLError("Connection refused")):
        assert adapter.health_check() is False


def test_ollama_client_monotonic_ttft():
    """First content chunk arrival determines TTFT via monotonic clock."""
    adapter = OllamaServingAdapter()
    ndjson_data = [
        json.dumps({"model": "qwen3:4b-instruct-2507-q4_K_M", "message": {"role": "assistant", "content": "Hello"}, "done": False}).encode("utf-8") + b"\n",
        json.dumps({"model": "qwen3:4b-instruct-2507-q4_K_M", "message": {"role": "assistant", "content": " world!"}, "done": False}).encode("utf-8") + b"\n",
        json.dumps({
            "model": "qwen3:4b-instruct-2507-q4_K_M",
            "message": {"role": "assistant", "content": ""},
            "done": True,
            "prompt_eval_duration": 45000000,  # 45 ms in ns
            "eval_duration": 120000000,         # 120 ms in ns
        }).encode("utf-8") + b"\n",
    ]

    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(ndjson_data)
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        chunks = list(adapter.stream_generate(ServingRequest(prompt="Hello", max_tokens=16)))

    assert len(chunks) == 3
    assert chunks[0].token == "Hello"
    assert chunks[0].index == 0
    assert chunks[0].latency_ms >= 0.0
    assert chunks[1].token == " world!"
    assert chunks[1].index == 1
    assert chunks[2].is_last is True


def test_ollama_server_eval_metadata():
    """Nanoseconds in prompt_eval_duration and eval_duration are converted to ms in metadata."""
    adapter = OllamaServingAdapter()
    chat_response = json.dumps({
        "model": "qwen3:4b-instruct-2507-q4_K_M",
        "message": {"role": "assistant", "content": "Deterministic response."},
        "prompt_eval_count": 10,
        "eval_count": 5,
        "prompt_eval_duration": 50000000,   # 50 ms in ns
        "eval_duration": 150000000,          # 150 ms in ns
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = chat_response
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        resp = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=16))

    assert resp.status_code == 200
    assert resp.text == "Deterministic response."
    assert resp.input_tokens == 10
    assert resp.output_tokens == 5
    assert resp.metadata["server_prompt_eval_duration_ms"] == 50.0
    assert resp.metadata["server_eval_duration_ms"] == 150.0
    assert resp.metadata["provider"] == "ollama"


def test_ollama_chunk_gap_observations():
    """Multi-token chunks are recorded as chunk-gap deltas in stream_generate."""
    adapter = OllamaServingAdapter()
    ndjson_data = [
        json.dumps({"message": {"content": "First token"}, "done": False}).encode("utf-8") + b"\n",
        json.dumps({"message": {"content": " second chunk"}, "done": False}).encode("utf-8") + b"\n",
        json.dumps({"message": {"content": ""}, "done": True}).encode("utf-8") + b"\n",
    ]

    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(ndjson_data)
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        chunks = list(adapter.stream_generate(ServingRequest(prompt="Test")))

    for chunk in chunks:
        assert chunk.metadata.get("is_chunk_gap") is True
        assert chunk.metadata.get("provider") == "ollama"


def test_ollama_capability_unsupported_knobs():
    """max_num_batched_tokens and max_num_seqs are marked UNSUPPORTED per BLK-17."""
    adapter = OllamaServingAdapter()
    candidate = CandidateConfig(
        candidate_id="cand-ollama-01",
        model_name="qwen3:4b-instruct-2507-q4_K_M",
        runtime_name="ollama",
        requested_settings={
            "max_num_batched_tokens": 1024,
            "max_num_seqs": 32,
            "temperature": 0.5,
        },
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )

    # In non-strict mode, returns updated config with parameter statuses
    applied = adapter.apply_config(candidate, strict=False)
    assert applied.parameter_status["max_num_batched_tokens"] == ParameterStatus.UNSUPPORTED
    assert applied.parameter_status["max_num_seqs"] == ParameterStatus.UNSUPPORTED
    assert applied.parameter_status["temperature"] == ParameterStatus.APPLIED
    assert applied.effective_settings["temperature"] == 0.5
    assert "max_num_batched_tokens" not in applied.effective_settings

    # In strict mode, raises ConfigurationError
    with pytest.raises(ConfigurationError) as exc_info:
        adapter.apply_config(candidate, strict=True)
    assert "max_num_batched_tokens" in str(exc_info.value)
    assert "unsupported" in str(exc_info.value).lower()


def test_ollama_secret_redaction():
    """Secrets in error messages or URLs are redacted."""
    raw_error = "Failed to connect to endpoint with api_key='sk-test-secret-value-99999' on server"
    sanitized = sanitize_secret_message(raw_error)
    assert "sk-test-secret-value-99999" not in sanitized
    assert "***REDACTED***" in sanitized


def test_ollama_rejects_loopback_domain_bypass():
    """Domains like 127.attacker.com are rejected and cannot bypass loopback check."""
    with pytest.raises(ConfigurationError) as exc_info:
        OllamaServingAdapter(base_url="http://127.attacker.com:11434")
    assert "not a permitted loopback address" in str(exc_info.value)

    with pytest.raises(ConfigurationError) as exc_info2:
        OllamaServingAdapter(base_url="http://127.0.0.1.nip.io:11434")
    assert "not a permitted loopback address" in str(exc_info2.value)


def test_ollama_generate_json_error():
    """Server-reported error in JSON response is captured in ServingResponse.error."""
    adapter = OllamaServingAdapter()
    error_json = json.dumps({"error": "CUDA out of memory: model runner crashed"}).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = error_json
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        resp = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=16))

    assert resp.status_code == 500
    assert resp.error is not None
    assert "CUDA out of memory" in resp.error
    assert resp.error_type == "server_error"
    assert resp.output_tokens == 0


def test_ollama_stream_generate_json_error():
    """Server-reported error in stream chunk is yielded as a terminating error chunk."""
    adapter = OllamaServingAdapter()
    error_chunk = json.dumps({"error": "Model execution timeout"}).encode("utf-8") + b"\n"

    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter([error_chunk])
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        chunks = list(adapter.stream_generate(ServingRequest(prompt="Test prompt", max_tokens=16)))

    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert chunks[0].error is not None
    assert "Model execution timeout" in chunks[0].error
    assert chunks[0].metadata.get("error_type") == "server_error"


def test_ollama_empty_output_zero_tokens():
    """Empty output text produces output_tokens == 0, not 1."""
    adapter = OllamaServingAdapter()
    empty_json = json.dumps({
        "message": {"content": ""},
        "prompt_eval_count": 8,
        "eval_count": 0,
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = empty_json
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        resp = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=16))

    assert resp.output_tokens == 0
    assert resp.input_tokens == 8
    assert resp.text == ""


def test_ollama_stream_generate_premature_termination():
    """Stream terminating without done flag emits a terminating premature close error chunk."""
    adapter = OllamaServingAdapter()
    partial_chunk = json.dumps({"message": {"content": "Hello"}, "done": False}).encode("utf-8") + b"\n"

    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter([partial_chunk])
    mock_resp.__enter__.return_value = mock_resp

    with patch.object(adapter._opener, "open", return_value=mock_resp):
        chunks = list(adapter.stream_generate(ServingRequest(prompt="Test prompt", max_tokens=16)))

    assert len(chunks) == 2
    assert chunks[0].token == "Hello"
    assert chunks[0].is_last is False
    assert chunks[1].is_last is True
    assert chunks[1].error is not None
    assert "interrupted prematurely" in chunks[1].error
