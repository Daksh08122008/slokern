"""
Purpose: Crash-resilient unaggregated JSONL recorder for RawRequestMeasurement.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/experiment-methodology.md Section 5 and AGENTS.md Section 1, 4
"""

from pathlib import Path
import threading
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, ConfigDict, Field

from slokern.contracts.evidence import RawRequestMeasurement


class RecorderStats(BaseModel):
    """Running aggregate counts and latency statistics for recorded requests."""
    model_config = ConfigDict(extra="forbid")

    total_count: int = Field(0, description="Total number of records written")
    warmup_count: int = Field(0, description="Count of warm-up records")
    active_count: int = Field(0, description="Count of active measurement records")
    valid_count: int = Field(0, description="Count of records marked is_valid=True across all records")
    active_valid_count: int = Field(0, description="Count of valid records during the active measurement window")
    error_count: int = Field(0, description="Count of records with errors or non-200 HTTP status across all records")
    active_error_count: int = Field(0, description="Count of error records during the active measurement window")

    # Dispatch latency metrics (ms)
    mean_dispatch_lag_ms: float = Field(0.0, description="Mean dispatch lag across all recorded requests in ms")
    max_dispatch_lag_ms: float = Field(0.0, description="Maximum dispatch lag observed in ms")
    min_dispatch_lag_ms: float = Field(0.0, description="Minimum dispatch lag observed in ms")
    active_mean_dispatch_lag_ms: float = Field(0.0, description="Mean dispatch lag across active requests in ms")
    active_max_dispatch_lag_ms: float = Field(0.0, description="Maximum dispatch lag across active requests in ms")


