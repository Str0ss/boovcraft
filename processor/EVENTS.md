# Events Output Data Structure

This document describes the JSON document produced by
`processor/extract_events.py` when run against an analyzer-output
JSON file. It is the contract between the events-extraction stage of
the Processor layer and any downstream consumer (LLM-prompting
harness, future Visualizer "Story" tab, sanity-check script).

See also:
- `parser/DATA.md` — the Parser layer's output (one stage upstream).
- `processor/DATA.md` — the analyzer's output (this stage's input).
- `specs/006-event-extraction/contracts/events-output-shape.md` —
  spec-time snapshot of the same contract.
- `specs/006-event-extraction/data-model.md` — the conceptual data
  model behind these fields.

## Scope of this stage

The events extractor reads one analyzer-output file and emits one
events JSON document next to it. It does not re-parse the original
`.w3g` file, does not load the parser-output JSON, does not invoke
`node` or `w3gjs`, and does not modify its input.

## Output location

Running `python processor/extract_events.py <path>/<name>.w3g.analysis.json`
writes the JSON document to `<path>/<name>.w3g.events.json`. Other
suffix shapes are handled per
`specs/006-event-extraction/contracts/extract-events-cli.md §Output`.

## Limitations and hedging

The extractor sees only player input — what each player clicked,
what each player queued for production, what each player typed in
chat, and what resources each player transferred. **It does not
observe**:

- Unit deaths, hero deaths, or building destruction.
- Gold, lumber, or food balances.
- Fog of war, vision, or what either side could see.
- Build completion (a building queued may have been cancelled).
- Combat outcomes — who won a fight, what units died, which side
  retreated first.

Five of the thirteen event kinds depend on inference around those
gaps. Each carries an explicit `inferenceLabel` on the event itself:

| Kind | `inferenceLabel` | What is inferred |
|---|---|---|
| `towerRushCandidate` | `towerRushCandidate` | A tower placement near an opponent's home is *consistent with* a tower rush — but we do not observe whether the building completed. |
| `baseIncursion` | `baseIncursionCandidate` | A run of clicks inside an opponent's home circle — but we do not observe whether anything was attacked or destroyed. |
| `allyZoneCreeping` | `allyZoneCreepingCandidate` | A run of clicks inside an ally's zone — *consistent with* stealing creep, but we do not observe creep camps or who got the kill. |
| `jointEngagement` | `jointEngagementCandidate` | A spatial-temporal cluster of clicks from teammates — *consistent with* a joint fight, but we do not observe combat. |
| `intensityPeak` | `intensityPeakCandidate` | A local maximum in the team or all-player APM curve — *consistent with* a fight, but we do not observe what's happening. |

The other eight kinds (`idlePeriod`, `buildingRebuild`, `techMilestone`,
`expoPlacement`, `creepingDeparture`, `heroTeleport`, `productionStall`,
`resourceTransfer`) report observed player input directly and have
`inferenceLabel: null`.

The events document MUST NOT use outcome vocabulary the data does not
support. Words like `killed`, `destroyed`, `stole`, and `won` MUST
NOT appear as factual claims (FR-026 / SC-008).

## Top-level shape

The root is a JSON object with exactly three keys:

| Key | Type | Meaning |
|---|---|---|
| `match` | object | Match-level metadata. See §match. |
| `events` | array | The flat chronological event array. See §events. |
| `diagnostics` | object | Per-replay extractor state and tooling metadata. See §diagnostics. |

No top-level `version` field is emitted in v1. Future incompatible
shape changes (kind removal, field removal, type changes) would
introduce one; additive changes (new kinds, new fields) do not.

## §match

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `parserId` | string | `analysis.diagnostics.parserId` | Stable hex hash w3gjs derived from replay content. Identifies the replay across re-extractions. |
| `durationMs` | integer | `analysis.match.durationMs` | In-game duration in milliseconds. |
| `players` | array | `analysis.players[]` (subset) | One entry per non-observer player. Each entry: `{ id: integer, teamId: integer, name: string }`. |

## §events

A flat array of event objects, ordered by `startTimeMs` ascending,
ties broken by `(kind, sortedParticipantIds)` ascending.

### Common fields on every event

