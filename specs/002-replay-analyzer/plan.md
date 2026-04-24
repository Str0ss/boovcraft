# Implementation Plan: Replay Analyzer

**Branch**: `002-replay-analyzer` | **Date**: 2026-04-23 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/002-replay-analyzer/spec.md`

## Summary

Deliver a Python command-line script that reads a single Parser-layer
JSON output (produced by `parser/parse.js` from a `.w3g` replay) and
emits a single analysis JSON document containing every metric the
Visualizer layer will display: match metadata, per-player statistics,
build orders, hero progression, resource transfers, chat, and
observers. Every Warcraft III entity ID referenced in the analysis is
accompanied by a human-readable display name, resolved through a
static `entity_names.json` mapping shipped alongside the script. The
mapping is sourced from `w3gjs`'s internal `mappings.js` data (items,
units, buildings, upgrades, hero abilities, and hero identities
derived from the hero-ability table), stripped of w3gjs's category
prefixes (`i_`, `u_`, `p_`, `b_`, `a_`) and committed as a reviewable
static file. An unmapped ID does not fail the run; it degrades
gracefully to a raw-ID placeholder with a deduplicated stderr
diagnostic. A Markdown document describes the analysis output shape
for Visualizer-layer consumers.

## Technical Context

**Language/Version**: Python 3.11+ (Processor-layer runtime per
constitution; 3.11 is the oldest LTS-tier release with modern
`tomllib`, `datetime` fixes, and faster startup that is widely
shipped on developer distros).
**Primary Dependencies**: None at runtime. The script uses only the
Python standard library (`argparse`, `json`, `pathlib`, `sys`,
`collections`). Test-only dependency: `pytest`.
**Storage**: Filesystem only. Input is a parser-layer JSON file.
Output is a single `.analysis.json` file written next to the input.
The `entity_names.json` mapping is bundled with the script in the
`processor/` directory.
**Testing**: `pytest`. Fixtures are the committed parser outputs
`sample_replays/base_1.w3g.json` and `sample_replays/base_2.w3g.json`
(the second fixture is generated from `base_2.w3g` and committed as
part of this feature — see Phase 0). No mocks, no synthetic parser
outputs (Principle IV).
**Target Platform**: Linux/macOS development environment. Pure Python
CLI, no OS-specific features.
**Project Type**: CLI tool (Processor layer of the three-layer
pipeline; Parser is already delivered, Visualizer is a later
feature).
**Performance Goals**: Producing the analysis for a typical 1 MB
replay's parser output (~50k–100k events) completes in under 5 seconds
on commodity hardware (SC-001).
**Constraints**: The Processor MUST NOT invoke `w3gjs`, shell out to
Node, import the Parser's JavaScript, or re-parse `.w3g` files
(Principle I, FR-010). The Processor MUST NOT modify upstream
artifacts (FR-011). The analysis output is the sole Processor →
Visualizer contract.
**Scale/Scope**: One parser-output file per invocation. Two committed
fixtures drive tests. No batch, watch, or directory-walking mode
(explicitly Out of Scope in the spec).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates derived from the five constitutional principles.

| Gate | Principle | Status | Evidence |
|------|-----------|--------|----------|
| Layer separation respected | I | ✅ Pass | Processor reads only the Parser's JSON file; it does not import Node, shell out to `node`/`npm`, or link to `w3gjs`. The analysis JSON file is its sole contract with the Visualizer. |
| w3gjs is the sole parser | II | ✅ Pass | This feature never parses `.w3g` bytes. It consumes the Parser's JSON — `w3gjs` remains the one and only binary reader. The entity-name mapping is *data* extracted once from `w3gjs`, not a parallel parser. |
| No premature abstractions | III | ✅ Pass | Single Python script, single entry point, zero runtime dependencies, one positional CLI arg, flat `{ id: name }` mapping (no enriched objects), no plugin surface or config system. |
| Fixture-based tests | IV | ✅ Pass | Tests load `sample_replays/base_1.w3g.json` and `sample_replays/base_2.w3g.json`. No mocks, no synthetic parser-output fragments. Second fixture (`base_2.w3g.json`) is generated once from the real `base_2.w3g` and committed. |
| Frontend restraint | V | N/A | This feature introduces no visualizer, framework, or build tooling. |

**Result**: All applicable gates pass. No entries required in the
Complexity Tracking table.

Re-check after Phase 1 design: see end of this document.

## Project Structure

### Documentation (this feature)

```text
specs/002-replay-analyzer/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output — analysis JSON entity model
├── quickstart.md        # Phase 1 output — run/test walkthrough
├── contracts/
│   ├── analyzer-cli.md  # CLI contract: args, exit codes, stderr/stdout
│   ├── output-shape.md  # Analysis JSON structural contract
│   └── mapping-shape.md # entity_names.json structural contract
├── checklists/
│   └── requirements.md  # Spec quality checklist (already written)
└── tasks.md             # Phase 2 output — created by /speckit.tasks
```

### Source Code (repository root)

```text
processor/
├── pyproject.toml          # Python package metadata, pytest config, no runtime deps
├── analyze.py              # CLI entry point: python analyze.py <parser-output.json>
├── entity_names.json       # Static WC3 entity ID → human-readable name mapping
├── DATA.md                 # Analysis-output structure documentation (FR-009 deliverable)
└── tests/
    ├── test_analyze.py     # Fixture-based end-to-end and field-level tests
    └── test_entity_names.py # Coverage checks on the mapping file

