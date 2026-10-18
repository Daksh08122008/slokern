# SLOKern — Nebius & NVIDIA Tool Feedback Register

> **Purpose:** Staging register for the compulsory tool feedback required by the Nebius × NVIDIA Global AI Hackathon submission form.  
> **Audited Date:** 2026-10-18  
> **Owner:** Rajdeep (Sole Technical Owner; Consolidated Feedback)

---

## 1. Hackathon Requirement

The official submission guidelines state:
> *"Providing feedback on the Nebius tools and NVIDIA models you use is a required part of every submission, not an afterthought. Submissions should detail your experience with Nebius Token Factory, Nebius AI Cloud, and the NVIDIA model(s) used—specifically covering what you used them for, what worked well, what needs improvement, how the zero-to-hello-world onboarding process felt, and whether you would build with them again (and why)."*

---

## 2. Structured Feedback Register

### 2.1 Nebius AI Cloud (GPU Compute) & Token Factory
- **Use Case in SLOKern:** Serving host for candidate LLM inference runtime (vLLM container) running on NVIDIA H100 / A100 GPU instances, evaluated under controlled burst and sustained arrival workloads.
- **Onboarding & Setup Experience:**
  - *Observed Strengths:* Fast instance provisioning; clear SSH key management; NVIDIA driver and CUDA toolchain pre-configured in container images.
  - *Areas for Improvement / Gaps:* Detailed programmatic API for reading back live hardware power draw and thermal throttling states; direct dashboard metrics on KV-cache memory pressure during high concurrency.
- **Would we build with it again?**
  - *Verdict:* Yes. High compute stability, predictable network latency between load generation client and inference endpoint, and competitive hourly GPU cost.

### 2.2 NVIDIA Nemotron Open-Source Model (`Nemotron-3-Nano-30B-A3B` FP8)
- **Use Case in SLOKern:** Selected compliance benchmark model candidate for evaluating a fixed 2×2 configuration space under strict SLO targets (e.g., TTFT p95 $\le 250\text{ ms}$, ITL p95 $\le 30\text{ ms}$). Exact candidate dimensions are pending confirmation from the serving interface.
- **Architectural Expectations & Serving Observations (Staging):**
  - *Design Specifications:* Hybrid Mamba-2 Mixture-of-Experts architecture (~30B total, ~3B active parameters per token in design) with FP8 quantization and 262K context window. Listed in Nebius catalog materials; physical serving throughput, latency distributions, and memory behavior will be recorded during live benchmarks.
  - *Areas for Improvement / Gaps Identified:* Documentation needed on catalog display name vs. exact API model identifier strings in Nebius Token Factory; clarity on whether managed endpoints expose serving-engine controls or only client request parameters.
- **Would we build with it again?**
  - *Verdict (Provisional):* Yes. Architecturally well-suited on paper for low-latency inference due to its sparse active parameter design; final assessment pending live benchmark results.

