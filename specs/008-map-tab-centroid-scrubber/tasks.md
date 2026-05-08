---
description: "Tasks for feature 008: Map Tab Centroid Scrubber"
---

# Tasks: Map Tab Centroid Scrubber

**Input**: Design from `/specs/008-map-tab-centroid-scrubber/`. Three phases: Processor, Visualizer helpers, Visualizer UI.

## Phase 1: Processor — `team.centroidTimeline`

- [ ] T001 Create `processor/team/timeline.py` with `compute_centroid_timeline(parser_output, ownership, position_state, unit_costs) -> dict`. Constants at top: `BUCKET_WIDTH_MS = 5_000`, `WORKER_IDS = frozenset({"hpea", "opeo", "uaco", "ewsp"})`. Returns the dict shape from spec FR-001.
- [ ] T002 Wire `compute_centroid_timeline` into `processor/team/shape.py::assemble_team_block`. Accept `unit_costs` parameter (already passed); thread through; emit as `team.centroidTimeline` in the populated branch.
- [ ] T003 [P] Pytest `processor/tests/test_centroid_timeline.py::test_bucket_count_and_width` — buckets are contiguous from 0 to `floor(durationMs / 5000)`; `tMs` is monotonic; `bucketWidthMs === 5000`.
- [ ] T004 [P] Pytest `test_centroid_per_player_per_bucket` — every non-AI player has a centroid record in every bucket; missing centroids have `x === None, y === None, source === "missing"`; non-missing have finite x/y and `source === "commanded"`.
- [ ] T005 [P] Pytest `test_combat_food_excludes_workers` — for `base_2`, kir#2613 has `combatFood` that does NOT include any of his Peons. (Construct: at end of match, `combatFood == sum(supply for unit in production.units.order if unit.id != "opeo") within tolerance`.)
- [ ] T006 [P] Pytest `test_combat_food_monotonic` — for any slot, `bucket[i].centroid.combatFood >= bucket[i-1].centroid.combatFood` (cumulative property — no decreases).
- [ ] T007 [P] Pytest `test_centroid_matches_position_state_at` — for a sampled bucket index, the bucket's centroid value equals `position_state.centroid_at(slot, max(0, tMs - 60_000), tMs)` exactly.
- [ ] T008 [P] Pytest `test_no_neutral_in_timeline` — no centroid record has `slot in {12, 15}`.
- [ ] T009 Run full processor pytest suite — 130 baseline + new ≥6 = ≥136 cases all green.
- [ ] T010 Regenerate `sample_replays/base_2.w3g.analysis.json` and verify the file size delta is < 50 KB additional.

## Phase 2: Visualizer types + pure helpers

- [ ] T011 Extend `visualizer/src/types/analysis.ts` — add `CentroidTimeline`, `CentroidTimelineBucket`, `TimelineCentroid` types. Add optional `centroidTimeline?: CentroidTimeline` to the populated `TeamBlock` discriminated union variant.
- [ ] T012 [P] Create `visualizer/src/data/mapHelpers.ts` with pure helpers:
  - `computeBounds(timeline, battles): { minX, maxX, minY, maxY }` — auto-fit over all coordinates with 10% padding.
  - `pingsInWindow(battles, tMs, windowMs): Array<{x, y, fromSlot}>` — pings active in [tMs-windowMs, tMs].
  - `currentBattleLabel(battles, tMs): string | null` — "in Battle N (mm:ss–mm:ss)" or null.
  - `formatCombatFood(food, count): string` — `"32f / 14u"`.
- [ ] T013 [P] `visualizer/tests/mapHelpers.test.ts` — Vitest cases:
  - `computeBounds` covers all coordinates + 10% padding; degenerate single-point input returns sensible default.
  - `pingsInWindow` includes pings exactly at boundaries; excludes outside.
  - `currentBattleLabel` returns null when between battles; correct label inside battle.
  - `formatCombatFood` correct for zero, normal values, large values.
- [ ] T014 Run vitest — 65 baseline + new ≥4 = ≥69 cases all green.

## Phase 3: Visualizer — Map Tab

- [ ] T015 Create `visualizer/src/tabs/MapTab.tsx`:
  - Empty-state for `team.applicable === false` OR `team.centroidTimeline` absent.
  - `useState<number>(0)` for currentBucketIndex; reset on analysis swap.
  - Auto-fit SVG `viewBox` from `computeBounds`.
  - `<input type="range">` slider with `min=0, max=buckets.length-1, step=1`.
  - Time label `mm:ss` updating with slider.
  - Battle indicator using `currentBattleLabel`.
  - Per-player dots: visible only when `centroid.source === "commanded"`; circle + two-line text label (name; combatFood / combatUnitCount).
  - Pings markers from `pingsInWindow(battles, currentBucket.tMs, 15_000)`.
- [ ] T016 Wire `MapTab` into `visualizer/src/App.tsx`. Route `'map'` to `<MapTab analysis={pageState.analysis} />` when `team.centroidTimeline` exists; otherwise fallback to existing `<MapStub />`.
- [ ] T017 Verify on `base_2`: open Map tab, slider works, dots show name + food labels, pings appear in 15s window, battle indicator switches inside/outside battles. (Manual quickstart spot-check.)
- [ ] T018 Verify pre-008 file path: load an old `*.analysis.json` (without `team.centroidTimeline`); Map tab shows the documented empty-state copy.

## Phase 4: Final review

- [ ] T019 Author `quickstart.md` — manual walkthrough on `base_2`. Verify scrubbing, food labels, ping markers, battle indicator, viewport fit, file-swap reset.
- [ ] T020 Run all test suites — pytest ≥136 green, vitest ≥69 green.
- [ ] T021 Update `contracts/ui-contract.md` (extends 007) with new map-tab UI invariants.

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → Phase 3 → Phase 4 strictly sequential (Phase 2 needs the JSON shape from Phase 1; Phase 3 needs helpers from Phase 2).
- Within Phase 1, T003-T008 are file-disjoint (`[P]` parallel).
- Within Phase 2, T012 and T013 are file-disjoint (`[P]` parallel).
- Phase 3 implementation tasks are file-coupled and serialize.
