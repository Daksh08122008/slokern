"""
Purpose: Removes secrets and private endpoints from outputs.
Owner: Rajdeep
"""

import re
from typing import Optional


def sanitize_secret_message(message: str, secret_key: Optional[str] = None) -> str:
    """
    Redacts API keys, Bearer tokens, and secrets from error messages and logs.
    Conforms to AGENTS.md Section 9 and Section 12.
    """
    if not message:
        return ""

    sanitized = str(message)
    if secret_key and len(secret_key) >= 4:
        sanitized = sanitized.replace(secret_key, "***REDACTED***")

    # Mask Authorization Bearer tokens
    sanitized = re.sub(
        r"(Bearer\s+)[A-Za-z0-9_\-\.\~\+\/\=%]{6,}",
        r"\g<1>***REDACTED***",
        sanitized,
        flags=re.IGNORECASE,
    )
    # Mask API key patterns
    sanitized = re.sub(
        r"((?:api[_-]?key|token|secret|password)\s*[:=]\s*['\"]?)[A-Za-z0-9_\-\.\~\+\/\=%]{6,}(['\"]?)",
        r"\g<1>***REDACTED***\g<2>",
        sanitized,
        flags=re.IGNORECASE,
    )
    return sanitized
