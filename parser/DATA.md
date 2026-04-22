# Parser Output Data Structure

This document describes the JSON document produced by
`parser/parse.js` when run against a `.w3g` replay file. It is the
contract between the Parser layer and all downstream consumers
(initially the Processor layer, later the Visualizer, and any
operator spot-checking output by hand).

The shape described here reflects `w3gjs@4.0.0` (pinned in
`parser/package.json`) as observed against the two committed
fixtures:

- `sample_replays/base_1.w3g` — 4v4 game, chat present, 8 players
- `sample_replays/base_2.w3g` — 3v3 game, no chat, 6 players

## Scope of this parser

The parser emits exactly what `w3gjs` returns, serialized as JSON.
Nothing is added, nothing is stripped, nothing is computed on top.

**Analytical values (APM averages, action counts, build orders,
win inference, etc.) that are already present here were computed
inside `w3gjs`**, not in this project's code. They are marked
**library-derived** below; everything else is **replay-native**.

This distinction matters for one reason: when a new analysis is
built, the place to add code is the downstream processor layer,
**not** this parser. Pull requests that make the parser richer —
by adding derivations, aggregations, helpers, or computed fields —
will be rejected. If a downstream analysis needs a value that is
not present here, and the value is not something `w3gjs` can be
asked to produce, that is a genuine gap worth a new specification
— not a parser extension.

