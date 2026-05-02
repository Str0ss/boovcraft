# Visualizer (layer 3 of 3)

The third and final layer of the Parser → Processor → Visualizer
pipeline. Reads one Processor-layer analysis JSON and renders it as a
single-replay match report on a static HTML page organized into four
tabs: **Summary**, **Timelines**, **Analysis**, **Map**.

## Input contract

`processor/DATA.md` defines the shape of the JSON this page consumes.
The Visualizer trusts that contract verbatim and never invokes the
Parser or the Processor at runtime.

## How to open

Double-click `visualizer/index.html` in a file manager — no server, no
build step, no install. The page loads under the `file://` protocol in
any modern desktop evergreen browser (Chrome / Firefox / Safari / Edge,
last two versions).

## How to use

1. Run the analyzer once per replay you want to view, e.g.
   `python processor/analyze.py sample_replays/base_1.w3g.json`. This
   writes `sample_replays/base_1.w3g.analysis.json` next to the parser
   output. (`*.analysis.json` files are `.gitignore`d; regenerate
   locally as needed.)
2. Open `visualizer/index.html`.
3. Click the file picker (or drag the file onto the page) and choose
   the `*.analysis.json` you produced in step 1.
4. The match report renders client-side. Pick a different file at any
   time to load another replay.

## The four tabs

- **Summary** (default after loading): match header, per-team grouped
  player panels with action totals, group hotkeys, **aggregated**
  production / heroes / resource transfers (counts and arrow chains —
  no per-event timestamps), chat, and observers. This is the at-a-
  glance overview.
- **Timelines**: one full-width histogram per player, stacked top to
  bottom. Bars show event counts per time bucket; major events
  (build / train, ability, item, transfers) are visually distinct
  from minor input (right-clicks, selects, hotkey selects). Zoom and
  pan are **global** — every row stays aligned on the match clock.
- **Analysis** (placeholder): reserved for a future LLM-ready text
  analysis.
- **Map** (placeholder): reserved for a future on-map action
  visualization.

## Implementation notes

- Static HTML + vanilla ES2020+ JavaScript — no framework, no build
  step, no package manager (Principle V). The whole layer lives in
  three files: `index.html`, `styles.css`, `visualizer.js`.
- `visualizer.js` is a single IIFE with a single `pageState` object
  as the source of truth. Tab routing is a `setActiveTab` /
  `renderActiveTab` pair; the Timelines tab's zoom + pan state lives
  in `pageState.zoomState` and is preserved across tab switches.
- File-split decision (research.md R7): not split. As of feature 004,
  `visualizer.js` is ~1,120 lines, comfortably under the ~1,500-line
  soft threshold flagged in feature 003's plan. Future features may
  push it over; at that point split into multiple plain `<script>`
  tags in load order (no ES modules — `file://` triggers CORS
  errors in Chromium when modules are involved).

## Where to look

- `specs/004-visualizer-tabs/spec.md` — feature 004 spec (tabs).
- `specs/004-visualizer-tabs/contracts/ui-contract.md` — the
  user-visible four-tab contract.
- `specs/004-visualizer-tabs/quickstart.md` — the manual review
  walkthrough across all four tabs and both fixtures.
- `specs/003-replay-visualizer/` — feature 003 baseline (single-page
  match report). Most cross-cutting concerns (file picker, drag-and-
  drop, error handling, unknown-entity rendering) carry forward
  unchanged.
