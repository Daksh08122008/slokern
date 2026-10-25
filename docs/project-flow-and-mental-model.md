# SLOKern — Project Flow & Mental Model
### An evidence-driven decision system for finding and verifying a better LLM-serving configuration

> **Event:** Nebius × NVIDIA Global AI Hackathon  
> **Canonical Pipeline:** `SPECIFY > VALIDATE > MEASURE > EVALUATE > OPTIMIZE > VERIFY > EXPLAIN`  
> **Execution Model:** Single-Owner Core Execution led by Rajdeep with bounded collaborator workstreams for Adriraj (Benchmark Integrity, active Oct 21) and Daksh (Decision Verification, active Oct 24)  
> **Document Status:** Authoritative Presentation & Mental Model Source (Reconciled with Accepted Architecture & Hackathon Rules)  
> **Rule:** *Illustrative values are examples only, not benchmark results. Mock fixtures must be labelled DEMO DATA.*

> **Profile status (2026-10-23):** ADR 0001-B's accepted model-family candidate remains Nemotron-3-Nano-30B-A3B FP8, with exact revision/API name pending. The current plan proposal is Serverless AI custom container + vLLM 0.12.0 + H100. Its 5-point config profile and long-run methodology are unratified. Current source still uses `{16, 64} × {1024, 2048}` and cannot apply/read back vLLM launch flags. See [DEC-0013](decision-log.md#dec-0013-reconcile-the-controlled-deployment-and-search-profile-open) and [implementation status](implementation-status.md#78-documentation-and-profile-reality-audit-2026-10-23).

---

The key is to stop thinking of SLOKern as merely a benchmark dashboard or an AI optimizer. **SLOKern is an evidence-driven decision system for finding and verifying a better LLM-serving configuration.**

---

## 1. The Entire Project in One Picture

Imagine you have an NVIDIA GPU serving an LLM. You can change certain serving parameters, such as supported batching, memory, or concurrency settings. Different configurations trade off latency, throughput, and resource consumption. But which configuration should you actually use? SLOKern runs controlled experiments to answer that question.

```text
1. Specify   ──► Model + serving environment + workload profile + hard SLO constraints
      │
2. Validate  ──► Validate specification, budget limits, and legal parameter space
      │
3. Measure   ──► Establish baseline anchor ──► Benchmark candidate configurations (raw timings)
      │
4. Evaluate  ──► Compute MetricSet (percentiles) ──► Apply deterministic SLO rules
      │
5. Optimize  ──► Search bounded legal space ──► Rank feasible candidates by declared objective
      │
6. Verify    ──► Freeze winning candidate ──► Independent rerun under fresh verification_run_id
      │
7. Explain   ──► Generate auditable ReportArtifact (verdict + evidence + environment + limitations)
```

The output is not simply *"use configuration B."* It is:

> *"Configuration B was tested in this environment under this workload, met every required SLO according to this policy, ranked best under this declared objective among the tested candidates, and passed a separate verification run."*

That sentence is the heart of SLOKern.

---

## 2. First, Understand the Problem We're Solving

Suppose a team serves an open-source LLM on a Nebius GPU instance. The team wants low latency, sufficient throughput, and reasonable resource consumption. There are multiple possible configurations, but they are not equally good.

* **The Serving System:** The model, runtime engine, GPU hardware, memory allocation, and serving parameters.
  * *Official Hackathon Compliance Target Candidate:* `Nemotron-3-Nano-30B-A3B` (FP8, Hybrid Mamba-2 MoE: ~30B total / ~3B active parameters per token in design, 262K context window, listed in Nebius catalog; endpoint access pending verification).
  * *Optional Secondary Comparison Model:* `nvidia/Llama-3.1-Nemotron-70B-Instruct` (unverified in team catalog; purely hypothetical secondary model).
  * *Internal Pipeline Baseline:* `meta-llama/Meta-Llama-3-8B-Instruct` (retained for pipeline comparison and fake-adapter tests; does not alone satisfy the NVIDIA model rule).
  * *Active Status:* Deployment on Nebius Cloud is `PENDING RUNTIME VERIFICATION` (blocked pending live single-request smoke test to confirm exact API model identifier).
