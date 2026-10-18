# SLOKern Engineering Ownership & Execution Model

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Reference / Governance (Transitioned to Single-Owner Execution: October 18, 2026)  
> **Sole Technical Owner & Integration Authority:** Rajdeep  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Ownership & Execution Philosophy

Starting October 18, 2026, SLOKern transitions from a distributed 5-person team sprint to **single-owner technical execution led by Rajdeep**. Rajdeep serves as the sole accountable technical owner and integration authority for all remaining architecture, engineering, validation, and hackathon submission deliverables.

### Guiding Principles for Single-Owner Execution

- **Consolidated Accountability:** A single engineer owns end-to-end coherence, eliminating coordination friction, handoff overhead, and multi-party synchronization delays.
- **Preserved Architectural Boundaries:** Consolidating execution does *not* mean collapsing architecture. The system remains a contract-driven modular monolith with explicit boundaries (`src/slokern/contracts/`).
- **Deterministic Governance:** Deterministic Python modules continue to own all metric calculations, constraint evaluations, experiment budget limits, and verification verdicts. No LLM or heuristic overrides deterministic logic.
- **Empirical Evidence First:** Every recommendation must be backed by unaggregated raw measurements (`RawRequestMeasurement`) and physical environment metadata. Offline fixtures and prototype dashboards remain strictly labeled **DEMO DATA**.
- **Historical Attribution Preserved:** The original functional workstreams and early design contributions from team members (Aman on serving, Daksh on evaluation, Adriraj on benchmarking, and Rohan on search) remain acknowledged in project records and historical ADRs.

---

## 2. Consolidated Ownership Responsibility Matrix

All core technical responsibilities are consolidated under Rajdeep:

| Area | Accountable Owner | Core Responsibilities | Key System Artifacts |
|---|---|---|---|
| **Architecture & Technical Direction** | **Rajdeep** | Scope boundaries, modular monolith design, Pydantic v2 contracts (`src/slokern/contracts/`), lifecycle state machines, and adherence to non-negotiable principles. | `docs/architecture.md`, `src/slokern/contracts/` |
| **Optimizer & Candidate Selection** | **Rajdeep** | Bounded search space definition (fixed 2×2 matrix), canonical candidate hashing, search controller (`src/slokern/core/search/`), deterministic ranking logic, and selection rationale. | `src/slokern/core/search/`, `SearchResult` |
| **Serving Integration & Infrastructure** | **Rajdeep** | Serving runtime deployment (vLLM / Nebius Cloud), serving adapter (`src/slokern/engine/serving/`), parameter read-back, preflight smoke testing, and environment fingerprinting. | `src/slokern/engine/serving/`, `docs/deployment.md` |
| **Benchmark Pipeline & Load Generation** | **Rajdeep** | Workload fixtures, arrival models (Poisson/constant), subprocess load generator (`src/slokern/engine/loadgen/`), raw event capture (`RawRequestMeasurement`), and metrics engine (`src/slokern/core/metrics/`). | `src/slokern/engine/loadgen/`, `docs/metrics.md` |
| **Verification & Evaluator Policy** | **Rajdeep** | Deterministic feasibility evaluator (`src/slokern/core/evaluator/`), reason code taxonomy, independent verification runner (`src/slokern/core/verification/`), and evidence audits. | `src/slokern/core/evaluator/`, `docs/decision-policy.md` |
| **CI, API & End-to-End Validation** | **Rajdeep** | FastAPI control plane (`src/slokern/api/`), CLI commands (`slokern verify / optimize`), contract testing, integration tests, and secret redaction. | `src/slokern/api/`, `src/slokern/cli/`, `tests/` |
| **Documentation, Demo & Submission** | **Rajdeep** | Living documentation, report generator (`src/slokern/engine/reporting/`), demo script, presentation rehearsal, tool feedback, and official hackathon submission package. | `README.md`, `ROADMAP.md`, `docs/demo-script.md` |

### Historical Workstream Context

During the initial hackathon phase (October 13–17, 2026), work was conceptualized across five functional roles:
- **Rajdeep:** Architecture, shared contracts, control plane, integration.
- **Aman:** Serving infrastructure, runtime deployment, and parameter mutability.
- **Daksh:** Feasibility evaluator, reason code taxonomy, and independent verification logic.
- **Adriraj:** Workload generation, raw timestamp capture, and metric definitions.
- **Rohan:** Search space definition, baseline search, and candidate ranking.

This historical attribution is preserved in project design records, ADRs, and commit history. Effective October 18, 2026, all active implementation and delivery duties are unified under Rajdeep.

