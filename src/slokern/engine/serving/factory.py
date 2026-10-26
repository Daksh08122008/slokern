"""
Purpose: Serving adapter factory with strict precedence resolution and zero silent fallback.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with AGENTS.md Section 1, 3, 12 and DEC-0014
"""

import os
from typing import Optional

from slokern.engine.serving.base import BaseServingAdapter, ConfigurationError
from slokern.engine.serving.fake import FakeServingAdapter
from slokern.engine.serving.nebius import NebiusServingAdapter
from slokern.engine.serving.ollama import OllamaServingAdapter


def create_serving_adapter(
    backend: Optional[str] = None,
    **kwargs,
) -> BaseServingAdapter:
    """
    Factory function creating the appropriate serving adapter according to explicit precedence:
    1. Explicit `backend` argument (e.g. from CLI `--adapter`).
    2. `SLOKERN_ADAPTER` environment variable.
    3. Default: `"local"` (Ollama on loopback).

    Enforces zero silent fallback: if 'nebius' credentials are missing, raises ConfigurationError.
    """
    resolved_backend = backend
    if not resolved_backend:
        resolved_backend = os.environ.get("SLOKERN_ADAPTER")
    if not resolved_backend:
        resolved_backend = "local"

    normalized = resolved_backend.strip().lower()

    if normalized == "local":
        local_kwargs = {
            k: v for k, v in kwargs.items()
            if k in ("model_name", "runtime_name", "base_url", "timeout_s", "allow_remote", "capabilities")
        }
        return OllamaServingAdapter(**local_kwargs)

    elif normalized == "nebius":
        api_key = kwargs.get("api_key") or os.environ.get("NEBIUS_API_KEY", "")
        if not api_key or not api_key.strip():
            raise ConfigurationError(
                "Missing required credentials for Nebius backend: NEBIUS_API_KEY must be set "
                "in environment or passed explicitly. Zero silent fallback per DEC-0014."
            )
        nebius_kwargs = {
            k: v for k, v in kwargs.items()
            if k in ("model_name", "runtime_name", "api_key", "base_url", "timeout_s", "capabilities")
        }
        if "api_key" not in nebius_kwargs:
            nebius_kwargs["api_key"] = api_key
        return NebiusServingAdapter(**nebius_kwargs)

    elif normalized == "fake":
        fake_kwargs = {
            k: v for k, v in kwargs.items()
            if k in (
                "model_name", "runtime_name", "capabilities", "failure_config",
                "seed", "simulate_delay", "base_ttft_ms", "ttft_per_token_ms",
                "base_itl_ms", "itl_per_seq_ms", "default_output_tokens",
            )
        }
        return FakeServingAdapter(**fake_kwargs)

    else:
        raise ValueError(
            f"Unknown serving backend '{resolved_backend}'. Valid backends are: 'local', 'nebius', 'fake'."
        )
