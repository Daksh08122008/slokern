---
name: SLOKern
version: "2.1"
description: Obsidian Black × NVIDIA Green — a precision instrument with an Apple-grade finish
colors:
  canvas: "#080A09"
  surface: "#0E120F"
  raised: "#151B15"
  elevated: "#1D251E"
  hover: "#1F281E"
  border: "#263124"
  border-strong: "#384635"
  border-focus: "#95D500"
  text-primary: "#F0F3EF"
  text-secondary: "#A0AAA0"
  text-tertiary: "#7A857B"
  text-muted: "#727D73"
  primary: "#76B900"
  primary-bright: "#95D500"
  warning: "#E9B949"
  error: "#FF5555"
  info: "#8F9AA5"
  info-border: "#394053"
  glass-chrome: "rgba(14, 18, 15, 0.72)"
  glass-float: "rgba(29, 37, 30, 0.78)"
  glass-hairline: "rgba(240, 243, 239, 0.08)"
  glass-highlight: "rgba(240, 243, 239, 0.05)"
  scrim: "rgba(8, 10, 9, 0.62)"
  primary-wash: "rgba(118, 185, 0, 0.12)"
  error-wash: "rgba(255, 85, 85, 0.12)"
  warning-wash: "rgba(233, 185, 73, 0.12)"
  info-wash: "rgba(143, 154, 165, 0.12)"
typography:
  hero:
    fontFamily: "'Inter Display', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(56px, 11vw, 144px)"
    fontWeight: 700
    lineHeight: 0.95
    letterSpacing: "-0.05em"
  display-stage:
    fontFamily: "'Inter Display', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(32px, 3.6vw, 48px)"
    fontWeight: 700
    lineHeight: 1.08
    letterSpacing: "-0.04em"
  headline-stage:
    fontFamily: "'Inter Display', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "28px"
    fontWeight: 650
    lineHeight: 1.15
    letterSpacing: "-0.03em"
  body-stage:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "16px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "-0.005em"
  label-stage:
    fontFamily: "'DM Mono', 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "12px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.08em"
  display:
    fontFamily: "'Inter Display', Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "clamp(21px, 2.2vw, 30px)"
    fontWeight: 700
    lineHeight: 1.15
    letterSpacing: "-0.035em"
  headline:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "20px"
    fontWeight: 650
    lineHeight: 1.25
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "15px"
    fontWeight: 600
    lineHeight: 1.35
    letterSpacing: "-0.015em"
  body:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
    fontSize: "13px"
    fontWeight: 400
    lineHeight: 1.5
    letterSpacing: "normal"
  label:
    fontFamily: "'DM Mono', 'SF Mono', Menlo, Consolas, monospace"
    fontSize: "11px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.06em"
rounded:
  xs: "3px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "10px"
  stage: "16px"
  hero: "22px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
  stage-gap: "48px"
  stage-section: "96px"
motion:
  instant: "0ms"
  fast: "120ms"
  base: "200ms"
  slow: "360ms"
  stage: "1400ms"
  ease-standard: "cubic-bezier(0.32, 0.72, 0, 1)"
  ease-exit: "cubic-bezier(0.4, 0, 1, 1)"
  spring-snappy: "stiffness 520, damping 42, mass 1"
  spring-ui: "stiffness 380, damping 34, mass 1"
  spring-stage: "stiffness 140, damping 20, mass 1"
glass:
  chrome-blur: "blur(28px) saturate(150%)"
  float-blur: "blur(20px) saturate(140%)"
shell:
  context-bar-height: "44px"
  status-bar-height: "28px"
  sidebar-width: "244px"
  drawer-width: "420px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "0 15px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.primary-bright}"
  button-primary-stage:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.pill}"
    padding: "0 24px"
    height: "44px"
  button-secondary:
    backgroundColor: "{colors.raised}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.md}"
    padding: "0 13px"
    height: "34px"
  button-ghost:
    backgroundColor: "transparent"
    textColor: "{colors.text-secondary}"
    rounded: "{rounded.md}"
    padding: "0 10px"
    height: "30px"
  card-panel:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.xl}"
    padding: "16px 20px"
  card-stage:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.stage}"
    padding: "24px 28px"
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "13px 15px"
  context-bar:
    backgroundColor: "{colors.canvas}"
    textColor: "{colors.text-secondary}"
    rounded: "0"
    padding: "0 16px"
    height: "44px"
  sidebar:
    backgroundColor: "{colors.glass-chrome}"
    textColor: "{colors.text-secondary}"
    rounded: "0"
    padding: "12px"
  status-bar:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-secondary}"
    rounded: "0"
    padding: "0 12px"
    height: "28px"
  drawer:
    backgroundColor: "{colors.elevated}"
    textColor: "{colors.text-primary}"
    rounded: "0"
    padding: "20px"
  floating-layer:
    backgroundColor: "{colors.glass-float}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "8px 12px"
---

# Design System: SLOKern (v2.1)

## Overview

**Creative North Star: "The Verified Instrument"**

