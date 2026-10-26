# AGENTS.md — SLOKern Engineering Instructions

> **Product:** SLOKern — *Optimize inference. Verify performance.*  
> **Purpose:** Repository-wide instructions for human contributors and coding agents.  
> **Authority:** Follow this file together with README.md, ROADMAP.md, and any more-specific AGENTS.md files in subdirectories.

## 1. Mission and non-negotiable principles

SLOKern is an SLO-aware LLM inference optimization system. Given a declared workload and service-level objectives (SLOs), it measures a bounded set of serving configurations, selects the lowest-cost evidenced configuration that satisfies the declared constraints, and independently verifies the recommendation.

**Core principle:** Do not guess the optimal configuration. Find it experimentally, then verify it.

- Keep the MVP focused: one model, one serving environment, a small legal configuration space, reproducible experiments.
- Prefer measured evidence over theoretical claims or attractive demo numbers.
- Report the best verified candidate **among configurations tested in the declared search space and environment**. Never claim global optimality.
- Deterministic code owns metrics, constraint evaluation, experiment-budget enforcement, candidate selection policy, and final verification verdicts.
- An LLM may help draft workload specifications, suggest candidates, or explain results. It must not override measured data, hard constraints, or deterministic verdicts.
- Never present mock, estimated, stale, or synthetic values as live measurements. Label frontend fixtures and simulated runs **DEMO DATA**.
- Do not claim a feature, command, integration, model, deployment, price, or benchmark result works until it has been run and verified in the target environment.

## 2. Before making changes

1. Read the relevant sections of README.md and ROADMAP.md.
2. Inspect the actual repository, existing conventions, dependencies, and test commands before choosing an implementation.
3. Check for more-specific AGENTS.md files and obey the closest applicable instructions.
4. Identify the owning workstream and its contract before changing shared interfaces.
5. State assumptions explicitly. If a decision materially affects metrics, correctness, security, or reproducibility, document it rather than silently guessing.
6. Keep changes scoped to the task. Do not introduce a framework, service, abstraction, or dependency without a concrete need.

The layout in README.md is a proposed structure, not proof that those directories or modules already exist. Adapt to the repository as it actually stands.

## 3. Architecture boundaries

Prefer a **modular monolith plus a controlled experiment worker** for the MVP unless the real platform imposes a different shape.

Keep responsibilities explicit:

- **Dashboard:** specification controls, tuning controls, progress, comparison, verification evidence, and reports.
- **Control plane/API:** validate requests, enforce budgets, manage experiment lifecycle and cancellation, and expose artifacts.
- **Serving adapter:** apply only supported runtime settings; report what was actually applied and capture environment metadata.
- **Load generator:** implement the declared arrival pattern and capture request-level timings.
- **Metrics engine:** derive documented metrics from raw observations.
- **Feasibility evaluator:** apply versioned, deterministic rules to evidence.
- **Search controller:** generate legal candidates, stay within budgets, track stopping conditions, and retain selection rationale.
- **Verification runner:** rerun the selected configuration with a new run ID and a defined protocol.
- **Report generator:** publish reproducible specifications, results, verdicts, and limitations.
- **Optional AI planner/explainer:** advisory only; never the source of truth for numeric results or pass/fail status.

Keep dashboard/API activity out of the measured request-generation path where practical. Do not allow UI polling, logging overhead, or background work to silently alter benchmark conditions.

## 4. Contracts and data integrity

- Define shared schemas before parallel implementation. Keep field names, units, nullability, enum values, and versioning consistent across API, worker, CLI, frontend, fixtures, and reports.
- Prefer explicit typed models and validation at system boundaries.
- Store the workload specification, SLO thresholds, candidate configuration, runtime/environment details, measurement protocol, timestamps, software versions, and artifact references with every run.
- Preserve raw measurements. Derived metrics must be traceable to raw evidence and a documented calculation.
- Distinguish **offered load** from **achieved load**; do not imply the target rate was delivered if it was not.
- Use unique run and verification IDs. A verification run must not be a renamed or copied search result.
- Record candidate configuration values that were requested and those actually applied. Fail or mark the run invalid when required settings cannot be applied.
- Make units explicit in code, schemas, UI labels, logs, and reports. Avoid ambiguous fields such as latency when a specific metric is meant.
- Version decision policies and metric definitions when changes could alter results.
- Never silently drop failed requests, warm-up observations, outliers, or invalid samples. Define and document exclusions in the protocol.
- Keep secrets, tokens, private endpoints, and credentials out of source control, logs, screenshots, fixtures, and reports.

