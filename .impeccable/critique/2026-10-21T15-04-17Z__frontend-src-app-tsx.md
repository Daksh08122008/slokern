---
target: entire SLOKern application
total_score: 33
max_score: 40
na_heuristics: 
p0_count: 1
p1_count: 2
target_identity: "file:C:\\Users\\paulr\\OneDrive\\DevArena\\slokern\\frontend\\src\\App.tsx"
target_fingerprint: "sha256:401933f1a43c76efec1d7a04e5ecc68fd6b9a4b03c0e0caf6a97b28d83e93c0c"
target_path: "C:\\Users\\paulr\\OneDrive\\DevArena\\slokern\\frontend\\src\\App.tsx"
timestamp: 2026-10-21T15-04-17Z
slug: frontend-src-app-tsx
closed: true
---
Method: dual-agent (A: 240c1db9-92d5-4bb1-b902-fb3d0d2665d6 · B: efd38446-11d3-4b80-b401-01002cb7b679)

#### Design Health Score

| # | Heuristic | Score | Key Finding |
|---|-----------|:-----:|-------------|
| 1 | Visibility of System Status | 4 | Flawless 4-domain state decoupling; persistent DEMO indicators; explicit spinner labels (`Evaluating...`, `Running rerun...`). |
| 2 | Match Between System and Real World | 3 | Authentic systems nomenclature (P95, KV cache, throughput floors). Deducted 1 pt for collapsing TTFT and ITL into single "P95 latency". |
| 3 | User Control and Freedom | 3 | Instant scenario switching; Escape key dismisses modals, search, and toasts. Deducted 1 pt for "Reset fields" button lacking undo/confirmation. |
| 4 | Consistency and Standards | 4 | Rigid token system; 100% tabular number formatting on telemetry; consistent button hierarchies (`primary`, `secondary`, `ghost`, `danger`). |
| 5 | Error Prevention | 3 | Pre-flight bounds enforcement (batch 1-128, concurrency 1-256); infeasible candidate verification button safely disabled. Deducted 1 pt for lack of inline input range flags before submission. |
| 6 | Recognition Rather Than Recall | 3 | Clear comparison cards with drift deltas; actual vs. limit headroom shown. Deducted 1 pt because SLO ceilings disappear when browsing the Tuning Lab matrix. |
| 7 | Flexibility and Efficiency of Use | 3 | Keyboard-navigable SVG time-series charts (ArrowLeft/Right/Home/End); clipboard copy buttons. Deducted 1 pt for lack of quick command palette (`Cmd+K`). |
| 8 | Aesthetic and Minimalist Design | 3 | High-density cyberpunk aesthetic; strict luminescence rationing (≤5%). Deducted 1 pt for metadata clutter in Candidate Inspector and Run Detail. |
| 9 | Help Users Recognize, Diagnose, and Recover from Errors | 4 | Industry-leading reason code clarity (`P95 latency 68 ms exceeds 50 ms ceiling by 18 ms`); dedicated "Restore demo evidence" button for stale states. |
| 10 | Help and Documentation | 3 | Clinical contextual notes on every panel; provenance statements. Deducted 1 pt for lack of inline documentation on KV cache precision trade-offs. |
| **Total** | | **33/40** | **Good** |

#### Design Specificity Verdict

**LLM Assessment (Unanchored Design Review):**
SLOKern successfully establishes a distinctive, high-rigor visual identity rooted in its **Obsidian Carbon × NVIDIA Phosphor** aesthetic (`#080A09` / `#76B900`). The domain logic—bounded 2×2 configuration matrices, independent verification drift gates, and microsecond latency constraints—permeates the micro-copy, status taxonomy, and state machines.
However, beneath the cyberpunk styling lies a **category-interchangeable SaaS dashboard structure**: a conventional 9-item left navigation rail (`WORKFLOW`, `OBSERVABILITY`, `SYSTEM`), standard 4-metric summary KPI rows, and disconnected tabs. A true GPU systems optimization workstation should operate as an iterative Pareto-frontier loop rather than a linear administrative portal. Furthermore, lumping TTFT (compute-bound) and ITL (memory-bandwidth-bound) into a single "P95 Latency" metric obscures the fundamental physics of LLM serving.

