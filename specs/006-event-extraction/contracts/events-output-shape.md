# Contract: Events JSON Output Shape

This document is the spec-time snapshot of the events JSON document's
structural contract. The same content is mirrored at
`processor/EVENTS.md`, which travels with the code and is the
operative reference for downstream consumers (FR-029). The two stay
identical until the events shape changes; any future change MUST
update both in the same PR (FR-032).

## Top-level shape

```json
{
  "match":       { ... },           // §match
  "events":      [ ... ],           // §events — the flat chronological array
  "diagnostics": { ... }            // §diagnostics
}
```

Exactly three top-level keys. No version field is emitted in v1; if
the shape evolves incompatibly, future plans will introduce one.

## §match

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `parserId` | string | analyzer's `diagnostics.parserId` | Stable hex hash w3gjs derived from replay content. |
| `durationMs` | integer | analyzer's `match.durationMs` | In-game duration. |
| `players` | array | analyzer's `players[]` (subset) | One entry per non-observer player: `{ "id": int, "teamId": int, "name": string }`. |

## §events

A flat array of event objects, ordered by `startTimeMs` ascending,
ties broken by `(kind, sortedParticipantIds)` ascending.

### Common fields on every event

```json
{
  "id":              "<16 hex chars>",
  "kind":            "<one of the 13 kind labels>",
  "startTimeMs":     <integer>,
  "endTimeMs":       <integer, when applicable>,
  "participants":    [<integer player ids>],
  "inferenceLabel":  "<string>" | null,
  "thresholds":      { ... per-replay threshold values used },

  // ... per-kind fields (see below)
}
```

### Per-kind field tables

The kind tables below match `data-model.md`. Their union enumerates
the entire field surface of the events document.

#### `idlePeriod`

| Field | Type |
|---|---|
| `playerId` | integer |
| `durationMs` | integer |
| `thresholds.idleMinGapMs` | integer |

#### `buildingRebuild`

| Field | Type |
|---|---|
| `playerId` | integer |
| `entityId` | string |
| `entityName` | string |
| `original` | object `{ timeMs, x, y }` |
| `rebuild` | object `{ timeMs, x, y }` |
| `gapMs` | integer |
| `thresholds.rebuildBucketSize` | integer |

#### `techMilestone`

| Field | Type |
|---|---|
| `playerId` | integer |
| `milestone` | string ∈ `{tier2Hall, tier3Hall, altar, keyTechBuilding, majorUpgradeStart}` |
| `entityId` | string |
| `entityName` | string |

#### `expoPlacement`

| Field | Type |
|---|---|
| `playerId` | integer |
| `entityId` | string |
| `entityName` | string |
| `placement` | object `{ x, y }` |
| `home` | object `{ x, y }` |
| `homeRadius` | integer |
| `distanceFromHome` | integer |
| `thresholds.homeRadius` | integer |

#### `creepingDeparture`

| Field | Type |
|---|---|
| `playerId` | integer |
| `destinationCentroid` | object `{ x, y }` |
| `distanceFromHome` | integer |
| `actionCount` | integer |
| `thresholds.homeRadius` | integer |
| `thresholds.minDurationMs` | integer |

#### `towerRushCandidate` (`inferenceLabel = "towerRushCandidate"`)

| Field | Type |
|---|---|
| `playerId` | integer |
| `entityId` | string |
| `entityName` | string |
| `placement` | object `{ x, y }` |
| `distanceToOwnHome` | integer |
| `threatenedOpponentId` | integer |
| `distanceToThreatenedHome` | integer |
| `thresholds.homeRadius` | integer |

#### `baseIncursion` (`inferenceLabel = "baseIncursionCandidate"`)

| Field | Type |
|---|---|
| `playerId` | integer |
| `opponentId` | integer |
| `actionCount` | integer |
| `centroid` | object `{ x, y }` |
| `thresholds.opponentHomeRadius` | integer |

#### `allyZoneCreeping` (`inferenceLabel = "allyZoneCreepingCandidate"`)

