# Feature Specification: Map Tab Centroid Scrubber

**Feature Branch**: `009-map-tab-centroid-scrubber`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "Map tab v1 — scrubbing time slider that shows where each player's army centroid was at any time, annotated with player nickname + current combat-unit food usage. No map terrain background; centroid-only (not per-unit positions). Pre-computed in processor for O(1) browser-side rendering."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Scrub through the match to see how armies moved (Priority: P1)

A reviewer wants to scrub through time and see where each player's army was at every moment of the match. They expect a horizontal time slider; dragging it shows player centroids on a coordinate map updating in real-time. Each centroid is labelled with the player's nickname and current combat-unit food usage (e.g., "Blayed#2127 — 32 food / 14 units"). They can stop at any time to inspect the situation, then continue.

**Why this priority**: This is the entire feature's core value. Without scrubbing, the rest is decoration.

**Independent Test**: Open Map tab on `base_2.w3g.analysis.json`. Verify a horizontal time slider at the top of the tab. Drag it — at each position, six dots (one per player) reposition on the canvas, each labelled with name and food. At time 4:05 (battle 0 start), the centroids should match the values in `team.battles[0].centroids[]`.

**Acceptance Scenarios**:

1. **Given** Map tab is loaded for `base_2`, **When** user drags the slider, **Then** each player's dot updates its `(x, y)` to the bucket's centroid value AND each dot's label shows player nickname + combat-food count for that bucket.
2. **Given** a player has no commanded handles in the lookback window at time T, **When** the slider lands on that bucket, **Then** the player's dot is hidden (or rendered as a faint outline at last-known position with a "missing" indicator).
3. **Given** the user releases the slider, **When** the page is left untouched for 5 seconds, **Then** the rendered state remains exactly at the released bucket — no auto-advance, no animation.
4. **Given** the slider is at bucket index 0 (t=0), **When** all players are still in their start positions, **Then** centroids are either missing (no commands yet) or pin near their start spots inferred from earliest commands.

---

### User Story 2 — Per-centroid annotation: name + combat-unit food (Priority: P1)

The user explicitly wants each dot to show the player's nickname AND their current combat-unit food usage. Combat units = anything NOT a worker (Peon `opeo`, Peasant `hpea`, Acolyte `uaco`, Wisp `ewsp`). Workers and buildings are excluded from the food count because the user wants to see "how big is this player's fighting force."

