"""
Purpose: Live endpoint smoke test; skipped by default.
Owner: Aman
"""

import pytest

pytestmark = pytest.mark.live


def test_smoke_live_endpoint():
    """Live endpoint smoke test. Requires live infrastructure credentials."""
    pytest.skip("Live endpoint smoke test requires configured Nebius infrastructure.")
