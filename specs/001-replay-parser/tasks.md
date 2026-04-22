---

description: "Task list for the Replay Parser feature"
---

# Tasks: Replay Parser

**Input**: Design documents from `/specs/001-replay-parser/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included. Constitutional Principle IV mandates fixture-based
tests, and spec SC-002 requires verifying that persisted output matches
`w3gjs`'s in-memory return value.

**Organization**: Tasks are grouped by user story (US1, US2, US3) so
each story can be implemented, tested, and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)
- File paths are exact and relative to the repository root

## Path Conventions

- Parser layer: `parser/` at repository root (`parser/parse.js`,
  `parser/package.json`, `parser/DATA.md`, `parser/test/`)
- Replay fixtures: `sample_replays/` at repository root (already
  present: `base_1.w3g`, `base_2.w3g`)
- Feature spec artifacts: `specs/001-replay-parser/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the parser layer's directory and package scaffolding.

- [X] T001 Create the parser layer directory tree: `parser/` and `parser/test/` at the repository root
- [X] T002 Create `parser/package.json` declaring: `"name": "boovcraft-parser"`, `"private": true`, `"type": "commonjs"` (or whatever matches w3gjs's module shape), `"engines.node": ">=20"`, runtime dependency `w3gjs` (latest stable), and `"scripts.test": "node --test test/"`
- [X] T003 From `parser/`, run `npm install` to resolve `w3gjs` and produce `parser/package-lock.json`
- [X] T004 [P] Add `parser/node_modules/` and `sample_replays/*.json` to `.gitignore` at the repository root

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Confirm the toolchain loads before any user story work begins.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T005 From `parser/`, run `node -e "require('w3gjs')"` and confirm it exits with status 0 (validates that the pinned `w3gjs` install is usable)

**Checkpoint**: Toolchain verified — user story implementation can now begin.

---

## Phase 3: User Story 1 - Extract Complete Raw Data From A Replay (Priority: P1) 🎯 MVP

**Goal**: A single `node parser/parse.js <path-to-replay>` invocation
produces `<path-to-replay>.json` containing the complete, unmodified
output of `W3GReplay.parse()` — or fails cleanly with a non-zero exit
and no partial output file (FR-001, FR-002, FR-003, FR-004, FR-005,
FR-006, FR-008).

**Independent Test**: Run `node parser/parse.js sample_replays/base_1.w3g`.
Confirm `sample_replays/base_1.w3g.json` is created, parses via
`JSON.parse`, and the root object is non-null. Delete the output,
point the tool at a non-existent path, and confirm non-zero exit with
a stderr message and no output file created.

### Tests for User Story 1

> Write these tests alongside implementation; they MUST pass before
> US1 is considered complete (SC-002).

- [X] T006 [P] [US1] Create `parser/test/parse.test.js` using `node:test`. Import the parser's programmatic entry (or spawn the CLI via `node:child_process`), run it against `sample_replays/base_1.w3g` and `sample_replays/base_2.w3g`, and assert: (a) the expected output file exists at `<input>.w3g.json`, (b) `JSON.parse` on the file contents yields a non-null object, (c) that parsed object deep-equals the value returned in-process by `W3GReplay.parse()` for the same buffer in the same test run (enforces `contracts/output-shape.md` invariant #3 — no injection, no stripping)
- [X] T007 [US1] Add a failure-path test in `parser/test/parse.test.js`: invoke the CLI with a non-existent path, assert non-zero exit, non-empty stderr, and that no output file is created

### Implementation for User Story 1

- [X] T008 [US1] Implement the happy path in `parser/parse.js`: read the single positional argument, read the replay file with `fs.readFileSync`, construct `new (require('w3gjs'))()` (or the equivalent `W3GReplay` named import per the library's current API), `await` its `parse(buffer)` method, write `JSON.stringify(result)` to `<input>.json` using `fs.writeFileSync`, exit 0
- [X] T009 [US1] Add failure handling in `parser/parse.js`: reject any `process.argv` that does not contain exactly one positional argument, wrap the read+parse+write in `try/catch`, on any error print a single-line `input-path: <message>` to `process.stderr`, ensure any partially written `<input>.json` is removed with `fs.unlinkSync` before exit, and call `process.exit(1)` — never throw uncaught
- [X] T010 [US1] Run `node parser/parse.js sample_replays/base_1.w3g` from the repo root and manually confirm (a) exit code 0, (b) `sample_replays/base_1.w3g.json` exists, (c) `node -e "JSON.parse(require('fs').readFileSync('sample_replays/base_1.w3g.json'))"` exits 0
- [X] T011 [US1] From `parser/`, run `npm test` and confirm all tests from T006 and T007 pass for both fixtures

**Checkpoint**: User Story 1 delivers the MVP — parser turns a `.w3g`
into a complete JSON artifact, or fails cleanly.

---

## Phase 4: User Story 2 - Document The Parsed Data Structure (Priority: P2)

**Goal**: `parser/DATA.md` exists and describes every top-level and
nested field the parser emits, with name, type, origin (replay-native
vs. `w3gjs`-derived), and meaning. A developer can find any field
without reading the parser or a sample output (FR-007, SC-003).

**Independent Test**: Generate the JSON for both fixtures. List the
union of top-level keys present across both outputs. Every one of
those keys MUST have a section in `parser/DATA.md`. Spot-check three
nested fields (e.g., a player's race, a chat message's sender, the
map file path) — each SHOULD be locatable from `DATA.md` alone.

### Implementation for User Story 2

- [X] T012 [US2] From the repo root, run the parser on both fixtures (`node parser/parse.js sample_replays/base_1.w3g` and `node parser/parse.js sample_replays/base_2.w3g`) to produce up-to-date `.json` outputs for inspection
- [X] T013 [US2] Author `parser/DATA.md` with: a short "Origin key" (replay-native vs. w3gjs-derived); one section per top-level key observed across both fixture outputs; per section, a table or bullet list of nested fields with name, JSON type, origin, and one-sentence meaning; note any fields that differ between fixtures (e.g., chat present in one, absent in the other) as "optional"
- [X] T014 [P] [US2] Verify DATA.md coverage: from `parser/`, run `node -e "const a=require('../sample_replays/base_1.w3g.json'); const b=require('../sample_replays/base_2.w3g.json'); console.log([...new Set([...Object.keys(a), ...Object.keys(b)])].sort().join('\n'))"` and confirm every listed top-level key has a heading in `parser/DATA.md`

**Checkpoint**: User Story 2 makes the parser's output contract
readable without running the code.

---

## Phase 5: User Story 3 - Parser Remains Unchanged As Analyses Evolve (Priority: P3)

**Goal**: Future contributors understand that the parser's minimalism
is intentional and enforced, so new analyses land in the downstream
processor rather than as parser edits (FR-009, SC-004).

**Independent Test**: A reader of `parser/DATA.md` can, in under a
minute, find a statement of this boundary and a pointer to where
analysis code belongs.

### Implementation for User Story 3

- [X] T015 [US3] Add a short "Scope of this parser" section at the top of `parser/DATA.md` stating: the parser emits what `w3gjs` exposes and nothing more; analytical values (APM, action counts, win inference, etc.) are produced by the downstream processor layer, not here; pull requests that add computed or aggregated fields to the parser will be rejected unless `w3gjs` itself is the one producing them

**Checkpoint**: The scope boundary is visible in the repo, not just in
spec documents.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the feature end-to-end and tidy generated
artifacts before handoff.

- [X] T016 Walk through `specs/001-replay-parser/quickstart.md` from a clean working directory: `cd parser && npm install`, then parse each sample replay from the repo root, then run `npm test`. Confirm every command in the quickstart works exactly as written and update the quickstart if any step drifted
- [X] T017 [P] Delete any generated `sample_replays/*.json` files that were produced during development (they are covered by the `.gitignore` entry from T004 but should not be left in the working tree)
- [X] T018 Re-run the Constitution Check gates from `specs/001-replay-parser/plan.md` against the final tree — I (layer separation), II (w3gjs canonical), III (no premature abstractions), IV (fixture-based tests), V (N/A) — and confirm all still pass; record any surprises in this task's commit message

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 (Setup)**: No dependencies — starts immediately.
- **Phase 2 (Foundational)**: Depends on Phase 1 (needs `node_modules`).
- **Phase 3 (US1)**: Depends on Phase 2. **BLOCKS** Phase 4 (US2
  needs real parser output to document).
- **Phase 4 (US2)**: Depends on Phase 3 being functionally complete
  (T010 or T011 has run at least once and produced fixture outputs).
- **Phase 5 (US3)**: Depends on Phase 4 (it edits `parser/DATA.md`).
- **Phase 6 (Polish)**: Depends on all preceding phases.

### User Story Dependencies (documented, not aspirational)

- **US1 (P1)**: Independent — no dependency on US2 or US3.
- **US2 (P2)**: Depends on US1 being runnable. DATA.md describes real
  output; it cannot be written blind. This dependency is acknowledged
  here rather than hidden.
- **US3 (P3)**: Depends on US2 (adds a section to the same file).

### Within Each User Story

- US1: tests (T006, T007) and implementation (T008, T009) can overlap;
  validation tasks (T010, T011) come last.
- US2: generate fixture output (T012) → write docs (T013) → verify
  coverage (T014).
- US3: single task (T015).

### Parallel Opportunities

- T004 (`.gitignore`) runs parallel to T002–T003 (different file).
- T006 and T008 (test file vs. CLI implementation) are different
  files with no code-level dependency — they can be authored in
  parallel. T007 edits the same test file as T006 and must be
  sequential after it.
- T014 (DATA.md coverage check) can run parallel to any non-DATA.md
  work.
- T017 (clean generated JSON) can run parallel to T018 (gates
  re-check).

---

## Parallel Example: User Story 1

```bash
# Once Phase 2 is done, US1 work can proceed. Authoring the test file
# and the CLI in parallel is safe because they are different files:
Task: "T008 [US1] Implement happy path in parser/parse.js"
Task: "T006 [P] [US1] Write fixture round-trip tests in parser/test/parse.test.js"

# Validation must be sequential — it depends on both being done:
Task: "T010 [US1] Smoke-test the CLI against sample_replays/base_1.w3g"
Task: "T011 [US1] Run npm test and confirm suite passes"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1: Setup — scaffold `parser/` and install `w3gjs`.
2. Phase 2: Foundational — confirm w3gjs loads.
3. Phase 3: US1 — implement `parse.js`, write fixture tests, validate
   against both sample replays.
4. **STOP and VALIDATE**: the MVP is now usable by a human or by a
   future processor. Demo: parse a replay, open the JSON.

### Incremental Delivery

1. Ship US1 as the MVP.
2. Add US2 (`DATA.md`) — makes the output contract consumable by
   other humans without reading code.
3. Add US3 (scope statement in `DATA.md`) — protects the boundary.
4. Polish — validate quickstart, clean up working tree, re-check
   constitutional gates.

### Not Applicable: Parallel Team Strategy

This feature is small enough that parallel staffing is unnecessary.
One contributor completes it end-to-end.

---

## Notes

- Every task names the exact file it touches; no "various files" tasks.
- Tests are fixture-driven per Principle IV. Neither the test file
  nor the CLI code may introduce mocked `w3gjs` behavior, synthetic
  byte streams, or hand-crafted replay bytes.
- No task adds a configuration file, abstraction layer, or framework.
  Any such addition must be backed by a constitution amendment
  (Principle III).
- The `.json` files under `sample_replays/` are build artifacts, not
  source. They are `.gitignore`d (T004).
- Commit cadence: one commit per task, or one commit per logical
  group (e.g., T008 + T009 as a single commit that completes the
  CLI).
- If any task surfaces that `w3gjs` does NOT expose a field a real
  analysis needs, treat it as outside this feature's scope: capture
  the gap in an issue or follow-up spec, do not extend the parser
  with custom extraction logic.
