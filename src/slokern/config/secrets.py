"""
Purpose: Automatic discovery, loading, and safe status reporting for runtime secrets.
Owner: Rajdeep
Authority: Aligned with AGENTS.md Section 1, 4, 12, DEC-0014, and hackathon credential guidelines.
"""

from dataclasses import dataclass
from enum import Enum
import json
import os
from pathlib import Path
import stat
import sys
from typing import Dict, List, Optional, Set, Tuple
import urllib.parse

from slokern.common.security import sanitize_credentials


class SecretSourceStatus(str, Enum):
    """Safe status categories for runtime secret availability. Discloses zero secret values."""
    AVAILABLE_FROM_PROCESS_ENV = "AVAILABLE_FROM_PROCESS_ENV"
    AVAILABLE_FROM_LOCAL_SECRET_FILE = "AVAILABLE_FROM_LOCAL_SECRET_FILE"
    AVAILABLE_FROM_CREDENTIAL_STORE = "AVAILABLE_FROM_CREDENTIAL_STORE"
    MISSING = "MISSING"
    INVALID_CONFIGURATION = "INVALID_CONFIGURATION"


@dataclass(frozen=True)
class SecretStatusResult:
    """Diagnostic outcome for a credential key without exposing sensitive data."""
    key: str
    status: SecretSourceStatus
    source_description: str
    is_available: bool
    warning: Optional[str] = None

    def to_dict(self) -> Dict[str, object]:
        return {
            "key": self.key,
            "status": self.status.value,
            "source_description": self.source_description,
            "is_available": self.is_available,
            "warning": self.warning,
        }


_SECRETS_CACHE: Optional[Dict[str, str]] = None


# Known placeholder fragments that indicate an unconfigured template rather than a valid secret
_PLACEHOLDER_MARKERS = {
    "",
    "your-nebius-api-key",
    "your_nebius_api_key",
    "placeholder",
    "<api_key>",
    "<your_api_key>",
    "sk-placeholder",
    "nvapi-placeholder",
}



def is_placeholder_secret(value: Optional[str]) -> bool:
    """Returns True if the string is empty or a known placeholder token."""
    if not value or not isinstance(value, str):
        return True
    cleaned = value.strip().strip("'\"").strip()
    if not cleaned:
        return True
    if cleaned.lower() in _PLACEHOLDER_MARKERS:
        return True
    if cleaned.startswith("<") and cleaned.endswith(">"):
        return True
    return False


def validate_endpoint_url(url: str, allow_insecure_http_override: bool = False) -> Tuple[bool, Optional[str]]:
    """
    Validates that serving endpoints use HTTPS by default.
    Allows HTTP only for local loopback development (localhost, 127.0.0.1, ::1) or when
    SLOKERN_ALLOW_INSECURE_HTTP is explicitly set to 1.
    Rejects missing hosts, invalid ports, and URL credentials.
    """
    if not url or not isinstance(url, str) or not url.strip():
        return False, "Endpoint URL is empty or invalid"
    try:
        parsed = urllib.parse.urlparse(url.strip())
    except Exception as exc:
        return False, f"Failed to parse endpoint URL: {sanitize_credentials(str(exc))}"

    if parsed.scheme not in ("http", "https"):
        return False, f"Invalid scheme '{parsed.scheme}': must be https (or http for local loopback)"

    if not parsed.netloc or not parsed.hostname:
        return False, "Endpoint URL must contain a valid host/domain"

    try:
        _ = parsed.port
    except ValueError:
        return False, f"Endpoint URL contains invalid port in '{parsed.netloc}'"

    if parsed.username or parsed.password or "@" in parsed.netloc:
        return False, "URL credentials (userinfo) are strictly prohibited in endpoint URL"

    if parsed.scheme == "http":
        hostname = (parsed.hostname or "").lower()
        is_loopback = hostname in ("localhost", "127.0.0.1", "::1")
        env_override = os.environ.get("SLOKERN_ALLOW_INSECURE_HTTP", "0").strip() == "1"
        if not is_loopback and not allow_insecure_http_override and not env_override:
            return False, f"Insecure HTTP scheme rejected for remote endpoint '{hostname}'. Use HTTPS."

    return True, None


