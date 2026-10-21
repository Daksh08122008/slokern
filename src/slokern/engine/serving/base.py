"""
Purpose: Serving adapter interface (capabilities, apply, environment, stream, health).
Owner: Rajdeep (Historical design: Aman)
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Iterator, AsyncIterator, Union
import asyncio
from pydantic import BaseModel, Field, ConfigDict

from slokern.contracts.config import CandidateConfig
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.engine.serving.capabilities import RuntimeCapabilities


class ServingAdapterError(Exception):
    """Base exception for serving adapter runtime errors."""
    pass


class ConfigurationError(ServingAdapterError):
    """Raised when requested serving configuration cannot be applied or is rejected."""
    pass


class ServingOOMError(ServingAdapterError):
    """Raised when serving runtime encounters Out-Of-Memory (OOM)."""
    pass


class ServingTimeoutError(ServingAdapterError):
    """Raised when inference request times out."""
    pass


class ServingServerError(ServingAdapterError):
    """Raised when serving runtime encounters internal failure."""
    pass


class ServingRequest(BaseModel):
    """Inference generation request."""
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(..., description="Input prompt text")
    max_tokens: int = Field(128, description="Maximum tokens to generate", ge=1)
    temperature: float = Field(0.0, description="Sampling temperature", ge=0.0)
    request_id: str = Field("", description="Unique request identifier")
    run_id: str = Field("", description="Experiment run identifier")
    stream: bool = Field(False, description="Whether to stream response tokens")
    extra_params: Dict[str, Any] = Field(default_factory=dict, description="Additional generation parameters")


class TokenChunk(BaseModel):
    """Single token chunk emitted in streaming response."""
    model_config = ConfigDict(extra="forbid")

    token: str = Field(..., description="Generated text token")
    token_id: int = Field(0, description="Synthetic or tokenizer token identifier")
    index: int = Field(..., description="0-indexed position in output sequence")
    timestamp_ms: float = Field(..., description="Timestamp of chunk arrival in ms", ge=0.0)
    latency_ms: float = Field(0.0, description="Interval latency from previous token (ITL) or start (TTFT)", ge=0.0)
    is_last: bool = Field(False, description="True if final chunk in stream")
    error: Optional[str] = Field(None, description="Error message if generation aborted")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags, e.g. DEMO DATA")


class ServingResponse(BaseModel):
    """Completed inference response with latency and token metrics."""
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(..., description="Unique request identifier")
    run_id: str = Field(..., description="Experiment run identifier")
    text: str = Field(..., description="Generated completion text")
    input_tokens: int = Field(..., description="Count of prompt tokens", ge=0)
    output_tokens: int = Field(..., description="Count of generated output tokens", ge=0)
    first_token_latency_ms: Optional[float] = Field(None, description="Time to first token (TTFT) in ms", ge=0.0)
    itl_observations_ms: List[float] = Field(default_factory=list, description="Observed inter-token latencies in ms")
    total_latency_ms: float = Field(0.0, description="End-to-end request duration in ms", ge=0.0)
    status_code: int = Field(200, description="HTTP response status code")
    error: Optional[str] = Field(None, description="Error detail if failed")
    error_type: Optional[str] = Field(None, description="Error category: 'cuda_out_of_memory', 'timeout', 'server_error', etc.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata tags, e.g. DEMO DATA")

    def to_raw_measurement(
        self,
        scheduled_at: float,
        sent_at: float,
        is_warmup: bool = False,
        is_valid: Optional[bool] = None
    ) -> RawRequestMeasurement:
        """Converts serving response into canonical RawRequestMeasurement event."""
        first_token_at = (
            sent_at + (self.first_token_latency_ms / 1000.0)
            if self.first_token_latency_ms is not None
            else None
        )
        completed_at = sent_at + (self.total_latency_ms / 1000.0)

        # Monotonicity protection: completed_at must never be earlier than first_token_at
        if first_token_at is not None and completed_at < first_token_at:
            completed_at = first_token_at

        if is_valid is None:
            timing_valid = (
                scheduled_at <= sent_at
                and (first_token_at is None or first_token_at >= sent_at)
                and completed_at >= sent_at
                and (self.first_token_latency_ms is None or self.total_latency_ms >= self.first_token_latency_ms)
            )
            is_valid = (
                self.status_code == 200
                and self.error is None
                and self.error_type is None
                and timing_valid
            )

        inferred_error_type = self.error_type
        if inferred_error_type is None and (self.status_code != 200 or self.error is not None):
            inferred_error_type = "http_error"

        return RawRequestMeasurement(
            request_id=self.request_id,
            run_id=self.run_id,
            scheduled_at=scheduled_at,
            sent_at=sent_at,
            first_token_at=first_token_at,
            completed_at=completed_at,
            http_status=self.status_code,
            input_tokens=self.input_tokens,
            output_tokens=self.output_tokens,
            itl_observations_ms=self.itl_observations_ms if self.itl_observations_ms else None,
            error_type=inferred_error_type,
            is_warmup=is_warmup,
            is_valid=is_valid
        )


class BaseServingAdapter(ABC):
    """
    Abstract Base Class defining the contract between the SLOKern experiment worker
    and inference serving runtimes (e.g., FakeServingAdapter, NebiusCloudAdapter).
    """

    def __init__(self, model_name: str, runtime_name: str) -> None:
        self.model_name = model_name
        self.runtime_name = runtime_name
        self._current_config: Optional[CandidateConfig] = None

    @property
    def current_config(self) -> Optional[CandidateConfig]:
        """Returns the currently active CandidateConfig, if applied."""
        return self._current_config

    @abstractmethod
    def apply_config(self, candidate_config: CandidateConfig, strict: bool = False) -> CandidateConfig:
        """
        Applies a candidate configuration to the serving runtime.
        Performs read-back verification: checks requested vs applied settings,
        classifies parameter statuses (APPLIED, UNSUPPORTED, REJECTED, DEFAULT_FALLBACK),
        attaches environment fingerprint, and returns the verified CandidateConfig.
        If strict=True, raises ConfigurationError if any parameter is rejected or unsupported.
        """
        pass

    @abstractmethod
    def health_check(self) -> bool:
        """Probes the serving runtime health and readiness to serve requests."""
        pass

    @abstractmethod
    def get_capabilities(self) -> RuntimeCapabilities:
        """Returns declared capabilities and supported parameter envelope."""
        pass

    @abstractmethod
    def get_environment_fingerprint(self) -> Dict[str, Any]:
        """Returns hardware, runtime, driver, and environment fingerprint."""
        pass

    @abstractmethod
    def generate(self, request: Union[ServingRequest, str]) -> ServingResponse:
        """Executes a synchronous request generation and returns complete ServingResponse."""
        pass

    @abstractmethod
    def stream_generate(self, request: Union[ServingRequest, str]) -> Iterator[TokenChunk]:
        """Streams token chunks for an inference request."""
        pass

    async def agenerate(self, request: Union[ServingRequest, str]) -> ServingResponse:
        """Asynchronous request generation (default implementation delegates to threadpool)."""
        return await asyncio.to_thread(self.generate, request)

    async def astream_generate(self, request: Union[ServingRequest, str]) -> AsyncIterator[TokenChunk]:
        """Asynchronous streaming token generation."""
        for chunk in self.stream_generate(request):
            yield chunk
            await asyncio.sleep(0)
