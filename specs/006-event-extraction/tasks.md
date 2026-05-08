---

description: "Task list for feature 006: Narrative Event Extraction"
---

# Tasks: Narrative Event Extraction

**Input**: Design documents from `/specs/006-event-extraction/`
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`

**Tests**: Tests are required. The project's constitution (Principle IV)
mandates fixture-based pytest coverage for all parser/processor changes,
and `plan.md §Project Structure` lists the test files this feature
adds. Tests are written and exercised against the two committed
fixture replays — never mocked.

**Organization**: Tasks are grouped by user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Maps to user stories from `spec.md` (US1, US2, US3, US4)
- File paths are absolute repository-relative paths

## Path Conventions

This is a **CLI tool** under the existing Processor layer. All Python
sources live under `processor/`; tests under `processor/tests/`;
fixtures under `sample_replays/`; documentation alongside the source
(`processor/DATA.md`, new `processor/EVENTS.md`).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add the two new runtime dependencies justified in the
plan's Library Justification gate.

- [X] T001 Add `pandas>=2.0,<3.0` and `scikit-learn>=1.5,<2.0` to runtime dependencies in `processor/pyproject.toml`. Keep `pytest` in `[project.optional-dependencies].dev`. Bump `version` from `0.1.0` to `0.2.0` (the analyzer's contract changes additively in this feature, and the new entry point ships).
- [X] T002 Run `pip install -e processor[dev]` from repo root. Confirm `pandas` and `scikit-learn` resolve and `pytest` still works against the existing test suite.

---

## Phase 2: Foundational (Baseline)

**Purpose**: Capture pre-change baseline so byte-additivity (FR-004 / SC-005) and existing-test-pass (Principle IV) can be verified.

- [X] T003 Run `python -m pytest processor/tests -v` and confirm the entire feature 002 suite passes against `main` before any code changes. Record the test count as the baseline that Phase 3 must preserve. **Baseline: 67 tests pass.**
- [X] T004 Save a copy of the pre-change analyzer outputs to `/tmp/`: `cp sample_replays/base_1.w3g.analysis.json /tmp/base_1.pre006.json` and the same for `base_2`. These pre-change copies are the byte-additivity reference for T013.

**Checkpoint**: Baseline captured. Implementation can begin.

---

## Phase 3: User Story 2 — Action Coordinates Survive The Analyzer Layer (Priority: P1)

**Goal**: Extend `processor/analyze.py` to retain the `(x, y)` coordinate of every replay action that carried a position. Strictly additive on the existing analyzer-output contract.

**Independent Test**: Re-run the analyzer on each fixture; assert `players[].actions.timedActions[]` entries with `category` ∈ {`rightclick`, `ability`, `buildtrain`, `item`} carry `x`/`y`; entries with `category` ∈ {`assigngroup`, `selecthotkey`, `select`, `esc`, `subgroup`, `removeunit`} do not. Assert every pre-existing field is byte-identical to `/tmp/base_*.pre006.json` (after stripping the new `x`/`y` keys). Existing visualizer (feature 005) continues to function unchanged when fed the new output.

**Why P1**: US1 cannot be implemented at all until coordinates flow through the analyzer. This is the hard precondition.

### Implementation for User Story 2

- [X] T005 [US2] In `processor/analyze.py`, extend `_extract_timed_actions()` (around the per-action loop in `_classify_action`) to read `position.x`/`position.y` from w3gjs action ids `0x11`/`0x12`/`0x13`/`0x14` per `research.md §R1`. Append `x` and `y` to the emitted dict only when present in the source action. Do not emit null sentinels for coord-less actions.
- [X] T006 [US2] In `processor/analyze.py`, extend `_build_production()` to forward `x`/`y` from the underlying parser-output entry's `position` field to each `order[]` entry. Apply the same "only when present" rule. Building placements will gain coordinates; train/research/item-use entries typically will not.
- [X] T007 [P] [US2] Update `processor/DATA.md` `§players.actions` and `§players.production` tables to document the new optional `x` and `y` fields. Cite `research.md §R1` for the action-id table and the unit (signed integers in WC3 map units, untransformed).

### Tests for User Story 2

- [X] T008 [P] [US2] Add `processor/tests/test_coord_retention.py`. For each fixture, assert: (a) at least one `timedActions[]` entry per coord-bearing category (`rightclick`, `ability`, `buildtrain`, `item`) has both `x` and `y` integer fields, (b) no `timedActions[]` entry of category `assigngroup`/`selecthotkey`/`select`/`esc`/`subgroup`/`removeunit` carries `x` or `y`, (c) at least one `production.buildings.order[]` entry has `x`/`y`, (d) the coord values are within the range of all coord-bearing actions in the same replay (sanity bound on map units).
- [X] T009 [P] [US2] Update `processor/tests/test_output_shape.py` with a byte-additivity assertion: load each fixture, walk it with `jq`-style traversal removing only `x` and `y` keys, and assert the result equals the pre-change copy from `/tmp/base_*.pre006.json` (T004). This nails SC-005.
- [X] T010 [P] [US2] Update `processor/tests/test_timed_actions.py`: extend the existing per-category invariant to assert that the *count* of coord-bearing entries within each coord-bearing category equals the count of underlying parser-output actions whose w3gjs id was in `{0x11, 0x12, 0x13, 0x14}` and whose classified category matched. Both numbers come from the same parser-event stream — this is a drift detector.

### Re-emit fixtures

- [X] T011 [US2] Re-run `python processor/analyze.py sample_replays/base_1.w3g.json` and the same for `base_2`. The committed `*.analysis.json` fixtures are now post-006.
- [X] T012 [US2] Run `python -m pytest processor/tests -v`. Confirm: feature 002 baseline tests still pass (every assertion that was green in T003 is still green), and the three new/updated US2 test files pass.
- [X] T013 [US2] Run the byte-additivity check from T009 by hand once: `jq 'walk(if type == "object" then del(.x, .y) else . end)' sample_replays/base_1.w3g.analysis.json > /tmp/post006-stripped.json && diff /tmp/base_1.pre006.json /tmp/post006-stripped.json`. Expected: empty diff.

**Checkpoint**: US2 complete. Analyzer output now carries coordinates; the visualizer (feature 005) and every previously-passing test continue to work. SC-005 satisfied.

---

## Phase 4: User Story 1 — A Replay Becomes A Narrative-Ready Event Stream (Priority: P1)

**Goal**: Implement `processor/extract_events.py` — a new Processor-layer CLI that reads the post-006 analyzer-output and emits a per-replay events JSON document containing all 13 recognized event kinds, a stable content-derived id per event, a top-level `diagnostics` block mirroring the analyzer's pattern, and match-level metadata.

**Independent Test**: Run `python processor/extract_events.py sample_replays/base_1.w3g.analysis.json` → assert a `*.events.json` is written, parses as JSON, has exactly the three top-level keys `match`/`events`/`diagnostics`, contains at least one event of every kind that base_1 actually exhibits (creeping, expo, joint engagement, idle, etc.), every event has a 16-hex-char `id`, every inferred-kind event has its `inferenceLabel` set, and re-running yields a byte-identical document.

**Why P1**: This is the entire deliverable of the feature. Depends on US2 having shipped.

### CLI scaffolding (Phase 4a)

- [ ] T014 [US1] Create `processor/extract_events.py` with: docstring citing `contracts/extract-events-cli.md` and `processor/EVENTS.md`, `argparse` accepting one positional argument, `_err()` and `_warn()` helpers identical in shape to `analyze.py`'s, exit-code semantics (0/1/2) from the contract, output-path derivation per `contracts/extract-events-cli.md §Output`, and a `main()` that exits 0 on a no-op stub. No event detection yet.
- [ ] T015 [US1] In `processor/extract_events.py`, implement input validation: load the analyzer-output JSON, assert its top-level keys match the post-006 contract (`match`, `players`, `chat`, `diagnostics`, `settings`, `map`, `observers`), assert at least one `players[].actions.timedActions[]` entry has `x`/`y` (or that the replay has zero coord-bearing actions in total — degenerate disconnect), and exit non-zero with a clear `[extract_events] error: ...` diagnostic if not. Match the `_err()` convention.
- [ ] T016 [US1] In `processor/extract_events.py`, implement atomic-write output: write to a temp file in the same directory as the output path, then `os.replace()` on success; remove the temp file on any error. Mirrors `analyze.py`'s pattern.

### DataFrame loader and per-replay derived values (Phase 4b)

- [ ] T017 [US1] In `processor/extract_events.py`, implement `_load_actions_dataframe(analysis: dict) -> pd.DataFrame`: produces a DataFrame with columns `(timeMs, playerId, teamId, x, y, category, entityId)` for every coord-bearing timed-action entry across all players. Non-coord-bearing actions are excluded (they are not spatial). Build a lookup from `playerId` to `teamId` from `analysis.players[]`.
- [ ] T018 [US1] In `processor/extract_events.py`, implement `_compute_map_active_region(df)` per `data-model.md §Per-replay derived values`: returns `(min_x, max_x, min_y, max_y, diagonal)`. The diagonal is `sqrt((max_x-min_x)**2 + (max_y-min_y)**2)`.
- [ ] T019 [US1] In `processor/extract_events.py`, implement `_derive_player_homes(analysis, df)` per `research.md §R2`: for each player, centroid of building placements in the first 120 s; record `homeDerivation = "primary"` or `"fallback:firstActions"` per the fallback rule. Returns `dict[playerId → (home, derivationLabel)]`.
- [ ] T020 [US1] In `processor/extract_events.py`, implement `_derive_player_home_radii(analysis, df, homes, map_diagonal)` per `research.md §R3`: for each player, `max(distance from home to first-180s building placements)` floored to `0.10 × map_diagonal`. Records `homeRadiusDerivation`.
- [ ] T021 [US1] In `processor/extract_events.py`, implement `_engagement_radius(map_diagonal)` and `_engagement_scale(map_diagonal, time_window_seconds=5)` per `research.md §R4`. Trivial one-liners; document the constants inline.

### Stable event id and emission helpers (Phase 4c)

- [ ] T022 [US1] In `processor/extract_events.py`, implement `_event_id(kind, start_time_ms, participants, disambiguator="")` per `research.md §R11`: `sha256("|".join(...)).hexdigest()[:16]`. Also implement an `_emit(events, kind, start_time_ms, participants, disambiguator, **fields)` helper that constructs the dict, computes the id, and appends.

### Event-kind detectors (Phase 4d)

The 13 detectors all live in `processor/extract_events.py` and operate on the loaded analysis dict and DataFrame. They are listed in the order of FR numbering and implementation order; each touches the same file so they are sequential, not parallel.

- [ ] T023 [US1] Implement `_detect_idle_periods(analysis, idle_min_gap_ms=15000) -> list[Event]` per FR-010 / `data-model.md §idlePeriod` / `research.md §R5`. Uses raw timed-action timestamps from `analysis.players[].actions.timedActions[]` (not the DataFrame, since this is non-spatial). Emits an event for every gap ≥ 15 s in a player's stream.
- [ ] T024 [US1] Implement `_detect_building_rebuilds(analysis, map_diagonal) -> list[Event]` per FR-011 / `data-model.md §buildingRebuild` / `research.md` (rebuild-bucket sized at `0.01 × map_diagonal`). Group `production.buildings.order` by `(playerId, entityId, round(x/bucket), round(y/bucket))`; entries with ≥ 2 placements and a gap ≥ 60 s become rebuild events.
- [ ] T025 [US1] Implement `_detect_tech_milestones(analysis) -> list[Event]` per FR-012 / `research.md §R8`. The catalog is hardcoded as a constant dict at the top of the module (cleaner than name-filtering at runtime; the catalog is small and stable).
- [ ] T026 [US1] Implement `_detect_expo_placements(analysis, homes, home_radii) -> list[Event]` per FR-013. Filter `production.buildings.order` for main-hall ids; the *first* hall placement per player is the starting hall (skip it); subsequent halls beyond `home_radius` from the player's home are expos.
- [ ] T027 [US1] Implement `_detect_creeping_departures(analysis, df, homes, home_radii, min_duration_ms=20000) -> list[Event]` per FR-014. For each player, compute a 10 s rolling centroid of their coord-bearing actions; detect transitions from inside the home circle to outside it that persist for ≥ `min_duration_ms`. Emit an event with the destination centroid and action count. Use pandas `rolling()` on a per-player time-indexed series.
- [ ] T028 [US1] Implement `_detect_tower_rush_candidates(analysis, homes) -> list[Event]` per FR-015 / `research.md §R7`. Filter `production.buildings.order` for tower entity ids; for each tower placement, compute distance to placer's home and to each opponent's home; emit when min-opponent-distance < own-home-distance.
- [ ] T029 [US1] Implement `_detect_base_incursions(df, homes, home_radii) -> list[Event]` per FR-016. For each player, find runs of their actions whose `(x, y)` is inside an opponent's home circle; collapse runs into single events per opponent per visit (gap > 30 s splits a run).
- [ ] T030 [US1] Implement `_detect_ally_zone_creeping(df, homes, home_radii, min_action_count=10) -> list[Event]` per FR-017. For each player, find runs of actions inside an ally's home-radius band (between `home_radius` and `2 × home_radius` of the ally) but outside the player's own band, with action density ≥ `min_action_count`.
- [ ] T031 [US1] Implement `_detect_joint_engagements(df, map_diagonal, time_window_seconds=5, min_samples=4) -> list[Event]` per FR-018 / `research.md §R4`. Apply `sklearn.cluster.DBSCAN` with `eps=0.05*map_diagonal` to the 3-D points `(x, y, t * scale)` per the research scale. Filter clusters to those with ≥ 2 distinct teammate `playerId`s. Emit one event per qualifying cluster with centroid, participants, action count, per-participant breakdown, and tightness.
- [ ] T032 [US1] Implement `_detect_hero_teleports(analysis) -> list[Event]` per FR-019 / `research.md §R9`. The TP item-id catalog is a hardcoded constant. Walk `production.items.order` (item-use entries) for matches; attribute the hero from the player's `heroes[]` only when unambiguous (record `attributionNote` otherwise).
- [ ] T033 [US1] Implement `_detect_production_stalls(analysis, stall_min_gap_ms=45000) -> list[Event]` per FR-020. For each player, find spans where `production.{buildings,units,upgrades,items}.order` had no entries for ≥ 45 s while `timedActions[]` was non-empty in the same span. Compute the player's input rate (actions per minute) over the span.
- [ ] T034 [US1] Implement `_detect_intensity_peaks(analysis) -> list[Event]` per FR-021 / `research.md §R10`. Build a per-second action timeseries via `pandas.Series.rolling(window='30s').sum()`; find local maxima within ±15 s neighborhoods that exceed `mean + 2*std`. Emit one event per peak. Compute both the all-player and per-team variants.
- [ ] T035 [US1] Implement `_detect_resource_transfers(analysis, burst_gap_ms=30000) -> list[Event]` per FR-022 / `research.md §R6`. Walk `players[].resourceTransfers` (also visible from the receiver side via `players[].resourceTransfers`); group by `(senderId, receiverId)` and merge consecutive transfers with `<= burst_gap_ms` between them. Emit one event per merged group with totals.

### Document assembly (Phase 4e)

- [ ] T036 [US1] In `processor/extract_events.py`, implement `_build_match_block(analysis)` per `data-model.md §match` and `_build_diagnostics_block(...)` per `data-model.md §diagnostics`. The diagnostics block records: `extractorVersion` (read from `processor/pyproject.toml` per the analyzer's existing pattern), `parserId` (forwarded from analyzer's `diagnostics.parserId`), `players` (per-player home derivation methods), `thresholds` (per-replay values used), `eventCounts` (kind → integer).
- [ ] T037 [US1] In `processor/extract_events.py`, implement the `main()` flow: validate input → load DataFrame → compute homes/radii/engagement-radius/map-region → run all 13 detectors → concatenate the event lists → sort by `(startTimeMs, kind, sortedParticipantIds)` → assign stable ids via T022 → assemble document → atomic-write per T016.

### Tests for User Story 1

- [ ] T038 [P] [US1] Add `processor/tests/test_events_cli.py`: argparse usage error → exit 2; missing input file → exit 1 with `[extract_events] error:` line; pre-006 analyzer output (synthesized by stripping `x`/`y` from a fixture) → exit 1 with the missing-coord diagnostic; happy path on `base_1.w3g.analysis.json` → exit 0, `*.events.json` written.
- [ ] T039 [P] [US1] Add `processor/tests/test_events_shape.py`: top-level keys exactly `{match, events, diagnostics}`; every event has `id`/`kind`/`startTimeMs`/`participants`/`inferenceLabel`/`thresholds`; every `id` matches `^[0-9a-f]{16}$`; events array is sorted by `startTimeMs` ascending; `diagnostics.eventCounts` sums to `len(events)`.
- [ ] T040 [P] [US1] Add `processor/tests/test_events_kinds.py`: per-fixture, per-kind assertions. For each kind that `base_1` actually exhibits (we list the expected presence/absence per fixture in the test file's docstring, derived from manual inspection), at least one event of that kind is emitted; for kinds that did not occur, the count is exactly 0 (no fabrication, SC-002). Apply the same to `base_2` with its own expected presence list.
- [ ] T041 [P] [US1] Add `processor/tests/test_events_helpers.py`: pure-function unit tests for `_event_id` (idempotent, kind-disambiguated, length-16-hex), `_compute_map_active_region` (small DataFrame inputs), `_derive_player_homes` and `_derive_player_home_radii` (primary path and fallback path), the rebuild-bucket grouping, and the resource-transfer-burst grouping. Inputs are derived from the fixtures' analyzer output, never hand-rolled (Principle IV).
- [ ] T042 [P] [US1] Add `processor/tests/test_events_determinism.py`: run the extractor twice on each fixture and assert byte-identical output (SC-006).

### Commit fixture event documents

- [ ] T043 [US1] Run `python processor/extract_events.py sample_replays/base_1.w3g.analysis.json` and the same for `base_2`. Commit both `*.events.json` as fixtures alongside the analyzer outputs.

**Checkpoint**: US1 complete. Both fixtures have committed events documents. SC-001 (LLM narrative) is testable manually; SC-002 (no fabrication) and SC-006 (determinism) pass automatically.

---

## Phase 5: User Story 3 — The Events Document Is Self-Describing (Priority: P2)

**Goal**: A developer can describe how to render or narrate every kind without opening source code.

**Independent Test**: Hand `processor/EVENTS.md` to a developer who has never seen the extractor's output. Ask them to describe how they'd render a `jointEngagement` event in a visualizer panel and how they'd phrase a `towerRushCandidate` in a natural-language summary. They answer correctly without consulting source.

### Implementation for User Story 3

- [ ] T044 [US3] Create `processor/EVENTS.md` mirroring `specs/006-event-extraction/contracts/events-output-shape.md` (the on-disk reference is the contract; the in-tree doc is the operative reference per FR-029). Include: the top-level shape, full `match` table, full `events`-array common-fields table, all 13 per-kind field tables, full `diagnostics` table, the deterministic-secondary-key rule, and the stable-id derivation per `research.md §R11`.
- [ ] T045 [US3] In `processor/EVENTS.md`, add a "Limitations and hedging" section per FR-031: explicit prose stating that the extractor does not observe unit deaths, gold, lumber, food, vision, or build completion. List which kinds depend on inferring around those gaps (the five kinds with non-null `inferenceLabel`: `towerRushCandidate`, `baseIncursion`, `allyZoneCreeping`, `jointEngagement`, `intensityPeak`). Cross-reference each kind to its FR number.
- [ ] T046 [US3] In `processor/EVENTS.md`, add the catalog appendices: tower entity-id list (per `research.md §R7`), tech-milestone entity-id list (per `research.md §R8`), and hero-TP item-id list (per `research.md §R9`). Each entry shows `id` → `name` and the source race.
- [ ] T047 [US3] In `processor/EVENTS.md`, add a "Version evolution" section per `contracts/events-output-shape.md §Version evolution`: which changes are additive (new kinds, new fields, new diagnostics keys) and which are breaking (kind removal, field removal, type changes — would warrant a `version` field).

**Checkpoint**: US3 complete. The events doc is self-describing.

---

## Phase 6: User Story 4 — Every Inferred Claim Is Hedged Honestly (Priority: P2)

**Goal**: Automated enforcement that no event overstates what the data supports. The hedging discipline (FR-022..FR-025, SC-008) is enforced by tests, not by code structure.

**Independent Test**: Run `pytest processor/tests/test_events_hedging.py -v`. All assertions pass on both fixtures.

### Tests for User Story 4

- [ ] T048 [P] [US4] Add `processor/tests/test_events_hedging.py`. (a) For each fixture's events doc, assert every event of an inferred kind (`towerRushCandidate`, `baseIncursion`, `allyZoneCreeping`, `jointEngagement`, `intensityPeak`) has `inferenceLabel` set to the documented label per `data-model.md` (FR-023). (b) For each event of a factual kind, assert `inferenceLabel is None` (FR-023). (c) Walk the entire events document as a string and assert that the forbidden outcome tokens (`killed`, `destroyed`, `stole`, `won`) do NOT appear anywhere (SC-008). Tokens are case-insensitive, whole-word matched.
- [ ] T049 [P] [US4] Add `processor/tests/test_events_thresholds.py`. For each event whose kind has a `thresholds` field per `data-model.md`, assert the `thresholds` object on the emitted event contains every documented key for that kind, with non-null values (FR-024). For each kind, assert at least one emitted event has the threshold value matching the per-replay derivation result from `diagnostics.thresholds` (cross-document consistency check).

**Checkpoint**: US4 complete. SC-008 (forbidden vocabulary) and SC-003 (auditability) pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T050 [P] Run `quickstart.md` Step 1 by hand: jq-spot-check the new coord fields on a rightclick action and on a building placement; jq-spot-check the *absence* of coord fields on a hotkey assignment. Both fixtures.
- [ ] T051 [P] Run `quickstart.md` Step 2 by hand: confirm `*.events.json` written, `keys` returns `["diagnostics", "events", "match"]`, `eventCounts` reports a value for every kind. Both fixtures.
- [ ] T052 Run `quickstart.md` Step 3: full `pytest processor/tests` from a clean checkout; confirm 100% pass.
- [ ] T053 Manual SC-001 LLM-narrative smoke test on `sample_replays/base_1.w3g.events.json`: prompt an LLM with the events document and ask for a 6-10 sentence summary. Verify the summary names ≥ 1 expo, ≥ 1 creeping departure, ≥ 1 joint engagement, ≥ 1 idle period, with event-id citations. Record the result in the PR description.
- [ ] T054 Cross-reference `processor/DATA.md` from `processor/EVENTS.md` and vice versa, so a developer landing on either file finds the other within one hop.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)** — no dependencies. Add deps; install.
- **Foundational (Phase 2)** — depends on Setup. Establishes baseline.
- **User Story 2 (Phase 3)** — depends on Foundational. **Hard-blocks US1** because the events extractor reads coordinates the analyzer must now retain.
- **User Story 1 (Phase 4)** — depends on **US2 completion** (T013 specifically). Cannot start until coord retention is shipped and tested.
- **User Story 3 (Phase 5)** — depends on US1 completion. The doc describes what the extractor emits; the extractor must exist first.
- **User Story 4 (Phase 6)** — depends on US1 completion. Tests audit emitted events.
- **Polish (Phase 7)** — depends on everything above.

### Story Dependency Graph

```text
US2 (P1) ──► US1 (P1) ──► US3 (P2)
                      └─► US4 (P2)
                                ├─► Polish
                                └─► Polish