* **The Workload:** The incoming request profile, prompt lengths, output-token limits, arrival pattern, and offered request rate.
* **The SLO Requirements:** Non-negotiable performance boundaries the system must satisfy, such as maximum p95 Time to First Token and minimum request throughput.

### The Optimization Problem Formulation

A configuration that produces high throughput but violates latency limits is not a winner. A configuration that appears fast because the client load generator failed to deliver the intended traffic is not a trustworthy winner either. SLOKern solves a constrained optimization problem:

$$\text{Choose } c^* = \arg\min_{c \in C_{\text{tested}}} J(c) \quad \text{subject to } g_i(c) \le 0, \; i = 1, \dots, m \quad \text{and } \text{Evidence}(c) \text{ is valid}$$

Here:
* $c$ is a candidate serving configuration.
* $C_{\text{tested}}$ is the bounded set of legal candidates actually evaluated.
* $g_i$ represents each hard SLO constraint.
* $J$ is the declared optimization objective, such as verified monetary cost (Mode A) or a non-monetary systems efficiency proxy (Mode B).

The objective is applied **only after feasibility is established**. The equation expresses the intended decision rule, not a claim that the optimizer has already been implemented or that a global optimum is guaranteed.

---

## 3. Walk Through One Complete SLOKern Experiment

Let's follow a hypothetical run from beginning to end. The values below are illustrative, not real benchmark results.

### Step 1: Specify the Experiment
The user opens the SLOKern dashboard and defines the optimization problem:

| Setting | Illustrative Value | Authoritative Context |
|---|---|---|
| **Model** | `Nemotron-3-Nano-30B-A3B` (FP8) | Selected hackathon compliance candidate (pending runtime verification via smoke test) |
| **Runtime** | `vLLM` container / Token Factory on Nebius | OpenAI-compatible streaming server |
| **Workload** | Versioned request fixture | Fixed prompt distribution (`WorkloadSpec`) |
| **Arrival policy** | Constant-rate requests | Deterministic request dispatch |
| **Offered load** | 20 requests/second | Intended client generation rate |
| **Warm-up** | 60 seconds (illustrative) | Window to prime GPU caches (illustrative default; proposed shorter durations remain unvalidated pending timing evidence) |
| **Measurement period** | 180 seconds (illustrative) | Active measurement window (illustrative default; proposed shorter durations remain unvalidated pending timing evidence) |
| **Hard SLO** | p95 TTFT $\le 500\text{ ms}$ | Non-negotiable latency constraint |
| **Hard SLO** | Error rate $\le 1.0\%$ | Allowed failure budget |
| **Optimization goal** | Declared efficiency objective | Mode B proxy default (`unavailable` fallback) or Mode A verified cost when rate card is provided |

*What happens internally?* The API receives a `WorkloadSpec` and an `SLOSpec`. Pydantic-based validation checks that the specification is structurally valid and coherent, rejecting malformed inputs before they consume GPU time.

### Step 2: Validate the Legal Search Space & Restrict Budget

To protect hackathon GPU credits, SLOKern restricts candidate exploration to a **fixed 2×2 configuration space (4 candidates total)** as a design requirement. However:
- **Current Code Grid:** `max_num_batched_tokens ∈ {1024, 2048}` × `max_num_seqs ∈ {16, 64}`. These values are generated by source but are not remotely applied or verified by the current Nebius adapter (`BLK-17`).
- **Distinguishing Client/Workload from Serving-Engine Knobs:**
  - *Client/Workload Parameters (e.g. client concurrency limit, max output tokens):* Control client traffic generation and request payload bounds. **Changing workload parameters does not prove GPU-serving optimization.**
  - *Serving-Engine Parameters (e.g. batch concurrency, GPU memory utilization, max model length):* Directly configure the inference runtime on the GPU.
  - Neither parameter set is confirmed supported until verified by runtime read-back on the live Nebius endpoint.
