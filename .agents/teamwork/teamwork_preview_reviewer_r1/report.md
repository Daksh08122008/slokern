# Adversarial Review Report: Subprocess-Isolated Load Generator (`SUB-06`, `TASK-06`)

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Reviewer Role:** Adversarial Reviewer (Round 1)  
> **Author / Prior Attempt:** teamwork_preview_implementer  
> **Review Date:** October 22, 2026  
> **Integrity Mode:** Development  
> **Authority:** Aligned with `AGENTS.md` Sections 1, 3, 4, 10, 16; `docs/experiment-methodology.md`; `docs/metrics.md`

---

## 1. Requirements Derivation & Independent Assessment

The requirements for `SUB-06` (`TASK-06`) dictate an open-loop load generator that:
1. **R1 (Arrival Schedules):** Accurately schedules arrival slots for `ArrivalMode.CONSTANT` ($\Delta t = 1/\lambda$) and `ArrivalMode.POISSON` ($\Delta t \sim \text{Exp}(\lambda)$) with reproducible PRNG seeding and warm-up partitioning.
2. **R2 (Crash-Resilient JSONL Recorder):** Streams unaggregated microsecond request events conforming strictly to Pydantic v2 `RawRequestMeasurement` (`ConfigDict(extra="forbid")`), flushed immediately after every write, tracking real-time dispatch delay statistics.
3. **R3 (Subprocess-Isolated Runner):** Executes dispatch in an isolated process spawned via `multiprocessing.get_context("spawn")` to eliminate GIL/GC interference, respecting `concurrency_limit` and microsecond timing, enforcing monotonicity (`scheduled_at <= sent_at <= first_token_at <= completed_at`).
4. **R4 (Scheduler Saturation Detection):** Tracks `offered_load_rps`, `achieved_load_rps`, `mean_dispatch_lag_ms`, and `max_dispatch_lag_ms`. Sets `generator_saturated = True` if `mean_dispatch_skew_ms > 10.0` or `offered_load_rps < 0.90 * target_offered_rate`.

---

## 2. Adversarial Findings & Root Causes (What the Prior Attempt Got Wrong)

### Finding 1: Streaming Error Chunk Corrupted TTFT and Output Token Counts
- **Input:** A streaming request that fails before generating valid tokens (e.g. `adapter.inject_oom(True)` emitting a `TokenChunk(token="", error=..., metadata={"failure_injected": "cuda_out_of_memory", "status_code": 500})`).
- **Expected:** Per `docs/metrics.md` Section 2.1: *"If a request aborts, times out, or fails before emitting a token, TTFT is recorded as null and the request increments the error count."* `RawRequestMeasurement` must record `first_token_at = None` and `output_tokens = 0`.
- **Actual:** `RawRequestMeasurement` recorded `first_token_at = 1792658036.9973195` (a valid timestamp) and `output_tokens = 1`.
- **Root Cause:** In `src/slokern/engine/loadgen/runner.py`, `_async_dispatch_loop` assigned `first_token_at = max(chunk_time, sent_at)` and incremented `tokens_received += 1` *before* checking `if chunk.error: break`. The prior test suite failed to catch this because `test_runner_handles_injected_server_errors` only asserted `scheduled_at <= sent_at <= completed_at` and omitted assertions on `first_token_at is None` or `output_tokens == 0`.

### Finding 2: Subprocess Crash / Hard Termination Handled via Uncaught EOFError Leaving Zombie Processes
- **Input:** Spawned child process abruptly terminating (e.g. killed by OS OOM killer, `SIGKILL`, or `os._exit(42)`).
- **Expected:** Runner detects process death, reaps child process via `proc.join()`, closes pipe file descriptors, and raises a descriptive `RuntimeError(f"LoadGenerator subprocess exited abnormally with code {proc.exitcode}")`.
- **Actual:** `parent_conn.poll()` returned `True` upon pipe EOF (standard POSIX behavior), but `parent_conn.recv()` raised an unhandled `EOFError`. Execution aborted without calling `proc.join()` or closing `parent_conn`, creating a zombie/defunct process and leaking file descriptors. Line 361 (`if proc.exitcode != 0 and not msg: raise RuntimeError(...)`) was unreachable.
- **Root Cause:** `parent_conn.recv()` was called without `try ... except EOFError:`, and process cleanup + pipe closing were not encapsulated in a `finally` block.

### Finding 3: Premature Subprocess Timeout on Standard Long Benchmark Workloads
- **Input:** Standard benchmark workload with duration $> 120$ seconds (e.g. 15s warmup + 120s measurement = 135s total, as described in `docs/experiment-methodology.md`).
- **Expected:** Subprocess timeout dynamically accommodates the declared workload duration plus drainage grace period (`max(120.0, total_duration + 60.0)`).
- **Actual:** Static default `spawn_timeout_s = 120.0` timed out at 120s, killing healthy benchmark runs and raising `TimeoutError`.
- **Root Cause:** `spawn_timeout_s` was a static constant that failed to scale with `workload.warmup_duration_s + workload.measurement_duration_s`.

### Finding 4: File Descriptor Leak in Parent Process
- **Input:** Repeated invocations of `LoadGeneratorRunner.run()`.
- **Expected:** Pipe file descriptors are cleanly closed in the parent process.
- **Actual:** `parent_conn.close()` was never called anywhere in `runner.py`, leaking one pipe file descriptor per experiment run.
- **Root Cause:** Missing `parent_conn.close()` in `finally` cleanup.