v1 described a cyberpunk command center. v2.1 keeps every piece of its rigor (the obsidian palette, the rationed green, tabular telemetry, provenance disclosure) and changes the *finish*: calm surfaces, generous space where it matters, glass only where something floats, and motion that feels physical rather than decorative. The Apple-grade quality is in the restraint, not in decoration.

The product is judged by two audiences at once: a judge who sees it for three minutes, and an engineer who lives in it for three hours. v2.1 serves both with a **two-tier system**. The **Stage** tier is airy, large, and cinematic, and it carries the first impression. The **Inspector** tier is dense, monospaced, and exact, and it carries the work. Both tiers share one palette, one grammar of state, and one rule: *nothing is shown as verified until it is verified.*

**Locked decisions**
- Audience: judges and engineers equally, demo-first first impression.
- Identity: keep the Obsidian × NVIDIA Green palette; change the feel (space, blur, motion).
- Density: two tiers, airy Stage plus dense Inspector, with hybrid screens (Stage header over Inspector body).
- Material: glass on the sidebar, scroll-edge toolbar, and floating layers only. Data and the inspector drawer stay solid.
- Motion: data is instant; space is spring-driven; one cinematic reveal for a verified winner.
- Type: Inter for UI, Inter Display for heroes, DM Mono first for telemetry.
- Theme: dark only. No light-theme tokens are defined.
- Destinations: Overview, Workloads, Experiments, Tuning Lab, Verification, Reports.
- Honesty: no invented numbers, no fake controls, no fabricated capabilities.

**Key Characteristics**
- **Obsidian Tonal Architecture:** near-black steps (`#080A09` to `#1D251E`) create depth without noisy shadows.
- **Phosphor Precision:** NVIDIA green is an instrument-grade signal, reserved for proven outcomes and focused controls.
- **Two Tiers, One Language:** Stage and Inspector differ in scale and spacing, never in color, state grammar, or terminology.
- **Glass Is Chrome:** translucency is for navigation and floating layers. Data always sits on solid surfaces.
- **Earned Reveal:** the signature animation plays only for a derived verified winner.
- **Explicit Provenance:** `DEMO DATA` is persistent and can never be covered, dismissed, or animated away.

## Colors

The palette is unchanged from v1 apart from the derived tokens listed below. These values are the only ones in use. The following earlier or blueprint values are **retired and must not appear**: `#151916`, `#1D241F`, `#252E27`, `#6E7C70`, `#EF4444`, `#F59E0B`, `#38BDF8`, `#263328`.

### Primary
- **NVIDIA Signal Green** (`#76B900`): verified-result badges, the winner border and glow, the headroom segment of the SLO gauge, the winning series, primary buttons, the scrubber crosshair.
- **Phosphor Bright Green** (`#95D500`): `:focus-visible` rings, primary hover, critical chart highlight dots.

### Neutral
- **Obsidian Canvas** (`#080A09`): the foundation.
- **Carbon Surface** (`#0E120F`): panels, cards, the status bar. Always solid.
- **Raised Charcoal** (`#151B15`): secondary buttons, input fills, table headers, the segmented-control track, the active sidebar item.
- **Elevated Slate** (`#1D251E`): the slide-over drawer, the segmented-control thumb, overlay fallback fill.
- **Border Wireframe** (`#263124`) and **Border Strong** (`#384635`): structural lines on solid surfaces; strong is for active edges and selected items.
- **Glacier Text** (`#F0F3EF`): primary text, about 17.5:1 on canvas.
- **Terminal Secondary** (`#A0AAA0`): labels and secondary fields; at least 6.5:1 on every surface including elevated.
- **Tertiary Text** (`#7A857B`): tertiary notes on Surface and Raised, about 4.9:1 and 4.6:1.
- **Muted Oxide** (`#727D73`): canvas only, about 4.6:1. On Carbon Surface it measures about 4.4:1 and fails AA for small text.

### Semantic
- **Telemetry Crimson** (`#FF5555`): constraint failures, drift breaches, errors.
- **Warning Amber** (`#E9B949`): inconclusive, stale, undeclared tolerance, budget exhausted.
- **Status Cyan** (`#8F9AA5`, border `#394053`): simulated and demo tags **only**. It never signals feasibility or any result state.

### Derived Tokens
Glass Chrome (`rgba(14,18,15,0.72)`), Glass Float (`rgba(29,37,30,0.78)`), Glass Hairline (`rgba(240,243,239,0.08)`), Glass Highlight (`rgba(240,243,239,0.05)`), Scrim (`rgba(8,10,9,0.62)`), and the four 12% washes for green, crimson, amber, and cyan.

### Named Rules
**The Rarity of Luminescence Rule.** Green occupies at most 8% of any viewport. When everything glows, nothing is critical.

**The One Green Moment Rule.** At any instant, at most one *luminous* green element (glow, filled bar, or animated ring) is the focal point of a view. Static green text, badges, and icons do not count.

**The Not-Green-by-Default Rule.** Active navigation, selected cards, active tabs, and selected segments are **not** green. Active navigation uses a Raised fill, primary text, and a 6px green pill dot. Selection uses Border Strong plus the inner highlight. Only a **verified winner** earns the green border and glow.

