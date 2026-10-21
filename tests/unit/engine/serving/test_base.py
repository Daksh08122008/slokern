"""
Purpose: Unit tests for engine/serving/base.
Owner: Rajdeep (Historical design: Aman)
"""

import pytest
from pydantic import ValidationError

from slokern.engine.serving.base import (
    BaseServingAdapter,
    ServingRequest,
    TokenChunk,
    ServingResponse,
    ServingAdapterError,
    ConfigurationError,
    ServingOOMError,
    ServingTimeoutError,
    ServingServerError,
)


def test_serving_request_validation():
    req = ServingRequest(
        prompt="Tell me about SLOs",
        max_tokens=64,
        temperature=0.7,
        request_id="req-123",
        run_id="run-456"
    )
    assert req.prompt == "Tell me about SLOs"
    assert req.max_tokens == 64
    assert req.temperature == 0.7
    assert req.request_id == "req-123"

    # extra='forbid'
    with pytest.raises(ValidationError):
        ServingRequest(prompt="hello", extra_field_illegal="bad")

    # ge=1 for max_tokens
    with pytest.raises(ValidationError):
        ServingRequest(prompt="hello", max_tokens=0)


def test_token_chunk_validation():
    chunk = TokenChunk(
        token="hello",
        token_id=1,
        index=0,
        timestamp_ms=15.2,
        latency_ms=15.2,
        is_last=False
    )
    assert chunk.token == "hello"
    assert chunk.index == 0
    assert chunk.timestamp_ms == 15.2

    with pytest.raises(ValidationError):
        TokenChunk(token="x", token_id=1, index=0, timestamp_ms=1.0, bad_field="err")


def test_serving_response_to_raw_measurement_success():
    resp = ServingResponse(
        request_id="req-001",
        run_id="run-001",
        text="[DEMO DATA] Output text",
        input_tokens=10,
        output_tokens=5,
        first_token_latency_ms=15.0,
        itl_observations_ms=[8.0, 8.2, 7.9, 8.1],
        total_latency_ms=47.2,
        status_code=200
    )

    scheduled_at = 1000.0
    sent_at = 1000.005

    raw = resp.to_raw_measurement(scheduled_at=scheduled_at, sent_at=sent_at, is_warmup=False)

    assert raw.request_id == "req-001"
    assert raw.run_id == "run-001"
    assert raw.scheduled_at == 1000.0
    assert raw.sent_at == 1000.005
    assert raw.first_token_at == pytest.approx(1000.005 + 0.015, rel=1e-5)
    assert raw.completed_at == pytest.approx(1000.005 + 0.0472, rel=1e-5)
    assert raw.http_status == 200
    assert raw.input_tokens == 10
    assert raw.output_tokens == 5
    assert raw.itl_observations_ms == [8.0, 8.2, 7.9, 8.1]
    assert raw.error_type is None
    assert raw.is_warmup is False
    assert raw.is_valid is True


def test_serving_response_to_raw_measurement_failure():
    resp = ServingResponse(
        request_id="req-002",
        run_id="run-001",
        text="",
        input_tokens=12,
        output_tokens=0,
        first_token_latency_ms=None,
        itl_observations_ms=[],
        total_latency_ms=5.0,
        status_code=500,
        error="CUDA out of memory [DEMO DATA]",
        error_type="cuda_out_of_memory"
    )

    scheduled_at = 1000.0
    sent_at = 1000.002

    raw = resp.to_raw_measurement(scheduled_at=scheduled_at, sent_at=sent_at, is_warmup=True)

    assert raw.request_id == "req-002"
    assert raw.first_token_at is None
    assert raw.completed_at == pytest.approx(1000.002 + 0.005, rel=1e-5)
    assert raw.http_status == 500
    assert raw.output_tokens == 0
    assert raw.itl_observations_ms is None
    assert raw.error_type == "cuda_out_of_memory"
    assert raw.is_warmup is True
    assert raw.is_valid is False


def test_serving_response_to_raw_measurement_http_error_fallback():
    # Response with 500 but error_type left as None -> inferred as http_error
    resp = ServingResponse(
        request_id="req-003",
        run_id="run-001",
        text="",
        input_tokens=5,
        output_tokens=0,
        first_token_latency_ms=None,
        itl_observations_ms=[],
        total_latency_ms=10.0,
        status_code=502,
        error="Bad Gateway"
    )
    raw = resp.to_raw_measurement(scheduled_at=100.0, sent_at=100.01)
    assert raw.error_type == "http_error"
    assert raw.is_valid is False


def test_serving_exceptions_hierarchy():
    assert issubclass(ConfigurationError, ServingAdapterError)
    assert issubclass(ServingOOMError, ServingAdapterError)
    assert issubclass(ServingTimeoutError, ServingAdapterError)
    assert issubclass(ServingServerError, ServingAdapterError)


def test_base_serving_adapter_abc():
    # Cannot instantiate BaseServingAdapter without concrete implementations
    with pytest.raises(TypeError):
        BaseServingAdapter(model_name="test", runtime_name="test")


def test_token_chunk_and_response_negative_latency_rejected():
    with pytest.raises(ValidationError):
        TokenChunk(token="t", token_id=1, index=0, timestamp_ms=-1.0)

    with pytest.raises(ValidationError):
        TokenChunk(token="t", token_id=1, index=0, timestamp_ms=1.0, latency_ms=-5.0)

    with pytest.raises(ValidationError):
        ServingResponse(
            request_id="r1",
            run_id="run1",
            text="text",
            input_tokens=1,
            output_tokens=1,
            first_token_latency_ms=-2.0
        )


def test_serving_response_to_raw_measurement_custom_is_valid_and_monotonicity():
    # Caller explicitly marks sample as invalid (e.g. client saturation)
    resp = ServingResponse(
        request_id="req-custom",
        run_id="run-1",
        text="[DEMO DATA] output",
        input_tokens=5,
        output_tokens=2,
        first_token_latency_ms=10.0,
        total_latency_ms=25.0,
        status_code=200
    )
    raw_invalid = resp.to_raw_measurement(
        scheduled_at=100.0,
        sent_at=100.01,
        is_valid=False
    )
    assert raw_invalid.is_valid is False

    # Monotonicity protection if total_latency_ms is shorter than first_token_latency_ms
    resp_anomaly = ServingResponse(
        request_id="req-anomaly",
        run_id="run-1",
        text="[DEMO DATA]",
        input_tokens=5,
        output_tokens=2,
        first_token_latency_ms=50.0,
        total_latency_ms=10.0,
        status_code=200
    )
    raw_anomaly = resp_anomaly.to_raw_measurement(
        scheduled_at=100.0,
        sent_at=100.01
    )
    assert raw_anomaly.completed_at >= raw_anomaly.first_token_at
    assert raw_anomaly.is_valid is False

    # Dispatch lag where sent_at is before scheduled_at (clock skew/anomaly)
    raw_skew = resp.to_raw_measurement(
        scheduled_at=100.05,
        sent_at=100.01
    )
    assert raw_skew.is_valid is False
