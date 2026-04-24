# Feature Specification: Replay Analyzer

**Feature Branch**: `002-replay-analyzer`
**Created**: 2026-04-23
**Status**: Draft
**Input**: User description: "The second tool in the pipeline is a python script that does the actual replay analysis. It will produce output that contains all data, necessary for the visualizer. The development consists of 3 steps: defining the metrics that can be extracted from the replay data — use already developed parser on real replays and see what can be extracted; creating an internal warcraft 3 entity ID (raw code) to human readable name mapping (for example `Nfir` → `Firelord`, `hpea` → `Peasant`), saved as a static JSON file, including entities that do not appear in the fixture replays (look up within w3gjs or online); writing the actual script."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Produce A Visualizer-Ready Match Report From A Parsed Replay (Priority: P1)

A developer working on the visualizer layer points a tool at the Parser's JSON output for a single replay and receives a single analysis JSON document that contains every metric a match-report page would display: match metadata, per-player statistics, build orders, timelines, hero progression, resource transfers, and chat. They never need to open the raw parser output, interpret event streams, or cross-reference WC3 codes themselves.

**Why this priority**: This is the raison d'être of the Processor layer. Without it, the pipeline has a raw-data layer (Parser) and a presentation layer (Visualizer) with nothing in between. Every downstream visualization or stats feature depends on this document.

**Independent Test**: Run the analyzer against the committed parser-output fixture (`sample_replays/base_1.w3g.json`) and confirm that (a) a single analysis JSON document is written to a predictable location, and (b) that document contains — at minimum — match-level metadata, one entry per player with their stats and build order, and any chat messages that were in the replay, all in a form a downstream renderer can consume without further transformation.

**Acceptance Scenarios**:

1. **Given** a parser output file written by the Parser layer, **When** the analyzer is run against it, **Then** a single analysis JSON document is written to disk and the process exits successfully.
2. **Given** the written analysis document, **When** a consumer opens it, **Then** they can locate match-level facts (duration, map, winning team, version, matchup), each player's identity and final statistics (race, APM, color, team), each player's ordered build history (buildings, units, upgrades, items with in-game timestamps), hero progression (heroes played, final levels, ability-learn sequence), inter-player resource transfers, and all chat messages — without having to open or interpret the raw parser output.
3. **Given** a parser output file that covers a replay with no chat and no resource transfers (`base_2.w3g`), **When** the analyzer is run, **Then** the analysis document still exits successfully with empty arrays for those sections rather than missing keys or an error.
4. **Given** a parser output file whose structure does not match the Parser layer contract (e.g., wrong shape, missing required top-level keys), **When** the analyzer is run, **Then** the process exits with a non-zero status, emits a clear diagnostic, and writes no partial output artifact.

---

### User Story 2 - Human-Readable Entity Names Everywhere (Priority: P2)

A developer reading the analysis output — whether for the visualizer, debugging, or spot-checking a match — sees human-readable names for every Warcraft III entity referenced (heroes, non-hero units, buildings, upgrades, items, and hero abilities). They never have to memorize, look up, or pipe through another tool to turn `"Nfir"` into `"Firelord"` or `"hpea"` into `"Peasant"`.

**Why this priority**: Raw WC3 codes are unreadable. A match report that shows `"hkee"` instead of `"Keep"` is unusable by a non-specialist and a daily nuisance for a specialist. The mapping is the bridge between the Parser's fidelity-first output and the Visualizer's usability.

**Independent Test**: Open the static ID→name mapping file directly and verify that the entity IDs observed across both committed fixture replays (`base_1.w3g.json` and `base_2.w3g.json`) — heroes, units, buildings, upgrades, items, and hero abilities — all resolve to plausible human names. Separately, spot-check a sample of entity IDs that do **not** appear in either fixture (for example, a race hero or an item that neither match featured) and confirm the mapping covers them too.

**Acceptance Scenarios**:

