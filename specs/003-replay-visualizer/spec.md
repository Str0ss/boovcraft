# Feature Specification: Replay Visualizer

**Feature Branch**: `003-replay-visualizer`
**Created**: 2026-04-24
**Status**: Draft
**Input**: User description: "The third and final tool in the pipeline is the visualizer: a static HTML page with vanilla JS and CSS that displays a single replay's analysis JSON as a match-report page. Loaded from disk (double-click `visualizer/index.html`) — no server, no build step, no framework. The user picks which replay to view via an HTML file picker; the page reads the chosen `*.analysis.json` client-side and renders the report. All display content comes from the analysis JSON alone — the visualizer does NOT load the entity-name mapping separately, does NOT re-run any analysis, and does NOT need network access. The report covers match header, per-player panels grouped by team, build orders with display names and times, hero progression with ability-learn sequences, resource transfers, chat, observers. There must be a timeline for each player that covers build orders and other notable actions (buildings, upgrades, hero level-ups, shop purchases). Entities flagged `unknown: true` still render with a visual marker; `match.winner === null` renders as 'undetermined'. Both committed fixtures must render correctly. No automated frontend tests in v1."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Read A Complete Match Report For A Picked Replay (Priority: P1)

A Warcraft III player (or a coach, analyst, commentator, or curious
friend) wants to review what happened in a single replay without
installing anything, without opening a terminal, and without having
the replay file itself — they just have the processor-produced JSON.
They open the visualizer in their browser, pick the analysis JSON,
and immediately see a self-contained match report: who played, on
which team, with which race, how long the game lasted, who won (or
that it was undetermined), and — for every player — what they built
and trained, which heroes they used, how their hero abilities
developed over the match, what items their heroes bought, what
resources they passed to allies, and the in-game chat.

**Why this priority**: This is the entire product from the end user's
perspective. The Parser and Processor layers are developer-facing; the
Visualizer is the only thing a non-developer ever looks at. Without
this story, nothing in the three-layer pipeline has user-visible
value.

**Independent Test**: Double-click the visualizer's entry HTML in a
browser. Use the file picker to choose
`sample_replays/base_1.w3g.analysis.json`. The page renders a readable
match report covering the sections listed above. Repeat with
`sample_replays/base_2.w3g.analysis.json` (shorter 3v3 match with no
chat) and confirm the report still renders cleanly, including the
empty-chat empty state.

**Acceptance Scenarios**:

1. **Given** the visualizer HTML freshly opened in a browser with no
   replay loaded, **When** the page first appears, **Then** the user
   sees a clear "pick a replay" affordance (a file-picker control and
   plain-language instruction) and no stale or mock content.
2. **Given** a file-picker dialog open on a valid analysis JSON,
   **When** the user selects it, **Then** within a couple of seconds
   the page replaces the landing state with a fully-rendered match
   report: a match header, per-player panels grouped by team, and the
   chat/observers sections if applicable.
3. **Given** a rendered report, **When** the user looks at any player
   panel, **Then** they can identify the player's displayed name, the
   team and race, final APM, winner status, the chronological list
   of every building / unit / upgrade / item with a human-readable
   name and an in-game time, the player's heroes with their final
   levels, and each hero's ability-learn order with ability names and
   times.
4. **Given** a rendered report for a match that had chat (base_1),
   **When** the user scrolls to the chat section, **Then** they see
   every message in send order with sender, channel (All / Team /
   Observer / Private), time, and text.
5. **Given** a rendered report for a match that had no chat (base_2),
   **When** the user scrolls to where the chat section would be,
   **Then** they see an explicit empty state ("no in-game chat")
   rather than a missing section or an error.
6. **Given** a rendered report for a match where the analysis JSON
   contains `match.winner === null`, **When** the user looks at the
   match header, **Then** the outcome reads explicitly as
   "undetermined" (or equivalent), not as a guess or a default team.
