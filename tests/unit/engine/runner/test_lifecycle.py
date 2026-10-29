"""
Purpose: Unit tests for engine/runner/lifecycle.
Owner: Rajdeep (Architecture & Verification)
"""

import pytest

from slokern.contracts.enums import ExecutionStatus
from slokern.engine.runner.lifecycle import InvalidStateTransitionError, RunLifecycle


def test_initial_state_pending():
    lifecycle = RunLifecycle()
    assert lifecycle.current_state == ExecutionStatus.PENDING
    assert lifecycle.is_terminal is False
    assert len(lifecycle.history) == 1
    assert lifecycle.history[0][0] == ExecutionStatus.PENDING


def test_custom_initial_state():
    lifecycle = RunLifecycle(ExecutionStatus.RUNNING)
    assert lifecycle.current_state == ExecutionStatus.RUNNING
    assert lifecycle.is_terminal is False


def test_legal_happy_path_transitions():
    lifecycle = RunLifecycle()
    assert lifecycle.can_transition_to(ExecutionStatus.RUNNING)
    lifecycle.transition_to(ExecutionStatus.RUNNING)
    assert lifecycle.current_state == ExecutionStatus.RUNNING
    assert lifecycle.is_terminal is False

    assert lifecycle.can_transition_to(ExecutionStatus.COMPLETED)
    lifecycle.transition_to(ExecutionStatus.COMPLETED)
    assert lifecycle.current_state == ExecutionStatus.COMPLETED
    assert lifecycle.is_terminal is True
    assert len(lifecycle.history) == 3


def test_legal_failure_from_pending():
    lifecycle = RunLifecycle()
    assert lifecycle.can_transition_to(ExecutionStatus.FAILED)
    lifecycle.transition_to(ExecutionStatus.FAILED)
    assert lifecycle.current_state == ExecutionStatus.FAILED
    assert lifecycle.is_terminal is True


def test_legal_cancel_from_pending():
    lifecycle = RunLifecycle()
    assert lifecycle.can_transition_to(ExecutionStatus.CANCELLED)
    lifecycle.transition_to(ExecutionStatus.CANCELLED)
    assert lifecycle.current_state == ExecutionStatus.CANCELLED
    assert lifecycle.is_terminal is True


def test_legal_failure_from_running():
    lifecycle = RunLifecycle()
    lifecycle.transition_to(ExecutionStatus.RUNNING)
    assert lifecycle.can_transition_to(ExecutionStatus.FAILED)
    lifecycle.transition_to(ExecutionStatus.FAILED)
    assert lifecycle.current_state == ExecutionStatus.FAILED
    assert lifecycle.is_terminal is True


def test_legal_cancel_from_running():
    lifecycle = RunLifecycle()
    lifecycle.transition_to(ExecutionStatus.RUNNING)
    assert lifecycle.can_transition_to(ExecutionStatus.CANCELLED)
    lifecycle.transition_to(ExecutionStatus.CANCELLED)
    assert lifecycle.current_state == ExecutionStatus.CANCELLED
    assert lifecycle.is_terminal is True


def test_illegal_jump_from_pending_to_completed():
    lifecycle = RunLifecycle()
    assert lifecycle.can_transition_to(ExecutionStatus.COMPLETED) is False
    with pytest.raises(InvalidStateTransitionError, match="Illegal lifecycle state transition"):
        lifecycle.transition_to(ExecutionStatus.COMPLETED)


@pytest.mark.parametrize("terminal_state", [
    ExecutionStatus.COMPLETED,
    ExecutionStatus.FAILED,
    ExecutionStatus.CANCELLED,
])
def test_terminal_states_cannot_transition(terminal_state):
    lifecycle = RunLifecycle()
    if terminal_state == ExecutionStatus.COMPLETED:
        lifecycle.transition_to(ExecutionStatus.RUNNING)
        lifecycle.transition_to(ExecutionStatus.COMPLETED)
    else:
        lifecycle.transition_to(terminal_state)

    assert lifecycle.is_terminal is True

    for target in [ExecutionStatus.PENDING, ExecutionStatus.RUNNING, ExecutionStatus.COMPLETED, ExecutionStatus.FAILED, ExecutionStatus.CANCELLED]:
        if target != terminal_state:
            assert lifecycle.can_transition_to(target) is False
            with pytest.raises(InvalidStateTransitionError, match="Illegal lifecycle state transition"):
                lifecycle.transition_to(target)


def test_transition_to_self_is_noop():
    lifecycle = RunLifecycle()
    assert lifecycle.can_transition_to(ExecutionStatus.PENDING) is True
    lifecycle.transition_to(ExecutionStatus.PENDING)
    assert lifecycle.current_state == ExecutionStatus.PENDING
    assert len(lifecycle.history) == 1
