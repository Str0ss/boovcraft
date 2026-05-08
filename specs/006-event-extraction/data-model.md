# Phase 1 Data Model: Event Extraction

This document catalogs the entities introduced or modified by feature
006. Each entry describes the entity's fields, types, origin (where
the data comes from), and any derivation rule that's not implicit in
the field name.

The contracts under `contracts/` are the on-disk shapes that consume
or produce these entities; this file is the conceptual model that
those contracts implement.

## Entities modified in the analyzer output (`*.analysis.json`)

### Coordinate-bearing timed action

An entry in `players[].actions.timedActions[]` (existing per
`processor/DATA.md §players.actions`) gains two new optional fields.

| Field | Type | Required | Origin | Meaning |
|---|---|---|---|---|
| `timeMs` | integer | yes | unchanged | In-game time of the action. (existing) |
| `category` | string | yes | unchanged | Action category. (existing) |
| `x` | integer | when underlying replay action carried a position | parser-output's `events[].commandBlocks[].actions[].position.x` for w3gjs action ids `0x11`/`0x12`/`0x13`/`0x14` | Map x-coordinate of the action target. |
| `y` | integer | when underlying replay action carried a position | parser-output's `events[].commandBlocks[].actions[].position.y` | Map y-coordinate of the action target. |

Entries from coordinate-less actions (selection, hotkey assignment,
escape, etc.) are emitted **without** the `x`/`y` fields, not with
null sentinels.

### Coordinate-bearing production-order entry

An entry in
`players[].production.{buildings,units,upgrades,items}.order[]` gains
the same two optional fields. In practice, building placements
(`0x11`/`0x12`) carry positions; unit-train and research actions
(typically `0x10`) do not.

| Field | Type | Required | Origin | Meaning |
|---|---|---|---|---|
| `id` | string | yes | unchanged | 4-char entity id. (existing) |
| `name` | string | yes | unchanged | Display name. (existing) |
| `unknown` | boolean | yes | unchanged | Mapping-status flag. (existing) |
| `timeMs` | integer | yes | unchanged | In-game time of placement. (existing) |
| `x` | integer | when underlying replay action carried a position | parser-output (same as above) | Map x-coordinate of the placement. |
| `y` | integer | when underlying replay action carried a position | parser-output | Map y-coordinate of the placement. |

## Entities introduced by the events stage (`*.events.json`)

### Document root

The events document is a JSON object with these top-level keys:

| Key | Type | Required | Meaning |
|---|---|---|---|
| `match` | object | yes | Match identification (parser id, durationMs, players[].id+teamId). Sufficient to identify the replay without re-opening the analyzer output (FR-009). |
| `events` | array | yes | The flat chronological event array. |
| `diagnostics` | object | yes | Per-replay extractor state and tooling metadata. |

### `match` block

| Field | Type | Origin | Meaning |
|---|---|---|---|
| `parserId` | string | analyzer's `diagnostics.parserId` | Stable hex hash w3gjs derived from replay content. Identifies the replay across re-extractions. |
| `durationMs` | integer | analyzer's `match.durationMs` | In-game duration. |
| `players` | array of `{ id: integer, teamId: integer, name: string }` | analyzer's `players[]` (subset) | Just enough player metadata that an event's `playerId` reference is meaningful without opening the analyzer. |

### `events` array

A flat chronological array of event objects. Order: by `startTimeMs`
ascending; ties broken by `(kind, sortedParticipantIds)` ascending
(deterministic, documented in EVENTS.md per FR-009).

#### Common fields on every event

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string (16 hex chars) | yes | Stable content-derived identifier. Derivation rule R11. |
| `kind` | string | yes | Discriminator. One of the 13 kind labels below. |
| `startTimeMs` | integer | yes | In-game start time. |
| `endTimeMs` | integer | when the kind has a non-instant span | In-game end time. |
| `participants` | array of integers | yes | Player ids the event concerns. Length 1 for single-player kinds, ≥ 2 for multi-player kinds. |
| `inferenceLabel` | string \| null | yes | `null` for factual kinds (idle, rebuild, milestone, transfer, expo, creeping, hero TP, production stall). For inferred kinds, one of: `"towerRushCandidate"`, `"baseIncursionCandidate"`, `"allyZoneCreepingCandidate"`, `"jointEngagementCandidate"`, `"intensityPeakCandidate"`. (FR-023) |
| `thresholds` | object | when the kind depended on a per-replay threshold | The per-replay threshold values as actually used for this event. (FR-024) |

