# Phase 1 Data Model — Team Cohesion Analysis

This document enumerates the entities the team-cohesion analyzer reads, the entities it emits as the new `team` top-level key on `AnalysisDocument`, and the relationships between them. It is the engineering-level counterpart to `spec.md`'s Key Entities section and the detailed source for the output-shape contract in `contracts/output-shape.md`.

This document **extends** `specs/002-replay-analyzer/data-model.md` — it does not redefine the existing inputs and outputs. Every input and output of feature 002 remains in force unchanged. New entries below are additive: a new top-level key (`team`), four new lookup tables, two new diagnostics arrays, and the Processor's first read of the parser's `events[]` stream.

## Glossary

Terms used throughout this document. Defined here so the rest of the document can be read without ambiguity.

- **Unit handle**: A pair of integers `[hi, lo]` (a 64-bit identifier split into two 32-bit halves) that uniquely identifies one game object — unit, building, hero, or item — in the replay. Same handle representation used by `w3gjs`. Throughout this document the term **unit handle** is preferred; bare "handle" is shorthand only.
- **Slot**: A player's slot id (a small integer, 0–11 for human players, 12 / 15 for the neutral-passive / neutral-aggressive players in WC3). Stable within a replay.
- **Centroid**: The arithmetic mean of `(x, y)` positions over a set of unit handles. Per-player centroids are computed at battle start (FR-002).
- **Battle window**: A contiguous time range `[startMs, endMs]` in which both opposing teams are actively dealing damage. Detected by the bucket-and-runs heuristic in `processor/team/battles.py`.
- **TEI** (Trade-Efficiency Index): `(value of enemy units removed) / (value of own-side units lost)` per battle. Capped at `99.0` when own-side losses are zero. Value function is gold + lumber (FR-021).
- **WC3 map units**: The native coordinate system `w3gjs` emits. Both `x` and `y` are floating-point values typically in the range `[-8192, 8192]`. Negative coordinates correspond to one half of the map and are normal (not error sentinels).
- **Active selection**: The set of unit handles a player currently has selected. Updated on every `0x16` / `0x17` event. Used by the position state machine to know which handles to update on a subsequent `0x11` / `0x12` action.
- **Tier 2**: The handle-tracking centroid approach chosen in `plan.md` (vs. Tier 1 target-averaging). Implies the existence of `processor/team/ownership.py` + `processor/team/positions.py`.

### Coordinate system

All `x`, `y`, `pos`, `target`, `targetA`, `targetB` fields throughout `team.*` (and throughout the parser's events stream) are in **WC3 map units**, the native coordinate system `w3gjs` emits. No re-projection is applied. Distances, centroids, and aura radii are all in the same unit; the values are directly subtractable / averageable / comparable. The map's origin `(0, 0)` is the map center; one corner is at approximately `(-8192, -8192)` and the opposite at approximately `(+8192, +8192)`.

## Inputs

### ParserOutput (read-only) — newly-consumed fields

The same JSON document feature 002 reads. Feature 006 extends the read footprint to the previously-ignored `events[]` stream and to one previously-passed-through settings field. No write-back; no field is reshaped.

| Source field | Used for | Action ids consumed |
|---|---|---|
| `events[].id === 31 → commandBlocks[].actions[]` | Per-event extraction: positions, transfers, item gives, pings, build orders, selections | `0x10`, `0x11`, `0x12`, `0x13`, `0x14`, `0x16`, `0x17`, `0x51`, `0x68` (full list per `team/events.py`) |
| `settings.fullSharedUnitControl` | `team.sharedControl.enabled` (FR-013) | n/a (already in settings, just re-exposed under `team`) |
| `players[].resourceTransfers[]` | Mirrored into `team.resourceCooperation.transfers[]` with added `purposeHint` (FR-012) | n/a (already aggregated; not re-derived from `events[]`) |
| `players[].buildings.summary`, `units.summary`, `upgrades.summary` | `totalMined` *estimate* via `Σ unit_costs[id] × count` — see Generosity derivation rule below | n/a |
| `players[].heroes[].id` | Recipient-fit-class lookup (matching item attribute to hero primary attribute, FR-009) | n/a |

The parser's `chat[]`, `map.*`, `winningTeamId`, `players[].apm`, `groupHotkeys`, `actions.totals`, `actions.timed`, etc. — feature 002 already reads these and feature 006 does not change that.

#### Action-id reference

Every action id consumed by feature 006 with the field shape observed in the committed fixtures (decoded from the Phase 0 probe — see `research.md`).

| Action id | Shape (relevant fields) | Used for |
|---|---|---|
| `0x10` (16) | `{ orderId, abilityFlags }` (no target) | Build-order detection (orderId resolves to a building/unit id); origin position recovered from issuing player's most recent active selection. Worker→building handoff in `positions.py`. |
| `0x11` (17) | `{ orderId, target: [x, y], abilityFlags }` | Move-to-position. Updates each currently-selected handle's position to `target`. |
| `0x12` (18) | `{ orderId, target: [x, y], object: [hi, lo], abilityFlags }` | Target-position-and-unit. Updates selected handles' positions to `target`. The `object` handle is the *target* unit (used by `cohesion.py` for focus-fire dominant target — the most-attacked enemy handle). |
| `0x13` (19) | `{ orderId, target: [x, y], unit: [hi, lo], item: [hi, lo] }` | Give-item. `item` is the item handle being given; `unit` is the recipient hero handle; `target` is the location. Source for `team.itemTransfers[]`. |
| `0x14` (20) | `{ orderId1, orderId2, targetA: [x, y], targetB: [x, y], owner, category, flags }` | Two-target ability. Phase 0 probes whether `owner`/`category` permit ally-cast detection (US2 stretch goal). |
| `0x16` (22) | `{ selectMode, numberUnits, units: [[hi, lo], ...] }` | Selection. Establishes player → handle ownership in `ownership.py`; updates the player's active selection set in `positions.py`. |
| `0x17` (23) | `{ groupNumber, numberUnits, units: [[hi, lo], ...] }` | Hotkey-group + units. Same ownership / active-selection role as `0x16`. |
| `0x51` (81) | `{ slot, gold, lumber }` | Resource transfer. Already aggregated by the parser into `players[].resourceTransfers[]`; feature 006 mirrors that into `team.resourceCooperation.transfers[]` and adds `purposeHint`. |
| `0x68` (104) | `{ pos: [x, y], duration }` | Minimap signal (ping). Source for `team.battles[i].pings[]`. |

Coordinates throughout are in **WC3 map units** — the same coordinate system w3gjs emits (negative coordinates on one half of the map are normal). No re-projection.

### EntityNamesMapping (read-only)

Same `processor/entity_names.json` feature 002 already reads. Feature 006 uses it for resolving item names, building names (for transfer purpose hints), and hero names. No edits.

### AurasTable (read-only) — NEW

`processor/auras.json` — a flat object whose keys are 4-char hero ability ids and whose values describe the aura's radius and category.

```text
{
  "AHad": { "radius": 900, "type": "support", "owner": "Hpal", "name": "Devotion Aura" },
  "AHab": { "radius": 900, "type": "support", "owner": "Hamg", "name": "Brilliance Aura" },
  "AEar": { "radius": 900, "type": "support", "owner": "Edem", "name": "Endurance Aura" },
  "AOcr": { "radius": 900, "type": "support", "owner": "Obla", "name": "Command Aura" },
  ...
}
```

Validation rules:

- Every key MUST be a string of exactly 4 ASCII alphanumerics (a w3gjs ability id).
- Every value MUST have `radius: number ≥ 0`, `type: "support" | "damage"`, `owner: string` (4-char hero id), `name: string`.
- Auras with `type: "damage"` (e.g., Vampiric, Trueshot) are recorded but only `type: "support"` auras are used as the FR-005 split-engagement threshold.
- Default radius **900** is hardcoded in `team/centroids.py`'s `DEFAULT_AURA_RADIUS` constant — used when no support aura is active in a battle (FR-006). The constant is referenced from `auras.json` documentation but is not itself in the table (data file holds *facts about WC3*, not *defaults for our analyzer*).

Coverage requirement: at least the seven canonical support auras (Devotion, Brilliance, Endurance, Trueshot, Unholy, Vampiric, Command). Gaps surface in `diagnostics.unmappedEntityIds` with `category: "ability"`.

Regenerator: `processor/tools/build_auras.py` extracts radii from `w3gjs`'s ability data tables. Manual overrides (auras observed in fixtures but absent from `w3gjs`'s published table) are listed under `MANUAL_OVERRIDES` at the top of the script.

