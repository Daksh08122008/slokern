"""
Purpose: Serving adapter for OpenAI-compatible vLLM endpoints on Nebius Cloud.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, 3, 9, 12 and ROADMAP.md TASK-09
"""

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, Optional, Union

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ParameterStatus
from slokern.engine.serving.base import (
    BaseServingAdapter,
    ConfigurationError,
    ServingRequest,
    ServingResponse,
    TokenChunk,
)
from slokern.engine.serving.capabilities import ParameterSpec, RuntimeCapabilities
from slokern.engine.store.redact import sanitize_secret_message


def _build_nebius_capabilities(runtime_name: str, model_name: str) -> RuntimeCapabilities:
    """Defines declared runtime capabilities for OpenAI-compatible Nebius/vLLM serving endpoint."""
    return RuntimeCapabilities(
        runtime_name=runtime_name,
        supported_models=[model_name, "*"],
        parameters={
            "max_num_seqs": ParameterSpec(
                name="max_num_seqs",
                param_type="int",
                default=32,
                min_value=1,
                max_value=256,
                description="Maximum concurrent sequences in a batch",
            ),
            "max_num_batched_tokens": ParameterSpec(
                name="max_num_batched_tokens",
                param_type="int",
                default=2048,
                min_value=128,
                max_value=32768,
                description="Maximum batched tokens per iteration",
            ),
            "temperature": ParameterSpec(
                name="temperature",
                param_type="float",
                default=0.0,
                min_value=0.0,
                max_value=2.0,
                description="Sampling temperature",
            ),
            "max_tokens": ParameterSpec(
                name="max_tokens",
                param_type="int",
                default=128,
                min_value=1,
                max_value=4096,
                description="Maximum output tokens to generate",
            ),
        },
        supports_streaming=True,
        supports_dynamic_batching=True,
        max_concurrency=128,
    )