**The Text Surface Rule.** Muted Oxide on canvas only. Tertiary on Surface and Raised only. On Elevated Slate and any glass layer, use Secondary or Primary. Every text/surface pair is at least 4.5:1, and verification is numerical, not by eye.

## Typography

**Hero and Display (Stage):** `Inter Display`. Implementation: load Inter 4 with the `opsz` axis and set `font-variation-settings: "opsz" 32` for any text at 24px or larger; prefer the static Inter Display family when available. Text below 24px uses the text cut.
**Interface:** `Inter`.
**Telemetry:** `DM Mono` **first**, then `SF Mono`, Menlo, Consolas, monospace. DM Mono comes first so numbers render identically on every machine a judge might use. Self-host or bundle font files when the repository already does; do not add a runtime CDN dependency without noting it.

### Hierarchy

| Tier | Role | Spec |
|---|---|---|
| Stage | **Hero numeral** | Inter Display 700, `clamp(56px, 11vw, 144px)`, lh 0.95, tracking `-0.05em`, tabular. Unit suffix at 0.28em in Terminal Secondary. |
| Stage | **Display** | Inter Display 700, `clamp(32px, 3.6vw, 48px)`, lh 1.08, tracking `-0.04em` |
| Stage | **Headline** | Inter Display 650, 28px, lh 1.15, tracking `-0.03em` |
| Stage | **Body** | Inter 400, 16px, lh 1.5 |
| Stage | **Label** | DM Mono 500, 12px, uppercase, tracking `0.08em` |
| Inspector | **Display** | Inter Display 700, `clamp(21px, 2.2vw, 30px)`, tracking `-0.035em` |
| Inspector | **Headline** | Inter 650, 18–20px, tracking `-0.025em` |
| Inspector | **Title** | Inter 600, 14–15px, tracking `-0.015em` |
| Inspector | **Body** | Inter 400, 12–13px, lh 1.5 |
| Inspector | **Label / Telemetry** | DM Mono 500, **11px absolute floor** for every label, unit, axis tick, and table header, tracking `0.06em` |

### Named Rules
**The Absolute Tabular Rigor Rule.** Every metric value, percentile, latency delta, rate, and timestamp declares `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1;` and carries an explicit unit (`ms`, `k tok/s`, `GB`, `req/min`). Naked numbers are prohibited. Stage numerals use Inter Display with `tnum`; Inspector numerals use DM Mono.

**The Two Tiers Rule.** A view region is either Stage or Inspector, and the boundary is visible. Stage uses 16px body, 48px gaps, `stage` radius, and 44px targets. Inspector uses 13px body, DM Mono telemetry, and 34px controls (24px minimum). Hybrid screens use a Stage header above an Inspector body. Never mix scales inside one panel.

## Layout

The persistent workstation shell stays. It has **no window controls** (no traffic-light buttons): they are nonfunctional in a browser and would break the no-fake-controls rule.

```
+----------------------------------------------------------------------------------------+
| Context bar: SLOKern | Exp: <real id> | [Runtime profile] [real actions]    [DEMO DATA] |
+----------------+-----------------------------------------------------------------------+
| SIDEBAR (glass)| WORKSPACE HEADER: title, provenance, actions                          |
| Overview       +-----------------------------------------------------------------------+
| Workloads      | MAIN: Stage hero (Overview) / Inspector content                       |
| Experiments    |                                                                       |
| Tuning Lab     +-----------------------------------------------+-----------------------+
| Verification   |                                               | SLIDE-OVER DRAWER     |
| Reports        |                                               | (solid, optional)     |
+----------------+-----------------------------------------------+-----------------------+
| Status bar: [DEMO DATA] | Scenario | (real health only) | Hotkeys 1-6                    |
+----------------------------------------------------------------------------------------+
```

- **Context bar (44px):** product mark, real experiment ID, runtime profile, real actions only. The `DEMO DATA` chip lives here at the top of the layer stack.
- **Main shell:** `calc(100% - var(--sidebar-width))`, padding 24px (desktop), 16px (tablet), 10px (mobile). Stage regions center a column at `max-width: 1200px`.
- **Stage rhythm:** 48px between blocks, 96px between major sections, one idea per viewport on the Overview.
- **Inspector rhythm:** 4 to 32px spacing; asymmetric grids `minmax(0, 1.3fr) minmax(280px, 0.7fr)`.
- **Touch targets:** Stage controls at least 44×44px; Inspector controls at least 24×24px (WCAG 2.2 AA) and 34px tall where space allows.

### Responsive Contract

| Width | Behavior |
|---|---|
| > 1280px | 244px glass sidebar; the drawer docks beside the content |
| 1050–1280px | 218px sidebar |
| ≤ 1050px | icon-only 66px glass spine; the drawer becomes a right sheet over content with a Scrim; two equal columns |
| ≤ 780px | single column; the drawer is a full-width sheet; the status bar condenses to the `DEMO DATA` chip and scenario selector |
| ≤ 520px | slim 50px sidebar; condensed context bar |
| 360px | **zero horizontal page overflow**; tables scroll inside internal `.table-scroll` ports; the hero numeral's 56px clamp floor still fits |

