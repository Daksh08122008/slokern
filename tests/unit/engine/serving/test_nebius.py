"""Fail-closed tests for the unverified Nebius adapter scaffold."""

import pytest

from slokern.contracts.config import CandidateConfig
from slokern.engine.serving.base import ConfigurationError, ServingAdapterError
from slokern.engine.serving.nebius import NebiusCloudAdapter


def make_config(settings=None):
    return CandidateConfig(
        candidate_id="candidate-test",
        model_name="nvidia/Nemotron-3-Nano-30B-A3B",
        runtime_name="nebius",
        requested_settings=settings or {},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )


def test_nebius_adapter_never_claims_unverified_readiness():
    adapter = NebiusCloudAdapter("nvidia/Nemotron-3-Nano-30B-A3B", "nebius")

    assert adapter.health_check() is False
    capabilities = adapter.get_capabilities()
    assert capabilities.supported_models == []
    assert capabilities.parameters == {}
    assert capabilities.supports_streaming is False
    assert capabilities.supports_dynamic_batching is False
    assert capabilities.max_concurrency == 0


def test_nebius_adapter_fails_closed_for_configuration_and_generation():
    adapter = NebiusCloudAdapter("nvidia/Nemotron-3-Nano-30B-A3B", "nebius")

    with pytest.raises(ConfigurationError, match="TASK-09"):
        adapter.apply_config(make_config({"max_tokens": 16}))
    with pytest.raises(ServingAdapterError, match="TASK-09"):
        adapter.generate("hello")
    with pytest.raises(ServingAdapterError, match="TASK-09"):
        list(adapter.stream_generate("hello"))
