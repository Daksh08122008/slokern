# ADR 0001: MVP Scope Boundary, Empirical Evidence, and Independent Verification Policy

> **Status:** Accepted  
> **Date:** 2026-10-13  
> **Owner:** Rajdeep (Technical Lead / Architecture)  
> **Scope:** Repository-wide  
> **Authority:** Aligned with [README.md](../../README.md) and [ROADMAP.md](../../ROADMAP.md)

---

## 1. Context and Problem Statement

Deploying Large Language Models (LLMs) requires navigating complex trade-offs between latency, throughput, hardware cost, and reliability. Serving engines such as vLLM and TensorRT-LLM expose numerous low-level configuration knobs (e.g., KV-cache allocation, tensor parallelism, max batch size, chunked prefill). Tuning these configurations manually is slow and prone to errors. Furthermore, naive benchmark scripts often declare an "optimal" configuration based on a single lucky measurement run, only for the configuration to violate service-level objectives (SLOs) under real traffic.

For the Nebius × NVIDIA Global AI Hackathon, the team faces a strict timeline (October 13–30, 2026) and constrained GPU resources. We must decide how to bound the product scope, how to discover serving configurations, and how to prove that our optimization recommendations are genuinely sound.

---

## 2. Decision Drivers

1. **Defensibility over Breadth:** A working end-to-end pipeline that experimentally proves its claims on one model is far more valuable than an expansive framework with superficial support for ten models.
2. **Tolerance to Benchmark Noise:** Latency measurements in cloud GPU environments exhibit tail variance. A single run is insufficient to prove that an SLO is satisfied.
3. **Auditability & Integrity:** Every metric, ranking decision, and verdict must be traceable to unaggregated raw request events and confirmed environment metadata.
4. **Feasibility within Hackathon Constraints:** The 5-person team must have non-overlapping workstreams and clear handoffs to complete the project without integration chaos.

---

## 3. Considered Options

### Option 1: Broad Multi-Model Simulator with Heuristic Search
- Build an abstract simulator that predicts latency across dozens of models and cloud providers using analytical formulas and heuristic optimization (e.g., genetic algorithms).
- *Pros:* Broad coverage, attractive demo numbers, no expensive GPU execution required.
- *Cons:* Claims cannot be verified; analytical formulas consistently fail to capture GPU memory fragmentation, kernel dispatch overhead, and tail queuing delays. Violates hackathon goals.

### Option 2: Single-Pass Benchmark Search without Verification
- Execute a baseline and multiple candidate configurations on a real GPU, calculate percentiles once, rank candidates, and immediately present the top candidate as verified.
- *Pros:* Faster execution; conserves GPU budget.
- *Cons:* High probability of selecting false winners due to transient network or server anomalies during a single measurement window. Leaves the recommendation unverified.

### Option 3: Focused Empirical Optimizer with Mandatory Independent Verification (Chosen)
- Lock scope to one permitted NVIDIA model, one dedicated serving environment (Nebius GPU), and a small legal configuration space.
- Benchmark candidates using a strictly controlled workload protocol, preserve raw request-level measurements, apply deterministic constraint evaluation, rank feasible candidates, and rerun the winning configuration under a fresh run ID before emitting a verdict.
- *Pros:* Scientifically rigorous, defensible, reproducible, and fits within the 5-person sprint timeline.
- *Cons:* Requires discipline to restrict scope; verification consumes additional experiment budget.

---

## 4. Decision Outcome

We choose **Option 3**. The SLOKern architecture will strictly adhere to the following principles:

### 4.1 The Core Operating Principle
> **One model, one serving environment, a small configuration space, reproducible experiments.**

### 4.2 Non-Negotiable Architectural Commitments
1. **Empirical Measurement First:** We do not guess or simulate optimal settings. We measure them on real infrastructure.
2. **Deterministic Governance:** Deterministic Python code owns metrics calculation, constraint evaluation, experiment budgets, candidate selection, and verification verdicts. Optional AI modules are strictly advisory and non-authoritative.
3. **Mandatory Independent Verification:** A candidate configuration selected during search is **never** certified as `VERIFIED` based on search evidence alone. It must undergo an independent verification run under a brand new `run_id` using the identical workload protocol.
4. **Strict Scope Boundaries:** The MVP explicitly excludes universal platform support, unconstrained search, production autoscaling, model fine-tuning, and heuristic cost fabrication.
5. **Separation of Concerns in State Management:** Execution health, evidence validity, feasibility verdicts, and verification states are maintained as separate status domains. Execution failure is never reported as an SLO failure.

---

## 5. Consequences

### Positive Consequences
- Guarantees high confidence and defensibility for the final demo and hackathon presentation.
- Eliminates ambiguous shared ownership across the 5 team members.
- Establishes clean audit trails from published reports down to raw microsecond request timestamps (`RawRequestMeasurement`).
- Prevents wasted effort on speculative features before the critical serving and measurement path is verified.

### Negative Consequences & Mitigations
- *Limitation:* The MVP recommendation applies only to the tested model and hardware tier.  
  *Mitigation:* Disclose search space boundaries and environment limitations explicitly in every report. Never claim global optimality.
- *Cost:* The independent verification run consumes additional wall-clock time and GPU compute.  
  *Mitigation:* Keep the candidate search space small (3–5 candidates) and enforce a strict experiment budget.

---

## 6. Related Documents

- [System Architecture](../architecture.md)
- [MVP Scope & Acceptance Checklist](../mvp-checklist.md)
- [Team Ownership Model](../ownership.md)
- [Decision Log](../decision-log.md)
- [ADR 0002: Dual-Mode Cost Accounting Policy](0002-cost-model.md)

