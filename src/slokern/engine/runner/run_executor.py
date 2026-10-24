"""
Purpose: Executes a single run: apply config, warm up, measure, derive metrics, evaluate SLO, persist artifacts.
Owner: Rajdeep (Architecture & Verification)
Authority: Aligned with docs/architecture.md Section 3, docs/experiment-methodology.md, docs/decision-policy.md, AGENTS.md Section 1, 3, 5, 7
"""

import asyncio
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Union
import uuid
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.config import CandidateConfig
from slokern.contracts.enums import (
    EvidenceValidity,
    ExecutionStatus,
    FeasibilityVerdict,
)
from slokern.contracts.evidence import RawRequestMeasurement
from slokern.contracts.metrics import MetricSet
from slokern.contracts.run import RunRecord
from slokern.contracts.spec import SLOSpec, WorkloadSpec
from slokern.contracts.verdict import FeasibilityResult
from slokern.contracts.versions import METRIC_VERSION, POLICY_VERSION
from slokern.core.evaluator.evaluate import evaluate_slo
from slokern.core.metrics.aggregate import calculate_metrics
from slokern.engine.loadgen.runner import LoadGeneratorRunner
from slokern.engine.runner.cancel import CancellationToken, RunCancelledError
from slokern.engine.runner.lifecycle import InvalidStateTransitionError, RunLifecycle
from slokern.engine.serving.base import BaseServingAdapter, ConfigurationError, ServingAdapterError


