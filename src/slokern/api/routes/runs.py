"""
Purpose: Run lifecycle orchestration, async execution, status query and SSE queuing.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 3, 5, 7 and DEC-0014
"""

import json
import threading
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from slokern.api.sse import SSEEventQueue
from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    ArrivalMode,
    ExecutionStatus,
    FeasibilityVerdict,
)
from slokern.contracts.run import RunRecord
from slokern.contracts.spec import (
    SLOConstraint,
    SLOSpec,
    WorkloadSpec,
)
from slokern.engine.runner.run_executor import SingleRunExecutor
from slokern.engine.serving.factory import create_serving_adapter

ACTIVE_RUNS: Dict[str, Dict[str, Any]] = {}
ACTIVE_QUEUES: Dict[str, SSEEventQueue] = {}
RUNS_LOCK = threading.Lock()


def get_run_queue(run_id: str) -> Optional[SSEEventQueue]:
    with RUNS_LOCK:
        return ACTIVE_QUEUES.get(run_id)


def _execute_run_worker(
    run_id: str,
    experiment_id: str,
    candidate_config: CandidateConfig,
    workload: WorkloadSpec,
    slo: SLOSpec,
    adapter_name: Optional[str],
    artifacts_root: str,
    sse_queue: SSEEventQueue,
) -> None:
    try:
        adapter = create_serving_adapter(backend=adapter_name)
        executor = SingleRunExecutor(
            adapter=adapter,
            artifacts_root=Path(artifacts_root),
            isolate_process=False,
        )

        sse_queue.emit("status", {"status": "STARTING", "run_id": run_id, "message": "Applying configuration and warm-up."})

        # Run benchmark
        run_res = executor.execute(
            candidate_config=candidate_config,
            workload=workload,
            slo=slo,
            experiment_id=experiment_id,
            run_id=run_id,
        )

        # Build payload
        metric_dump = run_res.metric_set.model_dump() if run_res.metric_set else None
        feas_dump = run_res.feasibility_result.model_dump() if run_res.feasibility_result else None

        result_data: Dict[str, Any] = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "candidate_id": candidate_config.candidate_id,
            "execution_status": run_res.execution_status.value,
            "is_completed": run_res.is_completed,
            "is_feasible": run_res.is_feasible,
            "metric_set": metric_dump,
            "feasibility_result": feas_dump,
            "raw_measurements_count": run_res.raw_measurements_count,
            "artifact_paths": run_res.artifact_paths,
            "workload": workload.model_dump(),
            "slo": slo.model_dump(),
            "error": None,
        }

        with RUNS_LOCK:
            ACTIVE_RUNS[run_id] = result_data

        sse_queue.emit("completed", {"run_id": run_id, "run_result": result_data})
        sse_queue.close()

    except Exception as exc:
        err_msg = str(exc)
        result_data = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "candidate_id": candidate_config.candidate_id,
            "execution_status": ExecutionStatus.FAILED.value,
            "is_completed": False,
            "is_feasible": False,
            "metric_set": None,
            "feasibility_result": None,
            "raw_measurements_count": 0,
            "artifact_paths": {},
            "error": err_msg,
        }
        with RUNS_LOCK:
            ACTIVE_RUNS[run_id] = result_data

        sse_queue.emit("failed", {"run_id": run_id, "error": err_msg})
        sse_queue.close()


