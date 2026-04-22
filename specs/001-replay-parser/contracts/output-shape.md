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
   by `parser/package.json`, serialized via
   `JSON.stringify(result, null, 1)` (1-space indentation) with a
   trailing newline. Formatting is for human readability; it is
   not part of the semantic contract — consumers MUST rely on
   `JSON.parse` rather than on any specific byte layout.
4. The parser adds no keys of its own to the root object. It also
   strips no keys.

Consumers SHOULD consult `parser/DATA.md` for the meaning of each
key and whether it originates from the replay binary or from
`w3gjs`'s internal derivation.

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
  analytical values computed by this project's code (FR-003).
  Values computed inside `w3gjs` pass through untouched — they are,
  by project convention, part of "what the canonical library
  exposes" and are noted as library-derived in `parser/DATA.md`.

## Contract tests

The fixture-based tests at `parser/test/parse.test.js` enforce this
contract by:

1. Running the parser against each committed fixture.
2. Reading the resulting `.json` file from disk.
3. Asserting that `JSON.parse` succeeds and yields a non-null
   object.
4. Asserting that the parsed object deep-equals the value returned
   by `W3GReplay.parse()` for the same input in the same run
   (confirms invariant #3: no stripping, no injection).

Tests SHOULD NOT assert on specific field presence (e.g., a
`players` key) beyond what is necessary to demonstrate the
round-trip invariant. Asserting specific fields couples the tests
to `w3gjs`'s internal shape, which this contract does not govern.
