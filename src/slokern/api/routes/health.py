"""
Purpose: Runtime and endpoint health and environment metadata.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, 9, 12 and DEC-0014
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional

from slokern.engine.serving.base import ConfigurationError, ServingRequest
from slokern.engine.serving.factory import create_serving_adapter


def get_health(adapter_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Checks serving runtime health, returns environment fingerprint and availability.
    """
    try:
        adapter = create_serving_adapter(backend=adapter_name)
        readiness_fn = getattr(adapter, "check_readiness", None)
        if callable(readiness_fn):
            readiness = readiness_fn()
            is_healthy = bool(readiness.get("ready", False))
            diag_error = readiness.get("error")
            diag_msg = readiness.get("message")
        else:
            is_healthy = adapter.health_check()
            diag_error = None if is_healthy else "Runtime health check failed"
            diag_msg = "Runtime healthy" if is_healthy else None

        fp = adapter.get_environment_fingerprint()
        res: Dict[str, Any] = {
            "status": "ok" if is_healthy else "degraded",
            "runtime": adapter.runtime_name,
            "model": adapter.model_name,
            "endpoint": fp.get("endpoint_host", "127.0.0.1:11434"),
            "is_healthy": is_healthy,
            "fingerprint": fp,
        }
        if diag_error:
            res["error"] = diag_error
        if diag_msg:
            res["message"] = diag_msg
        return res
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
            readiness_fn = getattr(adapter, "check_readiness", None)
            err_detail = "Runtime is unreachable or target model is not installed."
            if callable(readiness_fn):
                readiness = readiness_fn()
                if readiness.get("error"):
                    err_detail = readiness["error"]
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
                "error": err_detail,
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


def get_latest_smoke_test(artifacts_root: str = "artifacts") -> Dict[str, Any]:
    """
    Retrieves the latest verified preflight smoke test artifact from the filesystem.
    Priority:
    1. artifacts_root/smoke_test_result.json
    2. Deep search for smoke_test_result.json under artifacts_root
    """
    root = Path(artifacts_root)
    primary = root / "smoke_test_result.json"
    if primary.exists():
        try:
            return json.loads(primary.read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": f"Failed reading {primary}: {e}", "status": "FAILED"}

    matches = list(root.glob("**/smoke_test_result.json"))
    if matches:
        matches.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        try:
            return json.loads(matches[0].read_text(encoding="utf-8"))
        except Exception as e:
            return {"error": f"Failed reading {matches[0]}: {e}", "status": "FAILED"}

    return {
        "status": "NONE",
        "evidence_classification": "UNVERIFIED",
        "error": "No smoke test artifact recorded on filesystem",
    }


def get_runtime_profile(artifacts_root: str = "artifacts") -> Dict[str, Any]:
    """
    Retrieves complete runtime profile, capabilities, and active environment metadata.
    Preserves exact evidence classification and highlights Token Factory scheduling limits.
    """
    smoke_art = get_latest_smoke_test(artifacts_root)
    is_live = smoke_art.get("evidence_classification") == "LIVE"
    model_name = smoke_art.get("model", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
    endpoint_host = smoke_art.get("endpoint_host", "api.tokenfactory.nebius.com")
    adapter_name = smoke_art.get("adapter", "vllm-nebius")
    provider_name = smoke_art.get("provider", "nebius")

    return {
        "status": "ok",
        "adapter": adapter_name,
        "provider": provider_name,
        "model": model_name,
        "endpoint_host": endpoint_host,
        "endpoint_url": f"https://{endpoint_host}/v1" if endpoint_host != "N/A" else "N/A",
        "is_healthy": True,
        "is_simulated": smoke_art.get("is_simulated", False),
        "evidence_classification": "LIVE" if is_live else smoke_art.get("evidence_classification", "UNVERIFIED"),
        "capability_preflight": {
            "status": "VALID",
            "limitation_note": "Server-side vLLM scheduler controls unavailable through this endpoint.",
            "token_factory_constraint": True,
            "supported_serving_controls": [
                "request_rate",
                "concurrency_limit",
                "max_tokens",
                "temperature",
                "streaming"
            ],
            "unsupported_serving_controls": [
                "max_num_seqs",
                "kv_cache_dtype",
                "gpu_memory_utilization",
                "tensor_parallel_size"
            ]
        },
        "latest_smoke_test": smoke_art,
    }
