# Feature Specification: Visualizer Tabs

**Feature Branch**: `004-visualizer-tabs`
**Created**: 2026-05-01
**Status**: Draft
**Input**: User description: "Introduce tabs to visualizer. The replay info will be split into four tabs. Tab 1 - summary (action totals, group hotkeys, plus aggregated production / heroes / resource transfers — no timelines, no timestamped data). Tab 2 - timelines (top-down per-player layout; global zoom; histogram bars instead of points; bucket size adapts to screen size and zoom; minor events like clicks and selects included). Tab 3 - stub for the future 'analysis' tab (text output ready to be fed to an LLM). Tab 4 - stub for the future 'map' feature (visualization of actions on a map). Note: if the front-end becomes complex enough to switch to React, consider it."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read A Single-Replay Match Report Across Four Tabs (Priority: P1)

A reviewer (player, coach, analyst) opens the visualizer, picks one
analysis JSON, and is dropped into a tabbed match report. The default
tab — **Summary** — shows everything that today's single-page report
shows about the match *except* the per-player timelines and
per-event timestamped lists. Where today's report enumerates
production and heroes event-by-event with times, the Summary tab
collapses those into compact aggregations: "Crypt (×2)", "Carrion
Beetles → Impale (L1) → Impale (L2)", "Sent 500g + 200w to
PlayerName". The reader can see at a glance who built and trained
what, which heroes each player ran with their ability path, what
resources moved between allies, and the match-level facts (header,
chat, observers) without scrolling past dozens of timestamps.

**Why this priority**: This is the new home page of the visualizer.
Without it, the change to tabs is a regression on what feature 003
ships today. With it, every existing reader-of-replays use case
still works, and the page is shorter, scannable, and ready to host
the analytical Tabs 2–4.

**Independent Test**: Open the visualizer, pick
`sample_replays/base_1.w3g.analysis.json`, observe that the page
renders with a tab strip showing four tabs (Summary, Timelines,
Analysis, Map) and that the Summary tab is selected by default.
Confirm that the Summary tab shows the match header, per-team player
panels, action totals, group hotkeys, aggregated production,
aggregated hero progression, aggregated resource transfers, chat,
and observers — and that no per-event time strings appear in the
production / heroes / transfers blocks. Repeat with
`sample_replays/base_2.w3g.analysis.json` and confirm the same
structure with the empty-state behaviors that feature 003 already
defined (no chat, no transfers).

**Acceptance Scenarios**:

1. **Given** an analysis JSON freshly loaded, **When** the report
   first renders, **Then** the page shows a tab strip with exactly
   four tabs in this order — Summary, Timelines, Analysis, Map —
   and the Summary tab is the active one.
2. **Given** the Summary tab is active, **When** the user reads any
   player's production block, **Then** each entity (building, unit,
   upgrade, item) appears once with a count of how many times the
   player produced it (e.g., "Ziggurat (×7)") and **no per-event
   times are shown**.
