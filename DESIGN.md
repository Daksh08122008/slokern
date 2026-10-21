---
name: SLOKern
description: Obsidian Black × NVIDIA Green Precision AI Workstation
colors:
  canvas: "#080A09"
  surface: "#0E120F"
  raised: "#151B15"
  elevated: "#1D251E"
  hover: "#1F281E"
  border: "#263124"
  border-strong: "#384635"
  border-focus: "#76B900"
  text-primary: "#F0F3EF"
  text-secondary: "#A0AAA0"
  text-muted: "#727D73"
  primary: "#76B900"
  primary-bright: "#95D500"
  warning: "#E9B949"
  error: "#FF5555"
  info: "#394053"
typography:
  display:
    fontFamily: "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"
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
    fontFamily: "'DM Mono', 'SFMono-Regular', Consolas, monospace"
    fontSize: "10.5px"
    fontWeight: 500
    lineHeight: 1.3
    letterSpacing: "0.06em"
rounded:
  xs: "3px"
  sm: "4px"
  md: "6px"
  lg: "8px"
  xl: "10px"
  pill: "9999px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "12px"
  lg: "16px"
  xl: "24px"
  xxl: "32px"
components:
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.canvas}"
    rounded: "{rounded.md}"
    padding: "0 15px"
    height: "34px"
  button-primary-hover:
    backgroundColor: "{colors.primary-bright}"
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
  metric-card:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.text-primary}"
    rounded: "{rounded.lg}"
    padding: "13px 15px"
---

# Design System: SLOKern

## Overview

**Creative North Star: "The Cyberpunk Systems Command Center"**

SLOKern’s visual world is built for systems engineers operating under zero-latency tolerance and high operational risk. It rejects both the frivolous toy aesthetics of gamer RGB kits and the washed-out, lifeless pastel gradients of generic SaaS dashboards. Instead, it embodies a high-density, high-rigor technical command deck: deep obsidian carbon foundations, microsecond-accurate data telemetry, disciplined structural borders, and purposeful phosphor luminescence.

The interface prioritizes scanability, information hierarchy, and verifiable truth over decorative distraction. Surfaces feel physical and monolithic, layered with dark tonal steps rather than noisy drop shadows. Every component respects the operator's attention: state changes are instantaneous, metrics are aligned with monospace precision, and neon green light is strictly treated as an affirmative signal of verified proof.

**Key Characteristics:**
- **Obsidian Tonal Architecture:** Deep near-black background steps (`#080A09` to `#1D251E`) establish optical depth and reduce visual fatigue during marathon tuning runs.
- **Phosphor Precision:** Electric NVIDIA green (`#76B900` / `#95D500`) serves as an instrument-grade laser: sharp, readable, and reserved for proven affirmative outcomes and focused controls.
- **Instrument-Grade Telemetry:** All timestamps, latencies, percentiles, and rates render in tabular monospace with explicit units and headroom deltas.
- **Tactile Instrument Affordances:** Sub-220ms transitions, snappy spring transforms on cards, crisp 2px focus indicators, and continuous touch/keyboard chart scrubbing.
- **Explicit Provenance Disclosure:** Demo fixtures and simulated data streams carry persistent, unambiguous badges (`DEMO DATA`, `FIXTURE`) so simulated results are never mistaken for live GPU execution.

## Colors

The palette is rooted in deep obsidian carbon, contrasted with electric phosphor green accents and clinical diagnostic status indicators.

### Primary
- **NVIDIA Signal Green** (`#76B900`): The primary operational accent. Used for primary buttons, passing constraint badges, active tabs, winning candidate emblems, and scrubber crosshairs.
- **Phosphor Bright Green** (`#95D500`): High-intensity luminous green. Reserved for `:focus-visible` outlines, primary button hover states, and critical chart highlight dots.

### Neutral
- **Obsidian Canvas** (`#080A09`): The ultimate background foundation. Near-black with subtle cool-green undertones.
- **Carbon Surface** (`#0E120F`): Panel and card surface color. Sits one layer above canvas.
- **Raised Charcoal** (`#151B15`): Secondary interactive background (secondary buttons, input fills, table headers).
- **Elevated Slate** (`#1D251E`): Tooltips, HUD inspector callouts, and floating overlays.
- **Border Wireframe** (`#263124`): Structural bounding line separating panels, tables, and rows.
- **Border Strong** (`#384635`): Elevated borders, active cards, and focused fields.
- **Glacier Text** (`#F0F3EF`): Primary high-contrast typography (17.5:1 contrast against canvas).
- **Terminal Secondary** (`#A0AAA0`): Labels, subtitles, table secondary fields (8.0:1 contrast).
- **Muted Oxide** (`#727D73`): Tertiary notes, timestamps, inactive units (4.54:1 contrast).

