# Quickstart: Interactive Timelines (Feature 005)

A short manual walkthrough for verifying the migrated React +
ECharts visualizer end-to-end against the two committed replay
fixtures, in **both** deploy modes (production + development), per
Principle V (b) of constitution v1.1.0.

## 0. One-time setup (host machine)

```sh
# Parser / Processor — unchanged from prior features
cd parser && npm install && cd -
cd processor && pip install -e . && cd -

# Visualizer (React app) — first-time install
cd visualizer && npm install && cd -
```

Prerequisites: Node.js 20+, Python 3.11+, Docker Engine + Compose
plugin (for production mode).

## 1. Regenerate analysis JSON fixtures

Same step as feature 004:

```sh
node parser/parse.js sample_replays/base_1.w3g
node parser/parse.js sample_replays/base_2.w3g
python processor/analyze.py sample_replays/base_1.w3g.json
python processor/analyze.py sample_replays/base_2.w3g.json
```

The `*.analysis.json` files remain `.gitignore`d and unchanged in
shape from feature 004 (Principle V (a) — input contract
preserved).

Sanity-check the Processor pytest is still green:

```sh
cd processor && pytest && cd -
```

Expect: 67 passed (no Processor changes in this feature).

## 2. Bring up the visualizer (development mode)

```sh
cd visualizer && npm run dev
```

Vite prints a URL (default `http://localhost:5173`). Open it in a
modern desktop browser. Hot reload is active — file edits propagate
without a manual refresh.

**SC-005 dev check**: `npm run dev` to "ready" log line should
complete in ≤ 10 seconds.

## 3. Bring up the visualizer (production mode)

In a fresh terminal:

```sh
cd visualizer && docker compose up
```

This builds the multi-stage Docker image (first run takes longer)
then runs nginx-on-alpine serving `dist/` on port 8080. Open
`http://localhost:8080`.

**SC-005 production check**: from `docker compose up` to
first-meaningful-paint, ≤ 30 seconds on commodity laptop hardware
(measured against a warm Docker image cache; first-ever build of
the image is allowed to take longer).

To stop: `Ctrl-C` then `docker compose down`.

## 4. Smoke test against base_2 (short fixture, 3v3, no chat)

Pick `sample_replays/base_2.w3g.analysis.json` via the file picker
(or drag-drop).

### Tab strip

- 4 tabs, in order: **Summary**, **Timelines**, **Analysis**, **Map**.
- **Summary** is active by default.

### Summary tab — verify

- Match header: ~16-minute duration, 3v3, "Undetermined" outcome.
- 6 player panels grouped into 2 teams.
- For each player:
  - Action totals listed (rightclick, select, selecthotkey, etc.).
  - Group hotkeys table populated.
  - Production aggregation rows like `Ziggurat (×3)`, no timestamps.
  - Hero aggregation rows like `Far Seer — Level 4: ...`, no
    timestamps.
  - Resource transfer aggregation: empty state for players with no
    transfers; per-recipient + per-resource rows for players with
    transfers.
- Chat section: empty state ("No in-game chat in this replay.").
- Observers section: lists every observer.

### Timelines tab — verify (with new feature 005 capabilities)

Switch to **Timelines**.

- 6 player rows stacked top-to-bottom; each row spans the full
  available content width.
- Each row is an ECharts canvas histogram.
- Default zoom: full match (~16 min) visible.
- Legend rendered with one chip per category, plus bulk-toggle
  buttons.

**Brush-to-zoom (US1)**:
- Drag horizontally on any player's chart from time A to time B.
  A translucent rectangle follows the cursor with edge time labels.
- Release: every player's row re-renders zoomed to `[A, B]`. All
  rows stay aligned; bucket widths recompute.
- Press Escape during drag → no zoom change.
- Drag < 5 pixels → no zoom change (treated as click).
- Click "Back": returns to prior zoom (full match if this was the
  first brush). "Forward" then re-does the brush.
- Click "Reset zoom": back to full match; back/forward stacks
  cleared.