## 5. Metrics, SLOs, and verdicts

Use the definitions in the project documentation as the source of truth. If a definition is not yet settled, flag it as an open decision and do not invent incompatible implementations.

Expected metric families include:

- Time to first token (TTFT)
- Inter-token latency (ITL), with aggregation method defined
- End-to-end latency
- Request throughput and output-token throughput
- Offered and achieved load
- Error rate
- Cost per request or token, with pricing assumptions disclosed

Use the following verdict semantics unless a documented, reviewed policy supersedes them:

- **FEASIBLE:** valid, sufficient evidence supports every required hard constraint passing.
- **INFEASIBLE:** valid evidence shows at least one hard constraint failing.
- **INCONCLUSIVE:** evidence is invalid, insufficient, or too uncertain to support a reliable decision.
- **EXECUTION ERROR:** the experiment could not complete correctly. Track this separately from an SLO failure.

Additional rules:

- A missing metric is not a passing metric.
- Invalid or incomplete runs cannot win candidate selection.
- A candidate must satisfy every required hard constraint before cost ranking.
- State whether latency constraints use p50, p95, p99, a maximum, or another declared statistic.
- Define sample size, warm-up, run duration, repetitions, aggregation, and uncertainty handling in the experiment protocol.
- Compare candidates under equivalent workloads and controlled conditions.
- Keep the objective function and tie-breaking behavior deterministic and documented.
- Cost estimates must disclose source, currency, time basis, included resources, and assumptions. Do not fabricate prices.

## 6. Search and experiment-budget safety

- Validate the workload, legal parameter ranges, resource limits, and total experiment budget before launching work.
- The search space must contain only parameters the serving adapter can actually apply and observe.
- Bound candidate count, run duration, retries, concurrency, and total compute/time expenditure.
- Make search behavior reproducible from a saved specification, policy version, seed (where relevant), and candidate history.
- Preserve baseline results and explain why candidates were selected, skipped, rejected, or stopped.
- Treat adaptive search as optional until a correct baseline-to-verification path works end to end.
- Add cancellation and failure handling where the execution model supports them; cancellation must not be reported as a successful run.
- Avoid runaway loops, unbounded retries, uncontrolled load, or accidental expensive runs. Default to a small smoke test.
- Do not modify production deployments automatically in the MVP.

## 7. Independent verification

Verification is a product feature, not a decorative status badge.

- Rerun the chosen configuration using a fresh run ID and the documented verification protocol.
- Capture the actual applied configuration and environment for verification.
- Recompute metrics from verification evidence; do not reuse search-run metrics as verification results.
- Apply the deterministic evaluator to the verification evidence.
- If verification fails or is inconclusive, report that honestly and retain the original search result for diagnosis.
- Show the selected candidate, search evidence, verification evidence, thresholds, differences, and final verdict in the UI and report.
- A verified recommendation means it passed the defined verification protocol—not that it is universally optimal or guaranteed for all future traffic.

## 8. Dashboard and UX

The intended visual direction is a high-quality, cyberpunk-inspired technical command center: midnight/near-black surfaces, electric cyan accents, restrained violet, crisp typography, subtle grid/glow details, and strong information hierarchy.

Visual polish must not compromise readability, accessibility, or trust.

- Clearly distinguish live, queued, running, completed, failed, cancelled, stale, and demo states.
- Label all synthetic fixtures and simulated experiment results **DEMO DATA** in a persistent, unambiguous way.
- Never animate a fake live run or show fabricated “verified” results without a clear demo label.
- Show units, thresholds, run IDs, budget usage, and data freshness near the values they describe.
- Make constraint failures and inconclusive evidence legible; do not rely on color alone.
- Provide empty, loading, error, and partial-data states.
- Keep controls intuitive and validate inputs before expensive work begins.
- Avoid charts that imply unsupported precision or hide failed candidates.
- Use accessible contrast, keyboard-friendly controls, and clear focus states.
- Do not display a cost or performance number without identifying whether it is measured, calculated, estimated, or demo data.

## 9. Implementation and code quality

Follow the repository's established language, formatter, linter, package manager, and naming conventions. Do not invent commands or assume a toolchain without checking the project.

