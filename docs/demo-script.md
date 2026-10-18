# SLOKern Demo Narrative & Presentation Runbook

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Demo Script (Target: 3–5 Minutes)  
> **Owner:** Rajdeep (Technical Lead / Architecture)  
> **Authority:** Aligned with [README.md](../README.md) and [ROADMAP.md](../ROADMAP.md)

---

## 1. Demo Narrative Arc & Timing

The SLOKern presentation tells a coherent, evidence-first systems story in 3.5 to 5 minutes:

| Act | Duration | Focus | Key Message | Visual / Screen |
|---|---|---|---|---|
| **Act 1: The Dilemma** | 30s | The inference trade-off problem | Throughput without latency constraints is dangerous; manual tuning fails. | Overview Command Center |
| **Act 2: The Contract** | 45s | Declarative workload & SLO specification | Define traffic arrival and hard constraints before expensive runs. | Workload & SLO Builder |
| **Act 3: The Baseline** | 45s | Reference configuration reality | Default settings often breach tail latency or waste compute. | Baseline Results Panel |
| **Act 4: Bounded Search** | 60s | Controlled candidate evaluation | Test only legal, verified parameters; reject infeasible candidates. | Tuning Lab & Monitor |
| **Act 5: Selection & Verification** | 60s | The core product promise | Select by cost/objective, then rerun independently under a new run ID. | Verification View |
| **Act 6: Traceable Evidence** | 30s | Defensibility and limitations | Inspect raw request timestamps, environment fingerprint, and audit report. | Report & Artifact Viewer |

---

## 2. Step-by-Step Presentation Script

### Act 1: The Dilemma (0:00 – 0:30)
> *"In production LLM serving, raw throughput numbers are deeply misleading. A serving configuration might boast high tokens per second, but if the 95th percentile Time to First Token spikes to three seconds, users abandon the application. Conversely, over-provisioning GPUs to protect latency wastes thousands of dollars. Manual tuning is guesswork, and a single lucky benchmark run can trick teams into deploying a fragile configuration. That's why we built SLOKern: Optimize inference. Verify performance."*

### Act 2: Declarative Specification (0:30 – 1:15)
> *"SLOKern starts with a strict contract. Here in the Workload & SLO Builder, we declare our traffic profile: an open-loop Poisson arrival process at 10 requests per second with 512 input tokens. Crucially, we specify non-negotiable hard SLO constraints: TTFT p95 must remain under 250 milliseconds, and error rate must stay below 1%. Deterministic code—not an LLM—validates this specification and enforces a hard candidate budget before any expensive GPU compute begins."*

### Act 3: Baseline Reality (1:15 – 2:00)
> *"We first establish our baseline using the default serving configuration on our Nebius NVIDIA GPU instance. As the load generator delivers the offered load, SLOKern records every single request with microsecond client timestamps. The metrics engine calculates the distribution, and the deterministic evaluator renders its verdict: the default configuration violates our tail latency constraint—TTFT p95 reached 380 ms. Verdict: INFEASIBLE. Reason: TTFT_P95_EXCEEDED."*

### Act 4: Bounded Candidate Search (2:00 – 3:00)
> *"Next, our Search Controller explores a bounded space of legal parameters confirmed by our serving adapter: GPU memory utilization, max sequence concurrency, and KV-cache precision. Notice that SLOKern doesn't invent speculative settings; it applies only parameters it can read back and verify. As candidates execute, the Live Monitor tracks offered versus achieved load to guarantee client saturation didn't contaminate the run. Candidate A improves throughput but fails latency. Candidate B satisfies every hard constraint: TTFT p95 drops to 195 ms with zero errors. It is certified FEASIBLE and selected based on our declared efficiency objective."*

### Act 5: Mandatory Independent Verification (3:00 – 4:00)
> *"This is the core architectural innovation of SLOKern: we never award a verified badge from search evidence alone. A lucky run is not a verified recommendation. SLOKern automatically launches an independent verification run with a brand new, distinct run ID. Under the exact same workload protocol, Candidate B is benchmarked afresh. The verification engine recalculates metrics from the new raw measurements and compares drift. The candidate passes every hard constraint again. The verdict is sealed: VERIFIED."*

### Act 6: Auditable Evidence & Limitations (4:00 – 4:30)
> *"Finally, SLOKern generates a complete, self-contained Report Artifact. Every headline figure links directly to raw JSONL event traces, complete with environment fingerprints (NVIDIA driver, CUDA version, vLLM commit). If cloud pricing was unconfirmed, we declare cost unavailable and report GPU resource-time honestly. We don't claim global optimality—we prove the best verified candidate within the tested space. With SLOKern, teams optimize inference and verify performance."*

---

## 3. Demo Rules & Presentation Guardrails

1. **Honesty First:** Never present mock frontend data as live measurements. If displaying pre-recorded runs or offline fixtures, ensure the **DEMO DATA** badge is clearly visible.
2. **Show Failures:** Demonstrating a rejected candidate (`INFEASIBLE`) and an inconclusive run highlights the rigor of the deterministic evaluator.
3. **No Unsubstantiated Claims:** Do not claim "30% dollar savings" unless verified pricing was configured. If using a proxy, say: *"reduced GPU-seconds per request by 28% under strict SLO."*

---

## 4. Fallback Procedure (Contingency Runbook)

If the live Nebius endpoint experiences an outage or network latency during the presentation:

1. **Activate Fallback Mode:** In the dashboard shell, toggle to the archived evidence bundle:
   - Select the pre-recorded experiment session: `fixtures/demo/demo_experiment.json`.
2. **Explicit Disclosure:** Open the presentation by stating:
   > *"To ensure a smooth presentation within our 5-minute window, we are reviewing an evidence bundle measured on our Nebius NVIDIA H100 GPU instance earlier today, fully traceable to raw JSONL artifacts on disk."*
3. **Walk Through Artifacts:** Point out the `environment_fingerprint`, the distinct `search_run_id` vs `verification_run_id`, and open a raw measurement sample to demonstrate transparency.

---

## 5. Related Documentation

- [System Architecture](architecture.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [Daily Integration Checklist](integration-checklist.md)
- [Serving Deployment Notes](deployment.md)
