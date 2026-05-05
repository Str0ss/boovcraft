# Data Model: Interactive Timelines (Feature 005)

Phase 1 of `/specs/005-react-timelines/plan.md`. Documents the
**in-memory** data shapes the migrated visualizer holds. The
**on-disk** input contract — `*.analysis.json` produced by the
Processor — is unchanged; see `contracts/input-contract.md` and
`specs/004-visualizer-tabs/data-model.md` § A. for the JSON shape.

## A. Page state (top-level Context value)

```ts
type Tab = 'summary' | 'timelines' | 'analysis' | 'map';

interface PageState {
  loadedFile: { name: string; loadedAt: number } | null;
  analysis: AnalysisJson | null;
  activeTab: Tab;
  zoomState: ZoomState;          // see §B
  zoomHistory: ZoomHistory;      // see §C
  filterState: FilterState;      // see §D
}
```

`PageState` is the single source of truth for cross-component data.
Held in a React Context provider (`PageStateContext`) at the App
root. Components read with `useContext(PageStateContext)`; mutation
flows through dispatchers exposed alongside the value.

### Dispatcher surface

```ts
interface PageStateDispatchers {
  loadFile(file: File): void;          // FileReader → validate → set analysis
  setActiveTab(tab: Tab): void;
  brushZoom(rangeMs: { startMs: number; endMs: number }): void;
  setSliderZoom(visibleMs: number): void;
  panBy(deltaMs: number): void;
  resetZoom(): void;
  zoomBack(): void;
  zoomForward(): void;
  toggleCategory(category: ActionCategory): void;
  setBulkCategoryFilter(group: 'major' | 'minor' | 'all', enabled: boolean): void;
}
```

The dispatchers are thin wrappers around the reducers in §C / §D
plus simple `setState` calls for `activeTab`, `zoomState`. The
visualizer never mutates `analysis` — it is treated as immutable
once a file is loaded. Re-loading replaces the whole `analysis`
reference and triggers cascade resets per the rules below.

### State transitions

