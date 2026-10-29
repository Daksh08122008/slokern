"""
Purpose: Comprehensive unit tests for FakeServingAdapter.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, Section 8, and ROADMAP.md TASK-05
"""

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ParameterStatus
from slokern.engine.serving.base import ServingRequest
from slokern.engine.serving.fake import FailureInjectionConfig, FakeServingAdapter


def test_fake_adapter_initialization_and_fingerprint():
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        seed=123
    )

    assert adapter.model_name == "meta-llama/Meta-Llama-3-8B-Instruct"
    assert adapter.runtime_name == "vllm-fake"
    assert adapter.current_config is None
    assert adapter.health_check() is True

    # Environment fingerprint must explicitly carry DEMO DATA per AGENTS.md Section 1 and Section 8
    fp = adapter.get_environment_fingerprint()
    assert fp["mode"] == "DEMO DATA"
    assert fp["is_simulated"] is True
    assert fp["simulated"] is True
    assert "DEMO DATA" in fp["device"]
    assert "DEMO DATA" in fp["hardware_model"]
    assert "DEMO DATA" in fp["cuda_version"]
    assert "DEMO DATA" in fp["driver_version"]
    assert "DEMO DATA" in fp["disclaimer"]


def test_fake_adapter_capabilities():
    adapter = FakeServingAdapter()
    caps = adapter.get_capabilities()

    assert caps.runtime_name == "vllm-fake"
    assert caps.supports_streaming is True
    assert "max_num_seqs" in caps.parameters
    assert "gpu_memory_utilization" in caps.parameters
    assert "max_model_len" in caps.parameters
    assert "kv_cache_dtype" in caps.parameters
    assert "tensor_parallel_size" in caps.parameters


def test_fake_adapter_apply_config_read_back():
    adapter = FakeServingAdapter()

    candidate = CandidateConfig(
        candidate_id="cand-001",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={
            "max_num_seqs": 64,
            "gpu_memory_utilization": 0.85,
            "kv_cache_dtype": "fp8",
            "invalid_knob": "bad_value",
            "max_model_len": 999999  # Exceeds max_value 32768
        },
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )

    verified = adapter.apply_config(candidate)

    # Check candidate identity and current_config synchronization
    assert verified.candidate_id == "cand-001"
    assert adapter.current_config == verified

    # Check parameter classification
    status = verified.parameter_status
    assert status["max_num_seqs"] == ParameterStatus.APPLIED
    assert status["gpu_memory_utilization"] == ParameterStatus.APPLIED
    assert status["kv_cache_dtype"] == ParameterStatus.APPLIED
    assert status["invalid_knob"] == ParameterStatus.UNSUPPORTED
    assert status["max_model_len"] == ParameterStatus.REJECTED

    # Omitted supported parameters fall back to default
    assert status["tensor_parallel_size"] == ParameterStatus.DEFAULT_FALLBACK

    # Effective settings contains only successfully applied & default settings
    eff = verified.effective_settings
    assert eff["max_num_seqs"] == 64
    assert eff["gpu_memory_utilization"] == 0.85
    assert eff["kv_cache_dtype"] == "fp8"
    assert eff["tensor_parallel_size"] == 1
    assert "invalid_knob" not in eff
    assert "max_model_len" not in eff

    # Environment fingerprint attached
    assert verified.environment_fingerprint["mode"] == "DEMO DATA"


def test_fake_adapter_apply_config_generates_id_if_empty():
    adapter = FakeServingAdapter()
    candidate = CandidateConfig(
        candidate_id="",  # Empty ID should be populated deterministically
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 32},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )

    verified = adapter.apply_config(candidate)
    assert verified.candidate_id != ""
    assert len(verified.candidate_id) == 12


def test_fake_adapter_health_check_toggle():
    adapter = FakeServingAdapter()
    assert adapter.health_check() is True

    adapter.set_health(False)
    assert adapter.health_check() is False

    adapter.set_health(True)
    assert adapter.health_check() is True