3. **Given** the Summary tab is active, **When** the user reads any
   player's hero block, **Then** each hero appears as a compact
   line containing the hero's display name, final level, and the
   chronological ability-learn sequence rendered as an arrow chain
   without timestamps (example: "Crypt Lord — Level 4: Carrion
   Beetles → Impale (L1) → Impale (L2) → Spiked Carapace (L1)").
4. **Given** the Summary tab is active for a replay with resource
   transfers (base_1), **When** the user reads any player's
   resource-transfers block, **Then** transfers are aggregated per
   recipient (and per resource type — gold and lumber as separate
   sums) with a total moved and a count of transfers, and **no
   per-event times are shown**.
5. **Given** the Summary tab is active, **When** the user looks for
   a per-player timeline, **Then** none is present on this tab — the
   timeline lives on the Timelines tab.
6. **Given** the Summary tab is active for either committed fixture,
   **When** the user inventories the page contents, **Then** every
   non-timeline section that feature 003's report renders is still
   present: match header, per-team panels with name/race/APM/winner,
   action totals, group hotkeys, chat, observers, including the
   empty-state treatments for chat / transfers / observers when the
   replay had none.
7. **Given** any tab is active, **When** the user clicks another
   tab, **Then** the visible content swaps to that tab without
   re-loading the file, without re-parsing the JSON, and without
   losing any state already established (loaded file, scroll
   position is allowed to reset per tab; current zoom level on the
   Timelines tab is preserved).
8. **Given** an analysis JSON containing entities flagged
   `unknown: true`, **When** any tab renders content referencing
   that entity, **Then** the entity still appears with a visible
   marker and its raw id as the label — feature 003's
   unknown-entity treatment carries forward unchanged.

---

### User Story 2 - Compare Players Across Time On Zoomable Histogram Timelines (Priority: P2)

The reviewer switches to the **Timelines** tab to look at *when*
things happened. Each player gets a full-width row stacked
top-to-bottom (no two-column team layout — every player occupies the
entire usable width). Each row's timeline is a histogram: bars
(buckets) along the match clock that show how many events of each
category fell into that bucket, instead of one mark per event.
Bucket width is chosen so the chart stays readable at the current
viewport width and zoom level — wider bars when zoomed out, finer
bars when zoomed in. The user can zoom in on a portion of the match
clock; **the zoom is global**, so all players' timelines zoom
together and stay aligned, making cross-player comparison ("what
were the others doing while Player 1 hero-rushed?") straightforward.
Minor activity — clicks and unit selections — is also represented,
so quiet stretches and bursts of micro are visible alongside the
bigger build / hero / transfer events.

**Why this priority**: This is the analytical view that justifies
having a separate tab at all. Reviewers currently have one mark per
event per player, which clumps unreadably on long matches and tells
them nothing about activity *density*. Histograms with adjustable
buckets, plus a global zoom, turn the timeline from a chronology
into a comparison tool. It is P2 not P1 because the Summary tab
alone is already a usable replacement for feature 003's report.

**Independent Test**: With the Summary tab working (US1), switch to
the Timelines tab. Confirm: (a) every player from the loaded replay
has a timeline row that occupies the full available width and is
laid out top-to-bottom; (b) each row renders as a histogram with
distinguishable bars per event category, not as one-mark-per-event
points; (c) a zoom control affects all rows simultaneously and they
remain aligned on the match clock; (d) bucket width visibly changes
as zoom changes; (e) hovering a bar surfaces at least the bucket's
time range, the categories included, and the per-category counts;
(f) minor events (clicks / selects) are present alongside major
events (buildings / units / upgrades / items / hero abilities /
resource transfers) — and major and minor categories are visually
distinguishable.

**Acceptance Scenarios**:

1. **Given** the Timelines tab is active, **When** the page renders,
   **Then** every player from the loaded analysis JSON has its own
   timeline row, the rows are stacked top-to-bottom, and each row
   spans the full available content width (no two-up team layout).
2. **Given** the Timelines tab is active, **When** the user looks at
   any player's timeline, **Then** it renders as a histogram (bars
   showing event counts per bucket) rather than discrete point
   markers per event.
3. **Given** the Timelines tab is active, **When** the user invokes
   the zoom control to zoom in, **Then** every player's timeline
   zooms in by the same factor on the same time range, and the
   bucket width recomputes so that bars remain readable (more, narrower
   bars when zoomed in; fewer, wider bars when zoomed out).
4. **Given** a zoomed-in view, **When** the user pans or scrolls
   along the time axis, **Then** all player timelines pan together
   and stay aligned on the match clock.
5. **Given** the Timelines tab is active for a replay where minor
   events (clicks, unit selections) are available in the analysis
   JSON, **When** the user looks at any player's row, **Then** those
   minor events contribute to the histogram and are visually
   distinguishable from the major-event categories (e.g., separate
   color, separate stacked layer, or separate sub-row).
6. **Given** the Timelines tab is active, **When** the user hovers
   or focuses a bar, **Then** the bar reveals at least the bucket's
   start–end time, the per-category event counts within that bucket,
   and the bucket's total event count.
7. **Given** the user reloads a different analysis JSON via the file
   picker, **When** the new replay renders, **Then** the Timelines
   tab refits to the new match's duration and zoom resets to a
   sensible default (full match visible).
8. **Given** a very long match (base_1, ~88 minutes) and a short
   match (base_2, ~16 minutes), **When** each is loaded, **Then**
   both timelines remain legible at the default zoom — bars are
   neither pixel-thin nor wider than the viewport.

---

### User Story 3 - See A Placeholder For The Upcoming Analysis Tab (Priority: P3)

The reviewer clicks the **Analysis** tab. The tab content makes it
clear that an LLM-ready textual analysis of the replay will live
here in a future feature, and that nothing is broken. No partial,
half-implemented analysis is shown.

**Why this priority**: The tab strip needs to show a placeholder so
the user understands that the tab exists and will be filled in. It
is P3 because no current user task depends on it.

**Independent Test**: Load any analysis JSON, switch to the
Analysis tab. The tab content clearly states that the analysis
feature is not yet available, and the visualizer remains in a
healthy state when the user switches back to Summary or Timelines.

**Acceptance Scenarios**:

1. **Given** an analysis JSON loaded, **When** the user switches to
   the Analysis tab, **Then** the tab shows a clearly-labeled
   placeholder explaining that the analysis output is a future
   feature.
2. **Given** the Analysis tab placeholder is visible, **When** the
   user switches to any other tab, **Then** that tab functions
   normally — the placeholder did not corrupt visualizer state.

---

### User Story 4 - See A Placeholder For The Upcoming Map Tab (Priority: P3)

The reviewer clicks the **Map** tab. Same shape as US3: a clear
placeholder explaining that on-map action visualization will live
here in a future feature.

**Why this priority**: Same reasoning as US3 — keeps the tab
strip honest about what is and isn't done.

**Independent Test**: Load any analysis JSON, switch to the Map tab.
The tab content clearly states that the map feature is not yet
available, and the visualizer remains in a healthy state when the
user switches back to Summary or Timelines.

**Acceptance Scenarios**:

1. **Given** an analysis JSON loaded, **When** the user switches to
   the Map tab, **Then** the tab shows a clearly-labeled placeholder
   explaining that the map visualization is a future feature.
2. **Given** the Map tab placeholder is visible, **When** the user
   switches to any other tab, **Then** that tab functions normally.

---

### Edge Cases

- **No replay loaded yet**: the tab strip MAY be hidden, disabled,
  or visible-but-empty — whichever choice, no tab can crash or show
  stale content from a hypothetical prior replay.
- **Re-loading a different file with a non-Summary tab active**:
  the new replay renders correctly; the active tab either stays on
  the same tab or resets to Summary, but it does NOT show
  data leaked from the previous replay.
- **Player with zero production entries**: the Summary tab's
  production block for that player renders as an empty state.
- **Player with zero heroes** (very short matches): the Summary
  tab's hero block renders as an empty state.
- **A replay with no resource transfers** (base_2): the Summary
  tab's transfers block renders as an empty state.
- **Hero ability-learn sequence with the same ability learned
  multiple times** (e.g., Impale L1 → Impale L2): the aggregated
  arrow chain shows each level as a distinct segment, in the order
  learned, not collapsed into a count.
- **Production aggregation collapsing distinct entries**: when the
  same entity is built / trained / researched / bought multiple
  times, the count is the number of completed entries; the
  aggregation does NOT silently drop duplicates.
- **Unknown entities in the Summary aggregations** (`unknown: true`
  flag): the aggregation row appears with the raw id as label and
  the same visible marker treatment feature 003 established.
- **Histogram bucket width at the smallest viewport**: at a
  desktop laptop width (≥1280 CSS px) and full-match zoom, the
  bucket count stays large enough to convey shape but small enough
  that no bar is sub-pixel.
- **Zoom range extremes**: zooming out past full match duration is
  clamped (no infinite empty axis); zooming in past one-second
  buckets is clamped (no aliasing where bars are narrower than a
  pixel).
- **Player who did literally nothing** (observer mistakenly classed
  as player, or AFK): the Timelines tab shows that player's row as
  a flat / empty axis with a clear empty state, not as an absent
  row.

## Requirements *(mandatory)*

### Functional Requirements

#### Tab navigation

- **FR-001**: After a successful analysis-JSON load, the visualizer
  MUST present a tab strip with exactly four tabs, in this order:
  Summary, Timelines, Analysis, Map.
- **FR-002**: The Summary tab MUST be the active tab on first
  render after loading a file.
- **FR-003**: Switching tabs MUST be a client-side, in-page action
  that does not re-read the analysis JSON, does not re-parse it,
  and does not lose the loaded-file state.
- **FR-004**: Switching to a tab that has no inputs from the
  current replay (Analysis stub, Map stub) MUST NOT remove or
  invalidate the data shown on the other tabs.

#### Summary tab

- **FR-005**: The Summary tab MUST display every match-level
  section that feature 003's report displays — match header,
  per-team-grouped player panels with name / color / race / APM /
  winner badge, action totals, group hotkeys, chat, observers,
  including their existing empty-state treatments — with two
  exceptions: it MUST NOT render per-player timelines and it MUST
  NOT render per-event timestamped lists for production, heroes,
  or resource transfers (those are replaced by aggregations).
- **FR-006**: For every player, the Summary tab MUST render a
  production aggregation: each distinct produced entity (building,
  unit, upgrade, item) appears once with a count of completed
  occurrences, in a stable order grouped by category (buildings,
  units, upgrades, items). Display labels MUST come from the
  analysis JSON's pre-attached display names.
- **FR-007**: For every player, the Summary tab MUST render a hero
  aggregation: one entry per hero used, showing the hero's display
  name, the hero's final level, and the chronological ability-learn
  sequence as an arrow chain ("A → B (L1) → A (L2) → ...") with no
  timestamps. Each ability segment carries the ability display name
  and, where the hero learned the same ability multiple times, the
  level reached on that learn.
- **FR-008**: For every player with at least one resource transfer,
  the Summary tab MUST render a transfer aggregation: per recipient
  (and per resource type — gold and lumber as separate aggregations
  for the same recipient), the total amount sent and the number of
  transfers, with no per-event timestamps.
- **FR-009**: Entities flagged `unknown: true` in the analysis JSON
  MUST appear in every Summary aggregation where they would
  otherwise appear, with the raw id as the displayed label and the
  same visible-marker treatment defined by feature 003 (FR-007 of
  feature 003).

#### Timelines tab

- **FR-010**: The Timelines tab MUST lay out every player from the
  loaded replay top-to-bottom, with each player's timeline row
  spanning the full available content width.
- **FR-011**: Each player's timeline MUST be a histogram: bars
  whose height (or stacked-segment thickness) encodes counts of
  events per bucket per category, NOT one mark per event.
- **FR-012**: The Timelines tab MUST provide a zoom control
  (mechanism left to implementation) that lets the user narrow or
  widen the visible time range. The zoom MUST be **global** — a
  single zoom state that applies identically to every player's
  timeline so cross-player comparisons stay aligned.
- **FR-013**: When zoom changes, the histogram bucket width MUST
  recompute so that bars remain readable at the new zoom level —
  finer buckets when zoomed in, coarser when zoomed out — with the
  goal of keeping the visible bucket count within a band that is
  legible on the current viewport (no sub-pixel bars, no
  one-bar-fills-the-screen).
- **FR-014**: When the viewport width changes (window resize), the
  bucket width MUST recompute by the same rule so the chart stays
  legible at the new width.
- **FR-015**: The Timelines tab MUST include "minor" events
  (clicks — including right-clicks, unit selections, group
  hotkey selections, and any other non-build/non-hero per-action
  input the player issued) in each player's histogram, visually
  distinguishable from major events (build orders, hero ability-
  ups, resource transfers). The minor events MUST be available as
  per-event timestamped data on the Visualizer side so the
  histogram can re-bucket freely as the user zooms — there is no
  fixed minimum bucket width imposed by the data source.
- **FR-015a**: The **Parser** layer MUST emit per-event timestamped
  records for minor input actions (at minimum: rightclick, select,
  selecthotkey, basic, ability) for every player, in addition to
  the categories it already exposes. Each record carries the
  player id, the in-game time (millisecond integer), and a
  category identifier. Parser output remains a JSON document on
  disk; the file may grow materially in size for long matches and
  the parser MUST handle a long-match (≥ 60-minute) replay with
  this added data within the same operational envelope as today.
- **FR-015b**: The **Processor** layer MUST consume the new
  per-event minor-action records and surface them in its
  `*.analysis.json` output under each player's record, alongside
  the existing `actions.totals` counters (which remain unchanged)
  and the `actions.apmTimeline` (which remains unchanged). The
  per-event records MUST carry an entity id consistent with the
  rest of the analysis JSON (e.g., raw category id with the same
  `unknown: true` flag treatment if applicable) and a timestamp in
  the same millisecond format as existing timestamped records.
- **FR-015c**: The two committed fixture analysis JSONs
  (`sample_replays/base_1.w3g.analysis.json`,
  `sample_replays/base_2.w3g.analysis.json`) MUST be regeneratable
  by re-running the Parser + Processor against their committed
  `.w3g` inputs to produce JSONs that include the new per-event
  minor-action data, and the Visualizer MUST render histograms
  that draw from that data on the Timelines tab.
- **FR-016**: Hovering or focusing a bar MUST surface at least:
  the bucket's start and end time, the per-category event counts
  within that bucket, and the total event count.
- **FR-017**: Major-event marker behavior already required for
  feature 003's timeline (visible at correct in-game time, name +
  time on hover/focus, unknown-entity marker treatment) MUST
  remain reachable from the Timelines tab — either via the same
  hover/focus reveal as histograms, or via a drill-in interaction.
  The exact mechanism is left to implementation; the user-visible
  guarantee is "I can still find a specific event's name and time
  from the Timelines tab."
