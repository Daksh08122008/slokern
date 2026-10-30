"""
Purpose: Unit tests for NebiusServingAdapter with mocked HTTP responses and secret sanitization.
Owner: Rajdeep (Historical design: Aman)
"""

import io
import json
import urllib.error
from unittest.mock import MagicMock, patch

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ParameterStatus
from slokern.engine.serving.base import ConfigurationError, ServingRequest
from slokern.engine.serving.nebius import (
    NebiusServingAdapter,
    sanitize_secret_message,
)


def test_sanitize_secret_message():
    secret = "neb_sec_abc123456789"
    msg1 = f"Failed to connect using token {secret} to host"
    clean1 = sanitize_secret_message(msg1, secret)
    assert secret not in clean1
    assert "***REDACTED***" in clean1

    msg2 = "Authorization: Bearer my_top_secret_bearer_token_xyz"
    clean2 = sanitize_secret_message(msg2)
    assert "my_top_secret_bearer_token_xyz" not in clean2
    assert "Bearer ***REDACTED***" in clean2

    msg3 = "api_key='sk-test-secret-12345' connection failed"
    clean3 = sanitize_secret_message(msg3)
    assert "sk-test-secret-12345" not in clean3
    assert "***REDACTED***" in clean3


def test_nebius_adapter_initialization_and_fingerprint():
    adapter = NebiusServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-nebius",
        api_key="test-key-12345",
        base_url="https://api.studio.nebius.ai/v1",
    )

    assert adapter.model_name == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert adapter.runtime_name == "vllm-nebius"
    assert adapter.has_api_key is True

    fp = adapter.get_environment_fingerprint()
    assert fp["provider"] == "nebius"
    assert fp["endpoint_host"] == "api.studio.nebius.ai"
    assert fp["has_credentials"] is True
    assert fp["is_simulated"] is False
    # API key must NEVER be in fingerprint
    assert "test-key-12345" not in json.dumps(fp)


def test_nebius_default_base_url_uses_token_factory_endpoint(monkeypatch):
    monkeypatch.delenv("NEBIUS_BASE_URL", raising=False)
    adapter = NebiusServingAdapter(api_key="dummy-test-key")

    assert adapter.base_url == "https://api.tokenfactory.nebius.com/v1"


def test_nebius_adapter_apply_config():
    adapter = NebiusServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-nebius",
    )

    settings = {"max_num_seqs": 64, "temperature": 0.7}
    candidate = CandidateConfig(
        candidate_id="cand-nebius-01",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-nebius",
        requested_settings=settings,
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )

    applied = adapter.apply_config(candidate, strict=True)
    assert applied.effective_settings["max_num_seqs"] == 64
    assert applied.effective_settings["temperature"] == 0.7
    assert applied.parameter_status["max_num_seqs"] == ParameterStatus.APPLIED
    assert applied.parameter_status["temperature"] == ParameterStatus.APPLIED

    # Strict mode rejection on unsupported parameter
    bad_candidate = CandidateConfig(
        candidate_id="cand-bad",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-nebius",
        requested_settings={"completely_unsupported_knob": 999},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )
    with pytest.raises(ConfigurationError) as exc_info:
        adapter.apply_config(bad_candidate, strict=True)
    assert "completely_unsupported_knob" in str(exc_info.value)


@patch("urllib.request.urlopen")
def test_nebius_health_check_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="key-abc")
    assert adapter.health_check() is True


@patch("urllib.request.urlopen")
def test_nebius_health_check_failure(mock_urlopen):
    mock_urlopen.side_effect = urllib.error.URLError("Connection refused")

    adapter = NebiusServingAdapter(api_key="key-abc")
    assert adapter.health_check() is False


@patch("urllib.request.urlopen")
def test_nebius_generate_success(mock_urlopen):
    response_json = json.dumps({
        "id": "chatcmpl-test",
        "choices": [{
            "message": {"content": "Inference optimization is great."}
        }],
        "usage": {
            "prompt_tokens": 8,
            "completion_tokens": 4,
        }
    }).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = response_json
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="key-abc")
    resp = adapter.generate(ServingRequest(prompt="Tell me about inference.", max_tokens=16))

    assert resp.status_code == 200
    assert resp.text == "Inference optimization is great."
    assert resp.input_tokens == 8
    assert resp.output_tokens == 4
    assert resp.error is None


@patch("urllib.request.urlopen")
def test_nebius_stream_generate_success(mock_urlopen):
    sse_data = [
        b'data: {"choices":[{"delta":{"content":"Hello"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"delta":{"content":" world"},"finish_reason":null}]}\n\n',
        b'data: {"choices":[{"delta":{"content":""},"finish_reason":"stop"}]}\n\n',
        b'data: [DONE]\n\n',
    ]

    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(sse_data)
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="key-abc")
    chunks = list(adapter.stream_generate(ServingRequest(prompt="Hello", max_tokens=16)))

    assert len(chunks) == 3
    assert chunks[0].token == "Hello"
    assert chunks[0].index == 0
    assert chunks[0].latency_ms >= 0.0
    assert chunks[1].token == " world"
    assert chunks[1].index == 1
    assert chunks[2].is_last is True
    assert chunks[2].token == ""


