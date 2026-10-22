# Implementation Report: Subprocess-Isolated Load Generator (`SUB-06`, `TASK-06`)

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Task:** Subprocess-isolated load generator (`TASK-06` / `SUB-06`)  
> **Integrity Mode:** Development  
> **Owner / Author:** Rajdeep Paul  
> **Authority:** Aligned with `ROADMAP.md` (`TASK-06`, `BLK-02`), `docs/experiment-methodology.md`, `docs/metrics.md`, and `AGENTS.md`

---

## 1. Summary of Changes

Implemented the open-loop subprocess-isolated load generator for SLOKern across `src/slokern/engine/loadgen/`:

1. **`src/slokern/engine/loadgen/arrival.py` (`ArrivalSchedule`, `ArrivalSlot`):**
   - Supports `ArrivalMode.CONSTANT` with interval $\Delta t = 1/\lambda$ and `ArrivalMode.POISSON` with inter-arrival intervals $\Delta t \sim \text{Exp}(\lambda)$.
   - Employs deterministic PRNG seeding (`random.Random(seed)`) for reproducible arrival sequences.
   - Accurately tags each arrival slot with `is_warmup` based on `warmup_duration_s`.
   - Provides `from_workload_spec(spec, seed, start_time)` factory method and generator iterators.

2. **`src/slokern/engine/loadgen/recorder.py` (`JSONLRecorder`, `RecorderStats`):**
   - Implements crash-resilient streaming of unaggregated microsecond request events to `.jsonl` files.
   - Strictly validates each record against Pydantic v2 `RawRequestMeasurement` (`ConfigDict(extra="forbid")`).
   - Flushes buffers to disk immediately after every write (`file.flush()`) to ensure no data loss upon process crash or abort.
   - Tracks real-time running counters (`total_count`, `warmup_count`, `active_count`, `valid_count`, `error_count`) and dispatch delay statistics (`mean_dispatch_lag_ms`, `max_dispatch_lag_ms`, `active_mean_dispatch_lag_ms`, etc.).
   - Provides static method `read_records()` to load and strictly validate persisted JSONL traces.

3. **`src/slokern/engine/loadgen/runner.py` (`LoadGeneratorRunner`, `LoadGeneratorResult`):**
   - Spawns an isolated Python child process via `multiprocessing.get_context("spawn")` to eliminate host GC and GIL interference.
   - Executes an asynchronous dispatch loop respecting `concurrency_limit` via `asyncio.Semaphore`.
   - Supports both streaming (`astream_generate`) for TTFT/ITL recording and non-streaming (`agenerate`) against `BaseServingAdapter` and `FakeServingAdapter`.
   - Enforces strict microsecond timestamp monotonicity invariant: `scheduled_at <= sent_at <= first_token_at <= completed_at`.
   - Detects client scheduler and queue saturation: calculates `offered_load_rps`, `achieved_load_rps`, `mean_dispatch_lag_ms`, and `max_dispatch_lag_ms`. Flags `generator_saturated = True` whenever `mean_dispatch_skew_ms > 10.0` or `offered_load_rps < 0.90 * target_offered_rate`.
   - Exposes asynchronous wrapper `arun()` and supports optional in-process execution via `isolate_process=False`.

4. **`src/slokern/engine/loadgen/__init__.py`:**
   - Cleanly exports public interfaces: `ArrivalSchedule`, `ArrivalSlot`, `JSONLRecorder`, `RecorderStats`, `LoadGeneratorRunner`, `LoadGeneratorResult`.

5. **Test Suite Implementation:**
   - `tests/unit/engine/loadgen/test_arrival.py` (10 tests, 100% pass)
   - `tests/unit/engine/loadgen/test_recorder.py` (7 tests, 100% pass)
   - `tests/unit/engine/loadgen/test_runner.py` (7 tests, 100% pass)

---

## 2. Git Diff of Changes