1. **Given** the static ID→name mapping file alone, **When** a developer looks up any entity ID that the Parser could realistically emit for a standard WC3:TFT replay, **Then** they find a human-readable display name.
2. **Given** the analysis JSON document, **When** an entity ID appears in any build-order entry, summary map, hero-ability reference, or hero-unit reference, **Then** it is accompanied by its human-readable name (so the consumer does not have to join against the mapping file to render a label).
3. **Given** an entity ID present in the parser output but absent from the mapping, **When** the analyzer runs, **Then** it produces the analysis document with a clearly-marked placeholder name (the raw ID itself, or an explicit "unknown" indicator) so that a downstream renderer still renders something, and it emits a diagnostic identifying the missing ID so the mapping can be updated.
4. **Given** the mapping file, **When** a new WC3 entity becomes relevant (a future fixture, a new patch, a reported gap), **Then** a developer can extend the mapping by editing a single static JSON file — no code change, no analyzer rebuild.

---

### User Story 3 - Documented Catalog Of What The Analyzer Emits (Priority: P3)

A developer building the Visualizer, or adding a new analysis, needs to know exactly what fields the analyzer's output contains, what each field means, and which parser-output source each was derived from — without reading the analyzer's source code and without running it on a fixture.

**Why this priority**: The analysis JSON is the sole contract between Processor and Visualizer (constitution, Principle I). The Parser already ships `parser/DATA.md` for its layer; the Processor needs the same. It is not required for the first end-to-end run (US1), so it ranks below P1 and P2, but it is required before the Analyzer is considered complete.

**Independent Test**: Hand the Analyzer's output-structure document to a developer who has never seen the analyzer's output. Ask them to describe, from the document alone, how they would render a "build order" section, a "chat log" section, and a "player APM bar chart" in the visualizer. They should be able to answer without opening source code or sample output.

**Acceptance Scenarios**:

1. **Given** the output-structure document, **When** a developer reads it, **Then** for every top-level and nested field in the analysis JSON they can identify its name, type, meaning, and the parser-output source that produced it.
2. **Given** a change to the analyzer's output shape, **When** the change lands, **Then** the document is updated in the same change.
3. **Given** the document, **When** a developer considers adding a new metric, **Then** they can tell whether the data they need is already emitted, is derivable from the current parser output, or requires a new Parser-layer feature.

---

### Edge Cases

- **Parser output file does not exist or is unreadable**: Analyzer exits non-zero with a clear message; no analysis file is produced.
- **Parser output file exists but is not valid JSON**: Analyzer exits non-zero with a clear message; no analysis file is produced.
- **Parser output file is valid JSON but does not match the Parser-layer contract** (missing required keys, wrong types): Analyzer exits non-zero with a clear message; no analysis file is produced.
- **Replay covered by the parser output contained no chat** (`base_2.w3g` case): Analysis document still emits a chat section (an empty array), not a missing key.
- **Replay contained observers**: Observers are surfaced as a distinct section in the analysis document and are not mixed into per-player statistics.
- **`winningTeamId` is `-1`** (w3gjs could not determine a winner): Analysis document surfaces this state explicitly (e.g., `winner: null` with a flag indicating indeterminate) rather than suppressing it or claiming a default team won.
- **An entity ID appears in the parser output but is absent from the mapping**: Analyzer emits the analysis document with a placeholder name for that entity and emits a diagnostic naming the missing ID and its category. The analyzer does not fail.
- **The same ID is missing from the mapping across many entries**: The diagnostic is emitted once per missing ID, not once per occurrence.
- **Analysis output file already exists at the target location**: Analyzer overwrites it deterministically (no prompt, no rename, no error), matching the Parser layer's behavior.
- **Analysis output location is not writable** (permissions, read-only disk): Analyzer exits non-zero with a clear message.
- **Mapping file itself is malformed or missing**: Analyzer exits non-zero with a clear message before processing any replay data.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept a path to a single Parser-layer output file (the JSON document produced by the Parser layer) as its input.
- **FR-002**: The system MUST produce a single analysis JSON document per invocation, written to a deterministic location derived from the input path so that the Visualizer layer can locate it without extra configuration.
- **FR-003**: The analysis document MUST contain, at minimum:
  - Match-level metadata: game version, build number, duration, map (path, filename, checksums), matchup shorthand, game type (`4on4`, `3on3`, etc.), starting spots, game-speed and lobby settings, winning team identity (or explicit "undetermined"), and the list of observers.
  - Per-player entries for every non-observer slot, including the player's display identity (name, team, color), race (both chosen and detected), final APM, hotkey-group usage, per-category action counts, the per-bucket action timeline (with the bucket width surfaced), the full ordered build history (buildings, units, upgrades, items — each entry stamped with in-game time and accompanied by a human-readable name), hero progression (heroes played, final level, ability-learning sequence with human-readable ability names), and any resource transfers the player sent to allies.
  - A chat section listing every in-game chat message (sender, channel, time, text).
