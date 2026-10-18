# SLOKern — Official Hackathon Compliance & Requirements Traceability Matrix

> **Event:** Nebius × NVIDIA Global AI Hackathon (Devpost)  
> **Audited Date:** 2026-10-18  
> **Auditor:** Senior Software Architect & Hackathon Compliance Auditor  
> **Authority:** Aligned with official Devpost rules, FAQs, and updates cited below.

---

## 1. Compliance Authority & Official Sources

Official requirements were audited on **October 18, 2026** against the following primary sources:

1. **Hackathon Overview & Rules:** [Nebius × NVIDIA Global AI Hackathon on Devpost](https://nebiusglobalaihackathon.devpost.com/)
2. **Official Rules:** [Rules](https://nebiusglobalaihackathon.devpost.com/rules)
3. **Frequently Asked Questions:** [Details & FAQs](https://nebiusglobalaihackathon.devpost.com/details/faqs)
4. **Judging & Evaluation Criteria:** [Updates / How Judging Works](https://nebiusglobalaihackathon.devpost.com/updates/46204-here-s-how-judging-works)

---

## 2. Master Requirements Traceability Matrix

| Requirement | Official Source | Mandatory or Optional | SLOKern Implementation Strategy | Evidence in Repository | Status | Remaining Action |
|---|---|---|---|---|---|---|
| **Registration & Eligibility** | [Rules § Eligibility](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | 5-person team (Rajdeep, Aman, Daksh, Adriraj, Rohan) meeting age of majority and non-embargoed jurisdiction rules. | Registered team roster in `README.md`, `ROADMAP.md`. | `PASS` | Verify individual Devpost account links before submission. |
| **Submission Deadline** | [Overview](https://nebiusglobalaihackathon.devpost.com/) | Mandatory | Target submission cutoff: **Friday, October 30, 2026 at 10:00 AM PDT (10:30 PM IST)**. | Locked in `ROADMAP.md` sprint planning. | `PASS` | Maintain submission buffer on Oct 29–30. |
| **Track Selection** | [Rules § Tracks](https://nebiusglobalaihackathon.devpost.com/) | Mandatory | Primary track: **Coding and Agentic Engineering Track** (LLM inference serving, systems performance, and verification). | Documented in `README.md` and `docs/architecture.md`. | `PASS` | Select "Coding and Agentic Engineering" on Devpost submission dropdown. |
| **Nebius Infrastructure** | [Rules § Technical Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Serving system deployed on **Nebius AI Cloud** GPU instance (NVIDIA H100/A100) and/or integration with **Nebius Token Factory** inference runtime. | Serving adapter in `src/slokern/engine/serving/nebius.py`, deployment guide in `docs/deployment.md`. | `BLOCKED` | **Action for Aman:** Finalize Nebius GPU instance provisioning, endpoint URL, and execute live smoke test. |
| **NVIDIA Open-Source Model** | [Rules § Technical Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Must utilize **at least one NVIDIA open-source model** (e.g., *Nemotron*, *GR00T*, *Cosmos*, *Sonic*, *Alpamayo*). Selected candidate: `Nemotron-3-Nano-30B-A3B` (FP8, ~30B MoE / ~3B active per token in design, 262K context window, listed in Nebius catalog; access pending verification). Optional secondary comparison: `nvidia/Llama-3.1-Nemotron-70B-Instruct` (unverified in team catalog; purely hypothetical secondary model). | Addressed in `docs/adr/0001-model-runtime.md` Addendum 0001-B and `docs/deployment.md`. | `BLOCKED` | **Action for Aman & Rajdeep:** Validate endpoint reachability and execute live single-request smoke test for `Nemotron-3-Nano-30B-A3B` (FP8) on Nebius endpoint. Exact API identifier is pending smoke test read-back. Note: `meta-llama/Meta-Llama-3-8B-Instruct` is retained as an internal baseline only and does not satisfy this mandate on its own. |
| **Public Source Repository** | [Rules § Submission Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Public GitHub repository containing complete source code, tests, and configurations. | Active Git repository with clean main branch. | `PASS` | Ensure repository visibility is public before the Oct 30 deadline. |
| **Open Source License** | [Rules § Submission Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Open-source licensed codebase. | `LICENSE` file present in root directory (Apache 2.0). | `PASS` | Verified file exists and matches standard Open Source licensing. |
| **README & Setup Instructions** | [Rules § Submission Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Comprehensive README with architecture, quickstart, setup, and replication steps. | `README.md` with complete architecture, commands, and workflows. | `PASS` | Verify reproduction commands once live GPU endpoint is active. |
| **Working Demo Video** | [Rules § Submission Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Public video demonstration (YouTube/Vimeo) strictly **3 minutes or less** showing working system. | Planned in `docs/demo-script.md` and `ROADMAP.md` Phase 5. | `UNVERIFIED` | Record, edit, and upload a $\le 3\text{-minute}$ walkthrough showing live verification and dashboard. |
| **Public Demo Accessibility** | [Rules § Submission Requirements](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Deployed web UI or reproducible local CLI/script demo accessible to judges. | React/Vite dashboard in `frontend/`, CLI `slokern verify` in `src/slokern/cli/`. | `IN PROGRESS` | Build and host dashboard demo preview and provide fallback demo run script. |
| **Required Nebius & NVIDIA Tool Feedback** | [Rules § Submission Requirements](https://nebiusglobalaihackathon.devpost.com/details/faqs) | Mandatory | Structured feedback on Nebius Token Factory / AI Cloud and NVIDIA models (onboarding, what worked, areas for improvement, future build interest). | Dedicated feedback template created in `docs/hackathon-feedback.md`. | `IN PROGRESS` | Synthesize team feedback during live benchmarking on Nebius and include in submission form. |
| **Pre-Existing Code Disclosure** | [Rules § Fresh vs Pre-Existing Code](https://nebiusglobalaihackathon.devpost.com/rules) | Mandatory | Explain how project was created or significantly updated during the hackathon window (Oct 13–30, 2026). | Git commit history and `ROADMAP.md` sprint logs show creation within window. | `PASS` | Complete Devpost form section detailing work completed during hackathon dates. |
| **Submission Form Completion** | [Overview](https://nebiusglobalaihackathon.devpost.com/) | Mandatory | Complete all required fields on Devpost submission portal. | Documented submission checklist in `ROADMAP.md`. | `PENDING` | Submit prior to Oct 30, 10:00 AM PDT. |

---

## 3. Detailed Audit Findings & Remediation

### Finding 1: Mandatory NVIDIA Open-Source Model Requirement
- **Rule:** The hackathon rules explicitly mandate: *"Projects must utilize at least one NVIDIA open-source model (such as models from the Nemotron, GR00T, Cosmos, Sonic, or Alpamayo families)."*
- **Previous Repository State:** `docs/adr/0001-model-runtime.md` accepted `meta-llama/Meta-Llama-3-8B-Instruct` as the primary target. While Meta-Llama models are optimized by NVIDIA (e.g. TensorRT-LLM/NIM), Meta is the model author. Relying solely on `meta-llama/Meta-Llama-3-8B-Instruct` leaves the project vulnerable to disqualification under the model rule.
- **Remediation & Compliance Path:**
  1. Formally select `Nemotron-3-Nano-30B-A3B` (FP8) from the Nebius catalog as the **Hackathon Compliance Target Model Candidate**.
  2. Model feasibility audit: `Nemotron-3-Nano-30B-A3B` is an NVIDIA open-weights architecture combining Mamba-2 hybrid layers and MoE (~30B total, ~3B active parameters per token in design) with 262K context window in FP8. Serving throughput, latency percentiles, and memory headroom under SLOKern's benchmark are unmeasured and subject to empirical verification during live runs.
  3. Retain `meta-llama/Meta-Llama-3-8B-Instruct` as an **Internal Pipeline Validation Baseline**, with explicit documentation that it serves for comparative and pipeline development only.
  4. Status remains `PENDING RUNTIME VERIFICATION` (blocked until Aman executes the single-request smoke test on the live Nebius endpoint and confirms the exact API model identifier). Permitted terminology: `Selected candidate`, `Planned deployment target`, `Pending runtime verification`. Strictly avoid claims of `Successfully deployed` or `Benchmark completed`.

### Finding 2: Infrastructure Compliance
- **Rule:** Projects must run on either **Nebius Token Factory** or **Nebius AI Cloud**.
- **SLOKern Architecture Alignment:** SLOKern's serving adapter (`src/slokern/engine/serving/nebius.py`) is explicitly architected to target Nebius Cloud infrastructure.
- **Action Required:** Finalize the deployment script in `docs/deployment.md` with active Nebius instance details and verify the endpoint health check.

### Finding 3: Compulsory Tool Feedback
- **Rule:** Submissions require structured feedback on Nebius and NVIDIA tools. Submissions lacking substantive feedback risk point deduction or disqualification.
- **Remediation:** `docs/hackathon-feedback.md` is provided as an active staging area for Aman, Adriraj, and Rajdeep to log specific feedback on Nebius GPU provisioning, latency stability, and NVIDIA Nemotron inference performance.

---

## 4. Evaluation Criteria Alignment (25% Weight Each)

| Criteria | Hackathon Evaluation Standard | SLOKern Architectural Demonstration |
|---|---|---|
| **1. Technological Implementation** | Technical depth, functionality, robustness, and execution. | Subprocess loadgen isolation, microsecond timestamping, deterministic feasibility evaluator, read-back parameter verification, and mandatory independent verification rerun. |
| **2. Design** | UX/UI quality, command center ergonomics, clarity of trade-offs. | Cyberpunk technical command center, clear visual separation of the 4 state domains, unambiguous `DEMO DATA` vs `LIVE` labels, and inspectable audit reports. |
| **3. Potential Impact** | Real-world viability, solving a genuine engineering problem, cost efficiency. | Prevents silent SLA violations and thousands of dollars in wasted GPU cloud spend; provides defensible, audited configurations for enterprise LLM serving. |
| **4. Quality of the Idea** | Novelty, creativity, and principled engineering. | Rejects unverified benchmark numbers and heuristic guessing. "Do not guess the optimal configuration. Find it experimentally, then verify it." |

