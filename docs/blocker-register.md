# SLOKern Blocker & Risk Register

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Authority:** Aligned with `AGENTS.md`, `ROADMAP.md`, `docs/architecture.md`, `docs/final-integration-plan.md`, and `docs/hackathon-compliance.md`.  
> **Status:** AUTHORITATIVE AUDIT & RESOLUTION RECORD  
> **Date:** October 30, 2026  
> **Accountable Owner:** Rajdeep (Sole Technical Owner & Integration Authority)

---

## 1. Blocker Status Taxonomy

Every blocker is tracked with one of six canonical statuses:
- `RESOLVED`: Root cause addressed in code, covered by automated test suites, and verified.
- `EXTERNAL ACTION REQUIRED`: Local implementation complete; gated solely on external credential provisioning or operator action.
- `PROVIDER LIMITATION`: Inherent technical constraint of third-party API or cloud service (honestly disclosed; not bypassed with synthetic claims).
- `ENVIRONMENT LIMITATION`: Host operating system or platform sandbox constraint.
- `ACCEPTED LIMITATION`: Documented deliberate engineering trade-off for MVP scope.
- `OPEN`: Unresolved issue currently lacking fix or mitigation.

---

## 2. Comprehensive Register Table

| Blocker ID | Severity | Status | Title & Summary | Affected Subsystems / Files | Root Cause | Implemented Fix & Mitigation | Automated Test Evidence | External Action Needed? |
|---|---|---|---|---|---|---|---|---|
| **BLK-01** | High | `RESOLVED` | Shared contract schema drift | `src/slokern/contracts/`, `schemas/*.json` | Generated JSON schemas diverged from Pydantic v2 models. | Enforced strict Pydantic v2 schemas; regenerated schemas with `gen_contracts.py`. | `tests/contract/test_generated_files_current.py`, `tests/contract/test_schemas.py` (100% pass) | None |
| **BLK-02** | High | `RESOLVED` | Golden fixture calculation & provenance audit | `fixtures/`, `tests/contract/test_fixtures_validate.py` | Need deterministic validation of unaggregated trace fixtures against metrics engine. | Audited hand-calculated fixtures and verified formula consistency. | `tests/contract/test_fixtures_validate.py` (8 tests pass) | None |
| **BLK-03** | Critical | `RESOLVED` | Verification run independence | `src/slokern/core/verification/protocol.py`, `tests/contract/test_verification_independence.py` | Verification rerun must never reuse search run ID or metrics. | Enforced fresh run ID generation, drift evaluation policy, and independent re-execution. | `tests/contract/test_verification_independence.py` (17 tests pass) | None |
| **BLK-04** | Critical | `PARTIAL` (Local) / `EXTERNAL ACTION REQUIRED` (Live) | Nebius credential management & automatic discovery | `src/slokern/config/secrets.py`, `src/slokern/cli/commands/credentials.py`, `factory.py`, `nebius.py`, `main.py` | Startup discovery and diagnostics exist, but Windows ACL privacy for local secret files is not validated, and no authorized provider credential is available for live authentication evidence. | Environment takes precedence; only an explicit file path (`SLOKERN_SECRETS_FILE` or command option) is read; POSIX files with group/other access are rejected; optional OS keyring is third. Added status/setup/validate commands and redacted reporting. | `pytest tests/unit/config/test_secrets.py tests/unit/cli/commands/test_credentials.py tests/unit/cli/commands/test_smoke_test.py tests/unit/cli/test_main.py tests/unit/engine/serving/test_nebius.py -q`: 62 passed, 1 skipped (2026-10-30). | Provision an authorized credential securely. Until Windows ACL validation exists, use process environment or a supported OS credential store on Windows; do not rely on a local secret file there. Live auth remains NOT RUN. |
| **BLK-05** | High | `RESOLVED` | Loadgen saturation and skew handling | `src/slokern/engine/loadgen/runner.py`, `recorder.py` | Request generation in main process causes GIL contention and inaccurate timing. | Subprocess isolation for worker execution; JSONL unaggregated event recorder. | `tests/unit/engine/loadgen/` (34 tests pass) | None |
| **BLK-06** | High | `RESOLVED` | Decision drift and tie-breaking determinism | `src/slokern/core/verification/compare.py`, `src/slokern/core/search/rank.py` | Metric jitter between search and verification could cause indeterminate verdicts. | Defined explicit DriftPolicy (+15% latency, -15% throughput, +0.01 error rate). Deterministic tie-breaking by candidate ID. | `tests/unit/core/verification/test_compare.py`, `test_drift_boundary.py` (21 tests pass) | None |
| **BLK-07** | Medium | `RESOLVED` | Visual labeling of simulated data | `frontend/src/`, `ReportArtifact` | Simulated runs must never be misrepresented as live cloud runs. | Enforced persistent `DEMO DATA` banners on fake adapter in UI and reports. | `tests/contract/test_report_schemas.py`, `npm run build` | None |
| **BLK-08** | High | `RESOLVED` | Control plane HTTP/SSE server | `src/slokern/api/app.py`, `routes/` | Need zero-dependency control plane matching CLI functionality. | Implemented stdlib HTTP and SSE server supporting all 6 lifecycle endpoints. | `tests/integration/test_frontend_api_integration.py` | None |
| **BLK-09** | Medium | `RESOLVED` | Dual-mode cost policy disclosure | `src/slokern/core/cost/` | Fabricating cloud GPU pricing violates evidence integrity. | Implemented dual-mode cost engine: Mode A (authoritative provider rates) vs Mode B (GPU-seconds proxy). Declares "unavailable" when unverified. | `tests/unit/core/` cost tests | None |
| **BLK-10** | High | `RESOLVED` | Zero-dependency secret scanner | `scripts/scan_secrets.py`, `tests/unit/test_scan_secrets.py` | Credentials could accidentally be committed or serialized into artifacts. | Added regex-based scanner scanning tracked files and artifacts for tokens, bearer headers, and private keys. | `scripts/scan_secrets.py` exits 0; `tests/unit/test_scan_secrets.py` passes | None |
| **BLK-11** | Medium | `RESOLVED` | Solo ownership governance alignment | `docs/ownership.md`, `AGENTS.md` Section 13 | Multi-contributor assignments lingered after solo model transition. | Reconciled all documentation and subsystem ownership matrices to Rajdeep. | Documentation audit | None |
| **BLK-12** | High | `RESOLVED` | Audit report builder linking physical traces | `src/slokern/engine/reporting/` | Reports must be traceable to disk `.jsonl` files. | Built canonical ReportArtifact and Markdown dossier linking each metric to physical trace paths. | `tests/unit/engine/reporting/` | None |
| **BLK-13** | Low | `ENVIRONMENT LIMITATION` | Windows sandbox loopback socket constraint | `tests/unit/engine/loadgen/test_runner.py` | Windows sandbox blocks loopback TCP socket binding (`[WinError 10013]`). | Added `requires_subprocess_socket` skipif marker; passes in standard environment. | Full suite execution | None |
| **BLK-14** | High | `RESOLVED` | CLI command suite completion | `src/slokern/cli/main.py`, `commands/` | CLI required `smoke-test`, `optimize`, `verify`, `report`, `validate`, `credentials`, `serve`. | Implemented all commands with unified argument parsing, exit codes, and help text. | `tests/unit/cli/` (39 tests pass) | None |
| **BLK-15** | High | `RESOLVED` | Strict 6-run benchmark budget enforcement | `src/slokern/core/search/budget.py`, `grid.py` | Search could overrun budget and starve verification rerun. | Verified BudgetLimiter hard-caps search runs at 5, reserving run 6 for independent verification. Fails closed on budget exhaustion. | `tests/unit/core/search/test_budget.py` (15 tests pass) | None |
| **BLK-16** | Medium | `RESOLVED` | Frontend TypeScript / Vite compilation | `frontend/` | UI compilation and contract types needed synchronization. | Synchronized contract types, fixed imports, verified clean build with 0 warnings. | `npm run build` exits 0 (2.02s) | None |
| **BLK-17** | Critical | `PROVIDER LIMITATION` | Nebius Token Factory dynamic serving-engine parameters | `src/slokern/core/search/grid.py`, `nebius.py` | OpenAI-compatible Token Factory endpoint (`https://api.tokenfactory.nebius.com/v1`) accepts request-level params (`max_tokens`, `temperature`) but does not apply or expose server startup flags (`max_num_batched_tokens`, `max_num_seqs`). | Added `validate_search_capabilities()` gating in search controller. Halts optimization campaign on live managed endpoint to prevent false optimization claims. Track 1 deployment strategy: live baseline and independent verification on Token Factory; 2x2 grid search on fake adapter with `DEMO DATA` labeling. | `tests/unit/core/search/test_grid.py` (tests validate capability preflight gating) | If GPU VM becomes available, deploy containerized vLLM for dynamic restarts. |
| **BLK-18** | Medium | `PARTIAL` | Operational smoke/preflight evidence | `scripts/preflight.py`, `scripts/smoke.py`, `src/slokern/cli/commands/smoke_test.py` | Scripts had been incomplete; local behavior is now implemented but live artifact persistence and provider/model confirmation have not run here. | Smoke operation bounds one request and writes a sanitized artifact; preflight audits storage, credentials, and adapter readiness. | Targeted mocked suite is included in the 62-pass credential/smoke test run (2026-10-30); live run NOT RUN. | Run one authorized live smoke after credential provisioning; inspect persisted artifact. |
| **BLK-19** | Low | `ACCEPTED LIMITATION` | Prompt token estimation uses whitespace split | `src/slokern/engine/loadgen/runner.py` | Accurate Nemotron BPE token counting requires heavy HuggingFace `transformers` dependency. | Whitespace splitting used as lightweight fallback; exact output tokens captured from provider response; limitation disclosed in ReportArtifact. | `tests/unit/engine/loadgen/` | Optional: install `transformers` for local exact BPE token counts. |

---

## 3. Immediate Action Plan for Live Campaign

1. **Verify Credentials Without Secret Leakage:**
   ```powershell
   python -m slokern.cli credentials status
   python -m slokern.cli credentials validate --offline
   ```
2. **Execute Live Preflight Smoke Test (Gate 1 - Consumes ~16 output tokens):**
   ```powershell
   python -m slokern.cli smoke-test --adapter nebius --model nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B --stream
   ```
3. **Execute Offline Verified Demo Campaign (Zero Cloud Cost):**
   ```powershell
   python -m slokern.cli optimize fixtures/workloads/smoke_experiment.json --adapter fake --verify
   ```
4. **Compile Canonical Audit Report:**
   ```powershell
   python -m slokern.cli report artifacts/experiments/exp-smoke-01
   ```
5. **Run Secret Hygiene Scanner:**
   ```powershell
   python scripts/scan_secrets.py --check
   ```