def _check_file_permissions(filepath: Path) -> Tuple[bool, Optional[str]]:
    """
    Checks file permissions and path safety for local secrets file.
    Rejects directories, guards against invalid symlinks, and checks POSIX file permissions.
    """
    try:
        if filepath.is_dir():
            return False, f"Target secrets path '{filepath}' is a directory, not a regular file"
        if filepath.is_symlink():
            try:
                resolved = filepath.resolve(strict=True)
                if not stat.S_ISREG(resolved.stat().st_mode):
                    return False, f"Target secrets symlink '{filepath}' points to a non-regular file"
            except (OSError, RuntimeError) as exc:
                return False, f"Invalid symlink: {sanitize_credentials(str(exc))}"

        st = filepath.stat()
    except OSError as exc:
        return False, f"Cannot access file: {sanitize_credentials(str(exc))}"

    if not stat.S_ISREG(st.st_mode):
        return False, "Target secrets path is not a regular file"

    # POSIX permissions check. A configured secrets file is accepted only when
    # it is private to the current account; a warning still permits accidental
    # exposure and is therefore not sufficient for an API credential.
    if os.name == "posix":
        mode = st.st_mode
        if (mode & 0o077) != 0:
            return False, f"Insecure file permissions ({oct(mode & 0o777)}): secrets file is accessible by group/others. Restrict it with chmod 600 {filepath.name}"

    return True, None


def get_candidate_secret_files(explicit_file: Optional[Path | str] = None) -> List[Path]:
    """Returns candidate paths for local secrets file in priority order."""
    candidates: List[Path] = []

    # 1. Explicitly passed parameter
    if explicit_file:
        candidates.append(Path(explicit_file))

    # 2. Environment variable SLOKERN_SECRETS_FILE
    env_file = os.environ.get("SLOKERN_SECRETS_FILE")
    if env_file and env_file.strip():
        candidates.append(Path(env_file.strip()))

    return candidates


def _parse_secrets_file(filepath: Path) -> Dict[str, str]:
    """
    Safely parses KEY=VALUE lines or JSON content from a secrets file.
    Never logs or leaks the contents.
    Returns all non-empty parsed key/value pairs (including placeholders).
    """
    if not filepath.exists() or not filepath.is_file():
        return {}

    secrets: Dict[str, str] = {}
    try:
        text = filepath.read_text(encoding="utf-8")
    except Exception:
        return {}

    stripped = text.strip()
    if not stripped:
        return {}

    # Try JSON format first if starts with {
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            data = json.loads(stripped)
            if isinstance(data, dict):
                for k, v in data.items():
                    if isinstance(v, str) and v.strip():
                        secrets[k.strip()] = v.strip()
                return secrets
        except Exception:
            pass

    # Line-by-line KEY=VALUE format
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        # Support shell "export KEY=VALUE" syntax
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" in line:
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip()
            # If quoted, extract quoted content; if not quoted, strip inline comments (#...)
            if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                val = val[1:-1].strip()
            else:
                if "#" in val:
                    val = val.split("#", 1)[0].strip()
            if key and val:
                secrets[key] = val

    return secrets


def _read_from_keyring(service_name: str = "slokern", username: str = "nebius_api_key") -> Optional[str]:
    """
    Attempts to read secret from OS credential store via keyring without throwing errors
    if keyring is missing or unsupported.
    """
    try:
        import keyring
        val = keyring.get_password(service_name, username)
        if val and not is_placeholder_secret(val):
            return val.strip()
    except Exception:
        pass
    return None


