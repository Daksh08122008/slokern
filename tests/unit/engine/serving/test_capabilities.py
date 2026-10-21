"""
Purpose: Unit tests for engine/serving/capabilities.
Owner: Rajdeep (Historical design: Aman)
"""

import pytest
from slokern.contracts.enums import ParameterStatus
from slokern.engine.serving.capabilities import ParameterSpec, RuntimeCapabilities


def test_parameter_spec_int_validation():
    spec = ParameterSpec(
        name="max_num_seqs",
        param_type="int",
        default=32,
        min_value=1,
        max_value=128
    )

    # Valid integer
    valid, status, reason = spec.validate_value(64)
    assert valid is True
    assert status == ParameterStatus.APPLIED
    assert reason == ""

    # Integer-valued float
    valid, status, reason = spec.validate_value(64.0)
    assert valid is True
    assert status == ParameterStatus.APPLIED

    # Fractional float must be rejected
    valid, status, reason = spec.validate_value(64.5)
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "Expected integer float" in reason

    # Boolean must be rejected (Python bool is subclass of int)
    valid, status, reason = spec.validate_value(True)
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "Expected int" in reason

    # Out of bounds below min_value
    valid, status, reason = spec.validate_value(0)
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "< min_value" in reason

    # Out of bounds above max_value
    valid, status, reason = spec.validate_value(256)
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "> max_value" in reason

    # Boundary values exact match
    valid_min, status_min, _ = spec.validate_value(1)
    assert valid_min is True
    assert status_min == ParameterStatus.APPLIED

    valid_max, status_max, _ = spec.validate_value(128)
    assert valid_max is True
    assert status_max == ParameterStatus.APPLIED


def test_parameter_spec_float_validation():
    spec = ParameterSpec(
        name="gpu_memory_utilization",
        param_type="float",
        default=0.90,
        min_value=0.1,
        max_value=1.0
    )

    # Valid float
    valid, status, _ = spec.validate_value(0.85)
    assert valid is True
    assert status == ParameterStatus.APPLIED

    # Integer converted to float
    valid, status, _ = spec.validate_value(1)
    assert valid is True
    assert status == ParameterStatus.APPLIED

    # Boolean rejected
    valid, status, _ = spec.validate_value(False)
    assert valid is False
    assert status == ParameterStatus.REJECTED

    # Out of bounds
    valid, status, _ = spec.validate_value(1.05)
    assert valid is False
    assert status == ParameterStatus.REJECTED

    valid, status, _ = spec.validate_value(0.05)
    assert valid is False
    assert status == ParameterStatus.REJECTED


def test_parameter_spec_str_and_allowed_values():
    spec = ParameterSpec(
        name="kv_cache_dtype",
        param_type="str",
        default="auto",
        allowed_values=["auto", "fp16", "fp8"]
    )

    # Allowed value
    valid, status, _ = spec.validate_value("fp8")
    assert valid is True
    assert status == ParameterStatus.APPLIED

    # Disallowed string
    valid, status, reason = spec.validate_value("int4")
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "not in allowed_values" in reason

    # Non-string
    valid, status, _ = spec.validate_value(123)
    assert valid is False
    assert status == ParameterStatus.REJECTED


def test_parameter_spec_bool():
    spec = ParameterSpec(
        name="enable_prefix_caching",
        param_type="bool",
        default=False
    )

    valid, status, _ = spec.validate_value(True)
    assert valid is True
    assert status == ParameterStatus.APPLIED

    valid, status, _ = spec.validate_value("true")
    assert valid is False
    assert status == ParameterStatus.REJECTED


def test_runtime_capabilities_model_support():
    caps_wildcard = RuntimeCapabilities(
        runtime_name="vllm",
        supported_models=["*"]
    )
    assert caps_wildcard.is_model_supported("meta-llama/Meta-Llama-3-8B-Instruct")
    assert caps_wildcard.is_model_supported("custom-random-model")

    caps_specific = RuntimeCapabilities(
        runtime_name="vllm",
        supported_models=["Nemotron-3-Nano-30B-A3B", "meta-llama/Meta-Llama-3-8B-Instruct"]
    )
    assert caps_specific.is_model_supported("Nemotron-3-Nano-30B-A3B")
    assert caps_specific.is_model_supported("meta-llama/Meta-Llama-3-8B-Instruct")
    assert not caps_specific.is_model_supported("unsupported-model")


