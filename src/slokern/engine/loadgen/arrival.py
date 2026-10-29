"""
Purpose: Arrival schedule generator for constant and Poisson open-loop traffic.
Owner: Rajdeep (Historical design: Adriraj)
Authority: Aligned with docs/experiment-methodology.md Section 2.2 and AGENTS.md Section 13
"""

import math
import random
from dataclasses import dataclass
from typing import Iterator, List, Optional, Union

from slokern.contracts.enums import ArrivalMode
from slokern.contracts.spec import WorkloadSpec


@dataclass(frozen=True)
class ArrivalSlot:
    """Represents a scheduled arrival event in the workload timeline."""
    index: int
    scheduled_at: float
    is_warmup: bool
    offset_s: float


class ArrivalSchedule:
    """
    Open-loop arrival schedule generator.
    Supports ArrivalMode.CONSTANT (delta_t = 1 / lambda)
    and ArrivalMode.POISSON (delta_t ~ Exp(lambda)) with reproducible PRNG seeding.
    """

    def __init__(
        self,
        arrival_mode: Union[ArrivalMode, str],
        target_offered_rate: float,
        warmup_duration_s: float = 0.0,
        measurement_duration_s: float = 0.0,
        seed: Optional[int] = 42,
        start_time: float = 0.0,
    ) -> None:
        if isinstance(arrival_mode, str):
            try:
                arrival_mode = ArrivalMode(arrival_mode.lower())
            except ValueError:
                raise ValueError(
                    f"Unsupported arrival mode string: '{arrival_mode}'. "
                    f"Supported modes: {ArrivalMode.CONSTANT.value}, {ArrivalMode.POISSON.value}"
                )

        if arrival_mode not in (ArrivalMode.CONSTANT, ArrivalMode.POISSON):
            raise ValueError(
                f"Unsupported arrival mode: {arrival_mode}. "
                f"Supported open-loop modes: {ArrivalMode.CONSTANT}, {ArrivalMode.POISSON}"
            )

        try:
            target_rate = float(target_offered_rate)
            warmup_dur = float(warmup_duration_s)
            meas_dur = float(measurement_duration_s)
            start_t = float(start_time)
        except (ValueError, TypeError) as exc:
            raise ValueError(f"Numeric parameters must be valid floats: {exc}") from exc

        if not math.isfinite(target_rate) or target_rate <= 0:
            raise ValueError(f"target_offered_rate must be positive and finite, got {target_offered_rate}")
        if not math.isfinite(warmup_dur) or warmup_dur < 0:
            raise ValueError(f"warmup_duration_s must be non-negative and finite, got {warmup_duration_s}")
        if not math.isfinite(meas_dur) or meas_dur < 0:
            raise ValueError(f"measurement_duration_s must be non-negative and finite, got {measurement_duration_s}")
        if not math.isfinite(start_t):
            raise ValueError(f"start_time must be finite, got {start_time}")

        self.arrival_mode = arrival_mode
        self.target_offered_rate = target_rate
        self.warmup_duration_s = warmup_dur
        self.measurement_duration_s = meas_dur
        self.seed = seed
        self.start_time = start_t
        self.total_duration_s = self.warmup_duration_s + self.measurement_duration_s

    @classmethod
    def from_workload_spec(
        cls,
        spec: WorkloadSpec,
        seed: Optional[int] = 42,
        start_time: float = 0.0,
    ) -> "ArrivalSchedule":
        """Instantiates an ArrivalSchedule directly from a WorkloadSpec."""
        return cls(
            arrival_mode=spec.arrival_mode,
            target_offered_rate=spec.target_offered_rate,
            warmup_duration_s=float(spec.warmup_duration_s),
            measurement_duration_s=float(spec.measurement_duration_s),
            seed=seed,
            start_time=start_time,
        )

    def __iter__(self) -> Iterator[ArrivalSlot]:
        return self.generate(self.start_time)

    def generate(self, start_time: Optional[float] = None) -> Iterator[ArrivalSlot]:
        """Yields arrival slots across warmup and measurement windows."""
        if start_time is None:
            base_time = self.start_time
        else:
            try:
                base_time = float(start_time)
            except (ValueError, TypeError) as exc:
                raise ValueError(f"start_time must be a valid float: {exc}") from exc
            if not math.isfinite(base_time):
                raise ValueError(f"start_time must be finite, got {start_time}")
        if self.total_duration_s <= 0:
            return

        if self.arrival_mode == ArrivalMode.CONSTANT:
            interval = 1.0 / self.target_offered_rate
            slot_idx = 0
            while True:
                offset_s = slot_idx * interval
                if offset_s >= self.total_duration_s - 1e-9:
                    break
                is_warmup = offset_s < (self.warmup_duration_s - 1e-9)
                yield ArrivalSlot(
                    index=slot_idx,
                    scheduled_at=base_time + offset_s,
                    is_warmup=is_warmup,
                    offset_s=offset_s,
                )
                slot_idx += 1

        elif self.arrival_mode == ArrivalMode.POISSON:
            rnd = random.Random(self.seed)
            current_offset = 0.0
            slot_idx = 0
            while True:
                delta = rnd.expovariate(self.target_offered_rate)
                current_offset += delta
                if current_offset >= self.total_duration_s:
                    break
                is_warmup = current_offset < self.warmup_duration_s
                yield ArrivalSlot(
                    index=slot_idx,
                    scheduled_at=base_time + current_offset,
                    is_warmup=is_warmup,
                    offset_s=current_offset,
                )
                slot_idx += 1

    def slots(self, start_time: Optional[float] = None) -> List[ArrivalSlot]:
        """Materializes all arrival slots into a list."""
        return list(self.generate(start_time))
