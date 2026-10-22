# Adversarial Review Report (Round 3): Subprocess-Isolated Load Generator (`SUB-06`, `TASK-06`)

> [!WARNING] **Skepticism Disclaimer**
> High confidence (9.5/10) on load generator subprocess lifecycle, cancellation synchronization, and trace schema integrity across 38 dedicated unit tests and 284 full-suite tests; live remote TLS connection reset dynamics against Nebius Cloud remain unverified locally until Stage 2 live preflight.

---

## 1. What the prior attempt got wrong

### Finding 1: Concurrent Child Reaping Race Condition between `cancel()` and Background Worker Thread
- **Input:** Cancelling an asynchronous `runner.arun()` task via `task.cancel()`.
- **Expected:** Child process terminated, reaped cleanly, and `runner._current_proc is None or not runner._current_proc.is_alive()` evaluates to `True`.
- **Actual:** Intermittent `AssertionError: assert <SpawnProcess ... started>.is_alive()` failed in ~20% of test runs during `test_runner_arun_cancellation`.
- **Root Cause:** In Python's `multiprocessing`, when `task.cancel()` was called on `arun()`, `arun()` caught `CancelledError` and invoked `cancel()` on the main event-loop thread. `cancel()` sent `proc.kill()` and called `proc.join(timeout=1.0)`. Concurrently, the worker thread executing `run()` in `asyncio.to_thread` unblocked from `parent_conn.poll()` upon process death and *also* called `proc.join(timeout=5.0)`. In the Linux kernel, `waitpid()` can only be consumed once. Whichever thread was second received `OSError: [Errno 10] No child processes` (`ECHILD`). In Python's `multiprocessing/popen_fork.py::poll()`, `OSError` is swallowed and returns `None` without setting `self.returncode`. When `is_alive()` was subsequently called by the main thread, `self._popen.poll()` returned `None`, making `is_alive()` falsely evaluate to `True` even though the child process was already terminated by `SIGKILL`.

### Finding 2: Lack of Atomic Mutex and Cancellation Signal before Process Start
- **Input:** `task.cancel()` triggered before `proc.start()` finished or during the window between `proc.start()` and `self._current_proc = proc`.
- **Expected:** Process is either never spawned or immediately killed and reaped without leaving orphaned background processes.
- **Actual:** `cancel()` inspected `self._current_proc`, found `None`, and did nothing. `run()` then proceeded to start the child process and assigned `self._current_proc = proc`, leaving an active running subprocess and background worker thread alive.
- **Root Cause:** Missing thread-synchronization primitives (`threading.Lock` and cancellation state tracking `_cancel_requested`) guarding process instantiation, startup, and reaping.

### Finding 3: Unguarded Worker Thread Future Cancellation in `arun()`
- **Input:** Coroutine cancellation on `arun()` leaving the background thread running in the executor.
- **Expected:** Worker thread drain and cleanup before `arun()` re-raises `CancelledError`.
- **Actual:** `arun()` caught `CancelledError`, called `cancel()`, and immediately re-raised without waiting for the executor thread to finish `run()` and close file handles.
- **Root Cause:** Calling `asyncio.to_thread` without shielding and awaiting worker thread completion upon cancellation.

---

## 2. What I changed

1. **`src/slokern/engine/loadgen/runner.py`:**
   - Added `_proc_lock = threading.Lock()` and `_cancel_requested = False` on `LoadGeneratorRunner`.
   - Synchronized `cancel()` under `_proc_lock`: marks `_cancel_requested = True`, sends `proc.kill()`, joins with timeout, verifies OS process termination via `os.kill(proc.pid, 0)` (handling `ECHILD` race by setting `returncode = -9` if reaped), and clears `_current_proc = None`.
   - Protected `proc.start()` under `_proc_lock`: aborts with `asyncio.CancelledError` before spawning if cancelled, and ensures `_current_proc` is assigned atomically with process start.
   - Guarded `proc.join()` and process cleanup in `run()` under `_proc_lock` to eliminate concurrent `waitpid()` collisions between threads.
   - Refactored `arun()` to submit via `loop.run_in_executor` and on `asyncio.CancelledError`, call `self.cancel()` and await the worker thread future under `asyncio.shield` so the worker thread finishes cleaning up before cancellation propagates.
   - Passed `is_cancelled` callback into `_async_dispatch_loop` so in-process execution (`isolate_process=False`) also respects cancellation promptly.

2. **`tests/unit/engine/loadgen/test_runner.py`:**
   - Added `test_runner_arun_cancellation_in_process`: verifies cancelling `arun()` in in-process mode (`isolate_process=False`) raises `asyncio.CancelledError` cleanly.
   - Added `test_runner_cancel_noop_when_not_running`: verifies `runner.cancel()` is safe and a noop when no child process is active.

---

## 3. Verification Record

- **Deep Verification (ran actual tests):**
  - Cancellation Race Stability (50 consecutive runs):
    ```bash
    python3 -c "
    import subprocess
    for i in range(50):
        res = subprocess.run(['.venv/bin/pytest', 'tests/unit/engine/loadgen/test_runner.py', '-k', 'test_runner_arun_cancellation', '-q'], capture_output=True, text=True)
        if res.returncode != 0:
            print(f'Failed on run {i}:', res.stdout)
            break
    else:
        print('All 50 passed!')
    "
    ```
    **Result:** All 50 passed cleanly (0 failures, 100% reliability).
  - Load Generator Test Suite:
    ```bash
    .venv/bin/pytest tests/unit/engine/loadgen/ -v
    ```
    **Result:** 38 passed in 16.66s.
  - Full Repository Test Suite:
    ```bash
    .venv/bin/pytest tests/
    ```
    **Result:** 284 passed, 1 skipped in 17.03s (1 skipped live network test). Zero regressions across all contracts, core metrics, evaluator, ranker, states, serving, and loadgen.

- **Shallow Verification (manual only):**
  - None. All verification executed via automated tests in the Python virtual environment.

- **Unverified aspects:**
  - **Live Remote Endpoints:** Verified using local subprocess isolation against `FakeServingAdapter`; real-network HTTPS/TLS socket timings against live remote Nebius Cloud servers remain to be verified during stage 2 preflight.
  - **Massive Concurrency Socket Saturation:** Validated up to concurrency 32; socket/file descriptor limits at >1000 concurrent sockets require dedicated load host tuning.

---

## 4. Known Issues

- `Minor Robustness Risk`: High-rate Poisson schedules (>5000 req/s) with very short durations (<1s) may experience higher statistical variance around the 90% offered rate boundary due to natural Poisson dispersion ($3\sigma / \mu \approx 3/\sqrt{\lambda T}$).
- `Shallow Verification`: Remote Nebius vLLM HTTPS integration deferred to Stage 2 live preflight benchmark.

---

## 5. Remaining risk & next step

The subprocess-isolated load generator (`SUB-06`, `TASK-06`) is completely implemented, hardened against process lifecycle and threading races, and verified with 38 dedicated unit tests and 284 total passing tests across the entire repository. The task is fully complete. Next step: integrate into `TASK-08` / `SUB-08` (`src/slokern/engine/runner/run_executor.py`).