**Filter (US2)**:
- Click the **Right-click** chip in the legend. Every histogram
  re-renders with rightclick segments removed. Hover any bar — the
  tooltip lists only the remaining categories.
- Click the chip again — rightclick is restored.
- Click **All minor → off**. Every minor category disables at once.
  Histograms now show only major event bars (build / ability /
  item / transfer / etc.). Click **All minor → on** to restore.
- Click **All off**. Charts render empty axes (no bars), no
  errors, no hidden rows. Click **All on** to restore.

**Persistence**:
- Toggle a few categories off; brush-zoom into a 3-minute window;
  switch to Summary tab; switch back. Filter state and zoom state
  both still in place.
- Re-pick a different file — both reset to defaults.

**Performance (SC-002 / SC-003)**:
- After a brush release, every row's re-render visibly completes
  within ~100 ms of perceived latency.
- After a category toggle, same budget.

### Analysis tab — verify

Switch to **Analysis**. Placeholder renders with "coming soon"
copy. Switch back to Summary or Timelines: both still work.

### Map tab — verify

Switch to **Map**. Placeholder renders, optionally surfacing the
loaded match's map name. Switch back: other tabs still work.

## 5. Smoke test against base_1 (long fixture, 4v4, ~88 min, dense data)

Re-pick `sample_replays/base_1.w3g.analysis.json` via the file
picker.

- Page replaces prior report cleanly (no base_2 bleed-through).
- Summary tab active; 8 player panels.
- Timelines: 8 stacked rows; default zoom is full match
  (~88 min). Bars are legible at default zoom — none sub-pixel.
- Brush-to-zoom into a 3-minute window where you can see two
  players cluster activity. Confirm SC-001: the find-and-zoom
  gesture takes < 5 seconds and one drag.
- Toggle minor categories off — the major-event peaks become
  visible against quieter backgrounds.
- Verify base_1's `unknown: true` flagged hero entry still renders
  with the visible marker on the Summary tab and is represented
  on the Timelines tab.

## 6. Cross-cutting checks

### SC-006: zero outbound network egress

- Open browser DevTools → Network tab → filter "Other / Doc /
  Script / Stylesheet / Font" → reload the page.
- After the page is fully loaded, exercise every feature: load a
  file, switch tabs, brush-zoom, filter, back/forward, reload a
  different file.
- The Network tab MUST show **zero entries beyond the local
  origin** (the browser → local Vite dev server, or browser →
  local nginx container). No external `https://` URLs at any
  point.

### Non-regression (FR-023 / FR-024 / SC-004)

Walk through `specs/003-replay-visualizer/quickstart.md` § 3 and
`specs/004-visualizer-tabs/quickstart.md` § 3, against both
fixtures, against the migrated React app. Every check that passed
on feature 003/004's static page MUST pass here. Any deviation is
a regression.

## 7. Vitest unit tests

```sh
cd visualizer && npm run test
```

Expected coverage:
- `tests/zoomHistory.test.ts` — back/forward stack semantics,
  brush push, reset, file-load.
- `tests/filterState.test.ts` — toggle, set-group, reset,
  initial-state-all-enabled.
- `tests/aggregations.test.ts` — production count totals match
  feature 004's by-fixture spot checks; hero chains preserve
  abilityOrder; transfer aggregation grouping by (recipient,
  resource).
- `tests/timelineEvents.test.ts` — `bucketEvents` is linear;
  `chooseBucketWidth` snaps to nice intervals; counts match
  `actions.totals` invariant.

All tests MUST pass before declaring the feature shipped.

## 8. Acceptance

If sections 1–7 all pass, feature 005's user-facing scope is
verified. Combined with all-green Vitest and the Processor's still-
green pytest, this is the acceptance gate.

## Optional: alternative deployment without Docker

If the user does not have Docker installed, the production-equivalent
fallback is:

```sh
cd visualizer && npm run build && npx serve dist/
```

This serves the built `dist/` folder over plain HTTP via `serve`.
Documented in `visualizer/DATA.md`. Both `docker compose up` and
`npm run build && npx serve dist/` satisfy Principle V (b)'s
"single command, no manual configuration" requirement.
