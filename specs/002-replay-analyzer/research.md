# Phase 0 Research — Replay Analyzer

This document resolves every open decision the Technical Context
could surface as a potential "NEEDS CLARIFICATION". There are no
unresolved items; the table below captures each decision, its
rationale, and the alternatives that were weighed and rejected.

## R1 — Runtime language & version

**Decision**: Python 3.11 as the minimum supported version.

**Rationale**:

- The constitution fixes the Processor layer to Python. This is a
  project-wide invariant, not a per-feature choice.
- 3.11 is the oldest Python release that (a) is widely shipped on
  current Linux/macOS dev distros, (b) bundles `tomllib` (used for
  `pyproject.toml` parsing if the test runner ever needs it), and
  (c) has the startup-latency improvements that matter for a CLI
  script invoked per replay.
- Newer features (3.12/3.13) are not required. Pinning to 3.11+ is a
  floor, not a ceiling.

**Alternatives considered**:

- 3.10: rejected — missing `tomllib`, and the project has no reason
  to accommodate a version that is already exiting security support.
- 3.12+ as the floor: rejected — excludes developers on slightly
  older distros for no functional gain.

## R2 — Runtime dependencies

**Decision**: Zero runtime dependencies. The analyzer uses only the
Python standard library (`argparse`, `json`, `pathlib`, `sys`,
`collections`).

**Rationale**:

- Principle III (no premature abstractions): a ~one-file CLI does
  not need `click`, `typer`, `pydantic`, `orjson`, `rich`, or any
  similar library. `argparse` handles the one positional arg; `json`
  handles round-trip; `sys.stderr` handles diagnostics.
- Zero runtime deps means zero version drift, zero transitive CVEs,
  and no `pip install` step between "clone" and "run".
- The Parser layer is also dependency-minimal (`w3gjs` only). The
  Processor layer matches that posture.

**Alternatives considered**:

- `click` / `typer` for CLI: rejected — one positional arg does not
  justify a dependency.
- `pydantic` for schema modeling: rejected — the parser output is
  read-only input; the analysis output's shape is the contract, not
  a Pydantic model.
- `orjson` for speed: rejected — stdlib `json` is well under the 5s
  SC-001 budget even for 96k-event fixtures (measured under 1 s in
  informal tests); premature optimization.

## R3 — Test framework

**Decision**: `pytest` (dev dependency, not runtime).

**Rationale**:

- Wider pytest familiarity in Python projects than `unittest`.
- Fixture parametrization is useful for the "run the same checks
  against both committed parser-output fixtures" pattern.
- Already implied by the repo-root `.pytest_cache/` artifact present
  from earlier work; no new tooling footprint.

**Alternatives considered**:

- `unittest`: rejected — more boilerplate for the same tests.
- No test framework / ad-hoc scripts: rejected — Principle IV
  mandates a real, runnable fixture-based test suite.

## R4 — CLI argument & output-path convention

**Decision**: Single positional argument — the path to a Parser-layer
output JSON file. Output is written to a sibling file whose name is
the input filename with the suffix `.analysis.json` appended, so a
full run looks like:

```text
parser/parse.js              sample_replays/base_1.w3g
  → writes                   sample_replays/base_1.w3g.json
processor/analyze.py         sample_replays/base_1.w3g.json
  → writes                   sample_replays/base_1.w3g.analysis.json
```

The analyzer replaces a trailing `.json` on the input with
`.analysis.json` if present (so a user passing `x.w3g.json` gets
`x.w3g.analysis.json`, not `x.w3g.json.analysis.json`).

**Rationale**:

- FR-002 requires a deterministic output location derived from the
  input path so that the Visualizer can locate output "by convention,
  no configuration".
- Mirrors the Parser's convention (`<input>.json` produced from
  `<input>`). The Processor's output sits right alongside.
- The `.analysis.json` suffix makes the file type self-describing in
  a flat directory listing and avoids extension collisions.

**Alternatives considered**:

- A flag-based output path (`--out`): rejected — FR-002 specifies a
  deterministic convention; a flag is configuration, a speculative
  option, and Principle III territory.
- Writing into a sibling `analysis/` directory: rejected — adds a
  directory-creation concern and splits parser/processor artifacts
  across locations. Colocation is simpler.
- Overloading `<input>.json` (overwriting it): rejected — the parser
  output is the source of truth; the analyzer must not modify it
  (FR-011).

## R5 — Source of the entity-name mapping

