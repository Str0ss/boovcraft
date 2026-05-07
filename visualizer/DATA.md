# Visualizer (layer 3 of 3)

The third and final layer of the Parser → Processor → Visualizer
pipeline. A React + TypeScript single-page app that reads one
Processor-layer analysis JSON and renders a four-tab match report:
**Summary**, **Timelines**, **Analysis**, **Map**.

## Input contract

`processor/DATA.md` defines the shape of the JSON this app consumes.
The visualizer trusts that contract verbatim and never invokes the
Parser or the Processor at runtime.

## How to bring it up

Two first-class deploy modes (per constitution v1.1.0 Principle V (b)):

### Production — `docker compose up`

```sh
cd visualizer && docker compose up
```

Then open <http://localhost:8080>. The container is a multi-stage
build: `node:20-alpine` runs `npm ci && npm run build`,
`nginx:alpine` serves the resulting `dist/`. Cold image build to
serving page is ~30 seconds on commodity hardware (per SC-005).

To stop: `Ctrl-C`, then `docker compose down`.

### Development — `npm run dev`

```sh
cd visualizer
npm install         # one-time
npm run dev
```

Vite dev server with hot-module reload (default
<http://localhost:5173>). Ready in ~5 seconds (per SC-005).

### No-Docker fallback

```sh
cd visualizer
npm install && npm run build
npx serve dist/
```

Same `dist/` folder as the Docker image, served by `serve` over
plain HTTP.

## How to use it

1. Run the analyzer once per replay:
   `python processor/analyze.py sample_replays/base_1.w3g.json`
2. Open the visualizer URL.
3. Click the file picker (or drag the file onto the page) and
   choose the `*.analysis.json` produced in step 1.
4. The match report renders client-side. Pick a different file at
   any time to load another replay.

## The four tabs

- **Summary** (default): match header, per-team grouped player
  panels with action totals, group hotkeys, and aggregated
  production / heroes / resource transfers (counts and arrow
  chains — no per-event timestamps), chat, observers.
- **Timelines**: one full-width histogram per player, stacked
  top-to-bottom. Drag horizontally on any chart to **brush-zoom**;
  every player's row zooms to the same range. Click the legend
  chips to **filter** event categories on / off — filter is global
  across all rows, persists across tab switches.
- **Analysis** (placeholder): reserved for a future LLM-ready text
  analysis.
- **Map** (placeholder): reserved for a future on-map action
  visualization.

## Implementation notes

- **Stack** (per `specs/005-react-timelines/research.md`): React
  18 + TypeScript 5 + Vite 5 + Apache ECharts 5 (via
  `echarts-for-react`) + Vitest 1. State is plain React Context —
  no Redux / Zustand / Jotai. No router. No CSS framework.
- **No runtime network egress** (Principle V (c)): the production
  build bundles every asset; system-font stack only; no CDN, no
  Google Fonts, no analytics. Verified by inspecting the bundle
  for external URLs (only namespace IDs and license attribution
  strings appear; none are fetched).
- **Synchronized zoom across charts**: ECharts' `connect()` API
  groups the per-player chart instances; one zoom event updates
  every row.
- **Pure-logic Vitest tests** cover aggregations, bucket math,
  brush clamp, filter reducer, zoom-history reducer (35 tests
  derived from the committed `*.analysis.json` fixtures, no
  mocks). Visual correctness remains a manual walkthrough per
  `specs/005-react-timelines/quickstart.md`, consistent with the
  posture established in feature 003.

## Where to look

- `specs/005-react-timelines/spec.md` — feature 005 spec.
- `specs/005-react-timelines/contracts/ui-contract.md` — the
  user-visible four-tab + brush + filter contract.
- `specs/005-react-timelines/quickstart.md` — manual walkthrough
  across all four tabs and both fixtures, in both deploy modes.
- `specs/004-visualizer-tabs/` — the prior vanilla-JS visualizer.
  All cross-cutting capabilities (file picker, drag-and-drop,
  error handling, unknown-entity rendering) carry forward.
- `specs/003-replay-visualizer/` — the original visualizer
  scope (single-page match report).