sample_replays/              # Already present at repo root
├── base_1.w3g
├── base_1.w3g.json          # Committed parser-output fixture (already present)
├── base_2.w3g
└── base_2.w3g.json          # Committed parser-output fixture (generated once in this feature)
```

**Structure Decision**: A single top-level `processor/` directory for
the Python Processor layer, mirroring `parser/` for the Node layer.
This honors Principle I — each layer has its own runtime, dependency
set, and tests, and layer boundaries are filesystem-explicit. The
Visualizer layer will be added as a sibling `visualizer/` directory
in a later feature and will consume both the analysis JSON and the
`entity_names.json` mapping from `processor/`. `sample_replays/`
remains the single shared fixture root because fixtures cross layer
boundaries: a `.w3g` is Parser input, the corresponding `.w3g.json`
is Processor input, and both live here side by side.

The mapping file lives inside `processor/` for this feature. If the
Visualizer later needs the exact same mapping, it reads it from
`processor/entity_names.json` directly (filesystem read is the
cross-layer contract, consistent with Principle I). Promoting it to a
top-level `data/` directory is a later-feature decision if it
accumulates multiple consumers (Principle III — no premature
abstraction today).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No violations. Table omitted.

## Post-Design Constitution Re-Check

After Phase 1 (research, data model, contracts, quickstart) is
complete, the gates are re-evaluated:

| Gate | Principle | Status | Notes |
|------|-----------|--------|-------|
| Layer separation respected | I | ✅ Pass | `contracts/analyzer-cli.md` specifies JSON-file input/output only; no IPC, no library links. Mapping is a static data file, consumed by read. |
| w3gjs is the sole parser | II | ✅ Pass | Data model and contracts reference the Parser's output fields as inputs; nothing in this feature parses `.w3g` bytes. Mapping is derived once, at plan time, from `w3gjs`'s data tables. |
| No premature abstractions | III | ✅ Pass | Design has no config file, no logging framework, no abstraction layer. CLI takes exactly one positional arg. Mapping is flat `id→name`. Diagnostics go to stderr directly. |
| Fixture-based tests | IV | ✅ Pass | Test plan calls for exercising both committed fixture parser outputs and asserting against documented invariants. |
| Frontend restraint | V | N/A | Unchanged. |

**Result**: All gates still pass after design. Ready for
`/speckit.tasks`.