**Deterministic Scan (Automated Detector Evidence):**
The bundled detector identified **10 findings** (5 warning, 5 advisory, all categorized under `slop` in `frontend/src/styles.css`):
- **3 `side-tab` Warnings (L1567, L2484, L2928):** Asymmetric 2px/3px accent left borders. Most critically, **L2928 (`.inspector-reason`)** hardcodes a bright green (`var(--accent)`) left border on failure explanations, erroneously styling infeasible constraint violations with positive accent green!
- **2 `overused-font` Warnings (L1, L74):** Flagged `Inter`. *Contextually Defensible:* Inter was deliberately paired with `DM Mono` for its rock-solid tabular numeral support (`tnum 1`) and crisp rendering at small telemetry sizes (8.5–11px).
- **4 `bounce-easing` Advisories (L70, L71, L4326, L4756):** Flagged spring/bounce curves (`cubic-bezier(0.34, 1.56, ...)`). *Legitimate Smell:* The 1.56 bounce multiplier on toggle switches and toasts introduces cartoonish rubber-band motion that contradicts the clinical, instrument-grade aesthetic.
- **1 `codex-grid-background` Advisory (L685):** Flagged decorative grid-line background. *Intentional Feature with Tradeoff:* Explicitly requested in `AGENTS.md` ("subtle grid/glow details"), strictly bounded to the top 380px with a linear-gradient fade and ultra-faint 1.6% white opacity, toggled via workstation ambient settings.

**Visual Overlays:**
Local browser overlay injection was bypassed due to Windows sandbox AppContainer isolation on local loopback sockets; static AST analysis and production bundle verification (`npm run build`) confirmed 100% type safety and asset compilation with zero syntax errors.

#### Overall Impression
SLOKern delivers an exceptionally polished, serious, and credible systems interface that treats LLM inference optimization with scientific rigor. It decisively rejects the flimsy pastel gradients of generic web apps. Its biggest weakness is **cognitive overload and structural fragmentation**: operators must juggle 6+ candidate attributes across disjointed cards and tabs without an interactive Pareto-frontier visualization, while microscopic typography (8–9.5px) and low-contrast borders (1.4:1) strain readability during extended on-call sessions.

#### What's Working
1. **Unflinching Deterministic Integrity & 4-Domain State Decoupling:** Clean separation between Execution state, Telemetry stream type (live vs. simulated), Feasibility verdict, and Independent Verification verdict. Fixtures are persistently labeled `DEMO DATA`.
2. **Disciplined "Rarity of Luminescence" & Tactile Polish:** Restricting neon green (`#76B900`) strictly to verified winners and active controls preserves high cognitive contrast. Sub-220ms transitions, spring card compressions, and keyboard-driven time-series scrubbers give the deck an authentic hardware feel.
3. **Clinical, Actionable Reason Code Taxonomy:** Failure states display exact discrepancies (e.g., `P95 latency 68 ms exceeds 50 ms limit by 18 ms`, `Throughput falls 5.7k tok/s below target`, `P95 drift exceeds tolerance (+11 ms vs ≤ 5 ms limit)`).

#### Priority Issues

##### [P0] Microscopic Monospace Typography & Sub-Threshold Border Contrast
- **Why it matters:** Extensive typography between 8px and 9.5px across metadata, axes, and units, paired with 1.4:1 panel border contrast (`#263124` on `#0E120F`), violates WCAG AA legibility and causes panel hierarchy to collapse into a muddy dark mass on standard IPS monitors.
- **Fix:** Enforce an 11px minimum floor on all monospace labels and table metadata; elevate panel border wireframes to `#334230` (achieving ≥3:1 non-text contrast).
- **Suggested command:** `/impeccable typeset`

##### [P1] Composite Latency Obscures Prefill (TTFT) vs. Decode (ITL) Mechanics
- **Why it matters:** In vLLM serving, batch size trade-offs split sharply between TTFT (compute-bound prompt prefill) and ITL (memory-bandwidth-bound token generation). Masking this behind a single "P95 Latency" prevents root-cause analysis of batch size and concurrency impacts.
- **Fix:** Decompose latency telemetry into `TTFT P95` (ms) and `ITL P95` (ms/token), displaying independent SLO headroom and threshold indicators for each.
- **Suggested command:** `/impeccable clarify`