def get_secret_status(
    secret_key: str = "NEBIUS_API_KEY",
    secrets_file: Optional[Path | str] = None,
) -> SecretStatusResult:
    """
    Checks the status of a specific secret key across supported sources in priority order.
    NEVER discloses secret values, prefixes, suffixes, lengths, or hashes.
    """
    # 1. Process environment variable (Priority 1)
    env_val = os.environ.get(secret_key)
    if env_val is not None and env_val.strip():
        if is_placeholder_secret(env_val):
            return SecretStatusResult(
                key=secret_key,
                status=SecretSourceStatus.INVALID_CONFIGURATION,
                source_description=f"Process environment variable '{secret_key}' (contains placeholder/empty value)",
                is_available=False,
                warning=f"Environment variable '{secret_key}' is set to a placeholder or empty value.",
            )
        return SecretStatusResult(
            key=secret_key,
            status=SecretSourceStatus.AVAILABLE_FROM_PROCESS_ENV,
            source_description=f"Process environment variable '{secret_key}'",
            is_available=True,
        )

    # 2. Local secrets file (Priority 2)
    candidates = get_candidate_secret_files(secrets_file)
    for path in candidates:
        try:
            resolved = path.resolve()
            if resolved.exists():
                if resolved.is_dir():
                    return SecretStatusResult(
                        key=secret_key,
                        status=SecretSourceStatus.INVALID_CONFIGURATION,
                        source_description=f"Secrets path '{resolved.name}'",
                        is_available=False,
                        warning=f"Configured secrets path '{resolved}' is a directory, not a regular file.",
                    )
                is_valid, warning = _check_file_permissions(resolved)
                if not is_valid:
                    return SecretStatusResult(
                        key=secret_key,
                        status=SecretSourceStatus.INVALID_CONFIGURATION,
                        source_description=f"Local secrets file '{resolved.name}'",
                        is_available=False,
                        warning=warning or "Invalid file permissions or unsupported file type.",
                    )
                file_secrets = _parse_secrets_file(resolved)
                if secret_key in file_secrets:
                    val = file_secrets[secret_key]
                    if is_placeholder_secret(val):
                        return SecretStatusResult(
                            key=secret_key,
                            status=SecretSourceStatus.INVALID_CONFIGURATION,
                            source_description=f"Local secrets file '{resolved.name}' (contains placeholder)",
                            is_available=False,
                            warning=f"Secrets file '{resolved.name}' contains a placeholder value for '{secret_key}'. Replace it with your actual key.",
                        )
                    return SecretStatusResult(
                        key=secret_key,
                        status=SecretSourceStatus.AVAILABLE_FROM_LOCAL_SECRET_FILE,
                        source_description=f"Local secrets file '{resolved.name}'",
                        is_available=True,
                        warning=warning,
                    )
        except Exception:
            continue

    # 3. OS Credential Store (Priority 3)
    keyring_val = _read_from_keyring("slokern", secret_key.lower())
    if keyring_val:
        return SecretStatusResult(
            key=secret_key,
            status=SecretSourceStatus.AVAILABLE_FROM_CREDENTIAL_STORE,
            source_description="Operating system credential store (keyring)",
            is_available=True,
        )

    return SecretStatusResult(
        key=secret_key,
        status=SecretSourceStatus.MISSING,
        source_description="None (checked process environment, local secret files, and OS credential store)",
        is_available=False,
        warning=f"Credential '{secret_key}' not found in any approved source.",
    )


def clear_secrets_cache() -> None:
    """Clears in-memory secrets cache."""
    global _SECRETS_CACHE
    _SECRETS_CACHE = None


