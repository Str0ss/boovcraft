# UI Contract: Visualizer

**Feature**: 003 Replay Visualizer
**Branch**: `003-replay-visualizer`

## Purpose

This document defines what a rendered match report contains, in user-
visible terms. It is the manual-review checklist for the spec's
Success Criteria SC-003 / SC-004 / SC-005 / SC-006.

It is NOT a CSS spec, not a wireframe spec, and not a pixel-perfect
mockup. Implementers choose visual specifics (palette, spacing,
typography) within the bounds described here.

## Page lifecycle

### Landing state (no replay loaded)

What the user sees on first open and after every error or "no file
selected" interaction:

- A page title identifying the tool ("Boovcraft Replay Visualizer" or
  similar).
- A short plain-English instruction ("Pick a `.analysis.json` produced
  by `processor/analyze.py`, or drag one onto this page.").
- A visible file-picker control (an `<input type="file">` styled or
  with a clearly labelled button).
- (Optional, US3) A drop-target hint or affordance.
- No mock data, no zeroed-out template panels, no skeleton loaders.

### Loading state

After the user picks or drops a file, the page transitions:

- A brief inline status ("Loading…") replaces the landing instruction.
- The picker remains accessible (the user can change their mind).
- On success, the report renders; on failure, the landing state
  returns with an error message above the picker.

### Loaded state

The full match report. See §Match report.

### Error state

On any of the failures enumerated in `input-contract.md`, the
landing state re-displays with a dismissable error message in plain
English. The picker stays focused; the user can retry.

## Loading

- **Picker (FR-002, always present)**: An `<input type="file"
  accept=".json,application/json">`. Listening on `change` reads
  `event.target.files[0]` via `FileReader.readAsText`.
- **Drag-and-drop (US3, optional path)**: The whole document body is
  a drop target. On `dragover` (with a JSON file present), a dashed
  full-viewport overlay appears with a "Drop to load" cue. On `drop`,
  `event.dataTransfer.files[0]` flows into the same load path as the
  picker. On `dragleave` outside the document, the overlay disappears.
- **No URL loader**, no clipboard paste, no remote fetch.

## Match report

The report renders top-to-bottom in this order:

1. **Match header**
2. **Per-team player panels** (each team grouped together, each
   panel rich)
3. **Chat**
4. **Observers**

There is no "Match summary" section beyond the header — the per-team
panel content carries the rest.

### §match-header

A single horizontal block at the top of the report. Required fields:

- Match outcome: `"Team {teamId}"` won, OR `"Undetermined"` if
  `match.winner === null` (FR-005, edge case).
- Game version + build (`v2.00 (build 6072)`).
- Game type / matchup (`4on4 — HHNUvHHOO`).
- Map name (filename; full path on hover via `title` attribute).
- Duration (formatted via `formatTimeMs`: `m:ss` for matches under
  1 hour, `h:mm:ss` for ≥ 1 hour).

Optional, low-prominence (rendered nearby but not as headline):
- Game name, creator, lobby settings (speed, fixedTeams, observerMode,
  etc.). This is one paragraph or one definition list, not a feature
  block.

### §player-panel

One panel per player in `analysis.players[]`, grouped under a team
header. Within each team, panels are emitted in slot order
(ascending `player.id`).

Required panel content:

- **Header line**: name + race label + final APM + winner badge (when
  `player.isWinner`).
- **Team accent**: each panel is visibly tinted with `player.color`
  (e.g., as a left border) so adjacent panels are distinguishable
  without reading names.
- **Race label** (R8):
  - Default: full English race name (`"Human"` / `"Orc"` / `"Undead"` /
    `"Night Elf"` / `"Random"`).
  - When `race === "R"` and `raceDetected !== "R"`: `"Random → Detected"`.
- **Action totals** (compact list of `player.actions.totals`).
- **Group-hotkeys table** (8–10 rows, two columns: assigned, used).
- **Production sub-sections** (Buildings / Units / Upgrades / Items),
  each a chronological list rendered from
  `player.production.<cat>.order`. Each row: `"<timeLabel> — <name>"`
  with the unknown marker if applicable.
- **Heroes section** (FR-005 hero progression bullet): per hero,
  header line `"<name> — Level <N>"` (with unknown marker if
  applicable), followed by ability list rendered from
  `hero.abilityOrder` as `"<timeLabel> — <ability name> (L<ordinal>)"`.
- **Resource transfers**: list rendered from
  `player.resourceTransfers[]` as
  `"<timeLabel> → <recipient>: +<gold> gold, +<lumber> lumber"` when
  both gold and lumber are nonzero (skip the side that is zero).
  Empty-state (R7) when the array is empty.
- **Timeline** (US2 / FR-006): see §timeline.

### §timeline

One SVG per player, embedded inside the player panel in a
"Timeline" sub-section.

Required:

- **Axis**: a horizontal line (or implicit baseline of the SVG
  viewBox) representing match time from `0` to `match.durationMs`,
  with at least four labeled tick marks at evenly-spaced intervals
  in `formatTimeMs(t, durationMs)` form.
- **Five fixed rows** for event categories, top-to-bottom:
  `building`, `unit`, `upgrade`, `item`, `ability`. Empty rows still
  occupy their slot so two players' timelines align vertically.
- **Markers**: every entry in `TimelineView.events` (see
  `data-model.md §TimelineView`) renders as a marker of its
  category's shape, positioned at `(timeMs / durationMs) × axisWidth`.
- **Marker styling**:
  - Filled with `player.color` when `isUnknown === false`.
  - Stroke-only (no fill) in a neutral grey when `isUnknown === true`,
    matching §unknown-marker.
- **Marker tooltip**: every marker has a `<title>` child that
  surfaces on hover and on focus. Text format:
  - Resolved: `"{timeLabel} — {label}"`. Ability events extend this
    to `"{timeLabel} — {ability label} ({hero label} L{ordinal})"`.
  - Unknown: `"{timeLabel} — {rawId} (unknown entity)"`.
- **Keyboard reachability**: every marker has `tabindex="0"`, so
  Tab cycles through them and the focus outline reveals the
  current marker; the `<title>` also surfaces on focus.

Not in v1: cross-player overlay timelines, scrubbable playhead,
zoom/pan, cluster collapse, density indicators, color-by-category.

### §unknown-marker

The visual treatment for any entity reference whose
`unknown === true`:

- **Display label**: rendered in italic.
- **Adjacent badge**: a `[?]` glyph after the label.
- **Tooltip**: a `title` attribute on the containing element with text
  `"Unknown entity id: {rawId}"`.
- **Timeline marker**: stroke-only as described in §timeline.

Applied uniformly wherever the entity appears: hero name, build-order
row, ability-order row, timeline marker, anywhere else the entity is
named.

### §empty-states

Required (R7):

| Section | Empty state copy |
|---|---|
| Chat (whole replay) | "No in-game chat in this replay." |
| Observers | "No observers." |
| Resource transfers (per player) | "No allied resource transfers." |
| Heroes (per player) | "No heroes used." |
| Buildings / Units / Upgrades / Items (per player) | "No <category> recorded." |

Empty states render inside the section they would otherwise fill, in
italic and a muted color.

### §chat

A single chronological list at the bottom of the report (above the
observers section). Per row:

- Sender name.
- Channel label (one of "All" / "Team" / "Observer" / "Private").
- Time label (`formatTimeMs`).
- Message text.

Channel labels are visually distinguishable (e.g., "Team" tinted
green, "Observer" grey, "Private" tinted purple — implementer's
choice). Channels MUST be readable as text, not relying solely on
color.

### §observers

A single line or short list of observer names from
`analysis.observers[]`. Empty-state when length is 0.

## Time formatting

Single helper applied uniformly:

```text
formatTimeMs(ms, totalMs):
  totalSeconds = floor(ms / 1000)
  minutes = floor(totalSeconds / 60)
  seconds = totalSeconds % 60
  if totalMs < 3_600_000 (1 hour):
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  else:
    hours = floor(minutes / 60)
    remMinutes = minutes % 60
    return `${hours}:${remMinutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
```

Raw millisecond values MUST NOT appear anywhere in the user-visible
output (FR-010).

## Player color usage

`player.color` (`#rrggbb`) is used as:

- A left-border accent on the player's panel.
- A fill color on the player's timeline markers.

It is NOT used as the only signal for any required information (race,
team, unknown status, channel). Color is always an accent, never the
sole carrier of meaning.

## Reload / replace behavior (FR-009)

Loading a new analysis JSON after one is already rendered MUST:

1. Clear all rendered DOM nodes belonging to the prior report.
2. Reset all event listeners attached to prior nodes (drop them with
   the nodes; do not accumulate listeners on `document` or `window`
   beyond the global picker / drag handlers, which are bound once).
3. Render the new report from scratch in the same mount points the
   previous one used.

There MUST be no visible bleed-through (no partial old-replay names,
colors, panels, or timeline markers) between the two reports.

## Layout & responsive behavior

- Target viewport: ≥1280 CSS pixels wide. The layout is desktop-first.
- At 1280px, all per-team player panels fit in a 2-column or 4-column
  grid (4-on-4 → 4 columns × 2 rows; 3-on-3 → 3 columns × 2 rows).
- At narrower viewports (≥768px), panels MAY collapse to fewer
  columns. Below 768px, the layout MAY become single-column with
  acceptable horizontal scroll on the timeline. v1 does not optimize
  below 1280px.
- The page MUST remain readable (no overlapping text, no clipped
  buttons) at the target viewport.