def test_runtime_capabilities_evaluate_settings():
    caps = RuntimeCapabilities(
        runtime_name="vllm-fake",
        supported_models=["*"],
        parameters={
            "max_num_seqs": ParameterSpec(
                name="max_num_seqs",
                param_type="int",
                default=32,
                min_value=1,
                max_value=256
            ),
            "gpu_memory_utilization": ParameterSpec(
                name="gpu_memory_utilization",
                param_type="float",
                default=0.90,
                min_value=0.1,
                max_value=1.0
            ),
            "kv_cache_dtype": ParameterSpec(
                name="kv_cache_dtype",
                param_type="str",
                default="auto",
                allowed_values=["auto", "fp16", "fp8"]
            ),
        }
    )

    requested = {
        "max_num_seqs": 64.0,              # valid, coerced to int 64
        "gpu_memory_utilization": 1.5,     # invalid: > max_value 1.0 (REJECTED)
        "unsupported_knob": "foo"          # unknown parameter (UNSUPPORTED)
    }

    effective, status, notes = caps.evaluate_settings(requested)

    # max_num_seqs applied and coerced to integer
    assert status["max_num_seqs"] == ParameterStatus.APPLIED
    assert effective["max_num_seqs"] == 64
    assert isinstance(effective["max_num_seqs"], int)

    # gpu_memory_utilization rejected and not in effective
    assert status["gpu_memory_utilization"] == ParameterStatus.REJECTED
    assert "gpu_memory_utilization" not in effective

    # unsupported_knob classified as unsupported
    assert status["unsupported_knob"] == ParameterStatus.UNSUPPORTED
    assert "unsupported_knob" not in effective

    # kv_cache_dtype not in requested, fell back to default
    assert status["kv_cache_dtype"] == ParameterStatus.DEFAULT_FALLBACK
    assert effective["kv_cache_dtype"] == "auto"

    # Notes explain both rejected and unsupported parameters
    assert any("unsupported" in n.lower() for n in notes)
    assert any("rejected" in n.lower() for n in notes)


def test_parameter_spec_nan_inf_rejected():
    spec_float = ParameterSpec(
        name="gpu_memory_utilization",
        param_type="float",
        default=0.90,
        min_value=0.1,
        max_value=1.0
    )
    # NaN must be strictly rejected
    valid, status, reason = spec_float.validate_value(float("nan"))
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "NaN or Inf" in reason

    # Positive and negative infinity must be rejected
    valid, status, reason = spec_float.validate_value(float("inf"))
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "NaN or Inf" in reason

    valid, status, reason = spec_float.validate_value(float("-inf"))
    assert valid is False
    assert status == ParameterStatus.REJECTED
    assert "NaN or Inf" in reason

    # NaN on int spec must also be rejected
    spec_int = ParameterSpec(
        name="max_num_seqs",
        param_type="int",
        default=32,
        min_value=1,
        max_value=128
    )
    valid, status, reason = spec_int.validate_value(float("nan"))
    assert valid is False
    assert status == ParameterStatus.REJECTED


def test_parameter_spec_invalid_param_type():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        ParameterSpec(
            name="bad_param",
            param_type="unsupported_type",
            default=42
        )


def test_runtime_capabilities_mapping_interface():
    caps = RuntimeCapabilities(
        runtime_name="vllm-fake",
        supported_models=["*"],
        parameters={
            "max_num_seqs": ParameterSpec(
                name="max_num_seqs",
                param_type="int",
                default=32
            )
        }
    )

    # Subscript indexing support
    assert caps["runtime_name"] == "vllm-fake"
    assert "max_num_seqs" in caps["parameters"]
    assert "runtime_name" in caps
    assert "parameters" in caps

    with pytest.raises(KeyError):
        _ = caps["non_existent_key"]

    # Export to dictionary
    d = caps.to_dict()
    assert isinstance(d, dict)
    assert d["runtime_name"] == "vllm-fake"
    assert d["supports_streaming"] is True
