---
description: "Tasks for feature 005: Interactive Timelines (React Migration + Brush + Filter)"
---

# Tasks: Interactive Timelines (React Migration + Brush-to-Zoom + Event Filter)

**Input**: Design documents from `/specs/005-react-timelines/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Automated tests in this feature are **Vitest unit tests on
pure logic only** (brush math, bucket sizing, filter / history
reducers, aggregation helpers — see `research.md` § R5 / R9). Visual
correctness remains a manual walkthrough per `quickstart.md`,
preserving feature 003's "no automated frontend tests in v1" stance
for the visual layer. The Processor's pytest is unchanged in this
feature; running it green at the end is the non-regression check
for the unchanged input contract.

**Organization**: Tasks are grouped by user story to enable
independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on
  incomplete tasks)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2,
  US3, US4)
- File paths are project-relative paths from repo root

## Path Conventions

- **Visualizer (new React app)**: everything under `visualizer/`,
  replacing the feature 003 / 004 vanilla files in the same
  directory:
  - source: `visualizer/src/...`
  - tests: `visualizer/tests/...`
  - infra: `visualizer/{Dockerfile,docker-compose.yml,nginx.conf,vite.config.ts,tsconfig.json,package.json,index.html}`
- **Processor**: unchanged in this feature.
- **Parser**: unchanged in this feature.
- **Fixtures**: `sample_replays/base_*.w3g.analysis.json` (regenerable;
  `.gitignore`d) — same files feature 004 used.

---

## Phase 1: Setup (Project Initialization)

**Purpose**: Bring up the empty Vite + React + TypeScript + ECharts +
Vitest scaffold and the Docker production deployment shell. After
this phase, `npm run dev` opens an empty React page and
`docker compose up` serves an empty `dist/` over nginx-on-alpine.

- [X] T001 Remove the feature 003/004 vanilla files in preparation for the React replacement: `rm visualizer/visualizer.js visualizer/styles.css visualizer/index.html visualizer/DATA.md` (the new Vite-managed files take the same paths in subsequent tasks). Optionally `git rm` if you prefer explicit history.
- [X] T002 Initialize the npm package at `visualizer/package.json` with name `boovcraft-visualizer`, type `module`, scripts `dev`, `build`, `preview`, `test`, `test:watch`. Mark `private: true`.
- [X] T003 Install runtime dependencies in `visualizer/`: `npm install react@^18 react-dom@^18 echarts@^5 echarts-for-react@^3`. Lock with `package-lock.json` (commit it).
- [X] T004 Install dev dependencies in `visualizer/`: `npm install -D vite@^5 @vitejs/plugin-react@^4 typescript@^5.5 @types/react@^18 @types/react-dom@^18 vitest@^1 @types/node@^20`.
- [X] T005 Add `visualizer/tsconfig.json` with strict mode (`strict: true`, `noUncheckedIndexedAccess: true`, `noImplicitOverride: true`), target `ES2022`, `module: ESNext`, `moduleResolution: bundler`, `jsx: react-jsx`, `lib: [DOM, DOM.Iterable, ES2022]`. Includes `src` and `tests`.
- [X] T006 Add `visualizer/vite.config.ts` with `@vitejs/plugin-react`, dev server `port: 5173`, `build.outDir: 'dist'`, `build.sourcemap: false` (production), no externalized dependencies (everything bundled per V (c)).
- [X] T007 Add `visualizer/index.html` as the Vite entry: `<div id="root"></div>`, `<script type="module" src="/src/main.tsx">`, system-font CSS variables in `<style>`, page title `"Boovcraft Replay Visualizer"`, viewport `width=1280`.
- [X] T008 Add `visualizer/src/main.tsx` mounting an empty `<App />` placeholder onto `#root`.
- [X] T009 Add `visualizer/src/App.tsx` empty placeholder (`<main id="app"><h1>Boovcraft Replay Visualizer</h1></main>`) — content fills in during foundational + US4 phases.
- [X] T010 Add `visualizer/.gitignore` for `node_modules/`, `dist/`, `coverage/`, `.vite/`. Update repo `.gitignore` if needed.
- [X] T011 Configure Vitest in `visualizer/vite.config.ts` (or separate `vitest.config.ts`): `test.environment: 'node'` (pure-logic tests need no DOM), `test.globals: false`, `test.include: ['tests/**/*.test.ts']`. Pure-logic only — no jsdom needed.
- [X] T012 Add `visualizer/Dockerfile` — multi-stage: stage 1 `node:20-alpine` runs `npm ci && npm run build`; stage 2 `nginx:alpine` copies `dist/` to `/usr/share/nginx/html` and copies `nginx.conf` to `/etc/nginx/conf.d/default.conf`.
- [X] T013 Add `visualizer/nginx.conf` — single `server` block listening on port 80, root `/usr/share/nginx/html`, `try_files $uri $uri/ /index.html`, sensible cache headers, no upstream proxy, no remote anything.
- [X] T014 Add `visualizer/docker-compose.yml` — one service `visualizer` building from `Dockerfile`, port mapping `8080:80`, no environment variables required for default operation.
- [X] T015 Smoke-test the empty scaffold: `cd visualizer && npm run dev` opens an empty React page on `http://localhost:5173`; `npm run build` produces a `dist/` folder; `docker compose up` serves the empty page on `http://localhost:8080`. Document any deviations and fix.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build the cross-cutting infrastructure every user story
depends on — the typed `AnalysisJson` shape, the validate / format /
entity helpers, the single `PageStateContext`, the file-load
lifecycle, the tab-strip chassis, and the drag-and-drop overlay.
After this phase, the user can pick a file and see "Summary tab —
under construction" placeholder content; switching tabs works; no
data renders yet.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T016 Define the analysis JSON TypeScript types in `visualizer/src/types/analysis.ts` — `AnalysisJson`, `Match`, `Player`, `Production`, `Hero`, `AbilityLearn`, `ResourceTransfer`, `Actions`, `TimedAction`, `Chat`, `ActionCategory` literal-union (12 categories from feature 004 / data-model § D). Mirror the schema in `processor/DATA.md`.
- [X] T017 Implement JSON-shape validation in `visualizer/src/data/validate.ts` — port `validateAnalysisShape` from feature 003 to TS, returning `{ ok: true, value: AnalysisJson } | { ok: false, message: string }`. Same `REQUIRED_TOP_LEVEL_KEYS` set.
- [X] T018 Implement formatting helpers in `visualizer/src/data/format.ts` — `formatTimeMs(ms, totalMs): string` (`mm:ss` / `h:mm:ss` switch) and `formatInt(n): string` (locale-aware).
- [X] T019 Implement the `Entity` React component in `visualizer/src/components/Entity.tsx` — port `entityLabelEl` from feature 003 → renders display name with the `[?]` badge for `unknown: true` entries; reusable everywhere a labeled entity appears. Co-located CSS module for the unknown-marker styling.
- [X] T020 Define `PageState` shape and `PageStateDispatchers` type in `visualizer/src/state/types.ts` per `data-model.md` § A. Initial state constants too.
- [X] T021 Implement the `PageStateContext` provider in `visualizer/src/state/PageStateContext.tsx` — `useReducer` over the page state, exposes `{ pageState, dispatchers }` via Context. Stub the per-action dispatchers; wire them up across phases as needed.
- [X] T022 Implement the `loadFile` dispatcher in `PageStateContext.tsx` — uses `FileReader.readAsText`, validates via T017, populates `pageState.{loadedFile, analysis}`, resets `activeTab` to `summary`, resets `zoomState` to `{0, durationMs}`, resets `zoomHistory` and `filterState` to defaults (per data-model § A state-transition table).
- [X] T023 Implement `clearReport` and the malformed-file error path — bleed-through prevention (FR-024). Surface error message via a small error-banner component.
- [X] T024 Implement `FilePicker` component in `visualizer/src/components/FilePicker.tsx` — `<input type="file" accept=".json,application/json">`, on change dispatches `loadFile`. Loaded-file label rendered next to the picker once a file is loaded.
- [X] T025 Implement `DropZone` component in `visualizer/src/components/DropZone.tsx` — full-screen drag overlay, `dragenter` / `dragover` / `dragleave` / `drop` handlers; on drop dispatches `loadFile` (single file). Port the dragDepth counter pattern from feature 003.
- [X] T026 Implement `TabStrip` component in `visualizer/src/components/TabStrip.tsx` — horizontal nav with 4 buttons (Summary / Timelines / Analysis / Map), `aria-selected` driven by `pageState.activeTab`, click dispatches `setActiveTab`, hidden when no analysis loaded. Co-located CSS module.
- [X] T027 Implement tab routing in `visualizer/src/App.tsx` — header (title + file picker + loaded-file label), error banner, tab strip, and a switch on `pageState.activeTab` to render `<SummaryTab />` / `<TimelinesTab />` / `<AnalysisStub />` / `<MapStub />`. Each tab is a stub component for now (US4 fills them in).
- [X] T028 Implement four placeholder tab components in `visualizer/src/tabs/{SummaryTab,TimelinesTab,AnalysisStub,MapStub}.tsx` returning a single `<section>` with a "tab content goes here" placeholder. Lets the routing be exercised end-to-end before content is real.
- [X] T029 Add baseline app CSS in `visualizer/src/styles/global.css` — reset, dark palette (carry from feature 004's `styles.css` colors), system-font stack, `box-sizing: border-box`, `[hidden]` rule. Imported once from `main.tsx`.

**Checkpoint**: Pick a fixture; tab strip appears; clicking tabs swaps placeholder content; dropping a file works; loading a malformed file shows the error path. No tab content is real yet — that is each user story's work below.

---

## Phase 3: User Story 4 — Every Existing Capability Still Works After The Migration (Priority: P1) 🎯 MVP

**Goal**: Port every feature 003 + 004 user-facing capability into the
React app — Summary tab with all aggregations, Timelines tab with the
basic histogram + slider zoom + pan + reset zoom (no brush, no filter
yet), Analysis + Map stubs with the spec'd placeholder content. After
this phase, the React app is a strict superset of feature 004 (minus
the new US1/US2/US3 capabilities, which Phases 4–6 add).

**Why P1 / why first**: Although the spec lists US4 last, US1 / US2 /
US3 depend on the rendered chart surface to attach their behavior to.
Phase 3 is the migration body; Phases 4–6 are interaction
enhancements layered on top. After Phase 3 the React app passes
features 003 + 004's quickstarts.

**Independent Test**: Run `cd visualizer && npm run dev`, open
`http://localhost:5173`, pick `sample_replays/base_2.w3g.analysis.json`.
Verify every check in `specs/004-visualizer-tabs/quickstart.md` § 3 +
§ 4 against the migrated visualizer, ignoring the Phase 4 / 5 / 6
features (brush, filter, history). Repeat for `base_1` and via
`docker compose up`.

### Implementation for User Story 4

#### Summary tab content

- [X] T030 [P] [US4] Implement `aggregateProduction(player)` in `visualizer/src/data/aggregations.ts` per `data-model.md` § F — group by category, alphabetic order within each category, returns `ProductionAggregation`.
- [X] T031 [P] [US4] Implement `aggregateHeroes(player)` in `visualizer/src/data/aggregations.ts` — preserves `abilityOrder` order; returns `HeroAggregation[]`.
- [X] T032 [P] [US4] Implement `aggregateTransfers(player, analysis)` in `visualizer/src/data/aggregations.ts` — group by `(toPlayerId, resource)`, sort by total descending, returns `TransferAggregation[]`.
- [X] T033 [US4] Add `visualizer/tests/aggregations.test.ts` — Vitest tests load both committed `*.analysis.json` fixtures and assert aggregations match feature 004's by-fixture spot checks (production counts, hero chains, transfer rows). No mocks (Principle IV's spirit).
- [X] T034 [US4] Implement `MatchHeader` component in `visualizer/src/components/MatchHeader.tsx` — match-level facts row (outcome, duration, gametype, matchup, map, version) plus lobby-settings DL grid. Port styling from feature 004.
- [X] T035 [US4] Implement `ActionTotals` component in `visualizer/src/components/ActionTotals.tsx` — DL grid of category totals; carries the `ACTION_TOTAL_LABELS` array from feature 004.
- [X] T036 [US4] Implement `GroupHotkeys` component in `visualizer/src/components/GroupHotkeys.tsx` — 10-row table of (key, assigned, used).
- [X] T037 [US4] Implement `ProductionAggregationView` in `visualizer/src/components/ProductionAggregationView.tsx` — consumes `aggregateProduction`, renders 4 section blocks (Buildings / Units / Upgrades / Items), uses `Entity` for the entity label.
- [X] T038 [US4] Implement `HeroAggregationView` in `visualizer/src/components/HeroAggregationView.tsx` — consumes `aggregateHeroes`, renders the arrow-chain ability progression with `Entity` for each ability label.
- [X] T039 [US4] Implement `TransferAggregationView` in `visualizer/src/components/TransferAggregationView.tsx` — consumes `aggregateTransfers`, renders rows of `<Recipient>: <total> <resource> (<count> transfers)`.
- [X] T040 [US4] Implement `PlayerPanel` component in `visualizer/src/components/PlayerPanel.tsx` — composes header + meta + ActionTotals + GroupHotkeys + ProductionAggregationView + HeroAggregationView + TransferAggregationView. Port the color-swatch + slot/team annotations.
- [X] T041 [US4] Implement `TeamsGrid` component in `visualizer/src/components/TeamsGrid.tsx` — groups players by `teamId`, sorts ascending, renders one team section per group with the winning-team highlight; one `PlayerPanel` per player.
- [X] T042 [US4] Implement `ChatSection` component in `visualizer/src/components/ChatSection.tsx` — empty-state copy when no chat; row-grid layout for messages with channel coloring.
- [X] T043 [US4] Implement `ObserversSection` component in `visualizer/src/components/ObserversSection.tsx` — empty state vs comma-joined names.
- [X] T044 [US4] Replace the Summary tab placeholder with the real content in `visualizer/src/tabs/SummaryTab.tsx` — composes `MatchHeader` + `TeamsGrid` + `ChatSection` + `ObserversSection`. Hooks into `pageState.analysis`.
- [X] T045 [P] [US4] Add CSS modules for the summary components (`PlayerPanel.module.css`, `TeamsGrid.module.css`, etc.) porting feature 004's palette: dark background `#161920`, panel borders `#232831`, accent text colors, the unknown-entity `[?]` badge style.