def dispatch_single_run(
    payload: Dict[str, Any],
    artifacts_root: str = "artifacts",
) -> Dict[str, Any]:
    """
    Validates input parameters, registers run record, and launches execution in a background worker.
    """
    adapter_name = payload.get("adapter", "local")
    adapter = create_serving_adapter(backend=adapter_name)

    # Resolve or create workload spec
    raw_workload = payload.get("workload")
    if raw_workload:
        workload = WorkloadSpec.model_validate(raw_workload)
    else:
        workload = WorkloadSpec(
            schema_version="1.0.0",
            workload_name=payload.get("workload_name", "live-ui-benchmark"),
            fixture_id="fix-ui-live-01",
            arrival_mode=ArrivalMode(payload.get("arrival_mode", "constant")),
            target_offered_rate=float(payload.get("target_offered_rate", 2.0)),
            concurrency_limit=int(payload.get("concurrency_limit", 2)),
            warmup_duration_s=int(payload.get("warmup_duration_s", 1)),
            measurement_duration_s=int(payload.get("measurement_duration_s", 5)),
            max_input_tokens=int(payload.get("max_input_tokens", 64)),
            max_output_tokens=int(payload.get("max_output_tokens", 32)),
        )

    # Resolve or create SLO spec
    raw_slo = payload.get("slo")
    if raw_slo:
        slo = SLOSpec.model_validate(raw_slo)
    else:
        slo = SLOSpec(
            slo_id=payload.get("slo_id", "slo-ui-live-01"),
            constraints=[
                SLOConstraint(
                    metric_name="ttft_ms",
                    statistic="p95",
                    threshold=float(payload.get("p95_ttft_threshold", 2500.0)),
                    unit="ms",
                    operator="<=",
                ),
                SLOConstraint(
                    metric_name="error_rate",
                    statistic="mean",
                    threshold=float(payload.get("max_error_rate", 0.05)),
                    unit="fraction",
                    operator="<=",
                ),
            ],
            min_sample_count=int(payload.get("min_sample_count", 3)),
        )

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    experiment_id = payload.get("experiment_id", f"exp-{uuid.uuid4().hex[:8]}")
    cand_id = payload.get("candidate_id", f"cand-{adapter.runtime_name}-01")

    candidate_config = CandidateConfig(
        candidate_id=cand_id,
        model_name=adapter.model_name,
        runtime_name=adapter.runtime_name,
        requested_settings=payload.get("requested_settings", {}),
        effective_settings={},
        parameter_status={},
        environment_fingerprint={},
    )

    sse_queue = SSEEventQueue()
    with RUNS_LOCK:
        ACTIVE_RUNS[run_id] = {
            "run_id": run_id,
            "experiment_id": experiment_id,
            "candidate_id": cand_id,
            "execution_status": ExecutionStatus.RUNNING.value,
            "is_completed": False,
            "is_feasible": False,
            "metric_set": None,
            "feasibility_result": None,
            "raw_measurements_count": 0,
            "artifact_paths": {},
            "error": None,
        }
        ACTIVE_QUEUES[run_id] = sse_queue

    thread = threading.Thread(
        target=_execute_run_worker,
        args=(
            run_id,
            experiment_id,
            candidate_config,
            workload,
            slo,
            adapter_name,
            artifacts_root,
            sse_queue,
        ),
        daemon=True,
    )
    thread.start()

    return {
        "run_id": run_id,
        "experiment_id": experiment_id,
        "candidate_id": cand_id,
        "status": ExecutionStatus.RUNNING.value,
        "message": f"Run {run_id} started against {adapter.runtime_name} ({adapter.model_name}).",
    }


def get_run_status(run_id: str, artifacts_root: str = "artifacts") -> Dict[str, Any]:
    with RUNS_LOCK:
        if run_id in ACTIVE_RUNS:
            return ACTIVE_RUNS[run_id]

    # Check filesystem
    run_dir = Path(artifacts_root) / "runs" / run_id
    rec_file = run_dir / "run_record.json"
    if rec_file.exists():
        try:
            rec = RunRecord.model_validate_json(rec_file.read_text(encoding="utf-8"))
            metric_set = None
            met_file = run_dir / "metric_set.json"
            if met_file.exists():
                metric_set = json.loads(met_file.read_text(encoding="utf-8"))

            feas_result = None
            feas_file = run_dir / "feasibility_result.json"
            if feas_file.exists():
                feas_result = json.loads(feas_file.read_text(encoding="utf-8"))

            raw_count = 0
            raw_file = run_dir / "measurements.jsonl"
            if raw_file.exists():
                with open(raw_file, "r", encoding="utf-8") as f:
                    raw_count = sum(1 for line in f if line.strip())

            is_feasible = (
                feas_result is not None
                and feas_result.get("overall_verdict") == FeasibilityVerdict.FEASIBLE.value
            )

            return {
                "run_id": run_id,
                "experiment_id": rec.experiment_id,
                "candidate_id": rec.candidate_id,
                "execution_status": rec.execution_status.value,
                "is_completed": rec.execution_status == ExecutionStatus.COMPLETED,
                "is_feasible": is_feasible,
                "metric_set": metric_set,
                "feasibility_result": feas_result,
                "raw_measurements_count": raw_count,
                "artifact_paths": {
                    "run_record": str(rec_file),
                    "metric_set": str(met_file) if met_file.exists() else "",
                    "raw_measurements": str(raw_file) if raw_file.exists() else "",
                },
                "error": (
                    rec.execution_error.get("message")
                    if isinstance(rec.execution_error, dict)
                    else str(rec.execution_error) if rec.execution_error else None
                ),
            }
        except Exception as exc:
            return {"run_id": run_id, "error": f"Failed reading run artifacts: {exc}"}

    return {"run_id": run_id, "error": "Run not found", "execution_status": ExecutionStatus.FAILED.value}


def list_recent_runs(artifacts_root: str = "artifacts", limit: int = 10) -> List[Dict[str, Any]]:
    runs = []
    with RUNS_LOCK:
        for r in ACTIVE_RUNS.values():
            runs.append(r)

    runs_dir = Path(artifacts_root) / "runs"
    if runs_dir.exists():
        for r_dir in sorted(runs_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if r_dir.is_dir() and r_dir.name not in ACTIVE_RUNS:
                status = get_run_status(r_dir.name, artifacts_root=artifacts_root)
                if "error" not in status or status.get("execution_status"):
                    runs.append(status)
            if len(runs) >= limit:
                break
    return runs[:limit]