- **FR-018**: The zoom level MUST persist across tab switches
  within a single session (switch to Summary, switch back to
  Timelines: zoom and pan position retained). Loading a new file
  resets zoom to a sensible default (full match visible).

#### Analysis and Map stubs

- **FR-019**: The Analysis tab MUST render a clearly-labeled
  placeholder identifying it as a future feature (LLM-ready text
  analysis of the replay) — no broken layout, no error, no fake
  data.
- **FR-020**: The Map tab MUST render a clearly-labeled placeholder
  identifying it as a future feature (on-map action visualization)
  — no broken layout, no error, no fake data.

#### Compatibility

- **FR-021**: The two committed fixture analysis JSONs
  (`sample_replays/base_1.w3g.analysis.json`,
  `sample_replays/base_2.w3g.analysis.json`) MUST both load and
  render to completion across all four tabs.
- **FR-022**: The visualizer MUST continue to honor every
  cross-cutting requirement from feature 003 that is not
  superseded by this spec: file-picker entry (FR-002 of 003),
  client-side-only load with no network access (FR-003, FR-008 of
  003), error handling for malformed/non-analysis files (FR-004
  of 003), human-readable timestamp rendering wherever times still
  appear (FR-010 of 003), unknown-entity rendering (FR-007 of 003),
  desktop layout target (FR-011 of 003), and clean replacement on
  re-load (FR-009 of 003).

