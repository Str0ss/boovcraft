# Phase 0 Research: Replay Parser

**Feature**: Replay Parser (`specs/001-replay-parser`)
**Date**: 2026-04-21

This document consolidates the decisions needed to move from the
specification into implementation. All `NEEDS CLARIFICATION` items from
the Technical Context are resolved here.

## 1. Node.js runtime version

- **Decision**: Node.js 20 LTS.
- **Rationale**: LTS, widely available, supports the built-in `node:test`
  runner and top-level `await`. No features from newer versions are
  required.
- **Alternatives considered**:
  - Node 22 (current): newer than necessary; no needed features.
  - Node 18: EOL schedule is nearer; no reason to prefer over 20 LTS.

## 2. Parser library

- **Decision**: `w3gjs` (latest stable from npm).
- **Rationale**: Mandated by the constitution, Principle II. Using its
  default high-level parse output captures "everything the library
  exposes" (FR-002, SC-002).
- **Alternatives considered**: None eligible. Principle II forbids
  alternatives.

## 3. Parser output shape (what we persist)

- **Decision**: Serialize the complete object returned by
  `W3GReplay.parse()` (the library's default high-level output) as a
  single JSON document. No projection, no field stripping, no
  reinterpretation. If `w3gjs` computes values internally (e.g.,
  `apm`, `matchup`), those travel through untouched — they are what the
  canonical library exposes, and the project treats the library's
  output as the definition of "raw" (see spec Assumptions).
- **Rationale**: This is the smallest possible parser (Principle III),
  fully delegates to `w3gjs` (Principle II), and makes "100% of exposed
  fields" (SC-002) trivially true — the parser IS the library's output,
  JSON-stringified.
- **Alternatives considered**:
  - Capture only low-level `gamedatablock` events via `EventEmitter` and
    omit the high-level return value. Rejected: loses the library's
    derived convenience fields (matchup, player summaries) that
    downstream code will almost certainly want, and forces us to
    reimplement what the library already gives us for free.
  - Strip library-derived fields (e.g., `apm`) to satisfy a literal
    reading of FR-003. Rejected: FR-003 prohibits *our* analytical
    logic, not the library's; stripping also makes the output
    fundamentally less useful and violates FR-002 ("every piece of
    data the library exposes").
  - Capture both the high-level return and the low-level event stream
    to maximize coverage. Rejected for now as YAGNI (Principle III);
    will revisit only if a concrete downstream need surfaces a gap.

## 4. Output file naming and location

- **Decision**: Write the JSON next to the input file, appending
  `.json` to the input filename. A replay at
  `sample_replays/base_1.w3g` yields `sample_replays/base_1.w3g.json`.
- **Rationale**: Deterministic, requires no config (Principle III),
  preserves the `.w3g` segment in the output name so the origin is
  always obvious. Overwrite semantics (FR-006) apply if the file
  already exists.
- **Alternatives considered**:
  - Replace the extension (`base_1.json`). Rejected: could collide with
    an unrelated `base_1.json` if both exist.
  - Write under a separate `parsed/` directory. Rejected: introduces
    configuration surface; downstream layers would need to know about
    the directory convention.
  - Configurable output path via a flag. Rejected as YAGNI for v1.

## 5. CLI surface

- **Decision**: `node parse.js <path-to-replay>` — one positional
  argument, no flags. Exits 0 on success, non-zero on failure with a
  single-line diagnostic on stderr.
- **Rationale**: Smallest possible surface (Principle III). The
  downstream processor invokes the parser by shelling out with a path;
  nothing else is required.
- **Alternatives considered**:
  - A flag system (`--output`, `--verbose`, `--format`). Rejected:
    no current use case.
  - A library export that the processor imports directly in-process.
    Rejected: violates Principle I (the processor runs in Python and
    must consume a JSON file, not call Node code).

## 6. Error handling strategy

- **Decision**: Fail fast on any error. Catch exceptions from `w3gjs`,
  print a single clear diagnostic to stderr that names the input file
  and the underlying error, and exit non-zero. Never write a partial
  output file. If `w3gjs` itself signals a partial/truncated replay
  via its return value, pass that signal through in the JSON output
  unchanged (spec's Edge Cases — "truncated replay").
- **Rationale**: Matches FR-005 exactly. Using the library's own
  error semantics avoids reinventing what w3gjs already reports.
- **Alternatives considered**:
  - Structured JSON error output on stdout. Rejected: makes the
    "output file on disk is the sole success signal" rule ambiguous;
    stderr + exit code is unambiguous.
  - Retry logic / partial recovery. Rejected: not in spec; would
    duplicate w3gjs behavior.

## 7. Testing approach

- **Decision**: Node's built-in `node:test` runner. Tests parse the
  two committed replays (`sample_replays/base_1.w3g`,
  `sample_replays/base_2.w3g`) and assert structural invariants of
  the produced JSON: top-level keys present, `players` array non-
  empty, version and duration are of expected types, and the written
  file round-trips through `JSON.parse`. No mocking of `w3gjs`.
- **Rationale**: `node:test` requires zero dependencies (Principle
  III). Fixtures are real replays (Principle IV). The user's note for
  this plan explicitly states that the samples cover everything that
  is needed.
- **Alternatives considered**:
  - Jest / Vitest. Rejected: adds a dependency and a config file for
    no benefit at this scale.
  - Snapshot testing the entire JSON output. Rejected: brittle across
    `w3gjs` upgrades; the test value is in asserting stability of the
    top-level contract, not byte-identity.
  - Asserting exact `apm` or action counts. Rejected: couples tests
    to `w3gjs`'s internal derivations, which are outside our control
    and outside the spec's success criteria.

## 8. Structure documentation format

- **Decision**: A single Markdown file, `parser/DATA.md`, committed
  alongside `parser/parse.js`. Top-level sections correspond to
  top-level keys of the JSON output; nested sections describe nested
  objects/arrays. Each field lists: name, type, origin (replay-native
  vs. library-derived), and a short meaning.
- **Rationale**: Markdown is reviewable in PRs, co-located with the
  code it describes (so changes land in the same commit — FR-007),
  and readable without tooling.
- **Alternatives considered**:
  - JSON Schema / TypeScript `.d.ts`. Rejected: validation and
    type-checking are out of scope for v1 (Out of Scope in spec).
  - Generated docs from library types. Rejected: adds tooling surface
    for no current user value.

## 9. Package manager

- **Decision**: `npm` with a committed `package.json` and
  `package-lock.json`. No workspace, no monorepo tooling.
- **Rationale**: Shipped with Node; familiar; minimal.
- **Alternatives considered**: `pnpm`, `yarn`. Rejected: no benefit
  at this scale.

## 10. Coverage adequacy of committed fixtures

- **Decision**: Treat `sample_replays/base_1.w3g` (~1 MB) and
  `sample_replays/base_2.w3g` (~700 KB) as authoritative fixtures for
  this feature. Both are valid Warcraft III recorded games (verified
  via `file(1)`). Tests focus on contract-level invariants, not
  replay-specific content.
- **Rationale**: The user explicitly stated, in the plan input, that
  the samples cover everything that is needed. Honoring that directive
  avoids scope creep. Additional fixtures can be added later if real
  downstream analyses surface a gap.
- **Alternatives considered**:
  - Broaden the fixture set now (multiple patches, 2v2/FFA, partial
    replays). Rejected per the explicit user directive above.

---

**Phase 0 status**: All NEEDS CLARIFICATION items resolved. Proceeding
to Phase 1 (data model, contracts, quickstart).
