---
description: "Task list for feature 002-replay-analyzer"
---

# Tasks: Replay Analyzer

**Input**: Design documents from `/specs/002-replay-analyzer/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Test tasks ARE included because fixture-based testing of the Processor layer is mandated by the project constitution (Principle IV). Tests are written before the implementation they verify (TDD posture within each user-story phase).

**Organization**: Tasks are grouped by user story so each story can be implemented, tested, and demonstrated independently. MVP = Phase 1 + Phase 2 + Phase 3 (US1).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on still-incomplete tasks)
- **[Story]**: Which user story this task belongs to (US1, US2, US3). Setup / Foundational / Polish tasks have no story label.
- File paths in every implementation task are exact and rooted at the repository root.

## Path Conventions

- **Processor source**: `processor/`
- **Processor tests**: `processor/tests/`
- **One-off tooling**: `processor/tools/`
- **Shared fixtures**: `sample_replays/` (at repo root; fixtures shared with the Parser layer)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the Processor layer's directory skeleton and packaging metadata.

- [X] T001 Create the processor-layer directory skeleton at repo root: `processor/`, `processor/tests/`, `processor/tools/`. The directories are empty placeholders at this stage.
- [X] T002 [P] Create `processor/pyproject.toml` declaring `[project] name = "boovcraft-processor"`, `requires-python = ">=3.11"`, no runtime dependencies, and an optional `[project.optional-dependencies] dev = ["pytest"]`. Include a minimal `[tool.pytest.ini_options] testpaths = ["tests"]`. No build backend required beyond `setuptools` default.
- [X] T003 [P] Append entries to the repo-root `.gitignore` covering Python virtualenv and cache artifacts under `processor/`: `processor/.venv/`, `processor/**/__pycache__/`, `processor/.pytest_cache/`. Do NOT touch the existing `sample_replays/*.json` rule in this task — that rule is revised in Phase 2 (T004).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Produce the committed parser-output fixtures the Processor's tests consume (Principle IV), and stand up the initial (empty) entity-name mapping so the analyzer can load it from day one.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete. US1's tests require both fixtures on disk, and the analyzer contract (`contracts/analyzer-cli.md`) requires `processor/entity_names.json` to exist and be valid JSON.

- [X] T004 Revise the repo-root `.gitignore` rule for `sample_replays/`: replace the existing `sample_replays/*.json` line with `sample_replays/*.analysis.json`. This tracks parser-output JSON as committed fixtures (shared across Parser and Processor layers, per Principle IV and the `plan.md` Project Structure section) while still ignoring the Processor's per-run analysis artifacts.
- [X] T005 Regenerate `sample_replays/base_1.w3g.json` and create `sample_replays/base_2.w3g.json` by running the already-delivered Parser layer against the committed `.w3g` fixtures: from the repo root run `(cd parser && npm install)` once if `parser/node_modules/` is empty, then `node parser/parse.js sample_replays/base_1.w3g` and `node parser/parse.js sample_replays/base_2.w3g`. `git add -f` both `.w3g.json` files (the prior T004 gitignore change admits them).
- [X] T006 [P] Create `processor/entity_names.json` containing exactly the empty JSON object `{}` (one line: `{}\n`). This satisfies the analyzer's precondition that the mapping file exists and is valid JSON. The file is fully populated in Phase 4 (US2) — for US1's purposes it means every entity resolves to its raw-ID placeholder with `unknown: true`.
- [X] T007 [P] Create `processor/tests/__init__.py` (empty) and `processor/tests/conftest.py` exposing two session-scoped pytest fixtures: `base_1_parser_output` and `base_2_parser_output`, each of which reads the corresponding committed `sample_replays/base_*.w3g.json` and returns the parsed Python dict. No other test infrastructure in this file.

**Checkpoint**: Foundation ready — `processor/` is a valid Python package skeleton, both committed parser-output fixtures exist, the empty mapping is in place, and pytest fixtures for both replays load cleanly. User-story phases can now proceed.

---

## Phase 3: User Story 1 — Produce A Visualizer-Ready Match Report (Priority: P1) 🎯 MVP

**Goal**: Given a parser-output JSON file, write a complete analysis JSON file that the Visualizer layer can consume directly — match metadata, per-player statistics with build orders, hero progression, resource transfers, chat, and observers. Entity-name resolution uses whatever is in `processor/entity_names.json`; during this phase the map is empty, so entities come out as `unknown: true` placeholders. That is correct, spec-compliant behavior (FR-006 graceful degradation) and lets this story be tested independently of US2.

**Independent Test**: From the repo root (venv active), run `python processor/analyze.py sample_replays/base_1.w3g.json` and `python processor/analyze.py sample_replays/base_2.w3g.json`. Both exit 0, each writes a sibling `.analysis.json` file, `pytest processor/tests/` passes, and every invariant in `contracts/output-shape.md` §Invariants holds for both fixtures. During this phase, stderr for both runs will contain unmapped-entity warnings (one per `(category, id)`) — expected; US2 will remove those.

### Tests for User Story 1 (written first; must fail before implementation)

- [X] T008 [P] [US1] Create `processor/tests/test_cli.py` covering: (a) `python -m subprocess`-invoking the analyzer against both fixture parser-output files and asserting exit 0 and that the expected `.analysis.json` sibling file is created; (b) analyzer exits 1 with `[analyze] error:` stderr when given a nonexistent path; (c) analyzer exits 1 when given a file whose content is not valid JSON; (d) analyzer exits 1 when given a valid JSON file missing required top-level keys (e.g., `players`); (e) re-running on the same input produces byte-identical output EXCEPT for `diagnostics.parserParseTimeMs` (SC-007); (f) stdout is empty on success.
- [X] T009 [P] [US1] Create `processor/tests/test_output_shape.py` asserting the output-shape contract invariants from `contracts/output-shape.md` against both committed fixtures: top-level key set is exactly `{match, settings, map, players, observers, chat, diagnostics}`; `match.durationMs` non-negative; `match.winner` is null or `{teamId: int}`; every player's `race ∈ {H,O,U,N,R}` and `raceDetected ∈ {H,O,U,N}`; exactly one team has `isWinner=true` iff `match.winner` is non-null; `players[i].production` has exactly the four sub-keys with `order` + `summary`; chat entries have the exact documented key set; all `*Ms` fields are integers; `diagnostics.unmappedEntityIds` is a deduplicated list of `{category, id}` pairs.
- [X] T010 [P] [US1] Create `processor/tests/test_fixture_facts.py` asserting fixture-specific facts grounded in `parser/DATA.md`: `base_1` analysis has 8 player entries, 81 chat entries, 0 observers; `base_2` analysis has 6 player entries, 0 chat entries, 0 observers; `base_1.match.gameType == "4on4"` and `base_2.match.gameType == "3on3"`; every player's `id`, `name`, `color` passes through unchanged from the parser output; `diagnostics.parserId` equals `ParserOutput.id` verbatim.

### Implementation for User Story 1

- [X] T011 [US1] Scaffold `processor/analyze.py` with: module docstring referencing `contracts/analyzer-cli.md`; `main(argv)` entry point using `argparse` with one positional `parser_output`; `_err(msg)` helper writing `[analyze] error: {msg}` to stderr and returning exit code 1; `_warn(category, id, seen_set)` helper writing `[analyze] warn: unmapped {category} id "{id}"` to stderr only when `(category, id)` is new in `seen_set`; output path derivation (if input endswith `.json`, strip it and append `.analysis.json`, else append `.analysis.json`); atomic-write helper `_write_json_atomic(path, obj)` that writes to `path + ".tmp"` and `os.replace`s into place on success. The `main()` function reads inputs, calls a single top-level `build_analysis(parser_output, mapping, warn_fn) -> dict`, writes output, and returns 0. `build_analysis` is defined in this task but implemented incrementally in T012–T018 as a growing dict.
- [X] T012 [US1] In `processor/analyze.py`, implement `_build_match(parser_output)`, `_build_settings(parser_output)`, `_build_map(parser_output)`, `_build_observers(parser_output)` returning `MatchMetadata`, `LobbySettings` (verbatim forward), `MapInfo` (verbatim forward), and the observers string array. `_build_match` derives `winner` from `winningTeamId` per data-model.md: non-null `{teamId}` when the parser's `winningTeamId >= 0`, else `null`. Wire these into `build_analysis`.
- [X] T013 [US1] In `processor/analyze.py`, implement `_resolve_entity(category, entity_id, mapping, warn_fn)` returning the dict `{id, name, unknown}` per §Invariant 11 of `contracts/output-shape.md`. When `entity_id not in mapping`: `name = entity_id`, `unknown = True`, and `warn_fn(category, entity_id)` is called for the deduplicated stderr diagnostic. When present: `name = mapping[entity_id]`, `unknown = False`.
- [X] T014 [US1] In `processor/analyze.py`, implement `_build_production(player, mapping, warn_fn)` returning the `production` object for a single player, iterating `player["buildings"]`, `player["units"]`, `player["upgrades"]`, `player["items"]` from the parser output. For each: produce `order[i] = {..._resolve_entity(category, id, mapping, warn_fn), "timeMs": ms}` using the parser's `{id, ms}` entries; produce `summary[id] = {..._resolve_entity(..), "count": n}` for every `(id, n)` in the parser's `summary` map. Category strings used for diagnostics: `"building"`, `"unit"`, `"upgrade"`, `"item"`.
- [X] T015 [US1] In `processor/analyze.py`, implement `_build_heroes(player, mapping, warn_fn)` returning the `heroes` array. For each hero in `player["heroes"]`: resolve the hero id via `_resolve_entity("hero", h["id"], ...)`; emit `level` from `h["level"]`; build `abilityOrder` by iterating `h["abilityOrder"]` in sequence and assigning each entry's `level` field as `1, 2, 3, ...` counting from the first occurrence of its ability `value` (i.e., a per-ability-id running counter within the sequence); resolve each ability via `_resolve_entity("ability", value, ...)`; build `abilitySummary` as an object keyed by ability id with `{..._resolve_entity(...), "level": finalCount}` from `h["abilities"]`.
- [X] T016 [US1] In `processor/analyze.py`, implement `_build_player(player, mapping, warn_fn, match_winner_team_id)` stitching together the PlayerAnalysis record per data-model.md: pass-through `id, name, teamid→teamId, color, race, raceDetected, apm, groupHotkeys`; derive `isWinner` (`True` iff `match_winner_team_id is not None and match_winner_team_id == player["teamid"]`); build `actions` as `{apmTimeline: {bucketWidthMs: parser_output["apm"]["trackingInterval"], buckets: player["actions"]["timed"]}, totals: {every-key-of-player.actions-except-timed}}`; include `heroes`, `production`, and pass-through `resourceTransfers` renamed per data-model.md (`slot→fromSlot`, `playerId→toPlayerId`, `playerName→toPlayerName`, `gold`, `lumber`, `msElapsed→timeMs`). Wire into `build_analysis`: compute `match_winner_team_id` from match once, then map `_build_player` over `parser_output["players"]`.
- [X] T017 [US1] In `processor/analyze.py`, implement `_build_chat(parser_output)` remapping each `parser_output.chat[i]` to `{playerId, playerName, mode, text (from message), timeMs (from timeMS)}`; empty array when the source is empty. Wire into `build_analysis`.
- [X] T018 [US1] In `processor/analyze.py`, implement `_build_diagnostics(parser_output, unmapped_set, analyzer_version)` returning `{parserId: parser_output["id"], parserParseTimeMs: parser_output["parseTime"], unmappedEntityIds: sorted([{category, id} for (category, id) in unmapped_set]), analyzerVersion: analyzer_version}`. Read `analyzer_version` lazily from `processor/pyproject.toml` via `tomllib` at module import time (fall back to `"0.0.0"` if the file is unreadable during an in-tree invocation). Wire into `build_analysis` as the final key added to the output dict. The `unmapped_set` is populated in-place by `_warn` during the build.
- [X] T019 [US1] End-to-end smoke: run `python processor/analyze.py sample_replays/base_1.w3g.json` and `python processor/analyze.py sample_replays/base_2.w3g.json` and confirm each exits 0, writes the expected `.analysis.json`, and stderr lists unmapped-entity warnings (expected given the empty mapping). Then `pytest processor/tests/` and confirm all tests in T008–T010 pass.

**Checkpoint**: MVP ready — the analyzer consumes the Parser's JSON and emits complete analysis JSON that meets every structural invariant. Human-readable names are placeholders; that is closed out in US2.

---

## Phase 4: User Story 2 — Human-Readable Entity Names Everywhere (Priority: P2)

**Goal**: Populate `processor/entity_names.json` with exhaustive coverage of standard WC3:TFT entities (heroes, non-hero units, buildings, upgrades, items, hero abilities — all four races), sourced from `w3gjs`'s own `mappings.js`. After this phase, every entity reference in both committed fixtures resolves to a human-readable name with `unknown: false` and no stderr warnings.

**Independent Test**: Re-run `python processor/analyze.py sample_replays/base_1.w3g.json` and `...base_2.w3g.json`. Both exit 0 with empty stderr. `diagnostics.unmappedEntityIds` is `[]` for both outputs. `pytest processor/tests/test_entity_names.py` passes.

### Tests for User Story 2

- [X] T020 [P] [US2] Create `processor/tests/test_entity_names.py` with: (a) `test_mapping_shape` — loads `processor/entity_names.json`, asserts root is a dict, every key matches `^[A-Za-z0-9]{4}$`, every value is a non-empty string, no empty/whitespace-only values; (b) `test_fixture_coverage` — loads both committed fixture parser outputs, collects every 4-char entity id that appears in any hero id, ability id, and per-category `order`/`summary`/`abilities`, asserts every collected id is a key in the mapping (SC-002); (c) `test_no_unmapped_diagnostics_for_fixtures` — invokes `build_analysis` against both fixtures and asserts `diagnostics.unmappedEntityIds == []`.

### Implementation for User Story 2

- [X] T021 [US2] Create `processor/tools/build_entity_names.py` — a one-shot extraction script (not shipped as part of the analyzer runtime; it lives under `tools/` to make the separation explicit). Behavior: invoke `subprocess.run(["node", "-e", "const m = require('<REPO>/parser/node_modules/w3gjs/dist/cjs/mappings.js'); process.stdout.write(JSON.stringify({items: m.items, units: m.units, buildings: m.buildings, upgrades: m.upgrades, heroAbilities: m.heroAbilities, abilityToHero: m.abilityToHero}))"])` to dump the w3gjs data tables as JSON. Parse the JSON. Build `entity_names` as a flat dict by: (i) copying items/units/buildings/upgrades entries with values stripped of leading `i_`/`u_`/`p_`/`b_` prefixes if present; (ii) for each `heroAbilities` entry with value formatted `"a_<HeroName>:<AbilityName>"`, add `abilityId -> <AbilityName>` to the mapping AND derive `heroId -> <HeroName>` using `abilityToHero[abilityId]` as the hero id (collecting first-seen name, warning on in-mapping conflicts). Write the result to `processor/entity_names.json` sorted by key with a trailing newline. Add a `--check` mode that runs the extraction and diffs against the committed file, exiting nonzero if they differ — useful as a pre-merge sanity check after `w3gjs` upgrades.
- [X] T022 [US2] Run `python processor/tools/build_entity_names.py` and commit the resulting fully-populated `processor/entity_names.json`. Verify by inspection that both fixtures' entity IDs are present: heroes (`Edem, Hamg, Hblm, Hmkg, Nfir, Obla, Ucrl, Udea`), a spot-check of units (`hpea → Peasant`, `hfoo → Footman`), buildings (`hkee → Keep`, `etol → Tree of Life`), upgrades (`Rhme`), items (`bspd → Boots of Speed`), and abilities (`AHbz → Blizzard`, `AHfs → Flame Strike`).
- [X] T023 [US2] Re-run the full test suite (`pytest processor/tests/`) and confirm every test in T020 passes. Re-run the analyzer against both fixtures and confirm stderr is empty and `diagnostics.unmappedEntityIds` is `[]`.

**Checkpoint**: Names everywhere — analyzer output is visualizer-ready in the full sense. A developer scanning the `.analysis.json` sees `"Peasant"` and `"Firelord"`, not `"hpea"` and `"Nfir"`.

---

## Phase 5: User Story 3 — Documented Catalog Of Output (Priority: P3)

**Goal**: Publish `processor/DATA.md` — the Processor-layer counterpart to `parser/DATA.md` — describing every field of the analysis output, its type, its semantics, and the parser-output field it was derived from, plus a race-roster review checklist that anchors the coverage guarantee (SC-003).

**Independent Test**: Hand `processor/DATA.md` to a developer unfamiliar with the analyzer. Ask them to describe how they would render: (a) a build-order section, (b) the chat log, (c) an APM-per-minute bar chart. They should answer using only the document, citing specific field paths.

### Implementation for User Story 3

- [X] T024 [US3] Create `processor/DATA.md` with: top matter describing the file as the Processor→Visualizer contract and cross-referencing `specs/002-replay-analyzer/contracts/output-shape.md` and `parser/DATA.md`; §Output location documenting the `<input>.analysis.json` convention; §Top-level keys listing `match, settings, map, players, observers, chat, diagnostics` with one-line descriptions; per-section field tables (MatchMetadata, LobbySettings, MapInfo, PlayerAnalysis, ActionCounts, ProductionSection, HeroEntry, ResourceTransfer, ChatMessage, Diagnostics) each with columns `Key | Type | Origin (parser field) | Meaning`; §Volatility listing `diagnostics.parserParseTimeMs` as the single non-deterministic field; §Scope exclusions (event-level data, derived win inference, preformatted display strings).
- [X] T025 [US3] Append to `processor/DATA.md` a §Mapping coverage section listing the race rosters the mapping is required to cover per SC-003: Human (heroes Hamg/Hmkg/Hpal/Hblm; 13 unit types; 11 building types; upgrade and item ladder rosters); Orc (heroes Obla/Ofar/Otch/Obea; units, buildings, upgrades); Night Elf (heroes Edem/Emoo/Ekee/Ewar; units, buildings, upgrades); Undead (heroes Udea/Ucrl/Udre/Ulic; units, buildings, upgrades). For each entry, list the 4-char ids. This is the one-time review checklist that satisfies SC-003 and lives with the doc so future mapping regenerations can re-walk it in a PR.
- [X] T026 [US3] Review pass: walk the race-roster checklist from T025 against `processor/entity_names.json`, note any gaps, and if gaps exist, add the missing entries to `entity_names.json` manually (gap source: public WC3 reference per `contracts/mapping-shape.md`). Re-run tests.

**Checkpoint**: All three user stories are complete. The analyzer produces visualizer-ready JSON, names are exhaustive for standard ladder content, and the output contract is fully documented.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, developer-ergonomics polish, and performance verification.

- [X] T027 [P] Verify the quickstart walkthrough (`specs/002-replay-analyzer/quickstart.md`) by running every command in order from a fresh venv. Correct any drift between quickstart and actual behavior.
- [X] T028 [P] Measure analyzer wall-clock time on `sample_replays/base_1.w3g.json` (the larger ~4 MB parser-output fixture) via `/usr/bin/time -f "%e"` or equivalent and confirm it is under the 5-second SC-001 budget on the dev machine; record the measured value in the PR description when submitting this feature.
- [X] T029 Run the full Processor test suite once more (`pytest processor/tests/`) to confirm everything still passes after T022 and T026 edits. Run the Parser test suite (`cd parser && npm test`) to confirm no regression from the `.gitignore` change in T004. Both must pass.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup. BLOCKS all user-story phases.
- **User Story 1 (Phase 3)**: Depends on Foundational. Does NOT depend on US2/US3.
- **User Story 2 (Phase 4)**: Depends on Foundational. Soft-depends on US1 only in the sense that US2's acceptance test (`test_no_unmapped_diagnostics_for_fixtures`) invokes `build_analysis` from `processor/analyze.py` — which must exist. In parallel-team mode, US2 can be started against the in-progress US1 tree; in serial mode, US1 ships first.
- **User Story 3 (Phase 5)**: Depends on Foundational and on US1 (the output shape must be stable before it is documented). Does NOT depend on US2.
- **Polish (Phase 6)**: Depends on all desired user stories being complete.

### User Story Dependencies

- **US1 (P1)** is fully independent given Foundational.
- **US2 (P2)** reads the analyzer's behavior via its tests; depends on US1 being implemented (same-file edits precluded — T021 is its own file).
- **US3 (P3)** documents the analyzer output; depends on US1 (to have an output to document). Does NOT depend on US2.

### Within Each User Story

- Tests are written first (T008–T010 for US1, T020 for US2) and fail until implementation catches up.
- Implementation tasks that touch `processor/analyze.py` are sequential (same file); tasks in separate files are marked [P].
- Each story's final task is a run-the-suite validation gate.

### Parallel Opportunities

- **Setup phase**: T002, T003 in parallel.
- **Foundational phase**: T006 and T007 in parallel after T004 and T005 are in place; T004 and T005 must run first-T004-then-T005 (T005 relies on the revised gitignore).
- **US1 tests**: T008, T009, T010 in parallel (separate test files).
- **US1 implementation**: T011–T018 are all same-file edits to `processor/analyze.py`, so they run sequentially. T019 (smoke run) is the final gate.
- **US2**: T020 (its own test file) can be written in parallel with T021 (a separate tool script).
- **US3**: T024 and T025 edit the same file sequentially; T026 depends on them both.
- **Polish**: T027 and T028 are fully independent.

---

## Parallel Example: User Story 1 Tests

```bash
# These three test files are fully independent — launch together:
Task: "Create processor/tests/test_cli.py covering analyzer CLI behavior (T008)"
Task: "Create processor/tests/test_output_shape.py covering output-shape invariants (T009)"
Task: "Create processor/tests/test_fixture_facts.py covering fixture-specific facts (T010)"
```

## Parallel Example: Foundational

```bash
# After T004 (gitignore) and T005 (fixture regeneration) land,
# T006 (mapping stub) and T007 (conftest.py) are independent:
Task: "Create processor/entity_names.json containing {} (T006)"
Task: "Create processor/tests/conftest.py with fixture loaders (T007)"
```

---

## Implementation Strategy

### MVP First (Phases 1 + 2 + 3 = User Story 1)

1. Complete Phase 1: Setup — directories and `pyproject.toml`.
2. Complete Phase 2: Foundational — gitignore fix, parser-output fixtures generated and committed, empty mapping, conftest.
3. Complete Phase 3: User Story 1 — tests first (T008–T010), then analyze.py built up in T011–T018, then T019 smoke-and-validate.
4. **STOP and VALIDATE**: `python processor/analyze.py sample_replays/base_1.w3g.json` exits 0, file is written, tests pass. The analyzer is now a structurally-complete visualizer feed; names are placeholders.

### Incremental Delivery

1. MVP → ship. Visualizer work can begin against the placeholder-named analysis output.
2. Add US2 → re-ship with human-readable names. Visualizer sees display strings everywhere.
3. Add US3 → ship with documentation. Downstream developers can build against the contract without reading analyzer source.
4. Polish → finalize, measure SC-001, sanity-check quickstart.

### Parallel Team Strategy

With multiple developers:

1. Complete Setup + Foundational together.
2. Developer A picks up US1 (`processor/analyze.py` + its tests). Developer B can begin US2's extraction script (T021) and tests (T020) against the placeholder mapping the moment Foundational finishes — they need T020's fixture-coverage assertion to pass against the real mapping produced by T022, which requires US1 merged. A three-way split is possible but US3 is naturally the last write.

---

## Notes

- [P] tasks = different files, no dependencies on in-progress work.
- [Story] label maps tasks to the user story they serve (see spec.md §User Scenarios & Testing).
- Every task is scoped for immediate execution by one implementer.
- Fixture-based tests are the testing convention (Principle IV). Do NOT introduce mocks for `w3gjs` output, synthetic parser-output dicts, or hand-rolled JSON fragments; always load the committed fixtures.
- Cross-layer: the Processor layer MUST NOT import Node, run `w3gjs`, or shell out to `node` at analyzer runtime. T021's extraction script DOES invoke `node` — that is acceptable because it runs at tooling time, not analyzer runtime, and its output (`entity_names.json`) is the committed artifact, not a runtime dependency.
- Commit after each phase checkpoint so the branch history matches the MVP → increment narrative.
