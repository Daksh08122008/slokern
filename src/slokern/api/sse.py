"""
Purpose: Server-sent event stream queue of experiment progress.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 3, 9 and docs/architecture.md
"""

import json
import queue
import time
from typing import Any, Dict, Optional


class SSEEventQueue:
    """
    Thread-safe event queue buffering SSE data payloads for streaming HTTP clients.
    """

    def __init__(self, maxsize: int = 100) -> None:
        self._queue: queue.Queue[Optional[str]] = queue.Queue(maxsize=maxsize)
        self.is_closed: bool = False

    def emit(self, event_type: str, data: Dict[str, Any]) -> None:
        if self.is_closed:
            return
        payload = {"type": event_type, "timestamp": time.time(), **data}
        try:
            self._queue.put_nowait(f"data: {json.dumps(payload)}\n\n")
        except queue.Full:
            pass

    def close(self) -> None:
        self.is_closed = True
        self._queue.put(None)

    def get(self, timeout: Optional[float] = 1.0) -> Optional[str]:
        try:
            item = self._queue.get(timeout=timeout)
            return item if isinstance(item, str) else None
        except queue.Empty:
            return None