def _now_iso() -> str:
    """Returns current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def sanitize_error_message(message: str) -> str:
    """
    Redacts secrets, bearer tokens, API keys, and private IPs from error messages.
    Conforms to docs/deployment.md Section 4 and AGENTS.md Section 9, 12.
    """
    if not message:
        return ""

    sanitized = str(message)
    # Mask Authorization / Bearer tokens
    sanitized = re.sub(r"(Bearer\s+)[A-Za-z0-9_\-\.]{6,}", r"\g<1>***", sanitized, flags=re.IGNORECASE)
    # Mask key/secret values
    sanitized = re.sub(
        r"((?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.]{6,}(['\"]?)",
        r"\g<1>***\g<2>",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Redact private IPv4 ranges (10.x.x.x, 192.168.x.x, 172.16-31.x.x)
    sanitized = re.sub(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b", "10.x.x.x", sanitized)
    sanitized = re.sub(r"\b192\.168\.\d{1,3}\.\d{1,3}\b", "192.168.x.x", sanitized)
    sanitized = re.sub(r"\b172\.(?:1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}\b", "172.x.x.x", sanitized)

    return sanitized


class RunExecutionError(Exception):
    """Raised when single-run execution encounters an infrastructure or runtime error."""

    def __init__(
        self,
        message: str,
        stage: str,
        error_type: str,
        run_record: Optional[RunRecord] = None,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.error_type = error_type
        self.run_record = run_record


class SingleRunResult(BaseModel):
    """Immutable result structure emitted by SingleRunExecutor."""

    model_config = ConfigDict(extra="forbid")

    run_record: RunRecord = Field(..., description="Run metadata and lifecycle record")
    metric_set: Optional[MetricSet] = Field(None, description="Derived metrics if calculation succeeded")
    feasibility_result: Optional[FeasibilityResult] = Field(
        None, description="Deterministic feasibility verdict against SLOSpec"
    )
    applied_config: Optional[CandidateConfig] = Field(
        None, description="Verified configuration returned by serving runtime read-back"
    )
    raw_measurements_count: int = Field(0, description="Total unaggregated raw measurements recorded")
    artifact_paths: Dict[str, str] = Field(
        default_factory=dict, description="Resolved filesystem paths of persisted artifacts"
    )

    @property
    def run_id(self) -> str:
        """Convenience property for run ID."""
        return self.run_record.run_id

    @property
    def execution_status(self) -> ExecutionStatus:
        """Convenience property for execution lifecycle status."""
        return self.run_record.execution_status

    @property
    def is_completed(self) -> bool:
        """Returns True if run reached successful completion without execution abort."""
        return self.run_record.execution_status == ExecutionStatus.COMPLETED

    @property
    def is_failed(self) -> bool:
        """Returns True if run failed due to execution or infrastructure error."""
        return self.run_record.execution_status == ExecutionStatus.FAILED

    @property
    def is_cancelled(self) -> bool:
        """Returns True if run was cancelled via CancellationToken."""
        return self.run_record.execution_status == ExecutionStatus.CANCELLED

    @property
    def is_feasible(self) -> bool:
        """Returns True if the run completed and all hard constraints in SLOSpec passed."""
        return (
            self.feasibility_result is not None
            and self.feasibility_result.overall_verdict == FeasibilityVerdict.FEASIBLE
        )

    @property
    def raw_artifact_uri(self) -> Optional[str]:
        """Relative URI to raw measurement recordings."""
        return self.run_record.raw_artifact_uri

    def load_raw_measurements(self) -> List[RawRequestMeasurement]:
        """
        Parses and returns raw measurements recorded on disk for this run.
        Returns empty list if raw trace file does not exist.
        """
        raw_path_str = self.artifact_paths.get("raw_measurements")
        if not raw_path_str:
            return []
        raw_path = Path(raw_path_str)
        if not raw_path.exists():
            return []

        measurements: List[RawRequestMeasurement] = []
        with open(raw_path, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped:
                    measurements.append(RawRequestMeasurement.model_validate_json(stripped))
        return measurements


class SingleRunExecutor:
    """
    Orchestrates the single-run benchmark pipeline:
    apply_config -> health_check -> load_generation -> calculate_metrics -> evaluate_slo -> persist_artifacts.

    Guarantees deterministic metric derivation, strict budget/error accountability,
    cooperative cancellation without zombie subprocesses, and auditable disk persistence.
    """

    def __init__(
        self,
        adapter: Optional[BaseServingAdapter] = None,
        artifacts_root: Union[str, Path] = "artifacts",
        isolate_process: bool = True,
        load_generator_runner: Optional[LoadGeneratorRunner] = None,
        metric_version: str = METRIC_VERSION,
        strict_config: bool = True,
    ) -> None:
        self.adapter = adapter
        self.artifacts_root = Path(artifacts_root)
        self.isolate_process = isolate_process
        self.load_generator_runner = load_generator_runner
        self.metric_version = metric_version
        self.strict_config = strict_config

    def _resolve_run_dir(self, experiment_id: str, run_id: str) -> Path:
        """Returns target run artifact directory conforming to repository convention."""
        run_dir = self.artifacts_root / "experiments" / experiment_id / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def _canonical_raw_uri(self, experiment_id: str, run_id: str) -> str:
        """Returns canonical relative URI stored in RunRecord."""
        return f"artifacts/experiments/{experiment_id}/runs/{run_id}/raw_measurements.jsonl"

    def _persist_run_record(self, record: RunRecord, run_dir: Path) -> Path:
        """Persists run_record.json atomically to disk."""
        path = run_dir / "run_record.json"
        path.write_text(record.model_dump_json(indent=2), encoding="utf-8")
        return path

    def execute(
        self,
        candidate_config: CandidateConfig,
        workload: WorkloadSpec,
        slo: SLOSpec,
        experiment_id: str = "exp-default",
        run_id: Optional[str] = None,
        is_verification_run: bool = False,
        adapter: Optional[BaseServingAdapter] = None,
        cancellation_token: Optional[CancellationToken] = None,
        seed: Optional[int] = 42,
        stream: bool = True,
        prompts: Optional[Union[List[str], str]] = None,
        artificial_dispatch_delay_ms: float = 0.0,
        raise_on_failure: bool = False,
    ) -> SingleRunResult:
        """
        Executes a single benchmark run through the full lifecycle.

        Args:
            candidate_config: The serving configuration to evaluate.
            workload: The workload arrival profile to generate.
            slo: Hard SLO constraints to audit against.
            experiment_id: Parent experiment session identifier.
            run_id: Unique identifier for this run. If None, generated automatically.
            is_verification_run: Distinguishes search runs from independent verification reruns.
            adapter: Serving adapter instance to use. Overrides constructor adapter if provided.
            cancellation_token: Optional token for cooperative cancellation.
            seed: Random seed for workload arrival schedule generation.
            stream: Whether to request streaming token chunks.
            prompts: Custom benchmark prompt(s).
            artificial_dispatch_delay_ms: Client-side delay injection for saturation auditing.
            raise_on_failure: If True, raises RunExecutionError / RunCancelledError on failure.

        Returns:
            SingleRunResult containing run record, metrics, feasibility verdict, and artifact paths.
        """
        # 1. Identity & Directory Setup
        resolved_run_id = run_id or f"run-{uuid.uuid4().hex[:12]}"
        run_dir = self._resolve_run_dir(experiment_id, resolved_run_id)
        raw_path = run_dir / "raw_measurements.jsonl"
        canonical_raw_uri = self._canonical_raw_uri(experiment_id, resolved_run_id)

        lifecycle = RunLifecycle(ExecutionStatus.PENDING)
        record = RunRecord(
            run_id=resolved_run_id,
            experiment_id=experiment_id,
            candidate_id=candidate_config.candidate_id,
            is_verification_run=is_verification_run,
            execution_status=ExecutionStatus.PENDING,
            started_at=None,
            completed_at=None,
            raw_artifact_uri=None,
            execution_error=None,
        )

        artifact_paths: Dict[str, str] = {}
        applied_config: Optional[CandidateConfig] = None
        metrics: Optional[MetricSet] = None
        feasibility: Optional[FeasibilityResult] = None
        raw_count: int = 0

        effective_adapter = adapter or self.adapter

        # Check early cancellation
        if cancellation_token and cancellation_token.is_cancelled:
            lifecycle.transition_to(ExecutionStatus.CANCELLED)
            record.execution_status = ExecutionStatus.CANCELLED
            record.completed_at = _now_iso()
            record_path = self._persist_run_record(record, run_dir)
            artifact_paths["run_record"] = str(record_path.resolve())
            res = SingleRunResult(
                run_record=record,
                applied_config=None,
                metric_set=None,
                feasibility_result=None,
                raw_measurements_count=0,
                artifact_paths=artifact_paths,
            )
            if raise_on_failure:
                raise RunCancelledError("Run was cancelled prior to initialization.")
            return res

        # 2. Input Validation
        try:
            if effective_adapter is None:
                raise ValueError("No serving adapter provided. Set adapter in constructor or execute().")
            if workload.warmup_duration_s < 0 or workload.measurement_duration_s < 0:
                raise ValueError("Workload durations must be non-negative.")
            if (workload.warmup_duration_s + workload.measurement_duration_s) <= 0:
                raise ValueError("Total workload duration must be strictly positive.")
            if workload.concurrency_limit < 1:
                raise ValueError("Workload concurrency_limit must be >= 1.")
            if slo.min_sample_count < 1:
                raise ValueError("SLO min_sample_count must be >= 1.")
        except Exception as exc:
            lifecycle.transition_to(ExecutionStatus.FAILED)
            record.execution_status = ExecutionStatus.FAILED
            record.execution_error = {
                "stage": "validation",
                "error_type": type(exc).__name__,
                "message": sanitize_error_message(str(exc)),
            }
            record.completed_at = _now_iso()
            record_path = self._persist_run_record(record, run_dir)
            artifact_paths["run_record"] = str(record_path.resolve())
            res = SingleRunResult(
                run_record=record,
                applied_config=None,
                metric_set=None,
                feasibility_result=None,
                raw_measurements_count=0,
                artifact_paths=artifact_paths,
            )
            if raise_on_failure:
                raise RunExecutionError(
                    str(exc), stage="validation", error_type=type(exc).__name__, run_record=record
                ) from exc
            return res

        # 3. Transition to RUNNING
        lifecycle.transition_to(ExecutionStatus.RUNNING)
        record.execution_status = ExecutionStatus.RUNNING
        record.started_at = _now_iso()
        try:
            record_path = self._persist_run_record(record, run_dir)
            artifact_paths["run_record"] = str(record_path.resolve())
        except Exception as exc:
            # If disk write fails immediately, record failure
            lifecycle.transition_to(ExecutionStatus.FAILED)
            record.execution_status = ExecutionStatus.FAILED
            record.execution_error = {
                "stage": "persist_artifacts",
                "error_type": type(exc).__name__,
                "message": sanitize_error_message(f"Failed to initialize run record on disk: {exc}"),
            }
            record.completed_at = _now_iso()
            if raise_on_failure:
                raise RunExecutionError(
                    str(exc), stage="persist_artifacts", error_type=type(exc).__name__, run_record=record
                ) from exc
            return SingleRunResult(
                run_record=record,
                applied_config=None,
                metric_set=None,
                feasibility_result=None,
                raw_measurements_count=0,
                artifact_paths={},
            )

        # 4. Apply Configuration (Read-back verification)
        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise RunCancelledError("Cancelled before config application.")
            applied_config = effective_adapter.apply_config(candidate_config, strict=self.strict_config)
            applied_path = run_dir / "applied_config.json"
            applied_path.write_text(applied_config.model_dump_json(indent=2), encoding="utf-8")
            artifact_paths["applied_config"] = str(applied_path.resolve())
        except (RunCancelledError, asyncio.CancelledError):
            return self._handle_cancellation(
                lifecycle, record, run_dir, artifact_paths, applied_config, raise_on_failure
            )
        except Exception as exc:
            return self._handle_failure(
                lifecycle,
                record,
                run_dir,
                artifact_paths,
                applied_config,
                stage="apply_config",
                exc=exc,
                raise_on_failure=raise_on_failure,
            )

        # 5. Health Check
        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise RunCancelledError("Cancelled before health check.")
            is_healthy = effective_adapter.health_check()
            if not is_healthy:
                raise ServingAdapterError(
                    f"Serving adapter '{effective_adapter.runtime_name}' failed health check probe."
                )
        except (RunCancelledError, asyncio.CancelledError):
            return self._handle_cancellation(
                lifecycle, record, run_dir, artifact_paths, applied_config, raise_on_failure
            )
        except Exception as exc:
            return self._handle_failure(
                lifecycle,
                record,
                run_dir,
                artifact_paths,
                applied_config,
                stage="health_check",
                exc=exc,
                raise_on_failure=raise_on_failure,
            )

        # 6. Load Generation
        runner = self.load_generator_runner or LoadGeneratorRunner(isolate_process=self.isolate_process)
        if cancellation_token:
            cancellation_token.register_callback(runner.cancel)

        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise RunCancelledError("Cancelled before load generation dispatch.")

            loadgen_result = runner.run(
                workload=workload,
                adapter=effective_adapter,
                output_path=raw_path,
                run_id=resolved_run_id,
                seed=seed,
                stream=stream,
                prompts=prompts,
                artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
            )

            if raw_path.exists() and raw_path.stat().st_size > 0:
                record.raw_artifact_uri = canonical_raw_uri
                artifact_paths["raw_measurements"] = str(raw_path.resolve())

            if loadgen_result.error:
                raise RuntimeError(f"Load generator error: {loadgen_result.error}")

        except (RunCancelledError, asyncio.CancelledError):
            if raw_path.exists() and raw_path.stat().st_size > 0:
                record.raw_artifact_uri = canonical_raw_uri
                artifact_paths["raw_measurements"] = str(raw_path.resolve())
            return self._handle_cancellation(
                lifecycle, record, run_dir, artifact_paths, applied_config, raise_on_failure
            )
        except Exception as exc:
            if raw_path.exists() and raw_path.stat().st_size > 0:
                record.raw_artifact_uri = canonical_raw_uri
                artifact_paths["raw_measurements"] = str(raw_path.resolve())

            if cancellation_token and cancellation_token.is_cancelled:
                return self._handle_cancellation(
                    lifecycle, record, run_dir, artifact_paths, applied_config, raise_on_failure
                )
            return self._handle_failure(
                lifecycle,
                record,
                run_dir,
                artifact_paths,
                applied_config,
                stage="load_generation",
                exc=exc,
                raise_on_failure=raise_on_failure,
            )

        # 7. Consume Raw Evidence & Count Measurements
        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise RunCancelledError("Cancelled before evidence calculation.")

            has_trace = raw_path.exists() and raw_path.stat().st_size > 0
            if has_trace:
                with open(raw_path, "r", encoding="utf-8") as f:
                    raw_count = sum(1 for line in f if line.strip())

            trace_source: Union[Path, List[Any]] = raw_path if has_trace else []

            metrics = calculate_metrics(
                records=trace_source,
                run_id=resolved_run_id,
                target_offered_rate=float(workload.target_offered_rate),
                measurement_duration_s=float(workload.measurement_duration_s),
                metric_version=self.metric_version,
                metadata={
                    "candidate_id": candidate_config.candidate_id,
                    "experiment_id": experiment_id,
                    "model_name": candidate_config.model_name,
                    "runtime_name": candidate_config.runtime_name or effective_adapter.runtime_name,
                },
            )

        except (RunCancelledError, asyncio.CancelledError):
            return self._handle_cancellation(
                lifecycle, record, run_dir, artifact_paths, applied_config, raise_on_failure
            )
        except Exception as exc:
            # Under decision policy: malformed or corrupted evidence produces an INCONCLUSIVE FeasibilityResult
            # with EvidenceValidity.INVALID, and the run is marked FAILED because metrics could not be derived.
            feasibility = FeasibilityResult(
                policy_version=POLICY_VERSION,
                run_id=resolved_run_id,
                overall_verdict=FeasibilityVerdict.INCONCLUSIVE,
                constraint_evaluations=[],
                validity_status=EvidenceValidity.INVALID,
                audit_notes=sanitize_error_message(f"Metrics calculation failed: {exc}"),
            )
            try:
                feas_path = run_dir / "feasibility.json"
                feas_path.write_text(feasibility.model_dump_json(indent=2), encoding="utf-8")
                artifact_paths["feasibility"] = str(feas_path.resolve())
            except Exception:
                pass

            return self._handle_failure(
                lifecycle,
                record,
                run_dir,
                artifact_paths,
                applied_config,
                stage="calculate_metrics",
                exc=exc,
                feasibility=feasibility,
                raise_on_failure=raise_on_failure,
            )

        # 8. Evaluate Hard SLO Constraints
        try:
            if cancellation_token and cancellation_token.is_cancelled:
                raise RunCancelledError("Cancelled before SLO feasibility evaluation.")

            feasibility = evaluate_slo(metric_set=metrics, slo_spec=slo)

        except (RunCancelledError, asyncio.CancelledError):
            return self._handle_cancellation(
                lifecycle, record, run_dir, artifact_paths, applied_config, raise_on_failure
            )
        except Exception as exc:
            return self._handle_failure(
                lifecycle,
                record,
                run_dir,
                artifact_paths,
                applied_config,
                stage="evaluate_slo",
                exc=exc,
                metrics=metrics,
                raise_on_failure=raise_on_failure,
            )

        # 9. Persist Remaining Artifacts & Transition to COMPLETED
        try:
            metrics_path = run_dir / "metrics.json"
            metrics_path.write_text(metrics.model_dump_json(indent=2), encoding="utf-8")
            artifact_paths["metrics"] = str(metrics_path.resolve())

            feasibility_path = run_dir / "feasibility.json"
            feasibility_path.write_text(feasibility.model_dump_json(indent=2), encoding="utf-8")
            artifact_paths["feasibility"] = str(feasibility_path.resolve())

            lifecycle.transition_to(ExecutionStatus.COMPLETED)
            record.execution_status = ExecutionStatus.COMPLETED
            record.completed_at = _now_iso()

            record_path = self._persist_run_record(record, run_dir)
            artifact_paths["run_record"] = str(record_path.resolve())

        except Exception as exc:
            # If writing completed artifacts fails, run must not claim COMPLETED status
            return self._handle_failure(
                lifecycle,
                record,
                run_dir,
                artifact_paths,
                applied_config,
                stage="persist_artifacts",
                exc=exc,
                metrics=metrics,
                feasibility=feasibility,
                raise_on_failure=raise_on_failure,
            )

        return SingleRunResult(
            run_record=record,
            metric_set=metrics,
            feasibility_result=feasibility,
            applied_config=applied_config,
            raw_measurements_count=raw_count,
            artifact_paths=artifact_paths,
        )

    def _handle_cancellation(
        self,
        lifecycle: RunLifecycle,
        record: RunRecord,
        run_dir: Path,
        artifact_paths: Dict[str, str],
        applied_config: Optional[CandidateConfig],
        raise_on_failure: bool,
    ) -> SingleRunResult:
        """Handles cancellation transitions and records state without marking COMPLETED."""
        if lifecycle.can_transition_to(ExecutionStatus.CANCELLED):
            lifecycle.transition_to(ExecutionStatus.CANCELLED)
        record.execution_status = ExecutionStatus.CANCELLED
        record.completed_at = _now_iso()

        try:
            record_path = self._persist_run_record(record, run_dir)
            artifact_paths["run_record"] = str(record_path.resolve())
        except Exception:
            pass

        res = SingleRunResult(
            run_record=record,
            applied_config=applied_config,
            metric_set=None,
            feasibility_result=None,
            raw_measurements_count=0,
            artifact_paths=artifact_paths,
        )
        if raise_on_failure:
            raise RunCancelledError("Execution was cancelled.")
        return res

    def _handle_failure(
        self,
        lifecycle: RunLifecycle,
        record: RunRecord,
        run_dir: Path,
        artifact_paths: Dict[str, str],
        applied_config: Optional[CandidateConfig],
        stage: str,
        exc: Exception,
        metrics: Optional[MetricSet] = None,
        feasibility: Optional[FeasibilityResult] = None,
        raise_on_failure: bool = False,
    ) -> SingleRunResult:
        """Handles failure transitions, logs sanitized error details, and saves partial artifacts."""
        if lifecycle.can_transition_to(ExecutionStatus.FAILED):
            lifecycle.transition_to(ExecutionStatus.FAILED)
        record.execution_status = ExecutionStatus.FAILED
        record.execution_error = {
            "stage": stage,
            "error_type": type(exc).__name__,
            "message": sanitize_error_message(str(exc)),
        }
        record.completed_at = _now_iso()

        try:
            record_path = self._persist_run_record(record, run_dir)
            artifact_paths["run_record"] = str(record_path.resolve())
        except Exception:
            pass

        res = SingleRunResult(
            run_record=record,
            applied_config=applied_config,
            metric_set=metrics,
            feasibility_result=feasibility,
            raw_measurements_count=0,
            artifact_paths=artifact_paths,
        )
        if raise_on_failure:
            raise RunExecutionError(
                str(exc), stage=stage, error_type=type(exc).__name__, run_record=record
            ) from exc
        return res