class JSONLRecorder:
    """
    Crash-resilient JSONL event recorder streaming microsecond traces to disk.
    Strictly validates every record against RawRequestMeasurement and flushes after each write.
    """

    def __init__(
        self,
        file_path: Union[str, Path],
        flush_immediately: bool = True,
        mode: str = "a",
    ) -> None:
        self.file_path = Path(file_path).resolve()
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        self.flush_immediately = flush_immediately
        self._lock = threading.Lock()
        self._file = open(self.file_path, mode, encoding="utf-8")
        self._closed = False

        self._total_count = 0
        self._warmup_count = 0
        self._active_count = 0
        self._valid_count = 0
        self._active_valid_count = 0
        self._error_count = 0
        self._active_error_count = 0

        self._all_lags_ms: List[float] = []
        self._active_lags_ms: List[float] = []

    def record(self, measurement: Union[RawRequestMeasurement, Dict[str, Any]]) -> RawRequestMeasurement:
        """
        Validates, serializes, flushes, and updates statistics for a request measurement event.
        Raises ValidationError if measurement violates the RawRequestMeasurement schema.
        """
        if self._closed:
            raise RuntimeError(f"Cannot record to closed JSONLRecorder ({self.file_path})")

        if isinstance(measurement, RawRequestMeasurement):
            event = measurement
        elif isinstance(measurement, dict):
            event = RawRequestMeasurement.model_validate(measurement)
        else:
            event = RawRequestMeasurement.model_validate(measurement)

        # Calculate dispatch lag in ms: sent_at - scheduled_at
        dispatch_lag_ms = max(0.0, (event.sent_at - event.scheduled_at) * 1000.0)

        # Direct JSON serialization conforming strictly to RawRequestMeasurement
        json_line = event.model_dump_json() + "\n"

        with self._lock:
            if self._closed:
                raise RuntimeError(f"Cannot record to closed JSONLRecorder ({self.file_path})")
            self._file.write(json_line)
            if self.flush_immediately:
                self._file.flush()

            self._total_count += 1
            self._all_lags_ms.append(dispatch_lag_ms)

            is_error = (event.http_status is not None and event.http_status != 200) or (event.error_type is not None)

            if event.is_warmup:
                self._warmup_count += 1
            else:
                self._active_count += 1
                self._active_lags_ms.append(dispatch_lag_ms)
                if event.is_valid:
                    self._active_valid_count += 1
                if is_error:
                    self._active_error_count += 1

            if event.is_valid:
                self._valid_count += 1
            if is_error:
                self._error_count += 1

        return event

    def get_stats(self) -> RecorderStats:
        """Returns snapshot of running counters and dispatch delay statistics."""
        with self._lock:
            all_lags = self._all_lags_ms
            active_lags = self._active_lags_ms

            mean_lag = (sum(all_lags) / len(all_lags)) if all_lags else 0.0
            max_lag = max(all_lags) if all_lags else 0.0
            min_lag = min(all_lags) if all_lags else 0.0

            active_mean_lag = (sum(active_lags) / len(active_lags)) if active_lags else 0.0
            active_max_lag = max(active_lags) if active_lags else 0.0

            return RecorderStats(
                total_count=self._total_count,
                warmup_count=self._warmup_count,
                active_count=self._active_count,
                valid_count=self._valid_count,
                active_valid_count=self._active_valid_count,
                error_count=self._error_count,
                active_error_count=self._active_error_count,
                mean_dispatch_lag_ms=round(mean_lag, 4),
                max_dispatch_lag_ms=round(max_lag, 4),
                min_dispatch_lag_ms=round(min_lag, 4),
                active_mean_dispatch_lag_ms=round(active_mean_lag, 4),
                active_max_dispatch_lag_ms=round(active_max_lag, 4),
            )

    @property
    def total_count(self) -> int:
        with self._lock:
            return self._total_count

    @property
    def warmup_count(self) -> int:
        with self._lock:
            return self._warmup_count

    @property
    def active_count(self) -> int:
        with self._lock:
            return self._active_count

    @property
    def valid_count(self) -> int:
        with self._lock:
            return self._valid_count

    @property
    def error_count(self) -> int:
        with self._lock:
            return self._error_count

    @property
    def mean_dispatch_lag_ms(self) -> float:
        with self._lock:
            return round(sum(self._all_lags_ms) / len(self._all_lags_ms), 4) if self._all_lags_ms else 0.0

    @property
    def max_dispatch_lag_ms(self) -> float:
        with self._lock:
            return round(max(self._all_lags_ms), 4) if self._all_lags_ms else 0.0

    @property
    def min_dispatch_lag_ms(self) -> float:
        with self._lock:
            return round(min(self._all_lags_ms), 4) if self._all_lags_ms else 0.0

    @property
    def active_valid_count(self) -> int:
        with self._lock:
            return self._active_valid_count

    @property
    def active_error_count(self) -> int:
        with self._lock:
            return self._active_error_count

    @property
    def active_mean_dispatch_lag_ms(self) -> float:
        with self._lock:
            return round(sum(self._active_lags_ms) / len(self._active_lags_ms), 4) if self._active_lags_ms else 0.0

    @property
    def active_max_dispatch_lag_ms(self) -> float:
        with self._lock:
            return round(max(self._active_lags_ms), 4) if self._active_lags_ms else 0.0

    def close(self) -> None:
        """Flushes buffers and closes underlying file handle."""
        with self._lock:
            if not self._closed:
                try:
                    self._file.flush()
                    self._file.close()
                finally:
                    self._closed = True

    def __enter__(self) -> "JSONLRecorder":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    @staticmethod
    def read_records(file_path: Union[str, Path]) -> List[RawRequestMeasurement]:
        """Reads and validates all raw measurements from a JSONL file."""
        records: List[RawRequestMeasurement] = []
        path = Path(file_path)
        if not path.exists():
            return records
        with open(path, "r", encoding="utf-8") as f:
            for line_no, line in enumerate(f, start=1):
                stripped = line.strip()
                if stripped:
                    records.append(RawRequestMeasurement.model_validate_json(stripped))
        return records