### ItemAttributesTable (read-only) — NEW

`processor/item_attributes.json` — keys are 4-char item ids; values describe the item's primary-attribute fit and rescue-tool flag.

```text
{
  "stwp": { "primary": "universal", "isRescue": true,  "name": "Staff of Preservation" },
  "shea": { "primary": "universal", "isRescue": true,  "name": "Scroll of Healing" },
  "stwl": { "primary": "universal", "isRescue": true,  "name": "Scroll of Town Portal" },
  "tin1": { "primary": "int",       "isRescue": false, "name": "Tome of Intelligence" },
  "tst1": { "primary": "str",       "isRescue": false, "name": "Tome of Strength" },
  "tag1": { "primary": "agi",       "isRescue": false, "name": "Tome of Agility" },
  "ofir": { "primary": "agi",       "isRescue": false, "name": "Orb of Fire (agi-attack item)" },
  "rhe1": { "primary": "universal", "isRescue": true,  "name": "Lesser Healing Potion" },
  ...
}
```

Validation rules:

- Every key MUST be a 4-char item id.
- `primary` ∈ `{ "int", "str", "agi", "universal", "none" }`.
- `isRescue` is a boolean. (`true` for items that can save an ally hero — staves, healing scrolls, town-portal scrolls, healing potions.)

Regenerator: `processor/tools/build_item_attributes.py`. The companion `processor/rescue_items.json` is **derived** from this file (`[id for id, v in items.items() if v["isRescue"]]`) and committed for audit ease, not read directly by `analyze.py`.

### UnitCostsTable (read-only) — NEW

`processor/unit_costs.json` — keys are 4-char unit / building ids; values are the WC3 gold / lumber / supply cost.

```text
{
  "hkni": { "gold": 245, "lumber":  60, "supply": 4, "name": "Knight" },
  "hfoo": { "gold": 135, "lumber":   0, "supply": 2, "name": "Footman" },
  "hpal": { "gold": 425, "lumber": 100, "supply": 5, "name": "Paladin (hero, level 1 cost)" },
  "htow": { "gold": 385, "lumber": 205, "supply": 0, "name": "Town Hall" },
  ...
}
```

Validation rules:

- Every key MUST be a 4-char unit/building/upgrade/hero id.
- `gold ≥ 0`, `lumber ≥ 0`, `supply ≥ 0`.
- Heroes carry their level-1 summon-cost (used as the value proxy when a hero is killed; subsequent revives are not separately costed in v1).

Used by:
- `team/tei.py` for TEI numerator / denominator (`gold + lumber`; `supply` recorded for future use, not in v1 formula).
- `team/resources.py` for the generosity-score `totalMined` *estimate*.