### Screen Tier Map

| Destination | Tier |
|---|---|
| Overview | Stage |
| Workloads | Inspector |
| Experiments | Inspector body, Stage-style page header |
| Tuning Lab | Hybrid: Stage header, master-detail Inspector body |
| Verification | Hybrid |
| Reports | Inspector |

### Hotkeys
`1`–`6` switch destinations in sidebar order. They are ignored while focus is in an input, textarea, select, or contenteditable element, and when any modifier key is held. `Esc` closes the drawer or any floating layer. `R` replays the reveal while the Overview is focused. Show the hint in the status bar.

## Elevation & Depth

- **Level 0 (Canvas):** `#080A09` plus the Ambient Field.
- **Level 1 (Panels):** `#0E120F`, `1px solid #263124`, `0 1px 0 rgba(240,243,239,0.03) inset, 0 10px 30px rgba(0,0,0,0.42)`. **Solid, always.**
- **Level 2 (Cards, secondary controls):** `#151B15`, `1px solid #263124`.
- **Level 3 (Floating glass):** Glass Float, `backdrop-filter: blur(20px) saturate(140%)`, `1px solid` Glass Hairline, inner top highlight, `0 12px 32px rgba(0,0,0,0.45), 0 2px 6px rgba(0,0,0,0.35)`.
- **Level 4 (Modal):** Level 3 plus Scrim behind.
- **Chrome (sidebar, scroll-edge toolbar):** Glass Chrome, `backdrop-filter: blur(28px) saturate(150%)`, Glass Hairline on the inner edge only.
- **Drawer:** solid Elevated Slate, `1px solid #384635` leading edge, Level 3 shadow. **Not glass**, because it carries dense data.

### Ambient Field
A fixed layer behind the shell: `radial-gradient(60% 50% at 72% 0%, rgba(118,185,0,0.045), transparent 70%)` plus a neutral lift `radial-gradient(50% 40% at 0% 100%, rgba(240,243,239,0.025), transparent 70%)`. The green spotlight counts toward the 8% budget.

### Border Geometry
Solid surfaces: `1px solid #263124` (Border Strong for active edges). Glass: the translucent Glass Hairline. **Never mix the two definitions on one element.** Focus rings are 2px and are the only 2px stroke.

### Named Rules
**The Glass Is Chrome Rule.** Glass is for navigation and floating layers. Tables, chart plot areas, metric values, and drawer content sit on solid surfaces.

**The Legibility Floor Rule.** Glass fills are at least 72% opaque. If you lower the opacity for effect, you have broken the contract.

**The State-Driven Luminescence Rule.** Glow (`0 0 20px rgba(118,185,0,0.14)`) is forbidden on static elements. It activates only for a verified winner, an actively focused control, or an active telemetry crosshair.

**Fallbacks (required).** `@supports not (backdrop-filter: blur(1px))`, `prefers-reduced-transparency: reduce`, `prefers-contrast: more`, and `forced-colors: active` swap glass for solid Elevated Slate (floating) or Carbon Surface (chrome) with Border Strong. The product must look correct without blur.

## Status & Evidence Model

Verification is independent of feasibility. The interface models **four separate dimensions** and never collapses them into one status string.

| Dimension | Values |
|---|---|
| Execution | queued, running, completed, failed, cancelled |
| Evidence | valid, missing, invalid, stale |
| Feasibility | feasible, infeasible, inconclusive (with exact breach reason codes) |
| Verification | not_run, running, passed, failed, drift_exceeded |

**Verified Winner is derived, never stored.** A candidate is a Verified Winner if and only if all of these hold, computed by one pure, unit-tested function (`deriveVerifiedWinner`):

1. Feasibility is `feasible` and evidence is `valid` (not stale).
2. A verification run exists whose ID (`verify_...`) is non-empty and **different** from the search run ID.
3. Verification is `passed` and the measured drift is within the **declared** tolerance.

Any missing or unparseable field resolves to "not verified." Never default to pass. Tolerance values come from the contract or run configuration and are labeled "declared tolerance"; if none is declared, show amber "tolerance not declared" and do not pass.

### Badges

| State | Visual |
|---|---|
| **Verified Winner** (derived) | green wash, `#76B900` text and border, check icon, run ID in DM Mono |
| **Feasible, unverified** | neutral outline in Terminal Secondary, hollow check-circle, label "Awaiting verification" |
| **Infeasible** | crimson wash, `#FF5555` text and border, X icon, exact breach text (e.g. `P95 latency exceeds 50 ms ceiling by 14 ms`) |
| **Inconclusive / Stale** | amber wash, `#E9B949` text and border, clock icon, evidence age |
| **Evaluating** | neutral with a subtle opacity pulse, only while a run is genuinely executing |
| **Simulated / Demo** | `#8F9AA5` text, `#394053` border, label `DEMO DATA` |

