# Contract: Analysis Output Shape

Structural contract for the JSON document the analyzer writes. The
authoritative field-level documentation lives in `processor/DATA.md`
(delivered with the analyzer code); this contract captures the
invariants that tests and downstream consumers rely on.

## Top-level keys

The root is a JSON object with EXACTLY these seven keys:

```text
{
  "match":       { ... },
  "settings":    { ... },
  "map":         { ... },
  "players":     [ ... ],
  "observers":   [ ... ],
  "chat":        [ ... ],
  "diagnostics": { ... }
}
```

No extra top-level keys. Adding or removing a top-level key is a
breaking change that requires updating `processor/DATA.md` and the
Visualizer in the same pull request.

## Invariants

The following MUST hold for every analysis document, regardless of
replay content:

1. **Key set exactly matches** the seven listed above.
2. `match` is an object; `settings` is an object; `map` is an
   object; `diagnostics` is an object.
3. `players`, `observers`, `chat` are arrays (possibly empty).
4. `match.durationMs` is a non-negative integer.
5. `match.winner` is either `null` OR an object with a single
   integer key `teamId`. No other shape.
6. Each `players[i]` is an object with the key set documented in
   `processor/DATA.md` (`id`, `name`, `teamId`, `color`, `race`,
   `raceDetected`, `apm`, `isWinner`, `actions`, `groupHotkeys`,
   `heroes`, `production`, `resourceTransfers`).
7. `players[i].race` ∈ `{"H","O","U","N","R"}`.
8. `players[i].raceDetected` ∈ `{"H","O","U","N"}` (random is
   resolved by the parser; the analyzer does not preserve `"R"`
   here).
9. `players[i].isWinner === true` for every player whose
   `teamId === match.winner.teamId` when `match.winner` is
   non-null; `false` otherwise.
10. `players[i].production` has exactly four sub-keys:
    `buildings`, `units`, `upgrades`, `items`. Each is an object
    with exactly two keys: `order` (array) and `summary` (object).
11. Every entity reference across the document (hero, unit,
    building, upgrade, item, hero ability) is an object of shape
    `{ id: string, name: string, unknown: boolean, ...extras }`.
    `id` is a 4-character string, `name` is non-empty, `unknown`
    is a boolean. When `unknown` is `true`, `name === id`.
12. `chat[i]` has the key set `{ playerId, playerName, mode, text,
    timeMs }`.
13. `diagnostics.unmappedEntityIds` is an array whose entries each
    have shape `{ category: string, id: string }`. Deduplicated by
    `(category, id)`. Empty when no unmapped IDs were encountered.
14. `diagnostics.parserId` equals `ParserOutput.id` verbatim.
15. Timestamps are integers in milliseconds in every field whose
    name ends with `Ms` or `TimeMs`.

## Non-invariants (explicit)

The following are NOT guaranteed and MUST NOT be relied on:

- **Field order within an object**: JSON objects are unordered per
  the spec; the analyzer may emit keys in any stable order.
- **`diagnostics.parserParseTimeMs` stability**: forwarded
  non-deterministic parser value (R9).
- **Array order within `summary` objects**: `summary` is an object
  map, not an array; key iteration order is insertion order per
  Python 3.7+ but consumers should not depend on it.
- **Presence of trailing newline in the output file**: analyzer
  writes with `json.dump` + one trailing `\n`; consumers should
  parse the whole file, not tail-match.

## Compatibility

Additions of new nested fields within existing top-level objects are
NOT breaking as long as they are additive and documented in
`processor/DATA.md` in the same change. A field rename, removal, or
semantic change IS breaking.
