"""
Purpose: `slokern smoke-test`: preflight probe checking endpoint health and request latency.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, 10, 11 and DEC-0014
"""

import sys
from typing import Optional

from slokern.engine.serving.base import ConfigurationError, ServingRequest
from slokern.engine.serving.factory import create_serving_adapter


def smoke_test_command(
    adapter: Optional[str] = None,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    prompt: str = "SLOKern preflight smoke test probe.",
) -> int:
    """
    Executes a preflight health check and single test request against the selected runtime.
    Displays backend name, environment metadata, health status, and latency.
    """
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
        print(f"[FAIL] Configuration Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"[FAIL] Invalid Backend: {exc}", file=sys.stderr)
        return 1

    fp = serving_adapter.get_environment_fingerprint()
    print(f"[SLOKern Preflight Smoke Test]")
    print(f"  Runtime:  {serving_adapter.runtime_name}")
    print(f"  Model:    {serving_adapter.model_name}")
    print(f"  Endpoint: {fp.get('endpoint_host', 'N/A')}")
    print(f"  Provider: {fp.get('provider', 'N/A')}")
    if fp.get("is_simulated"):
        print(f"  Notice:   DEMO DATA (Simulated adapter)")

    print("\nProbing health check...")
    try:
        is_healthy = serving_adapter.health_check()
    except Exception as exc:
        print(f"[FAIL] Health check encountered exception: {exc}", file=sys.stderr)
        return 1

    if not is_healthy:
        print(f"[FAIL] Health check failed: runtime is unreachable or model is not installed.", file=sys.stderr)
        return 1
    print("[OK] Runtime is healthy and ready to serve requests.")

    print(f"\nSending single probe request...")
    req = ServingRequest(
        prompt=prompt,
        max_tokens=16,
        request_id="smoke-test-probe-01",
    )
    try:
        resp = serving_adapter.generate(req)
    except Exception as exc:
        print(f"[FAIL] Probe request failed: {exc}", file=sys.stderr)
        return 1

    if resp.status_code != 200 or resp.error:
        print(f"[FAIL] Request failed with HTTP {resp.status_code}: {resp.error}", file=sys.stderr)
        return 1

    print("[OK] Probe request completed successfully:")
    print(f"  HTTP Status:    {resp.status_code}")
    print(f"  TTFT Latency:   {resp.first_token_latency_ms} ms")
    print(f"  Total Latency:  {resp.total_latency_ms} ms")
    print(f"  Token Counts:   {resp.input_tokens} input / {resp.output_tokens} output")
    preview = resp.text.strip().replace("\n", " ")
    if len(preview) > 60:
        preview = preview[:57] + "..."
    print(f"  Output Preview: \"{preview}\"")

    return 0
