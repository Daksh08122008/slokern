## 2024-05-18 - Secret Redaction Gaps

**Vulnerability:** Weak, duplicated regular expressions for sanitizing API keys and credentials, missing characters typical in Base64 keys, AWS tokens, etc., which could lead to partial secret leakage in logs.

**Learning:** Duplicating security logic (like secret redaction) across multiple adapter implementations leads to divergent and potentially weak security controls. The previous implementations missed valid token characters (e.g. `+`, `=`, `/`, `~`).

**Prevention:** Centralize security-critical logic into a single module (`slokern.engine.store.redact`) with comprehensive regex rules, and ensure all adapters import from this single source of truth to maintain consistent, defense-in-depth protection.