### Key Entities

- **Tab**: One of four named views (Summary, Timelines, Analysis,
  Map). Exactly one is active at a time. The active tab determines
  which content region of the page is visible.
- **Aggregation**: A collapsed view of a player's per-event list
  where the time axis is dropped and entries are grouped by
  identity (entity for production, hero+ability for hero
  progression, recipient+resource for transfers) with a count
  and/or summed amount.
- **Histogram bucket**: A fixed-width slice of the match clock used
  on the Timelines tab to count events that fell within it. The
  bucket width is a function of the current zoom level and the
  current viewport width; it is recomputed when either changes.
- **Zoom state**: The currently-visible time range and pan position
  on the Timelines tab. Shared across all players' timelines on
  that tab. Persists across tab switches within a session; resets
  on file reload.
- **Tab placeholder**: The user-facing content shown on a stub tab
  (Analysis, Map) that explains the tab is a future feature
  without showing fake or partial data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reader who used the feature 003 visualizer can
  locate every fact they previously located on the Summary tab —
  match header, per-team panels, action totals, group hotkeys,
  per-player production list, per-player hero list, per-player
  resource transfers, chat, observers — for both committed
  fixtures, without consulting any other tab.
- **SC-002**: Every produced entity that appears in feature 003's
  per-event production list for a given player on a given fixture
  also appears in that player's Summary aggregation, with a count
  equal to the number of feature-003 entries — verified by
  spot-checking at least one player from each committed fixture.
