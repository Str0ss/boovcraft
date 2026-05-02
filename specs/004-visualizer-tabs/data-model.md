# Data Model: Visualizer Tabs (Feature 004)

Phase 1 of `/specs/004-visualizer-tabs/plan.md`. Documents the data
shapes the feature introduces or relies on, across the Processor's
analysis-JSON output and the Visualizer's in-memory state. The
project does not have a database; "data model" here means
JSON-on-disk schemas and in-page state.

## A. Analysis JSON additions (Processor output)

The Processor extends `players[].actions` with one new field. The
existing `apmTimeline` and `totals` fields are unchanged. No other
top-level additions or removals.

```jsonc
// players[i].actions  — superset of feature 002's shape
{
  "apmTimeline": {            // unchanged from feature 002
    "bucketWidthMs": 60000,
    "buckets": [95, 49, 66, ...]
  },
  "totals": {                 // unchanged from feature 002
    "rightclick": 723,
    "select": 267,
    "selecthotkey": 197,
    "basic": 33,
    "ability": 39,
    "buildtrain": 70,
    "assigngroup": 39,
    "item": 0,
    "removeunit": 0,
    "subgroup": 0,
    "esc": 0
  },
  "timedActions": [           // NEW in feature 004
    { "timeMs": 1230,  "category": "select" },
    { "timeMs": 1240,  "category": "rightclick" },
    { "timeMs": 1380,  "category": "buildtrain" },
    { "timeMs": 1450,  "category": "selecthotkey" },
    /* ... in chronological order, one record per per-player action */
  ]
}
```

### Field semantics

| Field | Type | Required | Semantics |
|---|---|---|---|
| `timedActions` | array | yes (may be empty) | Chronological per-player input-action stream extracted from the parser's `events[].commandBlocks[].actions[]` for that player. Empty array if the player issued no actions (e.g., observer mistakenly classed as player). |
| `timedActions[].timeMs` | integer | yes | In-game time in milliseconds at which the action occurred. Same time base and unit as every other timestamped field in the analysis JSON (`production[].timeMs`, `heroes[].abilityOrder[].timeMs`, `resourceTransfers[].timeMs`). |
| `timedActions[].category` | string | yes | One of the action categories already used by `actions.totals`: `assigngroup`, `rightclick`, `basic`, `buildtrain`, `ability`, `item`, `select`, `removeunit`, `subgroup`, `selecthotkey`, `esc`. The Visualizer treats `rightclick`, `select`, `selecthotkey`, `basic`, `assigngroup`, `subgroup` as **minor** events; `buildtrain`, `ability`, `item`, `removeunit`, `esc` as **major** events that complement the timestamped data already in `production[]`, `heroes[]`, `resourceTransfers[]`. |

### Invariants

- For every player and every category present in `actions.totals`,
  `count_of(timedActions, where category == c) == totals[c]`.
  This invariant is a free pytest assertion on both committed
  fixtures and is the primary correctness check for the new
  extractor.
- `timedActions` is sorted by `timeMs` non-decreasing.
- `timedActions[].timeMs` is bounded by `[0, match.duration]`.
- The `timedActions` field is **additive** to feature 002's
  contract: a consumer that does not know about the field (e.g.,
  the feature-003 visualizer) MUST continue to work unchanged.
  Backwards-compatibility is verified by re-running the existing
  feature-003 visualizer against a regenerated analysis JSON and
  observing identical Summary-equivalent rendering.

### What does **not** change

- `apmTimeline.bucketWidthMs` remains 60000 ms; the Visualizer's
  histogram does **not** consume `apmTimeline` (the new
  `timedActions` is the canonical source). `apmTimeline` is left
  in place because the analysis JSON is also a developer-facing
  artifact and the per-minute summary is independently useful.
- `actions.totals` are NOT recomputed from `timedActions` —
  they're still passed through from the parser's per-player
  counters. This is intentional: drift between the two would
  surface a parser/processor bug.
