# UI Contract: Interactive Timelines (Feature 005)

User-facing contract for the migrated visualizer. Builds on
`specs/004-visualizer-tabs/contracts/ui-contract.md` (the four-tab
contract) — only the deltas introduced by this feature are detailed
here.

## What carries forward unchanged from feature 004

- The four tabs in order: **Summary**, **Timelines**, **Analysis**,
  **Map**.
- Default active tab on load: Summary.
- File picker entry + drag-and-drop overlay.
- Summary tab content (match header, per-team panels, action totals,
  group hotkeys, aggregated production / heroes / transfers, chat,
  observers, all empty-state treatments).
- Per-team grouping and player-panel layout.
- Time formatting (`mm:ss` / `h:mm:ss`).
- Unknown-entity rendering (raw id + visible marker).
- Empty-state copy.
- Tab-switch behavior (state preserved across switches; analysis JSON
  not re-read).
- File-reload reset behavior (active tab → Summary, zoom → full match,
  no bleed-through).

The migrated React app MUST render every section identically to
feature 004's static page, modulo any incidental visual polish that
does not regress legibility.

## Brush-to-zoom (US1 / FR-001–008)

### Visual affordance

- Cursor changes to a **horizontal-resize style** (or equivalent —
  whatever ECharts' brush component renders by default) while
  hovering over a player's chart area.
- A subtle hint line (e.g., one line of caption text below the legend
  the first time the Timelines tab is shown per session) tells the
  user "drag horizontally on a chart to zoom into that range." This
  is not a modal or tutorial — just a discoverable affordance.

### Interaction

- **Press**: pointer-down on any player's chart area starts a brush.
  ECharts' `brush` component handles this; we configure
  `brushType: 'lineX'` (horizontal selection only) and
  `brushMode: 'single'`.
- **Drag**: a translucent rectangle follows the cursor; both edges
  labelled with the corresponding `mm:ss` / `h:mm:ss` time.
- **Release**: the brushed range becomes the new global zoom.
  ECharts dispatches `brushSelected`; the React handler converts
  the pixel range to time range, calls `dispatchers.brushZoom(range)`,
  which cascades:
  1. Push the prior `zoomState` onto `zoomHistory.back`; clear `forward`.
  2. Update `zoomState` to the new range.
  3. ECharts' `connect()` group re-renders all linked instances.
- **Click (drag < ~5 pixels)**: treated as a click, not a brush —
  no zoom change (FR-003).
- **Escape during drag**: cancels the brush (FR-005). ECharts'
  built-in `brushEnd` cancellation handles this; React keypress
  listener forwards `Escape` to the chart instance.

### Constraints

- Brush minimum: ~250 ms visible range. A brush narrower than this
  (in pixel terms, `pixelsToTimeRange` produces a sub-MIN range) is
  clamped to MIN centered on the brush midpoint (FR-004).
- Brush past chart edges: clamped to current visible bounds (FR-006).
- Slider position: updates to reflect the new zoom level after a
  brush completes (FR-007). Two-way sync: dragging the slider also
  updates `zoomState`, but slider movements do NOT push history.
- All player rows zoom together because they're members of the same
  `echarts.connect()` group (FR-002 / FR-008).

## Event-category filter (US2 / FR-009–017)

### Filter affordance — the legend chips

- The Timelines tab's legend renders one chip per category: 6 major
  (`Build / train`, `Ability`, `Item`, `Remove unit`, `Esc`,
  `Transfer`), 6 minor (`Right-click`, `Select`, `Hotkey select`,
  `Basic`, `Assign group`, `Subgroup`).
- Each chip shows the category's color swatch and label.
- Cursor on hover changes to a pointer.
- A disabled chip renders with reduced opacity and a strikethrough
  on the label (or equivalent unambiguous visual state).

### Bulk-toggle affordances (FR-012)

Adjacent to the legend, four small buttons:
- **All on** — every category enabled.
- **All off** — every category disabled.
- **Major on** / **Minor on** — one set enabled (toggle the named
  group; idempotent).
- (Equivalent compact UI variations are acceptable; the spec
  requires "at minimum" all-major / all-minor + all-on / all-off.)

### Interaction

- **Click a chip**: toggles its category. Every player's histogram
  re-renders with that category's bar segments removed (or restored).
  Tooltips on subsequent hovers exclude (or include) the toggled
  category.
- **Click a bulk button**: flips every category in the named group
  atomically.

### State & coordination

- The filter state is **global** to the Timelines tab — applies to
  every player's chart simultaneously (FR-010).
- Persists across tab switches and zoom changes (FR-013, FR-014).
- Resets to "all enabled" on file load (FR-015).
- Does NOT propagate to the Summary tab (FR-017 / Assumption in
  spec) — Summary aggregations always reflect the full data set.

### Empty-everything

When all categories are disabled, every player's chart still renders
the time axis but shows no bars. Tooltips on bucket hover show
"0 events in range." No error state, no hidden row (FR-016).

## Zoom history (US3 / FR-018–022)

### Affordance

Adjacent to the existing zoom controls:
- **◀ Back** — returns to the prior zoom state.
- **▶ Forward** — returns from a Back press to the state that was
  just left.
- Both buttons render visibly disabled when the corresponding stack
  is empty (FR-022).

### Interaction

- Click **Back**: pop from `zoomHistory.back`; push current
  `zoomState` onto `forward`; set `zoomState` to popped entry.
- Click **Forward**: symmetric.
- Click **Reset zoom**: clear both stacks; set `zoomState` to full
  match (FR-020).
- Brush-zoom while history has forward entries: discards forward
  (standard browser semantics, FR-019).
- File reload: clears both stacks, resets `zoomState` (FR-021).

### Slider interactions and history

- Slider movements do **not** push to history. (Otherwise dragging
  the slider one tick at a time would spam history with dozens of
  entries.) Only brush-to-zoom and Reset push.
- Pan-button presses also do not push history. Pan is a navigation
  refinement, not a "new view."

## Stub tabs (Analysis, Map)

Unchanged from feature 004's contract — clearly-labelled "coming
soon" placeholders. Same heading, same body copy. The React
implementation is a small `<section>` component each.

## Cross-tab requirements (preserved)

- All times rendered to the user are formatted (`mm:ss` /
  `h:mm:ss`); raw millisecond integers do NOT appear.
- All entity labels come from the analysis JSON's pre-attached
  display names; the visualizer does not load `entity_names.json`.
- All entities flagged `unknown: true` render with the raw id and
  a visible marker.
- Loading a new file cleanly replaces the prior render — no
  bleed-through.
- **No network access at runtime** (Principle V (c)): no remote
  fetch, no upload, no telemetry. Verified by SC-006.

## Deployment surface (NEW)

These are user-facing too — the way the visualizer is brought up
changes from "double-click a file" to:

- **Production**: `cd visualizer && docker compose up`, then open
  http://localhost:8080 in a browser.
- **Development**: `cd visualizer && npm install && npm run dev`,
  then open the URL Vite prints (default http://localhost:5173).

Documented in `quickstart.md`.
