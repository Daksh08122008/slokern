"""
Purpose: Runtime and endpoint health and environment metadata.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, 9, 12 and DEC-0014
"""

from typing import Any, Dict, Optional

from slokern.engine.serving.base import ConfigurationError, ServingRequest
from slokern.engine.serving.factory import create_serving_adapter


def get_health(adapter_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks serving runtime health, returns environment fingerprint and availability.
    """
    try:
        adapter = create_serving_adapter(backend=adapter_name)
        is_healthy = adapter.health_check()
        fp = adapter.get_environment_fingerprint()
        return {
            "status": "ok" if is_healthy else "degraded",
            "runtime": adapter.runtime_name,
            "model": adapter.model_name,
            "endpoint": fp.get("endpoint_host", "127.0.0.1:11434"),
            "is_healthy": is_healthy,
            "fingerprint": fp,
        }
    except ConfigurationError as exc:
        return {
            "status": "error",
            "runtime": adapter_name or "unknown",
            "model": "unknown",
            "endpoint": "unknown",
            "is_healthy": False,
            "error": str(exc),
            "fingerprint": {},
        }
    except Exception as exc:
        return {
            "status": "error",
            "runtime": adapter_name or "unknown",
            "model": "unknown",
            "endpoint": "unknown",
            "is_healthy": False,
            "error": str(exc),
            "fingerprint": {},
        }


def run_smoke_probe(
    adapter_name: Optional[str] = None,
    prompt: str = "SLOKern preflight smoke test probe.",
) -> Dict[str, Any]:
    """
    Executes a 1-request probe against the serving adapter, returning latencies and token counts.
    """
    try:
        adapter = create_serving_adapter(backend=adapter_name)
        if not adapter.health_check():
            return {
                "status": "failed",
                "runtime": adapter.runtime_name,
                "model": adapter.model_name,
                "status_code": 503,
                "first_token_latency_ms": None,
                "total_latency_ms": 0.0,
                "input_tokens": 0,
                "output_tokens": 0,
                "output_preview": "",
                "metadata": adapter.get_environment_fingerprint(),
                "error": "Runtime is unreachable or target model is not installed.",
            }

        req = ServingRequest(prompt=prompt, max_tokens=16, request_id="api-smoke-probe-01")
        resp = adapter.generate(req)

        preview = resp.text.strip().replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:57] + "..."

        is_success = resp.status_code == 200 and not resp.error
        return {
            "status": "success" if is_success else "failed",
            "runtime": adapter.runtime_name,
            "model": adapter.model_name,
            "status_code": resp.status_code,
            "first_token_latency_ms": resp.first_token_latency_ms,
            "total_latency_ms": resp.total_latency_ms,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "output_preview": preview,
            "metadata": resp.metadata,
            "error": resp.error,
        }
    except Exception as exc:
        return {
            "status": "failed",
            "runtime": adapter_name or "unknown",
            "model": "unknown",
            "status_code": 500,
            "first_token_latency_ms": None,
            "total_latency_ms": 0.0,
            "input_tokens": 0,
            "output_tokens": 0,
            "output_preview": "",
            "metadata": {},
            "error": str(exc),
        }
