"""
Purpose: Centralized security, credential redaction, and sanitization utilities.
Owner: Rajdeep
"""

import re
from typing import Any, Dict

from slokern.contracts.report import ReportArtifact

_TOKEN_PATTERN = re.compile(
    r'(?i)(bearer\s+[a-z0-9_\-\.]{16,})|(nebius_api_key\s*[:=]\s*["\']nvapi-[a-zA-Z0-9_\-]{16,}["\'])|((?:api_key|token|secret)\s*[:=]\s*["\'][a-zA-Z0-9_\-]{16,}["\'])|(nvapi-[a-zA-Z0-9_\-]{16,})',
    flags=re.IGNORECASE
)
_PASSWORD_URL_PATTERN = re.compile(
    r'(https?://)([^:/"\s]+):([^@/"\s]+)(@)'
)

def sanitize_credentials(text: str) -> str:
    """
    Redacts high-entropy credentials, tokens, and passwords from arbitrary text.
    Preserves diagnostic endpoints like loopback interfaces (localhost, 127.0.0.1).
    """
    text = _TOKEN_PATTERN.sub(r'***REDACTED***', text)
    text = _PASSWORD_URL_PATTERN.sub(r'\1***REDACTED***\4', text)
    return text


def _sanitize_dict(d: Dict[str, Any]) -> Dict[str, Any]:
    sanitized = {}
    for k, v in d.items():
        if isinstance(v, str):
            sanitized[k] = sanitize_credentials(v)
        elif isinstance(v, dict):
            sanitized[k] = _sanitize_dict(v)
        elif isinstance(v, list):
            sanitized[k] = [_sanitize_dict(item) if isinstance(item, dict) else (sanitize_credentials(item) if isinstance(item, str) else item) for item in v]
        else:
            sanitized[k] = v
    return sanitized


def sanitize_report_artifact(report: ReportArtifact) -> ReportArtifact:
    """
    Creates a sanitized copy of the structured report, ensuring no secrets
    are serialized to JSON. Re-validates against ReportArtifact schema.
    """
    dumped = report.model_dump()

    if "environment_fingerprint" in dumped:
        dumped["environment_fingerprint"] = _sanitize_dict(dumped["environment_fingerprint"])

    if "limitations_disclosed" in dumped:
        dumped["limitations_disclosed"] = _sanitize_dict(dumped["limitations_disclosed"])

    if "artifact_paths" in dumped:
        dumped["artifact_paths"] = {k: sanitize_credentials(v) for k, v in dumped["artifact_paths"].items()}

    return ReportArtifact.model_validate(dumped)


def assert_no_unredacted_credentials(text: str) -> None:
    """
    Raises ValueError if unmasked credentials are found in the text.
    """
    if _TOKEN_PATTERN.search(text) or _PASSWORD_URL_PATTERN.search(text):
        raise ValueError("Unredacted credentials found in text")