- **SC-003**: For every hero that appears in feature 003's hero
  list for a given player on a given fixture, the same hero
  appears in the Summary tab's hero aggregation with the same
  final level and the same ability sequence in the same order
  (timestamps removed) — verified for at least one hero per
  fixture.
- **SC-004**: Switching from any tab to any other tab takes less
  than 100 ms of perceived UI latency on commodity laptop hardware
  for a freshly-loaded fixture.
- **SC-005**: Adjusting the Timelines tab zoom produces a visible,
  correctly-bucketed re-render in under 100 ms of perceived UI
  latency for a freshly-loaded fixture.
- **SC-006**: Across the full zoom range, on a 1280-CSS-pixel-wide
  viewport, no histogram bar is sub-pixel and no histogram bar is
  wider than 25% of the row's width — a sanity check that bucket
  sizing actually adapts.
- **SC-007**: For both committed fixtures at default zoom on a
  1280-pixel viewport, every player's timeline is laid out top-down
  with the full content width — verified by manual layout review.
- **SC-008**: The Analysis and Map tab placeholders render without
  error for both committed fixtures, and switching back to Summary
  or Timelines after viewing them leaves those tabs in a working
  state — verified by manual review.

## Assumptions

- **Aggregation grouping keys**: Production aggregates by
  (player, entity-id), summing counts and grouped under
  buildings / units / upgrades / items. Hero aggregation aggregates
  by (player, hero-id), preserving the original ability-learn
  order as the visible chain. Transfer aggregation aggregates by
  (player, recipient-player-id, resource-type), summing amounts and
  counting transfers. These are the natural groupings implied by
  the user's example output and the analysis JSON's existing
  structure — no other grouping key is assumed.
