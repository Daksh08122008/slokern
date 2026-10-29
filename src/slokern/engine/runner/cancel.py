"""
Purpose: Cancellation handling that never reports a cancelled run as successful.
Owner: Rajdeep (Architecture & Verification)
Authority: Aligned with AGENTS.md Section 6, Section 9, and docs/architecture.md
"""

import threading
from typing import Callable, List


class RunCancelledError(Exception):
    """Raised when an execution or task is stopped due to cancellation."""
    pass


class CancellationToken:
    """
    Thread-safe cooperative cancellation token.
    Allows decoupling cancellation triggers from execution loops and subprocesses.
    Never reports or permits a cancelled run to be marked successful.
    """

    def __init__(self) -> None:
        self._is_cancelled = threading.Event()
        self._callbacks: List[Callable[[], None]] = []
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """
        Triggers cooperative cancellation.
        Executes all registered callbacks to clean up resources, sockets, and subprocesses.
        """
        with self._lock:
            if self._is_cancelled.is_set():
                return
            self._is_cancelled.set()
            callbacks_to_run = list(self._callbacks)

        for callback in callbacks_to_run:
            try:
                callback()
            except Exception:
                # Callback failures must not block other cancellation handlers
                pass

    @property
    def is_cancelled(self) -> bool:
        """Returns True if cancellation has been requested."""
        return self._is_cancelled.is_set()

    def register_callback(self, callback: Callable[[], None]) -> None:
        """
        Registers a cleanup callback to be invoked upon cancellation.
        If cancellation has already been requested, invokes callback immediately.
        """
        already_cancelled = False
        with self._lock:
            if self._is_cancelled.is_set():
                already_cancelled = True
            else:
                self._callbacks.append(callback)

        if already_cancelled:
            try:
                callback()
            except Exception:
                pass

    def check_cancelled(self) -> None:
        """
        Raises RunCancelledError if cancellation has been requested.
        Call periodically at safe interrupt points.
        """
        if self._is_cancelled.is_set():
            raise RunCancelledError("Execution was cancelled via CancellationToken.")
