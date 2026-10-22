# Adversarial Review Report (Round 2): Subprocess-Isolated Load Generator (`SUB-06`, `TASK-06`)

> [!WARNING] **Skepticism Disclaimer**
> Moderate confidence (8.5/10); 36 unit tests and all 282 full-suite tests pass with zero regressions, but real-network HTTP/TLS socket timings against live remote Nebius Cloud servers remain unverified in local tests.

---

## 1. What the prior attempt got wrong

### Finding 1: Infinite Loop Vulnerability on Non-Finite Inputs (NaN / Inf) in `ArrivalSchedule`
- **Input:** `ArrivalSchedule(ArrivalMode.CONSTANT, target_offered_rate=float('inf'))` or `float('nan')`, or durations with `float('inf')`/`float('nan')`.
- **Expected:** Immediate validation error (`ValueError: target_offered_rate must be positive and finite`).
- **Actual:** `inf <= 0` and `nan <= 0` both evaluate to `False`. For `inf`, `interval = 0.0` caused `while True:` to loop infinitely yielding slots at offset `0.0`. For `nan`, `offset_s = nan` caused `nan >= total_duration` to evaluate to `False` perpetually, freezing the process in an unkillable CPU loop.
- **Root Cause:** Standard inequality comparisons in Python return `False` when comparing with `float('nan')` or `float('inf')`. Missing `math.isfinite()` bounds checks on rates, durations, and start times.

### Finding 2: In-Flight Tasks Crashed upon Early Dispatch Exit or Cancellation
- **Input:** Early exception or cancellation during the dispatch loop while previously dispatched asynchronous tasks were still in flight.
- **Expected:** Pending in-flight tasks are gracefully cancelled and awaited before closing the underlying JSONL file descriptor.
- **Actual:** The `finally` block in `_async_dispatch_loop` immediately called `recorder.close()`. In-flight tasks completing moments later called `recorder.record()` on the closed recorder and crashed with unhandled `RuntimeError: Cannot record to closed JSONLRecorder`, leaking exceptions and dropping measurement events. In addition, task cancellations (`asyncio.CancelledError`, which inherits from `BaseException`) were ignored by `isinstance(res, Exception)`, masking dispatch task aborts from `LoadGeneratorResult.error`.
- **Root Cause:** Missing task drainage/cancellation logic before `recorder.close()` in `finally:`, and narrow `Exception` type check excluding `BaseException`.

### Finding 3: In-Process Runner Mode (`isolate_process=False`) Completely Ignored `spawn_timeout_s`
- **Input:** `LoadGeneratorRunner(isolate_process=False, spawn_timeout_s=0.05).run(...)` with an inference endpoint taking >200ms.
- **Expected:** Runner enforces `spawn_timeout_s` and raises `TimeoutError` consistently with `isolate_process=True`.
- **Actual:** When `isolate_process=False`, `run()` executed directly without applying `spawn_timeout_s`, ignoring timeouts and blocking indefinitely if the serving adapter hung.
- **Root Cause:** Timeout calculation and enforcement were placed after the `if not self.isolate_process: return ...` branch.

### Finding 4: Async Task Cancellation on `arun()` Failed to Reap Child Process
- **Input:** An asyncio coroutine cancelling an active `runner.arun()` task via `task.cancel()`.
- **Expected:** `CancelledError` caught, child process immediately reaped/killed, and no lingering background processes left running.
- **Actual:** `asyncio.to_thread` raised `CancelledError` to the caller, but the worker thread and spawned child process continued running until completion, consuming resources and risking file descriptor conflicts on subsequent runs.
- **Root Cause:** Child process was stored only in a local variable inside `run()`, with no cancellation hook on `arun()`.

### Finding 5: Resource Leak on Child Process Spawn Failure
- **Input:** `proc.start()` raising `OSError` (e.g. process limit or resource exhaustion).
- **Expected:** Both ends of the IPC pipe are closed.
- **Actual:** `child_conn.close()` was executed after `proc.start()`. If `proc.start()` raised, `child_conn` was never closed.
- **Root Cause:** Missing `try ... finally` around `proc.start()` and `child_conn.close()`.

### Finding 6: Missing Direct Statistics Accessors on `JSONLRecorder`
- **Input:** Accessing `recorder.active_valid_count`, `recorder.active_error_count`, `recorder.min_dispatch_lag_ms`, `recorder.active_mean_dispatch_lag_ms`, `recorder.active_max_dispatch_lag_ms`.
- **Expected:** Direct thread-safe property access matching `RecorderStats`.
- **Actual:** Missing attributes on `JSONLRecorder` instance.
- **Root Cause:** Incomplete property delegation in `JSONLRecorder`.

