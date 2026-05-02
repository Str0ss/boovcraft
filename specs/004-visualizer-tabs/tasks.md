---
description: "Tasks for feature 004: Visualizer Tabs"
---

# Tasks: Visualizer Tabs

**Input**: Design documents from `/specs/004-visualizer-tabs/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Automated tests are scoped to the **Processor** layer
only (per Principle IV — fixture-based testing for parsing/analysis
correctness). The **Visualizer** ships without automated tests in
v1, consistent with feature 003's stance and with the constitution
scope of Principle IV. Manual walkthrough per `quickstart.md` is
the visualizer acceptance gate.

**Organization**: Tasks are grouped by user story to enable
independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on
  incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1,
  US2, US3, US4)
- File paths are absolute project-relative paths

## Path Conventions

- **Visualizer**: `visualizer/index.html`, `visualizer/styles.css`,
  `visualizer/visualizer.js`, `visualizer/DATA.md`
- **Processor**: `processor/analyze.py`, `processor/tests/`
- **Parser**: `parser/` — unchanged in this feature
- **Fixtures**: `sample_replays/base_*.w3g.json` (parser output;
  unchanged), `sample_replays/base_*.w3g.analysis.json` (regenerable;
  `.gitignore`d)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm baseline state and prepare working fixtures.
No new dependencies are introduced (Principle V).

- [X] T001 Verify `processor/` pytest baseline passes on `main` before changes by running `pytest` in `processor/` and noting which tests cover `actions.totals` (used as the comparison invariant for the new extractor).
- [X] T002 Regenerate the working analysis-JSON fixtures from committed parser output by running `python processor/analyze.py sample_replays/base_1.w3g.json` and `python processor/analyze.py sample_replays/base_2.w3g.json`; confirm both files materialise locally and are ignored by git.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Restructure the existing visualizer entry point so
tabs can be plugged in. This is the minimum cross-cutting refactor
all four user stories depend on.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T003 Introduce a single `pageState` object inside the visualizer IIFE in `visualizer/visualizer.js` (per `data-model.md` §B), holding `loadedFile`, `analysis`, `activeTab` (default `"summary"`), and `zoomState` (initially `null`). Refactor `loadFile()` to populate `pageState` and call a new `renderActiveTab()` instead of the current monolithic `renderReport()`.
- [X] T004 Add a top-level `<nav>` tab strip element to `visualizer/index.html` immediately below the file-picker header, with four buttons in order — Summary, Timelines, Analysis, Map — each `role="tab"` and `aria-selected` driven by `pageState.activeTab`.
- [X] T005 Implement tab routing in `visualizer/visualizer.js`: a `setActiveTab(name)` function that mutates `pageState.activeTab`, updates the tab-strip aria/active classes, and calls `renderActiveTab()`. `renderActiveTab()` dispatches to `renderSummaryTab` / `renderTimelinesTab` / `renderAnalysisStub` / `renderMapStub` based on `pageState.activeTab`.
- [X] T006 Add tab-strip styling in `visualizer/styles.css` — horizontal layout, active-tab affordance (background + underline), focus ring for keyboard users, hidden-when-no-file-loaded behavior.
- [X] T007 Wire up cleanup-on-reload in `loadFile()` so loading a new analysis JSON resets `pageState.activeTab = "summary"` and `pageState.zoomState = null`, and re-renders cleanly with no bleed-through (FR-009 of feature 003 / FR-022 of feature 004).

**Checkpoint**: Tab strip is visible after loading a fixture; the four tabs are clickable; switching tabs swaps a placeholder content area without errors. No tab content is yet implemented — that is each user story's work below.

---

## Phase 3: User Story 1 - Read A Single-Replay Match Report Across Four Tabs (Priority: P1) 🎯 MVP

**Goal**: Deliver the new home tab — Summary — as the default view, preserving every match-level section feature 003 produced (header, per-team panels, action totals, group hotkeys, chat, observers, empty-state behavior, unknown-entity rendering) but replacing the per-event production / hero / resource-transfer lists with compact aggregations. After this story ships, the visualizer is a strict superset of feature 003 minus the per-player timeline (which moves to US2's tab).

**Independent Test**: With Phase 2 complete, load `sample_replays/base_1.w3g.analysis.json`. The Summary tab is active and shows the match header, per-team-grouped player panels, action totals, group hotkeys, aggregated production / heroes / transfers (no timestamps in those three sections), chat, and observers. Repeat with `base_2.w3g.analysis.json` — empty-state treatments render. Switch to Timelines / Analysis / Map: each shows a minimal placeholder, none crash. (Aggregation rendering rules per `contracts/ui-contract.md` §"Summary tab".)

### Implementation for User Story 1

- [X] T008 [P] [US1] Implement `aggregateProduction(player)` in `visualizer/visualizer.js` — group `player.production[]` by `(category, entityId)`, sum counts, return `{ buildings: [...], units: [...], upgrades: [...], items: [...] }` each pre-sorted alphabetically by display name. Preserves `unknown: true` flag per-entry for the renderer.
- [X] T009 [P] [US1] Implement `aggregateHeroes(player)` in `visualizer/visualizer.js` — produce one entry per hero with `displayName`, `finalLevel`, and a chain `[{ abilityName, level, unknown }]` mirroring `heroes[].abilityOrder` order. Per research.md R5, level parens render on every learn for visual consistency.
- [X] T010 [P] [US1] Implement `aggregateTransfers(player)` in `visualizer/visualizer.js` — group `player.resourceTransfers[]` by `(toPlayerId, resource ∈ {gold, lumber})`, sum amounts, count transfers, sort by total amount descending. Return `[{ recipientName, resource, total, count }]`.
- [X] T011 [US1] Implement `renderProductionAggregation(player)` in `visualizer/visualizer.js` — consumes `aggregateProduction(player)`; renders four section blocks (Buildings, Units, Upgrades, Items) each with rows of the form `Name (×N)`. Reuses the existing `entityLabelEl(entity, ...)` helper for unknown-entity marker treatment. Empty-state text per section.
- [X] T012 [US1] Implement `renderHeroAggregation(player)` in `visualizer/visualizer.js` — consumes `aggregateHeroes(player)`; renders one row per hero shaped as `<HeroName> — Level <N>: A1 (L1) → A2 (L1) → A1 (L2) → ...`. Empty-state text when the player has no heroes.
- [X] T013 [US1] Implement `renderTransferAggregation(player)` in `visualizer/visualizer.js` — consumes `aggregateTransfers(player)`; renders rows of the form `<Recipient>: <amount> <resource> (<count> transfers)`. Empty-state text when the player has none.
- [X] T014 [US1] Implement `renderSummaryTab()` in `visualizer/visualizer.js` — replaces the prior monolithic `renderReport`'s body for non-timeline content. Pipeline: match header → teams (each team's panels stacked, each panel calling `renderActionTotals`, `renderGroupHotkeys`, `renderProductionAggregation`, `renderHeroAggregation`, `renderTransferAggregation`) → chat → observers. The existing `renderTimeline(player, ...)` is **not** called from this path.
- [X] T015 [US1] Replace the existing `renderProductionSection`, `renderHeroSection`, `renderTransferSection` calls in the legacy code path with the new aggregation renderers, and remove dead per-event-list code paths from `visualizer/visualizer.js`. Preserve `renderTimeline` for US2's reuse.
- [X] T016 [P] [US1] Add Summary-tab styles in `visualizer/styles.css` — production aggregation section headers (Buildings/Units/Upgrades/Items), hero aggregation arrow chain typography, transfer aggregation rows, empty-state styling. Reuse existing player-panel layout where possible.
- [X] T017 [US1] Add minimal placeholder renderers `renderAnalysisStub()` and `renderMapStub()` to `visualizer/visualizer.js` — single `<section>` each with a heading "Coming soon" so the tab strip never lands on empty content during US1 testing. (US3/US4 polish these.)
- [X] T018 [US1] Manually walk `quickstart.md` §3 "Smoke test against base_1" Summary-tab checks and §4 base_2 Summary-tab checks. Capture any discrepancies and fix before declaring US1 complete.

**Checkpoint**: Loading either committed fixture renders a complete Summary tab with all aggregations correct; clicking Timelines / Analysis / Map shows a placeholder section without errors. The visualizer is a working MVP and a strict no-regression replacement for feature 003 (minus timelines, which US2 brings back better).

---

## Phase 4: User Story 2 - Compare Players Across Time On Zoomable Histogram Timelines (Priority: P2)

**Goal**: Ship the analytical view — Timelines tab — with full-width per-player histogram rows, global zoom-and-pan shared across all rows, viewport-and-zoom-adaptive bucket widths, and per-event minor-action data sourced from the Processor's new `timedActions` field.

**Independent Test**: Regenerate the analysis JSONs (Phase 1 step T002) so `players[].actions.timedActions` is populated. Load `base_1.w3g.analysis.json`. Switch to Timelines: 8 stacked full-width rows render as histograms (not points); zoom in / out / pan: every row updates simultaneously; bucket widths adapt; minor events (clicks/selects/etc.) render distinguishably from major events; bar hover shows bucket time range + per-category counts; switch tabs and back: zoom state persists. Load `base_2.w3g.analysis.json`: zoom resets, full match (~16 min) visible; bars legible.

### Processor extension — feeds the Timelines tab

- [X] T019 [US2] Add a `_classify_action_id(action_id: int) -> str` helper in `processor/analyze.py` mapping w3gjs action `id` values to the same category labels already used by `actions.totals` (`assigngroup`, `rightclick`, `basic`, `buildtrain`, `ability`, `item`, `select`, `removeunit`, `subgroup`, `selecthotkey`, `esc`). Source the mapping from w3gjs's documented opcode table; keep the table inline in `analyze.py` to avoid a fragile cross-language dependency on internal w3gjs constants.
- [X] T020 [US2] Add an `_extract_timed_actions(parser_output) -> dict[player_id, list[{timeMs, category}]]` helper in `processor/analyze.py` that walks `events[]`, accumulates the running in-game time from `timeIncrement`, iterates each `commandBlocks[].actions[]` entry, classifies via T019, and appends `{timeMs, category}` to the per-player list. Sort each list by `timeMs` non-decreasing on emission.
- [X] T021 [US2] Wire the extractor into the existing per-player builder: extend `_build_actions(player, tracking_interval_ms, timed_actions_for_player)` in `processor/analyze.py` so the returned dict gains `"timedActions": [...]` alongside the existing `apmTimeline` and `totals`. Pass the per-player list down from the top-level `analyze()` call site.
- [X] T022 [P] [US2] Add `processor/tests/test_timed_actions.py` covering both committed fixtures: assert (a) every player has a `timedActions` field that is a list, (b) for every category present in `actions.totals`, the count of entries with that category in `timedActions` equals the total, (c) `timedActions` is sorted by `timeMs` non-decreasing, (d) every `timeMs` is in `[0, match.duration]`.
- [X] T023 [P] [US2] Update `processor/tests/test_output_shape.py` (or equivalent shape assertion) to include `timedActions` in the expected `players[].actions` shape, so future schema regressions are caught.
- [X] T024 [US2] Re-run T002 to regenerate `*.analysis.json` against the extended Processor; confirm both fixtures load in the existing feature-003 visualizer codepath without error (additive-compat sanity check).

### Visualizer — Timelines tab

- [X] T025 [P] [US2] Implement `collectPlayerEvents(player, analysis)` in `visualizer/visualizer.js` — produces a single per-player event stream combining `player.actions.timedActions` (each tagged with its category), `player.production[]` entries (tagged `buildtrain` / `item` / `upgrade` etc. consistent with the Processor categorisation), `player.heroes[].abilityOrder[]` entries (tagged `ability`), and `player.resourceTransfers[]` (tagged `transfer`). Result is sorted by `timeMs`.
- [X] T026 [P] [US2] Implement `chooseBucketWidth(visibleMs, viewportPx)` in `visualizer/visualizer.js` per research.md R4 — target bucket count ≈ `viewportPx / TARGET_BUCKET_PX` (TARGET_BUCKET_PX = 10), then snap visibleMs/target to the nearest "nice" interval from `[1s, 2s, 5s, 10s, 15s, 30s, 1m, 2m, 5m, 10m, 15m, 30m, 1h]`.
- [X] T027 [P] [US2] Implement `bucketEvents(events, startMs, endMs, bucketWidthMs)` in `visualizer/visualizer.js` — returns `[{ start, end, counts: {category → n}, total }]` for every bucket overlapping `[startMs, endMs]`. Linear scan; no library.
- [X] T028 [US2] Implement `renderPlayerHistogram(player, zoomState, viewportPx)` in `visualizer/visualizer.js` — composes `collectPlayerEvents`, `chooseBucketWidth`, `bucketEvents`, and produces an SVG element with one `<rect>` (or stacked sub-rects) per bucket. Major events (categories `buildtrain`/`ability`/`item`/`removeunit`/`esc` plus production/heroes/transfer-tagged entries) and minor events (`rightclick`/`select`/`selecthotkey`/`basic`/`assigngroup`/`subgroup`) render in distinguishable colors.
- [X] T029 [US2] Implement `renderTimeAxis(zoomState, viewportPx, bucketWidthMs)` in `visualizer/visualizer.js` — renders `mm:ss` (or `h:mm:ss` over an hour) labels at snapped bucket boundaries. Reuses `formatTimeMs` from feature 003.
- [X] T030 [US2] Implement `renderTimelinesTab()` in `visualizer/visualizer.js` — renders the zoom control affordance (slider or wheel-zoom area), the time axis, and one full-width player row per `pageState.analysis.players[]` stacked top-to-bottom. Each row contains a name + color swatch and a histogram. On first activation, initialises `pageState.zoomState = {0, match.duration}` if `null`.
- [X] T031 [US2] Implement zoom + pan input handlers in `visualizer/visualizer.js` — mouse-wheel-with-modifier for zoom, drag-on-axis for pan (or simpler: `<input type="range">` slider for zoom + clickable buttons for pan). On each input event, mutate `pageState.zoomState` (clamped to `[0, match.duration]` and to a minimum bucket width of ~250 ms) and re-render the Timelines tab body. Single re-render of all rows at once — no per-row event listeners.
- [X] T032 [US2] Add a window-resize handler that triggers a `renderTimelinesTab()` re-render only if the Timelines tab is active, so the bucket width recomputes per FR-014.
- [X] T033 [US2] Implement bar hover/focus tooltips in `visualizer/visualizer.js` — show `start–end time`, per-category counts, total. Use plain DOM `title` attribute or a single shared absolute-positioned `<div>` updated on `mouseover` / `focusin`.
- [X] T034 [US2] Persist `pageState.zoomState` across tab switches; reset on file load (already wired in T007 — verify behavior on tab switch and on file reload).
- [X] T035 [P] [US2] Add Timelines-tab styles in `visualizer/styles.css` — full-width player row layout, name+swatch column, histogram bar colors per category (major vs. minor distinguishable), tooltip styling, zoom-control affordance, time-axis labels.
- [X] T036 [US2] Manually walk `quickstart.md` §3 Timelines-tab checks against base_1 (8 players, ~88 min, dense data) and §4 against base_2 (3v3, ~16 min). Verify SC-005 (zoom <100 ms perceived), SC-006 (no sub-pixel bars, no >25%-width bars), SC-007 (top-down full-width layout).

**Checkpoint**: Timelines tab fully functional. Major + minor events visible with global zoom. Both fixtures render correctly. Processor pytest passes on the new invariant.

---

## Phase 5: User Story 3 - See A Placeholder For The Upcoming Analysis Tab (Priority: P3)

**Goal**: Polish the Analysis tab placeholder from US1's minimal stub into the spec'd content (heading + 2–3 explanatory lines; no fake data).

**Independent Test**: With US1 (and ideally US2) complete, load any analysis JSON, click the Analysis tab. The tab content clearly identifies itself as a future feature; switching back to Summary leaves Summary working.

- [X] T037 [US3] Replace the US1 placeholder body of `renderAnalysisStub()` in `visualizer/visualizer.js` with the spec'd content per `contracts/ui-contract.md` §"Analysis tab (stub)" — heading "Analysis (coming soon)", two short paragraphs of explanatory text, no interactive controls. Optionally surface `pageState.analysis.match.id` as a one-line breadcrumb so the loaded replay is identifiable.
- [X] T038 [P] [US3] Add stub-tab styles in `visualizer/styles.css` — centered heading, muted body text, comfortable max-width column. Shared with the Map stub (US4) where possible.
- [X] T039 [US3] Manual check: load both fixtures, switch to Analysis, confirm placeholder renders, switch back to Summary / Timelines, confirm both still work.

---

## Phase 6: User Story 4 - See A Placeholder For The Upcoming Map Tab (Priority: P3)

**Goal**: Polish the Map tab placeholder from US1's minimal stub into the spec'd content (heading + 2–3 explanatory lines; optional mention of the loaded map name).

**Independent Test**: With US1 (and ideally US2) complete, load any analysis JSON, click the Map tab. The tab content clearly identifies itself as a future feature; switching back to Summary leaves Summary working.

- [X] T040 [US4] Replace the US1 placeholder body of `renderMapStub()` in `visualizer/visualizer.js` with the spec'd content per `contracts/ui-contract.md` §"Map tab (stub)" — heading "Map (coming soon)", two short paragraphs, optional one-line `<map>` path/name surfaced from `pageState.analysis.map`.
- [X] T041 [US4] Manual check: load both fixtures, switch to Map, confirm placeholder renders (and surfaces base_1 / base_2's map paths if implemented), switch back to Summary / Timelines, confirm both still work.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Cross-cutting cleanup, doc updates, full-walkthrough regression, and the file-split decision.

- [X] T042 Re-walk `quickstart.md` end-to-end against both fixtures with all four tabs — this is the feature's acceptance gate. Capture any deviations from `spec.md` SC-001 through SC-008 and fix.
- [X] T043 Decide on the visualizer file split per research.md R7: if `visualizer/visualizer.js` exceeds ~1,500 lines, split into multiple plain files (e.g., `state.js`, `tabs.js`, `summary.js`, `timelines.js`, `stubs.js`, `main.js`) loaded via separate `<script src="...">` tags in dependency order in `visualizer/index.html`. No ES modules, no `type="module"`. If under threshold, leave as-is and document the decision in DATA.md.
- [X] T044 [P] Update `visualizer/DATA.md` to describe the four-tab layout (Summary / Timelines / Analysis / Map), the new Summary aggregations, the Timelines tab's zoom + histogram behavior, and a pointer to `specs/004-visualizer-tabs/quickstart.md` for the full walkthrough.
- [X] T045 [P] Update `processor/DATA.md` to mention the new `players[].actions.timedActions` field, with a one-line description of the invariant that `count(timedActions, c) == totals[c]`.
- [X] T046 [P] Confirm `processor/tests/` pytest run passes cleanly (T001 baseline + T022 / T023 additions).
- [X] T047 Final non-regression sweep: run the unmodified feature-003 Visualizer codebase (e.g., a stash or branch checkout) against the regenerated `*.analysis.json` to confirm the additive `timedActions` field does not break the prior Visualizer — exercises the input-contract.md compatibility guarantee.

---

## Dependencies & Story Ordering

```text
Phase 1 (Setup) ─────────────────┐
                                 ├─→ Phase 2 (Foundational) ─┐
                                 │                            │
                                 │                            ├─→ Phase 3 (US1) — MVP
                                 │                            │       │
                                 │                            │       ├─→ Phase 4 (US2)   [needs T019–T024 Processor + T002 regen]
                                 │                            │       │
                                 │                            │       ├─→ Phase 5 (US3)
                                 │                            │       │
                                 │                            │       └─→ Phase 6 (US4)
                                 │                            │
                                 │                            └─→ Phase 7 (Polish)        [requires US1+US2+US3+US4]
                                 └────────────────────────────────────→ ...
