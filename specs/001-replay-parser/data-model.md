# Phase 1 Data Model: Replay Parser

**Feature**: Replay Parser (`specs/001-replay-parser`)
**Date**: 2026-04-21

This feature has a very narrow data model: it transforms one on-disk
entity into another on-disk entity, with a documentation artifact
describing the transformation's output shape. There is no database,
no persistent state, and no in-memory model beyond what `w3gjs`
returns during a single run.

## Entities

### Replay File (input)

- **Representation**: A binary `.w3g` file on the local filesystem.
- **Identity**: Its filesystem path.
- **Source**: The Warcraft III game client at the time a match was
  recorded.
- **Validation**: Treated as valid if and only if `w3gjs` can parse
  it. The parser itself performs no pre-validation.
- **Lifecycle**: Read-only input. The parser never writes to this
  file.
- **Fixtures in-repo**: `sample_replays/base_1.w3g`,
  `sample_replays/base_2.w3g`.

### Parse Output (artifact)

- **Representation**: A single JSON file on the local filesystem.
- **Identity**: Its filesystem path, derived deterministically from
  the input's path by appending `.json` (see
  `contracts/output-shape.md`).
- **Content**: The complete object returned by
  `W3GReplay.parse()`, serialized via `JSON.stringify`. No fields
  added by the parser; no fields stripped. See
  `contracts/output-shape.md` for the top-level shape contract, and
  `parser/DATA.md` (produced during implementation) for the full
  field catalogue.
- **Validation**: The file MUST be parseable by `JSON.parse`; no
  other runtime validation is performed by the parser.
- **Lifecycle**: Written once per successful parse. Overwritten on
  subsequent runs (FR-006). Never written on failed parse (FR-005).

### Structure Documentation (deliverable)

- **Representation**: A Markdown file at `parser/DATA.md`.
- **Identity**: Its filesystem path inside the repo.
- **Content**: Describes every field of the Parse Output — name,
  type, origin (replay-native vs. library-derived), and meaning.
  Grouped by top-level key, with nested sections for nested objects
  and arrays.
- **Validation**: Reviewed by a human in the same pull request that
  introduces or changes the parser. There is no automated schema
  check in v1.
- **Lifecycle**: Updated in the same change as any modification to
  the parser's output shape (FR-007).

## Relationships

- One Replay File → one Parse Output (one-to-one, by path).
- One Parse Output is described by one Structure Documentation
  (many-to-one at the file-instance level: any number of parse
  outputs share the same documentation, because they all conform to
  the same shape).

## State transitions

The parser is stateless. A single invocation goes through exactly
one transition:

```
[start]
   │
   ├── input path unreadable / missing ──▶ fail: stderr + non-zero exit, no output file
   │
   ├── w3gjs throws                    ──▶ fail: stderr + non-zero exit, no output file
   │
   └── w3gjs returns                    ──▶ success: write JSON next to input, exit 0
```

No retries, no partial writes, no persistent cursor or state file.

## Derived values

None produced by this feature. The Parse Output is the library's
output, verbatim. `w3gjs` may include values it derives internally
(for example, `matchup` or per-player `apm`); those are, by this
project's convention, part of "what the canonical library exposes"
and travel through unchanged (see `research.md` §3 and spec
Assumptions). They are NOT derived by this feature's code.