- Prefer small, cohesive modules with single responsibilities and explicit interfaces.
- Keep measurement, policy, search, serving integration, and presentation logic separated.
- Use clear names and explicit units; avoid unexplained abbreviations.
- Handle external process failures, timeouts, malformed responses, missing fields, and partial artifacts.
- Avoid swallowing exceptions. Errors should retain enough context to diagnose the failing stage without leaking secrets.
- Do not add dependencies when a small standard-library implementation is sufficient.
- Do not weaken types, validation, tests, or lint rules just to make a failing check pass.
- Do not leave placeholder implementations that appear production-ready. Mark unfinished paths clearly and fail safely.
- Avoid unrelated refactors and large generated files in focused changes.
- Keep comments useful: explain reasoning, constraints, and non-obvious behavior rather than narrating each line.

## 10. Testing and validation

Tests should prove behavior, not merely that code executes.

For a code change, run the narrowest relevant checks first, then broader checks when feasible. Use the repository's actual commands.

Expected test coverage as components mature:

- **Schemas/configuration:** valid inputs, invalid values, missing fields, boundary values, incompatible settings, and budget overflow.
- **Metrics:** hand-calculated fixtures, unit conversions, empty input, malformed records, percentile behavior, failed requests, and edge cases.
- **Evaluator:** each hard constraint independently passing/failing, multiple failures, missing metrics, invalid evidence, and inconclusive outcomes.
- **Search:** legal candidate generation, deterministic ranking, budget enforcement, duplicate prevention, stopping conditions, and no-feasible-candidate cases.
- **Serving adapter:** unsupported parameters, failed application, endpoint errors, timeouts, and accurate environment/configuration capture.
- **Load generation:** arrival pattern, request timing, offered versus achieved load, errors, warm-up handling, and repeatability.
- **Verification:** fresh run ID, independent metric computation, pass/fail/inconclusive cases, and failure reporting.
- **API/CLI/UI:** validation, lifecycle states, error paths, empty states, and consistent units/field names.
- **Integration:** a small, bounded end-to-end smoke test before any expensive run.

When reporting checks, distinguish:
- passed,
- failed,
- skipped,
- not run,
- blocked by unavailable hardware, credentials, quota, or environment.

Never claim tests passed unless they were actually run. Never claim real-GPU performance based only on mocks or local synthetic data.

## 11. CLI and API behavior

The intended CLI concept includes slokern verify; this is not evidence that the command is already implemented.

- Inspect existing CLI structure before adding commands.
- Provide clear help text, validated arguments, actionable errors, and nonzero exit codes for failures.
- Prefer machine-readable output for automation and human-readable summaries for interactive use.
- Make destructive, expensive, or long-running actions explicit.
- Provide a dry-run or plan mode when useful and feasible.
- Keep CLI, API, and UI behavior consistent by reusing the same schemas and decision logic.
- Do not duplicate evaluator logic in the frontend.

## 12. Security and operational safety

- Never commit .env files, credentials, access tokens, private keys, or secret-bearing logs.
- Use environment variables or the approved secret store; provide safe example configuration with placeholders.
- Validate external inputs and avoid shell interpolation of untrusted values.
- Apply request, runtime, retry, concurrency, and experiment-budget limits.
- Keep dependency versions and installation steps reproducible where the project supports lockfiles.
- Avoid exposing private endpoints, host details, or sensitive environment variables in public reports.
- Treat model output, remote responses, uploaded specifications, and generated text as untrusted input.
- Do not run expensive GPU experiments without checking budget and environment first.

## 13. Engineering ownership and execution model

Starting October 26, 2026, SLOKern operates under a **Strict Solo-Development and Solo-Execution Model**:

- **Rajdeep:** Sole technical owner, sole implementation owner, sole testing and verification owner, sole benchmarking and measurement owner, sole architecture and decision authority, sole integration and release authority, and sole documentation and hackathon submission owner.
- **Execution Model:** Independent solo execution, with no active collaborator workstreams.

Former contributors (Aman on serving, Rohan on search, Adriraj on benchmarking exploration, Daksh on boundary test exploration) contributed early design work in Phase 1 and Phase 2. They are not participating in current execution, and no ongoing tasks, gates, reviews, or deliverables are assigned to them. Rajdeep independently executes and verifies the complete minimum viable product.

### Subsystem Ownership Matrix