7. **Given** a rendered report that contains at least one entity
   flagged `unknown: true` (e.g., base_1's sentinel hero entry),
   **When** the user encounters it, **Then** the entry still renders
   using the raw id as a label and is visually marked (italic, badge,
   tooltip, or similar) so a developer can see that the underlying
   mapping has a gap — the report does NOT fail, skip the row, or
   show an error.
8. **Given** a replay with one or more observers listed in the
   analysis JSON, **When** the user looks at the observers section,
   **Then** each observer is listed by name.

---

### User Story 2 - See A Per-Player Timeline Of Notable Actions (Priority: P2)

Given a rendered report, a user wants a visual, time-axis view —
per player — of what happened when: the order in which the player
constructed buildings, trained units, researched upgrades, bought
items, and levelled up hero abilities, laid out against the match
clock. The timeline lets the reader spot timings (early expansion,
late tech, hero-level-6 unlocks) that a pure text list does not
surface at a glance.

**Why this priority**: Timelines are the step that turns this from a
data-dump page into a genuine match-report visualizer. They are not
required to deliver the factual content of the report (US1 already
does that), but without them the visualizer is a textual summary
rather than an analytic tool.

**Independent Test**: Load either committed fixture after US1 ships.
For every player panel, scroll to the timeline. Confirm that (a) the
timeline's horizontal axis covers the match duration end-to-end, (b)
every event the text build order and hero section lists is also
present on the timeline as a marker at its recorded in-game time,
(c) markers are visually distinguishable by event category
(building / unit / upgrade / item / hero-ability), and (d) hovering
or focusing a marker reveals its name and time.

**Acceptance Scenarios**:

1. **Given** a player panel with a fully-rendered report, **When** the
   user looks at the player's timeline, **Then** the axis clearly
   represents the match duration (in minutes or mm:ss) from 0 to the
   game's end time.
2. **Given** a player with buildings, units, upgrades, items, and
   hero ability-ups in the analysis, **When** the timeline renders,
   **Then** each of those events appears as a marker at its recorded
   time, and events of different categories are visually
   distinguishable from one another (colour, shape, row, or label).
3. **Given** a rendered timeline, **When** the user hovers (or
   focuses, for keyboard users) a marker, **Then** the marker reveals
   at least the event's name and time.
4. **Given** two players in the same match with very different
   activity levels (e.g., base_1 player 0 with ~180 timed events vs a
   less active opponent), **When** their timelines render side by
   side on the page, **Then** both are legible without overlapping
   markers becoming an unreadable clump.
5. **Given** a player whose timeline contains an entity flagged
   `unknown: true`, **When** the marker renders, **Then** it still
   appears at the correct time with the raw id as its label and is
   visually marked consistently with US1's unknown-entity treatment.

---

### User Story 3 - Drag-And-Drop An Analysis File Onto The Page (Priority: P3)

A user who already has the analysis JSON in a file-browser window
wants to drop it onto the visualizer tab rather than click through a
picker dialog. It is a quality-of-life alternative to US1's file
picker, not a replacement.

**Why this priority**: It saves one dialog. That is worth something
but nothing in the core product depends on it — US1's file picker
covers 100% of the load paths.

**Independent Test**: After US1 is shipped, drag an analysis JSON
file from the operating system's file manager onto the visualizer
page. The page renders the same report it would have rendered had
the file been picked via the picker.

**Acceptance Scenarios**:

1. **Given** the visualizer open with no replay loaded, **When** the
   user drags a JSON file over the page, **Then** the page shows a
   visible drop-zone cue (e.g., a dashed overlay) so the user knows
   the drop will be accepted.
2. **Given** the user drops a valid analysis JSON onto the page,
   **When** the drop completes, **Then** the page renders the same
   report it would have rendered had the user picked the same file
   via the file picker.
3. **Given** the user drops a file that is not a valid analysis JSON
   (wrong shape, malformed JSON, or a non-JSON file), **When** the
   drop completes, **Then** the page shows a clear, non-technical
   error message and does not enter a broken state — the file-picker
   path remains available.

---

### Edge Cases

- **A file the user picks is not valid JSON**: the page shows a clear
  error ("couldn't read this file as JSON") and stays in the
  pre-load state so the user can try again. No partial render.
- **A file is valid JSON but not a valid analysis document** (wrong
  shape, missing required top-level keys): the page shows a clear
  error identifying that the file does not look like a replay
  analysis, and stays in the pre-load state.
- **An analysis JSON with zero observers**: the observers section
  renders as an empty state, not a missing section.
- **An analysis JSON with zero chat messages** (base_2): the chat
  section renders as an empty state, not a missing section.
- **An analysis JSON with `match.winner === null`** (both committed
  fixtures today): the match header shows "undetermined" rather than
  inferring or defaulting to a team.
- **An analysis JSON with at least one entity flagged
  `unknown: true`** (base_1 has one hero so flagged): the entity
  renders in every section where it appears — player panel header,
  hero list, build-order list, AND timeline — with a visible marker
  and its raw id as the display label. The report renders to
  completion.
- **An analysis JSON with zero resource transfers** (base_2): the
  resource-transfers section renders as an empty state.
- **A player with zero heroes leveled** (possible in very short
  matches): the player's hero section renders as an empty state.
- **A very short match** (base_2: ~16 minutes) and a **very long
  match** (base_1: ~88 minutes): both timelines render legibly
  without axis scaling breaking or markers piling on top of each
  other.
- **A player with a hero entry whose id is the `"UNKN"` sentinel**:
  identical handling to other unknown entities — still renders, still
  marked.
- **Re-loading a different file after a first replay is already
  rendered**: the page replaces the prior report cleanly, without
  bleed-through from the prior replay's data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The visualizer MUST be a single HTML entry point that a
  user can open by double-clicking the file in their operating
  system's file manager; no server, no network connection, and no
  installation step beyond having a modern web browser.
- **FR-002**: The visualizer MUST provide a file-picker control that
  lets the user choose an analysis JSON file from their local
  filesystem. Drag-and-drop onto the page MAY additionally be
  supported (US3) but the file picker is the primary, always-present
  mechanism.
- **FR-003**: The visualizer MUST read the chosen file entirely on the
  client side (no network upload, no backend, no remote fetch) and
  parse it as a JSON document.
- **FR-004**: When the parsed JSON does not conform to the expected
  analysis-document shape, the visualizer MUST display a clear,
  non-technical error message and MUST NOT render a partial, broken,
  or stale report.
- **FR-005**: On a successful load, the visualizer MUST render a
  match report that contains, at minimum, these sections:
  - Match header: game version, duration, game type, matchup, map
    (path or filename), and winner — with `null` rendered explicitly
    as an "undetermined" state.
  - Per-player panels, visibly grouped by team, each showing:
    name, color, race (chosen and detected if different), final APM,
    and a winner badge when the player is on the winning team.
  - For every player, a build order section covering buildings,
    units, upgrades, and items, each entry showing the entity's
    human-readable display name (pre-attached by the Processor) and
    the in-game time at which it occurred.
  - For every player, a hero progression section showing every hero
    used with its final level and the chronological ability-learn
    sequence with ability names and times.
  - For every player, a resource-transfers subsection showing all
    gold/lumber transfers the player sent to allies, with recipient,
    amounts, and time.
  - A chat section listing every chat message in send order, with
    sender, channel, time, and text — rendered as an empty state if
    the replay had no chat.
  - An observers section listing every observer — rendered as an
    empty state if the replay had no observers.
- **FR-006**: For every player, the visualizer MUST render a visual
  timeline whose horizontal axis represents the match duration and
  whose markers represent the union of timestamped events in that
  player's record: buildings, units, upgrades, items, and hero
  ability-ups. Markers of different event categories MUST be visually
  distinguishable from each other, and MUST surface at least the
  event's name and time on user interaction (hover or keyboard
  focus).
