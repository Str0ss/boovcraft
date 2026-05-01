# Input Contract: Visualizer Tabs

The Visualizer's input contract is the Processor's
`*.analysis.json` document. Feature 002 defined the v1 contract;
feature 004 extends it **additively** with one new field per
player.

## Inherited contract (feature 002 / 003)

The Visualizer consumes a single JSON document with these
top-level keys:

- `match` — match-level facts (id, version, duration, type,
  matchup, map, winner)
- `players[]` — per-player records, grouped externally by team via
  `teamId`
- `chat[]` — chat messages
- `observers[]` — observer names
- `settings` — game settings (passthrough)
- `diagnostics` — processor diagnostics (passthrough)
- `map` — map metadata

Within each `players[]` element:

- `id`, `name`, `color`, `race`, `raceDetected`, `apm`,
  `isWinner`, `teamId`
- `actions` — see "Additive change" below
- `groupHotkeys` — passthrough
- `heroes[]` — hero entries with `abilityOrder` and final `level`
- `production[]` — flat list of timestamped production entries
  with embedded display names
- `resourceTransfers[]` — gold/lumber transfers with timestamps

The Visualizer's feature 003 contract (FR-007: render
`unknown: true`-flagged entities with the raw id and a visible
marker; FR-008: rely only on data present in the loaded JSON) is
preserved unchanged.

## Additive change introduced by this feature

The `players[].actions` object gains one new field:

| Field | Type | Required | Description |
|---|---|---|---|
| `players[].actions.timedActions` | `Array<{ timeMs: integer, category: string }>` | yes (may be empty) | Chronological per-player input-action stream extracted from the parser's `events[].commandBlocks[].actions[]`. Each entry's `category` is one of the same labels used by `actions.totals`. |

`apmTimeline` and `totals` keep their existing shape and meaning.

### Compatibility guarantees

- A consumer that does not know about `timedActions` (for example,
  the unmodified feature-003 visualizer) MUST still load and
  render the analysis JSON without error.
- A consumer that knows about `timedActions` (the feature-004
  Visualizer) MUST tolerate an empty array gracefully.
- The Processor MUST emit the field for every player, even when
  the per-player record is empty (empty array, not omitted, not
  `null`). This keeps Visualizer code branchless on the read side.

### Invariant the Processor MUST honor

For every player and every action category `c` present in
`players[].actions.totals`:

```text
count_of(timedActions, where category == c) == totals[c]
```

The Processor's pytest suite verifies this on both committed
fixtures.

## Things that are NOT changing

- The Parser's output JSON shape (parser/parse.js) is unchanged.
  The Parser already exposes `events[].commandBlocks[].actions[]`
  and per-player `player.actions.{...}` totals; the Processor
  consumes that existing data.
- The `*.w3g.json` parser-output fixtures
  (`sample_replays/base_*.w3g.json`) are unchanged.
- The `processor/entity_names.json` mapping is unchanged.
- The Processor's other top-level outputs (`match`, `chat`,
  `observers`, `settings`, etc.) are unchanged.

## Regenerating the fixtures

After the Processor change is shipped, the committed-fixture
analysis JSONs MUST be regenerated locally to exercise the new
field:

```sh
python processor/analyze.py sample_replays/base_1.w3g.json
python processor/analyze.py sample_replays/base_2.w3g.json
```

The `*.analysis.json` files remain `.gitignore`d (regenerable,
deterministic). The Visualizer is exercised against the
locally-regenerated copies, not committed JSON.