---

## 3. Subsystem Boundaries & Invariant Guardrails

Even under a single engineer, the structural boundaries between subsystems must be strictly preserved in code. This ensures modular testability and prevents architectural decay:

### 3.1 Serving Reality vs. Optimizer Intent
- **Physical reality dictates parameters:** The serving adapter reports only what the serving runtime can actually apply, observe, and read back. The optimizer must never invent speculative knobs that cannot be actively enforced on the serving host.
- **Client vs. Engine Knobs:** Client workload settings (e.g. concurrency limits) must never be substituted for GPU serving-engine settings (e.g. batch size, KV-cache precision).

### 3.2 Benchmarking Fidelity vs. Feasibility Evaluation
- **Raw measurement capture:** The load generator records unaggregated microsecond timestamps, detects generator saturation, and calculates percentiles. It does *not* render SLO pass/fail verdicts.
- **Deterministic evaluation:** The feasibility evaluator consumes the derived `MetricSet` and applies explicit mathematical rules. It does *not* modify raw timestamps or re-aggregate percentiles.

### 3.3 Feasibility Certification vs. Candidate Ranking
- **Primacy of hard constraints:** The search controller ranks *only* candidates certified as `FEASIBLE` by the evaluator. Infeasible or inconclusive candidates are never ranked or presented as winners.
- **Deterministic objective:** Ranking follows the declared objective (Mode A verified cost or Mode B systems proxy) without ad-hoc scoring or heuristic overrides.

### 3.4 Presentation Layer vs. Backend Core
- **Contract consumption:** The frontend dashboard and CLI consume canonical schemas exported from `src/slokern/contracts/`. The UI never re-implements metric aggregation or feasibility rules.
- **Explicit labeling:** Any offline mock data or synthetic fixtures must be persistently labeled **DEMO DATA**.

---

## 4. Shared Contract Interfaces

Consolidating ownership does not change the 11 canonical Pydantic v2 data models that decouple the pipeline:

1. **`WorkloadSpec`:** Traffic profile, arrival mode, offered rate, duration, and token limits.
2. **`SLOSpec`:** Non-negotiable latency, throughput, and error rate thresholds.
3. **`CandidateConfig`:** Requested settings vs. effective read-back settings and environment fingerprint.
4. **`ExperimentSpec`:** Root document bundling workload, SLO, search space, and budget.
5. **`RunRecord`:** Single execution run metadata, execution status, and artifact paths.
6. **`RawRequestMeasurement`:** Granular, unaggregated event capture for every request.
7. **`MetricSet`:** Aggregated performance indicators with offered/achieved load and saturation flags.
8. **`FeasibilityResult`:** Constraint-by-constraint audit, reason codes, and overall verdict.
9. **`SearchResult`:** Bounded exploration history, candidate rankings, and stopping rationale.
10. **`VerificationRecord`:** Independent verification run audit, metric comparison, drift, and final verdict.
11. **`ReportArtifact`:** Self-contained, immutable bundle linking recommendation, evidence, and limitations.

---

## 5. Single-Owner Development & Validation Workflow

Without the overhead of 5-person stand-ups and branch synchronization, single-owner execution follows a disciplined, evidence-based loop:

1. **Inspect & Bound:** Before implementing any feature, inspect existing interfaces and define explicit acceptance criteria.
2. **Contract-First Changes:** When data models must evolve, update `src/slokern/contracts/` first, followed by consumers, fixtures, and contract tests.
3. **Targeted Testing:** Execute contract and unit tests (`pytest tests/contract`, `pytest tests/unit`) after each change to guarantee regression-free execution.
4. **Branch & Commit Discipline:** Maintain a clean `main` branch. Implement major milestones on task branches (e.g., `feat/fake-adapter`, `feat/nebius-smoke`) and merge only when tests pass.
5. **Zero Secrets Policy:** Enforce pre-commit scanning to prevent API tokens, credentials, or private IPs from entering source control.
6. **Traceable Artifacts:** Every benchmark run must produce self-contained JSONL and JSON artifacts on disk. Never rely on in-memory state for verification claims.

---

## 6. Related Documentation

- [System Architecture](architecture.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [Execution Roadmap (October 18–30, 2026)](../ROADMAP.md)
- [Daily Integration & Verification Checklist](integration-checklist.md)
- [Architecture Decision Log](decision-log.md)
- [ADR 0001: MVP Scope & Evidence Policy](adr/0001-mvp-scope-and-evidence.md)
