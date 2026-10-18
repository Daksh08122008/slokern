# SLOKern Team Ownership & Collaboration Model

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Reference / Governance  
> **Owner:** Rajdeep (Technical Lead / Architecture)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Ownership Philosophy

SLOKern operates under a model of **single, non-overlapping accountability**. Each subsystem has one person accountable for its correctness, contracts, and delivery. Collaboration and code reviews across boundaries are expected, but ambiguous collective ownership is explicitly rejected.

### Guiding Principles

- **One Accountable Owner per Subsystem:** When an issue arises in a domain, there is no ambiguity about who leads the resolution.
- **Contract-Driven Collaboration:** Teammates interact through explicit, typed schemas (`src/slokern/contracts/`) rather than ad-hoc internal calls.
- **Respect Boundaries:** No owner unilaterally changes another owner's contract, assumptions, or verified parameter list.
- **Surface Blockers Early:** Unavailability of hardware, API keys, or external services must be declared immediately rather than masked by simulated success.

---

## 2. Team Roster & Ownership Matrix

| Member | Workstream / Role | Primary Ownership | Hand-Off Deliverable |
|---|---|---|---|
| **Rajdeep** | **Technical Lead / Architecture** | Scope boundaries, system architecture, shared contracts, control plane/API integration, dashboard alignment, final report narrative | Stable shared schemas, integrated API/control plane, validated end-to-end build, final claims audit |
| **Aman** | **Serving / GPU Infrastructure** | Model/runtime deployment, serving adapter (`src/slokern/engine/serving/`), supported tuning controls, parameter read-back, environment fingerprint | Verified healthy endpoint, confirmed parameter support matrix, environment metadata, cleanup runbooks |
| **Daksh** | **Verification / Evaluation** | Feasibility evaluator (`src/slokern/core/evaluator/`), reason codes, boundary test suites, independent verification runner (`src/slokern/core/verification/`) | Deterministic verdict logic, reason code taxonomy, independent verification protocol & verdict audit |
| **Adriraj** | **Benchmarking** | Workload fixtures, arrival models, load generator (`src/slokern/engine/loadgen/`), raw measurement capture, metrics engine (`src/slokern/core/metrics/`) | Raw event schema (`RawRequestMeasurement`), loadgen runner, deterministic metric aggregation, saturation detection |
| **Rohan** | **Optimization / Search** | Legal candidate space, canonical candidate serialization, baseline search, bounded search controller (`src/slokern/core/search/`), ranking logic | Candidate manifest generator, bounded search history, deterministic ranking objective, selection rationale |

---

## 3. Workstream Boundaries & Interaction Guardrails

To prevent friction and contradictory implementations during the fast-paced hackathon sprint, the following structural rules are strictly enforced:

### 3.1 Serving vs. Optimization (Aman & Rohan)
- **Aman dictates physical reality:** Aman alone decides and proves which serving parameters can be applied, verified, and read back from the serving runtime.
- **Rohan bounds search space:** Rohan designs the search space using *only* parameters confirmed in Aman's supported parameter table. Rohan must never invent speculative controls in the optimizer that the serving adapter cannot actively enforce.

### 3.2 Benchmarking vs. Evaluation (Adriraj & Daksh)
- **Adriraj owns measurement fidelity:** Adriraj captures raw timestamps, detects generator saturation, calculates summary percentiles, and asserts whether a benchmark run is valid.
- **Daksh owns feasibility verdicts:** Daksh consumes Adriraj's `MetricSet` and applies the deterministic `SLOSpec` rules. Adriraj does not declare whether a run passed an SLO; Daksh does not modify raw timestamps or re-aggregate percentiles.

### 3.3 Optimization vs. Evaluation (Rohan & Daksh)
- **Daksh owns pass/fail criteria:** Daksh determines whether a candidate is `FEASIBLE`, `INFEASIBLE`, or `INCONCLUSIVE`.
- **Rohan ranks only feasible candidates:** Rohan's search controller ranks only candidates that Daksh has certified as `FEASIBLE`. Rohan cannot relax constraints, ignore inconclusive evidence, or alter tie-breaking rules to make the optimizer look better.

### 3.4 Presentation vs. Backend Core (Frontend & Backend)
- **Frontend consumes backend contracts:** The React dashboard and CLI consume canonical schemas exported from `src/slokern/contracts/`. The UI must never re-implement or redefine metric aggregation or feasibility rules.
- **Explicit Labeling:** Any offline mock fixtures used during frontend development must be prominently labelled **DEMO DATA** to prevent confusing simulated runs with live experiments.