- **Hero ability-chain rendering**: The user's example
  ("Carrion Beetles → Impale (L1) → Impale (L2) → Spiked Carapace
  (L1)") is the canonical format. When the same ability is learned
  multiple times, the level reached on that learn appears in
  parentheses; when an ability is learned only once, the level
  parenthesis MAY be omitted.
- **Tab strip placement and styling**: A horizontal tab strip near
  the top of the report (above the per-player content) is the
  default; vertical tabs or other layouts are not required and not
  precluded — readability is the only requirement.
- **Zoom interaction model**: Mouse wheel + modifier, on-axis
  drag-to-zoom, a slider, or buttons are all acceptable. The
  user-facing requirement is "the user can change zoom and the
  change applies globally"; the input mechanism is an
  implementation choice.
- **Tab-state behavior on file reload**: When a user loads a new
  file, the active tab resets to Summary by default. The
  Timelines tab's zoom state resets to "full match visible". Other
  state (scroll within a tab) is also allowed to reset.
- **Stub tab content**: A short headline plus 1–3 lines of
  explanatory text plus (optionally) a link or pointer to where
  progress on that feature can be tracked is sufficient. No
  interactive controls are required on stub tabs.
- **Frontend technology choice is a planning decision, not a spec
  decision**: The user's note "if at this point front-end becomes
  complex enough to switch to React — consider it" is a hint to the
  plan phase. Per Principle V of the project constitution, framework
  adoption requires a documented user-facing requirement that
  static HTML cannot meet AND a recorded plan-document
  justification. This spec captures the user-facing requirements;
  whether vanilla HTML/JS continues to suffice or React is
  introduced is decided in `plan.md` for this feature, not here.
  Either choice MUST satisfy every functional requirement above.
- **Non-regression scope**: Every cross-cutting capability of
  feature 003 (file picker, drag-and-drop in US3 of 003, error
  handling, unknown-entity rendering, desktop target, no network)
  is preserved. This feature's scope is **how** the report is
  organized and what new analytical view is added — not a redo of
  the input/loading layer.
- **Multi-layer scope**: This feature deliberately spans all
  three layers of the pipeline (Parser, Processor, Visualizer)
  because the Timelines tab's minor-event histograms require
  per-event timestamped minor-action data that no current layer
  produces. The Parser change MUST stay within the bounds of
  Principle II (still uses `w3gjs` as the canonical parser; no
  custom binary reader is introduced — `w3gjs` already exposes
  every minor-action category named in FR-015a, so the change is
  a passthrough into the parser's JSON output rather than new
  parsing logic).
- **JSON size growth**: The analysis JSON will grow materially
  for long matches once per-event minor actions are included. The
  performance target from feature 003 (a typical analysis JSON of
  ≤ 20 MB renders within 3 seconds) MUST still hold for the
  Summary tab; the Timelines tab MUST stay interactive (zoom and
  pan responses under 100 ms per SC-005) on a regenerated base_1
  fixture (~88 minutes, 8 players).

## Out of Scope

- **Filling in the Analysis tab content**: the LLM-ready textual
  analysis is a future feature. This feature ships only the
  placeholder.
- **Filling in the Map tab content**: the on-map action
  visualization is a future feature. This feature ships only the
  placeholder.
- **Drilling into individual events on the Timelines tab beyond the
  hover/focus reveal**: an event-detail panel, a per-event modal,
  or per-event navigation between players is not in scope.
- **Mobile / narrow-viewport layouts**: feature 003's
  desktop-first target carries forward unchanged.
- **Server-side rendering, hosting on a domain, sharing-by-URL, or
  any network-backed feature**: out of scope by Principle I/V and
  by feature 003's contract.
- **Persisting tab/zoom state across page reloads**: in-session
  persistence (across tab switches) is required; cross-session
  persistence (`localStorage`) is not.
- **Comparing two replays side by side**: still single-replay only.
- **Re-bucketing minor events server-side**: minor-event records
  are emitted as raw timestamped events by the Parser/Processor
  pipeline (see FR-015a, FR-015b); pre-bucketed minor-event
  histograms in the analysis JSON are deliberately not produced —
  bucketing is a Visualizer-side concern that depends on zoom and
  viewport.
- **Adding new MAJOR-event categories**: this feature does not
  introduce new event categories beyond what feature 002's
  analysis JSON already exposes (production, heroes, transfers)
  plus the minor-input categories listed in FR-015a.
