"""
Purpose: Run lifecycle state transitions and invariant enforcement.
Owner: Rajdeep (Architecture & Verification)
Authority: Aligned with docs/architecture.md Section 3, docs/decision-policy.md, and contracts/enums.py
"""

from datetime import datetime, timezone
from typing import Dict, List, Set, Tuple

from slokern.contracts.enums import ExecutionStatus


class InvalidStateTransitionError(ValueError):
    """Raised when an illegal lifecycle state transition is attempted."""
    pass


# Deterministic state machine governing valid ExecutionStatus transitions
VALID_TRANSITIONS: Dict[ExecutionStatus, Set[ExecutionStatus]] = {
    ExecutionStatus.PENDING: {
        ExecutionStatus.RUNNING,
        ExecutionStatus.CANCELLED,
        ExecutionStatus.FAILED,
    },
    ExecutionStatus.RUNNING: {
        ExecutionStatus.COMPLETED,
        ExecutionStatus.FAILED,
        ExecutionStatus.CANCELLED,
    },
    # Terminal states: no further transitions permitted
    ExecutionStatus.COMPLETED: set(),
    ExecutionStatus.FAILED: set(),
    ExecutionStatus.CANCELLED: set(),
}

TERMINAL_STATES: Set[ExecutionStatus] = {
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
}


class RunLifecycle:
    """
    Tracks and enforces legal lifecycle state transitions for a single run.
    Guarantees that terminal states cannot be escaped or overwritten.
    """

    def __init__(self, initial_state: ExecutionStatus = ExecutionStatus.PENDING) -> None:
        self._current_state: ExecutionStatus = initial_state
        now_iso = datetime.now(timezone.utc).isoformat()
        self._history: List[Tuple[ExecutionStatus, str]] = [(initial_state, now_iso)]

    @property
    def current_state(self) -> ExecutionStatus:
        """Returns the current ExecutionStatus."""
        return self._current_state

    @property
    def is_terminal(self) -> bool:
        """Returns True if the current state is terminal (COMPLETED, FAILED, CANCELLED)."""
        return self._current_state in TERMINAL_STATES

    @property
    def history(self) -> List[Tuple[ExecutionStatus, str]]:
        """Returns ordered history of (state, timestamp_iso) transitions."""
        return list(self._history)

    def can_transition_to(self, target_state: ExecutionStatus) -> bool:
        """Checks if transitioning to target_state is legal from current_state."""
        if target_state == self._current_state:
            return True
        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        return target_state in allowed

    def transition_to(self, target_state: ExecutionStatus) -> None:
        """
        Transitions to target_state if legal.
        Raises InvalidStateTransitionError if transition is illegal.
        """
        if target_state == self._current_state:
            return

        allowed = VALID_TRANSITIONS.get(self._current_state, set())
        if target_state not in allowed:
            raise InvalidStateTransitionError(
                f"Illegal lifecycle state transition from '{self._current_state.value}' "
                f"to '{target_state.value}'. Allowed transitions: {[s.value for s in allowed]}"
            )

        now_iso = datetime.now(timezone.utc).isoformat()
        self._current_state = target_state
        self._history.append((target_state, now_iso))