**Why this priority**: User explicitly requested this (otherwise we'd just have anonymous dots). The combat-food count differentiates "developing" (low food) from "ready to fight" (high food) players.

**Independent Test**: At any slider position, every visible dot shows two-line label: line 1 = player nickname, line 2 = `Xf / Yu` where X is combat-food and Y is combat-unit count. At end of battle 0 (~10:30) on `base_2`, kir#2613 should show roughly "29f / 10u" (matching cumulative production minus worker units).

**Acceptance Scenarios**:

1. **Given** any visible centroid, **When** user looks at it, **Then** the dot has a label with at minimum `name` and the food/unit annotation.
2. **Given** combat-food is computed cumulatively (workers excluded), **When** comparing two snapshots in time, **Then** combat-food monotonically increases or stays flat (no decreases — death-aware accounting is out of scope for v1).
3. **Given** a worker entry in `production.units.order` (`opeo`, `hpea`, `uaco`, `ewsp`), **When** computing combat food, **Then** the worker is NOT counted toward combat-food OR combat-unit count.
4. **Given** the player has produced zero combat units yet, **When** the dot renders, **Then** the food annotation reads `0f / 0u`.

---

### User Story 3 — Pings and current battle indicator (Priority: P2)

The reviewer wants context for what's happening at the current scrub time. Pings active in the last 15 seconds appear as small markers on the map at their `(x, y)`. If the current time is inside a battle window's `[startMs, endMs]`, a text indicator at the top says "in Battle N (mm:ss–mm:ss)."

**Why this priority**: P2 — improves scrubbing experience but the core dots+labels deliver value alone.

**Independent Test**: Scrub to time 4:30 (inside Battle 0 of `base_2`). Verify (a) text shows "in Battle 0", (b) some ping markers visible from the past 15 seconds, (c) at time 11:00 (between Battle 0 and Battle 1, no battle), the indicator shows "no active battle" and zero ping markers if no pings in last 15s.

**Acceptance Scenarios**:

1. **Given** a ping at time `t_p`, **When** scrub time T is in `[t_p, t_p + 15_000]`, **Then** a small marker appears at `(t_p.x, t_p.y)` on the map. Outside this window, the marker is hidden.
2. **Given** scrub time T is inside `team.battles[i].[startMs, endMs]`, **When** the indicator updates, **Then** the indicator reads "in Battle i (mm:ss–mm:ss)" with the battle's time bounds.
3. **Given** scrub time T is outside any battle window, **When** the indicator updates, **Then** it reads "no active battle" or similar.

---

### User Story 4 — Auto-fitting coordinate viewport (Priority: P2)

The map is shown without terrain background. The viewport MUST auto-fit to the observed coordinates so dots aren't bunched in one corner of an enormous empty canvas. Bounds are computed from min/max of all centroids ever observed AND all ping `(x, y)` AND all battle centroids' coordinates, expanded by 10% padding.

**Why this priority**: Without auto-fit, the abstract coordinate system (-8192 to +8192 typical) makes dots tiny and the scrubber unusable. Essential to the basic UX.

**Independent Test**: On `base_2` (small map), the viewport rectangle reasonably fills the SVG canvas — dots are visible, with margin around the edges. On a larger committed fixture (`base_1`, 4v4), the viewport adjusts and dots remain visible at appropriate scale.

**Acceptance Scenarios**:

1. **Given** the timeline is loaded, **When** the viewport bounds are computed, **Then** they include every centroid coordinate ever observed in the timeline AND every ping coordinate AND every battle centroid.
2. **Given** the bounds, **When** the SVG `viewBox` is computed, **Then** there is at least 10% padding on each side beyond observed coordinates.
3. **Given** all coordinates are degenerate (a single point or zero coordinates), **When** computing bounds, **Then** a sensible default viewport is used (e.g., a 1000×1000 square centered on the point) — no `viewBox="0 0 0 0"` zero-area boxes.

---

### User Story 5 — Existing tabs continue to work (Priority: P1)

Replacing the Map placeholder with a real map tab MUST NOT change behavior of the four other tabs. All feature 003–007 functionality continues to render identically.

**Why this priority**: P1 by definition — non-regression gate.

**Independent Test**: Load `base_2`; verify Summary, Timelines, Team, Analysis tabs still render exactly as feature 008 left them. Click Map tab — see the new scrubber. Tab switches work bidirectionally without state leak.

**Acceptance Scenarios**:

1. **Given** the visualizer is loaded with `base_2`, **When** user opens Summary tab, **Then** the Summary tab content is identical to feature 008's behavior.
2. **Given** a `*.analysis.json` lacks `team.centroidTimeline` (pre-008 file), **When** the user opens the Map tab, **Then** the empty-state copy "Map tab requires a re-analyzed file (regenerate with the post-008 analyzer)" is shown — never a crash.
3. **Given** all existing 65 Vitest cases, **When** test run executes, **Then** all 65 still pass with no edits to existing assertions.

---

### Edge Cases

- **Replay with `team.applicable === false`** (1v1 / FFA / no battles): Map tab renders the same empty-state as Team tab — "Map analysis is not applicable to this replay."
- **Player with zero commanded handles for the entire match** (purely passive observer): their dot is never visible on the map; the player's name still appears in legend with "(no movement data)".
- **Scrub time exactly at bucket boundary**: deterministic — round to nearest bucket index `Math.floor(tMs / bucketWidthMs)`.
- **All players' centroids are `null` for a time window**: canvas renders empty grid; ping markers (if any) still visible; battle indicator if applicable.
- **Multiple pings at the same `(x, y)` within 15s window**: render as a single chip with count badge, not stacked overlapping markers.
- **Combat-food count exceeds 100** (cumulative ignoring deaths): expected — feature explicitly does not subtract deaths per US2 acceptance #2. UI may render "32f cumulative" or similar to make the intent clear.
- **Player's centroid jumps a long distance between two buckets** (e.g., army recall to base): the trail (if rendered, P3 polish) shows the discontinuity as a long line. Acceptable; matches reality.

## Requirements *(mandatory)*

### Functional Requirements

#### Centroid timeline (Processor side)

- **FR-001**: The Processor MUST emit a new field `team.centroidTimeline` of shape `{ bucketWidthMs: number, buckets: [{ tMs: number, centroids: [{ slot, x, y, source, combatFood, combatUnitCount }] }] }`.
- **FR-002**: `bucketWidthMs` MUST be 5000 (5 seconds) in v1. Tunable later via constant; not exposed as a parameter.
- **FR-003**: For every bucket index `i` from 0 to `floor(durationMs / bucketWidthMs)`, a bucket entry MUST exist with `tMs = i * bucketWidthMs`. No gaps.
- **FR-004**: For every non-AI player slot, every bucket MUST contain a centroid record (the slot is included even if `x === null`). The centroid is computed by querying `position_state.centroid_at(slot, max(0, tMs - 60_000), tMs)` (60-second lookback inherited from feature 007).
- **FR-005**: When `centroid_at` returns `None`, the bucket's centroid record has `x === null, y === null, source === "missing"`. Otherwise `x`, `y` are finite numbers and `source === "commanded"`.
- **FR-006**: `combatFood` and `combatUnitCount` MUST be computed as cumulative sums over `players[i].production.units.order[*]` filtered by `timeMs <= bucket.tMs` AND `id NOT IN { hpea, opeo, uaco, ewsp }` (the four worker ids). `combatFood = Σ unit_costs[id].supply`; `combatUnitCount = Σ 1`.
- **FR-007**: When a unit id appears in `production.units.order` but not in `unit_costs.json`, that unit contributes 0 to `combatFood` (best-effort degradation; not a crash). One match-level `diagnostics.cohesionMetricGaps[]` row may surface the gap if any occur — same pattern as existing generosity gap reporting.

#### Map tab UI (Visualizer side)

- **FR-008**: The Visualizer MUST replace the existing `MapStub` placeholder with a `MapTab` component. Tab strip retains 5 tabs in the same order: `Summary | Timelines | Team | Analysis | Map`.
- **FR-009**: When `team.applicable === true` AND `team.centroidTimeline` is populated, the Map tab MUST render: a horizontal time slider, a coordinate-grid SVG canvas, dots for each player at the current bucket's centroids.
- **FR-010**: Each dot MUST be labelled with the player's nickname (resolved from `analysis.players[].name` by slot) AND a two-element annotation `<combatFood>f / <combatUnitCount>u`.
- **FR-011**: When a centroid's `source === "missing"`, that player's dot MUST NOT be rendered for that bucket. The label MAY still appear in a separate legend (out of scope for v1 — keep it simple: if no centroid, no dot).
- **FR-012**: The slider MUST be a native `<input type="range">` element with `min=0, max=buckets.length-1, step=1`. Changes update `currentBucketIndex` state.
- **FR-013**: The SVG canvas viewport MUST be auto-fit to a bounding box computed from all centroid `(x, y)` ever observed in `centroidTimeline`, all `team.battles[i].pings[*].(x, y)`, and all `team.battles[i].centroids[*].(x, y)`. The bounds MUST include 10% padding on each side.
- **FR-014**: Pings active within `[currentBucket.tMs - 15000, currentBucket.tMs]` MUST appear as small markers at their `(x, y)` on the canvas. Outside this window, no ping markers.
- **FR-015**: When `currentBucket.tMs` is inside any `team.battles[i].[startMs, endMs]`, a text indicator above the canvas MUST read "in Battle i (mm:ss–mm:ss)" using the existing `formatTimeMs` helper. Otherwise: "no active battle" or equivalent.
- **FR-016**: The slider's current time MUST be displayed as a separate text label in `mm:ss` format, updating with each scrub.

#### Empty-state and pre-008 fallbacks

- **FR-017**: When `team.applicable === false`, the Map tab MUST show an empty-state matching the Team tab's empty-state pattern (same `reason` enum).
- **FR-018**: When `team.centroidTimeline` is absent (pre-feature-008 `*.analysis.json`), the Map tab MUST show an empty-state with copy: "Map tab requires re-analyzing this replay with the post-feature-008 processor."
- **FR-019**: The empty-state branches MUST short-circuit before any scrubber rendering. No null-deref crashes when timeline is absent.

#### Non-regression

- **FR-020**: All UI invariants from feature 008's `contracts/ui-contract.md` MUST continue to hold. Map tab is additive.
- **FR-021**: All 65 existing Vitest cases MUST continue to pass with no edits to existing assertions.
- **FR-022**: The Processor's analyzer JSON MUST remain a strict superset — every existing field unchanged, only `team.centroidTimeline` added (per feature 007's "additive only" non-regression rule, output-shape contract invariant 37).

