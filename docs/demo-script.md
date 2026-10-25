# SLOKern Demo Narrative & Presentation Runbook

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Status:** Active Demo Script (Target: 3–5 Minutes, Solo Presentation)  
> **Owner:** Rajdeep (Sole Presenter & Technical Lead)  
> **Authority:** Aligned with [README.md](../README.md), [ROADMAP.md](../ROADMAP.md), and [docs/ownership.md](ownership.md)

> **Rehearsal script only:** Sample thresholds and result narration below are illustrative placeholders, not measured evidence. Do not claim a live baseline, winning candidate, or `VERIFIED` outcome unless the corresponding fresh raw artifacts exist. If using fake or prerecorded synthetic data, label it **DEMO DATA**. The proposed Nemotron 30B / Serverless / vLLM 0.12.0 path and new search profile are not yet verified.

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
> *"We first establish the baseline under the declared configuration. [Show the run ID, endpoint/model revision, effective flags, offered and achieved load, valid sample count, and raw artifact.] The observed result is [insert only values derived from that artifact]; the deterministic evaluator reports [FEASIBLE / INFEASIBLE / INCONCLUSIVE] with [reason]. If using fixtures, label this screen DEMO DATA."*

### Act 4: Bounded Candidate Search (2:00 – 3:00)
> *"Next, the controller explores only the pre-registered bounded matrix. [Show each requested/effective setting pair and candidate artifact.] These vLLM settings are not eligible for an optimization claim until the runtime confirms them. Candidate results and verdicts come from their own valid evidence; [state the actual selected candidate/objective result, or say no eligible candidate was found]."*

### Act 5: Mandatory Independent Verification (3:00 – 4:00)
> *"A search result is not a verified recommendation. [If the verification engine has been implemented and run, show its distinct run ID and fresh raw evidence, then read its actual verdict.] Otherwise state plainly that independent verification is not yet available; do not show a `VERIFIED` badge."*

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
2. **Explicit Disclosure:** State whether the bundle contains live evidence or synthetic fixtures. For fixtures, say **DEMO DATA**. For live evidence, identify the run IDs and verify that the raw JSONL and environment fingerprint are present before describing the measurements.
3. **Walk Through Artifacts:** Point out the `environment_fingerprint`, the distinct `search_run_id` vs `verification_run_id`, and open a raw measurement sample to demonstrate transparency.

---

## 5. Related Documentation

- [System Architecture](architecture.md)
- [MVP Scope & Acceptance Checklist](mvp-checklist.md)
- [Daily Integration Checklist](integration-checklist.md)
- [Serving Deployment Notes](deployment.md)