def test_fake_adapter_deterministic_generate():
    adapter = FakeServingAdapter(seed=42)

    req = ServingRequest(
        prompt="Explain latency vs throughput in inference systems.",
        max_tokens=10,
        request_id="req-101",
        run_id="run-202"
    )

    resp1 = adapter.generate(req)
    assert resp1.status_code == 200
    assert resp1.error is None
    assert resp1.request_id == "req-101"
    assert resp1.run_id == "run-202"
    assert resp1.input_tokens > 0
    assert resp1.output_tokens == 10
    assert resp1.text.startswith("[DEMO DATA]")
    assert resp1.metadata["label"] == "DEMO DATA"
    assert resp1.metadata["simulated"] is True

    # Reproducibility check: identical seed and prompt produce exact same latencies
    resp2 = adapter.generate(req)
    assert resp1.first_token_latency_ms == resp2.first_token_latency_ms
    assert resp1.itl_observations_ms == resp2.itl_observations_ms
    assert resp1.total_latency_ms == resp2.total_latency_ms
    assert resp1.text == resp2.text


def test_fake_adapter_prompt_as_string():
    adapter = FakeServingAdapter()
    resp = adapter.generate("Hello world string prompt")
    assert resp.status_code == 200
    assert resp.output_tokens > 0
    assert resp.text.startswith("[DEMO DATA]")


def test_fake_adapter_latency_scaling_with_prompt_length():
    adapter = FakeServingAdapter(seed=99)

    short_req = ServingRequest(prompt="Short prompt", max_tokens=10)
    long_req = ServingRequest(
        prompt="This is a much longer prompt designed to demonstrate that the synthetic "
               "serving adapter scales Time to First Token (TTFT) as input prompt tokens increase.",
        max_tokens=10
    )

    short_resp = adapter.generate(short_req)
    long_resp = adapter.generate(long_req)

    assert long_resp.input_tokens > short_resp.input_tokens
    assert long_resp.first_token_latency_ms > short_resp.first_token_latency_ms


def test_fake_adapter_latency_scaling_with_candidate_config():
    adapter = FakeServingAdapter(seed=77)

    # Candidate 1: low concurrency batch limit
    c1 = CandidateConfig(
        candidate_id="c1",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 16, "kv_cache_dtype": "auto", "tensor_parallel_size": 1},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c1)
    resp_c1 = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=12))

    # Candidate 2: high concurrency batch limit
    c2 = CandidateConfig(
        candidate_id="c2",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 128, "kv_cache_dtype": "auto", "tensor_parallel_size": 1},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c2)
    resp_c2 = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=12))

    # Higher batch concurrency slightly increases TTFT and ITL
    assert resp_c2.first_token_latency_ms > resp_c1.first_token_latency_ms
    assert sum(resp_c2.itl_observations_ms) > sum(resp_c1.itl_observations_ms)

    # Candidate 3: Tensor Parallelism 2 reduces latency
    c3 = CandidateConfig(
        candidate_id="c3",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 16, "kv_cache_dtype": "auto", "tensor_parallel_size": 2},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c3)
    resp_c3 = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=12))
    assert resp_c3.first_token_latency_ms < resp_c1.first_token_latency_ms

    # Candidate 4: FP8 KV-cache provides speedup
    c4 = CandidateConfig(
        candidate_id="c4",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 16, "kv_cache_dtype": "fp8", "tensor_parallel_size": 1},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c4)
    resp_c4 = adapter.generate(ServingRequest(prompt="Test prompt", max_tokens=12))
    assert resp_c4.first_token_latency_ms < resp_c1.first_token_latency_ms


