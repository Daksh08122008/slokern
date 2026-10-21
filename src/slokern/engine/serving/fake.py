"""
Purpose: Simulated adapter for tests and demos; all output tagged simulated and DEMO DATA.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, Section 8, and docs/adr/0001-mvp-scope-and-evidence.md
"""

from typing import Dict, Any, List, Optional, Iterator, AsyncIterator, Union
import random
import time
import asyncio
from pydantic import BaseModel, Field, ConfigDict

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ParameterStatus
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.engine.serving.capabilities import RuntimeCapabilities, ParameterSpec
from slokern.engine.serving.base import (
    BaseServingAdapter,
    ServingRequest,
    TokenChunk,
    ServingResponse,
    ConfigurationError,
    ServingOOMError,
    ServingTimeoutError,
    ServingServerError,
    ServingAdapterError,
)

DEMO_WORDS: List[str] = [
    "This", "is", "a", "deterministic", "simulated", "inference", "response",
    "generated", "for", "SLOKern", "demonstration", "purposes", "under", "DEMO", "DATA", "rules."
]


class FailureInjectionConfig(BaseModel):
    """Configuration for injecting simulated runtime failures."""
    model_config = ConfigDict(extra="forbid")

    force_oom: bool = Field(False, description="Always trigger CUDA OOM error")
    force_timeout: bool = Field(False, description="Always trigger timeout error")
    force_server_error: bool = Field(False, description="Always trigger 500 server error")
    oom_max_num_seqs_threshold: Optional[int] = Field(None, description="Trigger OOM if effective max_num_seqs > threshold")
    oom_on_high_memory_pressure: bool = Field(False, description="Trigger OOM if gpu_memory_utilization > 0.95 and max_num_seqs >= 64")
    health_status: bool = Field(True, description="Health check return value")
    error_rate_prob: float = Field(0.0, ge=0.0, le=1.0, description="Random failure probability")
    target_error_request_ids: List[str] = Field(default_factory=list, description="List of request IDs that should fail")
    raise_on_failure: bool = Field(False, description="If True, raise serving exceptions instead of returning error response")


def _build_default_capabilities(runtime_name: str) -> RuntimeCapabilities:
    """Builds standard capabilities for synthetic vLLM serving runtime."""
    return RuntimeCapabilities(
        runtime_name=runtime_name,
        supported_models=[
            "meta-llama/Meta-Llama-3-8B-Instruct",
            "Nemotron-3-Nano-30B-A3B",
            "mistralai/Mistral-7B-Instruct-v0.3",
            "*"
        ],
        parameters={
            "max_num_seqs": ParameterSpec(
                name="max_num_seqs",
                param_type="int",
                default=32,
                min_value=1,
                max_value=256,
                description="Maximum concurrent sequences in a batch"
            ),
            "gpu_memory_utilization": ParameterSpec(
                name="gpu_memory_utilization",
                param_type="float",
                default=0.90,
                min_value=0.1,
                max_value=1.0,
                description="Fraction of GPU memory for KV cache"
            ),
            "max_model_len": ParameterSpec(
                name="max_model_len",
                param_type="int",
                default=2048,
                min_value=128,
                max_value=32768,
                description="Maximum model sequence length"
            ),
            "kv_cache_dtype": ParameterSpec(
                name="kv_cache_dtype",
                param_type="str",
                default="auto",
                allowed_values=["auto", "fp16", "fp8"],
                description="Data type for KV cache"
            ),
            "tensor_parallel_size": ParameterSpec(
                name="tensor_parallel_size",
                param_type="int",
                default=1,
                min_value=1,
                max_value=8,
                allowed_values=[1, 2, 4, 8],
                description="Number of GPUs for tensor parallelism"
            ),
        },
        supports_streaming=True,
        supports_dynamic_batching=True,
        max_concurrency=256
    )


