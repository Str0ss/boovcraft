# Implementation Plan: Team Tab Data Drill-Downs

**Branch**: `008-team-tab-drill-downs` | **Date**: 2026-05-08 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/008-team-tab-drill-downs/spec.md`

## Summary

Visualizer-only feature. Surfaces the ~40% of `team.*` JSON content that feature 007 emits but never renders: pings drill-down (US1), focus-fire contributors (US2), kills drill-down (US3), per-player TEI surface (US4), centroids + distance matrix (US5), attributions empty-state (US6), click-to-scroll executive findings (US7). Non-regression check (US8) is the merge gate.

The JSON contract is fixed at feature 007 — no analyzer / parser / data-model changes. Implementation is contained inside `visualizer/src/tabs/TeamTab.tsx` plus expanded helpers in `visualizer/src/data/teamFormat.ts`. No new dependencies.

## Technical Context

**Language/Version**: TypeScript 5.5+ (already in feature 005 / 006), React 18, Vite 5, Vitest 1.x — all already in `visualizer/package.json`. No version changes.

**Primary Dependencies**: None added. `react`, `react-dom`, `echarts` (unused in this feature — Team tab does not render charts), `vitest` for pure-logic tests. Princ. VI gate degenerate.

**Storage**: Browser memory only. New in-memory state surfaces:
- Per-battle expansion booleans (`kills expanded`, `geometry expanded`) — `useState` per `BattleRow` component, NOT lifted to the page-state context (Princ. III — no premature centralization).
- Highlight pulse state (`{targetId, expiresAt}`) — managed inside `TeamTab` via `useState` + `setTimeout`. Lives ~2 seconds.

**Testing**: Vitest pure-logic only — chip classifier, ping side resolver, kills top-N sorter, evidence-ref dispatcher. Visual correctness is manual via `quickstart.md`, mirroring features 003–006. No new component tests; no React Testing Library introduced.

**Target Platform**: Same as feature 007 — modern desktop evergreen browsers, served via `docker compose up` (production) or `npm run dev` (development).

**Project Type**: Visualizer-layer extension. No new project layer.

**Performance Goals**:
- Team-tab paint ≤ **150 ms** (inherits feature 007 SC-006). Measurement: DevTools Performance.
- Click-to-scroll arrival ≤ **500 ms** (US7 SC-007). Smooth-scroll honored.
- Kills top-N sort: O(n log n) over ≤ 60 entries per battle, < 1 ms per battle. Cumulative budget unchanged.

**Constraints**:
- **JSON contract fixed.** No reading new fields, no schema migration. (Princ. I.)
- **No new dependencies.** Reuse React + Vite from feature 005. (Princ. VI.)
- **Single TeamTab.tsx file is allowed to grow.** Splitting into per-component files (Princ. III) waits until two call-sites genuinely demand it. The drill-down code is concrete and concerns one tab.
- **No persistent state.** No `localStorage`. (Feature 005 / 006 stance preserved.)

**Scale/Scope**:
- New TypeScript: ~300–450 LOC across `TeamTab.tsx` + ~80 LOC in `teamFormat.ts`.
- New Vitest: ~8–12 cases for the four pure helpers.
- Existing files touched (additive only): `TeamTab.tsx`, `teamFormat.ts`. No file deletions.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constitution version: **1.1.0**. This feature inherits the Principle V interactive-analytical exception invoked in feature 005 (the visualizer is already a React + Vite SPA). No fresh exception is required.

| Gate | Principle | Status | Evidence |
|---|---|---|---|
| Layer separation | I. Strict Layer Separation | **PASS** | Visualizer changes only. Reads `team.*` per the existing JSON contract. No Processor / Parser edits. (FR-021, FR-023.) |
| Canonical parser | II. w3gjs Is The Canonical Parser | **PASS (N/A)** | Parser untouched. |
| No premature abstractions | III. No Premature Abstractions | **PASS** | New components live inline in `TeamTab.tsx`; no extraction into shared `<DrillDown>` framework, no per-section component file. State stays in `useState` (no Context lift, no reducer). The chip classifier is a single pure function — not a strategy pattern. If a second feature ever needs the same drill-down, refactoring then is cheaper than predicting now. |
| Fixture-based testing | IV. Fixture-Based Testing With Real Replays | **PASS** | New Vitest cases exercise pure helpers against fixtures derived from `base_2.w3g.analysis.json`. No mocked data, no synthetic shapes. |
| Frontend evolution | V. Incremental Frontend Evolution | **PASS** (no fresh exception needed) | The interactive-analytical exception from v1.1.0 was already invoked in feature 005. This feature is additive UI work within that envelope. All three V preserve clauses continue to hold: **(a)** JSON contract unchanged, **(b)** single-command deploy unchanged (`docker compose up` / `npm run dev`), **(c)** zero runtime egress unchanged. |
| Library justification | VI. Prefer Well-Established Tools | **PASS (no new deps)** | Zero new dependencies. The chip classification, sort, and scroll-into-view operations are stdlib JavaScript / DOM. |

**Violations**: none. Complexity Tracking table empty.

## Risks and Mitigation

| Risk | Severity | Mitigation |
|---|---|---|
| TeamTab.tsx grows past readable size | **Medium** | Hard cap ~700 LOC for the file. If exceeded, extract sub-components into `visualizer/src/components/team/` mirroring feature 007's planned-but-skipped layout. Decision deferred to implementation. |
| Click-to-scroll doesn't work for off-screen targets | **Low** | `element.scrollIntoView({behavior: 'smooth', block: 'center'})` is universally supported in modern browsers (V (c) target). Safari's smooth-scroll is well-tested. |
| Kills top-N rendering on 60-element list overflows the budget | **Low** | Sort + slice is O(n log n) on a small fixed N. Cumulative `team.battles[*].kills.length` summed across all battles is < 200 on the largest committed fixture. Negligible. |
| Pre-007 file path regression — drill-downs dereferencing missing `team.*` | **Low** | The empty-state branch from feature 007 returns BEFORE any drill-down rendering. Strict early return. Vitest test covers. |
| Highlight pulse memory leak via lingering `setTimeout` | **Low** | Cleanup via `useEffect` return + `clearTimeout`. Standard React idiom. |
| Expansion state bleeding between files | **Low** | The expansion state is local to each battle row's component; replaced wholesale on file reload because every battle row remounts under a fresh `key` (battle.index). Verified by FR-024 test. |

## Project Structure

### Documentation (this feature)

```text
specs/008-team-tab-drill-downs/
├── spec.md              # done — US1–US8 with FRs and SCs
├── plan.md              # this file
├── research.md          # heuristic decisions + Princ. VI evaluation table (degenerate)
├── tasks.md             # phased task list
├── quickstart.md        # manual review walkthrough on base_2
├── contracts/
│   └── ui-contract.md   # MUST UI invariants — first such contract in the project
└── checklists/
    └── requirements.md  # auto-populated by /speckit.specify (already exists)