Badges are 22px high, `0 8px` padding, pill radius. Color is never the only signal: every state pairs it with an icon and a text label.

## Motion

- **Data changes are instant (0ms).** Values, badges, and states change without animation. A number that animates between measurements is lying about when it was true.
- **Spatial changes are springs, ≤ 220ms perceived.** Navigation, drawer, popovers, and the segmented-control thumb use `spring-ui` (stiffness 380, damping 34). Press feedback is `scale(0.98)` on `spring-snappy`.
- **Stage motion is the only motion allowed to exceed 220ms.** One reveal per verified run.
- **Only animate `transform`, `opacity`, and `filter`.** Never layout properties.
- **Charts** may draw their line once on first mount (≤ 360ms); updates are instant.
- **`prefers-reduced-motion: reduce`:** replace every spring and the reveal with a 120ms opacity crossfade, with the final value shown immediately. No perpetual pulses, and nothing that implies live data when none is arriving.

### Hero Metric: Headroom on the Binding Constraint

The hero numeral is **headroom on the binding constraint**, the constraint with the smallest *relative* headroom.

- Upper-bound constraints (latency, error rate): `(ceiling − measured) / ceiling`.
- Lower-bound constraints (throughput floor): `(measured − floor) / floor`.

Display the absolute headroom with a unit, **name the metric** (for example `TTFT p95`), and show its ceiling or floor. Headroom is always a positive duration under the ceiling. A breach reads "N ms over ceiling" in crimson. There are no negative-headroom strings. A hero number never appears without its ceiling.

### The Verified-Winner Reveal (signature moment)

**Precondition (The Earned Reveal Rule).** The sequence plays only when `deriveVerifiedWinner` is true. Otherwise render the matching static Stage State with no reveal and no glow.

| t (ms) | Event |
|---|---|
| 0 | Ambient Field fades 0 → 1 over 600ms, ease-standard. The hero region is empty. |
| 120 | Eyebrow rises 8px and fades in: `VERIFIED RUN · verify_… · DEMO DATA`. The `DEMO DATA` chip is present from this frame and never animates out. |
| 240 | **Hero numeral resolves.** Each digit is a vertical wheel that rolls into place on `spring-stage`, staggered 60ms per digit left to right, with a 6px → 0 blur-in. Tabular figures keep widths fixed. The unit fades in last. |
| 760 | Caption fades in, naming the binding metric: `TTFT p95 headroom under the 50 ms SLO ceiling`. |
| 880 | SLO gauge draws left to right over 360ms: a neutral track to the ceiling, then the headroom segment in green. |
| 1180 | **Verification lands.** The Verified badge fades in and the winner glow switches on over 220ms. This is the first luminous green of the view. |
| 1240+ | Supporting metric cards stagger in (8px rise, 40ms apart, at most 6). |

**Rules for the reveal**
- The final value is in the DOM from the first frame. Animated wheels are `aria-hidden` over a real text node, and assistive technology announces the value once.
- Digits roll through glyph strips, never through a counted-up measurement that could be read as a real result.
- It plays once per verified run ID per session (`sessionStorage`). Returning to the view uses a 200ms crossfade. A ghost `Replay` button, and the `R` key, re-run it for presenters.
- Controls are usable from t = 240ms.

### Stage States (hero region)

| State | Hero shows | Motion | Green |
|---|---|---|---|
| **Verified winner** | Headroom numeral, caption, gauge, Verified badge | Signature reveal | Glow + gauge |
| **Evaluating** | Skeleton numeral with the ceiling visible | Evaluating pulse | None |
| **Feasible, unverified** | Candidate value, "Awaiting verification" neutral badge | None | None |
| **Infeasible** | Exact breach text | None | None |
| **Inconclusive / stale** | Last value with amber badge and evidence age | None | None |
| **Missing or invalid evidence** | "No evidence" empty state with the real next step | None | None |
| **Demo data** | Any of the above plus persistent `DEMO DATA` | As state | As state |

## Shapes

- **Radius Hierarchy:** `xs 3px` micro tags; `sm 4px` inputs and table actions; `md 6px` Inspector buttons and search; `lg 8px` metric cards and floating layers; `xl 10px` Inspector panels; **`stage 16px`** Stage cards; **`hero 22px`** the hero module; `pill 9999px` Stage buttons, badges, indicator dots, toggles.
- **Concentric Rule:** an inner radius equals the parent radius minus the padding between them (never below 3px).
- **Continuous corners:** where supported, apply `corner-shape: squircle` to the `stage` and `hero` radii as a progressive enhancement, falling back silently to circular corners.

## Components