- **Architectural Blocker Notice:** If the deployment interface (such as a managed Token Factory endpoint) exposes only client request parameters and lacks serving-engine controls, this is an **architectural blocker**. Resolving this blocker requires an explicit architecture decision by Rajdeep (such as deploying containerized vLLM on a dedicated Nebius Compute GPU instance).

The accepted DEC-0010 rule bounds candidate exploration to four combinations, but the exact profile has not been reconciled with the latest proposal. The proposal is a centre baseline `(max_num_seqs=128, max_num_batched_tokens=8192)` and four corners:
* **Candidate 1:** `(64, 2048)`
* **Candidate 2:** `(64, 16384)`
* **Candidate 3:** `(256, 2048)`
* **Candidate 4:** `(256, 16384)`

Current source still generates `{max_num_seqs: 16 or 64} × {max_num_batched_tokens: 1024 or 2048}`. The proposal is not implemented or yet verified as legal for vLLM 0.12.0/Serverless; see DEC-0013.

**The intended controller campaign allocates six runs:**
1. Baseline measurement (default configuration anchor)
2. Candidate 1
3. Candidate 2
4. Candidate 3
5. Candidate 4
6. Independent verification rerun of the selected candidate under a fresh `verification_run_id`

*(Note: The preflight smoke test is a separate preliminary single-request verification and is **not counted among the six benchmark runs**).*

The default `BudgetLimiter` follows this allocation, but custom limits can spend the verification reserve (`BLK-15`), and the current controller does not run independent verification. Preflight, pilot, retries, and startup/teardown must also be included in operational and billable budgets.

*Crucial Guardrail:* The intended adapter must validate proposed settings and read back the effective configuration. **Current `NebiusServingAdapter.apply_config()` evaluates locally declared capabilities and updates local state; it does not send or read back vLLM process flags.** A configuration written in a file is not proof that the server applied it. `BLK-17` remains active.

### Step 3: Measure — Establish Baseline First, Then Candidates

#### A. Baseline Establishment Anchor
Before testing candidate permutations, SLOKern runs the serving system under a known reference baseline configuration under the declared workload. The baseline answers:
* How fast is the default setup?
* How much traffic can it sustain?
* Does it already satisfy the SLO?
* Are the environment and measurements trustworthy?

Without a baseline, you cannot reliably explain whether an optimization was achieved. The baseline is the experiment's reference anchor, not necessarily its winner.

#### B. Generate Controlled Load and Collect Raw Evidence
* **Workload Generator:** Schedules and sends requests at the intended arrival rate in an isolated subprocess.
* **Serving Adapter & Model Runtime:** Intended to apply configuration, read back effective settings, and capture the environment fingerprint. The current Nebius adapter does not apply/read back remote flags (`BLK-17`).
* **Raw Measurement Capture:** Records unaggregated `RawRequestMeasurement` JSONL events (prompt token count is currently estimated from whitespace):
  * When the request was scheduled and sent.
  * When the first output token arrived (`first_token_at`).
  * When generation completed (`completed_at`).
  * Whether the request succeeded, failed, or timed out.
  * Input and output token counts.
  * Associated experiment, run, and candidate IDs.

#### Why a Separate Load Generator Subprocess?
If a benchmark process shares event loops with the web API or UI, client thread starvation can artificially delay request dispatch. A server might appear to have excellent latency simply because it never received the intended traffic. SLOKern compares **offered load** with **achieved load** and detects **generator saturation** (`generator_saturated = True`), immediately flagging contaminated runs.

---

## 4. Step 4: Evaluate the Evidence (Convert Raw Data into Metrics & Verdicts)

Raw timestamps are evidence. Metrics are derived interpretations of that evidence.

### Complete MetricSet Taxonomy