```

- **US1 (P1)** is the MVP. After Phase 3, the visualizer is shippable as a complete replacement for feature 003 (minus the per-player timeline, which US2 restores in upgraded form).
- **US2 (P2)** is independent of US3 / US4 and can ship before either. It is the only story that requires the Processor extension (T019–T024). After Phase 4, the visualizer's full analytical scope is delivered.
- **US3 (P3)** and **US4 (P3)** are tiny polish stories. Either can ship before the other; both depend only on the US1 stub-renderer scaffolding (T017).

---

## Parallel Execution Opportunities

Within a single story, tasks marked **[P]** touch independent files or independent function bodies and can run concurrently:

- **Phase 3 (US1)**: T008, T009, T010 (three pure aggregation functions, all in `visualizer.js` but in different function bodies — review-time only constraint, not implementation), and T016 (CSS, separate file) parallelize.
- **Phase 4 (US2)**:
  - Processor side: T022 and T023 (two test files) parallelize after T019–T021 land.
  - Visualizer side: T025, T026, T027 (three pure helper functions in different bodies) and T035 (CSS) parallelize before T028 / T030.
- **Phase 7 (Polish)**: T044, T045, T046 are independent (different files / different commands).

Cross-story parallelism is bounded by Phase 2's gate — no US tasks before T003–T007.

---

## Implementation Strategy

**MVP cut (P1 only)**: Stop after Phase 3. The Summary tab plus minimal stubs is a coherent shippable replacement for feature 003. The trade-off: the Timelines tab is a placeholder, so the only analytical regression vs. feature 003 is "no per-player timeline". For most reviewers, the cleaner Summary aggregations more than compensate.

**Recommended cut**: Phase 1 → Phase 2 → Phase 3 → **Phase 4** → Phase 7. Defer US3 + US4 polish (Phase 5 / 6) to a tiny follow-up. This delivers the full analytical value of the feature; the stub tabs from US1 are honest — they clearly say "coming soon" and aren't claiming to be done.

**Full feature**: Phases 1 → 7 in order. Within Phase 4, the Processor work (T019–T024) blocks the Timelines implementation (T025+), but T022 / T023 / T035 parallelize once their predecessors are in.

**Risk register**:
- **JSON size growth** (research.md / spec FR-015c assumption): if regenerated `base_1.analysis.json` exceeds ~25 MB, revisit FR-015 with the user — the original 20 MB envelope might need a small relaxation, or the Processor might need to omit a category. Measure during T024 and report.
- **w3gjs action-id classification table accuracy** (T019): if `count(timedActions, c) != totals[c]` for some category in T022, the inline mapping is wrong; cross-check against w3gjs's source or test cases before fudging the test.
- **Histogram performance at full match + 8 players + max zoom-out** (T028 / T036): if rendering exceeds 100 ms (SC-005 violation), profile before adding memoisation or a virtual-DOM library — the constitution still rules out a library.

---

## Validation Checklist (post-implementation)

- [ ] All `spec.md` Functional Requirements (FR-001 through FR-022) are exercised by at least one task above.
- [ ] All `spec.md` Success Criteria (SC-001 through SC-008) have a manual or automated check (mostly in T018 / T036 / T042).
- [ ] Every task has a checkbox, an ID, a story label where required, and an explicit file path.
- [ ] No task adds an npm dependency, a `node_modules/` to the visualizer, a build step, or a framework (Principle V).
- [ ] The Parser layer is untouched (Principle II).
- [ ] All Processor changes are covered by pytest assertions on both committed fixtures (Principle IV).
