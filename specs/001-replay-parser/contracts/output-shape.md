# Contract: Parse Output JSON Shape

**Feature**: Replay Parser (`specs/001-replay-parser`)
**Layer**: Parser → Processor boundary

This contract governs the JSON document the parser writes to disk.
It defines only the structural invariants that downstream consumers
(the Processor layer, and fixture-based tests) MAY rely on. It does
NOT enumerate every field produced by `w3gjs` — that full catalogue
lives in `parser/DATA.md`, which is produced during implementation
and evolves with `w3gjs`.

## Path

- **Location**: The output is written at `<input-path>.json`.
- **Example**: Input `sample_replays/base_1.w3g` → output
  `sample_replays/base_1.w3g.json`.
- **Overwrite**: Any file already present at that path is
  overwritten without prompting (FR-006).

## Top-level invariants

Consumers MAY rely on the following structural properties of the
written document:

1. The file parses successfully via `JSON.parse` (and any standard
   JSON parser in other languages).
2. The root value is a JSON object (`{...}`).
3. The root object is the complete, unmodified return value of
   `W3GReplay.parse(<input-buffer>)` in the `w3gjs` version pinned
   by `parser/package.json`, **plus one additional top-level key
   — `events` — holding the complete raw stream of
   `'gamedatablock'` events emitted by `W3GReplay` during the same
   parse, in emission order**. The combined object is serialized
   via `JSON.stringify(result, null, 1)` (1-space indentation)
   with a trailing newline. Formatting is for human readability;
   it is not part of the semantic contract — consumers MUST rely
   on `JSON.parse` rather than on any specific byte layout.
4. Apart from `events`, the parser adds no keys of its own. It
   also strips no keys that `W3GReplay.parse()` returned.

The `events` key is the parser's one concession: `w3gjs` exposes
the raw event stream only via its `EventEmitter` interface, not
via the `.parse()` return value. Persisting both together is
required to satisfy FR-002 ("extract every piece of data that the
canonical parsing library exposes").

Consumers SHOULD consult `parser/DATA.md` for the meaning of each
key — both the `.parse()` fields and the `events` stream.

## What this contract does NOT promise

- It does NOT promise that any specific key (e.g., `version`,
  `players`, `chat`) is present. That depends on the `w3gjs`
  version. `parser/DATA.md` is the authoritative enumeration.
- It does NOT promise stability across `w3gjs` major-version
  upgrades. Such an upgrade is a library change and is accompanied
  by a matching update to `parser/DATA.md` in the same change
  (FR-007).
- It does NOT promise byte-identity of the output across runs.
  `w3gjs` may include non-deterministic fields; any observed
  non-determinism is documented in `parser/DATA.md`.
- It does NOT include, nor permit the parser to include, any
  analytical values computed by **this project's code** (FR-003
  as clarified in `spec.md`). Values computed inside `w3gjs` —
  whether in the `.parse()` return value (per-player `apm`,
  action counts, `matchup`, `winningTeamId`, etc.) or in the
  `events` stream — pass through untouched. By project convention
  both are part of "what the canonical library exposes" and are
  noted accordingly in `parser/DATA.md`.

## Contract tests

The fixture-based tests at `parser/test/parse.test.js` enforce this
contract by:

1. Running the parser against each committed fixture.
2. Reading the resulting `.json` file from disk.
3. Asserting that `JSON.parse` succeeds and yields a non-null
   object.
4. Asserting that the parsed object deep-equals the combined
   `W3GReplay.parse()` return value + captured `'gamedatablock'`
   event stream for the same input in the same run (confirms
   invariant #3: no stripping, no injection, no events dropped).
5. Asserting that `events` is a non-empty array (every valid
   replay contains at least TimeSlot and LeaveGame events).

Tests SHOULD NOT assert on specific field presence beyond these
invariants. Asserting specific fields couples the tests to
`w3gjs`'s internal shape, which this contract does not govern.