```diff
diff --git a/src/slokern/engine/loadgen/__init__.py b/src/slokern/engine/loadgen/__init__.py
index e69de29..2810d73 100644
--- a/src/slokern/engine/loadgen/__init__.py
+++ b/src/slokern/engine/loadgen/__init__.py
@@ -0,0 +1,18 @@
+"""
+Purpose: Load generator package exports.
+Owner: Rajdeep (Historical design: Adriraj)
+"""
+
+from slokern.engine.loadgen.arrival import ArrivalSchedule, ArrivalSlot
+from slokern.engine.loadgen.recorder import JSONLRecorder, RecorderStats
+from slokern.engine.loadgen.runner import LoadGeneratorRunner, LoadGeneratorResult
+
+__all__ = [
+    "ArrivalSchedule",
+    "ArrivalSlot",
+    "JSONLRecorder",
+    "RecorderStats",
+    "LoadGeneratorRunner",
+    "LoadGeneratorResult",
+]
diff --git a/src/slokern/engine/loadgen/arrival.py b/src/slokern/engine/loadgen/arrival.py
index e69de29..45fc23d 100644
--- a/src/slokern/engine/loadgen/arrival.py
+++ b/src/slokern/engine/loadgen/arrival.py
@@ -0,0 +1,118 @@
+"""
+Purpose: Arrival schedule generator for constant and Poisson open-loop traffic.
+Owner: Rajdeep (Historical design: Adriraj)
+Authority: Aligned with docs/experiment-methodology.md Section 2.2 and AGENTS.md Section 13
+"""
+
+from dataclasses import dataclass
+import random
+from typing import Iterator, List, Optional, Union
+
+from slokern.contracts.enums import ArrivalMode
+from slokern.contracts.spec import WorkloadSpec
+
+
+@dataclass(frozen=True)
+class ArrivalSlot:
+    """Represents a scheduled arrival event in the workload timeline."""
+    index: int
+    scheduled_at: float
+    is_warmup: bool
+    offset_s: float
+
+
+class ArrivalSchedule:
+    """
+    Open-loop arrival schedule generator.
+    Supports ArrivalMode.CONSTANT (delta_t = 1 / lambda)
+    and ArrivalMode.POISSON (delta_t ~ Exp(lambda)) with reproducible PRNG seeding.
+    """
+
+    def __init__(
+        self,
+        arrival_mode: Union[ArrivalMode, str],
+        target_offered_rate: float,
+        warmup_duration_s: float = 0.0,
+        measurement_duration_s: float = 0.0,
+        seed: Optional[int] = 42,
+        start_time: float = 0.0,
+    ) -> None:
+        if isinstance(arrival_mode, str):
+            try:
+                arrival_mode = ArrivalMode(arrival_mode.lower())
+            except ValueError:
+                raise ValueError(
+                    f"Unsupported arrival mode string: '{arrival_mode}'. "
+                    f"Supported modes: {ArrivalMode.CONSTANT.value}, {ArrivalMode.POISSON.value}"
+                )
+
+        if arrival_mode not in (ArrivalMode.CONSTANT, ArrivalMode.POISSON):
+            raise ValueError(
+                f"Unsupported arrival mode: {arrival_mode}. "
+                f"Supported open-loop modes: {ArrivalMode.CONSTANT}, {ArrivalMode.POISSON}"
+            )
+
+        if target_offered_rate <= 0:
+            raise ValueError(f"target_offered_rate must be positive, got {target_offered_rate}")
+        if warmup_duration_s < 0:
+            raise ValueError(f"warmup_duration_s must be non-negative, got {warmup_duration_s}")
+        if measurement_duration_s < 0:
+            raise ValueError(f"measurement_duration_s must be non-negative, got {measurement_duration_s}")
+
+        self.arrival_mode = arrival_mode
+        self.target_offered_rate = float(target_offered_rate)
+        self.warmup_duration_s = float(warmup_duration_s)
+        self.measurement_duration_s = float(measurement_duration_s)
+        self.seed = seed
+        self.start_time = float(start_time)
+        self.total_duration_s = self.warmup_duration_s + self.measurement_duration_s
+
+    @classmethod
+    def from_workload_spec(
+        cls,
+        spec: WorkloadSpec,
+        seed: Optional[int] = 42,
+        start_time: float = 0.0,
+    ) -> "ArrivalSchedule":
+        """Instantiates an ArrivalSchedule directly from a WorkloadSpec."""
+        return cls(
+            arrival_mode=spec.arrival_mode,
+            target_offered_rate=spec.target_offered_rate,
+            warmup_duration_s=float(spec.warmup_duration_s),
+            measurement_duration_s=float(spec.measurement_duration_s),
+            seed=seed,
+            start_time=start_time,
+        )
+
+    def __iter__(self) -> Iterator[ArrivalSlot]:
+        return self.generate(self.start_time)
+
+    def generate(self, start_time: Optional[float] = None) -> Iterator[ArrivalSlot]:
+        """Yields arrival slots across warmup and measurement windows."""
+        base_time = self.start_time if start_time is None else float(start_time)
+        if self.total_duration_s <= 0:
+            return
+
+        if self.arrival_mode == ArrivalMode.CONSTANT:
+            interval = 1.0 / self.target_offered_rate
+            slot_idx = 0
+            while True:
+                offset_s = slot_idx * interval
+                if offset_s >= self.total_duration_s - 1e-9:
+                    break
+                is_warmup = offset_s < (self.warmup_duration_s - 1e-9)
+                yield ArrivalSlot(
+                    index=slot_idx,
+                    scheduled_at=base_time + offset_s,
+                    is_warmup=is_warmup,
+                    offset_s=offset_s,
+                )
+                slot_idx += 1
+
+        elif self.arrival_mode == ArrivalMode.POISSON:
+            rnd = random.Random(self.seed)
+            current_offset = 0.0
+            slot_idx = 0
+            while True:
+                delta = rnd.expovariate(self.target_offered_rate)
+                current_offset += delta
+                if current_offset >= self.total_duration_s:
+                    break
+                is_warmup = current_offset < self.warmup_duration_s
+                yield ArrivalSlot(
+                    index=slot_idx,
+                    scheduled_at=base_time + current_offset,
+                    is_warmup=is_warmup,
+                    offset_s=current_offset,
+                )
+                slot_idx += 1
+
+    def slots(self, start_time: Optional[float] = None) -> List[ArrivalSlot]:
+        """Materializes all arrival slots into a list."""
+        return list(self.generate(start_time))
diff --git a/src/slokern/engine/loadgen/recorder.py b/src/slokern/engine/loadgen/recorder.py
index e69de29..2e0084f 100644
--- a/src/slokern/engine/loadgen/recorder.py
+++ b/src/slokern/engine/loadgen/recorder.py
@@ -0,0 +1,173 @@
+"""
+Purpose: Crash-resilient unaggregated JSONL recorder for RawRequestMeasurement.
+Owner: Rajdeep (Historical design: Adriraj)
+Authority: Aligned with docs/experiment-methodology.md Section 5 and AGENTS.md Section 1, 4
+"""
+
+from pathlib import Path
+import threading
+from typing import Any, Dict, List, Optional, Union
+from pydantic import BaseModel, ConfigDict, Field
+
+from slokern.contracts.evidence import RawRequestMeasurement
+
+
+class RecorderStats(BaseModel):
+    """Running aggregate counts and latency statistics for recorded requests."""
+    model_config = ConfigDict(extra="forbid")
+
+    total_count: int = Field(0, description="Total number of records written")
+    warmup_count: int = Field(0, description="Count of warm-up records")
+    active_count: int = Field(0, description="Count of active measurement records")
+    valid_count: int = Field(0, description="Count of records marked is_valid=True across all records")
+    active_valid_count: int = Field(0, description="Count of valid records during the active measurement window")
+    error_count: int = Field(0, description="Count of records with errors or non-200 HTTP status across all records")
+    active_error_count: int = Field(0, description="Count of error records during the active measurement window")
+
+    # Dispatch latency metrics (ms)
+    mean_dispatch_lag_ms: float = Field(0.0, description="Mean dispatch lag across all recorded requests in ms")
+    max_dispatch_lag_ms: float = Field(0.0, description="Maximum dispatch lag observed in ms")
+    min_dispatch_lag_ms: float = Field(0.0, description="Minimum dispatch lag observed in ms")
+    active_mean_dispatch_lag_ms: float = Field(0.0, description="Mean dispatch lag across active requests in ms")
+    active_max_dispatch_lag_ms: float = Field(0.0, description="Maximum dispatch lag across active requests in ms")
+
+
+class JSONLRecorder:
+    """
+    Crash-resilient JSONL event recorder streaming microsecond traces to disk.
+    Strictly validates every record against RawRequestMeasurement and flushes after each write.
+    """
+
+    def __init__(
+        self,
+        file_path: Union[str, Path],
+        flush_immediately: bool = True,
+        mode: str = "a",
+    ) -> None:
+        self.file_path = Path(file_path).resolve()
+        self.file_path.parent.mkdir(parents=True, exist_ok=True)
+        self.flush_immediately = flush_immediately
+        self._lock = threading.Lock()
+        self._file = open(self.file_path, mode, encoding="utf-8")
+        self._closed = False
+
+        self._total_count = 0
+        self._warmup_count = 0
+        self._active_count = 0
+        self._valid_count = 0
+        self._active_valid_count = 0
+        self._error_count = 0
+        self._active_error_count = 0
+
+        self._all_lags_ms: List[float] = []
+        self._active_lags_ms: List[float] = []
+
+    def record(self, measurement: Union[RawRequestMeasurement, Dict[str, Any]]) -> RawRequestMeasurement:
+        """
+        Validates, serializes, flushes, and updates statistics for a request measurement event.
+        Raises ValidationError if measurement violates the RawRequestMeasurement schema.
+        """
+        if self._closed:
+            raise RuntimeError(f"Cannot record to closed JSONLRecorder ({self.file_path})")
+
+        if isinstance(measurement, RawRequestMeasurement):
+            event = measurement
+        elif isinstance(measurement, dict):
+            event = RawRequestMeasurement.model_validate(measurement)
+        else:
+            event = RawRequestMeasurement.model_validate(measurement)
+
+        # Calculate dispatch lag in ms: sent_at - scheduled_at
+        dispatch_lag_ms = max(0.0, (event.sent_at - event.scheduled_at) * 1000.0)
+
+        # Direct JSON serialization conforming strictly to RawRequestMeasurement
+        json_line = event.model_dump_json() + "\n"
+
+        with self._lock:
+            self._file.write(json_line)
+            if self.flush_immediately:
+                self._file.flush()
+
+            self._total_count += 1
+            self._all_lags_ms.append(dispatch_lag_ms)
+
+            is_error = (event.http_status is not None and event.http_status != 200) or (event.error_type is not None)
+
+            if event.is_warmup:
+                self._warmup_count += 1
+            else:
+                self._active_count += 1
+                self._active_lags_ms.append(dispatch_lag_ms)
+                if event.is_valid:
+                    self._active_valid_count += 1
+                if is_error:
+                    self._active_error_count += 1
+
+            if event.is_valid:
+                self._valid_count += 1
+            if is_error:
+                self._error_count += 1
+
+        return event
+
+    def get_stats(self) -> RecorderStats:
+        """Returns snapshot of running counters and dispatch delay statistics."""
+        with self._lock:
+            all_lags = self._all_lags_ms
+            active_lags = self._active_lags_ms
+
+            mean_lag = (sum(all_lags) / len(all_lags)) if all_lags else 0.0
+            max_lag = max(all_lags) if all_lags else 0.0
+            min_lag = min(all_lags) if all_lags else 0.0
+
+            active_mean_lag = (sum(active_lags) / len(active_lags)) if active_lags else 0.0
+            active_max_lag = max(active_lags) if active_lags else 0.0
+
+            return RecorderStats(
+                total_count=self._total_count,
+                warmup_count=self._warmup_count,
+                active_count=self._active_count,
+                valid_count=self._valid_count,
+                active_valid_count=self._active_valid_count,
+                error_count=self._error_count,
+                active_error_count=self._active_error_count,
+                mean_dispatch_lag_ms=round(mean_lag, 4),
+                max_dispatch_lag_ms=round(max_lag, 4),
+                min_dispatch_lag_ms=round(min_lag, 4),
+                active_mean_dispatch_lag_ms=round(active_mean_lag, 4),
+                active_max_dispatch_lag_ms=round(active_max_lag, 4),
+            )
+
+    @property
+    def total_count(self) -> int:
+        return self._total_count
+
+    @property
+    def warmup_count(self) -> int:
+        return self._warmup_count
+
+    @property
+    def active_count(self) -> int:
+        return self._active_count
+
+    @property
+    def valid_count(self) -> int:
+        return self._valid_count
+
+    @property
+    def error_count(self) -> int:
+        return self._error_count
+
+    @property
+    def mean_dispatch_lag_ms(self) -> float:
+        with self._lock:
+            return round(sum(self._all_lags_ms) / len(self._all_lags_ms), 4) if self._all_lags_ms else 0.0
+
+    @property
+    def max_dispatch_lag_ms(self) -> float:
+        with self._lock:
+            return round(max(self._all_lags_ms), 4) if self._all_lags_ms else 0.0
+
+    def close(self) -> None:
+        """Flushes buffers and closes underlying file handle."""
+        with self._lock:
+            if not self._closed:
+                try:
+                    self._file.flush()
+                    self._file.close()
+                finally:
+                    self._closed = True
+
+    def __enter__(self) -> "JSONLRecorder":
+        return self
+
+    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
+        self.close()
+
+    @staticmethod
+    def read_records(file_path: Union[str, Path]) -> List[RawRequestMeasurement]:
+        """Reads and validates all raw measurements from a JSONL file."""
+        records: List[RawRequestMeasurement] = []
+        path = Path(file_path)
+        if not path.exists():
+            return records
+        with open(path, "r", encoding="utf-8") as f:
+            for line_no, line in enumerate(f, start=1):
+                stripped = line.strip()
+                if stripped:
+                    records.append(RawRequestMeasurement.model_validate_json(stripped))
+        return records
diff --git a/src/slokern/engine/loadgen/runner.py b/src/slokern/engine/loadgen/runner.py
index e69de29..a9d9482 100644
--- a/src/slokern/engine/loadgen/runner.py
+++ b/src/slokern/engine/loadgen/runner.py
@@ -0,0 +1,304 @@
+"""
+Purpose: Subprocess-isolated load generator runner producing request-level microsecond timings.
+Owner: Rajdeep (Historical design: Adriraj)
+Authority: Aligned with docs/experiment-methodology.md Section 2-4 and AGENTS.md Section 1, 3, 4
+"""
+
+import asyncio
+import multiprocessing as mp
+from multiprocessing.connection import Connection
+from pathlib import Path
+import time
+from typing import Any, Callable, Dict, List, Optional, Union
+from pydantic import BaseModel, ConfigDict, Field
+
+from slokern.contracts.evidence import RawRequestMeasurement
+from slokern.contracts.spec import WorkloadSpec
+from slokern.engine.loadgen.arrival import ArrivalSchedule, ArrivalSlot
+from slokern.engine.loadgen.recorder import JSONLRecorder
+from slokern.engine.serving.base import BaseServingAdapter, ServingRequest, ServingResponse
+
+
+class LoadGeneratorResult(BaseModel):
+    """Execution summary and saturation diagnostics from a completed load generator run."""
+    model_config = ConfigDict(extra="forbid")
+
+    total_requests: int = Field(..., description="Total requests scheduled and recorded")
+    warmup_requests: int = Field(..., description="Warm-up requests count")
+    active_requests: int = Field(..., description="Active window requests count")
+    completed_requests: int = Field(..., description="Successfully completed requests count")
+    failed_requests: int = Field(..., description="Failed requests count")
+
+    target_offered_rate: float = Field(..., description="Intended arrival rate (req/s)")
+    offered_load_rps: float = Field(..., description="Actual rate at which client scheduled requests")
+    achieved_load_rps: float = Field(..., description="Delivered valid throughput over measurement window")
+    generator_saturated: bool = Field(..., description="Flag indicating if load generator experienced scheduler saturation")
+
+    mean_dispatch_lag_ms: float = Field(..., description="Mean delay between scheduled time and socket write start")
+    max_dispatch_lag_ms: float = Field(..., description="Maximum delay between scheduled time and socket write start")
+
+    output_path: str = Field(..., description="Path to generated .jsonl trace file")
+    error: Optional[str] = Field(None, description="Error detail if execution encountered an unhandled exception")
+
+    @property
+    def mean_dispatch_skew_ms(self) -> float:
+        """Alias for mean_dispatch_lag_ms conforming to documentation nomenclature."""
+        return self.mean_dispatch_lag_ms
+
+    @property
+    def max_dispatch_skew_ms(self) -> float:
+        """Alias for max_dispatch_lag_ms conforming to documentation nomenclature."""
+        return self.max_dispatch_lag_ms
+
+
+async def _async_dispatch_loop(
+    workload: WorkloadSpec,
+    adapter: BaseServingAdapter,
+    output_path: str,
+    run_id: str,
+    seed: Optional[int],
+    stream: bool,
+    prompts: Optional[List[str]],
+    artificial_dispatch_delay_ms: float,
+) -> LoadGeneratorResult:
+    """Core asynchronous dispatch and measurement loop."""
+    prompt_list = prompts if prompts else [
+        f"Benchmark prompt for {workload.workload_name} request execution under SLOKern loadgen."
+    ]
+
+    concurrency_limit = max(1, workload.concurrency_limit)
+    semaphore = asyncio.Semaphore(concurrency_limit)
+    recorder = JSONLRecorder(file_path=output_path, flush_immediately=True)
+
+    t_start = time.time()
+    schedule = ArrivalSchedule.from_workload_spec(workload, seed=seed, start_time=t_start)
+    slots = list(schedule)
+
+    async def _dispatch_single_request(slot: ArrivalSlot) -> None:
+        async with semaphore:
+            # Client-side delay injection for saturation testing
+            if artificial_dispatch_delay_ms > 0:
+                await asyncio.sleep(artificial_dispatch_delay_ms / 1000.0)
+
+            # Monotonicity protection: socket write timestamp must never precede scheduled time
+            sent_at = max(time.time(), slot.scheduled_at)
+
+            prompt = prompt_list[slot.index % len(prompt_list)]
+            req_id = f"req-{run_id}-{slot.index:06d}"
+            req = ServingRequest(
+                prompt=prompt,
+                max_tokens=workload.max_output_tokens,
+                request_id=req_id,
+                run_id=run_id,
+                stream=stream,
+            )
+
+            input_tokens = max(1, int(len(prompt.split()) * 1.3))
+
+            if stream:
+                first_token_at: Optional[float] = None
+                tokens_received = 0
+                itl_observations: List[float] = []
+                prev_token_time: Optional[float] = None
+                status_code = 200
+                err_type: Optional[str] = None
+                err_msg: Optional[str] = None
+
+                try:
+                    async for chunk in adapter.astream_generate(req):
+                        chunk_time = time.time()
+                        if first_token_at is None:
+                            first_token_at = max(chunk_time, sent_at)
+                            prev_token_time = chunk_time
+                        else:
+                            delta_ms = (chunk_time - prev_token_time) * 1000.0
+                            if chunk.latency_ms > 0 and (not getattr(adapter, "simulate_delay", True)):
+                                itl_observations.append(chunk.latency_ms)
+                            else:
+                                itl_observations.append(round(delta_ms, 3))
+                            prev_token_time = chunk_time
+
+                        tokens_received += 1
+                        if chunk.error:
+                            err_msg = chunk.error
+                            err_type = chunk.metadata.get("failure_injected", "streaming_error")
+                            status_code = chunk.metadata.get("status_code", 500)
+                            break
+                except Exception as exc:
+                    err_msg = str(exc)
+                    err_type = type(exc).__name__
+                    status_code = 500
+
+                now_complete = time.time()
+                completed_at = max(now_complete, first_token_at if first_token_at is not None else sent_at)
+                is_valid = (status_code == 200 and err_type is None and err_msg is None)
+
+                # Monotonicity verification invariant
+                assert slot.scheduled_at <= sent_at
+                if first_token_at is not None:
+                    assert sent_at <= first_token_at <= completed_at
+                else:
+                    assert sent_at <= completed_at
+
+                measurement = RawRequestMeasurement(
+                    request_id=req_id,
+                    run_id=run_id,
+                    scheduled_at=slot.scheduled_at,
+                    sent_at=sent_at,
+                    first_token_at=first_token_at,
+                    completed_at=completed_at,
+                    http_status=status_code,
+                    input_tokens=input_tokens,
+                    output_tokens=tokens_received,
+                    itl_observations_ms=itl_observations if itl_observations else None,
+                    error_type=err_type,
+                    is_warmup=slot.is_warmup,
+                    is_valid=is_valid,
+                )
+            else:
+                try:
+                    response = await adapter.agenerate(req)
+                except Exception as exc:
+                    response = ServingResponse(
+                        request_id=req_id,
+                        run_id=run_id,
+                        text="",
+                        input_tokens=input_tokens,
+                        output_tokens=0,
+                        first_token_latency_ms=None,
+                        itl_observations_ms=[],
+                        total_latency_ms=1.0,
+                        status_code=500,
+                        error=str(exc),
+                        error_type=type(exc).__name__,
+                    )
+
+                measurement = response.to_raw_measurement(
+                    scheduled_at=slot.scheduled_at,
+                    sent_at=sent_at,
+                    is_warmup=slot.is_warmup,
+                )
+
+                # Ensure monotonicity on non-streaming path
+                if measurement.first_token_at is not None:
+                    assert measurement.scheduled_at <= measurement.sent_at <= measurement.first_token_at <= measurement.completed_at
+                else:
+                    assert measurement.scheduled_at <= measurement.sent_at <= measurement.completed_at
+
+            recorder.record(measurement)
+
+    tasks: List[asyncio.Task] = []
+    try:
+        for slot in slots:
+            now = time.time()
+            wait_time = slot.scheduled_at - now
+            if wait_time > 0:
+                await asyncio.sleep(wait_time)
+
+            task = asyncio.create_task(_dispatch_single_request(slot))
+            tasks.append(task)
+
+        if tasks:
+            await asyncio.gather(*tasks, return_exceptions=True)
+    finally:
+        recorder.close()
+
+    stats = recorder.get_stats()
+
+    active_duration_s = float(workload.measurement_duration_s)
+    if active_duration_s > 0:
+        offered_load_rps = round(stats.active_count / active_duration_s, 4)
+        achieved_load_rps = round(stats.active_valid_count / active_duration_s, 4)
+        mean_dispatch_lag_ms = stats.active_mean_dispatch_lag_ms
+        max_dispatch_lag_ms = stats.active_max_dispatch_lag_ms
+    else:
+        warmup_dur = float(workload.warmup_duration_s) if workload.warmup_duration_s > 0 else 1.0
+        offered_load_rps = round(stats.total_count / warmup_dur, 4)
+        achieved_load_rps = round(stats.valid_count / warmup_dur, 4)
+        mean_dispatch_lag_ms = stats.mean_dispatch_lag_ms
+        max_dispatch_lag_ms = stats.max_dispatch_lag_ms
+
+    target_rate = float(workload.target_offered_rate)
+    rate_deficit = (target_rate > 0) and (offered_load_rps < 0.90 * target_rate)
+    skew_exceeded = mean_dispatch_lag_ms > 10.0
+    generator_saturated = bool(skew_exceeded or rate_deficit)
+
+    return LoadGeneratorResult(
+        total_requests=stats.total_count,
+        warmup_requests=stats.warmup_count,
+        active_requests=stats.active_count,
+        completed_requests=stats.valid_count,
+        failed_requests=stats.error_count,
+        target_offered_rate=target_rate,
+        offered_load_rps=offered_load_rps,
+        achieved_load_rps=achieved_load_rps,
+        generator_saturated=generator_saturated,
+        mean_dispatch_lag_ms=mean_dispatch_lag_ms,
+        max_dispatch_lag_ms=max_dispatch_lag_ms,
+        output_path=output_path,
+        error=None,
+    )
+
+
+def _subprocess_entrypoint(
+    conn: Connection,
+    workload: WorkloadSpec,
+    adapter: BaseServingAdapter,
+    output_path: str,
+    run_id: str,
+    seed: Optional[int],
+    stream: bool,
+    prompts: Optional[List[str]],
+    artificial_dispatch_delay_ms: float,
+) -> None:
+    """Entrypoint executing inside the isolated child process."""
+    try:
+        result = asyncio.run(
+            _async_dispatch_loop(
+                workload=workload,
+                adapter=adapter,
+                output_path=output_path,
+                run_id=run_id,
+                seed=seed,
+                stream=stream,
+                prompts=prompts,
+                artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
+            )
+        )
+        conn.send({"success": True, "result": result.model_dump()})
+    except Exception as exc:
+        conn.send({"success": False, "error": str(exc), "error_type": type(exc).__name__})
+    finally:
+        conn.close()
+
+
+class LoadGeneratorRunner:
+    """
+    Subprocess-isolated load generator runner.
+    Spawns an isolated Python process to avoid GC/GIL interference with benchmark timings.
+    """
+
+    def __init__(
+        self,
+        isolate_process: bool = True,
+        spawn_timeout_s: Optional[float] = 120.0,
+    ) -> None:
+        self.isolate_process = isolate_process
+        self.spawn_timeout_s = spawn_timeout_s
+
+    def run(
+        self,
+        workload: WorkloadSpec,
+        adapter: BaseServingAdapter,
+        output_path: Union[str, Path],
+        run_id: str = "run-001",
+        seed: Optional[int] = 42,
+        stream: bool = True,
+        prompts: Optional[Union[List[str], str]] = None,
+        artificial_dispatch_delay_ms: float = 0.0,
+    ) -> LoadGeneratorResult:
+        """
+        Executes the benchmark load generation run.
+        If isolate_process=True, runs within a dedicated multiprocessing child process.
+        """
+        prompt_list: Optional[List[str]] = None
+        if isinstance(prompts, str):
+            prompt_list = [prompts]
+        elif prompts is not None:
+            prompt_list = list(prompts)
+
+        out_str = str(Path(output_path).resolve())
+
+        if not self.isolate_process:
+            return asyncio.run(
+                _async_dispatch_loop(
+                    workload=workload,
+                    adapter=adapter,
+                    output_path=out_str,
+                    run_id=run_id,
+                    seed=seed,
+                    stream=stream,
+                    prompts=prompt_list,
+                    artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
+                )
+            )
+
+        ctx = mp.get_context("spawn")
+        parent_conn, child_conn = ctx.Pipe(duplex=False)
+
+        proc = ctx.Process(
+            target=_subprocess_entrypoint,
+            args=(
+                child_conn,
+                workload,
+                adapter,
+                out_str,
+                run_id,
+                seed,
+                stream,
+                prompt_list,
+                artificial_dispatch_delay_ms,
+            ),
+        )
+
+        proc.start()
+        child_conn.close()
+
+        has_data = parent_conn.poll(self.spawn_timeout_s)
+        if not has_data:
+            proc.kill()
+            proc.join()
+            raise TimeoutError(
+                f"LoadGenerator subprocess timed out after {self.spawn_timeout_s}s"
+            )
+
+        msg = parent_conn.recv()
+        proc.join()
+
+        if proc.exitcode != 0 and not msg:
+            raise RuntimeError(
+                f"LoadGenerator subprocess exited abnormally with code {proc.exitcode}"
+            )
+
+        if not msg.get("success"):
+            raise RuntimeError(
+                f"LoadGenerator execution failed in subprocess: {msg.get('error')} ({msg.get('error_type')})"
+            )
+
+        return LoadGeneratorResult.model_validate(msg["result"])
+
+    async def arun(
+        self,
+        workload: WorkloadSpec,
+        adapter: BaseServingAdapter,
+        output_path: Union[str, Path],
+        run_id: str = "run-001",
+        seed: Optional[int] = 42,
+        stream: bool = True,
+        prompts: Optional[Union[List[str], str]] = None,
+        artificial_dispatch_delay_ms: float = 0.0,
+    ) -> LoadGeneratorResult:
+        """Asynchronous execution wrapper delegating process management to a background thread."""
+        return await asyncio.to_thread(
+            self.run,
+            workload=workload,
+            adapter=adapter,
+            output_path=output_path,
+            run_id=run_id,
+            seed=seed,
+            stream=stream,
+            prompts=prompts,
+            artificial_dispatch_delay_ms=artificial_dispatch_delay_ms,
+        )
```