- **FR-004**: The analysis document MUST translate every Warcraft III entity ID it references (hero IDs, unit IDs, building IDs, upgrade IDs, item IDs, hero-ability IDs) into a human-readable display name, using the static mapping artifact defined in FR-005.
- **FR-005**: The system MUST ship a static, human-readable JSON mapping artifact from WC3 entity IDs (e.g., `"Nfir"`, `"hpea"`, `"AHbz"`) to human-readable display names (e.g., `"Firelord"`, `"Peasant"`, `"Blizzard"`).
  - The mapping MUST cover every entity ID observed across the committed fixture replays.
  - The mapping MUST also cover entity IDs that the fixtures do not exercise but that standard WC3:TFT replays may contain — including all four races' heroes, non-hero units, and buildings; the standard upgrade and item rosters; and hero abilities. Sources for the non-fixture entries are the `w3gjs` library's own data tables and public WC3 references.
  - The mapping artifact MUST live on disk as a static file that can be edited, diffed, and reviewed independently of executable code.
- **FR-006**: The system MUST, when it encounters an entity ID present in the parser output but absent from the mapping, emit the analysis document with a placeholder name for that entity AND emit a diagnostic message (to the operator, not the analysis document) naming the missing ID and its category, deduplicated per ID.
- **FR-007**: The system MUST exit with a non-zero status and emit a clear diagnostic message when (a) the parser-output file is missing, unreadable, not valid JSON, or does not match the Parser-layer contract, (b) the mapping artifact is missing or malformed, or (c) the analysis output location is not writable. In these cases, no partial analysis file MUST be written.
- **FR-008**: The system MUST overwrite an existing analysis file at the target location without prompting.
- **FR-009**: A documentation artifact describing the analysis output's shape — every top-level and nested field, with name, type, meaning, and the parser-output source from which it was derived — MUST exist alongside the analyzer. This document MUST be updated whenever the output shape changes.
- **FR-010**: The system MUST NOT re-parse `.w3g` replay files and MUST NOT invoke the Parser layer's runtime. It reads only the Parser layer's JSON output, per the three-layer separation principle.
- **FR-011**: The system MUST NOT modify the Parser layer's output file or any other upstream artifact.
- **FR-012**: The analysis document MUST be structured so that adding a new metric that can be computed from the existing parser output is a pure Analyzer-layer change — requiring no Parser-layer edit and no new mapping entries unless a genuinely new entity is referenced.

### Key Entities

- **Parser output file**: The JSON document produced by the Parser layer for a single `.w3g` replay. The sole input to this feature. Its contents and contract are defined in `parser/DATA.md`.
- **Entity-name mapping**: A static JSON artifact mapping WC3 4-character entity IDs to human-readable display names, covering heroes, units, buildings, upgrades, items, and hero abilities across all standard WC3:TFT races. A shared project data asset, edited and reviewed independently of analyzer code.
- **Analysis output file**: A single JSON document per replay that contains the visualizer-ready match report: match metadata, per-player statistics, build orders with readable names, hero progression, resource transfers, chat, and observers. The sole contract between the Processor and Visualizer layers.
- **Output-structure documentation**: A human-readable document describing the analysis output's fields, types, semantics, and provenance. The contract for downstream consumers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Running the analyzer on the parser output of a typical 1 MB replay produces a valid, non-empty analysis JSON file in under 5 seconds on commodity hardware.
- **SC-002**: For both committed fixture replays, 100% of entity IDs appearing anywhere in the parser output (heroes, units, buildings, upgrades, items, hero abilities) resolve to a human-readable name in the analysis output — verified by a test that collects every ID from the parser output and asserts none resolves to a placeholder.
- **SC-003**: The entity-name mapping additionally covers every standard WC3:TFT hero (all four races) and the standard non-hero-unit, building, upgrade, and item rosters for all four races, even those absent from the fixtures — verified by a review checklist of race rosters.
- **SC-004**: A developer unfamiliar with the analyzer can, using only the output-structure documentation, locate the field in the analysis document corresponding to any piece of match information the visualizer needs, in under 2 minutes per field — measured by spot-checking during review.
- **SC-005**: A new analysis metric that derives from parser-output fields already covered by the analyzer can be added without editing any file outside the Processor layer and without adding any new mapping entries — measured over the first three post-MVP metric additions.
- **SC-006**: Every analyzer failure produces a diagnostic a developer can act on within 1 minute (identifying which file, why, and what to do next) — verified by reviewing captured messages across the edge-case set.
- **SC-007**: Re-running the analyzer on the same parser-output file produces byte-identical analysis output (modulo any field the Parser itself flagged as non-deterministic, which the analyzer surfaces verbatim) — verified by a re-run-and-diff test.

