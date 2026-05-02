# Implementation Plan: Visualizer Tabs

**Branch**: `004-visualizer-tabs` | **Date**: 2026-05-01 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-visualizer-tabs/spec.md`

## Summary

Reorganize the static visualizer (feature 003) into a four-tab match
report — **Summary**, **Timelines**, **Analysis**, **Map** —
hosted on the same single-file, file://-loaded HTML page that
feature 003 ships. The Summary tab keeps every non-timeline match-
level section feature 003 produced, but replaces the per-event
production / hero / resource-transfer lists with compact
aggregations. The Timelines tab is the new analytical view: every
player gets a full-width histogram row, all rows share a single
**global** zoom-and-pan state, and bucket width adapts to viewport
+ zoom. To feed the Timelines tab with the per-event minor-action
data the spec requires (FR-015 / FR-015a / FR-015b / FR-015c), the
**Processor** layer is extended in this feature to walk the
existing parser-output `events[]` stream, classify each
`commandBlock.actions[]` entry into a category (rightclick, select,
selecthotkey, basic, ability, etc.), and emit a per-player
`timedActions` array of `{timeMs, category}` records into
`*.analysis.json`. The **Parser** layer requires no behavior change
— `w3gjs` already exposes the raw events the Processor consumes —
so Principle II (canonical parser) is upheld trivially. The
**Analysis** and **Map** tabs ship as labelled placeholders.

Per Principle V (Incremental Frontend Evolution) the Visualizer
remains static HTML + vanilla ES2020+ JavaScript with no build
step, no package manager, and no framework. The user's "consider
React" hint is recorded but the feature does not justify a
framework: tabs are CSS class swaps, histograms are SVG, and the
in-page state surface is a single object. The threshold that would
justify revisiting Principle V is captured in research.md so the
question is resolved going forward.

## Technical Context

**Language/Version**:
- Visualizer: HTML5 + CSS3 + ECMAScript 2020+ (vanilla JS, no
  TypeScript, no transpilation) — unchanged from feature 003.
- Processor: Python 3.11+ — unchanged from feature 002.
- Parser: Node.js + `w3gjs` — unchanged from features 001/003;
  no behavior change in this feature.

**Primary Dependencies**:
- Visualizer: NONE (no npm packages, no CDN scripts, no fonts or
  icons fetched at runtime). Per Principle V.
- Processor: existing `processor/pyproject.toml` only.
- Parser: existing `w3gjs` only.

**Storage**: Browser memory only on the Visualizer side (loaded
JSON lives in a single in-memory object for the page session;
re-loading replaces it). Parser and Processor remain file-in /
file-out.

**Testing**:
- Processor: extend the existing pytest suite to cover the new
  `timedActions` extraction against both committed fixtures
  (`sample_replays/base_1.w3g.json`, `sample_replays/base_2.w3g.json`),
  asserting record count and category breakdown sanity (totals
  equal the existing `actions.totals` per category, since both
  derive from the same event stream).
- Parser: no new tests (no behavior change).
- Visualizer: manual walkthrough against regenerated
  `*.analysis.json` fixtures (per quickstart.md) — feature 003's
  "no automated frontend tests in v1" stance carries forward.

**Target Platform**: Modern desktop evergreen browsers (last two
versions of Chrome, Firefox, Safari, Edge) on Linux / macOS /
Windows, loaded from `file://`. Unchanged from feature 003.

**Project Type**: Multi-layer pipeline (Node parser, Python
processor, static-HTML visualizer). This feature touches the
Processor and the Visualizer; the Parser is unchanged.

**Performance Goals**:
- A regenerated long-match analysis JSON (base_1: ~88 minutes, 8
  players, ~92k raw events → ~tens of thousands of per-player
  timed-action records) parses, validates, and renders the
  Summary tab within 3 seconds (carrying SC-002 of feature 003).
- Switching tabs: <100 ms perceived UI latency (SC-004).
- Zoom adjustment on the Timelines tab: <100 ms perceived UI
  latency (SC-005).
- Processor re-run on a long-match parser-output JSON: stays
  within the same operational envelope as today (no order-of-
  magnitude slowdown when adding the per-event walk). The walk
  is O(events × actions-per-block) — already what feature 002's
  totals computation does, just retaining each entry instead of
  incrementing a counter.

**Constraints**:
- Zero network access on the Visualizer (Principle V; FR-008 of
  feature 003).
- No build step, no bundler, no npm install in the visualizer/
  directory (Principle V).
- Single concatenated `visualizer.js` is acceptable; if it
  materially exceeds ~1,500 lines, split into multiple plain
  `<script>` tags loaded in dependency order (still no modules,
  to avoid `file://` CORS).
- The Processor MUST keep the existing analysis-JSON top-level
  shape stable — additions are additive, not breaking. Adding
  `players[].actions.timedActions` is additive; existing
  consumers (current visualizer, future tools) keep working.
- Analysis-JSON size growth: order-of-magnitude estimate for a
  90-minute 8-player match is ~50–150k minor-action records
  total at ~30–80 bytes each → ~5–15 MB JSON growth on top of
  the current ~5–8 MB. The 20 MB on-disk envelope from feature
  003's plan is comfortably preserved.

