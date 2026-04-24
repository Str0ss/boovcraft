# Analyzer Output Data Structure

This document describes the JSON document produced by `processor/analyze.py`
when run against a Parser-layer JSON file. It is the contract between the
Processor layer and the Visualizer layer, and the only document a developer
needs to know which fields are available and how to locate them.

See also:
- `specs/002-replay-analyzer/contracts/output-shape.md` — formal invariants.
- `specs/002-replay-analyzer/contracts/mapping-shape.md` — entity-name
  mapping shape.
- `parser/DATA.md` — upstream: the shape of the input this analyzer consumes.

## Scope of this analyzer

The analyzer emits one analysis document per replay. Input is the JSON file
the Parser layer wrote for that replay. Output is a JSON file written next
to the input with the suffix `.analysis.json` (see `Output location`).

The analyzer is pure: given the same input parser-output and the same
`processor/entity_names.json`, it produces byte-identical output except for
the single forwarded field `diagnostics.parserParseTimeMs`, which reflects
wall-clock parse time inside `w3gjs` and varies across runs.

## Output location

Running `python processor/analyze.py <path>/<name>.w3g.json` writes the JSON
document to `<path>/<name>.w3g.analysis.json`. Any existing file at that
path is overwritten.

If the input path does not end in `.json`, `.analysis.json` is appended
without stripping.

## Volatility

One field varies across runs for the same input:

- `diagnostics.parserParseTimeMs` — wall-clock milliseconds `w3gjs` spent
  parsing. Forwarded from the parser output verbatim; see `parser/DATA.md`.

All other fields are content-deterministic for a given parser-output.

## Top-level keys

The root is a JSON object with exactly these seven keys. Each appears
unconditionally.

| Key | Type | Meaning |
|---|---|---|
| `match` | object | Match-level metadata. See §match. |
| `settings` | object | Lobby settings, forwarded from parser output. See §settings. |
| `map` | object | Map path, filename, and checksums, forwarded from parser output. See §map. |
| `players` | array | One entry per non-observer player, in slot order. See §players. |
| `observers` | array of string | Observer names, forwarded from parser output (slot order). |
| `chat` | array | All in-game chat messages in send order. Empty array if none. See §chat. |
| `diagnostics` | object | Parser pass-through and analyzer-emitted diagnostics. See §diagnostics. |

## §match

| Key | Type | Origin (parser field) | Meaning |
|---|---|---|---|
| `version` | string | `version` | Game version string, e.g. `"2.00"`. |
| `buildNumber` | number | `buildNumber` | WC3 build number recorded in the replay header. |
| `durationMs` | number | `duration` | In-game duration in milliseconds. |
| `gameType` | string | `type` | Team-size shorthand derived by w3gjs, e.g. `"4on4"`. |
| `matchup` | string | `matchup` | Race matchup shorthand, e.g. `"HHNUvHHOO"`. |
| `startSpots` | number | `startSpots` | Starting spots on the map. |
| `expansion` | boolean | `expansion` | True if TFT expansion data is present. |
| `gameName` | string | `gamename` | Lobby/game name. |
| `creator` | string | `creator` | Game creator identifier, e.g. `"Battle.net"`. |
| `randomSeed` | number | `randomseed` | Replay's random seed. |
| `winner` | object \| null | `winningTeamId` | `{ "teamId": n }` when `winningTeamId >= 0`, else `null`. |

## §settings

Lobby options, forwarded verbatim from `parser_output.settings`. Keys:
`referees`, `observerMode`, `fixedTeams`, `fullSharedUnitControl`,
`alwaysVisible`, `hideTerrain`, `mapExplored`, `teamsTogether`,
`randomHero`, `randomRaces`, `speed`. See `parser/DATA.md §settings` for
types and meanings.

## §map

Forwarded verbatim from `parser_output.map`:

| Key | Type | Meaning |
|---|---|---|
| `path` | string | Full in-game path to the map file. |
| `file` | string | Map filename without directory. |
| `checksum` | string | Map CRC/checksum as hex string. |
| `checksumSha1` | string | Map content SHA-1 as hex string. |

## §players

Array of player entries. One per non-observer slot.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `id` | number | `players[].id` | Player slot id. |
| `name` | string | `players[].name` | Player battle.net name. |
| `teamId` | number | `players[].teamid` | Team id (0-based). |
| `color` | string | `players[].color` | Player color as `#rrggbb`. |
| `race` | string | `players[].race` | Race chosen in lobby. `"H"` Human, `"O"` Orc, `"U"` Undead, `"N"` Night Elf, `"R"` Random. |
| `raceDetected` | string | `players[].raceDetected` | Race w3gjs inferred from the first units/buildings trained when `race === "R"`; equal to `race` otherwise. |
| `apm` | number | `players[].apm` | Average actions-per-minute over the game. |
| `isWinner` | boolean | derived | `true` iff `match.winner` is non-null AND this player's `teamId` equals `match.winner.teamId`. |
| `actions` | object | mixed | Action counts plus per-bucket timeline. See §players.actions. |
| `groupHotkeys` | object | `players[].groupHotkeys` | Forwarded: per-hotkey (`0`–`9`) `{ assigned, used }` counts. |
| `heroes` | array | mixed | Heroes the player used. See §players.heroes. |
| `production` | object | mixed | Buildings, units, upgrades, items produced. See §players.production. |
| `resourceTransfers` | array | `players[].resourceTransfers` | Gold/lumber transfers this player sent to allies. See §players.resourceTransfers. |