## Assumptions

- **Upstream contract is `parser/DATA.md`**: The analyzer reads the JSON document described by `parser/DATA.md` and treats every field documented there as authoritative. It does not invoke Node, `w3gjs`, or any Parser-layer code in-process (constitution, Principle I).
- **Scope of metrics is derived empirically from real replays**: The concrete per-field metric list the analyzer emits is established during the first step of implementation by inspecting the parser output for both committed fixtures. The spec commits to the categories listed in FR-003; the exact field names and shapes are settled in `/speckit.plan` and `/speckit.tasks`.
- **Output location convention**: The analysis file lives at a deterministic path next to the parser-output file (e.g., `<parser-output>.analysis.json`), unless a future feature introduces a configurable location. Downstream tooling locates output by convention, mirroring the Parser layer.
- **Output format**: A single JSON document per replay. JSON is the inter-layer transport for the whole project (constitution, Technology Stack & Interface Contracts).
- **Mapping coverage is exhaustive for standard WC3:TFT**: The mapping covers all four races' heroes, non-hero units, buildings, upgrades, items, and hero abilities that standard melee ladder replays may contain. Custom-map-only entities, neutral-building shop entities beyond the standard roster, and arbitrary modded content are out of scope for the initial mapping and can be added incrementally as gaps are reported via FR-006 diagnostics.
- **Mapping shape is a flat id→name map**: The initial mapping is `{ "<4-char id>": "<display name>" }`. Enriched structures (category, race, portrait reference) are NOT introduced until the Visualizer demonstrably needs them (constitution, Principle III — no premature abstractions).
- **Mapping file is a shared data asset**: The mapping JSON is consumed by the Analyzer now and by the Visualizer in a later feature. Its on-disk location — whether inside `processor/` or at a repo-level `data/` directory — is a plan-time decision, not a spec-time decision.
- **Single-file invocation**: Each analyzer run processes one parser-output file. Batch, streaming, or watch-mode invocation is out of scope for this feature.
- **Fixture-based testing**: Tests exercise the committed fixtures `sample_replays/base_1.w3g.json` and `sample_replays/base_2.w3g.json` (produced by the Parser layer). No mocks, no synthetic parser-output fragments (constitution, Principle IV).
- **Chat in fixtures**: `base_1.w3g` contains 81 chat messages; `base_2.w3g` contains none. Both are exercised to cover the "chat present" and "chat absent" branches.
- **Pass-through of library-derived fields**: Values the Parser forwards from `w3gjs` (APM, matchup, `winningTeamId`, action-category counts, etc.) are treated as inputs to the analyzer, not recomputed. The analyzer is free to reshape, rename, and enrich them for visualizer consumption but does not second-guess the library's math.

## Out of Scope

- Re-parsing `.w3g` files. All `.w3g` parsing happens in the Parser layer.
- Cross-replay analytics (match series, ladder trends, head-to-head over time). This feature analyzes one replay at a time.
- Any visualization or rendering. Output is structured data only.
- A schema validator for the analysis output. The output-structure document is the contract.
- Uploading results, a web UI, a service, or any networked invocation.
- Internationalization of entity display names. The mapping is English-only for v1.
- Portraits, icons, lore, or other presentation assets for entities. The mapping is names only.
- Replay formats other than `.w3g`.
- Custom-map-specific entities and modded content beyond the standard WC3:TFT rosters.
- Automatic updates to the mapping from upstream `w3gjs` or WC3 patches. Mapping updates are manual, diagnostic-driven, and reviewed in-repo.
