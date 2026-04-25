# Implementation Plan: Replay Visualizer

**Branch**: `003-replay-visualizer` | **Date**: 2026-04-25 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/003-replay-visualizer/spec.md`

## Summary

Deliver a static, zero-build HTML page that a user opens by double-clicking
`visualizer/index.html`, picks one Processor-output `*.analysis.json` from
disk via a file picker (drag-and-drop is a P3 add-on), and reads a fully
rendered single-replay match report on the same page: match header,
per-team-grouped player panels with build orders, hero progression,
resource transfers, plus a per-player visual timeline of every
timestamped event in the player's record; chat and observers sections
below.

The Visualizer is the third and final layer of the Parser → Processor →
Visualizer pipeline. Per the constitution (Principle V) it begins as
plain HTML + CSS + vanilla ES2020+ JavaScript with **no framework, no
build step, no bundler, no package manager, no server, no network
access**, and per Principle I it consumes only the Processor's
`*.analysis.json` document — it does NOT load `processor/entity_names.json`
separately, does NOT re-parse `.w3g`, and does NOT shell out to anything.

## Technical Context

**Language/Version**: HTML5 + CSS3 + ECMAScript 2020+ (vanilla JavaScript;
no TypeScript, no transpilation; ES2020 minimum: optional chaining,
nullish coalescing, `Array.prototype.flat`)
**Primary Dependencies**: NONE. No npm packages, no CDN scripts, no fonts
or icons fetched at runtime, no `<link rel="preconnect">`. The page is
fully self-contained within `visualizer/` and runs from `file://`.
**Storage**: Browser memory only. The loaded analysis JSON lives in a
single in-memory object for the duration of the page session;
re-loading replaces it. No `localStorage`, no `IndexedDB`, no cookies.
**Testing**: Manual walkthrough against the two committed parser-output
fixtures (`sample_replays/base_1.w3g.json`, `sample_replays/base_2.w3g.json`)
re-analyzed via `python processor/analyze.py` to produce the matching
`*.analysis.json`. Acceptance is the spec's manual review walkthrough
(see `quickstart.md`). Per the spec ("No automated frontend tests in
v1") and Principle IV scope ("parsing or analysis correctness"), no
automated frontend tests are introduced in v1.
**Target Platform**: Modern desktop evergreen browsers — last two
versions of Chrome, Firefox, Safari, Edge, on Linux / macOS / Windows.
Loaded from `file://` (no `http://` server required). IE11 and any
Chromium release older than ES2020 support are not targets.
**Project Type**: Static single-page application (no backend, no server).
**Performance Goals**: A typical analysis JSON (≤20 MB on disk, ≤90
minutes of game time, up to 8 players, ~tens of thousands of timestamped
events) parses, renders, and becomes fully usable within 3 seconds on
commodity laptop hardware (SC-002).
**Constraints**:
- Zero network access. The page MUST function with the network stack
  fully disabled.
- No build step. `index.html` references `styles.css` and `visualizer.js`
  via plain `<link>` / `<script>` tags. No `<script type="module">`-only
  features that fail under `file://` in some browsers.
- Single-file JS bundle (`visualizer.js`). ES modules from `file://`
  trigger CORS errors in Chromium-family browsers; concatenated single
  file avoids that class of failure entirely.
- Desktop-first layout, ≥1280 CSS-pixel viewports (FR-011). Narrower
  viewports degrade acceptably (no broken layout) but no dedicated
  mobile breakpoint.
- All entity display names are read from the analysis JSON itself; the
  visualizer NEVER fetches `processor/entity_names.json` (FR-008).
**Scale/Scope**: Up to 8 player panels per page, up to ~90-minute
durations, up to ~hundreds of build-order entries per player and ~tens
of hero ability-learn entries per hero. The base_1 fixture has 8 players
and a ~88-minute duration — the upper edge of the v1 design envelope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version: 1.0.0 (`.specify/memory/constitution.md`).

| Gate | Principle | Status | Evidence |
|---|---|---|---|
| Layer separation | I. Strict Layer Separation | **PASS** | The visualizer's only input is the Processor's `*.analysis.json` file, picked from disk by the user (FR-002, FR-003, FR-008). No import of, link to, or invocation of upstream Parser or Processor code. |
| Canonical parser | II. w3gjs Is The Canonical Parser | **PASS (N/A)** | The visualizer does no replay parsing whatsoever — it consumes already-analyzed JSON. w3gjs is irrelevant to this layer. |
| No premature abstractions | III. No Premature Abstractions | **PASS** | Single-purpose page. No template engine, no component library, no plugin system, no reusable widget framework. Render functions are written inline against the concrete schema; helpers are only introduced at the second use. Build orders for buildings/units/upgrades/items use four direct render passes rather than one parameterized helper unless duplication exceeds three blocks. |
| Fixture-based testing | IV. Fixture-Based Testing With Real Replays | **PASS (scoped)** | Principle IV applies to "parsing or analysis correctness." The visualizer is a presentation layer; correctness is eyeball-checked. The spec ("No automated frontend tests in v1") and the constitution's scope are aligned. The manual walkthrough is run against fixtures derived from the two committed real-replay parser-outputs. |
| Frontend evolution | V. Incremental Frontend Evolution | **PASS** | Static HTML + vanilla JS. No React, Vue, Svelte, Lit, JSX, htm, Stimulus, Alpine, jQuery, lodash, d3, charts.js, or any other framework or library. No build step, bundler, transpiler, or package manager in `visualizer/`. |

**Violations**: none. Complexity Tracking table is empty.

## Project Structure

### Documentation (this feature)

```text
specs/003-replay-visualizer/
├── plan.md              # this file
├── research.md          # Phase 0 — open questions resolved
├── data-model.md        # Phase 1 — UI-data-model facets derived from analysis JSON
├── quickstart.md        # Phase 1 — open + smoke-test instructions
├── contracts/           # Phase 1 — input contract pointer + output (UI) contract
│   ├── input-contract.md
│   └── ui-contract.md
├── checklists/          # already populated by /speckit.specify
│   └── requirements.md
└── tasks.md             # Phase 2 — created by /speckit.tasks
```

### Source Code (repository root)

```text
visualizer/
├── index.html           # entry point: page skeleton, file-picker UI, mount points
├── styles.css           # all visual styling (layout, palette, timeline marks, empty states)
├── visualizer.js        # all behavior: file read, JSON parse, validation, render, timeline
└── DATA.md              # short README of how to open and what to expect (optional but tracked)

sample_replays/
├── base_1.w3g           # already committed (Parser fixture — feature 001/002)
├── base_1.w3g.json      # already committed (Parser output — feature 002 elevated to fixture)
├── base_2.w3g           # already committed
└── base_2.w3g.json      # already committed
# base_*.w3g.analysis.json files are .gitignored (regenerable, deterministic).
# The visualizer is exercised against locally-regenerated copies, not committed JSON.
```

**Structure Decision**: A single new top-level `visualizer/` directory
sibling to the existing `parser/` and `processor/` directories. Three
files at the root of `visualizer/` (HTML, CSS, JS) plus a short
`DATA.md` mirror the project's per-layer documentation pattern
(`parser/DATA.md`, `processor/DATA.md`). No subdirectories — the layer
is small, and Principle III rules out preemptive structure for code that
does not yet exist. If `visualizer.js` materially exceeds ~1,500 lines
and a clear seam appears, splitting into multiple files (still vanilla,
still no build step, served via plain `<script>` tags in load order)
is acceptable in a follow-up.

## Complexity Tracking

> Filled ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(no violations)_ | _(n/a)_ |