### Key Entities

- **CentroidTimeline**: A sequence of fixed-interval buckets. Each bucket carries one centroid record per non-AI slot.
- **CentroidTimelineBucket**: `{ tMs, centroids[] }`. The `centroids` array length equals the player count; entries are in slot-id order for deterministic iteration.
- **TimelineCentroid**: Per-bucket per-slot `{ slot, x, y, source, combatFood, combatUnitCount }`. Extends the per-battle `Centroid` shape from feature 007 with `combatFood` and `combatUnitCount`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer can scrub through the entire base_2 match in **under 5 seconds** by dragging the slider end-to-end. UX is responsive (no UI lag).
- **SC-002**: Every centroid value in `team.centroidTimeline.buckets` exactly matches the value `position_state.centroid_at(slot, max(0, t - 60000), t)` would return — verified by a pytest test against `base_2`.
- **SC-003**: Combat-food calculation passes a fixture-driven test: at `t = 600_000` (10:00) on `base_2`, kir#2613's `combatFood` matches the manually-summed supply over `production.units.order[]` filtered to non-worker entries.
- **SC-004**: Map-tab paint budget ≤ **150 ms** (inherits from feature 007 SC-006). Slider drag re-renders in well under that — pure dot repositioning, no chart redraw.
- **SC-005**: New JSON size impact: the `centroidTimeline` block adds at most **150 KB** to a `*.analysis.json` for the largest committed fixture (`base_1`, 88-min × 12 entries per bucket). Total analysis JSON remains under SC-003 of feature 007 (< 6 MB cap).
- **SC-006**: All 65 baseline Vitest cases plus all 130 baseline pytest cases remain green. New tests add: ≥ 6 pytest (centroid timeline shape + combat-food calc + worker exclusion + bucket monotonic time) + ≥ 4 Vitest (compute bounds, pingsInWindow, currentBattleLabel, food formatter).
- **SC-007**: Pre-008 `*.analysis.json` files load successfully; opening Map tab shows the documented empty-state — no crash.