| Area | Accountable Owner | Status | Scope and Responsibilities |
|---|---|---|---|
| **Architecture & Technical Direction** | **Rajdeep** | ACTIVE (SOLO) | Scope boundaries, modular monolith design, system contracts (`src/slokern/contracts/`), and adherence to non-negotiable principles. |
| **Optimizer & Candidate Selection** | **Rajdeep** | ACTIVE (SOLO) | Bounded search space definition (2×2 matrix), canonical candidate hashing, search controller (`src/slokern/core/search/`), deterministic ranking logic, and selection rationale. |
| **Serving Integration & Runtime** | **Rajdeep** | ACTIVE (SOLO) | Serving runtime setup (vLLM / Nebius Cloud / Ollama local), serving adapters (`src/slokern/engine/serving/`), parameter read-back, preflight smoke testing, and environment fingerprinting. |
| **Benchmark Pipeline & Loadgen** | **Rajdeep** | ACTIVE (SOLO) | Workload fixtures, arrival models, subprocess load generator (`src/slokern/engine/loadgen/`), raw event capture (`RawRequestMeasurement`), and metric engine (`src/slokern/core/metrics/`). |
| **Verification & Evaluator Policy** | **Rajdeep** | ACTIVE (SOLO) | Deterministic feasibility evaluator (`src/slokern/core/evaluator/`), reason code taxonomy, independent verification runner (`src/slokern/core/verification/`), and automated decision verification test suites (`tests/contract/test_verification_independence.py`). |
| **CI, API & End-to-End Validation** | **Rajdeep** | ACTIVE (SOLO) | FastAPI control plane (deferred), CLI (`src/slokern/cli/`), contract testing, integration tests, and secret redaction. |
| **Documentation, Demo & Submission** | **Rajdeep** | ACTIVE (SOLO) | Living documentation, report generator (`src/slokern/engine/reporting/`), demo script, presentation rehearsal, and official hackathon submission package. |
| **Benchmark Integrity & Credibility** | **Rajdeep** | ACTIVE (SOLO) | Automated benchmark schema validation, required metadata checks, missing/inconsistent record detection, offered-vs-achieved load audits, comparison summaries, and automated test fixtures (`tests/contract/test_fixtures_validate.py`). |
| **Independent Decision Verification** | **Rajdeep** | ACTIVE (SOLO) | Automated independent verification test suite, hard SLO violation tests, feasibility boundary tests, missing/invalid measurement handling, failed experiment tests, and candidate selection verification. |

### Solo Execution & Verification Invariants

1. **Sole Accountable Owner:** Every subsystem is directly owned and implemented by Rajdeep.
2. **Autonomous Critical Path:** Critical-path functionality is fully executable and verifiable without external dependencies or human handoffs.
3. **Automated Verification:** Measurement credibility and decision correctness are enforced through automated tests (`tests/contract/test_fixtures_validate.py` and `tests/contract/test_verification_independence.py`), deterministic evaluator rules, and reproducible physical traces.
4. **Contract Discipline:** Shared interfaces (`src/slokern/contracts/`) are strictly maintained with Pydantic v2 schemas and committed JSON schemas.
5. **Physical Evidence Standard:** All technical claims must be grounded in physical artifacts (unaggregated JSONL traces, environment fingerprints); no mock success or simulated benchmarks may be presented as live evidence.
6. **Daily Delivery Alignment:** Follow `ROADMAP.md` for daily engineering objectives, deliverables, acceptance criteria, and fallbacks leading to the October 30, 2026, 10:00 AM PDT (10:30 PM IST) submission deadline. For the complete operational model, see `docs/ownership.md`.

## 14. Documentation and experiment artifacts

Update documentation when behavior, contracts, metrics, policy, setup, or workflow changes.

Relevant docs may include README.md, ROADMAP.md, architecture notes, experiment methodology, metric definitions, decision policy, deployment instructions, and demo script. Do not create every proposed document unless it is useful to the implementation.

Each completed experiment should retain enough metadata to interpret or reproduce it, including:

- run ID and status;
- workload and SLO specification;
- requested and applied configuration;
- model, runtime, software, and hardware/environment details;
- protocol, warm-up, duration, repetitions, and relevant seeds;
- raw measurements and derived metrics;
- errors, exclusions, and validity notes;
- evaluator and policy version;
- budget usage and cost assumptions;
- verification linkage and report/artifact references.

Keep bulky raw artifacts out of source control unless the project explicitly requires them. Use small, deterministic fixtures for tests and demos.

## 15. Definition of done

A task is done only when its applicable conditions are met:

