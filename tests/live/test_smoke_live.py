"""
Purpose: Live endpoint smoke test probing OpenAI-compatible Nebius vLLM endpoint.
Owner: Rajdeep (Historical design: Aman)
Authority: Aligned with AGENTS.md Section 1, 10 and ROADMAP.md TASK-09 / BLK-04
"""

import os
import pytest

from slokern.contracts.config import CandidateConfig
from slokern.core.search.candidate_id import generate_candidate_id
from slokern.engine.serving.base import ServingRequest
from slokern.engine.serving.nebius import NebiusServingAdapter

pytestmark = pytest.mark.live


def test_smoke_live_endpoint():
    """
    Live endpoint preflight probe:
    If NEBIUS_API_KEY is unset, skips cleanly with actionable instructions (BLK-04 fallback).
    If NEBIUS_API_KEY is set, verifies health check, applies configuration, probes streaming,
    and captures environment fingerprint.
    """
    api_key = os.environ.get("NEBIUS_API_KEY", "").strip()
    if not api_key:
        pytest.skip(
            "NEBIUS_API_KEY environment variable is unset. Skipping live cloud probe per "
            "ROADMAP.md Section 6.1 (BLK-04 fallback policy). Set NEBIUS_API_KEY and "
            "NEBIUS_BASE_URL to execute live preflight probe."
        )

    base_url = os.environ.get("NEBIUS_BASE_URL", "https://api.studio.nebius.ai/v1")
    model_id = os.environ.get("NEBIUS_MODEL_ID", "meta-llama/Meta-Llama-3-8B-Instruct")

    adapter = NebiusServingAdapter(
        model_name=model_id,
        api_key=api_key,
        base_url=base_url,
    )

    # 1. Health check probe
    assert adapter.health_check() is True, f"Failed health check probe against {base_url}/models"

    # 2. Environment fingerprint read-back
    fingerprint = adapter.get_environment_fingerprint()
    assert fingerprint["provider"] == "nebius"
    assert fingerprint["has_credentials"] is True
    assert fingerprint["is_simulated"] is False

    # 3. Apply Candidate Config
    candidate = CandidateConfig(
        candidate_id=generate_candidate_id(model_id, adapter.runtime_name, {"max_tokens": 16}),
        model_name=model_id,
        runtime_name=adapter.runtime_name,
        requested_settings={"max_tokens": 16},
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )
    applied = adapter.apply_config(candidate, strict=True)
    assert applied.effective_settings.get("max_tokens") == 16

    # 4. Live streaming prompt probe
    req = ServingRequest(
        prompt="Respond with the single word 'VERIFIED'.",
        max_tokens=8,
        temperature=0.0,
    )
    chunks = list(adapter.stream_generate(req))
    assert len(chunks) > 0, "Expected at least 1 streaming chunk from live endpoint"

    first_chunk = chunks[0]
    assert first_chunk.latency_ms > 0.0, "Expected positive TTFT on first chunk"
    assert first_chunk.error is None, f"First chunk encountered error: {first_chunk.error}"

    # 5. Live synchronous generation probe
    resp = adapter.generate(req)
    assert resp.status_code == 200, f"Expected 200 OK, got {resp.status_code}: {resp.error}"
    assert len(resp.text.strip()) > 0, "Expected non-empty generated text"
    assert resp.output_tokens > 0, "Expected at least 1 output token"
