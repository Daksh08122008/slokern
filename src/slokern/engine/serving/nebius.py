"""Fail-closed placeholder for the not-yet-verified Nebius integration."""

from typing import Any, Dict, Iterator, Union

from slokern.contracts.config import CandidateConfig
from slokern.engine.serving.base import (
    BaseServingAdapter,
    ConfigurationError,
    ServingAdapterError,
    ServingRequest,
    ServingResponse,
    TokenChunk,
)
from slokern.engine.serving.capabilities import RuntimeCapabilities


class NebiusCloudAdapter(BaseServingAdapter):
    """Explicitly unavailable scaffold until TASK-09 verifies live behavior.

    The adapter intentionally advertises no model or runtime capabilities and
    never reports healthy. This prevents a placeholder from being mistaken
    for a usable live serving endpoint.
    """

    def get_capabilities(self) -> RuntimeCapabilities:
        return RuntimeCapabilities(
            runtime_name="NebiusCloudTokenFactory (unverified)",
            supported_models=[],
            parameters={},
            supports_streaming=False,
            supports_dynamic_batching=False,
            max_concurrency=0,
        )

    def apply_config(
        self, candidate_config: CandidateConfig, strict: bool = False
    ) -> CandidateConfig:
        raise ConfigurationError(
            "Nebius serving is unavailable: live endpoint configuration has not "
            "been implemented and verified (TASK-09)"
        )

    def health_check(self) -> bool:
        return False

    def get_environment_fingerprint(self) -> Dict[str, Any]:
        return {
            "provider": "Nebius",
            "adapter": "NebiusCloudAdapter",
            "live_verified": False,
        }

    def generate(self, request: Union[ServingRequest, str]) -> ServingResponse:
        raise ServingAdapterError(
            "Nebius serving is unavailable until the live adapter is implemented "
            "and verified (TASK-09)"
        )

    def stream_generate(
        self, request: Union[ServingRequest, str]
    ) -> Iterator[TokenChunk]:
        raise ServingAdapterError(
            "Nebius streaming is unavailable until the live adapter is implemented "
            "and verified (TASK-09)"
        )