| Field | Type | Required | Meaning |
|---|---|---|---|
| `id` | string (16 hex chars) | yes | Stable content-derived identifier. See §Stable id derivation. |
| `kind` | string | yes | Discriminator. One of the 13 kind labels below. |
| `startTimeMs` | integer | yes | In-game start time. |
| `endTimeMs` | integer | when the kind has a non-instant span | In-game end time. |
| `participants` | array of integers | yes | Player ids the event concerns. |
| `inferenceLabel` | string \| null | yes | `null` for factual kinds; one of the five inference-candidate labels for inferred kinds. See §Limitations and hedging. |
| `thresholds` | object | always present (may be empty) | Per-replay threshold values used for this event. |

Plus per-kind fields, documented below.

### Per-kind field tables

#### `idlePeriod` (FR-010)

A continuous span during which a single player issued no input.
Observable. `inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The idle player. |
| `durationMs` | integer | `endTimeMs - startTimeMs`. |
| `thresholds.idleMinGapMs` | integer | The 15 000 ms minimum (research §R5). |

#### `buildingRebuild` (FR-011)

A second placement of the same building entity by the same player at
approximately the same coordinate. Observable.
`inferenceLabel = null`. Note: we do **not** claim the original was
destroyed — only that the player re-placed at the same spot.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The placing player. |
| `entityId` | string | 4-char building entity id. |
| `entityName` | string | Display name. |
| `original` | object `{ timeMs, x, y }` | The first placement. |
| `rebuild` | object `{ timeMs, x, y }` | The colocated re-placement. |
| `gapMs` | integer | `rebuild.timeMs - original.timeMs`. |
| `thresholds.rebuildBucketSize` | integer | Spatial bucket size used to deem the two placements colocated. |

In-place upgrades (Keep, Castle, Stronghold, Fortress, Halls of the
Dead, Black Citadel, Tree of Ages, Tree of Eternity, upgraded
towers) are excluded from the rebuild detector — those are
transformations, not placements.

#### `techMilestone` (FR-012)

First-occurrence-per-player marker for a strategic phase change.
Observable. `inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The player who reached the milestone. |
| `milestone` | string ∈ `{tier2Hall, tier3Hall, altar, keyTechBuilding, majorUpgradeStart}` | The milestone label. |
| `entityId` | string | 4-char id of the building/upgrade that triggered the milestone. |
| `entityName` | string | Display name. |

#### `expoPlacement` (FR-013)

A main-hall placement at a coordinate beyond the placer's home
radius. Observable. `inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The placing player. |
| `entityId` | string | 4-char hall id. |
| `entityName` | string | Display name. |
| `placement` | object `{ x, y }` | Expo coordinate. |
| `home` | object `{ x, y }` | The placer's home (per-replay derivation). |
| `homeRadius` | integer | The placer's home radius (per-replay derivation). |
| `distanceFromHome` | integer | Euclidean distance. |
| `thresholds.homeRadius` | integer | Same as `homeRadius`, surfaced under the threshold convention. |

#### `creepingDeparture` (FR-014)

A sustained excursion of a player's coord-bearing actions outside
their home radius. Observable; the *purpose* (creeping vs scouting
vs harassment) is not inferred. `inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The departing player. |
| `destinationCentroid` | object `{ x, y }` | Centroid of the run's clicks. |
| `distanceFromHome` | integer | Distance from home to centroid. |
| `actionCount` | integer | Number of actions in the run. |
| `thresholds.homeRadius` | integer | The home radius the centroid had to cross. |
| `thresholds.minDurationMs` | integer | Minimum sustained duration (20 000 ms). |

#### `towerRushCandidate` (FR-015)

A tower placement closer to an opponent's home than to the placer's
own home. **Inference**: this is *consistent with* a tower rush —
we do not observe whether the building completed.
`inferenceLabel = "towerRushCandidate"`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The placing player. |
| `entityId` | string | 4-char tower id (see Catalog: towers). |
| `entityName` | string | Display name. |
| `placement` | object `{ x, y }` | Placement coordinate. |
| `distanceToOwnHome` | integer | Distance from placer's home. |
| `threatenedOpponentId` | integer | Opponent whose home is nearest. |
| `distanceToThreatenedHome` | integer | Distance from threatened opponent's home. |
| `thresholds.homeRadius` | integer | The placer's home radius. |

#### `baseIncursion` (FR-016)

A run of action coordinates inside an opponent's home circle.
**Inference**: *consistent with* an attack on the opponent's base —
we do not observe combat. `inferenceLabel = "baseIncursionCandidate"`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The intruding player. |
| `opponentId` | integer | Opponent whose base was entered. |
| `actionCount` | integer | Actions inside the opponent's radius. |
| `centroid` | object `{ x, y }` | Centroid of the in-base actions. |
| `thresholds.opponentHomeRadius` | integer | Radius that defined "inside". |

