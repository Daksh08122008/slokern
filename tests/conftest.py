"""
Purpose: Shared pytest configuration and the `live` marker.
Owner: Rajdeep
"""

import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "live: marks tests requiring live hardware or provider endpoints (deselect with '-m \"not live\"')",
    )


def pytest_collection_modifyitems(config, items):
    for item in items:
        # Guarantee that any test under tests/live/ is tagged with the live marker
        file_path = str(item.fspath).replace("\\", "/")
        if "/live/" in file_path or file_path.endswith("test_smoke_live.py"):
            item.add_marker(pytest.mark.live)