**Decision**: Derive `entity_names.json` from `w3gjs`'s bundled data
tables at `parser/node_modules/w3gjs/dist/cjs/mappings.js`. The
tables `items`, `units`, `buildings`, `upgrades`, and `heroAbilities`
contribute entries directly. Hero unit IDs (absent as keys from
`w3gjs`'s tables) are derived from `heroAbilities` + `abilityToHero`:
each hero-ability value is formatted `"a_<HeroName>:<AbilityName>"`,
so the `HeroName` portion, joined to the hero ID that `abilityToHero`
points to, yields `{ <heroId>: <HeroName> }` entries.

The `w3gjs` category prefixes (`i_`, `u_`, `p_`, `b_`, `a_`) are
stripped. Ability values of the form `a_Hero:Ability` are collapsed
to just the ability name (`"Ability"`) for the `entity_names.json`
entry, because the hero context is already available wherever the
ability ID appears in the analysis output (inside a hero's
`abilityOrder`).

The extraction runs **once**, at plan/task time, and the resulting
`entity_names.json` is committed as a static, reviewable artifact.
The analyzer never shells out to Node or reads `mappings.js` at
runtime.

**Rationale**:

- `w3gjs` is the canonical semantic source (Principle II). Copying
  its data once, with attribution, is faithful and deterministic.
- Running the extraction at plan/task time (not runtime) preserves
  layer separation: the Processor does not depend on the Parser's
  `node_modules/` being present.
- Re-extracting after a `w3gjs` upgrade is a well-defined, reviewable
  change (`entity_names.json` diff in a PR).

**Alternatives considered**:

- Hand-curating the mapping against external WC3 references:
  rejected — higher effort, higher error rate, no upstream to trust.
- Reading `mappings.js` at analyzer startup: rejected — adds a
  Node/w3gjs dependency to the Processor's runtime, violates
  Principle I.
- Publishing the mapping as a shared Python package: rejected —
  Principle III. A static JSON file in-repo is sufficient today.

## R6 — Coverage guarantees of the mapping

**Decision**:

1. Every entity ID observed in either committed fixture
   (`base_1.w3g.json`, `base_2.w3g.json`) resolves to a name
   (enforced by a test — SC-002).
2. All four standard WC3:TFT races' heroes, non-hero units,
   buildings, upgrades, items, and hero abilities are covered
   (extracted from `w3gjs`). A race-roster review checklist lives
   in `processor/DATA.md` and is walked once at ratification
   (SC-003).
3. Custom-map-only entities and modded content are **out of scope**
   for v1 (spec's Out of Scope).

**Rationale**:

- `w3gjs`'s tables already cover the standard rosters — see the
  `items`, `units`, `buildings`, `upgrades`, `heroAbilities`
  sections of `mappings.js`. The review is a read-through, not a
  data-entry task.
- Going beyond standard rosters (e.g., every custom unit in every
  Warcraft III custom map) is unbounded work with negligible payoff
  for the MVP visualizer.

**Alternatives considered**:

- Dynamic coverage ("whatever the fixtures happen to reference"):
  rejected — a new fixture immediately produces gaps and the
  Visualizer renders `"hfur"` instead of `"Furbolg Shaman"` until
  someone files a ticket. FR-005's "beyond fixtures" language
  precludes this.
- Exhaustive custom-map coverage: rejected — scope creep without a
  user.

## R7 — Handling an unmapped entity ID at runtime

**Decision**: When the analyzer encounters an entity ID present in
the parser output but absent from `entity_names.json`, it emits the
analysis document as normal, but:

- In the analysis JSON, the `name` field for that entity is the raw
  ID itself (e.g., `"hfxx"`) and is paired with a boolean
  `unknown: true` flag so downstream renderers can style unmapped
  entries distinctly.
- A diagnostic line is written to stderr naming the ID and its
  category (e.g., `[analyze] warn: unmapped building id "hfxx"`).
  Diagnostics are deduplicated per `(category, id)` tuple within a
  single run, collected in an in-process `set()`.

The process exits `0` on successful analysis even when diagnostics
were emitted. Missing-ID diagnostics are not errors; the analysis is
still valid.

**Rationale**:

- FR-006 specifies this behavior: placeholder + deduplicated
  diagnostic, analyzer does not fail.
- Patch-day replays must still render. Failing the run would block
  the Visualizer for every new unit Blizzard ships.

**Alternatives considered**:

- Fail on any unmapped ID: rejected — spec FR-006 forbids it.
- Silent placeholder, no diagnostic: rejected — gaps would rot
  undetected; FR-006 requires an operator-visible signal.
- Per-occurrence diagnostic: rejected — a single-player replay with
  100 Peasants would emit 100 lines; dedup-per-ID is the usable
  signal.

## R8 — Time-value representation

**Decision**: All in-game timestamps in the analysis document remain
raw milliseconds (`int`), matching the Parser's representation. The
Processor does NOT convert them to `mm:ss` strings or other
display-formatted values.

**Rationale**:

- The Visualizer owns presentation (Principle I, layer
  responsibility). Formatting at the Processor layer would force
  every Visualizer rendering choice (locale, precision, long-form
  vs. short-form) to be pre-baked.
- Raw ms is the lingua franca for charting, sorting, filtering, and
  arithmetic downstream.
- Matches the Parser's convention (`duration`, `timeMS`, `msElapsed`
  are all ms), so no impedance mismatch across the pipeline.

**Alternatives considered**:

- Emit both raw ms and a preformatted `"mm:ss"`: rejected —
  duplicates data, couples Processor to Visualizer display choices.
- Convert to seconds (float): rejected — introduces rounding and
  breaks round-trip identity with parser values.

## R9 — Determinism and the `parseTime` field

**Decision**: The analyzer treats the Parser's `parseTime` field as
pass-through but stores it under a clearly-labeled key in the
analysis output (e.g., `diagnostics.parserParseTimeMs`). The
Processor's own work produces no additional non-deterministic
fields; re-running the analyzer on the same parser-output file
produces byte-identical analysis JSON except for the pass-through
`parseTime`.

This aligns with SC-007's "modulo any field the Parser itself
flagged as non-deterministic" language.

**Rationale**:

- `parser/DATA.md` documents `parseTime` as library-derived and
  varying across runs. Hiding it would silently drop information;
  mixing it into top-level fields would make replays look "different"
  for non-replay reasons.
- Surfacing it under `diagnostics` keeps it discoverable without
  polluting user-facing metrics.

**Alternatives considered**:

- Drop `parseTime` entirely: rejected — it is useful for diagnosing
  parser-layer regressions, and the spec's pass-through convention
  covers it.
- Treat it as a top-level match attribute: rejected — it has nothing
  to do with the match.

## R10 — Test-fixture strategy

**Decision**:

1. The parser-output fixture for `base_1.w3g` already exists
   (`sample_replays/base_1.w3g.json`) and is used as-is.
2. The parser-output fixture for `base_2.w3g` is generated once,
   during Phase 2 tasks, by running the already-delivered
   `parser/parse.js` on `sample_replays/base_2.w3g`, and the
   resulting `sample_replays/base_2.w3g.json` is committed to the
   repository.
3. Tests load these JSON files from disk (they are the sole input
   contract). They do NOT shell out to `parser/parse.js` during the
   test run.
4. All analysis assertions are expressed against observable
   invariants (e.g., "every fixture player's race is one of
   H/O/U/N/R", "every entity ID in the build order is mapped"), not
   against byte-for-byte snapshots of analysis JSON. Snapshots are
   brittle and hide meaningful regressions behind acceptable
   whitespace changes.

**Rationale**:

- Committing parser-output JSON as a test fixture preserves strict
  layer separation (Principle I, Principle IV): Processor tests
  never cross into Parser runtime.
- Re-generating the fixture is a one-command operation; keeping it
  static is cheap and keeps tests fast.
- Invariant-based assertions survive benign re-generation of the
  parser output when `w3gjs` is upgraded non-semantically.

**Alternatives considered**:

- Generate parser-output fixtures on the fly during test setup:
  rejected — introduces a Node runtime dependency into Python
  tests, violates Principle I at the test layer.
- Snapshot-test the analysis JSON: rejected — noise from benign
  changes (adding a field, reordering a dict), no semantic signal.

## R11 — Packaging

**Decision**: A minimal `processor/pyproject.toml` declaring the
package name, Python version requirement, and a `[dev]` extra with
`pytest`. No `setuptools`-specific build backend; no entry-point
shim. The analyzer is invoked as `python processor/analyze.py
<parser-output.json>`.

**Rationale**:

- `pyproject.toml` is the modern Python project marker and
  configures pytest discovery cleanly. It is NOT being used for PyPI
  distribution.
- An entry-point script (`boovcraft-analyze`) would require
  `pip install -e .` in a venv before anything works — friction
  without payoff for an internal tool.

**Alternatives considered**:

- Bare `requirements-dev.txt`: rejected — `pyproject.toml` is
  idiomatic and carries pytest config too.
- Full `setuptools` packaging with entry points: rejected — YAGNI.

## Open items

None. All entries above are settled; Phase 1 design can proceed.