- The implementation matches the agreed contract and scope.
- Inputs are validated and failures are handled safely.
- Relevant automated tests and checks have been run, with results reported honestly.
- Metrics and verdicts are deterministic, documented, and traceable to evidence.
- UI, API, CLI, fixtures, and reports agree on names, units, and states.
- Demo data is unmistakably labelled; no unsupported claims are made.
- Documentation and examples reflect the actual behavior.
- No secrets or unintended large artifacts were added.
- Integration with dependent components has been checked, or remaining blockers are explicit.

A visually complete frontend, passing unit tests alone, or a successful mock run does **not** establish that the real inference pipeline works.

## 16. Working protocol for coding agents

Coding agents working in this repository must adhere to the following protocol:

1. **Inspect Before Implementation:** Inspect existing code, schemas, and interfaces before proposing or writing code. Do not assume or extrapolate APIs without reading source files.
2. **Work on Bounded Tasks:** Focus on explicit, bounded tasks with defined acceptance criteria. Avoid sprawling, multi-component refactors.
3. **Prefer Minimal, Reversible Changes:** Write the smallest coherent change that accomplishes the task. Preserve established architecture boundaries and subsystem contracts.
4. **Preserve Established Contracts:** Never alter Pydantic models in src/slokern/contracts/ or existing enum values without an explicit requirement and synchronized updates across all consumers.
5. **Add or Update Tests:** When authorized to implement or modify code, add or update corresponding unit or contract tests.
6. **Run Validation & Report Honestly:** Execute the narrowest relevant checks first, followed by broader checks where tools exist. Distinguish between passed, failed, skipped, not run, or blocked by environment. Never claim checks passed if they were not run or failed.
7. **Disclose Uncertainty & Blockers:** Identify uncertainty, missing dependencies, or missing hardware credentials immediately instead of inventing synthetic solutions or masking gaps.
8. **Avoid Conflicting Edits:** Avoid simultaneous or overlapping edits to critical shared files (e.g., contracts, core evaluators).
9. **Provide Clear Diffs & Reports:** Summarize exact files modified, rationales, test outcomes, and any follow-up actions required.

If a required dependency or environment is unavailable, implement only what can be validated honestly, mark the limitation, and do not simulate a successful real-world result.

## 17. Conflict resolution

When instructions conflict, use this order:

1. System, platform, and security requirements.
2. More-specific AGENTS.md instructions in the relevant directory.
3. This repository-wide AGENTS.md.
4. Current, agreed architecture/contracts and decision-policy documentation.
5. ROADMAP.md for execution sequencing and ownership.
6. README.md for the public-facing overview.
7. Local conventions and reasonable engineering judgment.

If a conflict changes correctness, measurement validity, cost, or scope, raise it and document the decision rather than silently choosing a convenient interpretation.

## 18. Mandatory Progress Reconciliation After Every Agent Run

Every coding-agent run that inspects, modifies, tests, or otherwise advances the repository must complete a formal progress reconciliation before handing control back to the user or requesting review.

This rule is non-negotiable and applies across all run outcomes:
- **Successful runs:** Full Definition of Done achieved, tests pass.
- **Partial runs:** Incremental progress made, some acceptance criteria remain unmet.
- **Blocked runs:** Progress halted by an explicit defect, missing prerequisite, environment limit, or contract ambiguity.
- **Read-only / Audit runs:** No code was modified, but inspection, verification, or test discovery took place.

### 18.1 Required End-of-Run Actions

Before concluding an execution turn, the agent must perform the following ten reconciliation steps in sequence:

1. **Inspect final Git state:** Run git status --short --branch --untracked-files=all and git diff --check. Inspect all modified and untracked files.
2. **Identify affected task IDs:** Map changes to exact roadmap tasks (TASK-xx) and blockers (BLK-xx).
3. **Record files and implementation reality:** Detail added, modified, deleted, or investigated files along with actual implementation state (ABSENT, PARTIAL, IMPLEMENTED).
4. **Record actual test execution:** Capture exact commands executed and actual outcomes.
5. **Distinguish status outcomes accurately:** Differentiate PASS, FAIL, BLOCKED, NOT RUN, and PARTIAL. Never assume unrun checks pass.
6. **Update ROADMAP.md:** Update task progress records, executive summary tables, blocker states, and next actions backed by verified evidence.
7. **Update docs/implementation-status.md:** Reconcile subsystem reality, resolve or register blockers, or update implementation ratings whenever changes warrant.
8. **Justify status transitions:** Promote task status, validation levels, or exit criteria only when justified by current physical evidence.
9. **Record unresolved risks and blockers:** Explicitly state known defects, environment blockers, contract ambiguities, and risks.
10. **Emit standardized handoff summary:** Conclude the final response using the mandatory run handoff schema in Section 19.