### Semantic
- **Telemetry Crimson** (`#FF5555`): Hard constraint failures, verification drift breaches, and execution errors.
- **Warning Amber** (`#E9B949`): Inconclusive metrics, stale evidence, and budget exhaustion warnings.
- **Status Cyan** (`#8F9AA5`): Telemetry stream markers, simulated demo tags, and auxiliary data signals.

### Named Rules
**The Rarity of Luminescence Rule.** Electric NVIDIA Green is strictly rationed to $\le 8\%$ of any viewport. Its cognitive power stems entirely from isolation against the dark obsidian substrate. When everything glows, nothing is critical.

## Typography

**Display / Interface Font:** `Inter` (with `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto` fallbacks).  
**Telemetry / Mono Font:** `DM Mono` (with `'SFMono-Regular', Consolas, monospace` fallbacks).

**Character:** Technical, clinical, and unapologetically engineered. Inter delivers crisp legibility at small sizes (10–13px) for dense control panels, while DM Mono guarantees rock-solid vertical alignment for multi-row numerical telemetry.

### Hierarchy
- **Display** (Bold 700, `clamp(21px, 2.2vw, 30px)`, line-height 1.15, tracking `-0.035em`): Page titles and primary dashboard heroes.
- **Headline** (SemiBold 650, `18–20px`, line-height 1.25, tracking `-0.025em`): Section headings and modal titles.
- **Title** (SemiBold 600, `14–15px`, line-height 1.35, tracking `-0.015em`): Panel titles and candidate names.
- **Body** (Regular 400, `12–13px`, line-height 1.5): Descriptive copy, rationale explanations, and audit documentation.
- **Label / Telemetry** (Medium 500, `9–11px`, line-height 1.3, tracking `0.06em`, uppercase or tabular): Status badges, table headers, timestamps, units, and configuration chips.

### Named Rules
**The Absolute Tabular Rigor Rule.** Every metric value, percentile, latency delta, rate, and timestamp must declare `font-variant-numeric: tabular-nums; font-feature-settings: "tnum" 1;` with an explicit unit (`ms`, `k tok/s`, `GB`, `req/min`). Naked numbers or unanchored floating-point decimals are strictly prohibited.

## Layout

SLOKern employs a persistent **workstation shell** designed for dual-orientation engineering productivity:

- **Sidebar Anchor:** Fixed 244px navigation rail at desktop widths ($>1280\text{px}$), tapering to 218px at $1280\text{px}$, collapsing to an icon-only 66px spine at $\le 1050\text{px}$, and adopting a slim 50px mobile anchor at $\le 520\text{px}$.
- **Main Shell Grid:** Fluid width calculated as `calc(100% - var(--sidebar-width))` with padding stepping from 24px (desktop) $\to$ 16px (tablet) $\to$ 10px (mobile).
- **Panel Rhythm:** Multi-column asymmetric grids (`minmax(0, 1.3fr) minmax(280px, 0.7fr)`) for candidate evaluation, collapsing to two equal columns at $1050\text{px}$ and single-column vertical flow at $\le 780\text{px}$.
- **Zero Horizontal Overflow:** All horizontal containers (tables, toolbars, metadata rails) utilize fluid wrapping or dedicated internal horizontal scrollports (`.table-scroll`), guaranteeing zero page-level horizontal overflow down to 360px viewport widths.

## Elevation & Depth

Depth is established primarily through **tonal stepping** and razor-sharp border contrast, reinforced by subtle structural drop shadows.

Surfaces do not float aimlessly in space. They are physically grounded slabs:
- **Level 0 (Canvas):** `#080A09` (Base background)
- **Level 1 (Panels & Shell):** `#0E120F` with border `1px solid #263124` and `--shadow-panel` (`0 10px 30px rgba(0, 0, 0, 0.42)`)
- **Level 2 (Cards & Secondary Controls):** `#151B15` with border `1px solid #263124`
- **Level 3 (HUD Scrubber & Tooltips):** `#1D251E` with border `1px solid #76B900` and `--shadow-elevated`
- **Ambient Illumination:** Optional radial gradient spotlight (`rgba(118, 185, 0, 0.045)`) positioned behind the primary optimization hero.

### Named Rules
**The State-Driven Luminescence Rule.** Glow effects (`box-shadow: 0 0 20px rgba(118, 185, 0, 0.14)`) are forbidden on static elements. They activate only in response to proven state: the verified winning candidate, an active focused control, or an active telemetry crosshair.

## Shapes

