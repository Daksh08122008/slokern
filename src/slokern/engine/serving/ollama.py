"""
Purpose: Serving adapter for local Ollama inference engine running on loopback.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with AGENTS.md Section 1, 3, 9, 12 and DEC-0014
"""

import ipaddress
import json
import os
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Iterator, List, Optional, Union

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ParameterStatus
from slokern.engine.serving.base import (
    BaseServingAdapter,
    ConfigurationError,
    ServingAdapterError,
    ServingRequest,
    ServingResponse,
    TokenChunk,
)
from slokern.engine.serving.capabilities import ParameterSpec, RuntimeCapabilities


def sanitize_secret_message(message: str, known_secret: Optional[str] = None) -> str:
    """Redacts API keys, Bearer tokens, and secrets from error messages and logs."""
    if not message:
        return ""
    sanitized = str(message)
    if known_secret and len(known_secret) >= 6:
        sanitized = sanitized.replace(known_secret, "***REDACTED***")
    sanitized = re.sub(
        r"(Bearer\s+)[A-Za-z0-9_\-\.]{6,}",
        r"\g<1>***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )
    sanitized = re.sub(
        r"((?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.]{6,}(['\"]?)",
        r"\g<1>***REDACTED***\g<2>",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized


class StrictLoopbackRedirectHandler(urllib.request.HTTPRedirectHandler):
    """
    Redirect handler that unconditionally prohibits HTTP redirects to prevent loopback pivoting.
    Conforms to DEC-0014 loopback security boundary.
    """

    def redirect_request(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any, newurl: str) -> urllib.request.Request:
        raise ConfigurationError(
            f"HTTP redirect ({code}) prohibited for loopback security boundary: redirection to '{newurl}' is blocked"
        )

    def _extract_location(self, headers: Any) -> str:
        if hasattr(headers, "get"):
            return headers.get("Location") or headers.get("location") or ""
        return ""

    def http_error_301(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any) -> urllib.request.Request:
        return self.redirect_request(req, fp, code, msg, headers, self._extract_location(headers))

    def http_error_302(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any) -> urllib.request.Request:
        return self.redirect_request(req, fp, code, msg, headers, self._extract_location(headers))

    def http_error_303(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any) -> urllib.request.Request:
        return self.redirect_request(req, fp, code, msg, headers, self._extract_location(headers))

    def http_error_307(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any) -> urllib.request.Request:
        return self.redirect_request(req, fp, code, msg, headers, self._extract_location(headers))

    def http_error_308(self, req: urllib.request.Request, fp: Any, code: int, msg: str, headers: Any) -> urllib.request.Request:
        return self.redirect_request(req, fp, code, msg, headers, self._extract_location(headers))


def _build_ollama_capabilities(runtime_name: str, model_name: str) -> RuntimeCapabilities:
    """
    Defines declared runtime capabilities for local Ollama serving endpoint.
    Process startup flags (max_num_batched_tokens, max_num_seqs) are omitted
    to honestly report them as UNSUPPORTED per BLK-17 / DEC-0014.
    """
    return RuntimeCapabilities(
        runtime_name=runtime_name,
        supported_models=[model_name, f"{model_name}:latest", "*"],
        parameters={
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
                description="Maximum output tokens to generate (num_predict)",
            ),
        },
        supports_streaming=True,
        supports_dynamic_batching=False,
        max_concurrency=16,
    )


class OllamaServingAdapter(BaseServingAdapter):
    """
    Serving adapter connecting to a locally running Ollama instance on loopback.
    Enforces loopback address validation, redirect prohibitions, and client-observed
    monotonic timing. Captures server-side evaluation duration metadata.
    """

    DEFAULT_BASE_URL = "http://127.0.0.1:11434"
    DEFAULT_MODEL = "qwen3:4b-instruct-2507-q4_K_M"

    def __init__(
        self,
        model_name: Optional[str] = None,
        runtime_name: str = "ollama",
        base_url: Optional[str] = None,
        timeout_s: float = 30.0,
        allow_remote: bool = False,
        capabilities: Optional[RuntimeCapabilities] = None,
    ) -> None:
        resolved_model = model_name or os.environ.get("OLLAMA_MODEL_ID", self.DEFAULT_MODEL)
        super().__init__(model_name=resolved_model, runtime_name=runtime_name)

        raw_url = base_url or os.environ.get("OLLAMA_BASE_URL", self.DEFAULT_BASE_URL)
        self.base_url = self._validate_and_normalize_url(raw_url, allow_remote=allow_remote)
        self.timeout_s = timeout_s
        self.capabilities = capabilities or _build_ollama_capabilities(runtime_name, resolved_model)
        self._opener = urllib.request.build_opener(StrictLoopbackRedirectHandler())

    def _validate_and_normalize_url(self, raw_url: str, allow_remote: bool = False) -> str:
        """
        Validates the base URL against strict loopback security rules and userinfo prohibitions.
        """
        parsed = urllib.parse.urlsplit(raw_url)
        if not parsed.scheme or not parsed.netloc:
            raise ConfigurationError(f"Invalid Ollama base_url '{raw_url}': missing scheme or netloc")

        # Prohibit URL userinfo (e.g. user:pass@host)
        if parsed.username or parsed.password or "@" in parsed.netloc:
            raise ConfigurationError(
                f"URL credentials (userinfo) are prohibited in Ollama base_url '{raw_url}'"
            )

        hostname = (parsed.hostname or "").lower()
        if not hostname:
            raise ConfigurationError(f"Invalid Ollama base_url '{raw_url}': missing hostname")

        remote_allowed = allow_remote or (
            os.environ.get("OLLAMA_ALLOW_REMOTE", "").strip().lower() in ("1", "true")
        )

        is_loopback = False
        if hostname in ("localhost", "localhost."):
            is_loopback = True
        else:
            try:
                ip = ipaddress.ip_address(hostname)
                is_loopback = ip.is_loopback
            except ValueError:
                is_loopback = False

        if not is_loopback and not remote_allowed:
            raise ConfigurationError(
                f"Host '{hostname}' is not a permitted loopback address (127.0.0.1, localhost, ::1). "
                f"Remote Ollama access must be explicitly enabled via allow_remote=True or OLLAMA_ALLOW_REMOTE=1."
            )

        return raw_url.rstrip("/")

    def _sanitize(self, msg: str) -> str:
        return sanitize_secret_message(msg)

    def _build_headers(self) -> Dict[str, str]:
        """Constructs headers. Note: Authorization header is strictly omitted for local isolation."""
        return {
            "Content-Type": "application/json",
            "User-Agent": "SLOKern/1.0",
        }

    def get_capabilities(self) -> RuntimeCapabilities:
        """Returns declared capabilities and supported parameter envelope."""
        return self.capabilities

    def get_environment_fingerprint(self) -> Dict[str, Any]:
        """Returns local hardware/runtime environment documentation."""
        parsed = urllib.parse.urlsplit(self.base_url)
        return {
            "provider": "ollama",
            "endpoint_host": parsed.netloc or "127.0.0.1:11434",
            "runtime_name": self.runtime_name,
            "model_name": self.model_name,
            "is_simulated": False,
            "security_boundary": "strict_loopback",
        }

    def health_check(self) -> bool:
        """
        Probes local Ollama daemon readiness via GET /api/tags and verifies presence of model.
        Returns True if reachable and target model is installed; False otherwise.
        Never triggers silent model downloads.
        """
        endpoint = f"{self.base_url}/api/tags"
        req = urllib.request.Request(
            endpoint,
            headers=self._build_headers(),
            method="GET",
        )
        try:
            with self._opener.open(req, timeout=min(5.0, self.timeout_s)) as resp:
                if resp.status != 200:
                    return False
                body = resp.read().decode("utf-8")
                data = json.loads(body)
                models = data.get("models", [])
                target = self.model_name.lower()
                target_base = target.split(":")[0]

                for m in models:
                    name = str(m.get("name", "")).lower()
                    model_field = str(m.get("model", "")).lower()
                    if name == target or name == f"{target}:latest" or model_field == target:
                        return True
                    # Also match if model prefix matches and target has tag
                    if ":" in target and name == target:
                        return True
                    if name == target_base or name.startswith(f"{target_base}:"):
                        return True
                return False
        except Exception:
            return False

    def apply_config(
        self,
        candidate_config: CandidateConfig,
        strict: bool = False,
    ) -> CandidateConfig:
        """
        Applies candidate configuration to Ollama adapter.
        Classifies unsupported parameters (such as max_num_batched_tokens and max_num_seqs)
        honestly as UNSUPPORTED per BLK-17 / DEC-0014.
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
        Synchronously executes a non-streaming request against /api/chat.
        Measures client-observed start-to-first-content latency via monotonic timing
        and captures server eval metrics in metadata.
        """
        req = self._normalize_request(request)
        endpoint = f"{self.base_url}/api/chat"

        options: Dict[str, Any] = {}
        if req.temperature is not None:
            options["temperature"] = req.temperature
        if req.max_tokens is not None:
            options["num_predict"] = req.max_tokens

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": req.prompt}],
            "stream": False,
            "options": options,
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        http_req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers=self._build_headers(),
            method="POST",
        )

        t_start = time.monotonic()
        try:
            with self._opener.open(http_req, timeout=self.timeout_s) as resp:
                t_end = time.monotonic()
                status_code = resp.status
                body = resp.read().decode("utf-8")
                total_latency_ms = round((t_end - t_start) * 1000.0, 2)

                resp_data = json.loads(body)
                if "error" in resp_data:
                    sanitized_err = self._sanitize(str(resp_data["error"]))
                    return ServingResponse(
                        request_id=req.request_id,
                        run_id=req.run_id,
                        text="",
                        input_tokens=max(1, len(req.prompt.split())),
                        output_tokens=0,
                        first_token_latency_ms=None,
                        itl_observations_ms=[],
                        total_latency_ms=total_latency_ms,
                        status_code=500,
                        error=sanitized_err,
                        error_type="server_error",
                        metadata={"provider": "ollama", "live": True},
                    )

                text = resp_data.get("message", {}).get("content", "")

                prompt_eval_count = resp_data.get("prompt_eval_count")
                input_tokens = int(prompt_eval_count) if prompt_eval_count is not None else max(1, len(req.prompt.split()))

                eval_count = resp_data.get("eval_count")
                output_tokens = int(eval_count) if eval_count is not None else max(0, len(text.split()))

                metadata: Dict[str, Any] = {
                    "provider": "ollama",
                    "model": self.model_name,
                    "live": True,
                }
                # Server reported durations (nanoseconds to milliseconds)
                if "prompt_eval_duration" in resp_data:
                    metadata["server_prompt_eval_duration_ms"] = round(
                        resp_data["prompt_eval_duration"] / 1_000_000.0, 3
                    )
                if "eval_duration" in resp_data:
                    metadata["server_eval_duration_ms"] = round(
                        resp_data["eval_duration"] / 1_000_000.0, 3
                    )

                return ServingResponse(
                    request_id=req.request_id,
                    run_id=req.run_id,
                    text=text,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    first_token_latency_ms=total_latency_ms,
                    itl_observations_ms=[],
                    total_latency_ms=total_latency_ms,
                    status_code=status_code,
                    error=None,
                    error_type=None,
                    metadata=metadata,
                )

        except urllib.error.HTTPError as exc:
            total_latency_ms = round((time.monotonic() - t_start) * 1000.0, 2)
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass
            sanitized_err = self._sanitize(f"HTTP {exc.code} {exc.reason}: {error_body}")
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
                metadata={"provider": "ollama", "live": True},
            )

        except (urllib.error.URLError, TimeoutError, ConfigurationError) as exc:
            total_latency_ms = round((time.monotonic() - t_start) * 1000.0, 2)
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
                metadata={"provider": "ollama", "live": True},
            )

    def stream_generate(self, request: Union[ServingRequest, str]) -> Iterator[TokenChunk]:
        """
        Executes a streaming request against /api/chat (stream=True).
        Parses NDJSON stream line-by-line, determining TTFT on the first content chunk
        via time.monotonic(), capturing server eval metadata, and recording chunk-gap deltas.
        """
        req = self._normalize_request(request)
        endpoint = f"{self.base_url}/api/chat"

        options: Dict[str, Any] = {}
        if req.temperature is not None:
            options["temperature"] = req.temperature
        if req.max_tokens is not None:
            options["num_predict"] = req.max_tokens

        payload = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": req.prompt}],
            "stream": True,
            "options": options,
        }
        data_bytes = json.dumps(payload).encode("utf-8")

        http_req = urllib.request.Request(
            endpoint,
            data=data_bytes,
            headers=self._build_headers(),
            method="POST",
        )

        t_start = time.monotonic()
        last_chunk_time = t_start
        chunk_index = 0
        first_content_received = False

        try:
            with self._opener.open(http_req, timeout=self.timeout_s) as resp:
                for raw_line in resp:
                    line = raw_line.decode("utf-8").strip()
                    if not line:
                        continue

                    try:
                        chunk_data = json.loads(line)
                    except json.JSONDecodeError:
                        continue

                    msg = chunk_data.get("message", {})
                    token_str = msg.get("content", "")
                    is_done = chunk_data.get("done", False)

                    # Check for server-reported error in stream chunk
                    if "error" in chunk_data:
                        elapsed_ms = round((time.monotonic() - t_start) * 1000.0, 2)
                        sanitized_err = self._sanitize(str(chunk_data["error"]))
                        yield TokenChunk(
                            token="",
                            token_id=chunk_index + 1,
                            index=chunk_index,
                            timestamp_ms=elapsed_ms,
                            latency_ms=elapsed_ms if chunk_index == 0 else round((time.monotonic() - last_chunk_time) * 1000.0, 2),
                            is_last=True,
                            error=sanitized_err,
                            metadata={"provider": "ollama", "live": True, "error_type": "server_error"},
                        )
                        return

                    # Skip empty chunks if not the final chunk
                    if not token_str and not is_done:
                        continue

                    now = time.monotonic()
                    elapsed_ms = round((now - t_start) * 1000.0, 2)

                    if not first_content_received:
                        interval_ms = elapsed_ms  # First content latency (TTFT)
                        if token_str:
                            first_content_received = True
                    else:
                        interval_ms = round((now - last_chunk_time) * 1000.0, 2)  # Chunk-gap delta

                    last_chunk_time = now

                    metadata: Dict[str, Any] = {
                        "provider": "ollama",
                        "live": True,
                        "is_chunk_gap": True,
                    }
                    if is_done:
                        if "prompt_eval_duration" in chunk_data:
                            metadata["server_prompt_eval_duration_ms"] = round(
                                chunk_data["prompt_eval_duration"] / 1_000_000.0, 3
                            )
                        if "eval_duration" in chunk_data:
                            metadata["server_eval_duration_ms"] = round(
                                chunk_data["eval_duration"] / 1_000_000.0, 3
                            )

                    yield TokenChunk(
                        token=token_str,
                        token_id=chunk_index + 1,
                        index=chunk_index,
                        timestamp_ms=elapsed_ms,
                        latency_ms=interval_ms,
                        is_last=is_done,
                        error=None,
                        metadata=metadata,
                    )
                    chunk_index += 1

                    if is_done:
                        break

                if chunk_index == 0:
                    elapsed_ms = round((time.monotonic() - t_start) * 1000.0, 2)
                    yield TokenChunk(
                        token="",
                        token_id=1,
                        index=0,
                        timestamp_ms=elapsed_ms,
                        latency_ms=elapsed_ms,
                        is_last=True,
                        error="Stream ended without content",
                        metadata={"provider": "ollama", "live": True, "error_type": "premature_close"},
                    )
                elif not is_done:
                    now = time.monotonic()
                    elapsed_ms = round((now - t_start) * 1000.0, 2)
                    yield TokenChunk(
                        token="",
                        token_id=chunk_index + 1,
                        index=chunk_index,
                        timestamp_ms=elapsed_ms,
                        latency_ms=round((now - last_chunk_time) * 1000.0, 2),
                        is_last=True,
                        error="Stream interrupted prematurely before completion",
                        metadata={"provider": "ollama", "live": True, "error_type": "premature_close"},
                    )

        except urllib.error.HTTPError as exc:
            elapsed_ms = round((time.monotonic() - t_start) * 1000.0, 2)
            error_body = ""
            try:
                error_body = exc.read().decode("utf-8")
            except Exception:
                pass
            sanitized_err = self._sanitize(f"HTTP {exc.code} {exc.reason}: {error_body}")
            yield TokenChunk(
                token="",
                token_id=chunk_index + 1,
                index=chunk_index,
                timestamp_ms=elapsed_ms,
                latency_ms=elapsed_ms,
                is_last=True,
                error=sanitized_err,
                metadata={"provider": "ollama", "live": True, "http_status": exc.code},
            )

        except Exception as exc:
            elapsed_ms = round((time.monotonic() - t_start) * 1000.0, 2)
            sanitized_err = self._sanitize(f"Serving stream error: {exc}")
            yield TokenChunk(
                token="",
                token_id=chunk_index + 1,
                index=chunk_index,
                timestamp_ms=elapsed_ms,
                latency_ms=elapsed_ms,
                is_last=True,
                error=sanitized_err,
                metadata={"provider": "ollama", "live": True},
            )