- All other top-level keys (`match`, `players[].heroes`,
  `players[].production`, `players[].resourceTransfers`,
  `players[].groupHotkeys`, `chat`, `observers`, `settings`,
  `diagnostics`, `map`) are untouched.

## B. Visualizer in-memory state

The Visualizer holds a single page-level state object initialised
to `null` and populated on file load.

```jsonc
// pageState
{
  "loadedFile": {
    "name": "base_1.w3g.analysis.json",     // for the file-name display in the header
    "loadedAt": 1746057600000               // wall-clock ms; only used to drive a "loaded just now" affordance
  },
  "analysis": <full parsed analysis JSON>,  // the validated Processor-output document
  "activeTab": "summary",                   // one of "summary" | "timelines" | "analysis" | "map"
  "zoomState": {                            // Timelines-tab-only; persists across tab switches within a session
    "visibleStartMs": 0,
    "visibleEndMs": <analysis.match.duration>
  }
}
```

### State transitions

| Trigger | State change |
|---|---|
| Page first opens | `pageState = null`. Tab strip MAY be hidden or visible-but-disabled. |
| User picks a valid analysis JSON | `pageState` populated; `activeTab = "summary"`; `zoomState = {0, match.duration}`. |
| User picks a malformed file | `pageState` left unchanged (or reset to `null` per feature 003's load-error flow); error surfaced; existing `pageState`, if any, MUST be cleared so no stale data renders (FR-009 of feature 003). |
| User clicks a tab | `pageState.activeTab = clicked`. Other state fields unchanged. |
| User adjusts Timelines zoom or pan | `pageState.zoomState` mutated. Re-render Timelines-tab content only. |
| User picks a different file mid-session | `pageState.loadedFile`, `analysis` replaced; `activeTab = "summary"` (per spec assumption); `zoomState` reset to full-match. |

### Derived data (computed lazily, not persisted on `pageState`)

- **Summary aggregations** (production, hero, transfers): pure
  functions over `pageState.analysis`. Recomputed on tab activation;
  not memoised in v1 (the cost is dominated by string-building, not
  arithmetic, and is bounded by the per-player entity counts).
- **Per-player histogram data**: a function `(player.timedActions +
  major events from production / heroes / resourceTransfers,
  zoomState, viewportPx) → { buckets: [{ start, end, counts: { ... }
  }] }`. Recomputed on Timelines-tab activation, on zoom change, and
  on viewport resize. Memoised by `(playerId, zoomVersion,
  viewportWidth)` if profiling shows the cost matters; not
  pre-memoised speculatively.

### Constraints

- `pageState` is the sole mutable store. No additional global
  variables, no event bus, no observer tree.
- The Visualizer NEVER mutates `pageState.analysis`. The analysis
  JSON is treated as immutable input data; aggregations are derived,
  not folded back in.
- The Visualizer NEVER reaches outside `pageState` for replay data
  (no fetch, no re-read of the file, no `localStorage`).

## C. UI-data-model facets per tab

Each tab's renderer is a pure function `(pageState) → DOM
fragment`. The facets each tab reads:

| Tab | Reads from `pageState.analysis` | Reads from `pageState` other |
|---|---|---|
| Summary | `match`, `players[].{name,color,race,raceDetected,apm,isWinner,teamId,actions.totals,groupHotkeys,heroes,production,resourceTransfers}`, `chat`, `observers` | (none) |
| Timelines | `match.duration`, `players[].{id,name,color,timedActions,production,heroes,resourceTransfers}` | `zoomState`, viewport width (read from DOM at render time) |
| Analysis (stub) | `match.id` (only to make the placeholder feel less abstract; optional) | (none) |
| Map (stub) | `map.path` or `map.name` (optional, same purpose) | (none) |

## D. Out of scope for this data model

- Persisted state across page reloads (`localStorage`, IndexedDB).
- Multi-replay state (comparison of two analyses in one session).
- Cross-session zoom or tab preference.
- Any schema for the future Analysis tab content (LLM-ready text)
  or Map tab content (per-action coordinate stream). Those are the
  scope of follow-up features.