Plus per-kind fields documented under the kind's entry below.

#### Per-kind fields

##### `idlePeriod` (FR-010)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The idle player. (Also in `participants`.) |
| `durationMs` | integer | `endTimeMs - startTimeMs`. |
| `thresholds.idleMinGapMs` | integer | The 15 000 ms minimum (R5). |

##### `buildingRebuild` (FR-011)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The placing player. |
| `entityId` | string | The 4-char building entity id. |
| `entityName` | string | Display name. |
| `original` | object `{ timeMs, x, y }` | The first placement. |
| `rebuild` | object `{ timeMs, x, y }` | The colocated re-placement. |
| `gapMs` | integer | `rebuild.timeMs - original.timeMs`. |
| `thresholds.rebuildBucketSize` | integer | The spatial bucket size in map units used to deem the two placements colocated (R3-derived). |

`startTimeMs` = `rebuild.timeMs`. `endTimeMs` is omitted (instant).

##### `techMilestone` (FR-012)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The player who reached the milestone. |
| `milestone` | string | One of: `tier2Hall`, `tier3Hall`, `altar`, `keyTechBuilding`, `majorUpgradeStart`. |
| `entityId` | string | The 4-char id of the building/upgrade that triggered the milestone. |
| `entityName` | string | Display name. |

`startTimeMs` = the milestone's in-game time. `endTimeMs` omitted.
No `thresholds` (the catalog itself is the rule, not a numeric threshold).

##### `expoPlacement` (FR-013)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The placing player. |
| `entityId` | string | The 4-char hall id. |
| `entityName` | string | Display name. |
| `placement` | object `{ x, y }` | The expo coordinate. |
| `home` | object `{ x, y }` | The placer's home (R2). |
| `homeRadius` | integer | The placer's home radius (R3). |
| `distanceFromHome` | integer | Euclidean distance. |
| `thresholds.homeRadius` | integer | Same as `homeRadius`, surfaced under the threshold convention. |

##### `creepingDeparture` (FR-014)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The departing player. |
| `destinationCentroid` | object `{ x, y }` | Centroid of clustered actions during the departure. |
| `distanceFromHome` | integer | Distance from home to destination centroid. |
| `actionCount` | integer | Number of actions clustered into the departure. |
| `thresholds.homeRadius` | integer | The home radius the centroid had to cross. |
| `thresholds.minDurationMs` | integer | Minimum duration the player had to stay outside home for the departure to register. |

##### `towerRushCandidate` (FR-015)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The placing player. |
| `entityId` | string | Tower's 4-char id (R7 catalog). |
| `entityName` | string | Display name. |
| `placement` | object `{ x, y }` | Placement coordinate. |
| `distanceToOwnHome` | integer | Distance from placer's home to placement. |
| `threatenedOpponentId` | integer | Opponent whose home is closest. |
| `distanceToThreatenedHome` | integer | Distance from threatened opponent's home to placement. |
| `thresholds.homeRadius` | integer | The placer's home radius. |

`inferenceLabel` = `"towerRushCandidate"`.

##### `baseIncursion` (FR-016)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The intruding player. |
| `opponentId` | integer | The opponent whose base was entered. |
| `actionCount` | integer | Actions inside the opponent's home radius. |
| `centroid` | object `{ x, y }` | Centroid of the in-base actions. |
| `thresholds.opponentHomeRadius` | integer | The radius that defined "inside". |

`inferenceLabel` = `"baseIncursionCandidate"`.

##### `allyZoneCreeping` (FR-017)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The player whose actions fell in the ally zone. |
| `allyId` | integer | The ally whose zone was entered. |
| `actionCount` | integer | Actions inside the ally's zone band but outside the player's own band. |
| `centroid` | object `{ x, y }` | Centroid of those actions. |
| `thresholds.allyHomeRadius` | integer | The ally's home radius. |
| `thresholds.minActionCount` | integer | The minimum action density that qualified the span. |

`inferenceLabel` = `"allyZoneCreepingCandidate"`.

##### `jointEngagement` (FR-018)