Regenerator: `processor/tools/build_unit_costs.py`. Manual overrides (units observed in fixtures but absent from `w3gjs`'s tables) listed at the top of the script.

### RescueItemsList (read-only, derived) — NEW

`processor/rescue_items.json` — a flat array of 4-char item ids derived from `ItemAttributesTable` by filtering `isRescue === true`.

```text
[ "stwp", "shea", "stwl", "rhe1", "rhe2", "phea", ... ]
```

Committed for audit / `tools/build_item_attributes.py` checks the two files agree on every regenerator run. `analyze.py` reads either; tests assert agreement.

## Outputs

### EntityRef (common shape)

A reusable shape, used throughout the `team.*` block wherever a WC3 entity (unit, building, hero, item, ability) is referenced. Identical in shape to feature 002's existing entity references in `players[]`.

```text
{
  "id":      string,    // 4-char WC3 entity id (e.g., "stwp", "hkni", "Hpal", "AHad")
  "name":    string,    // resolved display name (e.g., "Staff of Preservation", "Knight")
  "unknown": boolean    // true ⇔ id is not in entity_names.json (or the relevant lookup table)
}
```

When `unknown === true`, `name === id` (the raw 4-char id is used as the placeholder name; the Visualizer renders it with a visible "unmapped" indicator). Every appearance of an unmapped id additionally produces a `diagnostics.unmappedEntityIds[]` entry (or `diagnostics.itemAttributeGaps[]` for items missing from the attribute table).

### AnalysisDocument (extended)

The same root entity feature 002 emits, with **one new top-level key**: `team`. Every existing top-level key (`match`, `settings`, `map`, `players`, `observers`, `chat`, `diagnostics`) appears unchanged in shape and content.

```text
{
  "match":       { ... unchanged ... },
  "settings":    { ... unchanged ... },
  "map":         { ... unchanged ... },
  "players":     [ ... unchanged ... ],
  "observers":   [ ... unchanged ... ],
  "chat":        [ ... unchanged ... ],
  "diagnostics": { ... extended with two new arrays — see Diagnostics extensions below ... },
  "team":        TeamBlock      // NEW
}
```

### TeamBlock (NEW top-level)

The full team-cohesion output. One of two shapes depending on applicability:

#### Empty state (1v1, FFA, no detected battles, or any "not applicable" reason)

```text
{
  "applicable": false,
  "reason":     "noAllies" | "ffa" | "noBattlesDetected" | "preFeature006File"
}
```

When `applicable === false`, no other `team.*` fields are emitted. The Visualizer renders a single empty-state copy keyed on `reason`.

Examples of the empty state:

```text
// 1v1 replay — no allies anywhere
{
  "applicable": false,
  "reason":     "noAllies"
}

// FFA replay — fixedTeams === false and no two non-AI players share a teamId
{
  "applicable": false,
  "reason":     "ffa"
}

// Fully team-formed replay but the players never engaged
{
  "applicable": false,
  "reason":     "noBattlesDetected"
}
```

The fourth `reason: "preFeature006File"` is NOT produced by the analyzer (see Derived-field rules below); it is a Visualizer-side fallback when an old `*.analysis.json` document lacks the `team` key entirely.

#### Populated state

```text
{
  "applicable": true,
  "sharedControl":       SharedControl,          // FR-013
  "findings":            [ string, ... ],        // FR-013 ("sharedControlDisabled" etc.) — top-level non-battle findings
  "battles":             [ Battle, ... ],         // FR-001 .. FR-006, FR-016 .. FR-018
  "itemTransfers":       [ ItemTransfer, ... ],   // FR-007 .. FR-009
  "supportEvents":       [ SupportEvent, ... ],   // FR-010, FR-011 (and US2 stretch when Phase-0 probe succeeds)
  "resourceCooperation": ResourceCooperation,     // FR-012, FR-014
  "players":             [ TeamPlayer, ... ],      // per-player KP% (FR-019), one entry per non-AI player
  "battleSummary":       BattleSummary             // FR-021 .. FR-023
}
```

`applicable: true` requires at least two non-AI players on different teams *and* either at least one detected battle window OR at least one `0x13` / `0x51` event between allies. Otherwise `reason: "noBattlesDetected"`.

### SharedControl

```text
{
  "enabled": boolean    // copy of ParserOutput.settings.fullSharedUnitControl
}
```

Always present in the populated `team` object; never `null` in the populated branch.

### Battle

A single battle window, in chronological order within `team.battles[]`.

```text
{
  "index":               number,                  // 0-based, stable across runs
  "startMs":             number,                  // in-game ms when the run-of-engaged buckets started
  "endMs":               number,                  // in-game ms when the trailing 2-bucket gap closed it
  "sides": {
    "teamA":  [ slot, ... ],   // ARBITRARY LABEL — not tied to lobby teamId. The first team
                                //   encountered in the battle's events is named "teamA"; the
                                //   opposing one is "teamB". Stable within one analyzer run
                                //   (deterministic ordering by lowest-slot-id of each side).
    "teamB":  [ slot, ... ]
  },
  "centroids":           [ Centroid, ... ],        // one entry per participating non-AI player
  "alliedDistances":     [ AlliedDistance, ... ],  // one entry per allied pair (per side)
  "splitEngagement":     SplitEngagement,
  "focusFire":           FocusFire | null,         // null when w3gjs underexposes target-unit ownership
  "pings":               [ Ping, ... ],
  "kills":               [ KillEstimate, ... ]      // per-handle estimates feeding tei + KP%
}
```

`index` is stable: re-running the analyzer on the same input yields identical battle indices. (Phase 1b sorts battles by `startMs` before assigning.)

### Centroid

```text
{
  "slot":   number,                 // player slot id
  "x":      number | null,          // null only when source === "missing"
  "y":      number | null,
  "source": "commanded" | "missing" // "missing" → player had no commanded handles in the 60s lookback
}
```

### AlliedDistance

```text
{
  "fromSlot": number,
  "toSlot":   number,
  "distance": number      // Euclidean centroid distance in WC3 map units
}
```

`fromSlot < toSlot` to keep pair ordering deterministic. One entry per pair per side; cross-team pairs are NOT emitted (we don't measure enemy-to-enemy alignment).

### SplitEngagement

```text
{
  "flagged":            boolean,
  "distance":           number,           // max allied centroid distance in this battle
  "referenceAuraId":    string,           // 4-char ability id, or "default" when no support aura active
  "referenceAuraName":  string,           // resolved name (e.g., "Devotion Aura") or "default 900u"
  "flaggedSlots":       [ number, number ] // the pair achieving the max distance — only populated when flagged === true
}
```

When `flagged === false`, `flaggedSlots` is `[]`.

### FocusFire

```text
{
  "dominantTargetSlot": number | null,    // owner slot of the most-attacked enemy handle
  "dominantTargetEntity": EntityRef,      // { id, name, unknown } when resolvable, else { id: "UNKN", name: "UNKN", unknown: true }
  "cohesionPercent":    number,           // 0-100, share of team attack actions targeting the dominant
  "contributingPlayers": [ {              // sorted by attackCount desc
    "slot":         number,
    "attackCount":  number
  }, ... ]
}
```

`null` for the entire `focusFire` object surfaces a `diagnostics.cohesionMetricGaps[]` entry naming `focusFire` and the reason (typically "no enemy unit-handle ownership inferable from selection events in window"). Example of the null branch:

```text
// Inside team.battles[4]:
"focusFire": null,
...

// And in diagnostics:
"cohesionMetricGaps": [
  { "metric": "focusFire:battle=4", "reason": "no enemy unit-handle ownership inferable in window" },
  ...
]
```

### Ping

```text
{
  "fromSlot":            number,
  "x":                   number,             // ping target — WC3 map units
  "y":                   number,
  "timeMs":              number,
  "duration":            number,              // copied from action's `duration` field
  "respondedBySlot":     [ slot, ... ],       // allies who moved their centroid toward (x,y) within 15 s — see "Response detection" below
  "engagedElsewhereSlot": [ slot, ... ]       // allies whose army was already actively dealing damage in another battle window at timeMs
}
```

A slot in **neither** `respondedBySlot` nor `engagedElsewhereSlot` is implicitly "ignored the ping." The Visualizer renders this as the third bucket without it being emitted (the slot's absence from both arrays IS the signal).

#### Response detection

For each ally `a` (a slot on the same team as `fromSlot`), let `c0 = centroid(a, timeMs)` (centroid at ping time) and `c1 = centroid(a, timeMs + 15_000)` (centroid 15 in-game seconds later). The ally is added to `respondedBySlot[]` iff:

```
distance(c0, ping) - distance(c1, ping) >= MIN_RESPONSE_DELTA
```

That is: their centroid got closer to the ping by at least `MIN_RESPONSE_DELTA` map units within the 15-second response window. **Direction matters** — moving away from the ping (or moving by less than `MIN_RESPONSE_DELTA` toward it) does NOT count as a response.

Constants (declared at the top of `processor/team/cohesion.py`, validated against both fixtures by the SC-001 zero-error bar):

- `MIN_RESPONSE_DELTA = 200` (WC3 map units) — the floor for "meaningful movement toward the ping"
- `RESPONSE_WINDOW_MS = 15_000` (15 in-game seconds) — the look-ahead window
- `engagedElsewhereSlot` is populated by checking whether the ally was inside *some other* battle window's `[startMs, endMs]` at `timeMs`; armies actively dealing damage cannot be expected to disengage.

If the ally's centroid is `null` at either `timeMs` or `timeMs + 15_000` (the player issued no commands and has no Tier 2 position state), they are added to neither array; the Visualizer renders this with a tooltip noting "no movement data."

### KillEstimate

```text
{
  "victimHandle":   [ number, number ],   // the enemy unit handle that disappeared
  "victimEntity":   EntityRef,            // resolved from production tracking when known
  "victimSide":     "teamA" | "teamB",
  "victimValue":    number,               // unit_costs[victim].gold + unit_costs[victim].lumber — the TEI value contribution
  "killTimeMs":     number,
  "credits":        [ {                    // damage-share fractions; sum to 1.0 across one kill
    "slot":     number,
    "fraction": number                     // attack-action share within the 5s pre-death window
  }, ... ]
}
```

Kills with no team attack-action coverage in the 5-second pre-death window are NOT emitted (no row); a single match-level note is added to `diagnostics.cohesionMetricGaps[]` if any unattributed kills occurred.

### ItemTransfer

```text
{
  "fromSlot":           number,
  "toSlot":             number,
  "item":               EntityRef,         // { id, name, unknown }
  "timeMs":             number,
  "recipientFitClass":  "good" | "wrong" | "neutral" | "unknown",
  "recipientHero":      EntityRef          // the hero handle's resolved entity, when ownership tracking found it
}
```

Every `0x13` event in the input produces exactly one entry. `recipientFitClass` derivation rule:

- Item `primary === "int"`, recipient hero primary `int` → `"good"`
- Item `primary === "int"`, recipient hero primary `str` or `agi` → `"wrong"`
- Item `primary === "universal"` → `"neutral"`
- Item not in `item_attributes.json` OR recipient hero unmapped → `"unknown"` (one entry added to `diagnostics.itemAttributeGaps[]`)

### SupportEvent

Two `type` variants share the union:

#### `type: "missedSave"` (FR-010)

```text
{
  "type":            "missedSave",
  "deceasedSlot":    number,
  "deceasedHero":    EntityRef,
  "holderSlot":      number,
  "holderHero":      EntityRef,
  "itemId":          string,                // a 4-char id from rescue_items.json
  "itemName":        string,
  "deathTimeMs":     number,
  "distanceAtDeath": number                  // Euclidean distance from holderHero centroid to deceasedHero centroid
}
```

Emitted only when `distanceAtDeath ≤ RESCUE_RANGE` (default 800 units, declared in `team/support.py`).

#### `type: "supportSpellCast"` (US2 stretch — emitted only when Phase 0 probe succeeds)

```text
{
  "type":         "supportSpellCast",
  "casterSlot":   number,
  "casterHero":   EntityRef,
  "targetSlot":   number,                    // the ally on whose unit the spell was cast
  "targetEntity": EntityRef,                 // the target unit (e.g., another player's Knight)
  "spell":        EntityRef,                 // the ability id resolved
  "timeMs":       number
}
```

If the Phase 0 probe shows `0x14` does not permit ally-vs-self disambiguation, the entire `supportSpellCast` type is dropped from emission and a single `diagnostics.cohesionMetricGaps[]` entry names `supportSpellCast` with `reason: "phase0ProbeFailed"`. No partial / heuristic emission.

### ResourceCooperation

```text
{
  "transfers":   [ AnnotatedTransfer, ... ],
  "generosity":  [ GenerosityRow, ... ]
}
```

#### AnnotatedTransfer

```text
{
  "fromSlot":     number,
  "toPlayerId":   number,
  "toPlayerName": string,
  "gold":         number,
  "lumber":       number,
  "timeMs":       number,
  "purposeHint":  "tierUpAssist" | "baseDefense" | "lateGameTopUp" | "none"
}
```

Every entry in `players[].resourceTransfers[]` has exactly one corresponding `AnnotatedTransfer` (mirror invariant). `purposeHint` derivation rule:

- `"tierUpAssist"` if a tier-up `0x10` action by the recipient (orderId resolves to Keep / Stronghold / Halls of the Dead / Tree of Ages / Castle / Fortress / Black Citadel / Tree of Eternity) appears in `[timeMs - 60_000, timeMs + 60_000]`.
- `"baseDefense"` if at least 3 of the recipient's buildings disappear (handles drop from selection events) within the same window AND no tier-up was hit.
- `"lateGameTopUp"` if `timeMs > 0.75 * match.durationMs` AND neither earlier classifier matched.
- `"none"` otherwise.

#### GenerosityRow

```text
{
  "slot":                 number,
  "name":                 string,
  "sentGold":             number,                // sum of this player's outgoing transfers
  "sentLumber":           number,
  "estimatedMinedGold":   number | null,         // Σ unit_costs[id].gold × count over production.summary
  "estimatedMinedLumber": number | null,         // Σ unit_costs[id].lumber × count over production.summary
  "generosityPercent":    number | null
  // generosityPercent =
  //   100 * (sentGold + sentLumber) / (estimatedMinedGold + estimatedMinedLumber)
  // is null when EITHER estimatedMinedGold OR estimatedMinedLumber is null
  // (a single missing unit_cost entry on this player's production line poisons the
  // entire ratio — better honest null than a partial denominator that misranks players).
}
```

`null` on `estimatedMinedGold` / `estimatedMinedLumber` happens iff `unit_costs.json` lacks coverage for at least one entity in this player's `production.summary`; in that case a `diagnostics.cohesionMetricGaps[]` entry names `generosity:slot=N` AND a `diagnostics.unmappedEntityIds[]` entry with `category: "unitCost"` names every missing id. Adding the missing id to `unit_costs.json` (one-line PR) restores the metric to a number on the next analyzer run.

### TeamPlayer

```text
{
  "slot":                       number,
  "name":                       string,
  "killParticipationPercent":   number | null   // 0-100 across the whole match; null when too few attributable kills
}
```

`null` requires at least one accompanying `diagnostics.cohesionMetricGaps[]` entry.

### BattleSummary

```text
{
  "tei":           [ BattleTEI, ... ],          // one per battle, in battle index order
  "attributions":  [ Attribution, ... ],
  "executive":     [ ExecutiveFinding, ... ]    // length 0..3
}
```

### BattleTEI

```text
{
  "battleIndex":   number,
  "teamSideTei":   {
    "teamA": number | null,                // null when too few attributable kills/deaths
    "teamB": number | null
  },
  "perPlayerTei": [ {
    "slot":  number,
    "tei":   number | null
  }, ... ]
}
```

TEI sentinel: `99.0` when own-side losses are zero (FR-021 zero-loss handling). Renderable as a number; tooltip in the Visualizer surfaces "≥ 99.0 — perfect trade."

TEI formula:
- Numerator: `Σ value(enemy_unit_killed_by_team_in_battle)` where `value(u) = unit_costs[u].gold + unit_costs[u].lumber`.
- Denominator: `Σ value(own_unit_killed_by_enemy_in_battle)`. If denominator is zero → cap at `99.0`.
- Per-player: `(player_attack_share_in_window * battle_team_value_killed) / max(player_value_lost, 1)` then cap-at-99.

### Attribution

```text
{
  "playerSlot":   number,
  "battleIndex":  number,
  "reason":       "splitEngagement"    // initial reason set; extensible in later features
}
```

Emitted only when ALL three conditions hold (FR-022):

1. `battles[battleIndex].splitEngagement.flagged === true`
2. `battleSummary.tei[battleIndex].teamSideTei[playerSide] < 1.0` — the player's side lost the value trade in this battle.
3. **The player's centroid is the outlier** for their side. Concretely, let `S = battles[battleIndex].sides[playerSide]` (the slots on the player's side in this battle). Then:
   - `mean_centroid_team` = element-wise mean of `centroid` over the slots in `S` whose centroid is non-null.
   - `mean_pairwise_distance` = arithmetic mean of every `alliedDistances[].distance` whose `fromSlot` and `toSlot` are both in `S`. Cross-side pairs are excluded.
   - The player is flagged as outlier iff `distance(centroid[player], mean_centroid_team) > 1.5 * mean_pairwise_distance`.

Multiple attributions per battle are allowed; multiple battles per player are allowed. If `mean_pairwise_distance` is `0` (degenerate single-ally side) or `centroid[player]` is `null`, no attribution is emitted for this player on this battle.

### ExecutiveFinding

```text
{
  "rank":               number,                       // 1, 2, or 3 — top-N by weighted severity
  "weightedSeverity":   number,                       // base_weight * min(battle_duration / 60, 3.0)
  "kind":               "splitEngagement" | "missedSave" | "lowTei" | "sharedControlDisabled" | "wrongItemTransfer" | "ignoredPing",
  "battleIndex":        number | null,                // null for non-battle findings (e.g., sharedControlDisabled)
  "summary":            string,                       // short coach-style copy: "Split engagement at 0:34:17"
  "evidenceRef":        EvidenceRef                   // pointer into other team.* fields for the Visualizer
}
```

Length: 0..3. Sorted by `weightedSeverity` desc; ties broken by `battleIndex` asc (chronological order). `summary` strings are produced by `team/attribution.py`'s small string-builder; the Visualizer treats them as opaque display text.

#### EvidenceRef

A discriminated pointer the Visualizer uses to highlight the exact other-block field that triggered the finding. The full discriminated union (closed in v1):

```text
EvidenceRef =
  | { "kind": "battle",        "battleIndex": number }   // points at team.battles[battleIndex]
  | { "kind": "supportEvent",  "index": number }          // points at team.supportEvents[index]
  | { "kind": "itemTransfer",  "index": number }          // points at team.itemTransfers[index]
  | { "kind": "globalFlag",    "name": string }           // points at team.findings[] (name ∈ that closed enum)
```

Any future feature that adds a new finding kind (FR-029 candidate metrics, etc.) extends this union additively — existing kinds and their consumers remain unchanged.

### Diagnostics extensions (NEW arrays under existing `diagnostics`)

Two new arrays appear under the existing `diagnostics` object. Both are deduplicated by `(metric, ...)` and are `[]` when nothing degraded.

```text
diagnostics.cohesionMetricGaps:  [ { "metric": string, "reason": string }, ... ]
diagnostics.itemAttributeGaps:   [ { "id":     string, "category": "item" | "hero" }, ... ]
```

Examples:

- `{ "metric": "focusFire:battle=4", "reason": "no enemy unit-handle ownership inferable in window" }`
- `{ "metric": "supportSpellCast", "reason": "phase0ProbeFailed" }`
- `{ "metric": "killParticipation", "reason": "no attack-action coverage on 12 disappearing handles" }`
- `{ "id": "shex", "category": "item" }`

`diagnostics.unmappedEntityIds[]` (already in feature 002) carries new categories: `"ability"` (auras), `"item"` (rescue / attribute table gaps), `"unitCost"` (unit_costs.json gaps).

## Internal state (NOT in output)

These entities live only inside the Processor for the duration of one `analyze.py` run. They drive derivation of the output but are NEVER serialized.

### HandleOwnership (Tier 2 — `team/ownership.py`)

```text
{
  (handle): { "owner": slot, "firstSeenEventIdx": number, "coControlledBy": [ slot, ... ] }
}
```

Built by walking `0x16` and `0x17` events in chronological order. The first player to select a handle is its owner; subsequent selections by other players append to `coControlledBy` (used as evidence-ref data for shared-control banner; not used in centroid calculation).

### PositionState (Tier 2 — `team/positions.py`)

```text
{
  (handle): { "owner": slot, "x": number, "y": number, "lastUpdatedMs": number, "source": "command" | "build" | "selection" }
}
```

Updated on every `0x10` (build → handoff), `0x11` (move-to-position), `0x12` (target-position-and-unit), `0x13` (give-item — `target` updates the giver's selection), `0x14` (two-target).

### ActiveSelection (Tier 2 — `team/positions.py`)

```text
{
  slot: [ handle, ... ]   // each player's most recent selection
}
```

Updated on every `0x16` and `0x17`.

These three state objects are the bulk of Phase 1a's ~400 LOC. Their correctness is enforced by `test_unit_ownership.py` and `test_position_tracking.py` against committed fixtures.

## Error handling and degradation

Every error / data-gap path in the team-cohesion analyzer follows the same shape: **emit a structured `null` (or empty array) in the output, AND add a row to one of the diagnostics arrays.** The analyzer NEVER raises an unhandled exception on a malformed-but-parseable input; it never emits a partial / half-computed metric without a diagnostics entry naming the gap. The Visualizer NEVER displays a metric that is `null` without surfacing the corresponding diagnostic in a tooltip / footnote.

Exhaustive degradation table for v1:

| Condition | Output behavior | Diagnostics entry |
|---|---|---|
| `unit_costs.json` lacks an entry for an entity in `production.summary` | `GenerosityRow.estimatedMined{Gold,Lumber}` and `generosityPercent` set to `null` for that player | `cohesionMetricGaps: { metric: "generosity:slot=N", reason: "missing unit_cost" }` AND `unmappedEntityIds: { category: "unitCost", id: <id> }` |
| `unit_costs.json` lacks an entry for a killed unit | The kill is recorded but `victimValue` is `0` and the kill is excluded from TEI numerator/denominator | `unmappedEntityIds: { category: "unitCost", id: <victim id> }` |
| `auras.json` lacks the active aura's id | `splitEngagement.referenceAuraId: "default"`, `splitEngagement.referenceAuraName: "default 900u"`, default radius 900 used | `unmappedEntityIds: { category: "ability", id: <aura id> }` |
| `item_attributes.json` lacks an item id | `ItemTransfer.recipientFitClass: "unknown"` | `itemAttributeGaps: { id: <item id>, category: "item" }` |
| Recipient hero's primary attribute can't be determined (hero unmapped, hero handle never appeared in a selection) | `ItemTransfer.recipientFitClass: "unknown"` | `itemAttributeGaps: { id: <hero id>, category: "hero" }` |
| Phase 0 `0x14` probe fails | `team.supportEvents[]` contains no `"supportSpellCast"` entries; `0x14` events are simply not consumed | `cohesionMetricGaps: { metric: "supportSpellCast", reason: "phase0ProbeFailed" }` (one entry, match-level) |
| `team.battles[i].focusFire` cannot resolve enemy unit-handle ownership | `team.battles[i].focusFire: null` | `cohesionMetricGaps: { metric: "focusFire:battle=N", reason: "no enemy unit-handle ownership inferable in window" }` |
| Player has no commanded handles in the 60-s lookback before a battle | `Centroid.x: null, .y: null, .source: "missing"`; the player is excluded from `splitEngagement` and `Attribution` for this battle | (no diagnostic — this is a normal "passive opening" state, not a data gap) |
| All players' centroids are `null` for a battle | `splitEngagement.flagged: false`, `splitEngagement.referenceAuraId: "default"`, `flaggedSlots: []`; `alliedDistances: []` | `cohesionMetricGaps: { metric: "splitEngagement:battle=N", reason: "no centroids resolvable" }` |
| Kill has zero team attack-action coverage in the 5-s pre-death window | The kill is NOT emitted to `KillEstimate[]`; not included in TEI | (one match-level entry: `cohesionMetricGaps: { metric: "killParticipation", reason: "N kills had no attack-action coverage" }` if any unattributed kills occurred) |
| TEI denominator (own-side losses) is zero | `BattleTEI.teamSideTei.<side>: 99.0` (sentinel cap, not `null`) | (no diagnostic — sentinel is part of the contract, not an error) |
| Match clock is zero (corrupt replay) | Battle-window detection produces zero windows; `team.applicable: false`, `reason: "noBattlesDetected"` | (no diagnostic — empty-state shape is the contract) |
| `events[]` is missing or empty (parser-output corrupt) | `team.applicable: false`, `reason: "noBattlesDetected"` | `cohesionMetricGaps: { metric: "eventsStream", reason: "events[] missing or empty" }` |

Items NOT in this table are programmer errors and ARE allowed to raise (e.g., a malformed lookup-table JSON failing schema validation in `processor/tools/build_*.py` is a build-time error, not a runtime degradation). The boundary is: anything reachable from `analyze.py` on a real parser-output stays inside this table; anything in build / regeneration tooling is allowed to crash visibly.

## Derivation rules

- `team.applicable === false`, `reason === "noAllies"` when no team has ≥ 2 non-AI players.
- `team.applicable === false`, `reason === "ffa"` when `settings.fixedTeams === false` AND no two non-AI players share a teamId.
- `team.applicable === false`, `reason === "noBattlesDetected"` when battle-window detection found 0 windows AND there are zero `0x13` / `0x51` events between allies AND `settings.fullSharedUnitControl === false`.
- `team.applicable === false`, `reason === "preFeature006File"` is NOT produced by the analyzer — it is a Visualizer-side fallback for `*.analysis.json` files written before this feature. The Visualizer detects the absence of `team` on the document and renders the empty state with that reason. The analyzer does not need to emit this branch.
- `splitEngagement.flagged === true` ⇔ `splitEngagement.distance > splitEngagement.referenceAura.radius` (strict inequality; equal-to-radius is "barely covered" and not flagged).
- `findings[]` includes `"sharedControlDisabled"` when `settings.fullSharedUnitControl === false` AND `applicable === true`.
- `executive[].rank` is `1, 2, ..., min(3, len(findings))`. No empty rank slots.

## Invariants enforced by tests

These are the properties Phase 1–6 pytest (and one Vitest) cases assert against both committed fixtures. They are distinct from the **Derivation rules** above (which describe how the analyzer computes outputs) and from the **Error handling** table (which describes what happens when inputs are partial). An invariant must hold on every successful run; a derivation rule says how the analyzer arrives at the value; an error-handling row says what the analyzer does when it can't.

1. Top-level keys of `AnalysisDocument` are exactly `{ match, settings, map, players, observers, chat, diagnostics, team }` — strict superset of feature 002's seven; one new key.
2. Re-running the analyzer on the same input + same lookup tables produces a byte-identical `team.*` block. (Existing feature 002 invariant 7 unchanged: `diagnostics.parserParseTimeMs` remains the only volatile field.)
3. For every `0x13` event in `ParserOutput.events[]`, `team.itemTransfers[]` contains exactly one entry. (Mirror invariant.)
4. For every `0x51` entry counted by the parser into `players[].resourceTransfers[]`, `team.resourceCooperation.transfers[]` contains exactly one corresponding `AnnotatedTransfer`. (Mirror invariant.)
5. For every `0x68` event whose `timeMs` falls inside any battle window's `[startMs, endMs]`, `team.battles[i].pings[]` contains exactly one entry; pings outside any battle window are NOT emitted (consistent with the spec's "pings during a battle window" framing).
6. `team.battles[].splitEngagement.flagged === true` ⇒ `flaggedSlots.length === 2`; `flagged === false` ⇒ `flaggedSlots.length === 0`.
7. `team.applicable === false` ⇒ no other `team.*` field is present (strictly the empty-state shape).
8. Every entity reference (`item.id`, `dominantTargetEntity.id`, etc.) emitted by `team.*` resolves to `unknown: false` for entities the lookup tables cover; `unknown: true` ⇔ an entry exists in `diagnostics.unmappedEntityIds[]` or `diagnostics.itemAttributeGaps[]`.
9. `team.battleSummary.tei[i].teamSideTei.{teamA,teamB}` is either a number ≥ 0 (with `99.0` as the cap sentinel) or `null` (with a corresponding `diagnostics.cohesionMetricGaps[]` entry).
10. `team.battleSummary.executive` length ≤ 3.
11. `team.findings` only contains values from a closed enum: `{ "sharedControlDisabled" }` in v1; the enum is extended in later features only.
12. For `base_2.w3g.json` (3v3, no chat), `team.applicable === true` (3v3 has allies on each side) AND `team.battles.length ≥ 1`. (Acceptance bar from `quickstart.md`.)
13. For `base_1.w3g.json` (4v4), `team.applicable === true` AND `team.battles.length ≥ 1` AND `team.findings` contains `"sharedControlDisabled"` iff the lobby setting is off (audit value to be recorded in `quickstart.md` after Phase 1b first run).
14. Old `*.analysis.json` files (lacking the `team` key entirely) load into the new Visualizer with the empty-state `reason: "preFeature006File"` rendered on the Team tab; all other tabs are unaffected.

Tests #1–#11 are pytest, run by `cd processor && pytest`. Test #12 and #13 are pytest assertions that the analyzer's output on each fixture meets the documented audit values. Test #14 is a Vitest case in `visualizer/tests/teamFormat.test.ts` (or sibling), exercising the Visualizer's empty-state branch with a fixture stripped of `team`.

## State transitions

The analyzer is *almost* a pure function — `(ParserOutput × EntityNamesMapping × AurasTable × ItemAttributesTable × UnitCostsTable × RescueItemsList) → AnalysisDocument` — *except* that during a single run it maintains the three internal state objects (`HandleOwnership`, `PositionState`, `ActiveSelection`) that walk the event stream. These state objects are scoped to one `analyze.py` invocation; nothing persists between runs.

No external persistence is added. No database, no cache.

## Relationships diagram (text form)

```text
ParserOutput ─────────────────────────────┐
                                          │
EntityNamesMapping ────────────────┐       │
AurasTable ───────────────────────┐ │       │
ItemAttributesTable ──────────────┤ │       │
RescueItemsList (derived) ────────┤ │       │
UnitCostsTable ───────────────────┤ │       │
                                  ▼ ▼       ▼
                         processor/analyze.py
                              │  │  │
                              │  │  └─→ TeamBlock ──→ AnalysisDocument.team
                              │  └─→ Diagnostics ──→ AnalysisDocument.diagnostics (extended)
                              └─→ all existing feature-002 fields (unchanged)
                                          │
                                          ▼
                                  AnalysisDocument
                                          │
                                          ▼
                                    Visualizer layer
                                    (Team tab in feature 006;
                                     other four tabs unchanged
                                     from features 003–005)
```

Internal state (NOT serialized):

```text
events[] ──→ ownership.py ──→ HandleOwnership
            │
            └→ positions.py ──→ PositionState  + ActiveSelection
                                       │
                                       ▼
            battles.py / centroids.py / cohesion.py / kills.py / support.py / tei.py / attribution.py
                                       │
                                       ▼
                                   shape.py (envelope assembler)
                                       │
                                       ▼
                                   TeamBlock
```

## Scope exclusions (data model)

- **Movement-aware position interpolation** (Tier 3). The position state machine records last-commanded coordinates only; in-flight unit motion is not modeled.
- **Kill credit from damage events**. WC3 replays do not record damage events; KP% uses attack-action share as a proxy.
- **Per-second time series of any cohesion metric**. The output is per-battle and per-match; no per-bucket cohesion timeline.
- **Cross-replay aggregation**. One replay → one `team.*` block; aggregation across multiple replays is out of scope (mirrors features 003–005's per-replay-only stance).
- **In-browser recomputation**. The Visualizer treats every numeric field as opaque display data (Principle I / FR-031). It MUST NOT recompute centroids, TEI, or any other metric from the underlying `players[]` / `events[]` data.
- **Schema versioning of the team block**. v1 has no `version` field on `team`. If the team-block shape ever changes incompatibly, that change is a new feature spec with its own data-model.md and an additive migration plan; consumers detect it by the field presence rather than a version number.

## Forward-compatibility notes

These hooks are explicitly NOT implemented in v1 but are anticipated by the shape:

- `Attribution.reason` is a string enum starting with one value (`"splitEngagement"`); a future feature can add `"missedSave"`, `"badPing"`, etc., without reshaping the row.
- `ExecutiveFinding.kind` is a fixed enum in v1; future features can extend it.
- `SupportEvent` is a discriminated union by `type`; new types (`"giveItemReceived"`, `"baseDefenseAssist"`, etc.) plug in additively.
- `EvidenceRef.kind` is a small fixed enum in v1; new pointer kinds plug in additively.

No part of v1 emits multiple entries for "the same finding under different framings" — each event-derived row appears exactly once. The executive summary's findings carry an `evidenceRef` pointing back at the singular row, not a copy of its payload.
