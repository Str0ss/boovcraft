# Implementation Plan: Narrative Event Extraction

**Branch**: `006-event-extraction` | **Date**: 2026-05-07 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/006-event-extraction/spec.md`

## Summary

Two changes inside the Processor layer, shipped together as feature 006:

1. **Coordinate retention (additive contract change to `*.analysis.json`).**
   `processor/analyze.py` is extended to keep the `(x, y)` coordinate of
   every replay action that carried a position, surfaced on the
   matching `timedActions[]` entry and on each `production.*.order[]`
   entry. The contract is strictly additive: every previously-emitted
   field is unchanged in name, type, position, and value
   (FR-001..FR-005 / SC-005). `processor/DATA.md` is updated in the
   same change.

2. **New `processor/extract_events.py` stage.** A second Processor-layer
   CLI that takes the post-(1) analyzer-output as its sole input and
   emits a sibling `<name>.w3g.events.json` document. The events
   document is a flat chronological array of events under one
   well-known top-level key, plus a top-level `diagnostics` block
   mirroring the analyzer's pattern, plus match-level metadata
   sufficient to identify the replay (FR-006..FR-009). Every event
   carries a stable content-derived identifier and a `kind`
   discriminator (FR-009). Thirteen kinds are recognized
   (FR-010..FR-022). Inferred kinds carry an explicit "observable
   signal vs inferred meaning" label (FR-023..FR-026). All spatial
   thresholds are derived per-replay from observed building-placement
   spread, with a documented fallback (FR-027..FR-028).
   `processor/EVENTS.md` documents the output shape (FR-029..FR-032).

The events stage uses **pandas** (DataFrame as the workhorse for
keyed, time-windowed, and group-by operations) and
**scikit-learn DBSCAN** (single-player creep-camp identification and
cross-player engagement clustering). Both meet all four "well-established"
criteria of constitution Principle VI and are justified in the
Library Justification gate below.

The Visualizer is **not** touched in this feature. The events
document is produced and documented so a follow-up feature (a "Story"
tab, annotations on the existing timelines, a future Map tab) can
wire it in without re-spelunking the action stream.

## Technical Context

**Language/Version**: Python 3.11+ (matches the existing Processor
runtime in `processor/pyproject.toml`; both new code paths are pure
Python, no language version bump required).

**Primary Dependencies**:
- **`pandas` 2.x** (BSD-3-Clause, ~15 years of releases, used by
  every major data tool) — DataFrame is the natural representation
  of `(timeMs, playerId, teamId, x, y, category, entityId)` rows for
  keyed/grouped/windowed operations. Without it, every event kind
  re-implements the same `groupby` / `rolling` boilerplate by hand,
  which Principle VI explicitly forbids ("a handwritten histogram
  engine is not 'minimal' — it is a permanent maintenance debt
  swapped for a transient one-time integration cost").
- **`scikit-learn` 1.5+** (BSD-3-Clause, broad adoption, stable
  major-release line) — `sklearn.cluster.DBSCAN` for spatial-temporal
  clustering with noise tolerance. Two real uses: (i) collapsing a
  single player's runs of action coordinates into "creep camp"
  clusters during creeping-departure detection, and (ii) finding
  cross-teammate clusters in 3-D `(x, y, t/scale)` space for joint
  engagements. K-means is inapplicable (cluster count is unknown);
  hierarchical clustering would also work but DBSCAN's noise label
  matches the "ignore lone clicks" semantics we actually want.

The coord-retention change (item 1 above) adds **no new runtime
dependencies** — it only widens an existing dict literal.

**Storage**: Filesystem only. Inputs are JSON files on disk; outputs
are JSON files on disk. No database, no cache, no network.

**Testing**: `pytest` (existing pattern from feature 002). Fixtures
are the two committed parser/analyzer outputs:
- `sample_replays/base_1.w3g.json` / `.analysis.json` (4v4)
- `sample_replays/base_2.w3g.json` / `.analysis.json` (3v3)

Tests fall into three groups:
- **Coord-retention regression tests** — assert the analyzer's pre-change
  output is byte-identical on every existing field (SC-005), and that the
  new coordinate fields appear on the action categories we expect and are
  absent on the categories we don't.
- **Events-stage end-to-end tests** — run `extract_events.py` on each
  fixture analyzer-output and assert the emitted events document is
  structurally valid, contains no fabricated kinds (SC-002), and is
  byte-identical on re-run (SC-006).
- **Pure-helper unit tests** — per-replay threshold derivation,
  rebuild-bucket grouping, idle-gap detection, transfer-burst
  clustering, intensity-peak finding. These are pure data-in /
  data-out functions whose inputs are derived from the fixtures, not
  hand-rolled (Principle IV's spirit).

**Target Platform**: Linux/macOS development environment. CLI tool,
no OS-specific features.

**Project Type**: CLI tool. Two entry points in the Processor layer:
the existing `processor/analyze.py` (extended for coord retention) and
the new `processor/extract_events.py` (events stage).

**Performance Goals**: Producing the events document for either
committed fixture completes in **under 30 seconds** on commodity
hardware. The analyzer runs in <5 s today (SC-001 from feature 002);
the events stage is heavier (clustering, group-by) but operates on
already-aggregated input. 30 s is generous; the realistic target is
<10 s. We will not optimize past that without a concrete need.

**Constraints**:
- The events stage MUST NOT re-parse `.w3g` files, MUST NOT read the
  parser-layer JSON, and MUST NOT invoke `node` or load `w3gjs`
  (FR-036, Principle I, Principle II).
- Coord retention MUST be byte-additive on the existing analyzer
  output (FR-004, SC-005). Existing visualizer (feature 005) MUST
  continue to function unchanged against the new output.
- All spatial thresholds MUST be derived per-replay (FR-027). No
  hardcoded map-unit constants for home radius, engagement radius, or
  rebuild-bucket size.

**Scale/Scope**: One analyzer-output file per `extract_events.py`
invocation. Both committed fixtures drive tests. No batch, watch, or
directory-walking mode (consistent with the analyzer's CLI posture).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Gates derived from constitution v1.1.0 Principles I–VI.

| Gate | Principle | Status | Evidence |
|------|-----------|--------|----------|
| Layer separation respected | I | ✅ Pass | Both changes stay inside the Processor layer. Coord retention widens the existing analyzer's output JSON; the events stage consumes that JSON and writes its own JSON. No cross-layer imports, no shell-out to `node`, no in-process invocation of w3gjs (FR-036). |
| w3gjs is the sole parser | II | ✅ Pass | Neither change parses `.w3g` bytes. The coord-retention change reads coordinates that w3gjs already emitted into the parser-output's `events[].commandBlocks[].actions[]` stream and forwards them through the analyzer; w3gjs remains the one and only binary reader. |
| No premature abstractions | III | ✅ Pass | Two entry-point scripts in `processor/`, no plugin system, no config surface, no shared "event-kind base class". The 13 kinds are 13 concrete functions; if a fourth kind ever genuinely shares logic with another, the abstraction lands then, not now. The data-shape doc is plain Markdown, not a generated schema. |
| Fixture-based tests | IV | ✅ Pass | All tests load the two committed fixture replays' parser-output and analyzer-output JSON. No mocks, no synthetic events, no hand-rolled action streams. Fallback-rule tests (e.g., a player with no buildings in the first 60 s) use a per-fixture sub-slice of the real data, not a constructed file. |
| Frontend restraint | V | N/A | This feature introduces no visualizer change, no framework, no build step, no package manager. Visualizer integration is a deliberate follow-up. |
| Library justification | VI | ✅ Pass with justification | **`pandas`**: actively maintained (commits within the last week as of 2026-05); broad adoption (default dependency in scientific-Python and ML stacks; standard library-equivalent for tabular data); BSD-3-Clause; stable 2.x line since April 2023 with documented breaking-change policy. The "DataFrame" abstraction is exactly what we need for `(timeMs, playerId, teamId, x, y, category, entityId)` rows; rebuilding rolling/groupby in plain Python is the bespoke trap VI rules out. **`scikit-learn`**: actively maintained; broad adoption (the canonical Python ML library); BSD-3-Clause; stable 1.x line with backward-compatibility guarantees. We use exactly one class (`DBSCAN`) for two well-defined uses; we do **not** drag in the rest of the ML stack. **YAGNI escape hatch is not used.** A handwritten DBSCAN-equivalent would be 50-100 lines of correct-and-tested boilerplate; the dependency is the right call. |

**Result**: All applicable gates pass. The Library Justification gate
records the two dependencies' satisfaction of all four "well-established"
criteria. No entries required in the Complexity Tracking table.

Re-check after Phase 1 design: see end of this document.

## Project Structure

### Documentation (this feature)

```text
specs/006-event-extraction/
├── plan.md              # This file
├── research.md          # Phase 0 — open-question resolutions
├── data-model.md        # Phase 1 — entities (Event, kinds, diagnostics)
├── quickstart.md        # Phase 1 — run/test walkthrough
├── contracts/
│   ├── analyzer-coord-extension.md   # The additive coord-retention contract
│   ├── extract-events-cli.md         # CLI contract for the new entry point
│   └── events-output-shape.md        # Structural contract for events JSON
├── checklists/
│   └── requirements.md  # Spec quality checklist
└── tasks.md             # Phase 2 output — created by /speckit.tasks
```

### Source Code (repository root)

```text
processor/
├── analyze.py                    # EXTENDED: coord retention on timedActions and production order entries
├── extract_events.py             # NEW: events-stage CLI entry point
├── entity_names.json             # Unchanged
├── DATA.md                       # UPDATED: documents the new optional coordinate fields
├── EVENTS.md                     # NEW: data-shape doc for the events JSON output (FR-029)
├── pyproject.toml                # UPDATED: adds pandas + scikit-learn to runtime deps; pytest stays in dev deps
└── tests/
    ├── conftest.py               # UPDATED: fixtures expose post-coord-retention analyzer output
    ├── test_cli.py               # UNCHANGED (analyzer CLI is unchanged)
    ├── test_entity_names.py      # UNCHANGED
    ├── test_fixture_facts.py     # UNCHANGED (asserts continue to hold)
    ├── test_output_shape.py      # UPDATED: new optional-coord assertions
    ├── test_timed_actions.py     # UPDATED: coord assertions on classified actions
    ├── test_coord_retention.py   # NEW: coord-bearing categories and absent-on-others assertions
    ├── test_events_cli.py        # NEW: extract_events.py CLI surface and exit codes
    ├── test_events_shape.py      # NEW: events JSON top-level shape, kind discriminator, ids, diagnostics
    ├── test_events_kinds.py      # NEW: per-kind end-to-end assertions on each fixture
    ├── test_events_helpers.py    # NEW: pure helpers — threshold derivation, rebuild bucketing, transfer-burst, idle gap
    └── test_events_determinism.py # NEW: re-run produces byte-identical events JSON (SC-006)