class FakeServingAdapter(BaseServingAdapter):
    """
    Deterministic synthetic serving adapter for offline testing, CI, and local demos.
    All outputs, metadata, and environment fingerprints are unambiguously labeled DEMO DATA.
    Requires no GPU and performs zero external network calls.
    """

    def __init__(
        self,
        model_name: str = "meta-llama/Meta-Llama-3-8B-Instruct",
        runtime_name: str = "vllm-fake",
        capabilities: Optional[RuntimeCapabilities] = None,
        failure_config: Optional[FailureInjectionConfig] = None,
        seed: int = 42,
        simulate_delay: bool = False,
        base_ttft_ms: float = 12.0,
        ttft_per_token_ms: float = 0.04,
        base_itl_ms: float = 8.0,
        itl_per_seq_ms: float = 0.05,
        default_output_tokens: int = 16
    ) -> None:
        super().__init__(model_name=model_name, runtime_name=runtime_name)
        self.capabilities = capabilities or _build_default_capabilities(runtime_name)
        self.failure_config = failure_config or FailureInjectionConfig()
        self.seed = seed
        self.simulate_delay = simulate_delay
        self.base_ttft_ms = base_ttft_ms
        self.ttft_per_token_ms = ttft_per_token_ms
        self.base_itl_ms = base_itl_ms
        self.itl_per_seq_ms = itl_per_seq_ms
        self.default_output_tokens = default_output_tokens

    def get_capabilities(self) -> RuntimeCapabilities:
        """Returns declared capabilities and supported parameter envelope."""
        return self.capabilities

    def get_environment_fingerprint(self) -> Dict[str, Any]:
        """
        Returns synthetic hardware, runtime, driver, and environment fingerprint.
        Explicitly branded DEMO DATA per AGENTS.md Section 1 and Section 8.
        """
        return {
            "mode": "DEMO DATA",
            "is_simulated": True,
            "device": "DEMO DATA (Synthetic vLLM Engine)",
            "hardware_model": "NVIDIA H100 80GB SXM5 (DEMO DATA)",
            "cuda_version": "12.4 (DEMO DATA)",
            "driver_version": "550.54.14 (DEMO DATA)",
            "runtime_name": self.runtime_name,
            "runtime_version": "0.6.0-fake-demo",
            "commit": "simulated-demo-data-000000",
            "simulated": True,
            "disclaimer": "DEMO DATA: Synthetic serving adapter with zero GPU allocation."
        }

    def health_check(self) -> bool:
        """Returns True if the serving runtime is healthy and ready to serve requests."""
        return self.failure_config.health_status

    def set_health(self, healthy: bool) -> None:
        """Dynamically adjusts the simulated health status."""
        self.failure_config.health_status = healthy

    def inject_oom(self, enable: bool = True) -> None:
        """Enables or disables forced CUDA OOM failure."""
        self.failure_config.force_oom = enable

    def inject_timeout(self, enable: bool = True) -> None:
        """Enables or disables forced request timeout failure."""
        self.failure_config.force_timeout = enable

    def inject_server_error(self, enable: bool = True) -> None:
        """Enables or disables forced 500 server error."""
        self.failure_config.force_server_error = enable

    def reset_failures(self) -> None:
        """Resets all injected failures to default healthy state."""
        self.failure_config = FailureInjectionConfig()

    def apply_config(self, candidate_config: CandidateConfig, strict: bool = False) -> CandidateConfig:
        """
        Applies requested candidate configuration to the synthetic runtime.
        Performs read-back verification: classifies settings into APPLIED,
        UNSUPPORTED, REJECTED, or DEFAULT_FALLBACK, attaches environment
        fingerprint, and stores updated configuration.
        If strict=True, raises ConfigurationError if any parameter is rejected or unsupported.
        """
        if not self.capabilities.is_model_supported(candidate_config.model_name):
            raise ConfigurationError(
                f"Model '{candidate_config.model_name}' is not supported by runtime '{self.runtime_name}'. "
                f"Supported models: {self.capabilities.supported_models}"
            )

        effective_settings, parameter_status, notes = self.capabilities.evaluate_settings(
            candidate_config.requested_settings
        )

        if strict:
            rejected_or_unsupported = {
                k: v for k, v in parameter_status.items()
                if v in (ParameterStatus.REJECTED, ParameterStatus.UNSUPPORTED)
            }
            if rejected_or_unsupported:
                raise ConfigurationError(
                    f"Configuration rejected by runtime '{self.runtime_name}': {rejected_or_unsupported}. "
                    f"Notes: {notes}"
                )

        cand_id = candidate_config.candidate_id
        if not cand_id:
            cand_id = generate_candidate_id(
                candidate_config.model_name,
                candidate_config.runtime_name or self.runtime_name,
                candidate_config.requested_settings
            )

        updated_config = CandidateConfig(
            candidate_id=cand_id,
            model_name=candidate_config.model_name,
            runtime_name=self.runtime_name,
            requested_settings=candidate_config.requested_settings,
            effective_settings=effective_settings,
            parameter_status=parameter_status,
            environment_fingerprint=self.get_environment_fingerprint()
        )
        self._current_config = updated_config
        return updated_config

    def _normalize_request(self, request: Union[ServingRequest, str]) -> ServingRequest:
        if isinstance(request, str):
            return ServingRequest(prompt=request)
        return request

    def _check_failure_trigger(self, request: ServingRequest) -> Optional[tuple[int, str, str]]:
        """
        Evaluates failure injection rules for an incoming request.
        Returns None if request should succeed, or (status_code, error_message, error_type).
        """
        effective = self._current_config.effective_settings if self._current_config else {}
        max_num_seqs = effective.get("max_num_seqs", 32)
        gpu_mem = effective.get("gpu_memory_utilization", 0.90)

        failure: Optional[tuple[int, str, str]] = None

        # 1. Targeted request ID failure
        if request.request_id and request.request_id in self.failure_config.target_error_request_ids:
            failure = (500, f"CUDA out of memory: Injected failure for request {request.request_id} [DEMO DATA]", "cuda_out_of_memory")

        # 2. Forced OOM
        elif self.failure_config.force_oom:
            failure = (500, "CUDA out of memory: Tried to allocate 2.00 GiB (GPU 0; 79.15 GiB total capacity; 78.50 GiB already allocated) [DEMO DATA]", "cuda_out_of_memory")

        # 3. Threshold OOM on batch concurrency
        elif self.failure_config.oom_max_num_seqs_threshold is not None:
            if max_num_seqs > self.failure_config.oom_max_num_seqs_threshold:
                failure = (500, f"CUDA out of memory: Requested max_num_seqs {max_num_seqs} exceeds memory threshold {self.failure_config.oom_max_num_seqs_threshold} [DEMO DATA]", "cuda_out_of_memory")

        # 4. Memory pressure OOM
        elif self.failure_config.oom_on_high_memory_pressure:
            if gpu_mem > 0.95 and max_num_seqs >= 64:
                failure = (500, "CUDA out of memory: High memory pressure triggered KV cache exhaustion [DEMO DATA]", "cuda_out_of_memory")

        # 5. Forced Timeout
        elif self.failure_config.force_timeout:
            failure = (504, "Gateway Timeout: Inference request exceeded deadline [DEMO DATA]", "timeout")

        # 6. Forced Server Error
        elif self.failure_config.force_server_error:
            failure = (500, "Internal Server Error: Model worker crashed [DEMO DATA]", "server_error")

        # 7. Probabilistic error
        elif self.failure_config.error_rate_prob > 0.0:
            token_seed = self.seed + abs(hash(request.request_id or request.prompt)) % 100000
            rnd = random.Random(token_seed)
            if rnd.random() < self.failure_config.error_rate_prob:
                failure = (500, "Internal Server Error: Injected probabilistic failure [DEMO DATA]", "server_error")

        if failure is not None and self.failure_config.raise_on_failure:
            _, err_msg, err_type = failure
            if err_type == "cuda_out_of_memory":
                raise ServingOOMError(err_msg)
            elif err_type == "timeout":
                raise ServingTimeoutError(err_msg)
            elif err_type == "server_error":
                raise ServingServerError(err_msg)
            else:
                raise ServingAdapterError(err_msg)

        return failure

    def _calculate_latencies(
        self,
        request: ServingRequest,
        input_tokens: int,
        output_tokens: int
    ) -> tuple[float, List[float], float]:
        """
        Calculates deterministic, reproducible TTFT and ITL observations.
        Scaling factors:
            - Input tokens scale prefill latency (TTFT)
            - Batch concurrency (max_num_seqs) slightly increases TTFT and ITL
            - Tensor parallel size scales latency down
            - FP8 KV-cache provides a 10% latency reduction
        """
        effective = self._current_config.effective_settings if self._current_config else {}
        max_num_seqs = effective.get("max_num_seqs", 32)
        kv_cache_dtype = effective.get("kv_cache_dtype", "auto")
        tp_size = max(1, int(effective.get("tensor_parallel_size", 1)))

        # Deterministic pseudorandom generator based on seed and request identifier
        req_hash = abs(hash(request.request_id or request.prompt)) % 100000
        rnd = random.Random(self.seed + req_hash)

        tp_factor = 1.0 / (tp_size ** 0.5)
        dtype_factor = 0.90 if kv_cache_dtype == "fp8" else 1.0

        # TTFT Calculation
        base_ttft = self.base_ttft_ms + (input_tokens * self.ttft_per_token_ms)
        seq_ttft_penalty = max(0.0, (max_num_seqs - 32) * 0.05)
        ttft_calc = (base_ttft + seq_ttft_penalty) * tp_factor * dtype_factor
        ttft_jitter = rnd.uniform(-0.15, 0.15)
        ttft_ms = max(1.0, round(ttft_calc + ttft_jitter, 2))

        # ITL Observations
        itl_observations: List[float] = []
        base_itl = self.base_itl_ms + (self.itl_per_seq_ms * (max_num_seqs / 32.0))
        itl_calc = base_itl * tp_factor * dtype_factor

        for _ in range(1, output_tokens):
            itl_jitter = rnd.uniform(-0.10, 0.10)
            itl_i = max(0.5, round(itl_calc + itl_jitter, 2))
            itl_observations.append(itl_i)

        total_latency_ms = round(ttft_ms + sum(itl_observations), 2)
        return ttft_ms, itl_observations, total_latency_ms

    def generate(
        self,
        request: Union[ServingRequest, str],
        simulate_delay: Optional[bool] = None
    ) -> ServingResponse:
        """Executes a synchronous request generation and returns complete ServingResponse."""
        req = self._normalize_request(request)
        should_delay = self.simulate_delay if simulate_delay is None else simulate_delay

        # Estimate input tokens
        words = req.prompt.strip().split() if req.prompt.strip() else []
        input_tokens = max(1, int(len(words) * 1.3)) if words else 0

        # Check failure conditions
        failure = self._check_failure_trigger(req)
        if failure is not None:
            status_code, err_msg, err_type = failure
            dur_ms = 30000.0 if err_type == "timeout" else 5.0
            return ServingResponse(
                request_id=req.request_id,
                run_id=req.run_id,
                text="",
                input_tokens=input_tokens,
                output_tokens=0,
                first_token_latency_ms=None,
                itl_observations_ms=[],
                total_latency_ms=dur_ms,
                status_code=status_code,
                error=err_msg,
                error_type=err_type,
                metadata={
                    "demo_data": True,
                    "label": "DEMO DATA",
                    "simulated": True,
                    "adapter": "FakeServingAdapter",
                    "failure_injected": err_type
                }
            )

        # Determine output token count
        custom_out = req.extra_params.get("synthetic_tokens", self.default_output_tokens)
        output_tokens = max(1, min(req.max_tokens, custom_out))

        # Calculate reproducible latencies
        ttft_ms, itl_obs, total_lat_ms = self._calculate_latencies(req, input_tokens, output_tokens)

        # Build response text
        tokens_text = [DEMO_WORDS[i % len(DEMO_WORDS)] for i in range(output_tokens)]
        full_text = "[DEMO DATA] " + " ".join(tokens_text)

        if should_delay:
            time.sleep(total_lat_ms / 1000.0)

        return ServingResponse(
            request_id=req.request_id,
            run_id=req.run_id,
            text=full_text,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            first_token_latency_ms=ttft_ms,
            itl_observations_ms=itl_obs,
            total_latency_ms=total_lat_ms,
            status_code=200,
            error=None,
            error_type=None,
            metadata={
                "demo_data": True,
                "label": "DEMO DATA",
                "simulated": True,
                "adapter": "FakeServingAdapter"
            }
        )

    def stream_generate(self, request: Union[ServingRequest, str]) -> Iterator[TokenChunk]:
        """Streams token chunks for an inference request."""
        req = self._normalize_request(request)

        words = req.prompt.strip().split() if req.prompt.strip() else []
        input_tokens = max(1, int(len(words) * 1.3)) if words else 0

        failure = self._check_failure_trigger(req)
        if failure is not None:
            status_code, err_msg, err_type = failure
            dur_ms = 30000.0 if err_type == "timeout" else 5.0
            yield TokenChunk(
                token="",
                token_id=0,
                index=0,
                timestamp_ms=dur_ms,
                latency_ms=dur_ms,
                is_last=True,
                error=err_msg,
                metadata={
                    "demo_data": True,
                    "label": "DEMO DATA",
                    "simulated": True,
                    "adapter": "FakeServingAdapter",
                    "failure_injected": err_type,
                    "status_code": status_code
                }
            )
            return

        custom_out = req.extra_params.get("synthetic_tokens", self.default_output_tokens)
        output_tokens = max(1, min(req.max_tokens, custom_out))
        ttft_ms, itl_obs, _ = self._calculate_latencies(req, input_tokens, output_tokens)

        tokens_text = [DEMO_WORDS[i % len(DEMO_WORDS)] for i in range(output_tokens)]

        # Chunk 0: TTFT
        if self.simulate_delay:
            time.sleep(ttft_ms / 1000.0)

        yield TokenChunk(
            token="[DEMO DATA] " + tokens_text[0],
            token_id=1,
            index=0,
            timestamp_ms=ttft_ms,
            latency_ms=ttft_ms,
            is_last=(output_tokens == 1),
            error=None,
            metadata={"demo_data": True, "label": "DEMO DATA", "simulated": True}
        )

        elapsed = ttft_ms
        for i in range(1, output_tokens):
            chunk_lat = itl_obs[i - 1]
            elapsed = round(elapsed + chunk_lat, 2)
            if self.simulate_delay:
                time.sleep(chunk_lat / 1000.0)

            yield TokenChunk(
                token=" " + tokens_text[i],
                token_id=i + 1,
                index=i,
                timestamp_ms=elapsed,
                latency_ms=chunk_lat,
                is_last=(i == output_tokens - 1),
                error=None,
                metadata={"demo_data": True, "label": "DEMO DATA", "simulated": True}
            )

    async def agenerate(self, request: Union[ServingRequest, str]) -> ServingResponse:
        """Asynchronous request generation for synthetic adapter."""
        req = self._normalize_request(request)
        return self.generate(req)

    async def astream_generate(self, request: Union[ServingRequest, str]) -> AsyncIterator[TokenChunk]:
        """Asynchronous streaming token generation."""
        req = self._normalize_request(request)
        for chunk in self.stream_generate(req):
            yield chunk

