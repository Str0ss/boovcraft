# Implementation Plan: Interactive Timelines (React Migration + Brush-to-Zoom + Event Filter)

**Branch**: `005-react-timelines` | **Date**: 2026-05-04 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/005-react-timelines/spec.md`

## Summary

Replace the static-HTML + vanilla-JS visualizer of features 003 and 004
with a React + TypeScript SPA built by Vite, served in production from
an nginx-on-alpine container brought up by `docker compose up`, and
hot-reloaded in development by `npm run dev`. Use **Apache ECharts**
(via `echarts-for-react`) as the chart library — its built-in
`dataZoom` (with `brush` / `inside` types) and `connect()` API for
synchronized cross-chart zoom map directly to spec FR-002 (global
zoom across all players) and FR-009–FR-014 (per-category legend
toggles), eliminating most of the custom interaction logic that
feature 004 wrote by hand. The visualizer's input contract is
preserved unchanged (Principle I / Principle V (a) / FR-025): the
React app reads `*.analysis.json` exactly as feature 004 produced it,
with no upstream changes required. Feature 004's hand-rolled SVG
histogram code is removed; feature 003's vanilla-HTML page is
replaced. The four-tab structure (Summary / Timelines / Analysis /
Map), all Summary aggregations, all empty-state and unknown-entity
treatments, and every previously-passing functional requirement carry
forward (FR-023, FR-024).

This feature is the first invocation of the constitution v1.1.0
Principle V interactive-analytical exception (PR #5, merged
2026-05-03). All three V preserve clauses are gated by the
Constitution Check below.

## Technical Context

**Language/Version**: TypeScript 5.5+ (strict mode), targeting
ECMAScript 2022. The Visualizer side switches from vanilla JS to TS;
the Parser (Node + w3gjs) and Processor (Python) are unchanged.

**Primary Dependencies**:
- **React 18.x** (stable — the latest minor at the time of feature
  start; do not pin to 19 unless the toolchain catches up).
- **`echarts` 5.x** + **`echarts-for-react` 3.x** — chart rendering.
- **Vite 5.x** — dev server + production build.
- **Vitest 1.x** — unit tests for pure logic (brush math, bucket
  sizing, filter / history state reducers, aggregation helpers).
- **`@types/react`**, **`@types/react-dom`** — TypeScript types for
  React.

No state-management library (no Redux, no Zustand, no Jotai). Plain
React `useState` + a small Context provider for the cross-component
state surface (`activeTab`, `zoomState`, `zoomHistory`,
`filterState`). The state surface is small enough that adding a
library would violate Principle III (no internal abstractions ahead
of need) without delivering value VI's escape hatch covers.

No router (no React Router). The four tabs are conditional rendering
on a single state field. URL hash routing is out of scope per the
spec's "no cross-session persistence" assumption.

No CSS framework (no Tailwind, no Mantine, no MUI). Plain CSS modules
co-located with components, scoped by Vite. The aesthetic carries
forward from feature 004's `styles.css` palette; this is a port, not
a redesign.

**Storage**: Browser memory only (carrying feature 003's posture). The
loaded analysis JSON lives in a single in-memory object for the page
session; re-loading replaces it. No `localStorage`, no `IndexedDB`,
no cookies.

**Testing**:
- **Unit tests (new)**: Vitest covers pure functions — bucket-width
  selection from zoom + viewport, brush-rectangle → time-range
  conversion, filter-state reducer, zoom-history reducer, aggregation
  helpers (production / heroes / transfers). These are pure
  data-in / data-out functions with no DOM. Fixture inputs are
  derived from the committed `*.analysis.json` files at runtime — no
  mocks (Principle IV's spirit applied to the new test layer:
  derive from real fixture data, never hand-roll fake events).
- **Component tests (deferred)**: React Testing Library is NOT
  introduced in v1. Visual correctness remains a manual walkthrough
  (`quickstart.md` § Walkthrough), consistent with feature 003's
  "no automated frontend tests in v1" posture for the visual layer.
  If a regression in the visual layer is found post-merge, an RTL
  layer can be added in a follow-up.
- **Processor pytest**: unchanged. The Processor is not touched in
  this feature.

**Target Platform**: Modern desktop evergreen browsers (last two
versions of Chrome, Firefox, Safari, Edge) on Linux / macOS / Windows.
**Production**: served from a containerized nginx-on-alpine image
brought up by `docker compose up`. **Development**: served by
`npm run dev` (Vite dev server). Both are first-class per Principle
V (b); neither is privileged.

**Project Type**: Single-page application (SPA), built by Vite,
deployed as a static `dist/` folder served by an nginx container in
production or by Vite's dev server in development. The Parser and
Processor remain separate process layers — no cross-layer code
sharing.

**Performance Goals**:
- Brush release → all-row re-render: ≤ 100 ms perceived latency on
  commodity laptop hardware on the largest fixture (base_1, 8
  players, ~88 min, ~30k events) — SC-002.
- Filter toggle → all-row re-render: ≤ 100 ms — SC-003.
- Cold container start (`docker compose up`) to first-meaningful-
  paint: ≤ 30 seconds — SC-005.
- Dev server start (`npm run dev`) to hot-reloading-ready: ≤ 10
  seconds — SC-005.
- Tab switch perceived latency: ≤ 50 ms (carrying feature 004's
  SC-004 budget).
- Initial page load → ready-for-file-pick: ≤ 2 seconds on commodity
  laptop hardware (uncached, served from local container).

**Constraints**:
- **No runtime network egress from the browser** (Principle V (c) /
  FR-026 / SC-006). No CDN scripts, no Google Fonts, no analytics,
  no telemetry, no remote JSON. Verified during build by ensuring
  ECharts is bundled (not CDN-linked), system fonts are used (no
  webfont fetch), and DevTools Network tab shows zero outbound
  requests after page load.
- **JSON-only inter-layer contract** (Principle V (a) / FR-025). The
  new visualizer reads `*.analysis.json` from a user-picked file via
  the File API — exactly as feature 004 does. No Parser or Processor
  source change is part of this feature.
- **Single-command deploy in both modes** (Principle V (b) /
  FR-027). `docker compose up` for production, `npm run dev` for
  development. Documented in `quickstart.md`.
- **No bespoke chart code** (Principle VI). Brush selection, zoom
  sync, legend toggle, tooltip rendering, axis labels — all
  delegated to ECharts. Custom code is glue (state shape, prop
  threading) plus the small handful of helpers the spec calls out
  (zoom-history reducer, filter-state reducer, aggregation logic
  for the Summary tab — all Vitest-tested).
- **All committed Vitest tests MUST pass** before declaring the
  feature shipped. The Processor's pytest run remains green
  unchanged.

**Scale/Scope**:
- 4 tab views, 1 of which (Timelines) renders 1–8 ECharts instances
  simultaneously, all linked via `echarts.connect()`.
- ~30k events per long match (base_1 fixture); ECharts handles this
  comfortably with default canvas rendering.
- Code-size envelope: ~3,000–5,000 lines of TypeScript across ~20
  components/modules. Smaller per-file than feature 004's
  visualizer.js (1,121 lines) thanks to React decomposition.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version: 1.1.0 (`.specify/memory/constitution.md`),
ratified 2026-04-21, last amended 2026-05-03. This feature is the
first invocation of the V interactive-analytical exception added in
v1.1.0 and the first feature whose dependencies are gated by VI.

| Gate | Principle | Status | Evidence |
|---|---|---|---|
| Layer separation | I. Strict Layer Separation | **PASS** | The Visualizer's only input remains `*.analysis.json`. No Parser or Processor source is imported, edited, or invoked. The migration is contained entirely within the `visualizer/` directory. |
| Canonical parser | II. w3gjs Is The Canonical Parser | **PASS (N/A)** | The Parser layer is untouched in this feature. |
| No premature abstractions | III. No Premature Abstractions | **PASS** | Single state surface (one Context provider over `useState` hooks). No internal plugin system, no template engine, no generic component framework, no shared widget library. Components are written for the concrete tab content in front of them; helpers are introduced at the second use, not the first imagined one. The chart-rendering "abstraction" is the chart library itself (Principle VI), not internal scaffolding. |
| Fixture-based testing | IV. Fixture-Based Testing With Real Replays | **PASS** | New Vitest unit tests derive their inputs from the committed `*.analysis.json` fixtures (loaded at test time), not hand-rolled mocks. Visual correctness remains manual against the same fixtures. The Processor's pytest layer (which Principle IV most directly governs) is unchanged. |
| Frontend evolution | V. Incremental Frontend Evolution | **PASS** (interactive-analytical exception invoked) | The spec records the concrete trigger — multi-chart brush-to-zoom (US1 / FR-001–008), cross-chart filter coordination (US2 / FR-009–017), animation of derived state (zoom-history transitions, US3 / FR-018–022). All three preserve clauses are honored: **(a) JSON contract**: the React app reads `*.analysis.json` unchanged (FR-025); **(b) Single-command deploy in both modes**: `docker compose up` (production) and `npm run dev` (development) are both first-class (FR-027 / SC-005); **(c) No runtime egress**: Vite production build bundles all assets; system fonts only; no CDN; verified by network-tab inspection (FR-026 / SC-006). |
| Library justification | VI. Prefer Well-Established Tools | **PASS** | Each new dependency is verified against all four criteria in `research.md` § R1–R5 (active maintenance ≤ 12 mo, broad adoption, permissive license, API stability). React, ECharts, Vite, TypeScript, Vitest — all pass. No bespoke chart engine, no hand-rolled brush handler, no custom state-management library. |

**Violations**: none. Complexity Tracking table is empty.

## Project Structure

### Documentation (this feature)

```text
specs/005-react-timelines/
├── plan.md              # this file
├── research.md          # Phase 0 — library + tooling decisions, VI verifications
├── data-model.md        # Phase 1 — page state shape, history reducer, filter shape
├── quickstart.md        # Phase 1 — bring-up + walkthrough for both deploy modes
├── contracts/           # Phase 1 — input contract pointer + UI contract addendum
│   ├── input-contract.md     # unchanged from feature 004; pointer + non-regression
│   └── ui-contract.md        # brush, filter, history, deploy interactions
├── checklists/
│   └── requirements.md       # populated by /speckit-specify (already passing)
└── tasks.md             # Phase 2 — created by /speckit-tasks
```

### Source Code (repository root)

```text
visualizer/                    # REPLACED — all feature 003 + 004 vanilla files removed
├── package.json               # React + ECharts + Vite + Vitest
├── package-lock.json          # locked at first install
├── tsconfig.json              # strict mode
├── vite.config.ts             # plus dev server config; static asset bundling
├── index.html                 # Vite entry (single `<div id="root">` mount)
├── public/                    # any static assets that should not be hashed
├── src/
│   ├── main.tsx               # React root
│   ├── App.tsx                # tab routing shell
│   ├── state/
│   │   ├── PageStateContext.tsx     # the one Context: pageState + dispatchers
│   │   ├── zoomHistory.ts           # pure reducer; Vitest-covered
│   │   └── filterState.ts           # pure reducer; Vitest-covered
│   ├── data/
│   │   ├── validate.ts        # JSON-shape validator (port of feature 003 logic)
│   │   ├── aggregations.ts    # production / hero / transfer aggregations
│   │   ├── timelineEvents.ts  # collectPlayerEvents + bucket helpers
│   │   └── format.ts          # formatTimeMs, etc. (port of feature 003 helpers)
│   ├── tabs/
│   │   ├── SummaryTab.tsx
│   │   ├── TimelinesTab.tsx       # owns the ECharts instances + connect() group
│   │   ├── AnalysisStub.tsx
│   │   └── MapStub.tsx
│   ├── components/
│   │   ├── TabStrip.tsx
│   │   ├── FilePicker.tsx
│   │   ├── DropZone.tsx
│   │   ├── PlayerHistogram.tsx     # one ECharts wrapper per player; props-driven
│   │   ├── TimelineLegend.tsx      # clickable category chips (filter UI)
│   │   ├── ZoomControls.tsx        # slider + back/forward + reset
│   │   └── PlayerPanel.tsx         # Summary tab's per-player block
│   └── styles/
│       └── (CSS modules — co-located *.module.css per component)
├── tests/                     # Vitest unit tests for pure modules
│   ├── zoomHistory.test.ts
│   ├── filterState.test.ts
│   ├── aggregations.test.ts
│   └── timelineEvents.test.ts
├── Dockerfile                 # nginx-alpine; copies built dist/
├── docker-compose.yml         # one service: visualizer; port 8080:80 by default
├── nginx.conf                 # SPA fallback; no remote anything
└── DATA.md                    # bring-up + tab guide; supersedes feature 004's DATA.md

processor/                     # UNCHANGED — pytest still green; analysis JSON contract unchanged
parser/                        # UNCHANGED — w3gjs untouched (Principle II)

sample_replays/                # UNCHANGED — committed fixtures still acceptance bar
```

**Structure Decision**: Replace the contents of the existing
top-level `visualizer/` directory entirely. The old vanilla
`index.html` / `styles.css` / `visualizer.js` are removed in this
feature; the new Vite-managed React app takes the same directory.
Rationale:
- Single source of truth — no parallel "old vs new" code paths to
  reconcile during review.
- Once feature 005 ships, the old files are dead code by definition;
  the spec's non-regression bar (FR-023, FR-024) confirms the React
  app subsumes them. Carrying both indefinitely violates Principle
  III's anti-dead-code rule.
- Existing scripts and docs that reference `visualizer/index.html`
  by path continue to work — the file still exists at the same path,
  just produced by Vite (or the dev server).

If migration risk becomes a concern during implementation, the
feature can be split into two PRs (scaffold-only + content-port);
that decision lives in `tasks.md`.

## Complexity Tracking

> Filled ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(no violations)_ | _(n/a)_ |