### Buttons
- **Primary (Inspector):** 34px high, radius 6px, 11px 600. Background `#76B900`, text `#080A09`, hover `#95D500`.
- **Primary (Stage):** 44px high, pill, 15px 600, padding `0 24px`. One per Stage view.
- **Secondary:** Raised fill, `1px solid #263124`, text Primary. Hover border `#384635`, fill `#1F281E`.
- **Ghost:** transparent, text Secondary, hover text Primary.
- **Press:** `scale(0.98)` on `spring-snappy`.
- **Loading:** label switches to a progressive verb ("Evaluating…", "Running rerun…") with a rotating `.btn-spinner`.
- **Focus ring:** 2px `#95D500` with a 2px canvas-colored gap, visible on every surface including glass.
- **Every control works, or is visibly disabled with a one-line reason.**

### Sidebar (Glass Chrome)
Fill Glass Chrome with `backdrop-filter: blur(28px) saturate(150%)`, right edge `1px` Glass Hairline, top inner highlight. Items are 36px high, radius 8px, icon 18px, Inter 13px 500. Hover: `#1F281E`. Active: Raised fill, primary text, 6px green pill dot at the leading edge, and `aria-current="page"`. The collapsed spine keeps the glass.

### Context Bar
Solid canvas, 44px, `1px` bottom Border Wireframe. Real content only. It never carries window controls.

### Status Bar
Solid Carbon Surface, 28px, `1px` top Border Wireframe, DM Mono 11px.
- Persistent `DEMO DATA` chip (or `LIVE`, shown only when data truly comes from a working live integration).
- Scenario selector, shown only if the application supports scenarios.
- Hotkey hints.
- A health indicator **only** when it reflects a real API health round-trip, labeled with its source and age. Otherwise omit it or show "Offline" with no number. A fabricated latency is never displayed.

### Slide-Over Drawer (Run Detail, Candidate Deep-Dive)
Solid Elevated Slate, 420px wide on desktop, `1px solid #384635` leading edge. Enters on `spring-ui` with `translateX(16px) → 0` plus opacity; exits in 120ms. Below 1050px it becomes a right sheet with a Scrim; below 780px, full width. Focus moves into the drawer on open and returns to the trigger on close; `Esc` closes it.

### Scroll-Edge Toolbar (Glass Chrome)
The page header is transparent at rest. After 8px of scroll it fades to Glass Chrome with a bottom Glass Hairline.

### Floating Layers (Glass Float)
Tooltips, popovers, menus, the scrubber HUD, toasts, and modals. Radius `lg` (modal `stage`). Enter on `spring-ui` with `scale(0.96) → 1`; exit with ease-exit in 120ms. Text is Primary or Secondary only.

### Segmented Control and Switch
**Segmented control:** Raised track, radius `md`, 2px inner padding; Elevated Slate thumb with `1px solid #384635` sliding on `spring-ui`. Selected text Primary, unselected Secondary. **Never green.**
**Switch:** 42×26px pill. Off: Raised track with border. On: `#76B900` track, canvas-colored knob, travel on `spring-snappy`. Settings only; never for state that implies verification.

### Candidate Matrix Cards (hybrid)
Stage header region; each card radius `stage` on Carbon Surface, `1px solid #263124`, padding 24px 28px, with an Inspector table inside.
- **Hover:** border `#384635`, `translateY(-1px)` on `spring-ui`.
- **Selected:** Border Strong plus the inner highlight. **Selected never glows.**
- **Winner (verified only):** `1px solid #76B900`, the winner glow, the Verified badge.
- **Evaluating:** opacity pulse 0.65 → 1.0 on a 1.4s loop, only while a run is executing.

### Trade-Off Plot (replaces "Pareto frontier")
With a small fixed run budget (a baseline plus a handful of candidates), plot **measured points only**. Mark dominated and non-dominated points with distinct marker shapes. **Do not draw fitted or interpolated curves.** Axes carry explicit units and percentile labels; the SLO ceiling is a labeled dashed line. The winning candidate's marker is green; all other markers are Terminal Secondary. Use the word "frontier" only if enough runs exist to justify it.

### Head-to-Head Delta
Baseline and candidate side by side per metric, with unit, absolute delta, and ceiling. Improvements and regressions are shown with an arrow icon plus text, never color alone.

### Drift Gate Bar
Horizontal gauge of measured drift against the **declared** tolerance. Within tolerance is neutral with a pass icon; over tolerance is crimson with the exact exceedance; undeclared tolerance is amber "tolerance not declared" and fails closed.

### Telemetry Scrubber (LineChart)
- **Plot:** a solid Surface panel, 390×112 viewBox, responsive; 1.5px round-capped polyline; the SLO ceiling as a labeled dashed line (`50 ms SLO`).
- **Series:** neutral in Terminal Secondary; the winning candidate in `#76B900`.
- **Crosshair:** vertical line `#76B900` at 0.5 opacity following mouse, touch, or keyboard; snaps to samples.
- **HUD:** Glass Float pill clamped between 16% and 84% of plot width, following the crosshair on `spring-snappy`. Shows timestamp, value, and headroom (`18 ms headroom`, or `14 ms over ceiling` in Crimson). The HUD border turns green only while the crosshair is active.
- **Keyboard:** focusable; `ArrowLeft`, `ArrowRight`, `Home`, `End`, `Escape`. Every chart also has a text equivalent (table or summary).