- **FR-007**: Any entity that the analysis JSON flags with
  `unknown: true` MUST still be rendered by the visualizer — in every
  section where it appears (player header, hero list, build-order
  list, hero ability-order list, timeline marker) — with its raw id
  as the displayed label and a visible marker distinguishing it from
  resolved entities. The visualizer MUST NOT drop, hide, or fail on
  unknown entities.
- **FR-008**: The visualizer MUST rely only on data present in the
  loaded analysis JSON. It MUST NOT load the entity-name mapping
  separately, MUST NOT make any network request, and MUST NOT
  require access to the original `.w3g` replay file or the Parser's
  output.
- **FR-009**: Loading a new analysis file after a report is already
  rendered MUST cleanly replace the prior report, with no data,
  labels, or state leaking from the previously-loaded replay.
- **FR-010**: In-game timestamps in the analysis JSON (millisecond
  integers) MUST be rendered in a user-friendly form (e.g., `mm:ss`
  or `h:mm:ss`). Raw millisecond values MUST NOT appear in the
  user-visible report.
- **FR-011**: The visualizer MUST be readable on a modern desktop
  browser window at typical laptop screen widths (1280+ CSS pixels).
  A mobile/narrow-viewport layout is NOT required in v1; a desktop
  layout that degrades acceptably on narrower viewports is
  sufficient.
