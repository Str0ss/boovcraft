# Feature Specification: Interactive Timelines (React Migration + Brush-to-Zoom + Event Filter)

**Feature Branch**: `005-react-timelines`
**Created**: 2026-05-03
**Status**: Draft
**Input**: User description: "Visualizer scope: Migrating to React and updating timelines - adding 'brush to zoom' and event filter"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Drag To Zoom Into A Time Range Across All Players (Priority: P1)

A reviewer is on the Timelines tab looking at an 88-minute match. They want to focus on a 3-minute window where a key fight happened. Today's slider zoom is coarse and indirect: they have to estimate the fraction of the match, slide, then pan. Instead, they want to **drag a rectangle directly on a player's chart** — release the mouse, and every player's timeline zooms to exactly that range. This is the same interaction Kibana, Grafana, and observability dashboards use, and it makes finding-and-focusing a 30x faster gesture than slider-and-pan.

**Why this priority**: Brush-to-zoom is the single most-impactful interaction missing from feature 004's Timelines tab. It turns the histogram from "look at it" into "investigate it." Without it, the Timelines tab remains glanceable but not analytical.

**Independent Test**: With the Timelines tab open on a loaded fixture, drag horizontally on any player's chart from time A to time B. On mouse release, every player's timeline re-renders zoomed to `[A, B]`, all rows stay aligned on the match clock, the readout shows the new visible range, and bucket widths recompute to keep bars legible. Verify: a brush from 5:00 to 8:00 on player 0 results in player 1–7's timelines also showing 5:00–8:00.

**Acceptance Scenarios**:

1. **Given** the Timelines tab is active with a fixture loaded, **When** the user presses the mouse button on any player's chart and drags horizontally, **Then** a visible selection rectangle appears that follows the cursor, anchored at the press point.
2. **Given** an active brush selection, **When** the user releases the mouse button, **Then** every player's timeline re-renders zoomed to the selected time range, the readout text updates to show the new visible range, and the zoom slider's position updates to reflect the new zoom level.
3. **Given** an active brush selection, **When** the user presses **Escape** before releasing the mouse, **Then** the selection rectangle disappears and the zoom is unchanged.
4. **Given** the user releases the mouse after a near-zero drag (a click, not a drag), **Then** no zoom change occurs (treated as a click, not a brush — prevents accidental zoom-to-zero).
5. **Given** the user has zoomed in via brush, **When** they zoom back out via the slider or "Reset zoom" button, **Then** every row's brush behavior continues to work — no state gets stuck.
6. **Given** the user has zoomed in via brush, **When** they brush a *new* range inside the already-zoomed view, **Then** the new range becomes the visible window (zoom stack is replaced, not pushed — see US3 for history).
7. **Given** a brush selection that exceeds the current visible range (drag past the chart edge), **When** the user releases, **Then** the selection is clamped to the chart bounds; no error.

---

### User Story 2 - Toggle Event Categories To Cut Through Visual Noise (Priority: P1)

A reviewer looking at a long, busy match wants to see only the major events (build / train, ability, item, transfer) without the constant background of clicks and selects, OR vice versa — only the click density to gauge micro intensity. Today every row stacks all 12 categories at once, which makes the major-event timing harder to read at zoom-out. They want **clickable legend chips** that toggle each category on or off; the histogram and tooltips immediately reflect the filter. The change is global (applies to every player row), persists across tab switches and brush-zoom changes, and resets to "everything visible" when a new file loads.

**Why this priority**: With histograms at any zoom, the minor-event categories dominate counts (a long match can be 80%+ rightclick + select). Without filtering, the major-event peaks get visually swamped. P1 because it directly fixes the same readability problem as US1, just along the category axis instead of the time axis.

**Independent Test**: With the Timelines tab open, click a category chip in the legend (e.g., "Right-click"). Every player's histogram immediately re-renders with rightclick events excluded; tooltips no longer mention rightclick counts; the chip's visual state shows it as "off." Click the same chip again to re-enable it. Toggle multiple categories together. Switch to Summary tab and back — the filter state is preserved.

**Acceptance Scenarios**:

