# Implementation Plan: Map Tab Centroid Scrubber

**Branch**: `008-map-tab-centroid-scrubber` | **Date**: 2026-05-08 | **Spec**: [spec.md](./spec.md)

## Summary

Hybrid feature — Processor + Visualizer. Processor adds `team.centroidTimeline` (~80 LOC + tests), pre-computing per-slot centroids at fixed 5s intervals plus combat-unit food/count cumulatives. Visualizer adds Map tab (~250 LOC + tests) with native HTML range slider scrubber; per-player labelled dots over auto-fit coordinate canvas; pings + battle indicator at current scrub time. Centroid-only — no per-unit positions, no terrain background.

## Technical Context

**Language/Version**: Python 3.11+ (Processor) and TypeScript 5.5+ (Visualizer). No version changes.

**Primary Dependencies**: None added. Princ. VI degenerate.

**Storage**: Browser memory only on Visualizer side. JSON-on-disk contract on Processor side (Princ. I).

**Testing**: Pytest (Processor) for the timeline computation; Vitest (Visualizer) pure-logic helpers (compute bounds, pings-in-window, battle-label, food formatter). Manual `quickstart.md` walkthrough for visual rendering.

**Target Platform**: Same as feature 007 — modern desktop evergreen browsers; Python 3.11+ for analyzer.

**Project Type**: Hybrid Processor + Visualizer feature, mirrors the structure of feature 006 but smaller in scope.

**Performance Goals**:
- Slider drag → re-render: imperceptible (< 16ms per frame). Achieved by avoiding ECharts; pure SVG with 6-12 DOM nodes per render.
- Map-tab paint ≤ 150ms (inherits from feature 006 SC-006).
- Centroid timeline JSON addition ≤ 150 KB on `base_1` (88-min match). Measured during T010.

**Constraints**:
- **JSON contract additive only.** New `team.centroidTimeline` field; nothing existing changed. (Princ. I; output-shape invariant 37.)
- **No new dependencies.** Pure stdlib + existing React + native SVG.
- **No persistent state.** Scrub time resets on file reload (in-memory `useState` only).

**Scale/Scope**:
- New Processor LOC: ~80 in `team/timeline.py` + ~10 LOC wiring in `team/shape.py`.
- New Pytest cases: 6+ in `processor/tests/test_centroid_timeline.py`.
- New Visualizer LOC: ~250 in `visualizer/src/tabs/MapTab.tsx` + ~50 in `visualizer/src/data/mapHelpers.ts`.
- New Vitest cases: 4+ in `visualizer/tests/mapHelpers.test.ts`.

## Constitution Check

| Gate | Principle | Status | Evidence |
|---|---|---|---|
| I. Strict Layer Separation | **PASS** | New computation in Processor (`team/timeline.py`); Visualizer reads via JSON contract. No cross-layer imports. |
| II. w3gjs Canonical Parser | **PASS (N/A)** | Parser untouched. |
| III. No Premature Abstractions | **PASS** | New module is concrete: one function `compute_centroid_timeline`, one consumer (`shape.py`). No generic "TimeSeriesEmitter" base class. SVG is plain JSX, no chart-rendering library. |
| IV. Fixture-Based Testing | **PASS** | All Pytest cases derived from `base_2.w3g.json`. All Vitest cases derived from `base_2.w3g.analysis.json`. |
| V. Incremental Frontend Evolution | **PASS** (no fresh exception) | React + Vite SPA from feature 005 reused as-is. No new framework, no new chart library. Native HTML5 `<input type="range">` and SVG. The three V preserve clauses continue to hold. |
| VI. Well-Established Tools | **PASS (no new deps)** | All operations are stdlib (Python `math`, TS native types, native SVG). |

**Violations**: none. Complexity Tracking empty.

## Risks and Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| JSON size bloat from per-bucket centroids | **Low** | 5s buckets × 88-min × 6 slots × ~30 bytes per entry ≈ 100 KB. Well under SC-003 cap. Confirmed during T010. |
| Combat-food cumulative ignores deaths, may mislead | **Medium** | UI label includes "cumulative" in tooltip (FR documented). Death-aware accounting is feature 010 territory; documented in research.md as known v1 limitation. |
| Slider drag re-render cost on long matches | **Low** | 6-12 dots per render; SVG nodes are cheap. Worst case 88-min match = 1056 buckets but only ONE bucket renders at a time. No virtualization needed. |
| Pre-008 file path crashes | **Low** | Strict early return when `team.centroidTimeline` is undefined. Vitest case covers. |

## Project Structure

```text
specs/008-map-tab-centroid-scrubber/
├── spec.md
├── plan.md
├── tasks.md
├── research.md
├── contracts/ui-contract.md
└── quickstart.md

processor/
├── team/
│   ├── timeline.py             # NEW — compute_centroid_timeline
│   └── shape.py                # extended — wires in centroidTimeline
└── tests/
    └── test_centroid_timeline.py  # NEW — pytest cases

visualizer/
├── src/
│   ├── types/analysis.ts       # extended — CentroidTimeline types
│   ├── tabs/
│   │   ├── MapStub.tsx         # KEPT for backward-compat fallback (renders empty-state for pre-008 files)
│   │   └── MapTab.tsx          # NEW — scrubber UI
│   ├── data/
│   │   └── mapHelpers.ts       # NEW — pure helpers
│   └── App.tsx                 # extended — route 'map' → MapTab when timeline present, else MapStub
└── tests/
    └── mapHelpers.test.ts      # NEW — Vitest cases
```

**Structure Decision**: Keep both `MapStub.tsx` (existing, lightweight) and `MapTab.tsx` (new, full scrubber). `App.tsx` chooses between them based on whether `team.centroidTimeline` is present. This gives clean fallback for pre-008 files with zero conditional rendering inside the new component.

## Heuristic and parameter decisions

**Bucket width = 5000 ms.** Matches feature 006's battle-window bucket size for consistency. Tunable in code (`BUCKET_WIDTH_MS` constant in `team/timeline.py`).

**Centroid lookback = 60_000 ms.** Inherits from feature 006's `centroids.py::CENTROID_LOOKBACK_MS`. Same value used here for consistency.

**Worker IDs = `{hpea, opeo, uaco, ewsp}`.** Hardcoded set in `team/timeline.py`. The four canonical races' workers. If future content adds another worker race, add to the set.

**Ping window for map markers = 15_000 ms.** Inherits from feature 006's `RESPONSE_WINDOW_MS`. Same constant — same conceptual time-scale.

**Auto-fit padding = 10%.** Standard plotting convention. Avoids dots touching edges.

**Slider step = 1 (one bucket).** No sub-bucket scrubbing. Simple `<input type="range" step="1">`.

## Phase ordering

`tasks.md` will encode three phases:

- **Phase 1 — Processor.** `team/timeline.py` + tests + wiring in `shape.py`. After this phase, regenerated `*.analysis.json` contains `team.centroidTimeline`.
- **Phase 2 — Visualizer types + helpers.** TypeScript types in `analysis.ts`; pure helpers in `mapHelpers.ts`; Vitest cases.
- **Phase 3 — Visualizer Map tab.** `MapTab.tsx` component, wire into `App.tsx` routing. Manual quickstart walkthrough.

Each phase ends with a green test sweep.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_  | _(no violations)_ | _(n/a)_ |