### Finding 7: Monotonicity Invariants Stripped under Bytecode Optimization (`python -O`)
- **Input:** Running with bytecode optimization (`python -O`).
- **Expected:** Monotonicity invariant `scheduled_at <= sent_at <= first_token_at <= completed_at` verified and enforced regardless of optimization level.
- **Actual:** `assert` statements are stripped out in optimized bytecode (`__debug__ == False`).
- **Root Cause:** Use of `assert` rather than explicit `if ...: raise AssertionError(...)`.

---

## 2. What I changed

1. **`src/slokern/engine/loadgen/arrival.py`:**
   - Enforced `math.isfinite()` and positive/non-negative checks on `target_offered_rate`, `warmup_duration_s`, `measurement_duration_s`, and `start_time` in `__init__` and `generate()`.
   - Prevented infinite loops and process freezes when given `nan` or `inf`.

2. **`src/slokern/engine/loadgen/recorder.py`:**
   - Added thread-safe property accessors on `JSONLRecorder`: `active_valid_count`, `active_error_count`, `min_dispatch_lag_ms`, `active_mean_dispatch_lag_ms`, and `active_max_dispatch_lag_ms` for complete parity with `RecorderStats`.

3. **`src/slokern/engine/loadgen/runner.py`:**
   - Strengthened streaming error classification to inspect `chunk.metadata["failure_injected"]` and `chunk.metadata["error_type"]`.
   - Replaced Python `assert` statements with explicit `if ...: raise AssertionError(...)` to guarantee invariant enforcement even under `python -O`.
   - Added task drainage and cancellation in `_async_dispatch_loop`'s `finally:` block before closing `recorder`.
   - Captured `BaseException` (including `asyncio.CancelledError`) into `LoadGeneratorResult.error` and child process IPC.
   - Enforced `spawn_timeout_s` in both `isolate_process=False` and `isolate_process=True` modes via `asyncio.wait_for`.
   - Wrapped `proc.start()` in `try ... finally: child_conn.close()`.
   - Added `LoadGeneratorRunner.cancel()` and intercepted `asyncio.CancelledError` in `arun()` to terminate child processes immediately upon cancellation.

4. **`tests/unit/engine/loadgen/test_arrival.py`:**
   - Added `test_non_finite_parameters_raise` testing `inf`, `nan`, and non-finite `start_time`.

5. **`tests/unit/engine/loadgen/test_recorder.py`:**
   - Added `test_recorder_all_property_accessors` verifying all property accessors match `RecorderStats`.

6. **`tests/unit/engine/loadgen/test_runner.py`:**
   - Added `test_runner_in_process_timeout`: verifies `isolate_process=False` enforces `spawn_timeout_s`.
   - Added `test_runner_zero_duration_workload`: verifies clean handling of 0-duration degenerate workloads.
   - Added `test_runner_arun_cancellation`: verifies cancelling `arun()` terminates child processes.
   - Added `test_runner_trace_end_to_end_metrics_compatibility`: verifies end-to-end integration where `calculate_metrics()` parses and computes canonical metrics from runner-generated traces.

---

## 3. Verification Record

- **Deep Verification (ran actual tests):**
  - Load Generator Suite:
    ```bash
    .venv/bin/pytest tests/unit/engine/loadgen/ -v
    ```
    **Result:** 36 passed in 16.14s.
  - Full Repository Test Suite:
    ```bash
    .venv/bin/pytest tests/
    ```
    **Result:** 282 passed, 1 skipped in 16.46s (1 skipped live network test). Zero regressions across all contracts, core metrics, evaluator, ranker, states, serving, and loadgen.

- **Shallow Verification (manual only):**
  - None. All verification executed via automated tests in the Python virtual environment.

- **Unverified aspects:**
  - **Live Remote Endpoints:** Verified using local subprocess isolation against `FakeServingAdapter`; real-network HTTPS/TLS socket timings against live remote Nebius Cloud servers remain to be verified during stage 2 preflight.
  - **Massive OS Socket Saturation:** Validated up to concurrency 32; socket/file descriptor limits at >1000 concurrent sockets require dedicated load host tuning.

---

## 4. Known Issues

- `Minor Robustness Risk`: High-rate Poisson schedules (>5000 req/s) with very short durations (<1s) may experience higher statistical variance around the 90% offered rate boundary due to natural Poisson dispersion ($3\sigma / \mu \approx 3/\sqrt{\lambda T}$).
- `Shallow Verification`: Remote Nebius vLLM HTTPS integration deferred to Stage 2 live preflight benchmark.

---

## 5. Remaining risk & next step

The subprocess-isolated load generator (`SUB-06`, `TASK-06`) is fully implemented, hardened, and verified with 36 dedicated tests and 282 total passing tests. Next step: integrate into `TASK-08` / `SUB-08` (`src/slokern/engine/runner/run_executor.py`).