#### Timelines tab basic histogram (no brush / filter / history yet)

- [X] T046 [P] [US4] Implement `collectPlayerEvents(player)` in `visualizer/src/data/timelineEvents.ts` per `data-model.md` § E — combines `actions.timedActions` and `resourceTransfers` (tagged `transfer`), sorted by timeMs.
- [X] T047 [P] [US4] Implement `chooseBucketWidth(visibleMs, viewportPx)` in `visualizer/src/data/timelineEvents.ts` — same nice-interval snap rule from feature 004 (research `R7`).
- [X] T048 [P] [US4] Implement `bucketEvents(events, startMs, endMs, bucketWidthMs)` in `visualizer/src/data/timelineEvents.ts` — linear-scan bucketing into stacked-category counts.
- [X] T049 [US4] Add `visualizer/tests/timelineEvents.test.ts` — Vitest tests against committed fixtures: bucketing is linear; bucket counts match `actions.totals` invariant (matches feature 004's pytest); chooseBucketWidth snaps to nice intervals; `collectPlayerEvents` includes both `timedActions` and `resourceTransfers`.
- [X] T050 [US4] Implement `PlayerHistogram` component in `visualizer/src/components/PlayerHistogram.tsx` — wraps `echarts-for-react` `<ReactECharts />`. Receives `(player, zoomState, filterState, viewportPx)` props, computes events → buckets, builds the ECharts option object: x-axis time, one stacked-bar series per category (color from category palette), `tooltip.trigger: 'axis'` showing category counts, `dataZoom: [{ type: 'inside', xAxisIndex: 0 }]`. **Brush is configured but not wired in this phase** — added in Phase 4.
- [X] T051 [US4] Implement `useEChartsConnectGroup` hook (or inline equivalent) in `visualizer/src/components/PlayerHistogram.tsx` — calls `echarts.connect('timelines')` once when the first `PlayerHistogram` mounts; adds the `group: 'timelines'` prop on each chart instance. This is what makes zoom synchronized across all rows (feature 004 had to write this by hand).
- [X] T052 [US4] Implement `TimelineLegend` component in `visualizer/src/components/TimelineLegend.tsx` — renders one chip per category with color swatch + label, plus the empty bulk-toggle shell (clicks become live in Phase 5 / US2). Shows the major / minor groups visually.
- [X] T053 [US4] Implement `ZoomControls` component in `visualizer/src/components/ZoomControls.tsx` — slider input + pan buttons (⏮ ◀ ▶ ⏭) + Reset zoom button + view-range readout. Slider position derives from `zoomState`; on input dispatches `setSliderZoom`. Back/Forward buttons present but disabled (US3 wires them up in Phase 6).
- [X] T054 [US4] Replace the Timelines tab placeholder with the real content in `visualizer/src/tabs/TimelinesTab.tsx` — composes `ZoomControls` + `TimelineLegend` + a vertical stack of `PlayerHistogram` rows, one per `pageState.analysis.players[]`. Wraps each row with name + color-swatch + race / APM / winner meta in a left-column block (per `ui-contract.md`).
- [X] T055 [P] [US4] Add CSS modules for the Timelines components — full-width row layout with left-column meta, ECharts canvas filling the remainder; control bar styling; legend chip styling. Match feature 004's appearance.
- [X] T056 [US4] Add a `useViewportWidth` hook in `visualizer/src/hooks/useViewportWidth.ts` — `useEffect` on `window` resize, returns the current chart-area width. Drives `viewportPx` in `chooseBucketWidth` so resize triggers a re-bucket per FR-014.

#### Stub tabs

- [X] T057 [P] [US4] Replace the Analysis tab placeholder in `visualizer/src/tabs/AnalysisStub.tsx` with the spec'd content per `contracts/ui-contract.md` § "Analysis tab" — heading "Analysis (coming soon)", two short paragraphs.
- [X] T058 [P] [US4] Replace the Map tab placeholder in `visualizer/src/tabs/MapStub.tsx` with the spec'd content — heading "Map (coming soon)", surfacing `pageState.analysis.map.path` or `.file` as a one-line breadcrumb.

#### Manual verification

- [X] T059 [US4] Walk `quickstart.md` § 4 (base_2 smoke test) end-to-end against the React app in dev mode. Capture any deviations from feature 004's content/behavior and fix.
- [X] T060 [US4] Walk `quickstart.md` § 5 (base_1 smoke test) end-to-end. Verify base_1's `unknown: true` flagged hero entry renders with the visible marker on Summary; renders consistently on Timelines.
- [X] T061 [US4] Bring up production via `docker compose up`; repeat the base_2 + base_1 walkthrough on `http://localhost:8080`. Verify SC-005 cold-start ≤ 30 s.

**Checkpoint**: After Phase 3 the migrated React app is a strict no-regression port of feature 004 minus the new US1 / US2 / US3 capabilities. Vitest (`npm run test`) is green for aggregations + timelineEvents.

---

## Phase 4: User Story 1 — Drag To Zoom Into A Time Range (Priority: P1)

**Goal**: Add brush-to-zoom on the Timelines tab. Drag horizontally
on any player's chart, release: every row zooms to that time range
together, slider position syncs, prior zoom is captured (Phase 6 /
US3 will wire it into history).

**Independent Test**: With Phase 3 complete, drag from time 5:00 to
8:00 on player 0's chart. Release. Every player's chart zooms to
5:00–8:00. Slider position shows the new zoom level. Press
Escape during a drag → no zoom change. Drag <5 px → no zoom change.

### Implementation for User Story 1

- [X] T062 [P] [US1] Implement `clampBrushedRange(rawRange, durationMs, minBucketMs)` in `visualizer/src/data/timelineEvents.ts` — clamps to `[0, durationMs]` and to ≥ minBucketMs centered on the brush midpoint; returns `{visibleStartMs, visibleEndMs}`.
- [X] T063 [P] [US1] Implement `pixelsToTimeRange(brushPxRange, viewportPx, currentVisibleRange)` in `visualizer/src/data/timelineEvents.ts` — pure conversion; ECharts events give pixel coords on the chart's canvas.
- [X] T064 [P] [US1] Add `visualizer/tests/brushMath.test.ts` — Vitest tests against the two helpers: clamp behavior at edges, sub-MIN brush gets centered, brush past chart edge clamps to bounds, pixel→time conversion is invariant under viewport size.
- [X] T065 [US1] Add `brushZoom(range)` dispatcher in `visualizer/src/state/PageStateContext.tsx` — sets `zoomState` to the brushed range; in Phase 6 this dispatcher will also push the prior `zoomState` onto `zoomHistory.back`. For Phase 4 it just updates zoom.
- [X] T066 [US1] Configure ECharts brush on `PlayerHistogram` in `visualizer/src/components/PlayerHistogram.tsx` — add `brush: { toolbox: ['lineX'], xAxisIndex: 0, brushType: 'lineX', brushMode: 'single', throttleType: 'debounce', throttleDelay: 50 }` to the chart option. The brush rectangle is rendered by ECharts; we don't draw it ourselves.
- [X] T067 [US1] Wire the `brushSelected` (and / or `brushEnd`) ECharts event in `PlayerHistogram` — on receive, extract the selection's data range (`event.batch[0].areas[0].coordRange` is the time interval in axis units), pass through `clampBrushedRange`, dispatch `brushZoom(range)`. Then call `clearBrush` on the chart instance to remove the rectangle (the zoom is the visual feedback now).
- [X] T068 [US1] Implement the small-drag dead zone (FR-003) — if `event.batch[0].areas[0].range[1] - range[0] < 5 / chartWidth * visibleMs` (i.e., < 5 pixels worth of time), treat as a click and skip the zoom dispatch.
- [X] T069 [US1] Implement Escape-cancel (FR-005) — `useEffect` on the Timelines tab installs a `keydown` listener for `Escape` that calls `chartInstance.dispatchAction({ type: 'brush', areas: [] })` to clear in-progress brush. Removed on unmount.
- [X] T070 [US1] Slider position sync after brush — the `ZoomControls` slider is a derived view of `zoomState`, so it re-renders automatically via Context update; no extra wiring needed. Verify in dev that brush release does move the slider.
- [X] T071 [US1] Add a brush affordance hint — one-line caption text under the legend on the Timelines tab the first time it's shown per session: "Drag horizontally on any chart to zoom into that time range." Use `useState` + `sessionStorage`-free dismissal (the spec rules out `localStorage` but a memory-only `useRef` is fine for in-session dismissal).
- [X] T072 [US1] Walk `quickstart.md` § 4 brush-to-zoom checks against base_2 (short fixture). Verify SC-002 (brush release → re-render ≤ 100 ms perceived).
- [X] T073 [US1] Walk the base_1 brush-to-zoom checks. SC-002 holds on the largest fixture (8 players, ~88 min, ~30k events).

**Checkpoint**: Brush-to-zoom is fully functional. Slider stays in sync. Vitest + manual tests both pass.

---

## Phase 5: User Story 2 — Toggle Event Categories (Priority: P1)

**Goal**: Make the legend chips clickable so the user can hide /
show event categories on the Timelines tab. Add bulk-toggle
buttons. Filter persists across tab switches and brush-zoom changes;
resets on file load.

**Independent Test**: Click the "Right-click" chip in the legend.
Every player's histogram re-renders without rightclick segments.
Tooltip on bar hover excludes rightclick. Click "All minor → off"
→ all minor categories disable atomically. Switch to Summary tab,
back: filter state persists. Brush-zoom: filter persists.

### Implementation for User Story 2

- [X] T074 [P] [US2] Implement `filterState` reducer in `visualizer/src/state/filterState.ts` per `data-model.md` § D — actions `TOGGLE | SET_GROUP | RESET`; initial state all-enabled; `MAJOR_CATEGORIES` and `MINOR_CATEGORIES` constants exported.
- [X] T075 [P] [US2] Add `visualizer/tests/filterState.test.ts` — Vitest tests for the reducer: TOGGLE flips a single category; SET_GROUP for `major` / `minor` / `all` flips the right set atomically; RESET returns to all-enabled.
- [X] T076 [US2] Wire `filterState` into `PageStateContext` — add `filterState` to the state, add `toggleCategory(cat)` and `setBulkCategoryFilter(group, enabled)` dispatchers; `loadFile` resets filterState (FR-015).
- [X] T077 [US2] Implement `filterBuckets(buckets, filterState)` in `visualizer/src/data/timelineEvents.ts` — walks each bucket, zeros entries for disabled categories, recomputes `bucket.total`. Returns `RenderBucket[]`.
- [X] T078 [US2] Apply `filterBuckets` in `PlayerHistogram.tsx` between `bucketEvents` and the ECharts series option. The series option excludes filtered-out categories so ECharts' built-in legend / tooltip reflects the filter automatically — but since we want the legend chips to *be* the filter UI, we keep ECharts' legend hidden and drive everything from `filterState`.
- [X] T079 [US2] Make `TimelineLegend.tsx` chips interactive — each chip is now a `<button>`, on click dispatches `toggleCategory(category)`. Visual disabled state via reduced opacity + strikethrough on label.
- [X] T080 [US2] Add bulk-toggle buttons to `TimelineLegend.tsx` (or a sibling component) — at minimum: All on / All off / Major on / Major off / Minor on / Minor off. Each dispatches `setBulkCategoryFilter`.
- [X] T081 [US2] Tooltip handling for filtered categories — ECharts' default tooltip auto-reflects the series array, so simply omitting filtered series from the option fixes tooltips. Verify by hovering a bar with one category disabled — its line should not appear in the tooltip.
- [X] T082 [US2] Empty-everything edge case (FR-016) — when all categories disabled, the histogram option still renders the x-axis but with empty series; verify in dev that no chart-instance error is thrown.
- [X] T083 [US2] Walk `quickstart.md` § 4 filter checks against base_2. Verify SC-003 (toggle → re-render ≤ 100 ms).
- [X] T084 [US2] Walk against base_1 — confirm SC-003 holds on the largest fixture.

**Checkpoint**: Filter toggles and bulk affordances work. Filter state persists across tab + zoom changes. Resets on file load.

---

## Phase 6: User Story 3 — Step Back To Previous Zoom (Priority: P2)

**Goal**: Add zoom history. Brush-zoom three times → click Back to
return to the prior view; Forward to redo. Reset zoom clears
history.

**Independent Test**: With brush-to-zoom from US1 working, brush
three times in succession. Back → returns to second brush. Back →
first brush. Forward → second brush. Brush a new range mid-history
→ forward stack discarded.

### Implementation for User Story 3

- [X] T085 [P] [US3] Implement `zoomHistory` reducer in `visualizer/src/state/zoomHistory.ts` per `data-model.md` § C — actions `BRUSH | BACK | FORWARD | RESET | LOAD_FILE`; standard browser-back semantics.
- [X] T086 [P] [US3] Add `visualizer/tests/zoomHistory.test.ts` — Vitest covers BRUSH push + clear-forward, BACK pops back-stack and pushes onto forward-stack, FORWARD symmetric, BRUSH after BACK clears forward-stack, RESET clears both, LOAD_FILE clears both.
- [X] T087 [US3] Wire `zoomHistory` into `PageStateContext` — add `zoomHistory` field to `PageState`; the existing `brushZoom` dispatcher (T065) now also dispatches a `BRUSH` action with the prior `zoomState` snapshot; add `zoomBack()` and `zoomForward()` dispatchers; `resetZoom()` dispatches `RESET`; `loadFile` dispatches `LOAD_FILE`.
- [X] T088 [US3] Activate the `Back` and `Forward` buttons in `ZoomControls.tsx` — clicks dispatch `zoomBack` / `zoomForward`. `disabled` attribute reflects empty `zoomHistory.back` / `zoomHistory.forward` (FR-022).
- [X] T089 [US3] Slider movements MUST NOT push history — the existing `setSliderZoom` dispatcher skips the history push (only `brushZoom` and `resetZoom` interact with history). Pan buttons also do not push history.
- [X] T090 [US3] Walk `quickstart.md` § 4 brush + history checks against base_2.
- [X] T091 [US3] Walk against base_1 — verify history works correctly across deep nesting (5+ levels of brush).

**Checkpoint**: Zoom history Back/Forward buttons are functional. Vitest covers reducer. Manual verification on both fixtures.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Run the full quickstart end-to-end in both deploy modes
across both fixtures, verify the constitution-mandated guarantees
(SC-005 timing, SC-006 zero-egress, non-regression vs feature 004),
and tidy up documentation.

- [X] T092 Run `npm run test` from `visualizer/` and confirm all Vitest tests pass (aggregations, timelineEvents, brushMath, filterState, zoomHistory).
- [X] T093 Run `cd processor && pytest` and confirm 67/67 passes — Processor is unchanged in this feature (input contract preserved per Principle V (a) / FR-025).
- [X] T094 Walk `quickstart.md` end-to-end in **dev mode** (`npm run dev`) against base_1 + base_2 — every check in sections 4 + 5 passes. Capture any deviations from spec SC-001 through SC-008 and fix.
- [X] T095 Walk `quickstart.md` end-to-end in **production mode** (`docker compose up`) against base_1 + base_2 — every check passes. Verify SC-005 cold start ≤ 30 s on a warm Docker cache; SC-005 dev ready ≤ 10 s.
- [X] T096 Verify SC-006 — open DevTools Network tab, reload, exercise every feature including brush + filter + history + file reload, confirm zero outbound network requests beyond the local origin (Vite dev server or local nginx). No CDN, no fonts, no analytics, no telemetry.
- [X] T097 [P] Update `visualizer/DATA.md` to describe the migrated layer: brief overview of the four-tab + brush + filter + history capabilities, the dual-mode deploy story (`docker compose up` for production, `npm run dev` for development, `npx serve dist/` as the no-Docker fallback), pointer to `specs/005-react-timelines/quickstart.md` for the full walkthrough.
- [X] T098 [P] Update repo-root README (or equivalent) if it documented the file://-double-click flow — link to feature 005's `quickstart.md` for the new bring-up.
- [X] T099 Non-regression sweep: check out feature 004's merged commit (`81ab157`) into a worktree or stash, load a regenerated `*.analysis.json` in the *old* visualizer to confirm the JSON contract is genuinely unchanged (the React app and the static visualizer must be able to render the same files). Restores the migrated visualizer afterwards.
- [X] T100 Confirm `git status` is clean except for the deleted feature 003 / 004 vanilla files (handled in T001) — no dead code remains.

---

## Dependencies & Story Ordering

```text
Phase 1 (Setup) ─────────────────┐
                                 │
                                 ▼
Phase 2 (Foundational) ──────────┤
                                 │
                                 ▼
Phase 3 (US4) — MVP, port ──────►┤  After Phase 3, the React app is a
                                 │  strict superset of feature 004
                                 │  minus US1/US2/US3 capabilities.
                                 │
                                 ▼
Phase 4 (US1, brush) ────────────┤
                                 │
                                 ▼
Phase 5 (US2, filter) ──────────►┤  US1 / US2 are independent of each
                                 │  other; either can ship first after
                                 │  Phase 3.
                                 │
                                 ▼
Phase 6 (US3, history) ──────────┤  Depends on US1's brushZoom
                                 │  dispatcher (T065).
                                 │
                                 ▼
Phase 7 (Polish) ────────────────┘  Requires all prior phases.
```

- **Phase 3 (US4)** is the MVP. Although the spec lists US4 last,
  it's the logical foundation — US1 / US2 / US3 can't be tested
  without the rendered chart surface in place.
- **US1 (Phase 4)** and **US2 (Phase 5)** are independent of each
  other after Phase 3 lands. Either can ship first.
- **US3 (Phase 6)** depends on US1's `brushZoom` dispatcher (T065),
  since the history reducer's `BRUSH` action snapshots the prior
  zoom state.
- **Phase 7 (Polish)** requires all prior phases — final non-
  regression and acceptance gate.

## Parallel Execution Opportunities

Within a single phase, **[P]** marks tasks that touch different
files or different file regions and can be worked concurrently:

- **Phase 1 (Setup)**: T012 / T013 / T014 (three different infra
  files) and T010 (.gitignore) parallelize.
- **Phase 3 (US4)**:
  - **Aggregation helpers**: T030 / T031 / T032 are conceptually
    parallel but all live in `aggregations.ts` — implement
    sequentially or in one go.
  - **Timeline pure helpers**: T046 / T047 / T048 same caveat —
    same file.
  - **Component shells before they have content**: T034 (MatchHeader),
    T035 (ActionTotals), T036 (GroupHotkeys), T042 (ChatSection),
    T043 (ObserversSection), T057 (AnalysisStub), T058 (MapStub) —
    seven different files, parallelizable.
  - **CSS modules**: T045 / T055 — different module files.
- **Phase 4 (US1)**: T062 / T063 / T064 (math helpers + tests in
  separate files) parallelize before T066+.
- **Phase 5 (US2)**: T074 / T075 (reducer + reducer tests in
  separate files) parallelize before T076+.
- **Phase 6 (US3)**: T085 / T086 (reducer + tests in separate files)
  parallelize.
- **Phase 7 (Polish)**: T097 / T098 (different doc files)
  parallelize.

## Implementation Strategy

**MVP cut (Phase 1 → 2 → 3)**: After Phase 3, the React migration
is a strict no-regression replacement for feature 004. The new
analytical capabilities (brush, filter, history) are absent, but
the visualizer is shippable as a "framework migration without new
features" if you want to land the technology change first and
iterate on capabilities in follow-up PRs. This MVP cut gates on:
- All Vitest tests in Phases 1-3 green (`aggregations`, `timelineEvents`).
- Both committed-fixture quickstarts pass against the React app
  in both dev and production modes.

**Recommended cut**: Phases 1 → 2 → 3 → 4 → 5 → 7 (skip US3 zoom
history). After this cut, the user has brush-to-zoom and filtering
— the two P1 user-facing capabilities. Reset zoom (already in
US4) covers the "go back to full match" case adequately for a v1.
US3's back/forward stack is real polish; it shines on power-user
investigation flows but isn't essential for the spec's primary
gesture (find-and-zoom-into-a-3-min-fight per SC-001).

**Full feature**: All seven phases. Total ~100 tasks; the bulk
(roughly half) is in Phase 3's port. Phases 4-6 are smaller because
ECharts handles most of the interaction logic — the "do not
over-engineer" Principle VI is doing real work here.

**Risk register**:
- **`echarts-for-react` peer-dep mismatch with React 18/19**: pin
  React to 18.x (per research.md R2); if a future feature needs
  React 19, revisit `echarts-for-react`'s peer-dep range or
  consider `echarts` directly without the wrapper.
- **Bundle size growing past expectations**: ECharts is ~300 KB
  gzipped. If the dist exceeds ~1 MB and we discover an unused
  series type pulled in transitively, switch to ECharts'
  granular imports (`echarts/core` + selective component imports).
  Document in `quickstart.md` if applied.
- **Brush dead-zone tuning** (T068): the 5-pixel threshold may
  need tuning per feedback. Make it a constant `BRUSH_DEAD_ZONE_PX`
  in `timelineEvents.ts` so it's easy to tweak.
- **Container start exceeds SC-005**: if cold container start
  exceeds 30 s, profile the Dockerfile (multi-stage build is the
  standard fix; if already multi-stage, look at npm install times
  and consider `--prefer-offline --no-audit`).
- **Performance regression on base_1 brush**: if SC-002 is missed
  (>100 ms perceived), profile ECharts; consider:
  (a) `progressive` rendering for large series;
  (b) data downsampling at default zoom (sampling: 'lttb' or
  similar);
  (c) `useDirtyRect: true` on the chart for partial-redraw.

---

## Validation Checklist (post-implementation)

- [ ] All `spec.md` Functional Requirements (FR-001 through FR-028)
      are exercised by at least one task above.
- [ ] All `spec.md` Success Criteria (SC-001 through SC-008) have a
      manual or automated check (mostly in Phase 7).
- [ ] Every task has a checkbox, an ID, a story label where
      required, and an explicit file path.
- [ ] Constitution Check holds post-implementation:
      - I (layer separation) — Parser / Processor untouched ✓
      - II (w3gjs canonical) — Parser untouched ✓
      - III (no premature abstractions, internal) — single Context,
        no plugin system, four reducer files at most ✓
      - IV (fixture-based testing) — Vitest derives inputs from
        committed `*.analysis.json` files; visual layer manual
        against the same fixtures ✓
      - V (a/b/c) — JSON contract preserved (FR-025), single-command
        deploy in both modes (FR-027 / SC-005), no runtime egress
        (FR-026 / SC-006) ✓
      - VI — every new dep verified against the four "well-
        established" criteria in research.md § R1–R5 ✓
- [ ] Processor pytest is still 67/67 green after this feature lands.