**Scale/Scope**:
- 4 tabs, 1 of which (Timelines) renders 1–8 player histograms
  simultaneously at any zoom level.
- Per-player timed-action stream: typical ladder match
  ~5,000–20,000 records; long match (base_1) potentially
  ~50,000+ records; viewport renders only the bucketed counts so
  the per-frame cost is bucket-count × player-count, not record-
  count × player-count.
- Visualizer code-size envelope: feature 003 shipped 811 LOC of
  `visualizer.js`; this feature is expected to add ~600–900
  LOC (tabs scaffold, three new render passes for aggregations,
  histogram + zoom + pan, two stub tabs). At that ceiling the
  single-file is still tractable; we'll evaluate splitting in
  research.md.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version: 1.0.0 (`.specify/memory/constitution.md`).

| Gate | Principle | Status | Evidence |
|---|---|---|---|
| Layer separation | I. Strict Layer Separation | **PASS** | The Visualizer's only input remains the Processor's `*.analysis.json` (no upstream imports, no re-parsing). The Processor's only input remains the Parser's `*.json` (no `w3gjs` calls in Python). Each layer change is contained to that layer; the inter-layer contract is JSON-on-disk, additive only. |
| Canonical parser | II. w3gjs Is The Canonical Parser | **PASS** | The Parser layer is unchanged. `w3gjs`'s existing event-stream output (`events[].commandBlocks[].actions[]`) is the source of truth for minor-action data; this feature consumes it via the Processor rather than introducing a custom binary reader or alternative parser. No new parsing logic, no fork, no replacement library. |
| No premature abstractions | III. No Premature Abstractions | **PASS** | Four tabs are implemented as four render functions over a single state object — no tab framework, no router, no component system. Aggregations for production / heroes / transfers are three direct render passes, not a parameterized "aggregate-and-render" engine. The histogram is a single render function with zoom and bucket-width arguments, not a charting library. The `timedActions` extraction in the Processor is a single classifier function over the event stream — no event-bus or pluggable-classifier abstraction. |
| Fixture-based testing | IV. Fixture-Based Testing With Real Replays | **PASS** | Processor tests are extended to cover the new extraction against the two committed real-replay parser-output fixtures. The acceptance check is the same pattern feature 002 uses: regenerate analysis JSON, assert structural facts, verify counts equal totals. Visualizer is manual per its existing scope (presentation layer; correctness is eyeball-checked). |
| Frontend evolution | V. Incremental Frontend Evolution | **PASS** | Static HTML + vanilla JS continues. No React, Vue, Svelte, Lit, JSX, htm, Stimulus, Alpine, jQuery, lodash, d3, charts.js, or any other framework / library / build step / bundler / package manager / transpiler in `visualizer/`. The user's "consider React" hint is recorded in research.md as a future-trigger checklist (when this question would have a different answer); the present answer is that none of those triggers fire for this feature. |

**Violations**: none. Complexity Tracking table is empty.

## Project Structure

### Documentation (this feature)

```text
specs/004-visualizer-tabs/
├── plan.md              # this file
├── research.md          # Phase 0 — open questions resolved
├── data-model.md        # Phase 1 — UI-data-model facets + Processor extension shape
├── quickstart.md        # Phase 1 — open + smoke-test instructions for all four tabs
├── contracts/           # Phase 1 — input/output contract pointers
│   ├── input-contract.md     # additive change to analysis JSON shape (timedActions)
│   └── ui-contract.md        # tab strip + summary aggregations + timeline histogram
├── checklists/
│   └── requirements.md       # already populated by /speckit-specify
└── tasks.md             # Phase 2 — created by /speckit-tasks
```

### Source Code (repository root)

```text
visualizer/
├── index.html           # entry point: page skeleton, file-picker, tab strip mount points
├── styles.css           # all visual styling (tab strip, summary aggregations, timeline histogram, stub tabs)
├── visualizer.js        # all behavior: file read, JSON parse, validation, tab routing, all tab renderers, zoom state
└── DATA.md              # short README; updated to describe the four-tab layout

processor/
├── analyze.py           # extended: walks parser events, emits players[].actions.timedActions
├── tests/               # extended: covers timedActions extraction against committed fixtures
└── (DATA.md, pyproject.toml, entity_names.json — unchanged or doc-touched only)

parser/
└── (unchanged — w3gjs already exposes the events the processor consumes)

sample_replays/
└── (committed .w3g and .w3g.json fixtures unchanged; .w3g.analysis.json files remain regenerable / .gitignored)
```

**Structure Decision**: This feature reuses the existing
three-layer top-level structure (`parser/`, `processor/`,
`visualizer/`) without adding any new top-level directories. All
visualizer changes stay in the three existing files
(`index.html`, `styles.css`, `visualizer.js`); if `visualizer.js`
crosses ~1,500 lines during implementation, the split-into-multiple-
plain-script-tags option from feature 003's plan applies and is
exercised then. All Processor changes stay in `processor/analyze.py`
plus the existing `processor/tests/` directory; no new module is
introduced because the extraction is one classifier function and
one passthrough into the existing per-player builder.

## Complexity Tracking

> Filled ONLY if Constitution Check has violations that must be justified.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_ | _(no violations)_ | _(n/a)_ |
