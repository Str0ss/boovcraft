# Phase 1 — Data Model: Replay Visualizer

**Feature**: 003 Replay Visualizer
**Branch**: `003-replay-visualizer`
**Date**: 2026-04-25

## Scope

This document records the **UI-data-model** of the visualizer: the
in-memory shapes the rendering code traverses, derived from the
Processor's analysis JSON. The visualizer is read-only — these are
not persisted entities; they are runtime values.

The canonical input contract is `processor/DATA.md` plus
`specs/002-replay-analyzer/contracts/output-shape.md`. This document
does NOT redefine those; it cites them and describes the additional
UI-side facets (groupings, timeline projections, derived empty states)
the visualizer constructs as it renders.

## Entities

### Loaded analysis (root)

The single in-memory object produced by `JSON.parse(fileText)`. Shape
is exactly the Processor's seven-key root: `match`, `settings`, `map`,
`players[]`, `observers[]`, `chat[]`, `diagnostics`.

After loading, the visualizer does NOT mutate this object. Render
helpers consume it directly.

### TeamGrouping (UI-derived)

A grouping built once at render time:

```text
TeamGrouping = Map<teamId: number, players: PlayerEntity[]>
```

- Built by iterating `analysis.players[]` once and bucketing by
  `player.teamId`.
- Iteration order: ascending `teamId`. Within a team, players appear in
  the order they appear in `analysis.players[]` (i.e. slot order).
- The match header consults this grouping to render team summaries
  next to the matchup string.
- Player panels are emitted team-by-team, with a team header
  (`Team N — winners` / `Team N`) introducing each group.

There is no race-roster or per-team aggregate stat in this grouping —
it is purely a layout aid.

### MatchHeader (UI projection)

Read-only projection of `analysis.match` augmented with derived display
fields:

| Field | Source | Notes |
|---|---|---|
| `versionLabel` | `match.version` + `match.buildNumber` | Rendered as `"v2.00 (build 6072)"`. |
| `durationLabel` | `match.durationMs` formatted via `formatTimeMs` | `m:ss` if `<3_600_000` ms, else `h:mm:ss`. |
| `gameTypeLabel` | `match.gameType` | e.g. `"4on4"`. |
| `matchupLabel` | `match.matchup` | e.g. `"HHNUvHHOO"`. |
| `mapLabel` | `analysis.map.file` (preferred) or `analysis.map.path` | Filename only by default; `title` attr carries full path. |
| `winnerLabel` | `match.winner` | `null` → `"Undetermined"`. Object → `"Team N"`. |

### PlayerPanel (UI projection per player)

Read-only projection of one entry from `analysis.players[]`:

| Field | Source | Notes |
|---|---|---|
| `name`, `color` | `player.name`, `player.color` | Color used as a left-border accent and timeline-marker tint. |
| `raceLabel` | `player.race`, `player.raceDetected` | If `race === "R"` and `raceDetected !== "R"`, label is `"Random → Detected"`; otherwise the race full-name from the inline lookup. |
| `apmLabel` | `player.apm` | Integer; rendered as `"123 APM"`. |
| `winnerBadge` | `player.isWinner` | `true` → render a "winner" badge in the panel header. |
| `groupHotkeysSummary` | `player.groupHotkeys` | A small `0`–`9` table or inline key/value list showing assigned/used counts. |
| `actionTotals` | `player.actions.totals` | Rendered as a compact label list (`buildtrain: 1208`, `ability: 311`, etc.). The APM-timeline buckets are NOT visualized in v1 — they are present in the JSON but the timeline section uses production / hero events instead (see TimelineView). |
| `production` | `player.production` | See ProductionSection. |
| `heroes` | `player.heroes[]` | See HeroSection. |
| `resourceTransfers` | `player.resourceTransfers[]` | See TransferSection. |
| `timeline` | derived from `production` + `heroes[].abilityOrder` | See TimelineView. |

### ProductionSection (UI projection)

Four sub-sections — Buildings, Units, Upgrades, Items — each built
from the matching key under `player.production`:

```text
ProductionRow = {
  label: string,        // entity.name (or entity.id when entity.unknown)
  isUnknown: boolean,   // entity.unknown
  rawId: string,        // entity.id (always present, used in tooltip)
  timeLabel: string,    // formatTimeMs(entity.timeMs, match.durationMs)
}
```

Each sub-section is rendered as a chronological list (the Processor's
`order` array, not the per-id `summary` aggregation). The summary
aggregation is NOT rendered as its own table in v1; this is a
deliberate scope choice — production order is more informative for a
match-report read, and a per-id count table can be added in a later
feature without changing the data contract.

### HeroSection (UI projection)

Per hero in `player.heroes[]`:

```text
HeroBlock = {
  label: string,         // hero.name (or "UNKN" / hero.id when unknown)
  isUnknown: boolean,    // hero.unknown
  rawId: string,         // hero.id
  finalLevel: number,    // hero.level
  abilityOrder: AbilityRow[],
}

AbilityRow = {
  label: string,         // ability.name (or ability.id when unknown)
  isUnknown: boolean,
  rawId: string,
  ordinal: number,       // ability-learn ordinal within this hero (1, 2, 3, ...)
  timeLabel: string,     // formatTimeMs(ability.timeMs, match.durationMs)
}
```

