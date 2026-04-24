# Phase 1 Data Model — Replay Analyzer

This document enumerates the entities the analyzer reads, the
entities it emits, and the relationships between them. It is the
engineering-level counterpart to `spec.md`'s Key Entities section
and the detailed source for the output-shape contract in
`contracts/output-shape.md`.

## Inputs

### ParserOutput (read-only)

The JSON document produced by `parser/parse.js`, defined by
`parser/DATA.md`. The analyzer reads this document verbatim; it never
modifies or re-derives its fields. Notable source fields used by the
analyzer:

| Source field | Used for |
|---|---|
| `version`, `buildNumber`, `duration`, `gamename`, `creator`, `expansion` | Match-level metadata in the analysis output |
| `map.*` | Map metadata section |
| `matchup`, `type`, `startSpots`, `randomseed` | Match-level metadata |
| `settings.*` | Lobby-settings section |
| `winningTeamId` | Winner attribution |
| `observers` | Observers section |
| `players[]` with their `id`, `name`, `teamid`, `color`, `race`, `raceDetected`, `apm`, `groupHotkeys`, `actions`, `heroes`, `buildings`, `units`, `upgrades`, `items`, `resourceTransfers` | Per-player analysis entries |
| `apm.trackingInterval` | APM bucket width metadata |
| `chat[]` | Chat section |
| `parseTime`, `id` | Diagnostics section pass-through |
| `events[]` | NOT used for v1. The top-level aggregated fields above cover everything the visualizer needs; `events[]` is retained by the Parser for later features (e.g., action heatmaps, command-level replays) and is explicitly ignored by the Analyzer in this iteration. Out-of-scope per the spec's metric boundary. |

### EntityNamesMapping (read-only)

`processor/entity_names.json` — a flat object whose keys are 4-char
Warcraft III entity IDs and whose values are human-readable English
display names.

```text
{
  "Nfir": "Firelord",
  "hpea": "Peasant",
  "hkee": "Keep",
  "Rhme": "Swords",
  "bspd": "Boots of Speed",
  "AHbz": "Blizzard",
  ...
}
```

Validation rules:

- Every key MUST be a string of exactly 4 ASCII alphanumerics.
- Every value MUST be a non-empty string.
- No key appears twice (enforced by JSON object semantics).
- The ID namespace is flat — an ability ID (e.g., `AHbz`) and a unit
  ID (e.g., `hpea`) share one map. Conflict-free in practice because
  w3gjs's ID conventions use different leading characters per
  category.

## Outputs

### AnalysisDocument (root entity)

A single JSON object per replay, written to
`<input-path-without-.json>.analysis.json`. Top-level keys (final
list captured in `contracts/output-shape.md`):

| Key | Type | Meaning |
|---|---|---|
| `match` | object | Match-level metadata (MatchMetadata) |
| `settings` | object | Lobby settings (LobbySettings), forwarded from parser |
| `map` | object | Map metadata (MapInfo), forwarded from parser |
| `players` | array of PlayerAnalysis | One entry per non-observer slot, in slot-order |
| `observers` | array of string | Observer names, forwarded from parser |
| `chat` | array of ChatMessage | Chat messages, each with a human-readable channel label |
| `diagnostics` | object | Parser/analyzer diagnostics (Diagnostics) |

### MatchMetadata

| Field | Type | Source | Notes |
|---|---|---|---|
| `version` | string | `ParserOutput.version` | e.g. `"2.00"` |
| `buildNumber` | number | `ParserOutput.buildNumber` | |
| `durationMs` | number | `ParserOutput.duration` | In-game ms |
| `gameType` | string | `ParserOutput.type` | e.g. `"4on4"` |
| `matchup` | string | `ParserOutput.matchup` | e.g. `"HHNUvHHOO"` |
| `startSpots` | number | `ParserOutput.startSpots` | |
| `expansion` | boolean | `ParserOutput.expansion` | |
| `gameName` | string | `ParserOutput.gamename` | |
| `creator` | string | `ParserOutput.creator` | |
| `randomSeed` | number | `ParserOutput.randomseed` | |
| `winner` | object \| null | `ParserOutput.winningTeamId` | `{ "teamId": n }` when determined, `null` when parser returned `-1` |

