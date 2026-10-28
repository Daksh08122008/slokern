"""
Purpose: API runtime settings from environment variables.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 3, 9, 12 and DEC-0014
"""

import os
from pathlib import Path

DEFAULT_API_HOST: str = os.environ.get("SLOKERN_API_HOST", "127.0.0.1")
DEFAULT_API_PORT: int = int(os.environ.get("SLOKERN_API_PORT", "8000"))
DEFAULT_ADAPTER: str = os.environ.get("SLOKERN_ADAPTER", "local")
DEFAULT_ARTIFACTS_DIR: Path = Path(os.environ.get("SLOKERN_ARTIFACTS_DIR", "artifacts"))