| Field | Type | Meaning |
|---|---|---|
| `playerIds` | array of integers | The participating teammates. (Also in `participants`.) |
| `centroid` | object `{ x, y }` | Spatial centroid of the cluster. |
| `actionCount` | integer | Total clustered actions. |
| `perParticipantCounts` | object `{ playerId → integer }` | Per-player action contribution. |
| `tightness` | number | Cluster's mean intra-cluster distance, in map units. |
| `thresholds.engagementRadius` | integer | DBSCAN ε (R4). |
| `thresholds.engagementTimeWindowSeconds` | integer | The 5 s time window (R4). |

`inferenceLabel` = `"jointEngagementCandidate"`.

##### `heroTeleport` (FR-019)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The casting player. |
| `itemId` | string | The 4-char teleport-item id. |
| `itemName` | string | Display name. |
| `originPosition` | object `{ x, y }` \| null | Coordinate from which the TP was cast (when carried by the underlying action). |
| `heroId` | string \| null | The casting hero's 4-char id, when attribution is unambiguous. |
| `attributionNote` | string \| null | Reason hero attribution was omitted, when applicable. |

##### `productionStall` (FR-020)

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The stalled player. |
| `durationMs` | integer | `endTimeMs - startTimeMs`. |
| `inputRateDuringStall` | number | Player's actions-per-minute during the stall (timed actions only). |
| `thresholds.productionStallMinGapMs` | integer | The 45 000 ms minimum (R5). |

##### `intensityPeak` (FR-021)

| Field | Type | Meaning |
|---|---|---|
| `scope` | string | `"all"` or `"team:<teamId>"`. |
| `peakValue` | number | The rolling-sum value at the peak. |
| `baseline` | object `{ mean, std }` | Baseline statistics over the full game. |
| `participants` | array of integers | The team's player ids (or all players for `scope="all"`). |
| `thresholds.windowSeconds` | integer | The 30 s rolling window (R10). |
| `thresholds.peakSigma` | number | The 2.0 σ threshold (R10). |

`inferenceLabel` = `"intensityPeakCandidate"`. `endTimeMs` omitted
(peaks are instant local maxima).

##### `resourceTransfer` (FR-022)

A singleton transfer is one event; consecutive same-pair transfers
within the burst gap are merged.

| Field | Type | Meaning |
|---|---|---|
| `senderId` | integer | The sending player's id. |
| `receiverId` | integer | The receiving player's id. |
| `count` | integer | Number of transfers in the burst (≥ 1). |
| `totalGold` | integer | Sum of gold across the burst. |
| `totalLumber` | integer | Sum of lumber across the burst. |
| `thresholds.burstGapMs` | integer | The 30 000 ms threshold (R6). |

`startTimeMs` = first transfer's time. `endTimeMs` = last transfer's
time when `count > 1`; omitted when `count == 1`. Participants =
`[senderId, receiverId]`.

### `diagnostics` block

Mirrors the analyzer's `diagnostics` pattern (FR-009).

| Field | Type | Meaning |
|---|---|---|
| `extractorVersion` | string | Semver of `extract_events.py` at the time of the run. |
| `parserId` | string | Forwarded from the analyzer's `diagnostics.parserId`. |
| `players` | object `{ playerId → { homeDerivation, homeRadiusDerivation } }` | Per-player home derivation method record (R2/R3 fallback rules). Values are `"primary"` or `"fallback:<rule>"`. |
| `thresholds` | object | The per-replay threshold values used: `mapActiveDiagonal`, `engagementRadius`, `idleMinGapMs`, `productionStallMinGapMs`, `transferBurstGapMs`, etc. |
| `eventCounts` | object `{ kind → integer }` | Per-kind event counts. Sums to `len(events)`. |

## Per-replay derived values (computed inside `extract_events.py`, not on disk except in `diagnostics`)

| Value | Symbol | Source |
|---|---|---|
| Map active region bounding box | `(minX, maxX, minY, maxY)` | Min/max of all coordinate-bearing actions across all players in the replay. |
| Map active diagonal | `mapActiveDiagonal` | `sqrt((maxX-minX)² + (maxY-minY)²)`. |
| Player home (per-player) | `home[playerId]` | R2 derivation. |
| Player home radius (per-player) | `homeRadius[playerId]` | R3 derivation. |
| Engagement radius (single value) | `engagementRadius` | `0.05 × mapActiveDiagonal` (R4). |
| Rebuild bucket size | `rebuildBucketSize` | `0.01 × mapActiveDiagonal`, capped to 1/30 of the smallest player's home radius (R-finalized at impl). |
| Engagement time-scale | `engagementScale` | `engagementRadius / engagementTimeWindowSeconds` (R4). |