### Finding 5: Discarded Task Exceptions in Dispatch Loop
- **Input:** Unexpected exceptions raised during asynchronous request dispatch or recording.
- **Expected:** Exceptions captured by `asyncio.gather(*tasks, return_exceptions=True)` are inspected and surfaced via `LoadGeneratorResult.error`.
- **Actual:** Return value was discarded; `LoadGeneratorResult.error` was hardcoded to `None`.
- **Root Cause:** Missing iteration over `gather` results to capture exceptions into `LoadGeneratorResult.error`.

### Finding 6: Inconsistent Thread Locking on JSONLRecorder Counters
- **Input:** Reading recorder properties (`total_count`, `active_count`, etc.) while concurrent writes are active.
- **Expected:** All count properties acquire `self._lock` consistently with `mean_dispatch_lag_ms`.
- **Actual:** Count properties accessed bare internal variables without acquiring `self._lock`.
- **Root Cause:** Incomplete lock coverage across recorder properties.

---

## 3. Modifications Made

1. **`src/slokern/engine/loadgen/runner.py`:**
   - Moved `if chunk.error:` to the start of the token streaming loop, preventing error chunks from setting `first_token_at` or incrementing `output_tokens`.
   - Added sub-microsecond non-negative clamping: `delta_ms = max(0.0, (chunk_time - prev_token_time) * 1000.0)`.
   - Inspected `asyncio.gather(*tasks, return_exceptions=True)` results and populated `LoadGeneratorResult.error` with any unhandled task exceptions.
   - Dynamically scaled default subprocess timeout to `max(120.0, total_workload_time + 60.0)` while respecting explicitly specified timeouts.
   - Wrapped `parent_conn` IPC in `try ... finally` ensuring `parent_conn.close()` is always executed and child processes are never orphaned.
   - Handled `EOFError` during `parent_conn.recv()` to cleanly catch crashed/killed child processes, join them, and report their exit code.
   - Added safe delegation to a background thread when `isolate_process=False` is invoked within an active asyncio event loop.

2. **`src/slokern/engine/loadgen/recorder.py`:**
   - Wrapped `total_count`, `warmup_count`, `active_count`, `valid_count`, and `error_count` properties in `with self._lock:` for complete thread-safety.
   - Checked `self._closed` inside `with self._lock:` in `record()` to prevent race conditions during concurrent close and write operations.

3. **`tests/unit/engine/loadgen/test_runner.py`:**
   - Strengthened `test_runner_handles_injected_server_errors` to assert `rec.first_token_at is None` and `rec.output_tokens == 0`.
   - Added `test_runner_streaming_partial_failure`: verifies mid-stream failure preservation (`rec.output_tokens == 2`, `first_token_at is not None`, `is_valid == False`, strict monotonicity).
   - Added `test_saturation_triggered_by_concurrency_bottleneck`: verifies `generator_saturated = True` when low concurrency limit causes queueing delays.
   - Added `test_runner_subprocess_abrupt_crash_handling`: verifies child process exit code 42 is caught, child joined, and `RuntimeError` raised.
   - Added `test_runner_subprocess_timeout`: verifies clean termination and `TimeoutError` when `spawn_timeout_s` is exceeded.
   - Added `test_runner_multiple_prompts_round_robin`: verifies rotating prompt token variations across requests.

4. **`tests/unit/engine/loadgen/test_recorder.py`:**
   - Added `test_recorder_concurrent_thread_writes`: verifies thread-safe concurrent writes across 8 threads without loss or corruption.

---

## 4. Verification Record

### Deep Verification (Ran actual automated tests)
1. **Load Generator Test Suite (`tests/unit/engine/loadgen/`):**
   ```bash
   .venv/bin/pytest tests/unit/engine/loadgen/ -v
   ```
   **Output:** 30 passed in 12.67s.
   - `test_arrival.py`: 10 passed (constant/Poisson arrivals, seed reproducibility, warmup partitions, boundary checks).
   - `test_recorder.py`: 8 passed (JSONL schema validation, immediate flush, dict validation, error counts, thread safety).
   - `test_runner.py`: 12 passed (streaming dispatch, in-process fallback, server errors, artificial delay saturation, concurrency bottleneck saturation, mid-stream partial failure, abrupt crash exit code 42, subprocess timeout, multiple prompts round-robin, async wrapper).

2. **Full Repository Test Suite (`tests/`):**
   ```bash
   .venv/bin/pytest tests/
   ```
   **Output:** 234 passed, 1 skipped in 13.06s (1 skipped live network test). Zero regressions across contracts, evaluator, ranker, states, serving, and loadgen.

### Shallow Verification (Manual only)
- None. All verification executed via automated tests in the Python virtual environment.

### Unverified Aspects (Exhaustive & honest)
- **Live Remote Endpoints:** Load generator has been verified against `FakeServingAdapter` in isolated subprocesses; it has not yet been benchmarked against a live Nebius Cloud vLLM HTTPS endpoint.
- **Massive Concurrency ($> 1000$ concurrent sockets):** Tested with concurrency limits up to 32; OS-level file descriptor saturation under massive concurrency requires hardware stress testing in Stage 2.

---

## 5. Known Issues
- `None` (All identified defects fixed; 30 loadgen tests and 234 full suite tests passing).

---

## 6. Remaining Risk & Next Step
- **Verdict:** Fix verified and complete. Ready for integration into `TASK-08` / `SUB-08` (`src/slokern/engine/runner/run_executor.py`).