| Field | Type |
|---|---|
| `playerId` | integer |
| `allyId` | integer |
| `actionCount` | integer |
| `centroid` | object `{ x, y }` |
| `thresholds.allyHomeRadius` | integer |
| `thresholds.minActionCount` | integer |

#### `jointEngagement` (`inferenceLabel = "jointEngagementCandidate"`)

| Field | Type |
|---|---|
| `playerIds` | array of integers |
| `centroid` | object `{ x, y }` |
| `actionCount` | integer |
| `perParticipantCounts` | object `{ playerId(string) → integer }` |
| `tightness` | number |
| `thresholds.engagementRadius` | integer |
| `thresholds.engagementTimeWindowSeconds` | integer |

#### `heroTeleport`

| Field | Type |
|---|---|
| `playerId` | integer |
| `itemId` | string |
| `itemName` | string |
| `originPosition` | object `{ x, y }` \| null |
| `heroId` | string \| null |
| `attributionNote` | string \| null |

#### `productionStall`

| Field | Type |
|---|---|
| `playerId` | integer |
| `durationMs` | integer |
| `inputRateDuringStall` | number |
| `thresholds.productionStallMinGapMs` | integer |

#### `intensityPeak` (`inferenceLabel = "intensityPeakCandidate"`)

| Field | Type |
|---|---|
| `scope` | string ∈ `{"all", "team:<teamId>"}` |
| `peakValue` | number |
| `baseline` | object `{ mean: number, std: number }` |
| `thresholds.windowSeconds` | integer |
| `thresholds.peakSigma` | number |

#### `resourceTransfer`

| Field | Type |
|---|---|
| `senderId` | integer |
| `receiverId` | integer |
| `count` | integer |
| `totalGold` | integer |
| `totalLumber` | integer |
| `thresholds.burstGapMs` | integer |

## §diagnostics

Mirrors the analyzer's `diagnostics` pattern.

| Field | Type | Meaning |
|---|---|---|
| `extractorVersion` | string | Semver of `extract_events.py`. |
| `parserId` | string | Forwarded from the analyzer's `diagnostics.parserId`. |
| `players` | object `{ playerId(string) → { homeDerivation, homeRadiusDerivation } }` | Per-player home derivation method record. Values: `"primary"` or `"fallback:<rule>"`. |
| `thresholds` | object | Per-replay threshold values: `mapActiveDiagonal`, `engagementRadius`, `idleMinGapMs`, `productionStallMinGapMs`, `transferBurstGapMs`. |
| `eventCounts` | object `{ kind(string) → integer }` | Per-kind event counts. Sums to `len(events)`. |

## Determinism

The events document is **byte-identical** across re-runs against the
same analyzer-output input (FR-035 / SC-006). The extractor does not
embed wall-clock time; the only time-derived data is in-game time
from the underlying replay.

## What the document does NOT contain

- No outcome vocabulary (FR-026): no `killed`, `destroyed`, `stole`,
  `won` as factual labels.
- No raw timed-action stream (it lives in the analyzer output and is
  not duplicated here).
- No production-order list (same — analyzer output).
- No chat messages (same — analyzer output).
- No coordinate transformation (same map units as the analyzer).

If a consumer needs any of the above, they fetch the sibling
`*.analysis.json`. The `match.parserId` field in this document
matches the `diagnostics.parserId` of that document, allowing safe
cross-document referencing.

## What about events the extractor decided not to emit?

The extractor does not emit "candidate-but-rejected" events. If a
spatial cluster failed the `min_samples` test or the inference
hedging said no, the event simply does not appear in the document.
The diagnostics block's `eventCounts` lists what *was* emitted; it
does not list what was considered.

## Version evolution

Future spec revisions MAY add new event kinds, add fields to existing
event kinds, add fields to `diagnostics`, or extend the per-kind
threshold list. Removing a kind, removing a field, or changing a
field's type is a breaking change and would warrant a `version` field
on the document root (deferred until first needed).