See `specs/001-replay-parser/` for the full feature rationale and
the project constitution (Principle II: "w3gjs is the canonical
parser", Principle III: "no premature abstractions").

## Output location

Running `node parser/parse.js <path>/<name>.w3g` writes the JSON
document to `<path>/<name>.w3g.json`. Any existing file at that
path is overwritten.

## Volatility

One field varies across runs even when the input is identical:

- `parseTime` — milliseconds w3gjs spent parsing this replay.
  Library-derived, wall-clock-dependent.

All other fields are content-deterministic for a given replay.

## Top-level keys

The root of the JSON document is an object with these 19 keys.
Each appears in the output regardless of replay content.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `apm` | object | library-derived | Parameters used by `w3gjs` for APM-adjacent calculations. See §apm. |
| `buildNumber` | number | replay-native | Warcraft III build number recorded in the replay header. |
| `chat` | array | replay-native | All in-game chat messages in send order. Empty array if none. See §chat. |
| `creator` | string | replay-native | Game creator identifier (e.g., "Battle.net"). |
| `duration` | number | replay-native | Game duration in milliseconds of in-game time. |
| `expansion` | boolean | replay-native | True if The Frozen Throne expansion data is present. |
| `gamename` | string | replay-native | Game/lobby name from the replay header. |
| `id` | string | library-derived | A hex hash w3gjs derives from replay content (stable across re-parses of the same file). |
| `map` | object | replay-native | Map path, filename, and checksums. See §map. |
| `matchup` | string | library-derived | Race matchup shorthand (e.g., `"HHNUvHHOO"`, `"NOUvOOU"`). Teams separated by `v`. |
| `observers` | array of string | replay-native | Observer player names, in slot order. |
| `parseTime` | number | library-derived | Milliseconds w3gjs spent parsing. **Varies across runs**; do not rely on for equality checks. |
| `players` | array | mixed | One entry per non-observer player. See §players. |
| `randomseed` | number | replay-native | Replay's recorded random seed. |
| `settings` | object | replay-native | Game options chosen in the lobby. See §settings. |
| `startSpots` | number | replay-native | Number of starting spots on the map. |
| `type` | string | library-derived | Game type shorthand derived from team sizes (e.g., `"4on4"`, `"3on3"`). |
| `version` | string | replay-native | Game version as string (e.g., `"2.00"`). |
| `winningTeamId` | number | library-derived | Team ID w3gjs determined to be the winner; `-1` when undetermined. |

## §apm

Object with w3gjs-specific parameters used during parsing:

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `trackingInterval` | number | library-derived | Bucket width in milliseconds for the per-player `actions.timed` series (default `60000` = 1 minute). |

## §map

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `path` | string | replay-native | Full in-game path to the map file (e.g., `"Maps/Download/Season1/(8)RoyalGardens_S2_v1.2.w3x"`). |
| `file` | string | replay-native | Map filename without directory. |
| `checksum` | string | replay-native | Map CRC/checksum as hex string. |
| `checksumSha1` | string | replay-native | Map content SHA-1 as hex string. |

## §settings

Game lobby options.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `referees` | boolean | replay-native | Referees allowed. |
| `observerMode` | string | replay-native | One of the observer modes (`"NONE"`, `"ON_DEFEAT"`, `"FULL"`, `"REFEREES"`) — exact enumeration per w3gjs. |
| `fixedTeams` | boolean | replay-native | Teams fixed at lobby time. |
| `fullSharedUnitControl` | boolean | replay-native | Full shared unit control among allies. |
| `alwaysVisible` | boolean | replay-native | Always-visible lobby setting. |
| `hideTerrain` | boolean | replay-native | Terrain hidden until discovered. |
| `mapExplored` | boolean | replay-native | Map fully explored at start. |
| `teamsTogether` | boolean | replay-native | Teams placed together on the map. |
| `randomHero` | boolean | replay-native | Random hero setting. |
| `randomRaces` | boolean | replay-native | Random race setting. |
| `speed` | number | replay-native | Game speed index. |

## §chat

Array of chat-message objects in send order.

Each entry:

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `playerName` | string | replay-native | Sender's battle.net name (e.g., `"ownage#21776"`). |
| `playerId` | number | replay-native | Sender's in-replay player id. |
| `message` | string | replay-native | Chat text, UTF-8. |
| `mode` | string | library-derived | Channel w3gjs classified the message into (e.g., `"All"`, `"Team"`, `"Private"`, `"Observer"`). |
| `timeMS` | number | replay-native | In-game milliseconds at which the message was sent. |

Empty array when the replay contained no chat (e.g., `base_2.w3g`).

## §players

Array of player entries. One entry per non-observer slot.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `id` | number | replay-native | Player slot id. |
| `name` | string | replay-native | Player battle.net name. |
| `teamid` | number | replay-native | Team id (0-based). |
| `color` | string | library-derived | Player color as `#rrggbb` hex — w3gjs translates the replay's color index. |
| `race` | string | replay-native | Race chosen in lobby. `"H"` Human, `"O"` Orc, `"U"` Undead, `"N"` Night Elf, `"R"` Random. |
| `raceDetected` | string | library-derived | Race w3gjs inferred from the first units/buildings trained when `race === "R"`; equal to `race` otherwise. |
| `apm` | number | library-derived | Average actions-per-minute over the game. |
| `groupHotkeys` | object | library-derived | Per-hotkey (0–9) `{ assigned: number, used: number }` counts. |
| `heroes` | array | mixed | Heroes the player used. See §player.heroes. |
| `resourceTransfers` | array | replay-native | Gold/lumber transfers to allies. See §player.resourceTransfers. |
| `actions` | object | library-derived | Action counts by category plus the per-minute series. See §player.actions. |
| `buildings` | object | mixed | Buildings constructed: `order` (replay-native) plus `summary` (library-derived). See §player.productionSection. |
| `units` | object | mixed | Units trained: same shape as buildings. See §player.productionSection. |
| `upgrades` | object | mixed | Upgrades researched: same shape as buildings. See §player.productionSection. |
| `items` | object | mixed | Items acquired: same shape as buildings. See §player.productionSection. |

### §player.heroes

Array of hero objects. Each:

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `id` | string | replay-native | Hero unit id (e.g., `"Nfir"`). |
| `level` | number | library-derived | Final hero level w3gjs inferred (ability-point count). |
| `abilities` | object | library-derived | Map of hero-ability id → level count. |
| `abilityOrder` | array | replay-native | Ordered list of `{ type: "ability", time: ms, value: abilityId }` learning events. |

### §player.resourceTransfers

Array of gold/lumber transfer events sent by this player.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `slot` | number | replay-native | Sender slot. |
| `gold` | number | replay-native | Gold sent. |
| `lumber` | number | replay-native | Lumber sent. |
| `playerId` | number | replay-native | Recipient player id. |
| `playerName` | string | replay-native | Recipient battle.net name. |
| `msElapsed` | number | replay-native | In-game milliseconds at which the transfer occurred. |

### §player.actions

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `timed` | array of number | library-derived | Action count per time bucket (`apm.trackingInterval` ms wide), in chronological order. |
| `assigngroup` | number | library-derived | Count of assign-to-hotkey-group actions. |
| `rightclick` | number | library-derived | Count of right-click actions. |
| `basic` | number | library-derived | Count of basic actions (move, stop, hold, etc.). |
| `buildtrain` | number | library-derived | Count of build/train commands. |
| `ability` | number | library-derived | Count of ability activations. |
| `item` | number | library-derived | Count of item actions. |
| `select` | number | library-derived | Count of selection actions. |
| `removeunit` | number | library-derived | Count of remove-unit actions. |
| `subgroup` | number | library-derived | Count of subgroup-change actions. |
| `selecthotkey` | number | library-derived | Count of hotkey-group selections. |
| `esc` | number | library-derived | Count of ESC key events. |

### §player.productionSection

Shape shared by `buildings`, `units`, `upgrades`, and `items`:

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `order` | array | replay-native | Construction/training order, each `{ id: string, ms: number }` where `id` is the WC3 object id and `ms` is in-game milliseconds. |
| `summary` | object | library-derived | Map of object id → total count built/trained/researched/acquired. |

---

## Authoritative completeness

At the time of writing, the union of top-level keys observed across
both committed fixtures is exactly the set listed in the top-level
table above. This was verified programmatically during T014 (see
`specs/001-replay-parser/tasks.md`).

If `w3gjs` is upgraded or the fixture set changes and the output
gains or loses a top-level key, this document MUST be updated in
the same change. That rule lives in the project constitution
(Principle IV and the Governance section) and in `spec.md`
(FR-007).