def load_runtime_secrets(
    force_reload: bool = False,
    secrets_file: Optional[Path | str] = None,
) -> Dict[str, str]:
    """
    Discovers and injects runtime secrets into os.environ without overwriting existing
    non-empty environment variables. Discovered values remain in process environment
    for the process lifetime; a subsequent process start performs fresh discovery.
    Supported discovered keys:
      - NEBIUS_API_KEY
      - NEBIUS_BASE_URL
      - NEBIUS_MODEL_ID
    Returns a dictionary of discovered keys (for authorized caller use).
    """
    discovered: Dict[str, str] = {}
    target_keys = ["NEBIUS_API_KEY", "NEBIUS_BASE_URL", "NEBIUS_MODEL_ID"]

    # 1. Existing process environment takes precedence (Priority 1)
    for k in target_keys:
        val = os.environ.get(k)
        if val and not is_placeholder_secret(val):
            discovered[k] = val.strip()

    # 2. Local secrets file for any missing keys (Priority 2)
    missing_keys = [k for k in target_keys if k not in discovered]
    if missing_keys:
        candidates = get_candidate_secret_files(secrets_file)
        for path in candidates:
            try:
                resolved = path.resolve()
                if resolved.exists() and resolved.is_file():
                    is_valid, _ = _check_file_permissions(resolved)
                    if not is_valid:
                        continue
                    file_secrets = _parse_secrets_file(resolved)
                    for k in missing_keys:
                        if k in file_secrets and k not in discovered:
                            val = file_secrets[k]
                            if not is_placeholder_secret(val):
                                discovered[k] = val
                                # Inject into process environment
                                os.environ[k] = val
                    # Check if all keys found
                    if all(k in discovered for k in target_keys):
                        break
            except Exception:
                continue

    # 3. OS credential store for NEBIUS_API_KEY if still missing (Priority 3)
    if "NEBIUS_API_KEY" not in discovered:
        keyring_val = _read_from_keyring("slokern", "nebius_api_key")
        if keyring_val:
            discovered["NEBIUS_API_KEY"] = keyring_val
            os.environ["NEBIUS_API_KEY"] = keyring_val

    # Validate base_url if present
    if "NEBIUS_BASE_URL" in discovered:
        is_valid_url, url_err = validate_endpoint_url(discovered["NEBIUS_BASE_URL"])
        if not is_valid_url:
            # Do not use invalid URL
            discovered.pop("NEBIUS_BASE_URL", None)

    return discovered


def validate_required_secrets(
    required_keys: Optional[List[str]] = None,
    secrets_file: Optional[Path | str] = None,
) -> Tuple[bool, Dict[str, SecretStatusResult]]:
    """
    Validates availability of required credentials.
    Returns (all_available_bool, dict_of_status_results).
    """
    if required_keys is None:
        required_keys = ["NEBIUS_API_KEY"]

    # Trigger bootstrap discovery first
    load_runtime_secrets(force_reload=True, secrets_file=secrets_file)

    results: Dict[str, SecretStatusResult] = {}
    all_ok = True

    for k in required_keys:
        res = get_secret_status(k, secrets_file=secrets_file)
        results[k] = res
        if not res.is_available:
            all_ok = False

    return all_ok, results


def setup_credentials_help(source: Optional[str] = None) -> str:
    """Returns safe, platform-specific guidance for configuring secrets without exposing keys."""
    home_dir = Path.home()
    secrets_file_example = home_dir / ".slokern" / "secrets"

    return f"""======================================================================
SLOKern Secure Credential Setup Instructions
======================================================================
Nebius credentials are automatically discovered at startup from:
  1. Process environment variables (Priority 1)
  2. Local restricted secrets file (Priority 2)
  3. Operating system credential store / keyring (Priority 3)

[Option A: Environment Variable (Recommended for CI / Active Terminal)]
  - Windows PowerShell:
      $env:NEBIUS_API_KEY = "your-actual-api-key"
  - Linux / macOS (bash / zsh):
      export NEBIUS_API_KEY="your-actual-api-key"

[Option B: Local Secrets File (Recommended for Persistent Local Dev)]
  Create a restricted file outside source control:
    File location: {secrets_file_example}
    Contents:
      NEBIUS_API_KEY=your-actual-api-key
      NEBIUS_BASE_URL=https://api.tokenfactory.nebius.com/v1

  Linux / macOS only: restrict access, then configure the explicit file path:
      chmod 600 {secrets_file_example}
      export SLOKERN_SECRETS_FILE="{secrets_file_example}"
  Windows ACL privacy is not validated yet. Use process environment variables or an
  already-configured Windows credential store on Windows; do not use a secrets file.

[Verification]
  Check configuration status safely without printing keys:
    slokern credentials status
    slokern credentials validate
======================================================================"""