```

US3 and US4 are independent of each other once US1 lands; they can be worked on in parallel by different contributors.

### Within Phase 3 (US2)

- T005 → T006 (same file, sequential).
- T007, T008, T009, T010 (different files) can run in parallel after T005 + T006.
- T011 depends on T005 + T006.
- T012 depends on T005 + T006 + T007 + T008 + T009 + T010 + T011.
- T013 depends on T011.

### Within Phase 4 (US1)

- T014 → T015 → T016 (CLI scaffolding, same file, sequential).
- T017 → T018 → T019 → T020 → T021 (DataFrame + derived values, same file, sequential).
- T022 (id helper, same file, sequential after T021).
- T023..T035 (all 13 detectors, same file, **sequential** — they all touch `extract_events.py`).
- T036 → T037 (assembly, same file, sequential).
- T038, T039, T040, T041, T042 (test files, different files) can run in parallel after T037.
- T043 depends on T037.

### Within Phase 5 (US3)

- T044, T045, T046, T047 all touch `processor/EVENTS.md` — sequential.

### Within Phase 6 (US4)

- T048 and T049 touch different test files — can run in parallel.

### Within Phase 7 (Polish)

- T050, T051 touch nothing in source — can run in parallel.
- T052, T053, T054 depend on all prior phases.

---

## Parallel Examples

### Phase 3 (US2): test files in parallel

```bash
# After T005 and T006 land in processor/analyze.py, the three test edits run in parallel:
Task: "Add processor/tests/test_coord_retention.py"      # T008
Task: "Update processor/tests/test_output_shape.py"      # T009
Task: "Update processor/tests/test_timed_actions.py"     # T010
# Plus the doc update:
Task: "Update processor/DATA.md"                          # T007
```

### Phase 4 (US1): test files in parallel

```bash
# After T037 lands the assembled main flow, all five test files run in parallel:
Task: "Add processor/tests/test_events_cli.py"           # T038
Task: "Add processor/tests/test_events_shape.py"         # T039
Task: "Add processor/tests/test_events_kinds.py"         # T040
Task: "Add processor/tests/test_events_helpers.py"       # T041
Task: "Add processor/tests/test_events_determinism.py"   # T042
```

### Phase 6 (US4): hedging tests in parallel

```bash
Task: "Add processor/tests/test_events_hedging.py"       # T048
Task: "Add processor/tests/test_events_thresholds.py"    # T049
```

---

## Implementation Strategy

### MVP scope: US2 + US1

**US2 alone is not the MVP.** It ships a contract change that no consumer uses yet. The MVP is US2 + US1 together: the events document exists for both fixtures and can be handed to an LLM. Stop at the end of Phase 4 (T043) and validate: SC-001 (LLM narrative quality), SC-002 (no fabrication), SC-005 (analyzer byte-additivity), SC-006 (events determinism).

### Incremental delivery

1. Phase 1 + Phase 2 — environment ready.
2. Phase 3 — analyzer extension shipped (PR 1: small, atomic, low risk).
3. Phase 4 — events extractor shipped (PR 2: large, the deliverable).
4. Phase 5 + Phase 6 — documentation and hedging audit (PR 3: quality bar; can split into two PRs if reviewer prefers).
5. Phase 7 — polish (small commits or rolled into PR 3).

The **PR seam** is between Phase 3 and Phase 4. Shipping Phase 3 first is low-risk (it's strictly additive; visualizer is unaffected) and lets the team review the analyzer's coord-retention change in isolation before the much larger events-stage diff lands.

### Single-developer order

1. Phase 1 (T001-T002) — 30 minutes.
2. Phase 2 (T003-T004) — 5 minutes; baseline capture.
3. Phase 3 (T005-T013) — half a day; PR 1.
4. Phase 4 — 2-3 days, the bulk of the work; PR 2.
   - 4a CLI scaffolding (T014-T016) — 1-2 hours.
   - 4b DataFrame + derived values (T017-T021) — 2-3 hours.
   - 4c Stable id helper (T022) — 30 minutes.
   - 4d Detectors (T023-T035) — 1-2 days; the 13 detectors are the main implementation effort.
   - 4e Assembly (T036-T037) — 1 hour.
   - Tests (T038-T042) — half a day.
   - Fixture commit (T043) — 5 minutes.
5. Phase 5 (T044-T047) — 2-3 hours; PR 3 part 1.
6. Phase 6 (T048-T049) — 1 hour; PR 3 part 2.
7. Phase 7 (T050-T054) — 1 hour.

**Total estimate**: ~4-5 working days for one developer.

---

## Notes

- [P] tasks = different files, no dependencies on incomplete work.
- The 13 detectors in Phase 4d are sequential because they all live in `processor/extract_events.py` (Principle III: one file, no shared base class). They are *logically* independent — detector ordering inside the file is by FR number for readability.
- Constitution Principle IV: every test derives its inputs from the two committed fixture replays. No mocks, no hand-rolled action streams.
- Constitution Principle VI: pandas and scikit-learn are introduced in T001 with their justification recorded in `plan.md §Library Justification gate`.
- Commit cadence: one commit per task for the small ones, one commit per logical group (e.g., the whole Phase 4d block of 13 detectors) for the larger ones.
