# Research — Map Tab Centroid Scrubber

## R1. Why D-lite over full D

Full variant D (per-handle positions, expanding ping rings, requestAnimationFrame loop) was ~500-700 LOC with real performance concerns and visual clutter against an empty (no-terrain) canvas. The user-requested centroid + nickname + combat-food annotation gives the same situational-awareness signal without per-unit detail. Dropping per-handle positions removes the need to port Tier-2 PositionState into TypeScript or to virtualize 50+ DOM nodes per render.

## R2. Why pre-compute in Processor instead of TypeScript port

Three options for getting per-time centroids to the browser:
1. Pre-compute in Processor → JSON. ~80 LOC processor + small JSON addition.
2. TypeScript port of Tier-2 PositionState. ~400 LOC duplicate + browser-side perf.
3. Pure-JSON-only — only `team.battles[i].centroids` available. 4 scrub points on `base_2` — useless.

Option 1 wins on every axis: smaller LOC, no duplicated logic (Princ. III risk), JSON contract stays the SSoT, browser becomes pure renderer. Negligible JSON size impact (~100 KB on 88-min match).

## R3. Combat-food definition

WC3 food = supply. "Combat units" = anything that's NOT a worker. Workers are the four canonical race-specific gatherers:
- `hpea` Peasant (Human)
- `opeo` Peon (Orc)
- `uaco` Acolyte (Undead)
- `ewsp` Wisp (Night Elf)

These are excluded because the user's intent is "how big is this player's fighting force" — workers don't fight (well, except in extreme cheese cases — out of scope).

Heroes ARE combat units (they fight). They're produced via `players[].heroes[]` not `production.units.order[]`, but heroes are typically supply-5 each in WC3 ladder. We use `unit_costs.json` to look up hero supply when accumulating. (Note: heroes appear in `production.units.order` only sometimes, depending on w3gjs's behavior — so the cumulative sum naturally captures them when they do.)

Goblin Sappers / Shredders / Zeppelins are tagged combat units (they appear in production.units.order with non-worker ids); they correctly contribute to combat-food.

## R4. Cumulative vs death-aware accounting

Combat-food in v1 is **cumulative** — sum of supply over all combat units the player has ever produced, NOT counting deaths. Reasons:

- Per-handle ownership at kill time is feature 010 territory. Without it, we cannot reliably attribute deaths to specific players.
- Per-side death attribution exists in `team.battles[i].kills[*].victimSide`, but going from "team A lost X supply" to "kir specifically lost Y supply" needs the missing per-handle info.
- Showing cumulative is HONEST and STILL informative — it's "how much fighting force has this player invested." The reviewer can compare two players' cumulative growth curves.
- Documenting the cumulative-only nature in tooltip ("32f cumulative produced") is sufficient transparency.

When feature 010 ships per-handle ownership, this calculation can be upgraded to "currently-alive food" without breaking the JSON contract or the UI.

## R5. Bucket width = 5 seconds

Same as feature 006's battle-window bucket. Reasons:
- Feels responsive when scrubbing (5s slider step is granular enough).
- Aligns with battle detection — when scrubbing into a battle window, the scrubber lands on the same time grid as the battle's start.
- JSON size at 5s is acceptable (~100 KB on 88-min match). 1s would be 5× larger; 15s would feel choppy.

Tunable in code (`BUCKET_WIDTH_MS` constant). If the user later wants finer granularity, change one constant + regenerate.

## R6. Native `<input type="range">` over custom slider

Considered:
- Custom React slider with mouse-drag handling: ~200 LOC, accessibility work, focus management.
- `<input type="range">`: ~5 LOC, accessible by default, keyboard arrows work, screen-reader compatible.

Native wins by every measure that matters in v1. If a future feature needs more visual sophistication (zoom-to-region, multiple cursors, time markers on the track), the slider becomes a candidate for replacement — but not now.

## R7. Auto-fit viewport — why include all coordinate sources

Bounds computed from:
- All centroids in `centroidTimeline.buckets[*].centroids[*].(x, y)` where source is "commanded"
- All `team.battles[i].centroids[*].(x, y)`
- All `team.battles[i].pings[*].(x, y)`

Including ping coordinates ensures pings outside the cluster of player centroids (e.g., minimap signal toward enemy base) don't get clipped by the SVG viewBox. Including battle centroids covers the case where a battle happened at coordinates the timeline-buckets missed (rare but possible due to lookback windowing).

10% padding on each side keeps dots from touching edges and gives room for labels.

## R8. Princ. VI evaluation — degenerate

No new dependencies. Operations:
- Coordinate min/max → `Math.min`, `Math.max`
- SVG rendering → React JSX
- Slider → native HTML input
- Time formatting → existing `formatTimeMs` helper

Considered libraries (and rejected): `recharts`, `visx`, `@nivo/scatterplot`, `react-grid-system`. Each adds 100-300 KB bundle for visualizations a 6-DOM-node SVG handles natively. Princ. VI YAGNI.

## R9. Out-of-scope deferrals

- **Hero-specific iconography** (US2 explicitly skipped): each hero has a distinct portrait but rendering 4-12 different SVG icons per scrub frame across 6 players is a content-pipeline concern (sourcing icons, sizing, alt-text). Future feature.
- **Map terrain background**: feature 010 territory.
- **Play / pause auto-advance**: ~30 LOC trivial extension; left out to keep v1 focused on scrubbing-only. Add if user requests after seeing v1.
- **Trail of past centroids**: ~50 LOC fade-out polyline; left out for v1 simplicity. Same reasoning.
- **Click-from-executive-finding to scrub-to-time**: extends feature 007's evidence-ref dispatcher with a new `kind: "timestamp"` variant. Trivial follow-up if useful.

## R10. Constants tuning protocol

Per feature 006 § R5. The four constants:
- `BUCKET_WIDTH_MS = 5_000` — coarseness of timeline
- `CENTROID_LOOKBACK_MS = 60_000` — same as feature 006
- `WORKER_IDS = {hpea, opeo, uaco, ewsp}` — per R3
- Ping-window for map markers = 15_000 — same as feature 006's response window

If quickstart.md walkthrough on `base_2` reveals any of these need tuning, the constant changes in one place and `quickstart.md` updates in the same PR.