### LobbySettings

Forwarded verbatim from `ParserOutput.settings`. The analyzer does
not reshape boolean flags; the Visualizer renders each as-is. Keys
listed in `parser/DATA.md §settings`.

### MapInfo

Forwarded verbatim from `ParserOutput.map` (`path`, `file`,
`checksum`, `checksumSha1`).

### PlayerAnalysis

One per non-observer slot. Fields:

| Field | Type | Source | Notes |
|---|---|---|---|
| `id` | number | `ParserOutput.players[].id` | |
| `name` | string | `...name` | |
| `teamId` | number | `...teamid` | |
| `color` | string | `...color` | `#rrggbb` |
| `race` | string | `...race` | `"H"`, `"O"`, `"U"`, `"N"`, `"R"` |
| `raceDetected` | string | `...raceDetected` | |
| `apm` | number | `...apm` | |
| `isWinner` | boolean | derived | `true` iff `teamId === match.winner.teamId` |
| `actions` | object | `...actions` | ActionCounts |
| `groupHotkeys` | object | `...groupHotkeys` | Forwarded |
| `heroes` | array of HeroEntry | `...heroes` | |
| `production` | object | derived | ProductionSection (see below) |
| `resourceTransfers` | array of ResourceTransfer | `...resourceTransfers` | |

### ActionCounts

| Field | Type | Source |
|---|---|---|
| `apmTimeline` | object | `{ bucketWidthMs: ParserOutput.apm.trackingInterval, buckets: ParserOutput.players[].actions.timed }` |
| `totals` | object | Copy of `ParserOutput.players[].actions` MINUS the `timed` array — `assigngroup`, `rightclick`, `basic`, `buildtrain`, `ability`, `item`, `select`, `removeunit`, `subgroup`, `selecthotkey`, `esc` |

### ProductionSection

One object per player, consolidating the four parser sections
(`buildings`, `units`, `upgrades`, `items`) into a shape that keeps
the build chronology first-class and the aggregate summary
secondary. For each category `C` in `{ buildings, units, upgrades,
items }`:

```text
production.<C>.order[i]   = {
  "id":    "<4-char wc3 id>",
  "name":  "<display name or raw id>",
  "unknown": false,          # true when id is not in the mapping
  "timeMs": <in-game ms>
}
production.<C>.summary[id] = {
  "id":      "<id>",
  "name":    "<display name or raw id>",
  "unknown": false,
  "count":   <total>
}
```

Order preserves the parser's chronological sequence. Summary is an
object keyed by ID (not a deduplicated list) so the Visualizer can
render either a per-ID aggregate or a type-grouped roll-up.

### HeroEntry

```text
{
  "id":         "<hero 4-char id>",
  "name":       "<Firelord | Archmage | ...>",
  "unknown":    false,
  "level":      <library-inferred final level>,
  "abilityOrder": [
    {
      "id":     "<ability id>",
      "name":   "<Blizzard | ...>",
      "unknown": false,
      "timeMs": <in-game ms>,
      "level":  <ordinal: the 1st/2nd/3rd/... learn of this ability>
    },
    ...
  ],
  "abilitySummary": {
    "<ability id>": {
      "id":      "<ability id>",
      "name":    "<name>",
      "unknown": false,
      "level":   <final learned level>
    },
    ...
  }
}
```

Rationale for shape:

- `abilityOrder` is a chronological sequence (matching the Parser's
  `abilityOrder` array) with a derived `level` ordinal that lets the
  Visualizer draw "skill build" ladders without re-counting.
- `abilitySummary` flattens Parser's `abilities` (ID → count) into a
  name-annotated map using the same shape as ProductionSection's
  `summary`, for consistency.

### ResourceTransfer

| Field | Type | Source |
|---|---|---|
| `fromSlot` | number | `...resourceTransfers[].slot` (sender) |
| `toPlayerId` | number | `...playerId` |
| `toPlayerName` | string | `...playerName` |
| `gold` | number | `...gold` |
| `lumber` | number | `...lumber` |
| `timeMs` | number | `...msElapsed` |