```

NOT created (no need):
- `data-model.md` — JSON shape unchanged; pointer to `specs/007-team-cohesion-analysis/data-model.md` is sufficient.
- `contracts/output-shape.md` — JSON contract unchanged; pointer to `specs/007-team-cohesion-analysis/contracts/output-shape.md`.
- `contracts/lookup-tables.md` — no lookup tables.

### Source Code (repository root)

```text
visualizer/                     # EXTENDED
├── src/
│   ├── tabs/
│   │   └── TeamTab.tsx         # extended — adds drill-down components inline
│   └── data/
│       └── teamFormat.ts       # extended — adds chip-class helpers, ping-side resolver, kills sorter, evidence-ref dispatcher
└── tests/
    └── teamFormat.test.ts      # extended — new Vitest cases for new helpers (or split into team-derive.test.ts if growing past comfort)

processor/                      # UNCHANGED
parser/                         # UNCHANGED
sample_replays/                 # UNCHANGED
```

**Structure Decision**: All new code lives in two existing files plus the existing test file. No new files in the source tree. Spec-side artifacts go in the new `specs/007-...` folder per established convention.

Rationale:
- The drill-down code is tightly coupled to TeamTab's existing rendering — splitting into separate component files would force a useless prop-drilling layer between `analysis` (the JSON document) and the leaf renderers.
- Helpers are pure functions; the natural home is `teamFormat.ts` next to existing `formatTei` / `formatPercent` etc.
- If a future feature 010 (per-handle ownership) needs to reuse the chip classifier or evidence-ref dispatcher, that's the moment to extract into a shared module — not before.

## Heuristic and parameter decisions

This feature has fewer "magic constants" than 006. All decisions documented here:

**Kills drill-down — top N = 10.** Picked so a typical battle (60 kills on `base_2` battle 0) shows enough breadth without overflowing one screen. If `quickstart.md` review reveals a different ideal, it's a one-line edit.

**Highlight pulse duration — 2000 ms.** Long enough to be noticed without lingering. Common UX value.

**Smooth-scroll behavior — `behavior: 'smooth', block: 'center'`.** Universal browser support; centering keeps the highlighted target visually anchored.

**Chip group ordering — Responded → Busy → Ignored.** Maps to severity (positive → neutral → negative); aligns with reading order.

## Phase ordering

`tasks.md` will encode three phases:

- **Phase 1 — P1 stories.** US1 (pings), US2 (focus-fire contributors), US8 (non-regression sweep). Smallest viable shipping increment — buys back the most valuable missing data.
- **Phase 2 — P2 stories.** US3 (kills drill-down), US4 (per-player TEI surface).
- **Phase 3 — P3 stories.** US5 (geometry panel), US6 (attributions empty-state), US7 (click-to-scroll).

Each phase ends with green Vitest + manual quickstart spot-check on `base_2`.

## Complexity Tracking

> Filled ONLY if Constitution Check has violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| _(none)_  | _(no violations)_ | _(n/a)_ |