##### [P1] Cognitive Overload in Candidate Comparison (Missing Pareto Frontier)
- **Why it matters:** 4 multi-attribute cards in the Tuning Lab force operators to hold 6+ parameters in working memory across disjointed layouts, violating Cowan's working memory rule (≤4 chunks) and slowing decision velocity under production incidents.
- **Fix:** Introduce an interactive 2D Pareto-frontier trade-off plot (X: P95 Latency ceiling, Y: Throughput floor) where candidate configurations appear as coordinate nodes with hover diffs.
- **Suggested command:** `/impeccable layout`

##### [P2] Elimination of AI-Cliche Side-Tab Accent Borders & Cartoony Bounce Easing
- **Why it matters:** Detected by automated scanner: asymmetric thick left borders (`border-left: 3px solid var(--accent)`) on `.orbit-center`, `.trust-note`, and especially `.inspector-reason` (where failure reasons erroneously show bright green borders!). Exaggerated 1.56 bounce easing on toggle switches and toasts feels frivolous.
- **Fix:** Replace side-tabs with symmetric 1px borders and status-aware indicator badges; replace bounce easing with crisp exponential decay (`cubic-bezier(0.16, 1, 0.3, 1)`).
- **Suggested command:** `/impeccable polish`

##### [P2] Screen Reader Inaccessibility on SVG Telemetry Scrubber
- **Why it matters:** `LineChart` keyboard arrow scrubbing updates a visual HUD tooltip, but provides no dynamic screen reader live region, leaving low-vision or keyboard-only engineers unable to perceive time-series trends.
- **Fix:** Add a visually hidden `aria-live="polite"` element inside `LineChart` announcing `${activeSample.time}: ${activeSample.val} ${activeSample.unit}, ${activeSample.delta}` on keyboard focus change.
- **Suggested command:** `/impeccable audit`

##### [P2] Lack of Production-Ready Serving Config / CLI Flag Export
- **Why it matters:** Winning candidate displays abstract configuration numbers (Batch 16, Concurrency 32, FP8) without actionable runtime syntax, forcing engineers to manually transcribe values into deployment manifests.
- **Fix:** Provide a "Copy Serving Flags" button copying pre-formatted CLI arguments (`vllm serve ... --max-num-seqs 32 --kv-cache-dtype fp8`) directly to the clipboard.
- **Suggested command:** `/impeccable optimize`

#### Persona Red Flags
- **Alex (Impatient Power User / Systems Platform Engineer):** Lacks production-ready CLI export (`vllm serve` arguments); forced to mouse through a 9-item sidebar without a quick command palette (`Cmd+K`); cannot view raw request latency distribution histograms.
- **Jordan (Confused First-Timer / ML App Developer):** Cannot immediately parse why Candidate C-04 (P95: 42 ms, well below 50 ms limit) is marked `INFEASIBLE` because the throughput floor breach is buried in fine print; lacks contextual guidance on FP8 vs. FP16 KV cache accuracy risks.
- **Sam (Accessibility-Dependent User: Keyboard-Only / Low-Vision):** Sub-10px monospace typography (8px–9.5px) is unreadable without extreme zoom; 1.4:1 border contrast blurs panel boundaries; chart scrubber lacks screen-reader announcements.
- **Elena (Production SRE / On-Call Incident Responder):** Cannot distinguish whether a latency spike is prefill or decode; lacks an emergency "Rollback to Baseline (C-01)" action when verification fails; cannot overlay baseline and rerun latency curves directly.

#### Minor Observations
1. **False-Positive Notification Pip:** The header bell icon displays a permanent green alert pip even when there are no unread system notifications.
2. **Chart SVG X-Axis Origin Clipping:** `LineChart`'s first coordinate at $x=0$ clips slightly against the left border of the viewport due to `transform="translate(5 9)"`.
3. **Destructive Reset Lacks Guardrail:** The "Reset fields" button in Workload Builder clears custom parameters immediately without a confirmation prompt or undo banner.
4. **Lifecycle Step Line Wrapping:** The 7-step horizontal lifecycle rail in Run Detail drops connector lines awkwardly on intermediate viewports between 780px and 960px.

#### Questions to Consider
1. *What if SLOKern collapsed its 9-page administrative navigation into an integrated 3-stage workbench (Define Envelope → Sweep Matrix → Verify & Export)?*
2. *If independent verification is the core product moat, why is it sequestered on Page 6 rather than docked as a persistent verification gate inside the primary Decision Hero?*
3. *What if SLOKern quantified "Cost per 1M Verified Tokens" alongside P95 latency to give infrastructure leaders an empirical capital efficiency metric?*
