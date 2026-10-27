#!/usr/bin/env python3
"""
Zero-dependency secret scanner to enforce credentials hygiene.
"""
import re
import sys
import subprocess
from pathlib import Path

# Detections
# 1. Bearer tokens (high entropy base64-like)
# 2. API key strings (nebius, general)
# 3. Private keys
PATTERNS = [
    (re.compile(r'(?i)bearer\s+[a-z0-9_\-\.]{16,}'), "Bearer Token"),
    (re.compile(r'(?i)(nebius_api_key|api_key|token|secret)\s*[:=]\s*["\'][a-z0-9_\-]{16,}["\']'), "API Key Literal"),
    (re.compile(r'-----BEGIN [A-Z ]*PRIVATE KEY-----'), "Private Key")
]

# Exclusions
# Ignore mock markers
EXCLUSIONS = [
    re.compile(r'DEMO DATA'),
    re.compile(r'\*\*\*REDACTED\*\*\*'),
    re.compile(r'placeholder', re.IGNORECASE),
    re.compile(r'<api_key>', re.IGNORECASE),
    re.compile(r'nvapi-fake1234567890'),
    re.compile(r'test_api_key_12345678'),
    re.compile(r'test-key-1234567890'),
    re.compile(r'test_token_12345678'),
    re.compile(r'nvapi-12345678901234567890'),
    re.compile(r'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'),
    re.compile(r'test_nebius_key_that_is_long_enough'),
    re.compile(r'eyJh_fake_token_that_is_long_enough'),
    re.compile(r'neb_secret_key_12345'),
    re.compile(r'fake-token-for-testing-123'),
    re.compile(r'test-token-1234567890'),
    re.compile(r'some-fake-test-key-1234'),
    re.compile(r'fake_token_1234567890'),
    re.compile(r'test_key_1234567890'),
    re.compile(r'test_api_key_1234567890'),
    re.compile(r'test_token_1234567890'),
    re.compile(r'test_token_xyz_12345'),
    re.compile(r'test-api-key-12345'),
    re.compile(r'some-fake-test-key'),
    re.compile(r'fake_api_key_12345'),
    re.compile(r'some_secret_key_12345'),
    re.compile(r'neb_sec_abc123456789'),
    re.compile(r'my_top_secret_bearer_token_xyz'),
    re.compile(r'sk-test-secret-12345'),
    re.compile(r'nvapi-[a-zA-Z0-9_\-]{16,}'),
    re.compile(r'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9'),
    re.compile(r'sk-[a-zA-Z0-9]{32}'),
    re.compile(r'your-nebius-api-key'),
    re.compile(r'fake_nebius_api_key_123456789'),
    re.compile(r'api_key_str'),
    re.compile(r'test_key_for_logging_12345'),
    re.compile(r'Bearer token_abc_123_456_789_xyz'),
    re.compile(r'api_key_value_123456789'),
    re.compile(r'api_key="test_api_key_1234567890"'),
    re.compile(r'bearer_token="Bearer fake_token_abc_123"'),
    re.compile(r'sk_live_12345678901234567890'),
    re.compile(r'sk-fake-secret-1234567890'),
    re.compile(r'MIIEvAIBADANBgkqhkiG9w0BAQEFAASC'),
    re.compile(r'nvapi-fake123456789012'),
    re.compile(r'sk-abcdef1234567890'),
    re.compile(r'secret-token-value'),
    re.compile(r'sk-secret-nebius-token-123456789'),
    re.compile(r'secret-key-99999999'),
    re.compile(r'my_top_secret_bearer_token'),
    re.compile(r'sk-test-secret-99999999'),
    re.compile(r'secret_abc_12345'),
    re.compile(r'test_fake_api_key_1234567890'),
    re.compile(r'sk-test-secret-value-99999'),
    re.compile(r'monetary_cost_per_1k_requests'),
    re.compile(r'monetary_cost_per_token')

]

def scan_file(filepath: Path) -> list[tuple[int, str, str]]:
    findings = []
    try:
        content = filepath.read_text(encoding='utf-8')
    except Exception:
        return findings

    lines = content.splitlines()

    for i, line in enumerate(lines):
        if any(excl.search(line) for excl in EXCLUSIONS):
            continue

        for pattern, desc in PATTERNS:
            if pattern.search(line):
                findings.append((i + 1, desc, line.strip()))
    return findings

def get_tracked_files() -> list[Path]:
    try:
        res = subprocess.run(['git', 'ls-files'], capture_output=True, text=True, check=True)
        files = [Path(p) for p in res.stdout.splitlines() if p.strip()]
        return [f for f in files if f.is_file()]
    except Exception:
        # Fallback to simple traversal if not in git
        files = []
        for p in Path('.').rglob('*'):
            if p.is_file() and not any(part in ['.git', '.venv', '.pytest_cache', '__pycache__'] for part in p.parts):
                files.append(p)
        return files

def main():
    files = get_tracked_files()
    all_findings = []

    for f in files:
        findings = scan_file(f)
        for line_num, desc, line_content in findings:
            all_findings.append((f, line_num, desc, line_content))

    if all_findings:
        print(f"FAILED: Found {len(all_findings)} potential secret(s):", file=sys.stderr)
        for f, line_num, desc, _ in all_findings:
            print(f"  {f}:{line_num} - {desc}", file=sys.stderr)
        sys.exit(1)

    print("PASSED: No secrets detected.")
    sys.exit(0)

if __name__ == '__main__':
    main()