#### `allyZoneCreeping` (FR-017)

A run of action coordinates inside an ally's home-radius band but
outside the player's own band, with action density ≥ the documented
minimum. **Inference**: *consistent with* the player creeping in the
ally's zone (potentially "stealing" the ally's creep) — we do not
observe creep camps or kills.
`inferenceLabel = "allyZoneCreepingCandidate"`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The player whose actions fell in the ally zone. |
| `allyId` | integer | The ally whose zone was entered. |
| `actionCount` | integer | Actions inside the ally's zone band. |
| `centroid` | object `{ x, y }` | Centroid of those actions. |
| `thresholds.allyHomeRadius` | integer | Ally's home radius. |
| `thresholds.minActionCount` | integer | Minimum action density that qualified. |

#### `jointEngagement` (FR-018)

A spatial-temporal cluster of clicks involving two or more
teammates. **Inference**: *consistent with* a joint fight — we do
not observe combat. `inferenceLabel = "jointEngagementCandidate"`.

| Field | Type | Meaning |
|---|---|---|
| `playerIds` | array of integers | The participating teammates. |
| `centroid` | object `{ x, y }` | Cluster's spatial centroid. |
| `actionCount` | integer | Total clustered actions. |
| `perParticipantCounts` | object `{ playerId(string) → integer }` | Per-player action contribution. |
| `tightness` | number | Mean intra-cluster distance, in map units. |
| `thresholds.engagementRadius` | integer | DBSCAN ε used. |
| `thresholds.engagementTimeWindowSeconds` | integer | The 5 s time window (research §R4). |

#### `heroTeleport` (FR-019)

A timed item-use action whose item id is in the documented teleport
catalog. Observable. `inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The casting player. |
| `itemId` | string | 4-char teleport-item id (see Catalog: hero teleports). |
| `itemName` | string | Display name. |
| `originPosition` | object `{ x, y }` \| null | Origin coordinate when the underlying action carried one. |
| `heroId` | string \| null | Casting hero's 4-char id when unambiguously attributable. |
| `attributionNote` | string \| null | Reason hero attribution was omitted, when applicable. |

In v1 the attribution gap is universal (the analyzer output does not
expose selection state). Every `heroTeleport` event currently carries
`heroId: null` and a non-null `attributionNote`.

#### `productionStall` (FR-020)

A continuous span during which a player issued zero production-order
entries despite continuing to issue any actions. Observable.
`inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `playerId` | integer | The stalled player. |
| `durationMs` | integer | `endTimeMs - startTimeMs`. |
| `inputRateDuringStall` | number | Actions per minute during the stall. |
| `thresholds.productionStallMinGapMs` | integer | The 45 000 ms minimum (research §R5). |

#### `intensityPeak` (FR-021)

A local maximum in the per-team or all-player aggregate input-rate
curve (rolling 30 s sum) exceeding `mean + 2σ`. **Inference**:
*consistent with* a moment of heightened activity (often a fight) —
we do not observe what's happening on the map.
`inferenceLabel = "intensityPeakCandidate"`.

| Field | Type | Meaning |
|---|---|---|
| `scope` | string ∈ `{"all", "team:<teamId>"}` | The scope of the aggregate curve. |
| `peakValue` | number | The rolling-sum value at the peak. |
| `baseline` | object `{ mean: number, std: number }` | Baseline statistics over the full game. |
| `thresholds.windowSeconds` | integer | The 30 s rolling window. |
| `thresholds.peakSigma` | number | The 2.0 σ threshold. |

#### `resourceTransfer` (FR-022)

A gold or lumber transfer from one player to an ally. Consecutive
transfers between the same sender/receiver pair separated by
≤ `burstGapMs` are merged into a single "transfer burst" event;
isolated transfers are emitted as singleton events.
Observable. `inferenceLabel = null`.

| Field | Type | Meaning |
|---|---|---|
| `senderId` | integer | The sending player. |
| `receiverId` | integer | The receiving player. |
| `count` | integer | Number of transfers in the burst (≥ 1). |
| `totalGold` | integer | Sum of gold across the burst. |
| `totalLumber` | integer | Sum of lumber across the burst. |
| `thresholds.burstGapMs` | integer | The 30 000 ms inter-transfer threshold (research §R6). |

`startTimeMs` = first transfer's time. `endTimeMs` = last transfer's
time when `count > 1`; omitted when `count == 1`.

## §diagnostics

