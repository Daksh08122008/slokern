#!/usr/bin/env python3
"""
Purpose: Preflight check verifying environment, credentials, endpoint readiness, and artifact storage before benchmark execution.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 6, 10, 12 and DEC-0014
"""

import argparse
import os
from pathlib import Path
import sys
import tempfile

# Add project root to sys.path
root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "src"))

from slokern.config.secrets import (
    get_secret_status,
    load_runtime_secrets,
    validate_endpoint_url,
)
from slokern.engine.serving.base import ConfigurationError
from slokern.engine.serving.factory import create_serving_adapter


def check_artifact_directory(dirpath: Path) -> bool:
    """Verifies artifact directory exists or can be created and written to."""
    try:
        dirpath.mkdir(parents=True, exist_ok=True)
        test_file = tempfile.NamedTemporaryFile(dir=dirpath, delete=False, prefix="preflight_test_")
        test_file.write(b"ok\n")
        test_file.close()
        os.unlink(test_file.name)
        return True
    except Exception as exc:
        print(f"  [FAIL] Artifact storage check failed: {exc}", file=sys.stderr)
        return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="SLOKern Preflight Environment & Readiness Checker"
    )
    parser.add_argument(
        "--adapter",
        choices=["local", "nebius", "fake"],
        default=None,
        help="Serving adapter backend to inspect (default: local or SLOKERN_ADAPTER).",
    )
    parser.add_argument("--model", help="Target model identifier.")
    parser.add_argument("--base-url", help="Endpoint base URL.")
    parser.add_argument(
        "--artifacts-dir",
        default="artifacts",
        help="Target artifacts directory to check write permissions (default: artifacts).",
    )

    args = parser.parse_args()

    # 1. Bootstrap runtime secrets
    load_runtime_secrets()

    target_backend = (args.adapter or os.environ.get("SLOKERN_ADAPTER", "local")).strip().lower()

    print("======================================================================")
    print("SLOKern Preflight Readiness Audit")
    print("======================================================================")
    print(f"  Python Runtime:      Python {sys.version.split()[0]}")
    print(f"  Target Backend:      {target_backend}")
    print(f"  Working Directory:   {Path.cwd()}")

    all_passed = True

    # 2. Check storage
    print("\n[Gate 1: Storage & Artifact Write Permissions]")
    artifacts_path = Path(args.artifacts_dir)
    if check_artifact_directory(artifacts_path):
        print(f"  [PASS] Storage directory '{artifacts_path.resolve()}' is writeable.")
    else:
        all_passed = False

    # 3. Check Credentials (for Nebius backend)
    print("\n[Gate 2: Credential & Secret Bootstrap]")
    if target_backend == "nebius":
        status_res = get_secret_status("NEBIUS_API_KEY")
        print(f"  Secret Key:          NEBIUS_API_KEY")
        print(f"  Source Category:     {status_res.status.value}")
        print(f"  Discovered Source:   {status_res.source_description}")
        if status_res.is_available:
            print("  [PASS] Required Nebius credentials discovered and ready.")
        else:
            print("  [FAIL] NEBIUS_API_KEY missing. Run 'slokern credentials setup' to configure.", file=sys.stderr)
            all_passed = False

        raw_url = args.base_url or os.environ.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1")
        is_valid_url, url_err = validate_endpoint_url(raw_url)
        if is_valid_url:
            print(f"  [PASS] Base URL scheme verified (HTTPS): {raw_url}")
        else:
            print(f"  [FAIL] Base URL validation failed: {url_err}", file=sys.stderr)
            all_passed = False
    else:
        print(f"  [PASS] Backend '{target_backend}' does not require cloud API credentials.")

    # 4. Check Adapter Initialization & Health
    print("\n[Gate 3: Serving Adapter Readiness]")
    try:
        kwargs = {}
        if args.model:
            kwargs["model_name"] = args.model
        if args.base_url:
            kwargs["base_url"] = args.base_url
        adapter = create_serving_adapter(backend=target_backend, **kwargs)

        fp = adapter.get_environment_fingerprint()
        print(f"  Adapter Class:       {adapter.__class__.__name__}")
        print(f"  Runtime Name:        {adapter.runtime_name}")
        print(f"  Model Name:          {adapter.model_name}")
        print(f"  Endpoint Host:       {fp.get('endpoint_host', 'N/A')}")
        if fp.get("is_simulated"):
            print("  Evidence Domain:     DEMO DATA (Simulated)")
        else:
            print("  Evidence Domain:     LIVE")

        readiness_fn = getattr(adapter, "check_readiness", None)
        if callable(readiness_fn):
            readiness = readiness_fn()
            if readiness.get("ready"):
                print(f"  [PASS] Runtime is ready. Message: {readiness.get('message', 'OK')}")
            else:
                print(f"  [FAIL] Runtime is not ready: {readiness.get('error', 'Unknown error')}", file=sys.stderr)
                all_passed = False
        else:
            if adapter.health_check():
                print("  [PASS] Runtime health check returned HTTP 200.")
            else:
                print("  [FAIL] Runtime health check failed.", file=sys.stderr)
                all_passed = False

    except ConfigurationError as exc:
        print(f"  [FAIL] Configuration error: {exc}", file=sys.stderr)
        all_passed = False
    except Exception as exc:
        print(f"  [FAIL] Adapter initialization failed: {exc}", file=sys.stderr)
        all_passed = False

    print("\n======================================================================")
    if all_passed:
        print("[SUCCESS] All preflight gates PASSED. Ready for benchmark execution.")
        print("======================================================================")
        return 0
    else:
        print("[FAIL] Preflight checks failed. Review and remediate errors above before running.", file=sys.stderr)
        print("======================================================================")
        return 1


if __name__ == "__main__":
    sys.exit(main())