### ChatMessage

| Field | Type | Source |
|---|---|---|
| `playerId` | number | `ParserOutput.chat[].playerId` |
| `playerName` | string | `...playerName` |
| `mode` | string | `...mode` |
| `text` | string | `...message` |
| `timeMs` | number | `...timeMS` |

### Diagnostics

```text
{
  "parserId":           "<ParserOutput.id hex hash>",
  "parserParseTimeMs":  <ParserOutput.parseTime>,
  "unmappedEntityIds": [
    { "category": "building", "id": "hfxx" },
    { "category": "ability",  "id": "AXyz" },
    ...
  ],
  "analyzerVersion":    "<semver string tied to processor/pyproject.toml>"
}
```

`unmappedEntityIds` is emitted only if the run encountered unmapped
IDs (empty array otherwise) and is deduplicated by `(category, id)`.
`analyzerVersion` is sourced from `pyproject.toml`'s `[project]
version` so that downstream tooling can correlate output shape with
analyzer revision.

## Derived-field rules

- `PlayerAnalysis.isWinner`: `true` iff `match.winner` is non-null
  AND `match.winner.teamId === player.teamId`; `false` otherwise.
- `ProductionSection.*.order[i].name`, `summary[id].name`,
  `HeroEntry.name`, `HeroEntry.abilityOrder[i].name`: looked up
  from `entity_names.json`; fall back to the raw ID with
  `unknown: true` set, per R7.
- `HeroEntry.abilityOrder[i].level` ordinal: `1` for the first
  occurrence of that ability ID in the sequence, `2` for the next,
  etc.

## Validation rules surfaced in tests

These are the invariants the test suite enforces against both
committed fixtures. They drive `processor/tests/test_analyze.py`.

1. Top-level keys are exactly `{ match, settings, map, players,
   observers, chat, diagnostics }`.
2. `match.durationMs >= 0`.
3. Every `players[].race` ∈ `{ "H", "O", "U", "N", "R" }`; every
   `players[].raceDetected` ∈ `{ "H", "O", "U", "N" }` (random is
   resolved).
4. `players[].isWinner === true` for exactly one team iff
   `match.winner` is non-null; zero otherwise.
5. Every entity-ID occurrence (hero, non-hero unit, building,
   upgrade, item, hero ability) in the analysis output for the
   committed fixtures resolves to a name with `unknown: false` —
   SC-002.
6. `diagnostics.unmappedEntityIds` is empty for both committed
   fixtures — SC-002 corollary.
7. Re-running the analyzer on the same input produces byte-identical
   output EXCEPT for `diagnostics.parserParseTimeMs` — SC-007.
8. For `base_2.w3g.json` (no chat), `chat` is `[]` and not missing.
9. For `base_1.w3g.json` (chat present), `chat` has 81 entries and
   each has a non-empty `text`.

## State transitions

None. The analyzer is a pure function: `ParserOutput ×
EntityNamesMapping → AnalysisDocument`. No persistent state beyond
the output file it writes.

## Relationships diagram (text form)

```text
ParserOutput ──────────────────────┐
                                   │
EntityNamesMapping ──────┐          │
                         ▼          ▼
                   processor/analyze.py
                         │          │
                         ▼          ▼
                   AnalysisDocument   stderr diagnostics
                        │
                        ▼
                   Visualizer layer
                   (future feature;
                    reads Analysis
                    + optionally the
                    same mapping)
```

## Scope exclusions (data model)

The data model explicitly omits:

- Event-level action streams (`ParserOutput.events`). The processor
  emits no event-level data in v1. Adding an "action heatmap" or
  "command timeline" metric is a later feature and MUST remain a
  Processor-layer change — no parser or mapping edit required,
  per SC-005.
- Derived win inference. `match.winner` is a pass-through of the
  Parser's `winningTeamId`; the analyzer does not second-guess it.
- Preformatted display strings (time in `mm:ss`, resource totals
  with thousands separators, rank/MMR labels). The Visualizer owns
  all display formatting (R8).