| Trigger | State change |
|---|---|
| Page first opens | `pageState = initial` (all fields null / default). |
| User picks a valid analysis JSON | `loadedFile`, `analysis` populated; `activeTab = 'summary'`; `zoomState = { visibleStartMs: 0, visibleEndMs: match.durationMs }`; `zoomHistory = empty`; `filterState = allEnabled` (FR-015 / FR-021). |
| User picks a malformed file | Existing state cleared (no bleed-through, FR-024). Error is surfaced; pageState returns to initial. |
| User clicks a tab | `activeTab` updates; nothing else changes (zoom + filter persist across tab switches per FR-013/14, carrying forward feature 004's FR-018). |
| User brush-zooms | `zoomState` updated to brushed range; `zoomHistory` pushes prior `zoomState`. |
| User adjusts slider | `zoomState` updated; current slider position is canonical, but slider-driven zoom does NOT push history (continuous adjustment would otherwise spam history). |
| User clicks pan button | `zoomState` shifts; no history push. |
| User clicks Back / Forward | `zoomHistory` cursor moves; `zoomState` derived from cursor. |
| User clicks Reset zoom | `zoomState` returns to full match; `zoomHistory` clears. |
| User toggles a category | `filterState` updated. No history push (filter ≠ zoom). |
| User loads a different file mid-session | All transient state resets per the "User picks a valid analysis JSON" row. |

## B. ZoomState

```ts
interface ZoomState {
  visibleStartMs: number;        // ≥ 0
  visibleEndMs: number;          // ≤ analysis.match.durationMs
                                 // and ≥ visibleStartMs + MIN_BUCKET_MS
}
```

Derived view: `visibleMs = visibleEndMs - visibleStartMs`. Used by
ECharts as the `dataZoom` `start` / `end` percentage values:
`start = visibleStartMs / durationMs * 100` and similarly for `end`.

Constraints (enforced by the brush-clamp helper, FR-004 / FR-006):
- `0 ≤ visibleStartMs < visibleEndMs ≤ durationMs`.
- `visibleEndMs - visibleStartMs ≥ MIN_BUCKET_MS` (≈ 250 ms).

## C. ZoomHistory (reducer-shaped)

```ts
interface ZoomHistoryEntry {
  visibleStartMs: number;
  visibleEndMs: number;
}

interface ZoomHistory {
  back: ZoomHistoryEntry[];     // top of stack = most recent prior view
  forward: ZoomHistoryEntry[];  // top of stack = where 'Forward' goes next
}

type ZoomHistoryAction =
  | { type: 'BRUSH'; previous: ZoomHistoryEntry }   // push current onto back; clear forward
  | { type: 'BACK';  current: ZoomHistoryEntry }    // push current onto forward; pop from back
  | { type: 'FORWARD'; current: ZoomHistoryEntry }  // push current onto back; pop from forward
  | { type: 'RESET' }                               // clear both stacks
  | { type: 'LOAD_FILE' };                          // clear both stacks
```

Reducer file: `visualizer/src/state/zoomHistory.ts`. Pure;
Vitest-covered (`tests/zoomHistory.test.ts`).

Standard browser-style semantics:
- `BRUSH` discards the forward stack (FR-019).
- `BACK` requires `back.length > 0`; otherwise no-op (FR-022).
- `FORWARD` requires `forward.length > 0`; otherwise no-op (FR-022).
- `RESET` and `LOAD_FILE` clear both stacks (FR-020, FR-021).

## D. FilterState (reducer-shaped)

```ts
type ActionCategory =
  | 'buildtrain' | 'ability' | 'item' | 'removeunit' | 'esc' | 'transfer'
  | 'rightclick' | 'select' | 'selecthotkey' | 'basic'
  | 'assigngroup' | 'subgroup';

interface FilterState {
  // Each category maps to true (visible) or false (filtered out).
  enabled: Record<ActionCategory, boolean>;
}

type FilterAction =
  | { type: 'TOGGLE'; category: ActionCategory }
  | { type: 'SET_GROUP'; group: 'major' | 'minor' | 'all'; enabled: boolean }
  | { type: 'RESET' };  // back to allEnabled (used on LOAD_FILE)
```

Reducer file: `visualizer/src/state/filterState.ts`. Pure;
Vitest-covered (`tests/filterState.test.ts`).

Initial state: every category set to `true`. The `MAJOR_CATEGORIES`
and `MINOR_CATEGORIES` sets carry over from feature 004's
`TIMELINE_CONFIG`; `transfer` is in the major group.

The filter is consumed by the histogram-data pipeline:

```ts
function filterBuckets(buckets: Bucket[], filterState: FilterState): Bucket[]
```

which walks each bucket's `counts` map and zeros out entries for any
category where `filterState.enabled[category] === false`. Recompute
`bucket.total` afterwards.

## E. Histogram data pipeline (Timelines tab)

Pure pipeline, fed into ECharts as series data:

```text
analysis.players[i]
  ├─ collectPlayerEvents(player) ────────► PlayerEvent[]
  │                                        each: { timeMs, category }
  │                                        sourced from:
  │                                          - actions.timedActions (already classified)
  │                                          - resourceTransfers (tagged 'transfer')
  │
  ├─ chooseBucketWidth(visibleMs, viewportPx)  ► bucketWidthMs
  │                                              snapped to nice interval
  │
  ├─ bucketEvents(events, startMs, endMs, bucketWidthMs) ► Bucket[]
  │                                                        each: { start, end, counts, total }
  │
  └─ filterBuckets(buckets, filterState)  ► RenderBucket[]
                                            zeroed for filtered categories

ECharts option:
  xAxis: time axis from visibleStartMs to visibleEndMs
  series: one stacked-bar series per ActionCategory, color-coded
  dataZoom: type 'inside' (drag to pan) + brush (drag to zoom)
```

Each pipeline step is a pure function in `src/data/timelineEvents.ts`.
`bucketEvents` is the bottleneck on long matches; it must remain
linear in event count. Vitest-covered with the long-match fixture
(`base_1`).

## F. Aggregations (Summary tab)

The three aggregation helpers from feature 004 port to TypeScript,
with small typed return shapes:

```ts
interface ProductionAggregation {
  buildings: ProdRow[];
  units: ProdRow[];
  upgrades: ProdRow[];
  items: ProdRow[];
}
interface ProdRow { id: string; name: string; unknown: boolean; count: number; }

interface HeroAggregation {
  id: string;
  name: string;
  unknown: boolean;
  finalLevel: number;
  abilityChain: { id: string; name: string; unknown: boolean; level: number }[];
}

interface TransferAggregation {
  recipientName: string;
  resource: 'gold' | 'lumber';
  total: number;
  count: number;
}
```

Sources:
- `aggregateProduction(player) → ProductionAggregation` (uses
  `production[<cat>].summary` for counts, sorted alphabetically).
- `aggregateHeroes(player) → HeroAggregation[]` (one per hero;
  `abilityChain` is `heroes[i].abilityOrder` ported).
- `aggregateTransfers(player, analysis) → TransferAggregation[]`
  (sorted by total descending; gold and lumber as separate rows).

These helpers do NOT consume `filterState` — the Summary tab is
unaffected by the category filter (FR-017 / Assumption 4 in spec).

Files: `src/data/aggregations.ts`, tested in
`tests/aggregations.test.ts`.

## G. What does NOT change vs feature 004

- The `*.analysis.json` document shape is unchanged. `players[].
  actions.timedActions` is consumed exactly as feature 004 produced
  it.
- The category palette and major/minor classification (`MAJOR` vs
  `MINOR` lists in feature 004's `TIMELINE_CONFIG`) carry forward.
- All entity-name handling for `unknown: true` flagged entries
  carries forward — the React component for entity labels (`Entity`
  in `src/components/Entity.tsx`) is a port of feature 003's
  `entityLabelEl` helper.
- Time formatting (`formatTimeMs`, `mm:ss` / `h:mm:ss`) carries
  forward as `src/data/format.ts`.
- All empty-state copy carries forward verbatim ("No in-game chat in
  this replay.", "No allied resource transfers.", etc.).

## H. Out of scope for this data model

- Persisted state across page reloads (`localStorage`, IndexedDB).
- Multi-replay state (comparison of two analyses in one session).
- Cross-tab routing via URL hash.
- Per-player filtering on the Timelines tab (only per-category).
- Filter applied to the Summary tab.
- Touch / multi-touch gesture state.
