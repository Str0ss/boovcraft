# Boovcraft

A three-layer pipeline that turns a Warcraft III replay file (`.w3g`)
into a self-contained, browser-rendered match report. Each layer
communicates with the next only through JSON files on disk — never
through in-process imports — so any layer can be inspected, diffed,
or rerun in isolation.

```
.w3g  ──► [Parser]  ──►  *.w3g.json  ──► [Processor: analyze]  ──►  *.analysis.json  ──► [Visualizer]  ──►  Match report (browser)
        Node + w3gjs                  Python (stdlib)                                 React + TypeScript + ECharts
                                                                       └► [Processor: extract_events]  ──►  *.events.json
                                                                          Python + pandas + scikit-learn          (LLM-ready narrative events)
```

## End-to-end: from a replay file to a rendered report

Once-per-clone setup (do each command from the repo root):

```bash
# Parser layer (Node)
cd parser && npm install && cd ..

# Processor layer (Python 3.11+)
python3 -m venv processor/.venv
source processor/.venv/bin/activate
pip install -e 'processor[dev]'
deactivate
```

Then for each replay:

```bash
# 1. Parse the .w3g into raw JSON.
node parser/parse.js path/to/replay.w3g
# → writes path/to/replay.w3g.json

# 2. Analyze the parser output into a visualizer-ready document.
python3 processor/analyze.py path/to/replay.w3g.json
# → writes path/to/replay.w3g.analysis.json

# 3. (Optional) Derive a narrative-events JSON for LLM consumption.
python3 processor/extract_events.py path/to/replay.w3g.analysis.json
# → writes path/to/replay.w3g.events.json

# 4. Open the visualizer and pick the .analysis.json.
cd visualizer && docker compose up   # production (http://localhost:8080)
# or, for hot-reloading development:
cd visualizer && npm install && npm run dev   # http://localhost:5173
```

The two committed sample replays in `sample_replays/` come with their
parser-output JSON pre-tracked so step 1 is skippable for them — go
straight to step 2. Step 3 is only needed if you want the events
document; the visualizer does not consume it yet.

## What each layer does

### Parser (`parser/`)

