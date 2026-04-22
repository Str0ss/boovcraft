# Implementation Plan: Replay Parser

**Branch**: `001-replay-parser` | **Date**: 2026-04-21 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/001-replay-parser/spec.md`

## Summary

Deliver a Node.js command-line script that reads a single Warcraft III
`.w3g` replay file, parses it with the `w3gjs` library, and persists the
library's complete output as a single JSON document next to the input
file. No analytical logic is added on top of `w3gjs`. A Markdown
document, kept alongside the parser code, describes every field that
the output contains. Correctness is verified against the two real
replays already committed under `sample_replays/`.

## Technical Context

**Language/Version**: Node.js 20 LTS (parser). No Python or HTML code is
introduced in this feature.
**Primary Dependencies**: `w3gjs` (canonical parser — Principle II). No
other runtime dependencies.
**Storage**: Filesystem only. Output is a `.json` file written next to
the input `.w3g` file.
**Testing**: Node's built-in `node:test` runner. Fixtures are the two
committed replays in `sample_replays/` (base_1.w3g, base_2.w3g). No
mocks, no synthetic byte streams (Principle IV).
**Target Platform**: Linux/macOS development environment. Pure Node
script, no OS-specific features.
**Project Type**: CLI tool (Parser layer of a three-layer pipeline;
Processor and Visualizer layers are separate, future features).
**Performance Goals**: A ~1 MB replay parses in under 5 seconds on
commodity hardware (SC-001).
**Constraints**: Parser MUST NOT embed analytical logic (FR-003).
Parser MUST NOT import or invoke downstream layers (Principle I).
Parser output is the sole inter-layer contract (Principle I).
**Scale/Scope**: One replay per invocation. Two fixture replays drive
tests. No batch, watch, or streaming modes (explicitly Out of Scope in
spec).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates are derived from the five constitutional principles.

| Gate | Principle | Status | Evidence |
|------|-----------|--------|----------|
| Layer separation respected | I | ✅ Pass | Parser writes a JSON file; no imports from, no shell-outs to, no shared in-process state with Processor or Visualizer. The output file IS the contract. |
| w3gjs is the sole parser | II | ✅ Pass | `w3gjs` is the one runtime dependency; no custom binary reader, no alternative library, no fork. |
| No premature abstractions | III | ✅ Pass | Single script, single entry point, no config system, no plugin surface, no generic pipeline, no shared helpers for a hypothetical second parser. Duplication over speculation. |
| Fixture-based tests | IV | ✅ Pass | Tests load `sample_replays/base_1.w3g` and `sample_replays/base_2.w3g`. No mocks or synthetic byte streams. Per user input, these fixtures cover everything that is needed. |
| Frontend restraint | V | N/A | This feature introduces no visualizer, no framework, no build tooling. |

**Result**: All applicable gates pass. No entries required in the
Complexity Tracking table.

Re-check after Phase 1 design: see end of this document.

## Project Structure

### Documentation (this feature)

```text
specs/001-replay-parser/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   ├── parser-cli.md    # CLI contract: args, exit codes, stderr/stdout
│   └── output-shape.md  # JSON output structural contract (top-level keys)
├── checklists/
│   └── requirements.md  # Spec quality checklist (already written)
└── tasks.md             # Phase 2 output — created by /speckit.tasks
```

### Source Code (repository root)

```text
parser/
├── package.json         # Declares w3gjs dependency; node:test for tests
├── parse.js             # CLI entry point: node parse.js <path-to-replay>
├── DATA.md              # Structure documentation (FR-007 deliverable — US2)
└── test/
    └── parse.test.js    # Fixture-based tests using sample_replays/

sample_replays/          # Already present at repo root
├── base_1.w3g
└── base_2.w3g
```

**Structure Decision**: A single top-level `parser/` directory for the
Node parser layer. This mirrors the constitutional three-layer pipeline
(Parser → Processor → Visualizer) and keeps each layer's runtime,
dependencies, and tests self-contained. The processor and visualizer
layers will be added as sibling top-level directories in later features;
there is no shared code or shared tooling between layers. `sample_replays/`
stays at the repo root because fixtures are shared across layers (the
processor will consume the same replays via the parser's JSON output).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table omitted.

## Post-Design Constitution Re-Check

After Phase 1 (data model, contracts, quickstart) is complete, the
gates are re-evaluated:

| Gate | Principle | Status | Notes |
|------|-----------|--------|-------|
| Layer separation respected | I | ✅ Pass | Contracts specify a file-on-disk boundary only; no IPC, no shared memory. |
| w3gjs is the sole parser | II | ✅ Pass | Data model treats `w3gjs`'s return value as the complete source of fields; `DATA.md` documents it without reinterpretation. |
| No premature abstractions | III | ✅ Pass | Design has no config file, no logging framework, no abstraction layer over `w3gjs`. CLI takes exactly one positional arg. |
| Fixture-based tests | IV | ✅ Pass | Test plan calls for parsing `base_1.w3g` and `base_2.w3g` and asserting library-output invariants directly. |
| Frontend restraint | V | N/A | Unchanged. |

**Result**: All gates still pass after design. Ready for `/speckit.tasks`.
