#!/usr/bin/env python3
"""
Purpose: Operational script executing exactly one bounded smoke test probe against serving path.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 6, 10, DEC-0014, and hackathon preflight requirements.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from slokern.cli.commands.smoke_test import smoke_test_command
from slokern.config.secrets import load_runtime_secrets


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SLOKern Smoke Test Runner: executes exactly one bounded preflight probe and persists evidence."
    )
    parser.add_argument(
        "--adapter",
        choices=["local", "nebius", "fake"],
        default=None,
        help="Serving adapter backend (default: local or SLOKERN_ADAPTER).",
    )
    parser.add_argument("--model", help="Target model identifier.")
    parser.add_argument("--base-url", help="Endpoint base URL.")
    parser.add_argument(
        "--prompt",
        default="SLOKern preflight smoke test probe.",
        help="Probe prompt text.",
    )
    parser.add_argument(
        "--artifact-path",
        default="artifacts/smoke_test_result.json",
        help="Path to persist machine-readable result artifact (default: artifacts/smoke_test_result.json).",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Execute probe in streaming mode to verify TokenChunk streaming and measure TTFT.",
    )

    args = parser.parse_args()

    # Bootstrap secrets early
    load_runtime_secrets()

    return smoke_test_command(
        adapter=args.adapter,
        model=args.model,
        base_url=args.base_url,
        prompt=args.prompt,
        artifact_path=args.artifact_path,
        stream=args.stream,
    )


if __name__ == "__main__":
    sys.exit(main())
