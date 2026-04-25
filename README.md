# Boovcraft

A three-layer pipeline that turns a Warcraft III replay file (`.w3g`)
into a self-contained, browser-rendered match report. Each layer
communicates with the next only through JSON files on disk — never
through in-process imports — so any layer can be inspected, diffed,
or rerun in isolation.

```
.w3g  ──► [Parser]  ──►  *.w3g.json  ──► [Processor]  ──►  *.analysis.json  ──► [Visualizer]  ──►  Match report (browser)
        Node + w3gjs                  Python (stdlib only)                  Static HTML + vanilla JS
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
xdg-open visualizer/index.html      # Linux
open visualizer/index.html          # macOS
# or just double-click visualizer/index.html in a file manager.
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
- Tests: `cd processor && pytest` (53 fixture-based pytest cases)
- Reference: `processor/DATA.md` for the output shape and the mapping
  coverage review checklist.
- Stdlib-only at runtime; `pytest` is the only dev dependency.

### Visualizer (`visualizer/`)

Static HTML page with vanilla CSS and ES2020+ JavaScript. The user
double-clicks `visualizer/index.html`, picks (or drags-and-drops) an
analysis JSON, and the page renders a complete match report
client-side: header with match outcome, per-team-grouped player
panels with build orders / heroes / resource transfers / action
totals, an inline SVG timeline per player, plus chat and observers.

- Entry point: open `visualizer/index.html` in a modern desktop
  evergreen browser (last two versions of Chrome / Firefox / Safari /
  Edge). No server. No build step. No install.
- Reference: `visualizer/DATA.md` for orientation and
  `specs/003-replay-visualizer/quickstart.md` for the manual review
  walkthrough.

## Repository layout

```
parser/                Node + w3gjs parser layer
processor/             Python analyzer layer + entity-name mapping
visualizer/            Static HTML report renderer
sample_replays/        Committed .w3g and .w3g.json fixtures
                       (.analysis.json files are .gitignored —
                       regenerate with the processor)
specs/                 Per-feature spec / plan / tasks (Spec Kit)
.specify/              Spec Kit configuration, templates, hooks
CLAUDE.md              Agent runtime guidance
```

## Project posture

The architecture and the workflow are governed by
`.specify/memory/constitution.md` (v1.0.0). Five principles in short:

1. **Strict layer separation** — JSON-on-disk is the only inter-layer
   contract. No cross-layer imports.
2. **`w3gjs` is the canonical parser** — no custom binary readers.
3. **No premature abstractions** — code for the concrete case.
4. **Fixture-based testing with real replays** — no synthetic byte
   streams, no mocked `w3gjs` output.
5. **Incremental frontend evolution** — visualizer starts as static
   HTML; framework adoption requires a plan + amendment.

Each feature follows the Spec Kit `/speckit.specify → /speckit.plan
→ /speckit.tasks → /speckit.implement` workflow; per-feature design
docs and task lists live under `specs/`.

## Status

| Layer | Feature | State |
|---|---|---|
| Parser | [001](specs/001-replay-parser/) | shipped |
| Processor | [002](specs/002-replay-analyzer/) | shipped |
| Visualizer | [003](specs/003-replay-visualizer/) | shipped (v1; timeline UX redesign queued for a future iteration) |
