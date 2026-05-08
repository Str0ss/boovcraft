# Contract: Analyzer Coordinate Extension

This document specifies the additive change feature 006 makes to the
existing analyzer-output contract from feature 002. Together with the
feature-002 documents (`specs/002-replay-analyzer/contracts/output-shape.md`
and `processor/DATA.md`), it defines the post-006 shape of
`*.analysis.json`.

## What changes

Two existing entry shapes gain two new optional fields each.

### `players[].actions.timedActions[]`

**Before (feature 002)**:

```json
{ "timeMs": 12345, "category": "rightclick" }
```

**After (feature 006), when the underlying replay action carried a
position**:

```json
{ "timeMs": 12345, "category": "rightclick", "x": -3120, "y": 4280 }
```

**After (feature 006), when the underlying replay action did NOT carry
a position** (e.g., a hotkey assignment or selection):

```json
{ "timeMs": 12345, "category": "selecthotkey" }
```

— unchanged. The `x`/`y` keys are absent, not null sentinels (FR-003).

### `players[].production.{buildings,units,upgrades,items}.order[]`

**Before**:

```json
{ "id": "halt", "name": "Altar of Kings", "unknown": false, "timeMs": 50100 }
```

**After (feature 006), when the underlying replay action carried a
position** (typically applies to building placements):

```json
{ "id": "halt", "name": "Altar of Kings", "unknown": false, "timeMs": 50100, "x": -2880, "y": 4480 }
```

**After (feature 006), when the underlying replay action did NOT carry
a position** (typically applies to `units`, `upgrades`, and `items`
order entries, which originate from non-position ability codes):

— unchanged from the feature 002 shape.

## What does NOT change

- Every existing field on every existing entry retains its name, type,
  position in the JSON, and value (FR-004 / SC-005).
- The set of top-level keys in `*.analysis.json` is unchanged.
- The set of per-player keys is unchanged.
- The `apmTimeline` shape is unchanged.
- The `totals` shape is unchanged.
- The `diagnostics` block is unchanged. (The events stage's separate
  document gets its own `diagnostics` block; the analyzer's stays as it
  was.)

## Source of coordinates

Coordinates are read from the parser-output's
`events[].commandBlocks[].actions[]` stream as documented in
`parser/DATA.md`, specifically from the `position` field on w3gjs
action ids `0x11`, `0x12`, `0x13`, and `0x14`. See
`research.md §R1` for the full action-id table and the rationale for
keeping only the first position on `0x14` (two-target) actions.

## Units

Coordinate values are w3gjs's raw `position.x` and `position.y`:
signed integers in WC3 map units. The analyzer does not transform
them; downstream consumers (the events stage) absorb the unit choice
through per-replay threshold derivation.

## Backward compatibility

Consumers that ignore `x`/`y` keys (notably feature 005's React
visualizer in its current form) continue to function unchanged
(FR-003). Re-running the analyzer on a fixture that has both a
pre-006 and a post-006 analyzer-output committed lets a reviewer
diff the two and verify byte-additivity.

## Validation

The post-006 analyzer-output is **not** considered valid pre-006 input
for any consumer that strictly schema-validates against the feature
002 shape — a strict validator would reject the new `x`/`y` keys as
unknown. No such validator exists in this project; the visualizer and
tests both consume the JSON loosely. If a future consumer chooses to
strictly validate, it MUST be updated to the post-006 shape in the
same change.