## Assumptions

- **5-second bucket width is sufficient.** Higher resolution (1s) would 5× the JSON size for marginal UX gain. Coarser (15s) would feel choppy. 5s matches the existing battle-window bucket size from feature 007.
- **Workers identified by 4-char id.** `hpea` (Peasant), `opeo` (Peon), `uaco` (Acolyte), `ewsp` (Wisp). No other worker types in standard ladder; goblin shredder / mercenary builders are NOT workers in this taxonomy. Future races / mods would need extending this list.
- **Combat food is cumulative produced**, not "currently alive." Death-aware accounting requires per-handle owner tracking at kill time (feature 010) and is out of scope. Surface this clearly in UI tooltip if confusion arises.
- **No play/pause control.** The user can drag the slider; there is no auto-advance. Adding play/pause is a follow-up if requested.
- **No trail rendering.** The current dot at the current bucket is shown — no fading historical trail. Adding a trail is a follow-up.
- **No per-handle positions.** Centroid only — explicitly the "centroid scrubber" not "unit scrubber" simplification per the user's choice of D-lite.
- **No map terrain background.** Coordinate grid only.
- **Hero icons not differentiated from non-hero centroid.** All players rendered as same-shape dots, differentiated by color and label. Hero-specific iconography is a polish concern.

## Out of Scope

- Per-handle unit positions (centroid only).
- Map terrain rendering (no PNG overlays in v1).
- Play / pause auto-advance.
- Trail rendering of past centroids.
- Hero-specific iconography or model-aware rendering.
- Death-aware combat-food accounting.
- Click-on-dot to inspect player details.
- Click-from-executive-finding to scrub-to-time (could be added trivially in a follow-up by extending feature 008's `dispatchEvidenceRef` with a new `kind: "timestamp"` variant).
- Mobile / touch-first gestures.
- Persistent scrub state across page reloads.
- Multi-replay overlay / comparison.