@patch("urllib.request.urlopen")
def test_nebius_generate_http_error_redaction(mock_urlopen):
    err = urllib.error.HTTPError(
        url="https://api.studio.nebius.ai/v1/chat/completions",
        code=401,
        msg="Unauthorized",
        hdrs=None,
        fp=io.BytesIO(b'{"error": "Invalid API key provided: secret_abc_12345"}'),
    )
    mock_urlopen.side_effect = err

    adapter = NebiusServingAdapter(api_key="secret_abc_12345")
    resp = adapter.generate(ServingRequest(prompt="Hello"))

    assert resp.status_code == 401
    assert "secret_abc_12345" not in resp.error
    assert "***REDACTED***" in resp.error


def test_nebius_cloud_adapter_alias():
    from slokern.engine.serving.nebius import NebiusCloudAdapter
    assert NebiusCloudAdapter is NebiusServingAdapter
    adapter = NebiusCloudAdapter(api_key="key-test")
    assert isinstance(adapter, NebiusServingAdapter)
    assert adapter.has_api_key is True


@patch("urllib.request.urlopen")
def test_nebius_check_readiness(mock_urlopen):
    # Test readiness success
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "data": [{"id": "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"}]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="test-key-12345")
    res = adapter.check_readiness()
    assert res["ready"] is True
    assert res["model_confirmed"] is True

    # Test readiness without credentials
    unauth_adapter = NebiusServingAdapter(api_key="")
    unauth_adapter._api_key = ""
    res = unauth_adapter.check_readiness()
    assert res["ready"] is False
    assert "Missing credentials" in res["error"]


@patch("urllib.request.urlopen")
def test_nebius_stream_provider_error(mock_urlopen):
    sse_data = [
        b'data: {"error":{"message":"Rate limit exceeded for model","code":429}}\n\n',
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(sse_data)
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="test-key-12345")
    chunks = list(adapter.stream_generate(ServingRequest(prompt="Hello", max_tokens=16)))
    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert "Rate limit exceeded" in chunks[0].error
    assert chunks[0].metadata["error_type"] == "provider_error"


@patch("urllib.request.urlopen")
def test_nebius_stream_empty_completion(mock_urlopen):
    sse_data = [
        b'data: [DONE]\n\n',
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(sse_data)
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="test-key-12345")
    chunks = list(adapter.stream_generate(ServingRequest(prompt="Hello", max_tokens=16)))
    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert chunks[0].token == ""
    assert chunks[0].metadata.get("empty_stream") is True


@patch("urllib.request.urlopen")
def test_nebius_generate_rate_limit_429(mock_urlopen):
    err = urllib.error.HTTPError(
        url="https://api.studio.nebius.ai/v1/chat/completions",
        code=429,
        msg="Too Many Requests",
        hdrs=None,
        fp=io.BytesIO(b'{"error": "Too Many Requests"}'),
    )
    mock_urlopen.side_effect = err

    adapter = NebiusServingAdapter(api_key="test-key-12345")
    resp = adapter.generate(ServingRequest(prompt="Hello"))
    assert resp.status_code == 429
    assert resp.error_type == "rate_limit_exceeded"


@patch("urllib.request.urlopen")
def test_nebius_check_readiness_model_not_confirmed(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.status = 200
    mock_resp.read.return_value = json.dumps({
        "data": [{"id": "meta-llama/Meta-Llama-3-8B-Instruct"}]
    }).encode("utf-8")
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(
        model_name="nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B",
        api_key="test-key-12345",
    )
    res = adapter.check_readiness()
    assert res["ready"] is True
    # Must NOT rubber-stamp confirmation
    assert res["model_confirmed"] is False
    assert "not confirmed in catalog" in res["message"]


@patch("urllib.request.urlopen")
def test_nebius_stream_event_error_header(mock_urlopen):
    sse_data = [
        b"event: error\n",
        b'data: {"message": "Model is overloaded, try again later", "code": 503}\n\n',
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(sse_data)
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="test-key-12345")
    chunks = list(adapter.stream_generate(ServingRequest(prompt="Hello", max_tokens=16)))
    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert "Model is overloaded" in chunks[0].error
    assert chunks[0].metadata["error_type"] == "provider_error"


@patch("urllib.request.urlopen")
def test_nebius_stream_data_without_space(mock_urlopen):
    sse_data = [
        b'data:{"choices":[{"delta":{"content":"Hi"}}]}\n\n',
        b"data:[DONE]\n\n",
    ]
    mock_resp = MagicMock()
    mock_resp.__iter__.return_value = iter(sse_data)
    mock_resp.__enter__.return_value = mock_resp
    mock_urlopen.return_value = mock_resp

    adapter = NebiusServingAdapter(api_key="test-key-12345")
    chunks = list(adapter.stream_generate(ServingRequest(prompt="Hello", max_tokens=16)))
    assert len(chunks) >= 1
    assert chunks[0].token == "Hi"