sample_replays/
├── base_1.w3g                    # Unchanged
├── base_1.w3g.json               # Re-emitted (parser unchanged, but committed for completeness — see research.md)
├── base_1.w3g.analysis.json      # RE-EMITTED with coord retention
├── base_1.w3g.events.json        # NEW: committed events fixture for base_1
├── base_2.w3g                    # Unchanged
├── base_2.w3g.json               # Unchanged
├── base_2.w3g.analysis.json      # RE-EMITTED with coord retention
└── base_2.w3g.events.json        # NEW: committed events fixture for base_2

CLAUDE.md                         # UPDATED: agent-context pointer in the SPECKIT marker block
```

**Structure Decision**: A two-file change inside the existing
`processor/` directory. No new top-level layer, no new package, no
new sub-module: the two scripts sit side-by-side as the analyzer's
two stages. This matches the Parser layer's pattern (one
`parse.js`) and the existing Processor layer's pattern (one
`analyze.py` plus a static `entity_names.json`). Adding
`extract_events.py` keeps each concern at one file (Principle III).
The committed `*.events.json` fixtures live next to the existing
`*.analysis.json` fixtures, matching the parser/analyzer convention.

## Complexity Tracking

> No constitution violations to justify. Library adoption (pandas,
> scikit-learn) is recorded in the Library Justification gate above
> and does NOT count as a violation under Principle VI — both
> libraries satisfy all four "well-established" criteria.

## Phase 0 — Outline & Research

The spec leaves a number of decisions to "the data-shape document"
or "documented thresholds" — those decisions land here in Phase 0
and are written up in `research.md`. The questions:

1. **Which w3gjs action types carry coordinates, and where does
   w3gjs put them?** The parser-output's `events[].commandBlocks[].actions[]`
   stream uses w3gjs's action-id codes; we need the concrete subset
   that has positions, the field name (`object`? `targetX/targetY`?
   `position`?), and the unit/range of the coordinates. → `research.md`.
2. **Per-replay home derivation rule.** Spec mandates it's per-replay
   (FR-027) but the formula is plan-level. Candidates: weighted
   centroid of the first-60s building placements; first-main-hall
   coordinate; centroid of first-30s rightclicks. → `research.md`.
3. **Per-replay home-radius derivation rule.** Candidates: 90th
   percentile of building-placement Euclidean distance from home;
   2× median; max of the first-60s placements. → `research.md`.
4. **Engagement-cluster radius and time-scale.** DBSCAN ε in 3-D
   `(x, y, t/scale)` requires a per-replay ε and a time-to-space
   scale factor. → `research.md`.
5. **Idle-period minimum gap and production-stall minimum gap.**
   The spec says "documented minimum"; pick concrete values and the
   rationale. Likely 15 s (idle) and 45 s (stall). → `research.md`.
6. **Transfer-burst inter-transfer-gap threshold.** Spec FR-022
   names the threshold; pick a concrete value (probably 30 s). → `research.md`.
7. **Tower entity-id catalog (per race).** Which `b_<id>` codes count
   as a tower for FR-015? → `research.md`.
8. **Tech-milestone entity-id catalog.** Which buildings/upgrades
   count as the "tier-2 hall", "tier-3 hall", "altar/equivalent",
   "key tech buildings", "major upgrade research starts" per race? → `research.md`.
9. **Hero teleport item-id catalog.** Town Portal, Staff of
   Teleportation, Mass Teleport scroll, etc. → `research.md`.
10. **Intensity-peak detection.** Window size, peak-vs-baseline
    threshold, baseline definition. → `research.md`.
11. **Stable event-id derivation rule.** Spec FR-009 says
    content-derived; pick the exact hash function and field set. → `research.md`.

**Output**: `research.md` resolves all eleven questions with the
"Decision / Rationale / Alternatives considered" tri-pane the plan
template prescribes.

## Phase 1 — Design & Contracts

**Prerequisites**: Phase 0 complete (`research.md` exists).

1. **Extract entities to `data-model.md`.** The spec's Key Entities
   list (Coordinate-bearing timed action, Coordinate-bearing
   production-order entry, Player home, Home radius, Event, Events
   document) becomes a structured catalog with field lists, types,
   and origin/derivation notes. The 13 kinds get their own per-kind
   sub-entry inside `data-model.md`, each with the full field list
   from FR-010..FR-022 plus the per-replay thresholds the kind
   depends on.

2. **Define interface contracts in `contracts/`.** Three documents:
   - `analyzer-coord-extension.md` — the additive contract change to
     `*.analysis.json`. Per FR-001..FR-005: which categories of
     timed actions gain `x`/`y`, which production-order entries gain
     `x`/`y`, what's emitted when the underlying action lacks a
     position, and the byte-additivity guarantee on every other
     field.
   - `extract-events-cli.md` — the new CLI's surface, mirroring the
     existing `contracts/analyzer-cli.md` from feature 002. One
     positional argument (analyzer-output path), no flags, no env
     vars, no stdin. Exit codes 0/1/2. Output path derivation
     (strip `.json` suffix, append `.events.json`). Stderr/stdout
     contract. Idempotency.
   - `events-output-shape.md` — the structural contract of the
     events JSON document. Top-level keys, the flat events array,
     the kind discriminator, the stable id derivation, the
     diagnostics block, and per-kind field tables for all 13 kinds.
     This file's content also lives under `processor/EVENTS.md`
     (the data-shape doc the spec mandates in FR-028); the
     `contracts/` copy is the spec-time snapshot, the
     `processor/EVENTS.md` copy travels with the code. The two stay
     identical until the events shape changes.

3. **Walkthrough in `quickstart.md`.** Three runnable invocations,
   each verified by a side-effect check:
   - Run the extended analyzer on `sample_replays/base_1.w3g.json`
     → assert coord fields appear on the expected categories.
   - Run `extract_events.py` on the resulting analyzer JSON → assert
     a sibling `*.events.json` is written and parses as JSON.
   - Run pytest → assert the existing test suite still passes (the
     coord-retention change must not regress feature 002's tests),
     and the new tests pass.

4. **Update agent context.** The `<!-- SPECKIT START -->` marker in
   `CLAUDE.md` updates to point at this plan file, replacing the
   feature 005 reference. (Mechanical; one-line edit in the marker
   block.)

5. **Re-run the Constitution Check post-design.** See the bottom of
   this document.

**Output**: `data-model.md`, `contracts/analyzer-coord-extension.md`,
`contracts/extract-events-cli.md`, `contracts/events-output-shape.md`,
`quickstart.md`, and an updated `CLAUDE.md`.

## Constitution Check (Post-Design Re-evaluation)

Re-evaluating after Phase 1 artifacts are in place:

| Gate | Principle | Status | Evidence |
|------|-----------|--------|----------|
| Layer separation respected | I | ✅ Pass | Phase 1 contracts confirm: `extract_events.py` reads only `*.analysis.json`, writes only `*.events.json`. The analyzer extension widens the analyzer's existing JSON output, no cross-layer code paths. |
| w3gjs is the sole parser | II | ✅ Pass | No `.w3g` byte handling anywhere in the design. The coord-retention change forwards w3gjs's existing position fields through the analyzer; w3gjs remains the one and only reader. |
| No premature abstractions | III | ✅ Pass | Phase 1 surfaces no shared "event base class" or "kind plugin registry". 13 kinds are 13 functions in one file; if reuse emerges in a follow-up, refactor then. The diagnostics block mirrors the analyzer's existing pattern by repetition, not by abstraction. |
| Fixture-based tests | IV | ✅ Pass | Every test path documented in Phase 1 derives its inputs from the two committed fixture replays' analyzer outputs. No mocks, no synthetic action streams. |
| Frontend restraint | V | N/A | Phase 1 introduces no visualizer change. |
| Library justification | VI | ✅ Pass | `research.md` records concrete uses of `pandas` and `scikit-learn.cluster.DBSCAN` only; no other ML/sklearn modules are imported. The dependencies stay within the Processor layer. |

**Result**: All applicable gates still pass. No retrofits required.
Plan is ready for `/speckit.tasks`.