| Metric | Field Name | Unit | Definition & Measurement Source |
|---|---|---|---|
| **Time to First Token (TTFT)** | `ttft_ms` | `ms` | Time from request dispatch (`sent_at`) to first output token receipt (`first_token_at`). Evaluated at p50, p90, p95, p99. |
| **Inter-Token Latency (ITL)** | `itl_ms` | `ms/tok` | Time between successive generated tokens, aggregated per request and across population percentiles. |
| **End-to-End Latency** | `e2e_latency_ms` | `ms` | Round-trip duration from client dispatch to complete response stream termination. |
| **Request Throughput** | `request_throughput_rps` | `req/s` | Successfully completed valid requests divided by measurement duration. |
| **Output-Token Throughput** | `token_throughput_tps` | `tok/s` | Total generated output tokens divided by measurement duration. |
| **Error Rate** | `error_rate` | fraction / `%` | Failed requests divided by total offered requests. |
| **Offered Load** | `offered_load_rps` | `req/s` | Actual dispatch rate scheduled by client load generator according to workload arrival model. |
| **Achieved Load** | `achieved_load_rps` | `req/s` | Actual request rate delivered/completed over the measurement window. |
| **Generator Saturation Flag** | `generator_saturated` | `bool` | Set to `True` if client dispatch latency > 10 ms or offered rate diverges > 10% from target. Flags data as `CONTAMINATED`. |

### Deterministic SLO Evaluation

The deterministic Feasibility Evaluator applies versioned, deterministic rules against the `MetricSet`. Consider these hypothetical results (SLO: p95 TTFT $\le 500\text{ ms}$, Error Rate $\le 1.0\%$):

| Candidate | p95 TTFT | Error Rate | Evidence Validity | Feasibility Verdict | Audit Reason Code |
|---|---|---|---|---|---|
| **A** | 420 ms | 0.4% | `VALID` | `FEASIBLE` | `HARD_CONSTRAINTS_PASSED` |
| **B** | 310 ms | 0.3% | `VALID` | `FEASIBLE` | `HARD_CONSTRAINTS_PASSED` |
| **C** | 270 ms | 2.5% | `VALID` | `INFEASIBLE` | `ERROR_RATE_EXCEEDED` |
| **D** | Insufficient samples | Unknown | `INVALID` | `INCONCLUSIVE` | `INSUFFICIENT_SAMPLES` |

*Candidate C has the fastest latency, but it violates the error rate constraint.* Candidate D lacks sufficient valid samples. Neither can be selected. The evaluator emits an auditable `FeasibilityResult`.

---

## 5. Step 5: Optimize (Candidate Ranking & Cost Policy)

The search controller ranks only **evidenced feasible** candidates. It operates inside a strict budget:

```text
Choose legal candidate ──► Run experiment ──► Evaluate feasibility ──► Record in SearchResult ──► Continue / Stop
```

### The Cost Question: What Does "Best" Mean?
SLOKern follows a principled **Dual-Mode Cost Policy** (ADR 0002):

* **Mode A: Verified Monetary Accounting**  
  When official, verified cloud pricing is provided (e.g. Nebius GPU rate card), compute cost per 1k requests:
  $$\text{Cost per 1k requests} = \frac{\text{Hourly GPU Rate}}{\text{Achieved Requests/hr}} \times 1000$$
  Rank feasible candidates to find the lowest-cost configuration.
* **Mode B: Non-Monetary Systems Proxy**  
  When monetary pricing cannot be verified, report cost as **`unavailable`** (never invent prices!). Rank feasible candidates by a declared systems proxy:
  1. *Resource-Time:* GPU seconds consumed per request. *(Note: If the deployment cannot provide verified GPU count or dedicated residency data, such as on managed serverless endpoints where GPU allocation is hidden, GPU-seconds per request is also reported as **`unavailable`**).*
  2. *Throughput Under SLO:* Maximum output tokens/second (or requests/second) while satisfying all declared latency hard constraints.

*Important:* "Best candidate" means the best supported candidate **among those tested in the declared search space and environment**, never a claim of global optimality.

---

## 6. Step 6: Verify Independently (The "Kern" in SLOKern)

Suppose Candidate B wins the search. Should SLOKern immediately declare victory? **No.** A single benchmark run can be distorted by transient network jitter, noisy neighbors, or warm-up artifacts.

SLOKern freezes Candidate B, generates a **brand new `verification_run_id`**, and reruns the identical workload protocol.

