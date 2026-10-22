"""
Purpose: Unit tests for engine/runner/cancel.
Owner: Rajdeep (Architecture & Verification)
"""

import pytest
from slokern.engine.runner.cancel import CancellationToken, RunCancelledError


def test_cancellation_token_initial_state():
    token = CancellationToken()
    assert token.is_cancelled is False
    # check_cancelled should not raise
    token.check_cancelled()


def test_cancellation_token_cancel():
    token = CancellationToken()
    token.cancel()
    assert token.is_cancelled is True
    with pytest.raises(RunCancelledError, match="Execution was cancelled"):
        token.check_cancelled()


def test_cancellation_token_callbacks():
    token = CancellationToken()
    called = []

    def cb1():
        called.append("cb1")

    def cb2():
        called.append("cb2")

    token.register_callback(cb1)
    token.register_callback(cb2)
    assert called == []

    token.cancel()
    assert called == ["cb1", "cb2"]

    # Calling cancel again should be idempotent
    token.cancel()
    assert called == ["cb1", "cb2"]


def test_callback_registered_after_cancel_runs_immediately():
    token = CancellationToken()
    token.cancel()

    called = []
    token.register_callback(lambda: called.append("late"))
    assert called == ["late"]


def test_callback_exception_does_not_block_others():
    token = CancellationToken()
    called = []

    def faulty_cb():
        raise RuntimeError("boom")

    def normal_cb():
        called.append("normal")

    token.register_callback(faulty_cb)
    token.register_callback(normal_cb)

    token.cancel()
    assert called == ["normal"]
    assert token.is_cancelled is True
