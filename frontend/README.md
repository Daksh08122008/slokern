# SLOKern Frontend

A frontend-only demonstration of the SLOKern inference optimization workstation, built around the approved **NVIDIA Green × Arasaka-inspired Corporate Futurism** design system.

## Requirements

- Node.js 20 or newer
- npm

## Run locally

```bash
npm install
npm run dev
```

Vite prints a local URL when the development server starts.

## Production build

```bash
npm run build
npm run preview
```

## Included workflows

- Command Center with decision, candidate ranking, hard constraints, and an audit event feed
- Experiments registry with search, status filtering, and run detail views
- Workload & SLO Builder with inline blocking validation and review-before-launch
- Tuning Lab with a 2×2 candidate matrix and candidate inspector
- Live Monitor with deterministic telemetry and pause/resume presentation controls
- Verification comparison with pending, failed, and stale evidence scenarios
- Evidence & Reports with an engineering dossier view and Markdown export
- Runtime Profile with explicitly illustrative, non-detected hardware/runtime information
- Settings with local preferences and deterministic scenario selection

## Demo behavior and boundaries

- All benchmark values, hardware inventory, event history, and verification outcomes are fixture data. The UI visibly labels the demo boundary.
- There is no backend, live telemetry stream, actual GPU detection, inference execution, or signed/tamper-proof report provenance.
- Ranking and feasibility are computed from the local deterministic fixture set and the builder's current hard thresholds; infeasible candidates are never declared winners.
- The scenario selector covers the normal feasible/pending case, verification drift failure, no-feasible-candidate behavior, and stale evidence.
- UI preferences and the selected scenario are stored in `localStorage` where available.
- Charts and icons use inline SVG and CSS to keep the dependency set small. The visual layout is responsive and honors reduced-motion preferences.

## Project structure

```text
src/
  App.tsx       Application shell, workflow screens, fixture evaluation, interactions
  main.tsx      React entry point
  styles.css    Design tokens, workspaces, responsive layouts, and motion rules
index.html      Vite HTML entry
vite.config.ts Vite + React configuration
```