### Canonical Verification Outcomes

| Verification State | Formal Code Enum | Meaning |
|---|---|---|
| **Verification Succeeds** | `VERIFIED` | Intended outcome when a fresh run produces valid evidence and satisfies all hard constraints. Current verification modules are stubs, so the implementation cannot yet issue this evidence-backed recommendation. |
| **Verification Fails** | `VERIFICATION_FAILED` | The selected candidate breaches an SLO threshold during the rerun. SLOKern reports the failure honestly and does not present it as a winner. |
| **Verification Inconclusive** | `VERIFICATION_INCONCLUSIVE` | The fresh run experienced client saturation or dropped samples. Evidence is unresolved, not a pass. |

A verification failure does not mean the initial run was fabricated; it means the configuration is unstable and failed to prove repeatability. The audit is preserved in a `VerificationRecord`.

---

## 7. Step 7: Explain & Produce Auditable Artifacts

The system compiles an immutable `ReportArtifact` containing:
1. Complete `ExperimentSpec` and workload configuration.
2. Verified `environment_fingerprint` (GPU model, driver, CUDA, container commit).
3. Baseline summary vs. winning configuration metrics and deltas.
4. Formal verification audit and drift analysis.
5. Declared pricing source or `unavailable` declaration.
6. Explicit search space limitations and boundary disclosures.

---

## 8. How All Software Components Fit Together

| Component | Primary Owner | Architectural Responsibility |
|---|---|---|
| **Dashboard & Control Plane** | Rajdeep | Accepts specs, manages experiment lifecycle, streams SSE events, presents cyberpunk UI. |
| **Experiment Runner & Controller** | Rajdeep | Orchestrates baseline, candidate iterations, stopping conditions, and verification dispatch. |
| **Serving Adapter** | Rajdeep | Intended to apply candidate settings, verify read-back, and capture environment fingerprint. Current Nebius adapter does not apply/read back remote flags (`BLK-17`). |
| **Load Generator** | Rajdeep | Generates scheduled request arrival patterns in an isolated subprocess; records floating-point epoch timestamps without a verified microsecond accuracy guarantee. |
| **Metrics Engine & Evaluator** | Rajdeep | Computes percentile distributions and evaluates deterministic SLO rules and reason codes. |
| **Artifact Store & Reporting** | Rajdeep | Persists raw JSONL records, manifests, reports, and ensures secret redaction. |
| **Shared Contracts** | Rajdeep | Pydantic v2 data models enforcing exact schemas across API, worker, CLI, and frontend. |

### The 11 Shared Contracts

1. `WorkloadSpec`: Defines the offered traffic profile.
2. `SLOSpec`: Defines non-negotiable performance thresholds.
3. `CandidateConfig`: Represents requested vs. effective read-back serving settings.
4. `ExperimentSpec`: Root specification bundling workload, SLO, space, and budget.
5. `RunRecord`: Tracks single execution metadata and execution status.
6. `RawRequestMeasurement`: Unaggregated event record with floating-point epoch timestamps; exact clock resolution is not guaranteed.
7. `MetricSet`: Aggregated performance indicators and load-generator health flags.
8. `FeasibilityResult`: Deterministic constraint-by-constraint audit and verdict.
9. `SearchResult`: Bounded exploration history, rankings, and stopping rationale.
10. `VerificationRecord`: Independent verification rerun audit and drift metrics.
11. `ReportArtifact`: Self-contained, immutable bundle published for users and judges.

---

## 9. The Four Kinds of State You Must Never Confuse

Most naive systems collapse execution state, data validity, feasibility, and verification into a single status string. SLOKern maintains **four distinct state domains**:

