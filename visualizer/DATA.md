# Visualizer (layer 3 of 3)

The third and final layer of the Parser → Processor → Visualizer
pipeline. Reads one Processor-layer analysis JSON and renders it as a
single-replay match report on a static HTML page.

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

## Where to look

- `specs/003-replay-visualizer/spec.md` — feature spec.
- `specs/003-replay-visualizer/contracts/ui-contract.md` — the
  user-visible match-report contract (what each section must contain).
- `specs/003-replay-visualizer/quickstart.md` — the manual review
  walkthrough.