Node.js script that wraps the [`w3gjs`](https://www.npmjs.com/package/w3gjs)
library and writes `w3gjs`'s full parse result — match metadata,
players, lobby settings, map info, plus the raw `gamedatablock` event
stream — to `<input>.w3g.json`. It does no interpretation: anything in
the parser output is exactly what `w3gjs` produced.

- Entry point: `parser/parse.js` (`node parser/parse.js <replay.w3g>`)
- Tests: `cd parser && npm test`
- Reference: `parser/DATA.md` for the output shape.

### Processor (`processor/`)

Python 3.11+ with two CLI entry points.

**`processor/analyze.py`** — consumes a parser-output JSON and produces
a visualizer-ready analysis JSON. Computes per-player build orders,
hero progression, action totals, resource transfers; annotates every
WC3 entity reference with a human-readable display name from a
committed mapping (`processor/entity_names.json`, ~650 entries
extracted from `w3gjs`'s own data tables); forwards chat, observers,
and match metadata; retains action coordinates on every replay action
that carried a target position.

**`processor/extract_events.py`** (added in feature 006) — consumes
the analyzer-output JSON and produces a narrative-events JSON
document for downstream LLM tooling. Emits a flat chronological array
of 13 recognized event kinds (idle periods, building rebuilds, tech
milestones, expos, creeping departures, tower-rush candidates, base
incursions, ally-zone creeping, joint engagements, hero teleports,
production stalls, intensity peaks, resource transfers). Every event
carries a stable content-derived 16-hex-char id; inferred kinds carry
an explicit `inferenceLabel` so a consumer can distinguish observable
signal from inferred meaning. The events document is byte-identical
across re-runs.

- Entry points:
  - `python3 processor/analyze.py <input.w3g.json>` → `<input>.w3g.analysis.json`
  - `python3 processor/extract_events.py <input.w3g.analysis.json>` → `<input>.w3g.events.json`
- Tests: `cd processor && pytest` (146 fixture-based pytest cases:
  67 baseline, 16 covering coord retention, 51 covering the events
  stage, 12 covering hedging discipline and threshold consistency)
- References: `processor/DATA.md` (analyzer output shape) and
  `processor/EVENTS.md` (events output shape, hedging discipline,
  entity catalogs).
- Runtime dependencies: `pandas` and `scikit-learn` (used by
  `extract_events.py`); `pytest` is the only dev dependency. Both
  runtime deps are declared in `processor/pyproject.toml` and
  installed by the `pip install -e 'processor[dev]'` line above.

### Visualizer (`visualizer/`)

React 18 + TypeScript single-page app, bundled with Vite and
rendered client-side. The user opens the served URL, picks (or
drags-and-drops) an analysis JSON, and the page renders a four-tab
match report: **Summary** (header, per-team-grouped player panels
with build orders / heroes / resource transfers / action totals,
chat, observers), **Timelines** (one Apache ECharts histogram per
player, brush-to-zoom synchronized across rows, clickable category
filter), **Analysis** (placeholder for an LLM-ready text export),
**Map** (placeholder for on-map action visualization).

Two first-class deploy modes (per constitution v1.1.0 Principle V):

- **Production** — `cd visualizer && docker compose up`, open
  <http://localhost:8080>. Multi-stage build (`node:20-alpine`
  builds, `nginx:alpine` serves).
- **Development** — `cd visualizer && npm install && npm run dev`,
  open <http://localhost:5173>. Vite dev server with HMR.

The bundle ships every asset; no runtime network egress (no CDN, no
Google Fonts, no analytics).

- Tests: `cd visualizer && npm test` (35 Vitest cases — pure-logic
  unit tests over aggregations, bucket math, brush clamp, filter
  reducer, zoom-history reducer).
- Reference: `visualizer/DATA.md` for orientation and
  `specs/005-react-timelines/quickstart.md` for the manual review
  walkthrough across both deploy modes.

## Repository layout

```
parser/                Node + w3gjs parser layer
processor/             Python — two entry points (analyze, extract_events)
                       + entity-name mapping + DATA.md + EVENTS.md
visualizer/            React + Vite + ECharts SPA report renderer
sample_replays/        Committed .w3g and .w3g.json fixtures
                       (.analysis.json and .events.json files are
                       .gitignored — regenerate with the processor)
specs/                 Per-feature spec / plan / tasks (Spec Kit)
.specify/              Spec Kit configuration, templates, hooks
CLAUDE.md              Agent runtime guidance
```

## Project posture

The architecture and the workflow are governed by
`.specify/memory/constitution.md` (v1.1.0). Six principles in short:

1. **Strict layer separation** — JSON-on-disk is the only inter-layer
   contract. No cross-layer imports.
2. **`w3gjs` is the canonical parser** — no custom binary readers.
3. **No premature abstractions in internal code** — code for the
   concrete case.
4. **Fixture-based testing with real replays** — no synthetic byte
   streams, no mocked `w3gjs` output.
5. **Incremental frontend evolution** — the visualizer started as
   static HTML; the interactive-analytical exception (added in
   v1.1.0) permits a framework when it preserves the JSON contract,
   single-command deploy, and zero runtime egress.
6. **Prefer well-established tools** — adopt a mature library over a
   bespoke implementation when it meets the four criteria spelled
   out in the constitution.

Each feature follows the Spec Kit `/speckit.specify → /speckit.plan
→ /speckit.tasks → /speckit.implement` workflow; per-feature design
docs and task lists live under `specs/`.

## Status

| Layer | Feature | State |
|---|---|---|
| Parser | [001](specs/001-replay-parser/) | shipped |
| Processor | [002](specs/002-replay-analyzer/) | shipped |
| Visualizer | [003](specs/003-replay-visualizer/) | shipped (v1 vanilla-JS SPA) |
| Visualizer | [004](specs/004-visualizer-tabs/) | shipped (four-tab layout + per-event minor timelines) |
| Visualizer | [005](specs/005-react-timelines/) | shipped (React + ECharts, brush-zoom, category filter) |
| Processor | [006](specs/006-event-extraction/) | shipped (coord retention + narrative events stage) |