| State Domain | Question It Answers | Canonical State Enums | Example |
|---|---|---|---|
| **1. Execution Status** | Did the process and GPU run without crashing? | `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`, `CANCELLED` | `FAILED` (CUDA OOM) |
| **2. Evidence Validity** | Can we trust the collected measurements? | `VALID`, `INVALID`, `CONTAMINATED` | `CONTAMINATED` (Generator saturated) |
| **3. Feasibility Verdict** | Did valid evidence satisfy all hard SLOs? | `FEASIBLE`, `INFEASIBLE`, `INCONCLUSIVE` | `INCONCLUSIVE` (Insufficient samples) |
| **4. Verification State** | Did the winner pass the fresh rerun? | `NOT_RUN`, `VERIFYING`, `VERIFIED`, `VERIFICATION_FAILED`, `VERIFICATION_INCONCLUSIVE` | `VERIFIED` |

*That separation is what keeps the system honest.*

---

## 10. Architectural Roles and the Five Disciplines of Truth

While all engineering execution is unified under **Rajdeep** as sole technical owner, the system enforces five distinct architectural disciplines to ensure integrity:

* **1. Serving Reality:** Intended to validate runtime capability, verify parameter read-back, and record the environment fingerprint (`src/slokern/engine/serving/`). Current Nebius flag read-back remains blocked (`BLK-17`).
* **2. Measurement Credibility:** Captures request timestamps, arrival distribution, metric aggregation, and saturation signals (`src/slokern/engine/loadgen/`, `src/slokern/core/metrics/`). Microsecond clock accuracy is not established.
* **3. Decision Correctness:** Applies deterministic SLO rules and reason codes (`src/slokern/core/evaluator/`). Independent verification protocol and metric comparison are not implemented (`BLK-08`).
* **4. Search Intelligence:** Proposes legal candidate configurations within the declared budget and ranks feasible options against the declared objective (`src/slokern/core/search/`).
* **5. Architecture & Integration:** Ensures all subsystems adhere to shared contracts, produces inspectable reports, and maintains system-level defensibility.

---

## 11. What the Judges and Demo Audience See

The Cyberpunk Technical Command Center presents 7 coherent views:
1. **Overview / Command Center:** Active experiment, progress, selected model, environment fingerprint.
2. **Workload & SLO Builder:** Request distribution, arrival pattern, hard constraints, and budget limits.
3. **Search Space / Tuning Lab:** Legal parameter space and candidate allowlists.
4. **Live Experiment Monitor:** Real-time requests, throughput, latency distributions, and validity flags.
5. **Results / Candidate Comparison:** Feasibility table, objective ranking, trade-offs.
6. **Verification / Evidence:** Verification rerun audit, threshold drift, and `VERIFIED` status.
7. **Run Detail / Report:** Immutable specification, hardware metadata, and downloadable artifacts.

*Non-Negotiable Rule:* Mock fixtures and simulated runs are visibly labelled **DEMO DATA**. A simulated result must never be presented as a measured GPU benchmark.

---

## 12. Your 60-Second Explanation to Judges and Reviewers

> *"SLOKern is being built as an evidence-driven optimizer for LLM inference serving.
> The accepted model-family candidate is `Nemotron-3-Nano-30B-A3B` FP8, with exact model access and deployment still pending. The proposed Serverless/vLLM 0.12.0 profile and five-point matrix are not yet ratified or implemented. Current source uses a different 2×2 candidate matrix, and its Nebius adapter does not apply or read back vLLM launch flags. The default run allocation is one baseline, four candidates, and one verification, but budget overrides can consume the reserve.
> We preserve raw request-level measurements, derive metrics using explicit definitions—including offered load, achieved load, and generator saturation—and use a deterministic evaluator to classify candidates as feasible, infeasible, or inconclusive. The optimizer ranks only candidates supported by valid evidence that satisfy every hard SLO, using verified monetary cost when available or a clearly declared systems proxy otherwise.
> The product requirement is a fresh independent verification run and an auditable report. The current verification modules are stubs, so we will not claim a verified recommendation until that path has been implemented and run.
> Our goal is to produce the best eligible candidate found within the declared tested space and budget, with limitations stated plainly."*

---

### One Final Principle

**SLOKern's product is not the tuning algorithm alone. Its product is the entire chain from a declared requirement to a defensible recommendation.**  
*The search proposes; the measurements provide evidence; the evaluator decides feasibility; verification earns trust; and the report explains why the result deserves to be believed.*

