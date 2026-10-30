"""
Purpose: `slokern credentials`: secure inspection, setup instructions, and authentication validation.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 4, 11, 12 and DEC-0014
"""

import argparse
import sys
from typing import Optional
import urllib.error
import urllib.parse
import urllib.request

from slokern.common.security import sanitize_credentials
from slokern.config.secrets import (
    SecretSourceStatus,
    get_secret_status,
    load_runtime_secrets,
    setup_credentials_help,
    validate_endpoint_url,
)


def credentials_status_command(
    secrets_file: Optional[str] = None,
    json_output: bool = False,
) -> int:
    """
    Displays credential configuration status without revealing secret values, hashes, or lengths.
    """
    load_runtime_secrets(force_reload=True, secrets_file=secrets_file)

    key_res = get_secret_status("NEBIUS_API_KEY", secrets_file=secrets_file)
    url_res = get_secret_status("NEBIUS_BASE_URL", secrets_file=secrets_file)
    model_res = get_secret_status("NEBIUS_MODEL_ID", secrets_file=secrets_file)

    if json_output:
        import json
        payload = {
            "NEBIUS_API_KEY": key_res.to_dict(),
            "NEBIUS_BASE_URL": url_res.to_dict(),
            "NEBIUS_MODEL_ID": model_res.to_dict(),
        }
        print(json.dumps(payload, indent=2))
        return 0 if key_res.is_available else 1

    print("======================================================================")
    print("SLOKern Credential & Secret Configuration Status")
    print("======================================================================")
    print(f"  Target Secret:       NEBIUS_API_KEY")
    print(f"  Status:              {key_res.status.value}")
    print(f"  Discovered Source:   {key_res.source_description}")
    print(f"  Available:           {'YES' if key_res.is_available else 'NO'}")
    if key_res.warning:
        print(f"  Warning / Note:      {key_res.warning}")

    print("\n  Related Settings:")
    print(f"  NEBIUS_BASE_URL:     {url_res.status.value} ({url_res.source_description})")
    print(f"  NEBIUS_MODEL_ID:     {model_res.status.value} ({model_res.source_description})")
    print("======================================================================")

    if not key_res.is_available:
        print("\n[ACTION REQUIRED] Run 'slokern credentials setup' for configuration instructions.", file=sys.stderr)
        return 1
    return 0


def credentials_setup_command(source: Optional[str] = None) -> int:
    """
    Prints safe setup instructions for configuring credentials without logging or storing secrets.
    """
    instructions = setup_credentials_help(source=source)
    print(instructions)
    return 0


def credentials_validate_command(
    offline: bool = False,
    secrets_file: Optional[str] = None,
    timeout_s: float = 15.0,
) -> int:
    """
    Performs minimal authentication validation against the Nebius serving endpoint.
    Distinguishes:
      - MISSING_CREDENTIALS
      - INVALID_CREDENTIALS (HTTP 401)
      - INACCESSIBLE_MODEL (HTTP 404)
      - RATE_LIMIT_OR_QUOTA (HTTP 429)
      - NETWORK_FAILURE (URLError, timeout)
      - AUTHENTICATED_SUCCESS (HTTP 200)
    Offline mode validates format and scheme without contacting remote servers.
    """
    discovered = load_runtime_secrets(force_reload=True, secrets_file=secrets_file)
    api_key = discovered.get("NEBIUS_API_KEY", "")

    if not api_key or not api_key.strip():
        print("[FAIL] Missing Credentials: NEBIUS_API_KEY is not configured in any approved source.", file=sys.stderr)
        print("Run 'slokern credentials setup' to see how to configure credentials securely.", file=sys.stderr)
        return 1

    base_url = discovered.get("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1").rstrip("/")
    is_valid_url, url_err = validate_endpoint_url(base_url)
    if not is_valid_url:
        print(f"[FAIL] Invalid Base URL: {url_err}", file=sys.stderr)
        return 1

    if offline:
        print("[OK] Offline Validation Passed: Credential format and endpoint scheme verified.")
        return 0

    print(f"Validating authentication against endpoint: {urllib.parse.urlparse(base_url).netloc}...")
    models_endpoint = f"{base_url}/models"
    headers = {
        "Authorization": f"Bearer {api_key.strip()}",
        "User-Agent": "SLOKern-Credential-Validator/1.0",
        "Accept": "application/json",
    }

    req = urllib.request.Request(models_endpoint, headers=headers, method="GET")

    try:
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            if resp.status == 200:
                print("[OK] Authentication Successful: Remote provider accepted credentials (HTTP 200 OK).")
                return 0
            else:
                print(f"[FAIL] Unexpected response status: HTTP {resp.status}", file=sys.stderr)
                return 1

    except urllib.error.HTTPError as exc:
        sanitized_reason = sanitize_credentials(str(exc.reason))
        if exc.code == 401:
            print("[FAIL] Authentication Failed (HTTP 401 Unauthorized): Invalid, expired, or unauthorized API key.", file=sys.stderr)
            print("Remediation: Verify your NEBIUS_API_KEY in Nebius Cloud Console.", file=sys.stderr)
        elif exc.code == 403:
            print("[FAIL] Access Forbidden (HTTP 403 Forbidden): Credentials lack permission for requested resource.", file=sys.stderr)
        elif exc.code == 404:
            print("[FAIL] Resource Not Found (HTTP 404): Models catalog endpoint not found on this base URL.", file=sys.stderr)
        elif exc.code == 429:
            print("[FAIL] Rate Limited / Quota Exceeded (HTTP 429): Endpoint rate limit or quota reached.", file=sys.stderr)
        elif exc.code >= 500:
            print(f"[FAIL] Provider Server Error (HTTP {exc.code} {sanitized_reason}): Nebius service temporarily unavailable.", file=sys.stderr)
        else:
            print(f"[FAIL] Provider returned HTTP {exc.code}: {sanitized_reason}", file=sys.stderr)
        return 1

    except (urllib.error.URLError, TimeoutError) as exc:
        err_msg = sanitize_credentials(str(exc))
        if "timed out" in err_msg.lower() or isinstance(exc, TimeoutError):
            print(f"[FAIL] Connection Timed Out ({timeout_s}s): Could not reach endpoint.", file=sys.stderr)
        else:
            print(f"[FAIL] Network Connection Failure: {err_msg}", file=sys.stderr)
        return 1

    except Exception as exc:
        print(f"[FAIL] Validation error: {sanitize_credentials(str(exc))}", file=sys.stderr)
        return 1