def test_fake_adapter_stream_generate():
    adapter = FakeServingAdapter(seed=42)
    req = ServingRequest(prompt="Stream test", max_tokens=8)

    chunks = list(adapter.stream_generate(req))
    assert len(chunks) == 8

    # Chunk 0: TTFT
    assert chunks[0].index == 0
    assert chunks[0].token.startswith("[DEMO DATA]")
    assert chunks[0].is_last is False
    assert chunks[0].metadata["label"] == "DEMO DATA"
    assert chunks[0].metadata["simulated"] is True

    # Intermediate chunks
    for i in range(1, 7):
        assert chunks[i].index == i
        assert chunks[i].is_last is False
        assert chunks[i].timestamp_ms > chunks[i - 1].timestamp_ms

    # Final chunk
    assert chunks[7].index == 7
    assert chunks[7].is_last is True

    # String prompt streaming
    string_chunks = list(adapter.stream_generate("Simple string prompt"))
    assert len(string_chunks) > 0


def _run_coroutine(coro):
    """Executes a coroutine to completion without requiring an OS-level event loop."""
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value
    raise RuntimeError("Coroutine did not complete immediately")


def _collect_async_gen(agen):
    """Collects all items from an async generator without requiring an OS-level event loop."""
    items = []
    while True:
        try:
            coro = agen.__anext__()
            try:
                coro.send(None)
            except StopIteration as e:
                items.append(e.value)
        except StopAsyncIteration:
            break
    return items


def test_fake_adapter_async_generate():
    adapter = FakeServingAdapter(seed=42, simulate_delay=False)
    req = ServingRequest(prompt="Async test", max_tokens=5)
    resp = _run_coroutine(adapter.agenerate(req))
    assert resp.status_code == 200
    assert resp.output_tokens == 5
    assert resp.text.startswith("[DEMO DATA]")


def test_fake_adapter_async_stream_generate():
    adapter = FakeServingAdapter(seed=42, simulate_delay=False)
    req = ServingRequest(prompt="Async stream test", max_tokens=5)

    chunks = _collect_async_gen(adapter.astream_generate(req))
    assert len(chunks) == 5
    assert chunks[0].index == 0
    assert chunks[0].token.startswith("[DEMO DATA]")
    assert chunks[-1].is_last is True
    assert "".join(c.token for c in chunks).startswith("[DEMO DATA]")

    # Async streaming with failure injection
    adapter.inject_oom(True)
    err_chunks = _collect_async_gen(adapter.astream_generate(req))
    assert len(err_chunks) == 1
    assert err_chunks[0].is_last is True
    assert "CUDA out of memory" in err_chunks[0].error


def test_fake_adapter_failure_injection_forced_oom():
    adapter = FakeServingAdapter()
    adapter.inject_oom(True)

    # Non-streaming OOM
    resp = adapter.generate(ServingRequest(prompt="Crash me"))
    assert resp.status_code == 500
    assert resp.error_type == "cuda_out_of_memory"
    assert "CUDA out of memory" in resp.error
    assert "[DEMO DATA]" in resp.error
    assert resp.output_tokens == 0
    assert resp.first_token_latency_ms is None
    assert resp.itl_observations_ms == []
    assert resp.metadata["failure_injected"] == "cuda_out_of_memory"

    # Streaming OOM
    chunks = list(adapter.stream_generate(ServingRequest(prompt="Crash me stream")))
    assert len(chunks) == 1
    assert chunks[0].is_last is True
    assert "CUDA out of memory" in chunks[0].error
    assert chunks[0].metadata["status_code"] == 500

    # Reset failure restores healthy generation
    adapter.reset_failures()
    assert adapter.generate(ServingRequest(prompt="Recovered")).status_code == 200


def test_fake_adapter_failure_injection_forced_timeout():
    adapter = FakeServingAdapter()
    adapter.inject_timeout(True)

    resp = adapter.generate(ServingRequest(prompt="Timeout me"))
    assert resp.status_code == 504
    assert resp.error_type == "timeout"
    assert "Gateway Timeout" in resp.error
    assert resp.output_tokens == 0
    assert resp.total_latency_ms == 30000.0


def test_fake_adapter_failure_injection_forced_server_error():
    adapter = FakeServingAdapter()
    adapter.inject_server_error(True)

    resp = adapter.generate(ServingRequest(prompt="Server error"))
    assert resp.status_code == 500
    assert resp.error_type == "server_error"
    assert "Internal Server Error" in resp.error
    assert resp.output_tokens == 0