- **FR-012**: The two committed fixture analysis JSONs
  (`sample_replays/base_1.w3g.analysis.json`,
  `sample_replays/base_2.w3g.analysis.json`) MUST both load and
  render to completion with every required section present.

### Key Entities

- **Analysis JSON file**: A single structured data document produced
  by the Processor layer for one replay. The sole input to the
  Visualizer. Shape and field semantics are defined by the Processor
  layer's output contract.
- **Match report**: The full user-facing rendering of an analysis
  JSON — match header, per-player panels with timelines, chat, and
  observers. The deliverable of this feature.
- **Player panel**: A per-player section within the match report
  containing that player's identity, stats, build order, heroes,
  resource transfers, and timeline.
- **Timeline**: A per-player visual axis covering the match duration
  along which every timestamped event in the player's record is
  placed as a marker.
- **Unknown-entity marker**: A visual treatment (icon, badge,
  style) applied to entities flagged `unknown: true` so the reader
  can tell a mapping gap apart from resolved data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with no prior exposure to the project can, from
  receiving a copy of the visualizer and an analysis JSON, open the
  report in under one minute — including double-clicking the HTML,
  picking the file, and reaching a rendered report.
- **SC-002**: Rendering a match report for a typical ladder-length
  replay analysis JSON (≤ 20 MB on disk, up to ~90 minutes of game
  time, up to 8 players) completes and is fully usable within 3
  seconds of the user selecting the file, on commodity laptop
  hardware.
- **SC-003**: For each committed fixture, a reviewer spot-checking
  the rendered report against the analysis JSON can locate any of
  these facts in under 30 seconds per fact: the winner (or
  "undetermined"), a named player's race, a named player's final
  APM, the time of a named hero's first ability learn, the total
  number of chat messages.
- **SC-004**: 100% of required sections listed in FR-005 appear in
  both committed-fixture reports (measured by a manual rendering
  review walkthrough against this spec).
- **SC-005**: Every timestamped event in the analysis JSON for a
  given player also appears as a timeline marker for that same
  player — verified by spot-counting the build-order, hero, and
  upgrade entries against the timeline markers for at least one
  player from each committed fixture.
- **SC-006**: Every entity flagged `unknown: true` in either
  committed fixture's analysis JSON is rendered visibly in the report
  (not dropped) with a distinct visual marker — verified by locating
  base_1's sentinel hero entry in the rendered output.
- **SC-007**: Re-running the visualizer against a freshly-regenerated
  analysis JSON (after `w3gjs` upgrade, mapping refresh, or replay
  re-analysis) requires no visualizer code changes, provided the
  analysis JSON's top-level contract from the Processor layer is
  unchanged.