1. **Given** the Timelines tab with all categories enabled, **When** the user clicks a category chip in the legend, **Then** that chip enters an "off" visual state and every player's histogram re-renders without that category contributing to bar heights.
2. **Given** a category is disabled, **When** the user hovers any bar, **Then** the bar's tooltip lists only the enabled-category counts and the total reflects only enabled categories.
3. **Given** the user has disabled some categories, **When** they switch to the Summary tab and back to Timelines, **Then** the filter state is unchanged.
4. **Given** the user has disabled some categories, **When** they brush-zoom to a new range (US1) or use the slider, **Then** the filter state is unchanged.
5. **Given** the user has disabled some categories, **When** they load a different file, **Then** all categories reset to "enabled" along with the zoom reset.
6. **Given** all categories are disabled, **When** the user looks at any player's row, **Then** the histogram shows an empty axis (no bars) without crashing or rendering an error state.
7. **Given** the user wants quick coarse toggles, **When** they look at the legend, **Then** there are also bulk-toggle affordances — at minimum "All major" / "All minor" / "All on" / "All off" — so the user can flip the whole set without clicking 12 chips.

---

### User Story 3 - Step Back To The Previous Zoom Level (Priority: P2)

A reviewer brush-zoomed into a 30-second slice, looked, and now wants to step back to the 3-minute window they were looking at *before* that brush, then back to the full match. They want **zoom history**: a back button (and forward button) to traverse zoom levels they've already visited. Without this, returning to context requires hand-eye estimation of where they were, or hitting "Reset zoom" and re-brushing from full-match.

**Why this priority**: P2 because US1's "Reset zoom" already gives an escape hatch. A back/forward stack is real polish and makes deep investigation comfortable, but the feature ships usefully without it.

**Independent Test**: With brush-to-zoom from US1 working, brush three times in succession to nest deeper and deeper. Click "Back" — view returns to the second brush's range. Click "Back" again — first brush. Click "Forward" — second again. Reset zoom — history clears.

**Acceptance Scenarios**:

1. **Given** the user has performed at least one brush-zoom, **When** they click the "Back" affordance, **Then** the visible range returns to the immediately-prior zoom state and the "Forward" affordance becomes active.
2. **Given** the user has stepped back via "Back," **When** they click "Forward," **Then** the visible range returns to the previously-visited zoom they had just left.
3. **Given** the user has stepped back, **When** they perform a *new* brush-zoom, **Then** the forward history is discarded (standard browser-back semantics).
4. **Given** the user clicks "Reset zoom," **When** the view resets to the full match, **Then** the back/forward history is cleared.
5. **Given** the user has not yet zoomed at all, **When** they look at the controls, **Then** "Back" and "Forward" are present but visibly disabled.

---

### User Story 4 - Every Existing Capability Still Works After The Migration (Priority: P1)

