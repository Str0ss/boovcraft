# Contract: Map Tab UI Surface

Extends feature 007's UI contract. New invariants UM-1 through UM-12 cover the Map tab.

## UM-1
For every applicable analysis JSON with `team.centroidTimeline` populated, the Map tab MUST render a horizontal time slider (native `<input type="range">`) with `min=0, max=buckets.length-1, step=1`.

## UM-2
For every slider position, the Map tab MUST render an SVG canvas containing one labelled dot per non-AI player whose centroid for the current bucket has `source === "commanded"`. Dots whose centroid is `source === "missing"` MUST NOT be rendered (no placeholder or ghost).

## UM-3
Each rendered dot MUST display two-line label minimum: line 1 = player nickname (resolved from `analysis.players[].name`); line 2 = `<combatFood>f / <combatUnitCount>u`.

## UM-4
The SVG `viewBox` MUST be auto-fit using `computeBounds(timeline, battles)` from `mapHelpers.ts`, with at least 10% padding on each side. Degenerate single-coordinate input MUST yield a sensible default viewport (e.g., 1000×1000 centered) — never `viewBox="0 0 0 0"`.

## UM-5
A text label above the canvas MUST display the current scrub time formatted `mm:ss` using the existing `formatTimeMs` helper.

## UM-6
A second text label MUST display either "in Battle N (mm:ss–mm:ss)" when the current scrub time is inside a battle window, OR "no active battle" otherwise. Computed via `currentBattleLabel(battles, tMs)`.

## UM-7
For every ping in `team.battles[*].pings[*]` whose `timeMs ∈ [currentBucket.tMs - 15000, currentBucket.tMs]`, a small marker MUST appear at the ping's `(x, y)` on the canvas. Outside this window, no ping markers.

## UM-8
When `team.applicable === false`, the Map tab MUST render the same empty-state pattern as the Team tab (using the same `reason` enum copy).

## UM-9
When `team.centroidTimeline` is absent (pre-feature-008 file), the Map tab MUST render an empty-state with copy: "Map tab requires re-analyzing this replay with the post-feature-008 processor."

## UM-10
When `team.applicable === true` AND `team.centroidTimeline` is present AND `buckets.length === 0` (degenerate edge case for zero-duration replay), the Map tab MUST render an empty-state — never a slider with no positions.

## UM-11
File-swap MUST reset `currentBucketIndex` to 0. The previous file's scrub position MUST NOT carry over.

## UM-12
The Map tab MUST NOT use ECharts or any chart-rendering library. Native React JSX + SVG only. (Performance / Princ. VI / consistency with the centroid-only design.)

## Test mapping

| Invariant | Coverage |
|---|---|
| UM-1, UM-2, UM-3 | Manual `quickstart.md` § Map tab |
| UM-4 | Vitest `computeBounds` test + manual visual inspection |
| UM-5, UM-6 | Vitest `currentBattleLabel` test + manual |
| UM-7 | Vitest `pingsInWindow` test + manual |
| UM-8, UM-9, UM-10 | Manual + dedicated empty-state Vitest case |
| UM-11 | Manual file-swap test |
| UM-12 | Code review / `npm ls echarts` shows no MapTab import |