### §players.actions

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `apmTimeline.bucketWidthMs` | number | `apm.trackingInterval` | Bucket width for `buckets`, in milliseconds. |
| `apmTimeline.buckets` | array of number | `players[].actions.timed` | Per-bucket action count in chronological order. |
| `totals` | object | `players[].actions` minus `timed` | Action-count totals by category: `assigngroup`, `rightclick`, `basic`, `buildtrain`, `ability`, `item`, `select`, `removeunit`, `subgroup`, `selecthotkey`, `esc`. All numbers. |

### §players.heroes

Array of hero objects. Each is shaped like an "entity reference" (see
"Entity references" below) plus hero-specific fields:

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `id` | string | `heroes[].id` | 4-char hero unit id (e.g., `"Nfir"`). When `w3gjs` could not attribute a unit id (observed with some random-race heroes), the id is the sentinel `"UNKN"` and `unknown` is `true`. |
| `name` | string | from `entity_names.json` | Display name (e.g., `"Firelord"`). Falls back to `id` when `unknown` is true. |
| `unknown` | boolean | derived | `true` when `id` is not in the mapping (or is the `"UNKN"` sentinel). |
| `level` | number | `heroes[].level` | Final hero level w3gjs inferred. |
| `abilityOrder` | array | mixed | Chronological ability-learn sequence. Each entry: `{ id, name, unknown, timeMs, level }` where `level` is the ordinal (1, 2, 3, ...) of this ability within the hero's own learn sequence. |
| `abilitySummary` | object | mixed | Map of ability id → `{ id, name, unknown, level }` where `level` is the final learned count (pass-through of the parser's `abilities` map value). |

### §players.production

Object with exactly these four sub-keys: `buildings`, `units`, `upgrades`,
`items`. Each sub-key has this shape:

| Key | Type | Meaning |
|---|---|---|
| `order` | array | Chronological sequence. Each entry: `{ id, name, unknown, timeMs }`. |
| `summary` | object | Map of entity id → `{ id, name, unknown, count }`. |

`order` preserves the parser's chronological sequence from
`player.<category>.order`. `summary` preserves the parser's per-id totals
from `player.<category>.summary`, annotated with display names.

### §players.resourceTransfers

Array of gold/lumber transfers this player sent to allies.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `fromSlot` | number | `resourceTransfers[].slot` | Sender slot. |
| `toPlayerId` | number | `resourceTransfers[].playerId` | Recipient player id. |
| `toPlayerName` | string | `resourceTransfers[].playerName` | Recipient battle.net name. |
| `gold` | number | `resourceTransfers[].gold` | Gold sent. |
| `lumber` | number | `resourceTransfers[].lumber` | Lumber sent. |
| `timeMs` | number | `resourceTransfers[].msElapsed` | In-game milliseconds of the transfer. |

## §chat

Array of chat-message objects in send order.

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `playerId` | number | `chat[].playerId` | Sender player id. |
| `playerName` | string | `chat[].playerName` | Sender battle.net name. |
| `mode` | string | `chat[].mode` | Channel (`"All"`, `"Team"`, `"Private"`, `"Observer"`). |
| `text` | string | `chat[].message` | UTF-8 chat text. |
| `timeMs` | number | `chat[].timeMS` | In-game milliseconds at which the message was sent. |

Empty array when no chat (e.g., `base_2.w3g`).

## §diagnostics

| Key | Type | Origin | Meaning |
|---|---|---|---|
| `parserId` | string | `id` | Stable hex hash `w3gjs` derived from replay content. |
| `parserParseTimeMs` | number | `parseTime` | **Volatile.** Wall-clock ms w3gjs spent parsing. |
| `unmappedEntityIds` | array | derived | Every entity id encountered that was absent from `entity_names.json`. Deduplicated by `(category, id)`. Shape per entry: `{ category, id }`. Empty array when all entities resolved. |
| `analyzerVersion` | string | `pyproject.toml` | Analyzer semver at the time of the run. |

## Entity references

Throughout the document, any place that names a WC3 entity uses a common
shape — an "entity reference" object:

```json
{
  "id":      "Nfir",
  "name":    "Firelord",
  "unknown": false
}
```

- `id` is always a 4-character string.
- `name` is a human-readable display name from `entity_names.json`.
- `unknown` is `true` when `id` is not in the mapping; in that case
  `name === id` (the raw id is used as the placeholder).

Some references carry extra fields on top — e.g., hero entries add
`level`/`abilityOrder`/`abilitySummary`; production-order entries add
`timeMs`; production-summary entries add `count`; hero-ability entries add
`timeMs`/`level`.

## Scope exclusions (data model)

The analyzer intentionally omits:

- **Event-level action streams.** `parser_output.events[]` is not consumed.
  The aggregated `players[]` fields already carry everything needed for
  MVP-scope visualizations. An action heatmap or command timeline is a
  future Processor-layer feature and stays a Processor-layer change.
- **Derived win inference.** `match.winner` is a pass-through of the
  parser's `winningTeamId`. The analyzer does not second-guess it.
- **Preformatted display strings.** No `mm:ss`-formatted timestamps, no
  thousands-separator-formatted numbers. Visualizer owns presentation.
- **Internationalization.** Names are English-only (source: w3gjs's own
  tables).

## Mapping coverage

The `processor/entity_names.json` file is generated by
`processor/tools/build_entity_names.py` from `w3gjs`'s own data tables.
Coverage is required for:

| Race | Heroes | Non-hero units | Buildings | Upgrades | Items |
|---|---|---|---|---|---|
| Human | `Hamg` (Archmage), `Hmkg` (Mountain King), `Hpal` (Paladin), `Hblm` (Blood Mage) | Peasant, Footman, Rifleman, Priest, Sorceress, Knight, Mortar Team, Siege Engine, Gryphon Rider, Flying Machine, Spell Breaker, Dragonhawk Rider | Town Hall, Keep, Castle, Altar of Kings, Barracks, Farm, Lumber Mill, Blacksmith, Workshop, Arcane Sanctum, Gryphon Aviary, Arcane Vault, Scout Tower, Guard Tower, Cannon Tower, Arcane Tower | Standard ladder set (armor, weapons, training, defend, …) | Standard ladder shop inventory |
| Orc | `Obla` (Blademaster), `Ofar` (Far Seer), `Otch` (Tauren Chieftain), `Oshd` (Shadow Hunter) | Peon, Grunt, Troll Headhunter, Shaman, Witch Doctor, Raider, Kodo Beast, Tauren, Troll Batrider, Wind Rider, Spirit Walker, Troll Berserker, Demolisher | Great Hall, Stronghold, Fortress, Altar of Storms, Barracks, Burrow, Voodoo Lounge, War Mill, Beastiary, Spirit Lodge, Tauren Totem, Watch Tower | Standard ladder set | Standard |
| Undead | `Udea` (Death Knight), `Ucrl` (Crypt Lord), `Udre` (Dreadlord), `Ulic` (Lich) | Acolyte, Ghoul, Crypt Fiend, Gargoyle, Abomination, Necromancer, Banshee, Meat Wagon, Shade, Obsidian Statue, Destroyer, Frost Wyrm | Necropolis, Halls of the Dead, Black Citadel, Altar of Darkness, Crypt, Graveyard, Sacrificial Pit, Slaughterhouse, Tomb of Relics, Boneyard, Temple of the Damned, Ziggurat | Standard ladder set | Standard |
| Night Elf | `Edem` (Demon Hunter), `Emoo` (Priestess of the Moon), `Ekee` (Keeper of the Grove), `Ewar` (Warden) | Wisp, Archer, Huntress, Dryad, Hippogryph, Druid of the Talon, Druid of the Claw, Chimaera, Mountain Giant, Faerie Dragon, Glaive Thrower | Tree of Life, Tree of Ages, Tree of Eternity, Altar of Elders, Ancient of War, Ancient of Lore, Ancient of Wind, Hunter's Hall, Chimaera Roost, Moon Well, Ancient of Wonders | Standard ladder set | Standard |
| Neutral / Tavern | `Nfir` (Firelord), `Nbrn` (Dark Ranger), `Npbm` (Pandaren Brewmaster), `Nbst` (Beastmaster), `Nngs` (Naga Sea Witch), `Nalc` (Goblin Alchemist), `Ntin` (Goblin Tinker), `Nplh` (Pit Lord) | — | — | — | — |

This is the one-time SC-003 review checklist. When `entity_names.json` is
regenerated (after a `w3gjs` upgrade), a reviewer walks this table against
the new mapping and accepts or amends the diff in the same pull request.

## Regeneration

To regenerate `processor/entity_names.json`:

```bash
python processor/tools/build_entity_names.py
```

To check whether the committed mapping is up to date with `w3gjs`:

```bash
python processor/tools/build_entity_names.py --check
```

Exits non-zero if the committed file and the freshly-extracted mapping
differ. Suitable for a pre-merge sanity check after a `w3gjs` upgrade.

Known manual overrides (entries observed in real fixtures but absent from
`w3gjs`'s published mapping tables) are listed in
`processor/tools/build_entity_names.py` under `MANUAL_OVERRIDES`. Add new
overrides only when a real fixture produces an unmapped id belonging to
standard WC3:TFT content. Do not speculate.