## Assumptions

- **Processor output is the sole contract**: The visualizer is
  downstream of the Processor layer per the project's three-layer
  separation. The Processor already embeds human-readable display
  names on every entity reference, and the visualizer trusts those
  names verbatim. A change to the Processor's output shape is handled
  in the Processor's feature, not here.
- **No framework / build step in v1**: The constitution's Principle V
  (Incremental Frontend Evolution) requires the visualizer to start
  as static HTML with plain JS. A framework or build system is not
  adopted by this feature. If a concrete future requirement makes
  static HTML materially insufficient, that requirement is captured
  in a later feature and Principle V is amended before the framework
  is introduced.
- **Target browsers are modern evergreen browsers** (last two
  versions of Chrome, Firefox, Safari, Edge on desktop). IE11 and
  other legacy browsers are not a target.
- **Desktop-first layout**: v1 targets laptop / desktop viewports
  (≥1280 CSS pixels wide). A dedicated mobile breakpoint is out of
  scope for v1.
- **English-only display names**: the mapping file the Processor
  uses is English-only (FR-007 of feature 002 / the mapping
  contract), so the visualizer renders English labels throughout.
- **Load target size**: typical analysis JSONs range from under 1 MB
  (short matches) to ~20 MB (long 4v4 matches with tens of thousands
  of production events). The visualizer is sized for that range.
- **Timeline event set**: "notable actions" in the timeline is the
  union of the player's build-order entries (buildings, units,
  upgrades, items — each carries an in-game time) and the player's
  hero ability-order entries (each carries an in-game time). The
  user's illustrative list "buildings, upgrades, hero level-ups,
  shop purchases" is interpreted inclusively to mean this full set.
- **Chat channel styling**: the analysis JSON includes a `mode`
  field per chat message ("All", "Team", "Observer", "Private").
  Visually distinguishing channels by colour or label is a visual
  detail the implementation chooses; the requirement is only that
  the channel is surfaced to the reader.
- **Player color as accent**: each player record includes a `color`
  field (e.g., `#rrggbb`). The visualizer may use that color as a
  visual accent for that player's panel; it is not required to
  match the in-game color swatch exactly.
- **No manual login / privacy concern**: the visualizer runs entirely
  client-side against a file the user already has on their disk. No
  upload, no telemetry, no account.

## Out of Scope

- **Multi-replay comparison, series view, or session history**. The
  visualizer shows one replay at a time.
- **Any form of network access**: no remote JSON fetch, no CDN
  dependency, no analytics, no upload to share, no "open by URL"
  loader. A user offline, in an airplane, or on a disconnected LAN
  can still use the full feature set.
- **A build system, bundler, transpiler, package manager, or any
  framework** (React, Vue, Svelte, Lit, etc.). Principle V.
- **Automated frontend tests** (unit tests, integration tests,
  Playwright, Cypress, visual regression). Testing is a manual
  walkthrough against the two committed fixtures. Principle IV
  pertains to the parsing/analysis layers where correctness is
  invisible; visualizer correctness is eyeball-checked.
- **Rendering replays analyzed by anything other than this
  project's Processor layer**. A fan-made or historical replay JSON
  with a different shape is not a v1 concern.
- **Interactive playback** (scrubbable time cursor, "play forward in
  time" animation). Timelines are static views in v1.
- **Editing or modifying the loaded replay data**. The visualizer is
  strictly read-only.
- **Cross-player overlays on a single shared timeline**. Timelines
  are per-player in v1.
- **Internationalization** of the UI chrome (buttons, labels,
  section titles). English-only in v1.
- **Print stylesheets, dark mode toggles, keyboard shortcuts beyond
  basic tab-ordering, and accessibility beyond "it is keyboard-
  navigable and marker tooltips are focus-reachable"**. Not
  forbidden, but not in-scope for v1 measurement.
