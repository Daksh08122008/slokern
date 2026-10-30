"""
Purpose: `slokern smoke-test`: preflight probe checking endpoint health, request latency, and evidence artifact persistence.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, 10, 11 and DEC-0014
"""

from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Dict, Optional

from slokern.common.security import sanitize_credentials
from slokern.engine.serving.base import ConfigurationError, ServingRequest
from slokern.engine.serving.factory import create_serving_adapter


def _atomic_write_json(filepath: Path, data: Dict[str, Any]) -> None:
    """Safely writes JSON data atomically using a temporary file."""
    filepath.parent.mkdir(parents=True, exist_ok=True)
    temp_file = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        dir=filepath.parent,
        delete=False,
        prefix="smoke_",
        suffix=".tmp",
    )
    temp_path = Path(temp_file.name)
    try:
        json.dump(data, temp_file, indent=2)
        temp_file.flush()
        os.fsync(temp_file.fileno())
        temp_file.close()
        temp_path.replace(filepath)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def smoke_test_command(
    adapter: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    prompt: str = "SLOKern preflight smoke test probe.",
    artifact_path: Optional[str] = None,
    stream: bool = False,
) -> int:
    """
    Executes a preflight health check and single bounded test request against the selected runtime.
    Displays backend name, environment metadata, health status, and latency.
    Persists a machine-readable artifact at artifacts/smoke_test_result.json.
    """
    out_path = Path(artifact_path) if artifact_path else Path("artifacts") / "smoke_test_result.json"
    now_iso = datetime.now(timezone.utc).isoformat()

    artifact: Dict[str, Any] = {
        "timestamp": now_iso,
        "status": "FAILED",
        "adapter": adapter or os.environ.get("SLOKERN_ADAPTER", "local"),
        "model": model or "unknown",
        "endpoint_host": "unknown",
        "provider": "unknown",
        "is_simulated": False,
        "evidence_classification": "UNVERIFIED",
        "health_check": False,
        "model_confirmed": False,
        "probe_request": None,
        "streaming_probe": None,
        "error": None,
    }

    kwargs = {}
    if model:
        kwargs["model_name"] = model
    if base_url:
        kwargs["base_url"] = base_url
    if api_key:
        kwargs["api_key"] = api_key

    try:
        serving_adapter = create_serving_adapter(backend=adapter, **kwargs)
    except ConfigurationError as exc:
        sanitized_msg = sanitize_credentials(str(exc))
        print(f"[FAIL] Configuration Error: {sanitized_msg}", file=sys.stderr)
        artifact["error"] = sanitized_msg
        _atomic_write_json(out_path, artifact)
        return 1
    except ValueError as exc:
        sanitized_msg = sanitize_credentials(str(exc))
        print(f"[FAIL] Invalid Backend: {sanitized_msg}", file=sys.stderr)
        artifact["error"] = sanitized_msg
        _atomic_write_json(out_path, artifact)
        return 1

    fp = serving_adapter.get_environment_fingerprint()
    artifact["adapter"] = serving_adapter.runtime_name
    artifact["model"] = serving_adapter.model_name
    artifact["endpoint_host"] = fp.get("endpoint_host", "N/A")
    artifact["provider"] = fp.get("provider", "N/A")
    artifact["is_simulated"] = fp.get("is_simulated", False)
    artifact["evidence_classification"] = "DEMO DATA" if fp.get("is_simulated") else "LIVE"

    print("[SLOKern Preflight Smoke Test]")
    print(f"  Runtime:  {serving_adapter.runtime_name}")
    print(f"  Model:    {serving_adapter.model_name}")
    print(f"  Endpoint: {artifact['endpoint_host']}")
    print(f"  Provider: {artifact['provider']}")
    if artifact["is_simulated"]:
        print("  Notice:   DEMO DATA (Simulated adapter)")

    print("\nProbing health and readiness...")
    try:
        readiness_fn = getattr(serving_adapter, "check_readiness", None)
        is_healthy = False
        if callable(readiness_fn):
            readiness = readiness_fn()
            if isinstance(readiness, dict):
                is_healthy = bool(readiness.get("ready", False))
                artifact["model_confirmed"] = bool(readiness.get("model_confirmed", False))
                err_val = readiness.get("error")
                if err_val and isinstance(err_val, str):
                    artifact["error"] = sanitize_credentials(err_val)
            else:
                is_healthy = bool(serving_adapter.health_check())
                artifact["model_confirmed"] = is_healthy
        else:
            is_healthy = bool(serving_adapter.health_check())
            artifact["model_confirmed"] = is_healthy

    except Exception as exc:
        sanitized_err = sanitize_credentials(f"Health check exception: {exc}")
        print(f"[FAIL] {sanitized_err}", file=sys.stderr)
        artifact["error"] = sanitized_err
        _atomic_write_json(out_path, artifact)
        return 1

    artifact["health_check"] = is_healthy
    if not is_healthy:
        err_msg = artifact.get("error") or "Runtime is unreachable or model is not installed."
        print(f"[FAIL] Health check failed: {err_msg}", file=sys.stderr)
        _atomic_write_json(out_path, artifact)
        return 1

    print("[OK] Runtime is healthy and ready to serve requests.")

    print("\nSending single bounded probe request...")
    req = ServingRequest(
        prompt=prompt,
        max_tokens=16,
        request_id="smoke-test-probe-01",
    )

    if stream:
        try:
            chunks = list(serving_adapter.stream_generate(req))
        except Exception as exc:
            sanitized_err = sanitize_credentials(f"Probe request failed: {exc}")
            print(f"[FAIL] {sanitized_err}", file=sys.stderr)
            artifact["error"] = sanitized_err
            _atomic_write_json(out_path, artifact)
            return 1

        first_chunk = chunks[0] if chunks else None
        first_token_ttft_ms = first_chunk.timestamp_ms if first_chunk else None
        total_latency_ms = chunks[-1].timestamp_ms if chunks else 0.0
        generated_text = "".join(c.token for c in chunks)
        error_chunk = next((c for c in chunks if c.error), None)
        status_code = 200 if not error_chunk else 500

        preview = generated_text.strip().replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:57] + "..."

        artifact["probe_request"] = {
            "status_code": status_code,
            "ttft_ms": first_token_ttft_ms,
            "total_latency_ms": total_latency_ms,
            "input_tokens": max(1, len(prompt.split())),
            "output_tokens": len(chunks),
            "output_preview": preview,
            "error": error_chunk.error if error_chunk else None,
        }
        artifact["streaming_probe"] = {
            "chunk_count": len(chunks),
            "first_chunk_ttft_ms": first_token_ttft_ms,
            "stream_success": error_chunk is None and len(chunks) > 0,
        }

        if error_chunk is not None:
            sanitized_err = sanitize_credentials(f"Streaming probe failed: {error_chunk.error}")
            print(f"[FAIL] {sanitized_err}", file=sys.stderr)
            artifact["error"] = sanitized_err
            _atomic_write_json(out_path, artifact)
            return 1

        print("[OK] Single streaming probe request completed successfully:")
        print(f"  HTTP Status:    {status_code}")
        print(f"  TTFT Latency:   {first_token_ttft_ms} ms")
        print(f"  Total Latency:  {total_latency_ms} ms")
        print(f"  Token Chunks:   {len(chunks)} chunks received")
        print(f"  Output Preview: \"{preview}\"")
    else:
        try:
            resp = serving_adapter.generate(req)
        except Exception as exc:
            sanitized_err = sanitize_credentials(f"Probe request failed: {exc}")
            print(f"[FAIL] {sanitized_err}", file=sys.stderr)
            artifact["error"] = sanitized_err
            _atomic_write_json(out_path, artifact)
            return 1

        preview = resp.text.strip().replace("\n", " ")
        if len(preview) > 60:
            preview = preview[:57] + "..."

        artifact["probe_request"] = {
            "status_code": resp.status_code,
            "ttft_ms": resp.first_token_latency_ms,
            "total_latency_ms": resp.total_latency_ms,
            "input_tokens": resp.input_tokens,
            "output_tokens": resp.output_tokens,
            "output_preview": preview,
            "error": sanitize_credentials(resp.error) if resp.error else None,
        }

        if resp.status_code != 200 or resp.error:
            sanitized_err = sanitize_credentials(f"Request failed with HTTP {resp.status_code}: {resp.error}")
            print(f"[FAIL] {sanitized_err}", file=sys.stderr)
            artifact["error"] = sanitized_err
            _atomic_write_json(out_path, artifact)
            return 1

        print("[OK] Probe request completed successfully:")
        print(f"  HTTP Status:    {resp.status_code}")
        print(f"  TTFT Latency:   {resp.first_token_latency_ms} ms")
        print(f"  Total Latency:  {resp.total_latency_ms} ms")
        print(f"  Token Counts:   {resp.input_tokens} input / {resp.output_tokens} output")
        print(f"  Output Preview: \"{preview}\"")

    artifact["status"] = "PASSED"
    _atomic_write_json(out_path, artifact)
    print(f"\n[OK] Smoke test artifact successfully persisted to: {out_path}")
    return 0