### Metric Cards
- **Inspector:** radius 8px, 92px high, padding `13px 15px`, value 23px tabular bold in DM Mono, unit descriptor at 11px minimum, trend chip.
- **Stage:** radius `stage`, 24px padding, value in Inter Display tabular at 40px, unit at 0.4em.
- Every latency or throughput value shows its comparison to the declared hard SLO ceiling or floor where one exists.

### Conditional Actions
**"Copy vLLM CLI Flags"** is enabled only if the candidate configuration maps to real flags in the contracts or adapter. Otherwise it renders disabled with a one-line reason. Flags are never synthesized. **Export** and **Report** actions work only for artifacts that actually exist; the interface never claims a report was generated when it was not.

## Accessibility

- Contrast: at least 4.5:1 for all text, at least 7:1 for primary text. Obey the Text Surface Rule.
- Focus: visible 2px ring with offset on every interactive element, including those on glass.
- Reduced motion, reduced transparency, increased contrast, and forced-colors are all supported. Under `forced-colors: active`, use system colors and keep borders.
- Never rely on color alone: every state pairs its color with an icon and a text label.
- Semantic landmarks (`nav`, `main`, `aside`), a skip link, labeled icon buttons, `aria-current` on the active destination, and live-region announcements only for real events.
- The reveal and all charts have text equivalents; the scrubber is fully keyboard operable.
- Every screen has designed loading (skeleton), empty (with a real next step), error (exact message plus retry), partial-evidence, stale-evidence, and demo-data states.

## Implementation Tokens

```css
:root {
  /* colors */
  --canvas:#080A09; --surface:#0E120F; --raised:#151B15; --elevated:#1D251E; --hover:#1F281E;
  --border:#263124; --border-strong:#384635; --focus:#95D500;
  --text:#F0F3EF; --text-2:#A0AAA0; --text-3:#7A857B; --text-muted:#727D73;
  --primary:#76B900; --primary-bright:#95D500; --warn:#E9B949; --err:#FF5555;
  --info:#8F9AA5; --info-border:#394053;
  --primary-wash:rgba(118,185,0,.12); --err-wash:rgba(255,85,85,.12);
  --warn-wash:rgba(233,185,73,.12); --info-wash:rgba(143,154,165,.12);

  /* glass */
  --glass-chrome:rgba(14,18,15,.72); --glass-float:rgba(29,37,30,.78);
  --glass-hairline:rgba(240,243,239,.08); --glass-highlight:rgba(240,243,239,.05);
  --scrim:rgba(8,10,9,.62);
  --blur-chrome:blur(28px) saturate(150%); --blur-float:blur(20px) saturate(140%);

  /* shell */
  --context-bar-h:44px; --status-bar-h:28px; --sidebar-w:244px; --drawer-w:420px;

  /* shape + space */
  --r-md:6px; --r-lg:8px; --r-xl:10px; --r-stage:16px; --r-hero:22px;
  --gap-stage:48px; --section-stage:96px;

  /* motion */
  --ease:cubic-bezier(.32,.72,0,1); --ease-exit:cubic-bezier(.4,0,1,1);
  --t-fast:120ms; --t-base:200ms; --t-slow:360ms;

  /* type */
  --font-ui:Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  --font-display:'Inter Display',Inter,-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
  --font-mono:'DM Mono','SF Mono',Menlo,Consolas,monospace;
}

.glass-chrome{background:var(--glass-chrome);-webkit-backdrop-filter:var(--blur-chrome);backdrop-filter:var(--blur-chrome);
  box-shadow:inset 0 1px 0 var(--glass-highlight)}
.glass-float{background:var(--glass-float);-webkit-backdrop-filter:var(--blur-float);backdrop-filter:var(--blur-float);
  border:1px solid var(--glass-hairline);
  box-shadow:inset 0 1px 0 var(--glass-highlight),0 12px 32px rgba(0,0,0,.45),0 2px 6px rgba(0,0,0,.35)}
.drawer{background:var(--elevated);border-left:1px solid var(--border-strong)}  /* solid, not glass */

@supports not ((backdrop-filter:blur(1px)) or (-webkit-backdrop-filter:blur(1px))){
  .glass-chrome{background:var(--surface)} .glass-float{background:var(--elevated);border-color:var(--border-strong)}}
@media (prefers-reduced-transparency:reduce),(prefers-contrast:more),(forced-colors:active){
  .glass-chrome{background:var(--surface);-webkit-backdrop-filter:none;backdrop-filter:none}
  .glass-float{background:var(--elevated);border-color:var(--border-strong);-webkit-backdrop-filter:none;backdrop-filter:none}}
@media (prefers-reduced-motion:reduce){*{animation-duration:.01ms!important;transition-duration:var(--t-fast)!important}}

:focus-visible{outline:2px solid var(--focus);outline-offset:2px}
.num{font-variant-numeric:tabular-nums;font-feature-settings:"tnum" 1}
.hero-num{font-family:var(--font-display);font-variation-settings:"opsz" 32;font-weight:700;
  font-size:clamp(56px,11vw,144px);line-height:.95;letter-spacing:-.05em}
```