### 3.5 Cross-Cutting Contracts (Rajdeep's Coordination)
- **Rajdeep arbitrates interface changes:** If an interface must change, Rajdeep coordinates the review with affected owners and ensures contracts, fixtures, and contract tests are updated synchronously.

---

## 4. Shared Handoff Specifications

### 4.1 Workload/SLO Specification — Rajdeep Coordinates, Adriraj & Daksh Author
- **Contents:** Versioned schema (`WorkloadSpec`, `SLOSpec`, `ExperimentSpec`) declaring traffic profile, arrival model, warm-up/measurement durations, required SLO thresholds, and experiment budget.
- **Handoff:** Submitted via API or CLI; consumed by Experiment Controller, Load Generator, and Feasibility Evaluator.

### 4.2 Effective Configuration — Aman Supplies Reality, Rohan Supplies Intent
- **Contents:** `CandidateConfig` containing requested settings, effective read-back settings, parameter status (`applied`, `unsupported`, `rejected`), and runtime environment fingerprint.
- **Handoff:** Generated by Search Controller, applied by Serving Adapter, recorded in `RunRecord`.

### 4.3 Raw Measurements — Adriraj Owns
- **Contents:** Granular JSONL stream of `RawRequestMeasurement` records with microsecond timestamps (scheduled, sent, first-token, completed), HTTP status, token counts, and client validity flags.
- **Handoff:** Written by Load Generator subprocess to local artifact store; consumed by Metrics Engine.

### 4.4 Metrics — Adriraj Defines, Daksh Consumes
- **Contents:** `MetricSet` detailing TTFT, ITL, end-to-end latency, request throughput, token throughput, error rate, offered load, and achieved load with explicit units and sample counts.
- **Handoff:** Derived by Metrics Engine; consumed by Feasibility Evaluator and Dashboard.

### 4.5 Feasibility Verdict — Daksh Owns
- **Contents:** `FeasibilityResult` with overall verdict (`FEASIBLE`, `INFEASIBLE`, `INCONCLUSIVE`), constraint-by-constraint audit, observed values, thresholds, and structured reason codes.
- **Handoff:** Emitted by Feasibility Evaluator; consumed by Search Controller (for candidate ranking) and Report Generator.

### 4.6 Candidate & Search History — Rohan Owns
- **Contents:** `SearchResult` logging all tested candidates, execution order, associated run IDs, feasibility status, ranking values, selection rationale, and budget stopping reason.
- **Handoff:** Emitted by Search Controller; consumed by Verification Runner and Report Generator.

### 4.7 Final Report & Release Bundle — Rajdeep Integrates
- **Contents:** `ReportArtifact` linking immutable specification, environment fingerprint, baseline summary, candidate table, winning configuration, independent verification record, and disclosed limitations.
- **Handoff:** Published as Markdown and JSON; presented to hackathon evaluators.

---

## 5. Development Rituals & PR Review Protocol

To ensure clean daily integration without blocking teammates:

### 5.1 Branching Strategy
- `main` is protected and represents the known-good, stable build.
- Feature branches follow the naming pattern: `<owner>/<feature-description>` (e.g., `aman/nebius-adapter`, `adriraj/loadgen-arrival`, `daksh/evaluator-reason-codes`).
- Merge to `main` only via pull requests; direct pushes to `main` are restricted.

### 5.2 Pull Request & Review Rules
1. **Scope Focus:** Keep PRs small and focused on a single deliverable. Avoid combining unrelated refactors with core logic.
2. **Mandatory Reviews:** Every PR must be reviewed and approved by at least one other team member.
3. **Cross-Boundary Review:** Any PR that modifies a file in `src/slokern/contracts/` requires approval from **Rajdeep** plus every affected workstream owner.
4. **Automated Checks:** All unit tests and contract validation checks must pass before merging.
5. **No Secrets:** Never commit `.env` files, API tokens, cloud keys, or internal endpoint hostnames.

---

## 6. Related Documentation

- [System Architecture](architecture.md)
- [MVP Checklist & Acceptance Criteria](mvp-checklist.md)
- [Architecture Decision Log](decision-log.md)
- [Daily Integration Checklist](integration-checklist.md)
- [ADR 0001: MVP Scope & Evidence Policy](adr/0001-mvp-scope-and-evidence.md)