The visualizer is being migrated to a new technology stack (React + chart library, per V's interactive-analytical exception). A returning user expects **every feature delivered by features 003 and 004 to still work** — picking a file, drag-and-drop, the four-tab layout, all Summary aggregations, the `mm:ss` / `h:mm:ss` time formatting, unknown-entity markers, empty states, the per-team grouping, chat and observers sections, the existing zoom slider and pan buttons, tab persistence of zoom state, file-reload reset behavior. They expect the *new* capabilities (US1, US2, US3) to be additions, not replacements.

**Why this priority**: A migration that breaks existing capability is a regression even if the new capability is great. P1 because no other story can be declared shipped if existing functionality regresses.

**Independent Test**: The full feature 003 + 004 quickstart walkthrough (`specs/003-replay-visualizer/quickstart.md` + `specs/004-visualizer-tabs/quickstart.md`) MUST pass on the migrated visualizer against both committed fixtures, with the *additions* of US1's brush-to-zoom and US2's filter exercised on the same path.

**Acceptance Scenarios**:

1. **Given** a migrated visualizer brought up via its documented one-command start, **When** the user picks `sample_replays/base_1.w3g.analysis.json` (or drag-drops it), **Then** the Summary tab renders with every section feature 004's Summary tab rendered (match header, per-team panels, action totals, group hotkeys, aggregated production / heroes / transfers, chat, observers).
2. **Given** the migrated visualizer with base_1 loaded, **When** the user switches to Timelines, **Then** 8 full-width player rows render with histograms covering the same data feature 004 covered (timed-action stream + transfers).
3. **Given** any tab is active, **When** the user clicks another tab, **Then** the visible content swaps without re-loading the file, and zoom + filter state on the Timelines tab is preserved across tab switches (FR-018 of feature 004 + new FR for filter state).
4. **Given** the user picks a different analysis JSON mid-session, **When** the new replay renders, **Then** active tab resets to Summary, zoom resets to full match, and category filters reset to all-enabled — no bleed-through from the prior file.
5. **Given** an analysis JSON containing entities flagged `unknown: true`, **When** any tab renders content referencing them, **Then** the entities still appear with their visible markers (per FR-007 of feature 003 / FR-009 of feature 004).
6. **Given** a malformed or non-analysis file is picked, **When** the load fails, **Then** the existing error-handling path remains: a clear message, no partial render, no broken state.
7. **Given** the visualizer is brought up offline (no network connectivity), **When** the user uses every feature including US1 / US2, **Then** every feature works — no remote requests, no CDN fonts, no telemetry (per Principle V (c) of constitution v1.1.0).

---

### Edge Cases

- **Brush smaller than the minimum bucket width** (~250 ms): clamp the resulting visible range to a sensible minimum so bars don't go sub-pixel; do not zoom past the legibility floor.
- **Brush across the entire visible width** (full chart): treat as a no-op (effectively zooming to current view); do not crash.
- **Brush starts on a tooltip / interactive element** (a bar with hover handler): the brush still wins — pointer-down captures, hover ends. Do not get stuck mid-brush.
- **All categories filtered out**: the chart axis still renders; the bars just show nothing. No "blank screen of failure."
- **Filter state on a category that has zero events for a player**: still applies — the bar (which was already empty) stays empty; no edge case to handle differently.
- **Brush across a re-render** (window resize fires while brush is in progress): brush state survives the re-render, OR is cancelled cleanly — not a half-state where the rectangle is rendered but the next mouse-up does nothing.
- **Rapid repeated brushes** (user is exploring fast): the response stays under the 100 ms perceived-latency target across all 8 player rows on the largest fixture (base_1).
- **Touch / trackpad gestures**: at minimum, mouse drag works. Touch / two-finger gestures are not required in v1 but MUST NOT crash if someone tries (graceful no-op or browser-default behavior).
- **Pre-existing slider zoom interacting with brush**: the slider's bidirectional sync — slider moves on brush, brush respects slider — must not produce feedback loops or jitter.
- **Re-loading a different file mid-brush**: in-progress brush is cancelled cleanly when the file load completes.

## Requirements *(mandatory)*

### Functional Requirements

#### Brush-to-zoom

- **FR-001**: The Timelines tab MUST allow the user to define a time range by pressing the mouse button on any player's chart area, dragging horizontally, and releasing. While dragging, a visible selection rectangle MUST follow the cursor so the user can see what range will be selected.
- **FR-002**: On mouse release after a non-trivial horizontal drag, the visible time range of EVERY player's timeline MUST update to the selected `[startMs, endMs]`. All player rows MUST stay aligned on the same time axis (per FR-012 of feature 004 — global zoom remains global).
- **FR-003**: A drag of less than ~5 pixels horizontally MUST be treated as a click, not a brush — no zoom change.
- **FR-004**: A brush whose resulting visible range would fall below the minimum legible bucket width (~250 ms) MUST be clamped to that minimum centered on the brush midpoint. The system MUST NOT zoom past the legibility floor.
- **FR-005**: Pressing **Escape** during an in-progress brush MUST cancel the selection (rectangle disappears, no zoom change). The user MUST be able to brush again immediately after cancelling.
- **FR-006**: A brush extending past the chart edges MUST be clamped to the current visible bounds, not crash or wrap.
- **FR-007**: After a brush completes, the existing zoom slider's position MUST update to reflect the new zoom level (slider stays in sync). The existing zoom-readout, axis ticks, and bucket-width recomputation (FR-013, FR-014 of feature 004) MUST continue to work.
- **FR-008**: A brush MUST be possible from any player row's chart area, and the result is the same regardless of which row was the source — there is no per-row brush state.

#### Event-category filter

- **FR-009**: The Timelines tab MUST present, in or near the legend, a clickable affordance for each event category (the same set already enumerated in feature 004: `buildtrain`, `ability`, `item`, `removeunit`, `esc`, `transfer`, `rightclick`, `select`, `selecthotkey`, `basic`, `assigngroup`, `subgroup`).
- **FR-010**: Clicking an enabled category's affordance MUST disable that category for ALL players' histograms simultaneously and update tooltips so disabled categories are not counted.
- **FR-011**: Clicking a disabled category's affordance MUST re-enable it. Each affordance MUST have a clear visible state distinguishing "enabled" from "disabled."
- **FR-012**: The Timelines tab MUST provide bulk-toggle affordances for at minimum: "All major on/off" and "All minor on/off" (or equivalent). Clicking a bulk affordance MUST flip every category in the named group atomically.
- **FR-013**: The category-filter state MUST persist across tab switches within a single session — switching to Summary and back leaves the same categories enabled/disabled.
- **FR-014**: The category-filter state MUST persist across brush-zoom changes (US1) and across slider zoom + pan changes — filtering is orthogonal to zoom.
- **FR-015**: Loading a new analysis JSON MUST reset all categories to "enabled" (along with the existing zoom-reset and active-tab reset rules).
- **FR-016**: When all categories are disabled, the chart axis MUST still render. Bars are absent; the empty visible state MUST NOT crash, error, or hide the row.
- **FR-017**: The Summary tab is NOT affected by the category filter — Summary aggregations always reflect the full event set per feature 004's contract. (Out of Scope confirms this; no FR forbids it but no FR requires propagation either.)

#### Zoom history (P2)

- **FR-018**: The Timelines tab MUST provide "Back" and "Forward" affordances that walk the zoom history. "Back" returns to the prior visible range; "Forward" returns from a "Back" press to the range that was just left.
- **FR-019**: Performing a new brush-zoom or moving the slider MUST discard the forward history (standard browser-style semantics).
- **FR-020**: Clicking "Reset zoom" MUST clear the back/forward history.
- **FR-021**: Loading a new analysis JSON MUST clear the back/forward history along with the other reset rules.
- **FR-022**: When no history is available in a direction, the corresponding affordance MUST be visibly disabled.

#### Non-regression (the migration)

- **FR-023**: Every functional requirement of feature 003 (FR-001 through FR-012 of `specs/003-replay-visualizer/spec.md`) MUST continue to hold in the migrated visualizer, except where this spec or feature 004's spec explicitly supersedes it.
- **FR-024**: Every functional requirement of feature 004 (FR-001 through FR-022 of `specs/004-visualizer-tabs/spec.md`) MUST continue to hold in the migrated visualizer.
- **FR-025**: The visualizer's input contract MUST remain `*.analysis.json` documents produced by the existing Processor — no Parser or Processor changes are required for the migrated visualizer to load any previously-rendered fixture (per Principle V (a) of constitution v1.1.0).
- **FR-026**: The visualizer MUST function fully offline once started — no CDN scripts, no remote fonts, no telemetry, no analytics, no remote JSON fetches (per Principle V (c)). Local-only HTTP between the browser and a sibling local container is permitted.
- **FR-027**: The visualizer MUST be deployable via a single command for both production usage and developer iteration, with no manual configuration of paths, ports, or environment beyond documented defaults (per Principle V (b)). Both modes MUST be first-class — neither privileged. The exact commands are decided in the plan.
- **FR-028**: Every external dependency newly introduced by this feature MUST satisfy Principle VI's four "well-established" criteria (active maintenance in past ~12 months, broad adoption, permissive license MIT/BSD/Apache-2.0/ISC, API stability track record), OR carry a documented escape-hatch justification in the feature plan.

### Key Entities

- **Brush selection**: A user-defined `[startMs, endMs]` time range produced by a drag-on-chart gesture. Lives only during the drag; on release it becomes the new global zoom state.
- **Category filter state**: A set of enabled / disabled category flags applied to the Timelines tab's histogram rendering and tooltip counts. Defaults to "all enabled"; persists across tab switches and zoom changes; resets on file load.
- **Zoom history entry**: A snapshot of the visible time range. The history is a stack with a back/forward cursor.
- **Migrated visualizer**: The visualizer layer after this feature ships — a browser-based interactive analytical UI that consumes `*.analysis.json` exactly as before, started via a single command, runs fully offline.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can find and zoom into a 3-minute fight in the 88-minute base_1 match in **fewer than 5 seconds and 2 user actions** (one brush + an optional release-to-confirm). Compared with feature 004's slider-and-pan workflow (typically ≥ 10 seconds and ≥ 5 actions), this is a measurable >2× improvement on the primary investigation gesture.
- **SC-002**: After a brush release, every player's row finishes re-rendering within **100 ms of perceived latency** on commodity laptop hardware on the largest fixture (base_1: 8 players, ~88 min, ~30k events). This is the same SC-005 budget feature 004 set for slider zoom; brush MUST NOT regress it.
- **SC-003**: After a category-filter toggle, every player's row re-renders within the same **100 ms** budget on the same hardware and fixture.
- **SC-004**: 100% of feature 003 and feature 004 functional requirements pass against the migrated visualizer when both committed fixtures are walked through manually — measured by a non-regression checklist that explicitly enumerates each prior FR.
- **SC-005**: The migrated visualizer starts via a single documented command (e.g., `docker compose up`) in **under 30 seconds from a cold image** on commodity laptop hardware. The dev iteration command (e.g., `npm run dev`) yields a hot-reloading dev server in **under 10 seconds**.
- **SC-006**: The migrated visualizer functions with **zero outbound network requests** observable via the browser's network tab once the page has loaded — verified manually by loading the page, exercising every feature, and confirming the network tab shows no entries beyond the local origin (or empty for `file://`).
- **SC-007**: Brush-to-zoom is discoverable without prior instruction: a user encountering the Timelines tab for the first time identifies brush-to-zoom within **30 seconds of looking at the page** — measured by a brief visible affordance (cursor change on hover, a subtle hint line, or a tooltip) that signals "you can drag to select." This is qualitative; the test is "would a reasonably curious user discover it?"
- **SC-008**: The category filter is discoverable: a user can flip categories within **15 seconds of seeing the legend** — measured by the legend chips being visibly clickable (cursor change, hover state) and the bulk-toggle affordances being labelled clearly.

## Assumptions

- **Brush mechanics — horizontal time, not vertical**: The brush is a horizontal time-range selector. Dragging vertically (across players) does NOT filter to those players or do anything other than continue tracking the horizontal component. Per-player filtering, if ever needed, is a separate feature.
- **Brush surface — anywhere on the chart**: The user can start a brush from any player row's chart area; they don't have to start from the time axis. This matches Kibana / Grafana convention.
- **Filter state granularity — per-category, not per-player**: Filtering applies globally across all players. Per-player visibility (hide a player) is out of scope; it is a separate feature.
- **Filter state granularity — Timelines only, not Summary**: The category filter affects histograms and tooltips on the Timelines tab. Summary tab aggregations always reflect the full data set, since the Summary tab's purpose is overview, not interactive exploration. (See FR-017.)
- **Filter UI placement — the legend chips are the toggles**: The existing per-category color-coded legend chips become clickable. No separate "filter panel" UI is required; the legend doubles as the filter control. Bulk-toggle affordances ("All on / off", "Major / Minor") are added near the legend.
- **Zoom state coordination**: The slider, brush, pan buttons, and zoom-history Back/Forward all read from and write to the same single visible-range state. There is no per-control state; coordination is automatic by virtue of the single source of truth.
- **Frontend technology choice**: The plan will record the framework + chart library choice. The constitution v1.1.0 amendment (Principle V (b)) requires a single-command-deploy for both production and development; per Principle VI, every newly-adopted external dependency MUST satisfy the "well-established" criteria. Whether the choice is React + visx, React + ECharts, Svelte + chart-of-choice, or another stack, every functional requirement and success criterion above MUST be met. The spec does not pre-commit a stack.
- **Deployment model**: Per the constitution v1.1.0 amendment (Principle V (b)), production usage and developer iteration are both first-class. The expected shape: production via a containerized one-command bring-up (e.g., `docker compose up`); development via a hot-reloading dev server (e.g., `npm run dev`). The dist artifact's exact shape (single-file HTML, dist folder, container image) is a plan-level decision — only the user-facing one-command property is required by spec.
- **Non-regression target**: Both committed fixtures (`sample_replays/base_1.w3g.analysis.json`, `sample_replays/base_2.w3g.analysis.json`) — already regenerable via the Processor — are the acceptance bar. No new fixtures are required for this feature.
- **Brush input device**: Mouse drag is the primary input. Touch and trackpad gestures are not required to work but MUST NOT crash if attempted (graceful no-op or browser-default).
- **Discoverability without modal hints**: A discreet cursor change on chart hover (and matching color/legend state) is sufficient affordance; the spec does NOT require a tutorial overlay or first-run modal. If the chart library provides built-in interaction hints, those count.

## Out of Scope

- **Per-player filtering** (hide / show individual players on the Timelines tab). Could be a future feature; not part of this one.
- **Per-event-id filtering** (e.g., "show only Crypt builds"). The spec covers per-category filtering only.
- **Filtering applied to the Summary tab.** Summary always shows full aggregations (FR-017). If a future feature needs filterable summary, that's a separate spec.
- **Cross-replay comparison** (still single-replay only).
- **Persisting filter / zoom state across page reloads** (`localStorage` etc.). Cross-session persistence is out of scope; in-session persistence (across tab switches and brushes within one page load) is required.
- **The Analysis tab's actual content** (still a placeholder). The Analysis tab continues to render the placeholder it has today; no LLM integration in this feature.
- **The Map tab's actual content** (still a placeholder).
- **A keyboard-driven brush-zoom UX** (e.g., Shift+arrow keys to define a range). Mouse-drag is the only required input mechanism in v1; keyboard accessibility is a polish concern for a later feature.
- **Mobile / touch-first layouts.** Desktop-first remains, per feature 003 / 004's existing scope.
- **Changes to the Parser or Processor layers.** Per Principle V (a) of constitution v1.1.0, the migration MUST consume `*.analysis.json` exactly as feature 004 produced it.
- **Telemetry, analytics, or usage-tracking of any kind in the running visualizer.** Per Principle V (c) — no runtime network egress.