```ts
// Framer Motion presets
export const spring = {
  snappy: { type: "spring", stiffness: 520, damping: 42, mass: 1 },
  ui:     { type: "spring", stiffness: 380, damping: 34, mass: 1 },
  stage:  { type: "spring", stiffness: 140, damping: 20, mass: 1 },
} as const;
```

## Build Priority

**P0 (the demo path):**
1. Tokens, Ambient Field, two-tier type scale, fallbacks, `DEMO DATA` chip, badges.
2. Status model with the unit-tested `deriveVerifiedWinner`.
3. Shell: context bar, glass sidebar, status bar, drawer, responsive contract.
4. Overview Stage hero with the Verified-Winner Reveal, SLO gauge, and every Stage State.
5. Tuning Lab with the Selected-versus-Winner distinction and the trade-off plot.

**P1:** Verification console with drift gate and JSONL export; Experiments ledger with drawer; Workloads; Reports; scrubber HUD as a glass pill.

**P2:** segmented control, scroll-edge toolbar, switch, concentric-radius polish, `corner-shape: squircle`, replay shortcut.

Never trade a working verification flow for visual polish. If time runs short, drop from the bottom up.

## Do's and Don'ts

### Do
- **Do** keep the two tiers visibly separate; Stage is airy, Inspector is dense.
- **Do** put glass only on the sidebar, the scroll-edge toolbar, and floating layers.
- **Do** derive Verified Winner from the four-dimension model; require a fresh `verify_...` ID that differs from the search run ID.
- **Do** show every latency, throughput, token, and memory figure as a tabular numeral with an explicit unit, next to its declared ceiling or floor.
- **Do** persistently label fixtures and simulated streams with `DEMO DATA`.
- **Do** read drift tolerance from the contract or run configuration and label it "declared."
- **Do** keep the final value in the DOM from the first frame of any animation.
- **Do** provide solid fallbacks for blur, reduced transparency, increased contrast, forced-colors, and reduced motion.
- **Do** provide keyboard scrubbing (Arrow keys, Home, End, Escape) on every time-series chart.
- **Do** make every control work, or visibly disable it with a reason.

### Don't
- **Don't** add window controls (traffic lights), invented health or latency numbers, or synthesized CLI flags.
- **Don't** put glass behind tables, charts, drawer content, or any number a person must read precisely, and never go below 72% glass opacity.
- **Don't** animate data values between measurements.
- **Don't** play the reveal for unverified, stale, infeasible, or evidence-missing results, and never style an unverified candidate as verified.
- **Don't** treat feasibility as verification.
- **Don't** color active nav, selected cards, tabs, or segments green; don't show more than one luminous green focal element per view.
- **Don't** use cyan (`#8F9AA5`) for anything but simulated or demo.
- **Don't** draw fitted or interpolated curves, and don't call a handful of measured points a "frontier."
- **Don't** hard-code a drift tolerance in the interface.
- **Don't** use pastel or blue/purple SaaS gradients; buttons stay solid.
- **Don't** hide or truncate constraint failures; show the exact breach reason.
- **Don't** let any layout create a horizontal scrollbar down to 360px.
- **Don't** place Muted Oxide on Surface or above, or Tertiary on Elevated or glass.
- **Don't** use any retired color value (see Colors).

## Changelog

| Area | v1 | v2.0 | v2.1 (this version) |
|---|---|---|---|
| Identity | Cyberpunk Systems Command Center | The Verified Instrument | Unchanged |
| Density | One dense scale | Two tiers | Adds hybrid screens, a screen tier map, and a 360px responsive contract |
| Material | Solid slabs only | Glass on sidebar and floating layers | The drawer is explicitly solid; border definitions never mix |
| Motion | Instant everywhere | Instant data, spring space, one reveal | Reveal requires the derived verified winner; charts draw once on mount |
| Type | Inter + DM Mono | Adds Inter Display | DM Mono is first in the mono stack so numbers match everywhere |
| Green | Active tabs, selected cards, HUD border | Green reserved for proof and focus | Adds The Not-Green-by-Default Rule and the One Green Moment Rule |
| Status | One badge set | Selected vs Winner split | Four-dimension model; Verified Winner derived; feasible-unverified is a neutral outline |
| Hero | Not defined | Headroom numeral | Headroom on the binding constraint, always naming its metric and ceiling |
| Shell | Sidebar only | Sidebar, scroll-edge toolbar | Adds context bar, status bar, drawer, hotkeys; explicitly no window controls |
| Charts | Scrubber only | Scrubber with glass HUD | Adds trade-off plot (measured points only), head-to-head delta, drift gate |
| Honesty | `DEMO DATA` labeling | Same | Adds no invented numbers, conditional CLI flags, declared-tolerance fail-closed |
| Colors | One palette | Adds text-tertiary, glass tokens | Retired list: `#151916`, `#1D241F`, `#252E27`, `#6E7C70`, `#EF4444`, `#F59E0B`, `#38BDF8`, `#263328` |