Mirrors the analyzer's `diagnostics` pattern.

| Field | Type | Meaning |
|---|---|---|
| `extractorVersion` | string | Semver of `extract_events.py` at the time of the run, read from `processor/pyproject.toml`. |
| `parserId` | string | Forwarded from the analyzer's `diagnostics.parserId`. |
| `players` | object `{ playerId(string) → { homeDerivation, homeRadiusDerivation } }` | Per-player home derivation method record. Values: `"primary"` or `"fallback:<rule>"`. |
| `thresholds` | object | Per-replay threshold values: `mapActiveDiagonal`, `engagementRadius`, `rebuildBucketSize`, `idleMinGapMs`, `productionStallMinGapMs`, `transferBurstGapMs`, `engagementTimeWindowSeconds`, `intensityWindowSeconds`, `intensityPeakSigma`. |
| `eventCounts` | object `{ kind(string) → integer }` | Per-kind event counts. Sums to `len(events)`. Kinds with zero events are omitted. |

## Determinism

The events document is **byte-identical** across re-runs against the
same analyzer-output input (FR-035 / SC-006). The extractor does not
embed wall-clock time. The only time-derived data is in-game time
from the underlying replay.

## Stable id derivation

Each event's `id` is computed as:

```python
canonical = "|".join([
    kind,
    str(start_time_ms),
    ",".join(sorted(str(p) for p in participants)),
    disambiguator,
])
event_id = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]
```

The 16-hex-character truncation gives 64 bits of collision resistance,
plenty for the ~hundreds of events per replay. The id is stable
across re-runs and across non-breaking spec revisions.

Per-kind disambiguators:

| Kind | Disambiguator |
|---|---|
| `idlePeriod` | `str(end_time_ms)` |
| `productionStall` | `str(end_time_ms)` |
| `buildingRebuild` | `f"{entity_id}@{bucket_x},{bucket_y}"` |
| `techMilestone` | The milestone label (`tier2Hall`, etc.). |
| `intensityPeak` | The scope label (`"all"` or `"team:<id>"`). |
| All others | `""` (empty). |

## Catalogs

### Towers (FR-015)

| Race | Entity ids |
|---|---|
| Human | `hgtw` Guard Tower, `hctw` Cannon Tower, `hatw` Arcane Tower, `hwtw` Scout Tower |
| Orc | `otto` Watch Tower |
| Undead | `uzg1` Spirit Tower, `uzg2` Nerubian Tower |

(Sacrificial Pit `usep` is included in the filter set for
completeness; in practice it does not pass the
"closer-to-opponent-than-own-home" rule and emits no false events.)

### Tech milestones (FR-012)

| Milestone | Entity ids (per race) |
|---|---|
| `tier2Hall` | `hkee` Keep, `ostr` Stronghold, `unp1` Halls of the Dead, `etoa` Tree of Ages |
| `tier3Hall` | `hcas` Castle, `ofrt` Fortress, `unp2` Black Citadel, `etoe` Tree of Eternity |
| `altar` | `halt` Altar of Kings, `oalt` Altar of Storms, `uaod` Altar of Darkness, `eaoe` Altar of Elders |
| `keyTechBuilding` | `hlum` Lumber Mill, `ofor` War Mill (Orc), `usep` Sacrificial Pit, `eaom` Ancient of Lore |
| `majorUpgradeStart` | The first entry in the player's `production.upgrades.order` list, whatever entity id it has. |

### Hero teleports (FR-019)

| Item id | Item name |
|---|---|
| `stwp` | Scroll of Town Portal |
| `stel` | Staff of Teleportation |
| `mtel` | Mass Teleport Scroll |

## What this document does NOT contain

- No outcome vocabulary (no `killed`, `destroyed`, `stole`, `won`
  used as factual claims). Verifiable by string search.
- No raw timed-action stream (it lives in the analyzer output).
- No production-order list (analyzer output).
- No chat messages (analyzer output).
- No coordinate transformation (same map units as the analyzer).

If a consumer needs any of the above, they fetch the sibling
`*.analysis.json`. The `match.parserId` field in this document
matches the `diagnostics.parserId` of that document, allowing safe
cross-document referencing.

## Version evolution

Future spec revisions MAY add new event kinds, add fields to
existing event kinds, add fields to `diagnostics`, or extend the
per-kind threshold list. Any such change MUST update this document
in the same PR (FR-032). Removing a kind, removing a field, or
changing a field's type is breaking and would warrant a top-level
`version` field on the document root, deferred until first needed.
