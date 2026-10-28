"""
Purpose: Run lifecycle orchestration, async execution, status query and SSE queuing.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 3, 5, 7 and DEC-0014
"""

import json
import re
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

        def on_progress(completed: int, total: int, current_ttft: Optional[float] = None) -> None:
            sse_queue.emit("progress", {
                "run_id": run_id,
                "completed_requests": completed,
                "total_requests": total,
                "current_ttft_ms": current_ttft,
            })
            with RUNS_LOCK:
                if run_id in ACTIVE_RUNS:
                    ACTIVE_RUNS[run_id]["raw_measurements_count"] = completed

        # Run benchmark
        run_res = executor.execute(
            candidate_config=candidate_config,
            workload=workload,
            slo=slo,
            experiment_id=experiment_id,
            run_id=run_id,
            progress_callback=on_progress,
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
            "applied_config": run_res.applied_config.model_dump() if run_res.applied_config else None,
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
            "workload": workload.model_dump(),
            "slo": slo.model_dump(),
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

    if not re.match(r"^[a-zA-Z0-9_\-]+$", run_id):
        return {"run_id": run_id, "error": f"Invalid run_id format: {run_id}"}

    # Check filesystem: check both direct runs/ and SingleRunExecutor experiments/*/runs/
    run_dir = Path(artifacts_root) / "runs" / run_id
    if not (run_dir / "run_record.json").exists():
        matches = list(Path(artifacts_root).glob(f"experiments/*/runs/{run_id}"))
        if matches and (matches[0] / "run_record.json").exists():
            run_dir = matches[0]

    rec_file = run_dir / "run_record.json"
    if rec_file.exists():
        try:
            rec = RunRecord.model_validate_json(rec_file.read_text(encoding="utf-8"))

            metric_set = None
            met_file_resolved = ""
            for met_name in ("metrics.json", "metric_set.json"):
                mf = run_dir / met_name
                if mf.exists():
                    try:
                        metric_set = json.loads(mf.read_text(encoding="utf-8"))
                        met_file_resolved = str(mf)
                        break
                    except Exception:
                        pass

            feas_result = None
            for feas_name in ("feasibility.json", "feasibility_result.json"):
                ff = run_dir / feas_name
                if ff.exists():
                    try:
                        feas_result = json.loads(ff.read_text(encoding="utf-8"))
                        break
                    except Exception:
                        pass

            raw_count = 0
            raw_file_resolved = ""
            for raw_name in ("raw_measurements.jsonl", "measurements.jsonl"):
                rf = run_dir / raw_name
                if rf.exists():
                    raw_file_resolved = str(rf)
                    try:
                        with open(rf, "r", encoding="utf-8") as f:
                            raw_count = sum(1 for line in f if line.strip())
                        break
                    except Exception:
                        pass

            is_feasible = (
                feas_result is not None
                and feas_result.get("overall_verdict") == FeasibilityVerdict.FEASIBLE.value
            )

            applied_cfg = None
            ac_file = run_dir / "applied_config.json"
            if ac_file.exists():
                try:
                    applied_cfg = json.loads(ac_file.read_text(encoding="utf-8"))
                except Exception:
                    pass

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
                "applied_config": applied_cfg,
                "artifact_paths": {
                    "run_record": str(rec_file),
                    "metric_set": met_file_resolved,
                    "raw_measurements": raw_file_resolved,
                },
                "error": (
                    rec.execution_error.get("message")
                    if isinstance(rec.execution_error, dict)
                    else str(rec.execution_error) if rec.execution_error else None
                ),
            }
        except Exception as exc:
            return {"run_id": run_id, "error": f"Failed reading run artifacts: {exc}"}

    return {"run_id": run_id, "error": "Run not found"}


def list_recent_runs(artifacts_root: str = "artifacts", limit: int = 10) -> List[Dict[str, Any]]:
    runs = []
    seen_ids = set()
    with RUNS_LOCK:
        for r in ACTIVE_RUNS.values():
            runs.append(r)
            seen_ids.add(r.get("run_id"))

    candidate_dirs: List[Path] = []
    runs_dir = Path(artifacts_root) / "runs"
    if runs_dir.exists():
        for r_dir in runs_dir.iterdir():
            if r_dir.is_dir() and r_dir.name not in seen_ids:
                candidate_dirs.append(r_dir)

    exp_runs = Path(artifacts_root).glob("experiments/*/runs/*")
    for r_dir in exp_runs:
        if r_dir.is_dir() and r_dir.name not in seen_ids:
            candidate_dirs.append(r_dir)

    candidate_dirs.sort(key=lambda p: p.stat().st_mtime, reverse=True)

    for r_dir in candidate_dirs:
        if r_dir.name not in seen_ids:
            seen_ids.add(r_dir.name)
            status = get_run_status(r_dir.name, artifacts_root=artifacts_root)
            if status.get("error") != "Run not found":
                runs.append(status)
        if len(runs) >= limit:
            break
    return runs[:limit]
