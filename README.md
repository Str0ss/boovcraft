# Boovcraft

A three-layer pipeline that turns a Warcraft III replay file (`.w3g`)
into a self-contained, browser-rendered match report. Each layer
communicates with the next only through JSON files on disk — never
through in-process imports — so any layer can be inspected, diffed,
or rerun in isolation.

```
.w3g  ──► [Parser]  ──►  *.w3g.json  ──► [Processor]  ──►  *.analysis.json  ──► [Visualizer]  ──►  Match report (browser)
        Node + w3gjs                  Python (stdlib only)                  React + TypeScript + ECharts
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

# 3. Open the visualizer and pick the .analysis.json.
cd visualizer && docker compose up   # production (http://localhost:8080)
# or, for hot-reloading development:
cd visualizer && npm install && npm run dev   # http://localhost:5173
```

The two committed sample replays in `sample_replays/` come with their
parser-output JSON pre-tracked so step 1 is skippable for them — go
straight to step 2.

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

Python 3.11+ CLI that consumes a parser-output JSON and produces a
visualizer-ready analysis JSON. It computes per-player build orders,
hero progression, action totals, resource transfers; annotates every
WC3 entity reference with a human-readable display name from a
committed mapping (`processor/entity_names.json`, ~650 entries
extracted from `w3gjs`'s own data tables); and forwards chat,
observers, and match metadata.

- Entry point: `processor/analyze.py` (`python3 processor/analyze.py <input.w3g.json>`)
- Tests: `cd processor && pytest` (67 fixture-based pytest cases —
  53 baseline plus 14 covering the per-event timed-actions
  extraction added in feature 004)
- Reference: `processor/DATA.md` for the output shape and the mapping
  coverage review checklist.
- Stdlib-only at runtime; `pytest` is the only dev dependency.

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
processor/             Python analyzer layer + entity-name mapping
visualizer/            React + Vite + ECharts SPA report renderer
sample_replays/        Committed .w3g and .w3g.json fixtures
                       (.analysis.json files are .gitignored —
                       regenerate with the processor)
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
