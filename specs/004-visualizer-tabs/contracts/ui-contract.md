# UI Contract: Visualizer Tabs

User-facing contract for the four-tab visualizer. Mirrors the
spec's FRs in concrete UI terms a manual reviewer can verify
against a freshly-rendered page.

## Page chrome (unchanged from feature 003 unless noted)

- Header with the visualizer title and the loaded file name.
- File picker control, always visible.
- Drag-and-drop overlay (carried forward from feature 003 US3).

## Tab strip

- A horizontal strip rendered immediately below the file-picker
  control, above all per-replay content.
- Exactly four tabs in this order: **Summary**, **Timelines**,
  **Analysis**, **Map**.
- The active tab has a visible affordance (background contrast,
  underline, or equivalent) — keyboard-focusable.
- On first render after loading a file, **Summary** is active.
- Clicking a tab swaps the visible content region without
  re-loading the file.

### Hidden / disabled tab strip when no file is loaded

- Either: the tab strip is hidden until the first file load, or:
  it is visible but each tab is `aria-disabled` and content area
  shows the existing landing state. Implementation MAY pick
  either, provided no tab can crash or render stale content.

## Summary tab

The Summary tab renders, in this top-down order:

1. **Match header** — game version, duration, type, matchup, map,
   winner ("undetermined" when `match.winner === null`).
2. **Per-team grouped player panels**. Each panel:
   - Player display name, color swatch, race (chosen + detected
     if different), final APM, winner badge if on winning team.
   - **Action totals** (all categories from `actions.totals`).
   - **Group hotkeys** (`groupHotkeys`).
   - **Production aggregation** — see below.
   - **Hero aggregation** — see below.
   - **Resource transfer aggregation** — see below; empty state
     when the player has none.
3. **Chat section** — every message with sender, channel, time,
   text. Empty state ("no in-game chat") when none.
4. **Observers section** — every observer name. Empty state when
   none.

**No timeline. No per-event timestamps anywhere in production /
hero / transfer rendering on this tab.**

### Production aggregation contract

Grouped under section headers `Buildings`, `Units`, `Upgrades`,
`Items` (preserving feature 003's section order). Within each
section, one row per distinct produced entity, sorted
alphabetically by display name:

```text
Crypt (×2)
Ziggurat (×7)
Spirit Tower (×1)
```

Display name comes from the analysis JSON's pre-attached label.
Entries flagged `unknown: true` render with the raw id as the
displayed label and a visible marker (italic / badge / icon),
consistent with feature 003's unknown-entity treatment.

### Hero aggregation contract

One row per hero used by the player. Each row reads:

```text
<HeroDisplayName> — Level <finalLevel>: <Ability1> (L1) → <Ability2> (L1) → <Ability1> (L2) → ...
```

Where the arrow chain preserves the order of the analysis JSON's
`heroes[].abilityOrder` array, with each segment showing the
ability's display name and the level reached on that learn. The
final-level number is the `heroes[].level` field. No timestamps
anywhere in this row.

### Resource transfer aggregation contract

One row per `(recipient, resource)` pair, where `resource ∈ {gold,
lumber}`, sorted by total amount descending:

```text
PlayerName: 1500 gold (3 transfers)
PlayerName: 600 lumber (2 transfers)
OtherPlayer: 500 gold (1 transfer)
```

Empty state when the player sent no transfers.

## Timelines tab

The Timelines tab renders:

1. A **zoom control** affordance (slider, buttons, on-axis
   drag-zoom, mouse wheel + modifier — implementation choice; the
   user-visible requirement is that the control exists and is
   discoverable).
2. A **time axis** showing `mm:ss` (or `h:mm:ss` for matches over
   one hour) labels at the snapped bucket boundaries.
3. A **player row** per player, stacked top-to-bottom, each row
   spanning the full available content width. Rows include:
   - The player's display name and color swatch on the left.
   - A horizontally-aligned histogram filling the rest of the
     row's width.
4. The histogram's bars represent buckets of the visible time
   range (start = `zoomState.visibleStartMs`, end =
   `zoomState.visibleEndMs`). Each bar's height (or stacked
   sub-bar layers) encodes the per-category event counts in that
   bucket.
5. Bar visual encoding distinguishes:
   - **Major** events (build orders + hero abilities + resource
     transfers — categories `buildtrain`, `ability`, `item`,
     plus the timestamped major-event sources from
     `production[]`, `heroes[]`, `resourceTransfers[]`).
   - **Minor** events (categories `rightclick`, `select`,
     `selecthotkey`, `basic`, `assigngroup`, `subgroup`, `esc`).
   The two MUST be distinguishable (color, stacked layer, or
   sub-row).
6. Hover or keyboard focus on a bar reveals at least:
   - The bucket's start–end time (formatted same as the axis).
   - Per-category event counts within that bucket.
   - The bucket's total event count.

### Zoom + pan behavior

- A single zoom-and-pan state applies to **all** player rows
  simultaneously (FR-012). Adjusting zoom on one row's affordance
  visibly redraws every row.
- Bucket width recomputes on zoom change (FR-013) and on viewport
  resize (FR-014) per research.md R4.
- Zoom-out clamp: visible range cannot exceed `[0,
  match.duration]`. Zoom-in clamp: bucket width cannot fall below
  ~250 ms (or whatever value keeps bars ≥ 1 px on a 1280-px
  viewport at the chosen `TARGET_BUCKET_PX`).
- Zoom state is preserved when switching to another tab and back
  (FR-018).
- Loading a different file resets zoom to full match (FR-018).

## Analysis tab (stub)

Renders a static placeholder:

```text
Analysis (coming soon)

This tab will host an LLM-ready textual analysis of the loaded
replay — produced by a separate analysis pipeline that is not yet
implemented. Switch back to the Summary or Timelines tab for the
data the visualizer currently surfaces.
```

No interactive controls. No data fields read from the analysis
JSON beyond an optional one-line breadcrumb (e.g., the match id)
to reassure the reader that the right replay is loaded.

## Map tab (stub)

Renders a static placeholder, same shape as the Analysis stub:

```text
Map (coming soon)

This tab will visualize per-player actions on the match map —
also not yet implemented. The map for this match was: <map.path>.
```

## Cross-tab requirements (preserved from feature 003)

- All times rendered to the user are formatted (`mm:ss` or
  `h:mm:ss`); raw millisecond integers do NOT appear.
- All entity labels come from the analysis JSON's pre-attached
  display names; the Visualizer does not load `entity_names.json`.
- All entities flagged `unknown: true` render with the raw id and
  a visible marker — in every tab that surfaces them.
- Loading a new file cleanly replaces the prior render with no
  bleed-through.
- No network access, no remote fetch, no upload, no telemetry.