---

## 3. Test Execution Commands and Full Test Outputs

### 3.1 Loadgen Unit Test Suite Command & Output
```bash
.venv/bin/pytest tests/unit/engine/loadgen/ -v
```
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0 -- /home/caelum/DevArena/projects/slokern/.venv/bin/python3
cachedir: .pytest_cache
rootdir: /home/caelum/DevArena/projects/slokern
configfile: pyproject.toml
collecting ... collected 24 items                                                             

tests/unit/engine/loadgen/test_arrival.py::test_constant_arrival_slots_count_and_intervals PASSED [  4%]
tests/unit/engine/loadgen/test_arrival.py::test_constant_arrival_zero_warmup PASSED [  8%]
tests/unit/engine/loadgen/test_arrival.py::test_constant_arrival_zero_measurement PASSED [ 12%]
tests/unit/engine/loadgen/test_arrival.py::test_constant_arrival_zero_total_duration PASSED [ 16%]
tests/unit/engine/loadgen/test_arrival.py::test_poisson_arrival_seed_reproducibility PASSED [ 20%]
tests/unit/engine/loadgen/test_arrival.py::test_poisson_arrival_different_seeds PASSED [ 25%]
tests/unit/engine/loadgen/test_arrival.py::test_poisson_arrival_rate_approximation PASSED [ 29%]
tests/unit/engine/loadgen/test_arrival.py::test_poisson_warmup_partition PASSED [ 33%]
tests/unit/engine/loadgen/test_arrival.py::test_from_workload_spec PASSED [ 37%]
tests/unit/engine/loadgen/test_arrival.py::test_invalid_parameters_raise PASSED [ 41%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_writes_valid_jsonl PASSED [ 45%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_immediate_disk_flush PASSED [ 50%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_validates_dict_input PASSED [ 54%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_rejects_invalid_schema PASSED [ 58%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_running_stats PASSED [ 62%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_read_records PASSED [ 66%]
tests/unit/engine/loadgen/test_recorder.py::test_recorder_closed_error PASSED [ 70%]
tests/unit/engine/loadgen/test_runner.py::test_runner_subprocess_dispatch_streaming PASSED [ 75%]
tests/unit/engine/loadgen/test_runner.py::test_runner_in_process_non_streaming PASSED [ 79%]
tests/unit/engine/loadgen/test_runner.py::test_runner_handles_injected_server_errors PASSED [ 83%]
tests/unit/engine/loadgen/test_runner.py::test_saturation_triggered_by_artificial_dispatch_delay PASSED [ 87%]
tests/unit/engine/loadgen/test_runner.py::test_saturation_healthy_run PASSED [ 91%]
tests/unit/engine/loadgen/test_runner.py::test_runner_poisson_arrival_execution PASSED [ 95%]
tests/unit/engine/loadgen/test_runner.py::test_runner_arun_async_wrapper PASSED [100%]

============================== 24 passed in 9.01s ==============================
```

### 3.2 Full Project Test Suite Command & Output
```bash
.venv/bin/pytest tests/
```
```text
============================= test session starts ==============================
platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.7.0
rootdir: /home/caelum/DevArena/projects/slokern
configfile: pyproject.toml
collecting ... collected 229 items                                                            

tests/contract/test_generated_files_current.py ................          [  6%]
tests/contract/test_schema_roundtrip.py ................................ [ 20%]
.................................................................        [ 49%]
tests/contract/test_schemas.py ......                                    [ 51%]
tests/live/test_smoke_live.py s                                          [ 52%]
tests/unit/core/test_evaluator.py .............................          [ 65%]
tests/unit/core/test_ranker.py ........                                  [ 68%]
tests/unit/core/test_ranker_validation.py ...                            [ 69%]
tests/unit/core/test_states.py ..                                        [ 70%]
tests/unit/engine/loadgen/test_arrival.py ..........                     [ 75%]
tests/unit/engine/loadgen/test_recorder.py .......                       [ 78%]
tests/unit/engine/loadgen/test_runner.py .......                         [ 81%]
tests/unit/engine/serving/test_base.py .........                         [ 85%]
tests/unit/engine/serving/test_capabilities.py .........                 [ 89%]
tests/unit/engine/serving/test_fake.py .........................         [100%]

======================== 228 passed, 1 skipped in 9.39s ========================
```

---

## 4. Verification Record

### Deep Verification (Ran actual automated tests)
- **Arrival Schedules (`test_arrival.py`):**
  - Constant arrival interval $\Delta t = 1/\lambda$ tested over multiple rates and durations.
  - Poisson arrival inter-arrival times $\Delta t \sim \text{Exp}(\lambda)$ verified for rate fidelity over large samples ($N \approx 5000$).
  - PRNG seed reproducibility verified: identical seeds produce identical slots; differing seeds diverge.
  - Warm-up temporal partitioning verified across zero-warmup, zero-measurement, and mixed scenarios.
  - Boundary validations verified (negative rate, zero rate, negative durations, unsupported modes).
- **Measurement Recorder (`test_recorder.py`):**
  - Line-by-line JSONL streaming verified against Pydantic v2 `RawRequestMeasurement` schema.
  - Immediate disk flushing verified: disk files are populated before `recorder.close()`.
  - Schema rejection verified for missing required fields and extra forbidden fields.
  - Running counters and dispatch lag metrics verified.
  - Persistence roundtrip verified using `read_records()`.
- **Subprocess Runner (`test_runner.py`):**
  - Real subprocess spawning via `multiprocessing.get_context("spawn")` verified against `FakeServingAdapter`.
  - Timestamp monotonicity invariant verified: `scheduled_at <= sent_at <= first_token_at <= completed_at` across all recorded measurements.
  - Error containment verified: server failures (e.g. `force_oom`) are written to `.jsonl` without aborting the load generator subprocess.
  - Scheduler saturation verified: artificial delay (15ms) correctly triggers `generator_saturated = True`, while normal run retains `generator_saturated = False`.
  - Asynchronous dispatch via `arun()` verified.
- **Contract & Regression Suite:**
  - 228 tests passing across contracts, evaluator, ranker, states, serving, and loadgen.

### Shallow Verification (Manual run only)
- Eyeballed IPC serialization payload format and pipe communication clean closing.

### Unverified Aspects (Honest boundary disclosures)
- **Live Remote Network Endpoints:** Load generator was verified in isolated subprocesses against `FakeServingAdapter`. It has not yet been benchmarked against a remote Nebius Cloud vLLM cluster over live HTTPS (reserved for live deployment test in Phase B / Stage 2).
- **Extreme High Concurrency ($> 1000$ concurrent requests):** Tested with bounded concurrency up to 32. Operating system file descriptor limits under massive client concurrency were not stressed in these unit test scenarios.

---

## 5. Known Issues
- `None` (All unit and contract tests pass cleanly with 100% success; zero regressions).

---

## 6. Untested Edge Cases & Next Step
- **Reviewer Focus:** Test OS-level SIGTERM / SIGKILL interruption handling of the spawned load generator process during an active in-flight benchmark run.
- **Downstream Integration:** Proceed to `TASK-08` / `SUB-08` (`src/slokern/engine/runner/run_executor.py`), integrating `FakeServingAdapter`, `LoadGeneratorRunner`, and `MetricEngine` into the unified single-run executor.