- **Radius Hierarchy:**
  - `xs (3px)`: Micro-tooltips and small inline tags.
  - `sm (4px)`: Form inputs, selects, and table action buttons.
  - `md (6px)`: Buttons, search fields, and metric cards.
  - `lg (8px)`: Intermediate containers and status chips.
  - `xl (10px)`: Primary workstation panels and hero modules.
  - `pill (9999px)`: Status indicator dots and circular icons.
- **Border Geometry:** 1px solid crisp hairline borders throughout. Double borders or heavy 2px decorative borders are avoided; 2px is reserved strictly for `:focus-visible` accessibility rings.

## Components

### Buttons
- **Shape:** Rounded 6px (`--radius-md`), height 34px, font-size 11px, font-weight 600.
- **Primary:** Background `#76B900`, text `#080A09`, padding `0 15px`. Hover `#95D500`, active transform `translateY(1px)`.
- **Secondary:** Background `#151B15`, border `1px solid #263124`, text `#F0F3EF`. Hover border `#384635`, background `#1F281E`.
- **Ghost:** Transparent background, text `#A0AAA0`, padding `0 10px`. Hover text `#F0F3EF`.
- **Loading State:** Text switches to progressive label ("Evaluating...", "Running rerun..."), icon replaced with rotating `.btn-spinner`.

### Candidate Matrix Cards
- **Geometry:** Rounded 10px, background `#0E120F`, border `1px solid #263124`.
- **Selected State:** Border `#76B900`, box-shadow `0 0 20px rgba(118, 185, 0, 0.14)`.
- **Winner Badge:** Dedicated `#76B900` status badge with check icon.
- **Evaluating Pulse:** Subtle opacity pulse (`0.65` to `1.0`) during re-evaluation runs.

### Telemetry Scrubber (LineChart)
- **Geometry:** 390×112 SVG viewport, responsive vector polyline, horizontal threshold line (50 ms SLO ceiling).
- **Crosshair:** Dynamic vertical tracking line (`#76B900`, opacity 0.5) following mouse, touch, or keyboard scrubbing.
- **HUD Popup:** Floating pill positioned between 16% and 84% width showing exact timestamp (`14:40:24`), metric value (`32 ms`), and headroom delta (`-18 ms headroom`).
- **Keyboard Access:** Tab-focusable (`tabIndex={0}`), navigable via `ArrowLeft`, `ArrowRight`, `Home`, `End`, and dismissible via `Escape`.

### Metric Cards
- **Geometry:** Height 92px, background `#0E120F`, border `1px solid #263124`, padding 13px 15px.
- **Values:** Font size 23px tabular bold, accompanied by 10px unit descriptor (`ms`, `k tok/s`).
- **Trend Delta:** Color-coded chip indicating headroom vs. baseline or SLO breach.

### Status Badges
- **Geometry:** Height 22px, padding `0 8px`, border-radius 9999px.
- **Feasible / Pass:** Green wash (`rgba(118, 185, 0, 0.12)`), text `#76B900`, border `#76B900`.
- **Infeasible / Fail:** Red wash (`rgba(255, 85, 85, 0.12)`), text `#FF5555`, border `#FF5555`.
- **Stale / Warning:** Amber wash (`rgba(233, 185, 73, 0.12)`), text `#E9B949`, border `#E9B949`.
- **Simulated / Demo:** Cyan wash, text `#8F9AA5`, border `#394053`.

## Do's and Don'ts

### Do:
- **Do** format every latency, throughput, token volume, and memory figure with tabular monospace numbers (`font-feature-settings: "tnum" 1`) and explicit physical units.
- **Do** require a fresh verification run ID (`verify_...`) before displaying the verified badge on any feasible candidate.
- **Do** persistently label synthetic fixtures, simulated streams, and non-monetary system proxies with `DEMO DATA`.
- **Do** maintain a minimum 4.5:1 contrast ratio for all secondary labels and >7:1 for primary interface text.
- **Do** provide keyboard scrubbing (Arrow keys, Home, End, Escape) for all time-series charts.

### Don't:
- **Don't** use pastel purple or blue SaaS gradient buttons; keep buttons solid, high-contrast, and instrument-grade.
- **Don't** allow electric green glow effects to bleed across static layout containers; reserve luminescence strictly for verified winners and active focus.
- **Don't** display a floating-point latency or throughput metric without displaying its comparison to the declared hard SLO ceiling.
- **Don't** hide or truncate constraint failures; display the exact breach reason code (`P95 latency exceeds 50 ms ceiling by 14 ms`).
- **Don't** introduce layout elements that induce horizontal window scrollbars at viewports down to 360px.