### 18.2 Evidence Policy & Standards of Proof

- **Code existence is not completion:** A task is not complete merely because files or functions were written. It is complete only when its documented Definition of Done is fully satisfied.
- **Tests must be executed:** A test is not passing unless it was actually executed and its output verified in the current environment during the run.
- **Distinguish implementation from validation:** A component may be IMPLEMENTED while its validation level remains NONE, STATIC, UNIT, INTEGRATION, or LIVE.
- **Validation hierarchy:**
  - STATIC: compilation (compileall), linters (ruff), schema checks.
  - UNIT: isolated unit tests (pytest tests/unit).
  - INTEGRATION: multi-component tests (e.g., FakeServingAdapter pipeline).
  - LIVE: verified against external live infrastructure (e.g., Nebius Cloud GPU).
- **Task-specific acceptance required:** A general test suite pass does not substitute for task-specific acceptance tests and edge-case verification.
- **Unrun tests are NOT RUN:** Never infer or report that a test passed if it was skipped or omitted.
- **Persistent defect visibility:** Failing tests or broken invariants must remain visible as blockers (BLK-xx) until physically resolved or ratified as documented limitations.
- **Never fabricate evidence:** Never fabricate commit IDs, test counts, benchmark measurements, hardware fingerprints, or environment credentials.
- **Preserve evidence history:** Do not erase historical audit trails; update them with new verified timestamps and commits.
- **Persistent DEMO DATA labeling:** All synthetic fixtures, simulated latencies, and offline fake adapters must remain conspicuously labeled **DEMO DATA** and never reported as live benchmark measurements.

### 18.3 Scope & Git Safety Rules

- **Preserve unrelated work:** Never alter, overwrite, or discard unrelated user modifications or untracked files.
- **No destructive Git commands:** Do not run git reset --hard, git clean -fd, git checkout -- ., git stash, or similar destructive commands without explicit user instruction.
- **No unauthorized commits/pushes:** Do not run git commit or git push unless explicitly instructed by the user or required by the approved task scope.
- **Truth in working tree status:** Never claim a clean working tree unless git status --short returns zero modified or untracked files.
- **Minimal, bounded edits:** Keep documentation and code edits strictly scoped to the assigned task.

### 18.4 Failure & Interruption Protocol

If an agent run is interrupted, encounters unexpected errors, or fails to complete all acceptance criteria, the agent must still execute a best-effort reconciliation:

- Record exactly what was completed.
- Record what was attempted and remains incomplete.
- Document the exact failure, error traceback, or blocker preventing progress.
- Explicitly state which validation checks were run and which were NOT RUN.
- Disclose whether the repository was left in a partial, inconsistent, or broken state.
- State the single most effective next action to resume or recover work.
- Never conceal partial or failed work to present a false impression of success.

---

## 19. Mandatory Run Handoff Format

Every agent response concluding an execution block must conclude with a structured handoff formatted under the following schema:

markdown
### Run summary
- **Objective & Tasks:** [Primary goal and roadmap task IDs addressed (e.g. TASK-06)]
- **Run Outcome:** [COMPLETED | PARTIAL | BLOCKED | NO CHANGE]

### Repository changes
- **Files Modified:** [List of modified files, or 'None']
- **Files Added:** [List of new files created, or 'None']
- **Files Deleted:** [List of files removed, or 'None']
- **Documentation Reconciled:** [Roadmap, implementation-status, or other docs updated]

### Validation evidence
- **Commands Executed:** [Exact commands run in virtualenv/shell]
- **Results:** [Exact pass/fail/skip counts and execution duration]
- **Checks Skipped / Not Run:** [Tests or validations omitted, with rationale]
- **Git Diff & Working Tree:** [Output of git diff --check and git status]

### Task status changes
- **[TASK-xx]:** [Old Status] -> [New Status] ([Validation Level])
- **Evidence:** [Exact test command, commit, or artifact validating the transition]

### Outstanding issues
- **Blockers & Defects:** [Active BLK-xx blockers or newly discovered issues]
- **Contract / Architecture Risks:** [Any open decisions or contract concerns]

### Next action
- **Immediate Next Step:** [One specific, actionable next task with Task ID, target files, and primary deliverable]