def test_fake_adapter_threshold_oom_on_batch_concurrency():
    adapter = FakeServingAdapter(
        failure_config=FailureInjectionConfig(oom_max_num_seqs_threshold=64)
    )

    # Within threshold: max_num_seqs = 32
    c_ok = CandidateConfig(
        candidate_id="c_ok",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 32},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c_ok)
    assert adapter.generate(ServingRequest(prompt="Normal")).status_code == 200

    # Exceeding threshold: max_num_seqs = 128
    c_oom = CandidateConfig(
        candidate_id="c_oom",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"max_num_seqs": 128},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c_oom)
    resp_oom = adapter.generate(ServingRequest(prompt="Exceeds memory limit"))
    assert resp_oom.status_code == 500
    assert resp_oom.error_type == "cuda_out_of_memory"
    assert "exceeds memory threshold" in resp_oom.error


def test_fake_adapter_memory_pressure_oom():
    adapter = FakeServingAdapter(
        failure_config=FailureInjectionConfig(oom_on_high_memory_pressure=True)
    )

    # High GPU memory utilization + high batch sequences -> triggers memory pressure OOM
    c_pressure = CandidateConfig(
        candidate_id="c_press",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"gpu_memory_utilization": 0.98, "max_num_seqs": 64},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c_pressure)
    resp = adapter.generate(ServingRequest(prompt="Memory pressure test"))
    assert resp.status_code == 500
    assert resp.error_type == "cuda_out_of_memory"
    assert "High memory pressure" in resp.error

    # Safe memory utilization -> succeeds
    c_safe = CandidateConfig(
        candidate_id="c_safe",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={"gpu_memory_utilization": 0.80, "max_num_seqs": 64},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter.apply_config(c_safe)
    assert adapter.generate(ServingRequest(prompt="Safe test")).status_code == 200


def test_fake_adapter_targeted_request_id_failure():
    adapter = FakeServingAdapter(
        failure_config=FailureInjectionConfig(target_error_request_ids=["req-bad-99"])
    )

    # Normal request succeeds
    resp_ok = adapter.generate(ServingRequest(prompt="Good request", request_id="req-good-01"))
    assert resp_ok.status_code == 200

    # Targeted request fails with OOM
    resp_bad = adapter.generate(ServingRequest(prompt="Targeted failure", request_id="req-bad-99"))
    assert resp_bad.status_code == 500
    assert resp_bad.error_type == "cuda_out_of_memory"
    assert "req-bad-99" in resp_bad.error


def test_fake_adapter_probabilistic_error():
    # 100% error rate
    adapter = FakeServingAdapter(
        failure_config=FailureInjectionConfig(error_rate_prob=1.0)
    )
    resp = adapter.generate(ServingRequest(prompt="Always fail"))
    assert resp.status_code == 500
    assert resp.error_type == "server_error"


def test_fake_adapter_to_raw_measurement_pipeline():
    adapter = FakeServingAdapter(seed=42)
    req = ServingRequest(prompt="Pipeline test", max_tokens=10, request_id="req-pipe-1", run_id="run-pipe-1")

    resp = adapter.generate(req)
    raw = resp.to_raw_measurement(scheduled_at=1700000000.0, sent_at=1700000000.005, is_warmup=False)

    assert raw.request_id == "req-pipe-1"
    assert raw.run_id == "run-pipe-1"
    assert raw.http_status == 200
    assert raw.is_valid is True
    assert raw.is_warmup is False
    assert raw.first_token_at is not None
    assert raw.first_token_at > raw.sent_at
    assert raw.completed_at > raw.first_token_at
    assert raw.output_tokens == 10
    assert len(raw.itl_observations_ms) == 9


def test_fake_adapter_empty_prompt_zero_tokens():
    adapter = FakeServingAdapter(seed=42)
    resp = adapter.generate(ServingRequest(prompt=""))
    assert resp.status_code == 200
    assert resp.input_tokens == 0
    assert resp.output_tokens > 0

    # Also test whitespace-only prompt
    resp_ws = adapter.generate(ServingRequest(prompt="    \t\n  "))
    assert resp_ws.input_tokens == 0


def test_fake_adapter_unsupported_model_raises_configuration_error():
    from slokern.engine.serving.base import ConfigurationError
    from slokern.engine.serving.capabilities import RuntimeCapabilities

    # Adapter with strict supported models (no wildcard)
    restricted_caps = RuntimeCapabilities(
        runtime_name="vllm-restricted",
        supported_models=["meta-llama/Meta-Llama-3-8B-Instruct"]
    )
    adapter = FakeServingAdapter(
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-restricted",
        capabilities=restricted_caps
    )

    bad_candidate = CandidateConfig(
        candidate_id="bad-model-cand",
        model_name="unsupported/some-foreign-model",
        runtime_name="vllm-restricted",
        requested_settings={},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )

    with pytest.raises(ConfigurationError) as exc_info:
        adapter.apply_config(bad_candidate)
    assert "not supported by runtime" in str(exc_info.value)


def test_fake_adapter_strict_mode_rejects_invalid_params():
    from slokern.engine.serving.base import ConfigurationError

    adapter = FakeServingAdapter()
    invalid_candidate = CandidateConfig(
        candidate_id="invalid-settings-cand",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={
            "max_num_seqs": -10,  # Invalid below min_value 1
            "unknown_knob": 123   # Unsupported parameter
        },
        effective_settings={},
        parameter_status={},
        environment_fingerprint={}
    )

    # In default non-strict mode, returns read-back recording REJECTED and UNSUPPORTED
    readback = adapter.apply_config(invalid_candidate, strict=False)
    assert readback.parameter_status["max_num_seqs"] == ParameterStatus.REJECTED
    assert readback.parameter_status["unknown_knob"] == ParameterStatus.UNSUPPORTED

    # In strict mode, raises ConfigurationError immediately
    with pytest.raises(ConfigurationError) as exc_info:
        adapter.apply_config(invalid_candidate, strict=True)
    assert "Configuration rejected by runtime" in str(exc_info.value)


def test_fake_adapter_failure_injection_raise_on_failure_exceptions():
    from slokern.engine.serving.base import ServingOOMError, ServingServerError, ServingTimeoutError

    # Forced OOM with raise_on_failure=True
    adapter_oom = FakeServingAdapter(
        failure_config=FailureInjectionConfig(force_oom=True, raise_on_failure=True)
    )
    with pytest.raises(ServingOOMError) as exc_oom:
        adapter_oom.generate(ServingRequest(prompt="Crash me"))
    assert "CUDA out of memory" in str(exc_oom.value)

    # Forced Timeout with raise_on_failure=True
    adapter_to = FakeServingAdapter(
        failure_config=FailureInjectionConfig(force_timeout=True, raise_on_failure=True)
    )
    with pytest.raises(ServingTimeoutError) as exc_to:
        adapter_to.generate(ServingRequest(prompt="Timeout me"))
    assert "Gateway Timeout" in str(exc_to.value)

    # Forced Server Error with raise_on_failure=True
    adapter_se = FakeServingAdapter(
        failure_config=FailureInjectionConfig(force_server_error=True, raise_on_failure=True)
    )
    with pytest.raises(ServingServerError) as exc_se:
        adapter_se.generate(ServingRequest(prompt="Server error"))
    assert "Internal Server Error" in str(exc_se.value)


def test_fake_adapter_tensor_parallel_size_zero_safety():
    # If effective settings has tensor_parallel_size = 0, must not raise ZeroDivisionError
    adapter = FakeServingAdapter()
    c = CandidateConfig(
        candidate_id="tp-zero",
        model_name="meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name="vllm-fake",
        requested_settings={},
        effective_settings={"tensor_parallel_size": 0},
        parameter_status={},
        environment_fingerprint={}
    )
    adapter._current_config = c
    resp = adapter.generate(ServingRequest(prompt="Safety test"))
    assert resp.status_code == 200
    assert resp.first_token_latency_ms is not None
