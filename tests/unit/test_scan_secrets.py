import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../scripts')))
from scan_secrets import EXCLUSIONS, PATTERNS


def test_secret_scanner_synthetic_positive():
    """Asserts scanner catches fake synthetic tokens."""
    positives = [
        "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "nebius_api_key = 'nvapi-fake123456789012'",
        "api_key: 'sk-abcdef1234567890'",
        "token='secret-token-value'",
        "-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASC"
    ]

    for text in positives:
        # One of the patterns must match
        matched = False
        for p, _ in PATTERNS:
            if p.search(text):
                matched = True
                break
        assert matched is True, f"Failed to detect secret in: {text}"

def test_secret_scanner_synthetic_negative():
    """Asserts scanner passes on valid documentation and test mocks."""
    negatives = [
        "This is just normal text.",
        "DEMO DATA: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
        "api_key: '***REDACTED***'",
        "Use <api_key> in your request headers."
    ]

    for text in negatives:
        if any(excl.search(text) for excl in EXCLUSIONS):
            # Safe because it's excluded
            continue

        # Or it shouldn't match any secret pattern
        for p, _ in PATTERNS:
            assert p.search(text) is None, f"False positive match in: {text}"
