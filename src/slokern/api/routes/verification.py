"""
Purpose: Verification runner dispatch endpoint for independent audits under fresh run ID.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 7 and DEC-0014
"""

import uuid
from pathlib import Path
from typing import Any, Dict, Optional

from slokern.api.routes.runs import ACTIVE_RUNS, RUNS_LOCK
from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import ArrivalMode
from slokern.contracts.metrics import MetricSet
from slokern.contracts.spec import (
    SLOConstraint,
    SLOSpec,
    WorkloadSpec,
)
from slokern.contracts.verification import VerificationRecord
from slokern.core.verification.protocol import run_independent_verification
from slokern.engine.serving.factory import create_serving_adapter


def dispatch_verification_run(
    payload: Dict[str, Any],
    artifacts_root: str = "artifacts",
) -> Dict[str, Any]:
    """
    Reruns the specified candidate under a fresh verification_run_id and evaluates metric drift.
    """
    adapter_name = payload.get("adapter", "local")
    adapter = create_serving_adapter(backend=adapter_name)

    cand_id = payload.get("candidate_id", f"cand-{adapter.runtime_name}-01")
    orig_run_id = payload.get("original_run_id", f"run-search-{cand_id[:8]}")
    experiment_id = payload.get("experiment_id")

    is_local = adapter_name in ("ollama", "local")
    default_rate = 1.0 if is_local else 2.0
    default_concurrency = 1 if is_local else 2

    raw_workload = payload.get("workload")
    raw_slo = payload.get("slo")

    with RUNS_LOCK:
        if orig_run_id in ACTIVE_RUNS:
            if not raw_workload and ACTIVE_RUNS[orig_run_id].get("workload"):
                raw_workload = ACTIVE_RUNS[orig_run_id]["workload"]
            if not raw_slo and ACTIVE_RUNS[orig_run_id].get("slo"):
                raw_slo = ACTIVE_RUNS[orig_run_id]["slo"]
            if not experiment_id and ACTIVE_RUNS[orig_run_id].get("experiment_id"):
                experiment_id = ACTIVE_RUNS[orig_run_id]["experiment_id"]

    # If experiment_id is still unknown, search artifacts on disk for the original run
    if not experiment_id:
        for p in Path(artifacts_root).glob(f"experiments/*/runs/{orig_run_id}/metrics.json"):
            experiment_id = p.parents[2].name
            break

    if not experiment_id:
        experiment_id = f"exp-{uuid.uuid4().hex[:8]}"

    if raw_workload:
        workload = WorkloadSpec.model_validate(raw_workload)
    else:
        workload = WorkloadSpec(
            schema_version="1.0.0",
            workload_name="verification-workload",
            fixture_id="fix-ui-verify-01",
            arrival_mode=ArrivalMode.CONSTANT,
            target_offered_rate=default_rate,
            concurrency_limit=default_concurrency,
            warmup_duration_s=1,
            measurement_duration_s=5,
            max_input_tokens=64,
            max_output_tokens=32,
        )

    if raw_slo:
        slo = SLOSpec.model_validate(raw_slo)
    else:
        slo = SLOSpec(
            slo_id="slo-verify-01",
            constraints=[
                SLOConstraint(
                    metric_name="ttft_ms",
                    statistic="p95",
                    threshold=2500.0,
                    unit="ms",
                    operator="<=",
                ),
            ],
            min_sample_count=2,
        )

    candidate_config = CandidateConfig(
        candidate_id=cand_id,
        model_name=adapter.model_name,
        runtime_name=adapter.runtime_name,
        requested_settings=payload.get("requested_settings", {}),
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )

    orig_metrics: Optional[MetricSet] = None
    with RUNS_LOCK:
        if orig_run_id in ACTIVE_RUNS and ACTIVE_RUNS[orig_run_id].get("metric_set"):
            try:
                orig_metrics = MetricSet.model_validate(ACTIVE_RUNS[orig_run_id]["metric_set"])
                if not payload.get("experiment_id"):
                    experiment_id = ACTIVE_RUNS[orig_run_id].get("experiment_id", experiment_id)
            except Exception:
                orig_metrics = None

    if orig_metrics is None:
        if experiment_id:
            direct_p = Path(artifacts_root) / "experiments" / experiment_id / "runs" / orig_run_id / "metrics.json"
            if direct_p.is_file():
                try:
                    orig_metrics = MetricSet.model_validate_json(direct_p.read_text(encoding="utf-8"))
                except Exception:
                    pass
        if orig_metrics is None:
            for p in Path(artifacts_root).glob(f"experiments/*/runs/{orig_run_id}/metrics.json"):
                try:
                    orig_metrics = MetricSet.model_validate_json(p.read_text(encoding="utf-8"))
                    break
                except Exception:
                    pass

    record: VerificationRecord = run_independent_verification(
        original_run_id=orig_run_id,
        candidate_config=candidate_config,
        workload=workload,
        slo=slo,
        experiment_id=experiment_id,
        original_metrics=orig_metrics,
        adapter=adapter,
        artifacts_root=artifacts_root,
        isolate_process=False,
    )

    # Persist record in experiment folder
    exp_dir = Path(artifacts_root) / "experiments" / experiment_id
    exp_dir.mkdir(parents=True, exist_ok=True)
    (exp_dir / "verification_record.json").write_text(
        record.model_dump_json(indent=2), encoding="utf-8"
    )

    return record.model_dump()