class NebiusServingAdapter(BaseServingAdapter):
    """
    Serving adapter connecting to OpenAI-compatible vLLM endpoints hosted on Nebius Cloud.
    Uses standard library urllib (zero heavy third-party dependencies). Known API-key
    text is sanitized in selected adapter-generated messages; this is not a guarantee
    that every exception, remote response, or diagnostic path redacts all bearer tokens.
    """

    DEFAULT_BASE_URL = "https://api.tokenfactory.nebius.com/v1"
    DEFAULT_MODEL = "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"

    def __init__(
        self,
        model_name: Optional[str] = None,
        runtime_name: str = "vllm-nebius",
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_s: float = 30.0,
        capabilities: Optional[RuntimeCapabilities] = None,
    ) -> None:
        resolved_model = model_name or os.environ.get("NEBIUS_MODEL_ID", self.DEFAULT_MODEL)
        super().__init__(model_name=resolved_model, runtime_name=runtime_name)

        if not api_key:
            from slokern.config.secrets import load_runtime_secrets
            secrets = load_runtime_secrets()
            self._api_key = secrets.get("NEBIUS_API_KEY", "") or os.environ.get("NEBIUS_API_KEY", "")
        else:
            self._api_key = api_key

        raw_url = (base_url or os.environ.get("NEBIUS_BASE_URL", self.DEFAULT_BASE_URL)).rstrip("/")
        from slokern.config.secrets import validate_endpoint_url
        is_valid_url, url_err = validate_endpoint_url(raw_url)
        if not is_valid_url:
            raise ConfigurationError(f"Invalid Nebius base_url '{raw_url}': {url_err}")

        self.base_url = raw_url
        self.timeout_s = timeout_s
        self.capabilities = capabilities or _build_nebius_capabilities(runtime_name, resolved_model)


    @property
    def has_api_key(self) -> bool:
        """Returns True if a non-empty API key is configured."""
        return bool(self._api_key and self._api_key.strip())

    def _sanitize(self, msg: str) -> str:
        """Sanitizes text removing secrets."""
        return sanitize_secret_message(msg, self._api_key)

    def _build_headers(self) -> Dict[str, str]:
        """Constructs safe HTTP request headers."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "SLOKern/1.0",
        }
        if self.has_api_key:
            headers["Authorization"] = f"Bearer {self._api_key.strip()}"
        return headers

    def get_capabilities(self) -> RuntimeCapabilities:
        """Returns declared capabilities and supported parameter envelope."""
        return self.capabilities

    def get_environment_fingerprint(self) -> Dict[str, Any]:
        """
        Returns hardware, runtime, and endpoint metadata.
        Secret keys are never included in the fingerprint.
        """
        parsed = urllib.parse.urlparse(self.base_url)
        host_sanitized = parsed.netloc or "nebius-endpoint"
        return {
            "provider": "nebius",
            "endpoint_host": host_sanitized,
            "runtime_name": self.runtime_name,
            "model_name": self.model_name,
            "has_credentials": self.has_api_key,
            "is_simulated": False,
        }

    def health_check(self) -> bool:
        """
        Probes the Nebius serving runtime readiness by querying the /models endpoint.
        Returns True if the endpoint returns HTTP 200, False otherwise.
        """
        endpoint = f"{self.base_url}/models"
        req = urllib.request.Request(
            endpoint,
            headers=self._build_headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, self.timeout_s)) as resp:
                return resp.status == 200
        except Exception:
            return False

    def check_readiness(self) -> Dict[str, Any]:
        """
        Detailed readiness check probing endpoint reachability, credentials, and model presence.
        Returns a dictionary with 'ready' (bool), 'model_confirmed' (bool), 'error' (Optional[str]),
        and 'message' (Optional[str]). Zero secrets leaked.
        """
        if not self.has_api_key:
            return {
                "ready": False,
                "model_confirmed": False,
                "error": "Missing credentials: NEBIUS_API_KEY is not configured.",
                "message": None,
            }

        endpoint = f"{self.base_url}/models"
        req = urllib.request.Request(
            endpoint,
            headers=self._build_headers(),
            method="GET",
        )
        try:
            with urllib.request.urlopen(req, timeout=min(10.0, self.timeout_s)) as resp:
                if resp.status == 200:
                    body = resp.read().decode("utf-8")
                    data = json.loads(body)
                    models = [m.get("id") for m in data.get("data", []) if isinstance(m, dict)]
                    model_confirmed = (
                        (self.model_name in models)
                        or ("*" in models)
                        or any(self.model_name.lower() == str(m).lower() for m in models)
                    )
                    if model_confirmed:
                        msg = f"Endpoint reachable; model '{self.model_name}' confirmed in catalog ({len(models)} model(s) available)."
                    else:
                        msg = f"Endpoint reachable ({len(models)} model(s) available); model '{self.model_name}' not confirmed in catalog."
                    return {
                        "ready": True,
                        "model_confirmed": model_confirmed,
                        "error": None,
                        "message": msg,
                    }
                return {
                    "ready": False,
                    "model_confirmed": False,
                    "error": f"Endpoint returned HTTP {resp.status}",
                    "message": None,
                }
        except urllib.error.HTTPError as exc:
            sanitized = self._sanitize(f"HTTP {exc.code} {exc.reason}")
            return {
                "ready": False,
                "model_confirmed": False,
                "error": sanitized,
                "message": None,
            }
        except Exception as exc:
            sanitized = self._sanitize(f"Connection failure: {exc}")
            return {
                "ready": False,
                "model_confirmed": False,
                "error": sanitized,
                "message": None,
            }


    def apply_config(
        self,
        candidate_config: CandidateConfig,
        strict: bool = False,
    ) -> CandidateConfig:
        """
        Applies requested candidate configuration to the Nebius adapter.
        Evaluates settings against locally declared capabilities and stores the resulting
        config locally. It does not send serving flags to, or read effective flags back
        from, the remote endpoint (see BLK-17).
        If strict=True, raises ConfigurationError if any parameter is rejected or unsupported.
        """
        if not self.capabilities.is_model_supported(candidate_config.model_name):
            raise ConfigurationError(
                self._sanitize(
                    f"Model '{candidate_config.model_name}' is not supported by runtime '{self.runtime_name}'."
                )
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
                    self._sanitize(
                        f"Configuration rejected by runtime '{self.runtime_name}': {rejected_or_unsupported}. "
                        f"Notes: {notes}"
                    )
                )

        cand_id = candidate_config.candidate_id
        if not cand_id:
            from slokern.core.search.candidate_id import generate_candidate_id

            cand_id = generate_candidate_id(
                candidate_config.model_name,
                self.runtime_name,
                candidate_config.requested_settings,
            )

        updated_config = CandidateConfig(
            candidate_id=cand_id,
            model_name=candidate_config.model_name,
            runtime_name=self.runtime_name,
            requested_settings=candidate_config.requested_settings,
            effective_settings=effective_settings,
            parameter_status=parameter_status,
            environment_fingerprint=self.get_environment_fingerprint(),
        )
        self._current_config = updated_config
        return updated_config

    def _normalize_request(self, request: Union[ServingRequest, str]) -> ServingRequest:
        if isinstance(request, str):
            return ServingRequest(prompt=request)
        return request

    def generate(self, request: Union[ServingRequest, str]) -> ServingResponse:
        """
        Executes a synchronous non-streaming inference request against /chat/completions.
        Captures end-to-end latency and token counts.
        """
        req = self._normalize_request(request)
        endpoint = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": req.prompt}],
            "max_tokens": req.max_tokens,
            "temperature": req.temperature,
            "stream": False,
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        http_req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers=self._build_headers(),
            method="POST",
        )

        t_start = time.time()
        try:
            with urllib.request.urlopen(http_req, timeout=self.timeout_s) as resp:
                t_end = time.time()
                status_code = resp.status
                body = resp.read().decode("utf-8")
                total_latency_ms = round((t_end - t_start) * 1000.0, 2)

                resp_data = json.loads(body)
                choices = resp_data.get("choices", [])
                text = choices[0].get("message", {}).get("content", "") if choices else ""

                usage = resp_data.get("usage", {})
                input_tokens = usage.get("prompt_tokens", max(1, len(req.prompt.split())))
                output_tokens = usage.get("completion_tokens", max(1, len(text.split())))

                return ServingResponse(
                    request_id=req.request_id,
                    run_id=req.run_id,
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    first_token_latency_ms=total_latency_ms,  # For non-streaming, TTFT ~ total latency
                    itl_observations_ms=[],
                    total_latency_ms=total_latency_ms,
                    status_code=status_code,
                    error=None,
                    error_type=None,
                    metadata={"provider": "nebius", "live": True},
                )

        except urllib.error.HTTPError as exc:
            total_latency_ms = round((time.time() - t_start) * 1000.0, 2)
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass
            sanitized_err = self._sanitize(f"HTTP {exc.code} {exc.reason}: {error_body}")
            if exc.code == 401:
                error_type = "authentication_error"
            elif exc.code == 403:
                error_type = "permission_denied"
            elif exc.code == 404:
                error_type = "not_found"
            elif exc.code == 429:
                error_type = "rate_limit_exceeded"
            elif "out of memory" in sanitized_err.lower():
                error_type = "cuda_out_of_memory"
            else:
                error_type = "server_error"

            return ServingResponse(
                request_id=req.request_id,
                run_id=req.run_id,
                text="",
                input_tokens=max(1, len(req.prompt.split())),
                output_tokens=0,
                first_token_latency_ms=None,
                itl_observations_ms=[],
                total_latency_ms=total_latency_ms,
                status_code=exc.code,
                error=sanitized_err,
                error_type=error_type,
                metadata={"provider": "nebius", "live": True},
            )

        except (urllib.error.URLError, TimeoutError) as exc:
            total_latency_ms = round((time.time() - t_start) * 1000.0, 2)
            sanitized_err = self._sanitize(f"Network error: {exc}")
            is_timeout = "timed out" in str(exc).lower() or isinstance(exc, TimeoutError)

            return ServingResponse(
                request_id=req.request_id,
                run_id=req.run_id,
                text="",
                input_tokens=max(1, len(req.prompt.split())),
                output_tokens=0,
                first_token_latency_ms=None,
                itl_observations_ms=[],
                total_latency_ms=total_latency_ms,
                status_code=504 if is_timeout else 502,
                error=sanitized_err,
                error_type="timeout" if is_timeout else "network_error",
                metadata={"provider": "nebius", "live": True},
            )

    def stream_generate(self, request: Union[ServingRequest, str]) -> Iterator[TokenChunk]:
        """
        Executes a streaming request against /chat/completions (stream=True).
        Parses Server-Sent Events (SSE) line-by-line, capturing TTFT on the first token chunk
        and microsecond ITL observations on subsequent chunks.
        """
        req = self._normalize_request(request)
        endpoint = f"{self.base_url}/chat/completions"

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": req.prompt}],
            "max_tokens": min(req.max_tokens, 4096),
            "temperature": req.temperature,
            "stream": True,
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        http_req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers=self._build_headers(),
            method="POST",
        )

        t_start = time.time()
        last_chunk_time = t_start
        chunk_index = 0
        current_event: Optional[str] = None

        try:
            with urllib.request.urlopen(http_req, timeout=self.timeout_s) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        current_event = None
                        continue

                    # Track SSE event name if present (e.g. "event: error")
                    if line.startswith("event:"):
                        current_event = line[6:].strip()
                        continue

                    if not line.startswith("data:"):
                        continue

                    json_payload = line[5:]
                    if json_payload.startswith(" "):
                        json_payload = json_payload[1:]
                    json_payload = json_payload.strip()

                    if json_payload == "[DONE]":
                        break

                    try:
                        chunk_data = json.loads(json_payload)
                    except json.JSONDecodeError:
                        continue

                    # Handle provider error event embedded in SSE stream or flagged by event: error
                    is_error_event = (current_event in ("error", "provider_error")) or (
                        "error" in chunk_data and bool(chunk_data["error"])
                    )
                    if is_error_event:
                        err_obj = chunk_data.get("error", chunk_data)
                        err_msg = err_obj.get("message", str(err_obj)) if isinstance(err_obj, dict) else str(err_obj)
                        sanitized_err = self._sanitize(f"Provider stream error: {err_msg}")
                        yield TokenChunk(
                            token="",
                            token_id=chunk_index + 1,
                            index=chunk_index,
                            timestamp_ms=round((time.time() - t_start) * 1000.0, 2),
                            latency_ms=round((time.time() - last_chunk_time) * 1000.0, 2),
                            is_last=True,
                            error=sanitized_err,
                            metadata={"provider": "nebius", "live": True, "error_type": "provider_error"},
                        )
                        return

                    choices = chunk_data.get("choices", [])
                    if not choices:
                        continue

                    delta = choices[0].get("delta", {})
                    token_str = delta.get("content", "")
                    finish_reason = choices[0].get("finish_reason")
                    is_last = finish_reason is not None

                    if not token_str and not is_last:
                        continue

                    now = time.time()
                    elapsed_ms = round((now - t_start) * 1000.0, 2)

                    if chunk_index == 0:
                        interval_ms = elapsed_ms  # TTFT: request dispatch to first content token
                    else:
                        interval_ms = round((now - last_chunk_time) * 1000.0, 2)  # ITL

                    last_chunk_time = now

                    yield TokenChunk(
                        token=token_str,
                        token_id=chunk_index + 1,
                        index=chunk_index,
                        timestamp_ms=elapsed_ms,
                        latency_ms=interval_ms,
                        is_last=is_last,
                        error=None,
                        metadata={"provider": "nebius", "live": True},
                    )
                    chunk_index += 1

                    if is_last:
                        break

                if chunk_index == 0:
                    # Clean completion but zero tokens returned (empty stream)
                    now = time.time()
                    elapsed_ms = round((now - t_start) * 1000.0, 2)
                    yield TokenChunk(
                        token="",
                        token_id=1,
                        index=0,
                        timestamp_ms=elapsed_ms,
                        latency_ms=elapsed_ms,
                        is_last=True,
                        error=None,
                        metadata={"provider": "nebius", "live": True, "empty_stream": True},
                    )

        except urllib.error.HTTPError as exc:
            elapsed_ms = round((time.time() - t_start) * 1000.0, 2)
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass
            sanitized_err = self._sanitize(f"HTTP {exc.code} {exc.reason}: {error_body}")
            if exc.code == 401:
                error_type = "authentication_error"
            elif exc.code == 403:
                error_type = "permission_denied"
            elif exc.code == 404:
                error_type = "not_found"
            elif exc.code == 429:
                error_type = "rate_limit_exceeded"
            else:
                error_type = "server_error"

            yield TokenChunk(
                token="",
                token_id=chunk_index + 1,
                index=chunk_index,
                timestamp_ms=elapsed_ms,
                latency_ms=elapsed_ms,
                is_last=True,
                error=sanitized_err,
                metadata={"provider": "nebius", "live": True, "error_type": error_type, "http_status": exc.code},
            )

        except Exception as exc:
            elapsed_ms = round((time.time() - t_start) * 1000.0, 2)
            sanitized_err = self._sanitize(f"Serving stream error: {exc}")
            is_timeout = "timed out" in str(exc).lower() or isinstance(exc, TimeoutError)
            yield TokenChunk(
                token="",
                token_id=chunk_index + 1,
                index=chunk_index,
                timestamp_ms=elapsed_ms,
                latency_ms=elapsed_ms,
                is_last=True,
                error=sanitized_err,
                metadata={"provider": "nebius", "live": True, "error_type": "timeout" if is_timeout else "network_error"},
            )



# Backward compatibility alias for scaffold callers
NebiusCloudAdapter = NebiusServingAdapter