Each hero is rendered as: a header (label + level + unknown marker if
applicable) followed by a chronological ability list. `abilitySummary`
is NOT separately rendered in v1 (the order list already conveys what
was learned and how often, via the ordinal).

### TransferSection (UI projection)

Per `player.resourceTransfers[]` entry:

```text
TransferRow = {
  recipientLabel: string,   // toPlayerName
  goldLabel: string,        // gold integer with thousands separators
  lumberLabel: string,      // lumber integer with thousands separators
  timeLabel: string,        // formatTimeMs(timeMs, match.durationMs)
}
```

Empty array → empty-state ("No allied resource transfers.").

### ChatList (UI projection)

Per `chat[]` entry:

```text
ChatRow = {
  senderLabel: string,      // playerName
  channelLabel: string,     // mode ("All" / "Team" / "Observer" / "Private")
  timeLabel: string,        // formatTimeMs(timeMs, match.durationMs)
  text: string,             // message text, rendered as plain text (NEVER as innerHTML)
}
```

Empty array → empty-state ("No in-game chat in this replay.").

### ObserverList (UI projection)

`analysis.observers[]` is a `string[]`. Rendered as a comma-separated
list, or empty-state ("No observers.") when length is 0.

### TimelineView (UI projection per player)

The single most-derived structure. Built per player at render time:

```text
TimelineEvent = {
  category: "building" | "unit" | "upgrade" | "item" | "ability",
  label: string,            // entity/ability name (or rawId on unknown)
  isUnknown: boolean,
  rawId: string,
  timeMs: number,
  // For ability events only:
  heroLabel?: string,       // owning hero's display label
  abilityOrdinal?: number,  // ability ordinal within the hero
}

TimelineView = {
  durationMs: number,       // = match.durationMs
  events: TimelineEvent[],  // unioned + chronologically sorted
  rowAssignments: Map<category, rowIndex>,  // see "row layout" below
}
```

#### Construction

```text
events := concat(
  player.production.buildings.order  → category="building",
  player.production.units.order      → category="unit",
  player.production.upgrades.order   → category="upgrade",
  player.production.items.order      → category="item",
  flatMap(player.heroes[],
          hero ⇒ hero.abilityOrder    → category="ability",
                                       label=ability.name,
                                       heroLabel=hero.name,
                                       abilityOrdinal=ability.level)
)
sort(events, by ascending timeMs)
```

This union is exactly the spec's "notable actions" set (FR-006,
spec Assumptions §"Timeline event set").

#### Row layout

Markers are placed on five distinct horizontal rows inside the SVG,
top to bottom: `building`, `unit`, `upgrade`, `item`, `ability`. The
per-category row is fixed regardless of which categories the player
actually used, so two players' timelines visually align.

Rows that contain zero markers for a given player are still rendered
(empty), so the row layout is consistent across player panels.

#### Marker position

For an event with `timeMs = t`:
```text
x = (t / durationMs) * (svgWidth - leftMargin - rightMargin) + leftMargin
y = rowOffset[category]
```

#### Marker shape

| Category | Shape |
|---|---|
| `building` | square (`<rect>`) |
| `unit` | circle (`<circle>`) |
| `upgrade` | upward triangle (`<polygon>`) |
| `item` | downward triangle (`<polygon>`) |
| `ability` | star (`<polygon>`, 5-point) |

Filled with the player's color (`player.color`) when known; stroked
only (no fill) with a neutral grey when `isUnknown`.

#### Marker tooltip

Each marker has a `<title>` child. Text:
- Resolved: `"{timeLabel} — {label}"`
  e.g. `"4:32 — Footman"` or `"12:08 — Blizzard (Archmage L2)"` for an
  ability event.
- Unknown: `"{timeLabel} — {rawId} (unknown entity)"`.

The marker is also `tabindex="0"` so keyboard users can focus it; the
`<title>` is what tooltip-presenting browsers surface on focus.

## Identity & lifecycle

- The visualizer holds at most one analysis object at any time.
- Picking or dropping a new file replaces the current object after a
  successful parse + validation pass; on parse or validation failure
  the existing render (if any) is also cleared and the landing state is
  re-shown together with the error message (FR-004, edge case
  "Re-loading a different file").
- There is no "library", no "history", and no concept of a session
  beyond the current page load. Closing the tab discards everything.

## What this layer does NOT model

- **Per-player APM-timeline buckets** (`player.actions.apmTimeline.buckets`).
  Available in the JSON; not rendered in v1. Future feature.
- **Per-id production summary aggregations** (`player.production.<cat>.summary`).
  Not rendered in v1; the chronological order list is more informative
  for match-report reading.
- **Action-count totals** (`player.actions.totals`). Rendered as a
  compact list inside the player panel header, not as a chart.
- **Group-hotkey usage** (`player.groupHotkeys`). Rendered as a small
  table inside the player panel; no derived aggregation.
- **Cross-player overlay timelines**. Per spec Out-of-Scope.
