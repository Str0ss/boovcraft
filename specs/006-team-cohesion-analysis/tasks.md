---
description: "Tasks for feature 006: Team Cohesion Analysis (Spatial, Support, Economic, Tactical)"
---

# Tasks: Team Cohesion Analysis (Spatial, Support, Economic, Tactical)

**Input**: Design documents from `/specs/006-team-cohesion-analysis/`
**Prerequisites**: plan.md, spec.md, data-model.md, contracts/output-shape.md (research.md and quickstart.md will be authored alongside Phase 0 / Phase 6 respectively)

**Tests**: This feature is **fixture-based pytest-first** for the Processor side and **Vitest pure-logic** for the new Visualizer helpers. Each functional requirement FR-001 through FR-024 maps to at least one named pytest case (SC-004 minimum 24). Each invariant from `contracts/output-shape.md` maps to at least one test as well — the test-coverage map at the end of this file enumerates the bidirectional mapping. Visual correctness on the Team tab is a manual `quickstart.md` walkthrough on both committed fixtures, mirroring the feature 003–005 stance.

**Organization**: Tasks are grouped by user story / phase to enable independent shipping and testing. Per `plan.md`, this feature ships as one big-bang feature 006 (per the user's decision); within the feature, work is staged across seven phases.

## Format: `[ID] [P?] [Story/Phase] Description`

- **[P]**: Can run in parallel — different files, no incomplete-task dependencies.
- **[Story]**: Which user story / phase this task belongs to (e.g., US1, US2, P1a for Phase 1a foundation work).
- File paths are project-relative paths from repo root.

## Path Conventions

- **Processor source**: `processor/` (existing `analyze.py` + new `processor/team/` package).
- **Processor tests**: `processor/tests/` (existing 67 cases stay, ≥24 new cases are additive).
- **Lookup tables**: `processor/{auras,item_attributes,unit_costs,rescue_items}.json` co-located with `entity_names.json`.
- **Lookup-table regenerators**: `processor/tools/build_*.py`.
- **Visualizer source**: `visualizer/src/` — extending the feature 005 React app, not replacing it.
- **Visualizer tests**: `visualizer/tests/` (existing 35 cases stay, new pure-logic cases are additive).
- **Fixtures**: `sample_replays/base_*.w3g.json` and the regenerable `sample_replays/base_*.w3g.analysis.json` — same files features 002–005 used.
- **Parser**: NOT touched in this feature (Principle II).

---

## Phase 0: Setup, probes, and committed lookup tables

**Purpose**: Lay the data foundation before any code that depends on it is written. Phase 0 produces four committed JSON tables, three regenerator scripts, and a documented Phase-0 probe outcome that gates the cooperative-spell-cast metric (FR-029 candidate).

**Why first**: Every later phase reads at least one of these tables. The `0x14` probe gates US2's stretch goal; if it fails, the affected code paths are dropped from later phases without rework.

- [ ] T001 [P0] Create the empty `processor/team/` package: `processor/team/__init__.py` (empty), and a `processor/team/events.py` containing only the action-id constants (`ACT_NO_TARGET = 0x10`, `ACT_TARGET_POSITION = 0x11`, `ACT_TARGET_POSITION_AND_UNIT = 0x12`, `ACT_GIVE_ITEM = 0x13`, `ACT_TWO_TARGETS = 0x14`, `ACT_SELECTION = 0x16`, `ACT_HOTKEY_GROUP = 0x17`, `ACT_TRANSFER_RESOURCES = 0x51`, `ACT_MINIMAP_SIGNAL = 0x68`) plus a single helper `iter_command_actions(parser_output)` yielding `(time_ms, player_id, action_dict)` tuples in chronological order. No business logic yet.
- [ ] T002 [P] [P0] Implement `processor/tools/build_auras.py` — extracts aura ability ids and radii from `parser/node_modules/w3gjs/dist/lib/mappings.js` (Phase-0 probe will confirm the import path). Writes `processor/auras.json` matching the `data-model.md` § AurasTable shape. Initial coverage: Devotion (`AHad`), Brilliance (`AHab`), Endurance (`AEar`), Trueshot (`AEar`-confirm), Unholy (`AUau`), Vampiric (`AUav`), Command (`AOcr`). All `radius: 900` per `plan.md` Heuristic decisions § Aura table.
- [ ] T003 [P] [P0] Commit the generated `processor/auras.json`. Verify it round-trips: `python3 processor/tools/build_auras.py --check` exits 0.
- [ ] T004 [P] [P0] Implement `processor/tools/build_item_attributes.py` — extracts items from `entity_names.json` filtered to ladder-shop ids; assigns `primary` from a small inline mapping (tomes by name, orbs by attribute, scrolls / staves as `universal`); flags rescue items (`isRescue: true` for `stwp`, `shea`, `stwl`, `rhe1`, `rhe2`, `phea`). Writes `processor/item_attributes.json`. Manual overrides allowed at top of the script.
- [ ] T005 [P] [P0] Commit the generated `processor/item_attributes.json` AND `processor/rescue_items.json` (derived array of ids where `isRescue === true`). Verify both regenerate consistently.
- [ ] T006 [P] [P0] Implement `processor/tools/build_unit_costs.py` — extracts gold / lumber / supply per unit-id from `w3gjs`'s unit-data tables. Writes `processor/unit_costs.json`. Initial coverage MUST include every unit / building / hero appearing in either committed fixture's `production.summary` (use a script-local validation pass that walks both fixtures' analysis-jsons and reports gaps).
- [ ] T007 [P] [P0] Commit `processor/unit_costs.json`. Verify gap-free coverage on `sample_replays/base_1.w3g.analysis.json` and `base_2.w3g.analysis.json`.
- [ ] T008 [P0] **`0x14` probe** — write `processor/tools/probe_spell_target.py`: walks both fixtures' `events[]` streams, dumps every distinct `(orderId1[0..3] resolved as ability id, owner, category, flags)` combination with a sample count. Manually inspect the output and decide: does the data permit distinguishing ally-target from self-target from enemy-target casts? Record decision in `research.md` (created in T009). If YES, T034 ships `team/support.py::detect_support_spell_casts`; if NO, T034 emits a single `cohesionMetricGaps` row and the FR-029 fallback applies.
- [ ] T009 [P0] Author `specs/006-team-cohesion-analysis/research.md` — captures the Phase-0 decisions: lookup-table sources, 0x14-probe outcome, the eight heuristic constants chosen in `plan.md`'s Heuristic-decisions section (all recorded with one-line rationale each), and the Princ. VI evaluation table (degenerate — no new external deps). Mirror the structure of `specs/005-react-timelines/research.md`.

**Checkpoint**: Four committed JSON tables sit in `processor/`. The 0x14-probe outcome is recorded in `research.md` and feeds T034. No business code is written yet.

---

## Phase 1a: Tier 2 foundation — handle ownership + position state machine

**Purpose**: Build the two state-machines that every subsequent spatial / cohesion metric reads from. After this phase, `processor/team/ownership.py` and `processor/team/positions.py` are pure event-stream walkers, fully tested, with no consumer wired up yet.

**⚠️ CRITICAL**: No spatial / cohesion / TEI work can begin until Phase 1a is green. This is the largest piece of new LOC in the feature (~400 LOC of state-machine logic) and the biggest correctness risk.

**Independent Test**: `cd processor && pytest tests/test_unit_ownership.py tests/test_position_tracking.py` is green against both committed fixtures. Ownership map covers ≥ 95% of selectable handles in `base_2`; position state has a non-null position for ≥ 95% of `0x12` action targets observed.

- [ ] T010 [P1a] Implement `processor/team/ownership.py::build_ownership_map(parser_output) -> dict[handle, OwnershipRow]`. Walks `0x16` and `0x17` events in chronological order. First selecting player owns the handle; subsequent selectors append to `coControlledBy`. Excludes neutral handles (slots 12, 15). Returns a frozen dict.
- [ ] T011 [P1a] Implement `processor/team/positions.py::PositionState` class — internal state map `{ handle: { owner, x, y, lastUpdatedMs, source } }`, plus `step(action_dict, time_ms, owning_player)` that updates per-handle position on `0x10` (build → handoff), `0x11`, `0x12`, `0x13`, `0x14`. Also tracks `ActiveSelection` per slot (updated on `0x16`/`0x17`). Pure class, no I/O.
- [ ] T012 [P1a] Implement `processor/team/positions.py::run_position_state(parser_output, ownership) -> PositionState` — orchestrates the full event-stream walk and returns the final state. The state object exposes `centroid_at(slot, lookback_ms_from, lookback_ms_to)` which Phase 1b uses.
- [ ] T013 [P1a] Write `processor/tests/test_unit_ownership.py` — fixture-driven assertions: every selection event in `base_2` produces a non-empty ownership entry; ownership is stable across re-runs (determinism); neutral handles excluded. **Covers FR-001 prerequisite.**
- [ ] T014 [P1a] Write `processor/tests/test_position_tracking.py` — fixture-driven: at least one `0x12` action per non-neutral player produces a `PositionState` update; worker→building handoff (`0x10` build orderId resolves to a known building id and the resulting building's handle gets a position) is observed at least once on `base_2`; `centroid_at` returns `None` when fewer than 1 handle has been updated in the lookback window.

**Checkpoint**: Phase 1a tests green on both fixtures. `tasks.md` Phase 1b can begin.

---

## Phase 1b: Battle windows + centroids + split engagement (US1)

**Goal**: Detect battle windows, compute per-player centroids at battle start, flag battles whose maximum allied centroid distance exceeds the active aura radius. After Phase 1b, the analyzer emits `team.battles[]` and `team.battles[i].splitEngagement` with deterministic, fixture-validated values — but the visualizer is not touched yet.

**Independent Test**: `cd processor && pytest tests/test_battle_windows.py tests/test_centroids.py tests/test_split_engagement.py tests/test_aura_lookup.py` is green; manual `jq` inspection of the regenerated `base_1.w3g.analysis.json` shows expected battle counts and at least one `splitEngagement.flagged === true` row that matches manual review of the replay.

### Implementation for US1

- [ ] T015 [US1] Implement `processor/team/battles.py::detect_battle_windows(parser_output, ownership) -> list[BattleWindow]` per `plan.md` § Heuristic decisions: 5-s buckets, run-length floor 3, gap tolerance 2; `engaged` bucket = ≥ 1 PvP attack action (`0x11`/`0x12`/`0x14` against an opposing-team unit per ownership map). Excludes creep aggro by ownership. Returns sorted list with stable indices.
- [ ] T016 [US1] Implement `processor/team/centroids.py::compute_centroids(battle, position_state) -> list[Centroid]` — for each player on either side, query `position_state.centroid_at(slot, battle.startMs - 60_000, battle.startMs)`. Falls back to single-most-recent if < 3 handles in window; returns `null` centroid with `source: "missing"` if no commands ever issued.
- [ ] T017 [US1] Implement `processor/team/centroids.py::compute_allied_distances(battle, centroids) -> list[AlliedDistance]` — pairwise Euclidean for each unordered allied pair on each side. `fromSlot < toSlot` canonicalization.
- [ ] T018 [US1] Implement `processor/team/centroids.py::active_aura_radius(battle, hero_summaries, auras_table) -> (radius, ability_id, name)` — picks the maximum-radius active *support* aura among heroes leveled up by the team in this battle window. Falls back to `(900, "default", "default 900u")` if none active.
- [ ] T019 [US1] Implement `processor/team/centroids.py::flag_split_engagement(battle, allied_distances, aura_radius_tuple) -> SplitEngagement` — flagged iff `max(allied_distances) > radius`; flaggedSlots = the pair achieving the max.
- [ ] T020 [US1] Wire Phase 1b into `processor/analyze.py` — under a feature flag or unconditionally: build ownership, run position state, detect battles, compute centroids + distances + split-engagement, populate `team.battles[]` and `team.applicable`. `team.applicable: false` empty-state branches when 1v1 / FFA / no battles detected.

### Tests for US1

- [ ] T021 [P] [US1] `processor/tests/test_battle_windows.py` — battle-window detection on both fixtures: `base_1` produces ≥ 1 battle window; `base_2` produces ≥ 1; bucket parameters are tunable (constants exposed at module top); creep-aggro events do not open windows. **Covers FR-001.**
- [ ] T022 [P] [US1] `processor/tests/test_centroids.py` — `Centroid.x === null ⇔ y === null ⇔ source === "missing"`; coordinates are finite when non-null; computed centroid is the arithmetic mean of position-state values for the active selection. **Covers FR-002, invariant 7.**
- [ ] T023 [P] [US1] `processor/tests/test_split_engagement.py` — biconditional: `flagged === true ⇔ flaggedSlots.length === 2 ⇔ distance > radius`; `flagged === false ⇔ flaggedSlots === []`. **Covers FR-005, invariant 9.**
- [ ] T024 [P] [US1] `processor/tests/test_aura_lookup.py` — when no support aura is active in a battle, `referenceAuraId === "default"` and the radius defaults to 900; when an active aura is found, `referenceAuraId` is a 4-char ability id resolvable via `auras.json`. **Covers FR-004, FR-006, invariant 10.**
- [ ] T025 [P] [US1] `processor/tests/test_team_applicability.py` — synthetic 1v1-stripped fixture (drop one ally from `base_2` in a transient pytest fixture) yields `team.applicable: false, reason: "noAllies"`; FFA-stripped (clear `fixedTeams`) yields `reason: "ffa"`; zero-battle stripped yields `reason: "noBattlesDetected"`. **Covers FR-026, invariants 1, 2, 7.**

**Checkpoint**: After Phase 1b, the JSON contract for `team.battles[]` is fully populated and tested. `team.itemTransfers[]`, `team.supportEvents[]`, etc. still empty / absent — those land in subsequent phases.

---

## Phase 2: Support events + resource cooperation (US2 + US3)

**Goal**: Item transfers (`0x13` give-item) with attribute-fit classification, missed-save detection, optional cooperative spell-cast detection (gated by Phase-0 probe), resource-transfer purpose hints, shared-control banner, generosity score. After Phase 2, the JSON has populated `team.itemTransfers[]`, `team.supportEvents[]`, `team.resourceCooperation`, `team.findings[]`, `team.sharedControl`.

**Independent Test**: `cd processor && pytest tests/test_item_transfers.py tests/test_recipient_fit_class.py tests/test_missed_saves.py tests/test_resource_purpose.py tests/test_shared_control.py tests/test_generosity.py` green on both fixtures. `team.itemTransfers.length === number of 0x13 events in events[]` (mirror invariant 16). `team.resourceCooperation.transfers.length === sum of players[].resourceTransfers.length` (mirror invariant 17).

### Implementation for US2

- [ ] T026 [P] [US2] Implement `processor/team/support.py::extract_item_transfers(parser_output, ownership, item_attributes, hero_summaries) -> list[ItemTransfer]` — walks `0x13` events; resolves giver / recipient via ownership; classifies `recipientFitClass` per the four-way matrix in `plan.md` § Item-give recipient fit class. Adds `diagnostics.itemAttributeGaps[]` rows for unmapped item ids or unmapped recipient hero attributes.
- [ ] T027 [P] [US2] Implement `processor/team/support.py::detect_missed_saves(parser_output, ownership, position_state, rescue_items, battles) -> list[SupportEvent]` — for each hero death (handle disappears from selections for ≥ 30 s after a battle window's start, AND owned by a non-neutral slot), scan all allies' inventories at that timestamp for any rescue item; if found AND `distance(holderHero.position, deceasedHero.position) ≤ 800`, emit `type: "missedSave"`.
- [ ] T028 [US2] **Conditional** on T008 / T009 outcome: implement `processor/team/support.py::detect_support_spell_casts(parser_output, ownership) -> list[SupportEvent]` if the 0x14 probe succeeded. Otherwise: emit a single `diagnostics.cohesionMetricGaps[]` row and skip emission entirely.

### Tests for US2

- [ ] T029 [P] [US2] `processor/tests/test_item_transfers.py` — mirror invariant: every `0x13` event in `events[]` produces exactly one `team.itemTransfers[]` entry with matching `timeMs`. **Covers FR-007, invariant 16.**
- [ ] T030 [P] [US2] `processor/tests/test_recipient_fit_class.py` — three branches against synthetic transfers (or fixture-found ones if any): `int → int = "good"`, `int → str = "wrong"`, `universal → any = "neutral"`, unmapped → `"unknown"` with a diagnostic entry. **Covers FR-009, invariant 18.**
- [ ] T031 [P] [US2] `processor/tests/test_missed_saves.py` — synthetic fixture (or a fixture-found case if either committed replay has one): hero death + ally with rescue item in inventory + within 800u → exactly one `"missedSave"` entry. Distance > 800 ⇒ no entry. Hero saving itself is impossible (`holderSlot !== deceasedSlot`). **Covers FR-010, invariants 19, 20.**

### Implementation for US3

- [ ] T032 [P] [US3] Implement `processor/team/resources.py::annotate_transfers(parser_output, players_analysis, durationMs) -> list[AnnotatedTransfer]` — mirrors `players[].resourceTransfers[]` 1:1 plus `purposeHint` per `plan.md` § Resource transfer purpose hint heuristic windows.
- [ ] T033 [P] [US3] Implement `processor/team/resources.py::compute_generosity(players_analysis, unit_costs) -> list[GenerosityRow]` — `estimatedMined{Gold,Lumber}` from `Σ unit_costs[id] × count` over each player's `production.summary`. `generosityPercent` is null iff either estimated value is null (one missing unit_cost poisons the ratio).
- [ ] T034 [US3] Wire US2+US3 into `processor/analyze.py`'s team-block builder — `team.itemTransfers`, `team.supportEvents`, `team.resourceCooperation`, `team.sharedControl`, `team.findings` are populated; `team.applicable === false` branches still emit nothing here.

### Tests for US3

- [ ] T035 [P] [US3] `processor/tests/test_resource_purpose.py` — synthetic transfer scenarios (constructed via fixture override): tier-up coincidence within ±60s → `"tierUpAssist"`; building loss within window → `"baseDefense"`; > 75% match → `"lateGameTopUp"`; otherwise → `"none"`. **Covers FR-012, invariant 21.**
- [ ] T036 [P] [US3] `processor/tests/test_shared_control.py` — `team.sharedControl.enabled` mirrors `settings.fullSharedUnitControl`; `team.findings` includes `"sharedControlDisabled"` iff `enabled === false`; otherwise `"sharedControlDisabled"` not present. **Covers FR-013, invariant 23.**
- [ ] T037 [P] [US3] `processor/tests/test_generosity.py` — null-coupling biconditional: `generosityPercent === null ⇔ either estimatedMinedGold OR estimatedMinedLumber is null`; numeric `generosityPercent ≥ 0`; coverage gaps populate `diagnostics.cohesionMetricGaps` AND `diagnostics.unmappedEntityIds` with `category: "unitCost"`. **Covers FR-014, invariant 22.**

**Checkpoint**: All US2 and US3 acceptance scenarios are green at JSON level. The Visualizer is still untouched.

---

## Phase 3: Tactical cohesion — focus fire, ping reactions, KP% (US4)

**Goal**: Per-battle focus-fire dominant-target / cohesion percent, minimap-ping reactions with responded vs. engagedElsewhere classification, per-player kill participation. After Phase 3, `team.battles[i].focusFire`, `team.battles[i].pings`, `team.battles[i].kills`, and `team.players[].killParticipationPercent` are populated.

**Depends on**: Phase 1b (battle windows are needed to scope all three metrics).

**Independent Test**: `cd processor && pytest tests/test_focus_fire.py tests/test_pings.py tests/test_kill_participation.py` is green. Pings inside battle windows are emitted; pings outside are not (invariant 5). Focus-fire `cohesionPercent` is in `[0, 100]`.

### Implementation for US4

- [ ] T038 [P] [US4] Implement `processor/team/cohesion.py::compute_focus_fire(battle, parser_output, ownership) -> FocusFire | None` — walks `0x12` actions inside `[battle.startMs, battle.endMs]` whose `object` handle is owned by an opposing-team slot. Aggregates by target handle; dominant target = max-attacked. Returns `None` (with diagnostic) if no enemy-handle ownership inferable.
- [ ] T039 [P] [US4] Implement `processor/team/cohesion.py::extract_pings(battle, parser_output, position_state) -> list[Ping]` — walks `0x68` events inside the battle window. For each, computes `respondedBySlot[]` per the formula in `data-model.md` § Response detection (`distance(c0, ping) - distance(c1, ping) >= 200` over a 15-s window) and `engagedElsewhereSlot[]` (slot is inside *some other* battle window's `[startMs, endMs]` at `ping.timeMs`).
- [ ] T040 [P] [US4] Implement `processor/team/kills.py::estimate_kills(battle, parser_output, ownership, position_state, unit_costs) -> list[KillEstimate]` — detects handle disappearances inside the battle window (handle was selected before, never selected after for ≥ 30 s); attributes each by attack-action share in the 5-s pre-disappearance window across the team; emits with damage-share `credits[]` summing to 1.0; skips kills with zero coverage (one match-level diagnostic).
- [ ] T041 [P] [US4] Implement `processor/team/kills.py::compute_match_kp_percent(battles, players_analysis) -> dict[slot, float | None]` — per-player KP% is `100 * Σ this_player_credits / Σ team_kills` across the match; null when a player has no attributable credits AND a corresponding diagnostic.
- [ ] T042 [US4] Wire Phase 3 into `processor/analyze.py` — `team.battles[i].focusFire`, `team.battles[i].pings`, `team.battles[i].kills`, `team.players[].killParticipationPercent` are populated.

### Tests for US4

- [ ] T043 [P] [US4] `processor/tests/test_focus_fire.py` — `cohesionPercent` ∈ `[0, 100]`; `dominantTargetSlot` is owner of an opposing-team handle; null branch produces a `cohesionMetricGaps` entry naming `focusFire:battle=N`. **Covers FR-016, invariants 11, 12.**
- [ ] T044 [P] [US4] `processor/tests/test_pings.py` — mirror invariant: every `0x68` event inside any battle window produces exactly one `Ping` entry under that battle; pings outside any battle are NOT emitted; `respondedBySlot ∩ engagedElsewhereSlot === ∅`; `fromSlot` is on the same side as the battle. **Covers FR-017, FR-018, invariants 5, 13, 14.**
- [ ] T045 [P] [US4] `processor/tests/test_kill_participation.py` — credit fractions sum to 1.0 ± 1e-6; each fraction > 0; unattributed kills are NOT emitted but a single match-level diagnostic exists; per-player KP% in `[0, 100]` or null. **Covers FR-019, invariants 15, 25.**

**Checkpoint**: All Phase 3 acceptance scenarios green.

---

## Phase 4: TEI + attribution + executive summary (US5)

**Goal**: Per-battle Trade-Efficiency Index (gold + lumber) per side and per player, attribution rows when split-engagement + low TEI + outlier centroid coincide, top-3 executive summary by weighted severity. After Phase 4, the analyzer emits a complete `team.battleSummary`.

**Depends on**: Phases 1b (battles, centroids), 3 (kills).

**Independent Test**: `cd processor && pytest tests/test_tei.py tests/test_tei_zero_loss.py tests/test_attributions.py tests/test_executive_summary.py` is green. Sentinel value `99.0` appears for zero-loss battles. `executive` length ≤ 3.

### Implementation for US5

- [ ] T046 [P] [US5] Implement `processor/team/tei.py::compute_battle_tei(battle, kills, players_analysis, unit_costs) -> BattleTEI` — gold-plus-lumber numerator over enemy units killed by the team; same denominator for own losses; cap at `99.0` when denominator is zero; per-player formula is `(attack_share * battle_team_value_killed) / max(player_value_lost, 1)` with the same cap. `null` when too few attributable kills (with diagnostic).
- [ ] T047 [P] [US5] Implement `processor/team/attribution.py::detect_attributions(battles, battleSummary_tei, centroids_per_battle) -> list[Attribution]` — emits a row when ALL three conditions hold: `splitEngagement.flagged === true`, `teamSideTei[playerSide] < 1.0`, player's centroid distance to side mean > `1.5 * mean_pairwise_distance` (per side). Multiple rows per battle allowed; multiple battles per player allowed.
- [ ] T048 [P] [US5] Implement `processor/team/attribution.py::compute_executive(team_block) -> list[ExecutiveFinding]` — collects every finding kind (`splitEngagement`, `missedSave`, `lowTei`, `sharedControlDisabled`, `wrongItemTransfer`, `ignoredPing`); applies severity weights from `plan.md` § Severity weights for executive summary; multiplies by `min(battle_duration / 60, 3.0)` (1.0 for non-battle-bound findings); sorts desc with chronological tiebreaker; caps at 3.
- [ ] T049 [US5] Implement `processor/team/shape.py::assemble_team_block(...) -> TeamBlock` — the JSON envelope assembler that wires all module outputs into the populated-state shape per `data-model.md` § TeamBlock. Single source of truth for the shape; called from `analyze.py`.
- [ ] T050 [US5] Wire Phase 4 into `processor/analyze.py` — final `team.battleSummary` is populated; the analysis JSON is feature-complete on the Processor side.

### Tests for US5

- [ ] T051 [P] [US5] `processor/tests/test_tei.py` — gold-plus-lumber formula correctness against a synthetic battle with known kills; sentinel `99.0` for zero-loss; `null` with diagnostic when too few kills. **Covers FR-021, invariant 24.**
- [ ] T052 [P] [US5] `processor/tests/test_tei_zero_loss.py` — explicit branch: own-side losses === 0 ⇒ `teamSideTei === 99.0` (NOT `null`, NOT `Infinity`); per-player with `value_lost === 0` produces ratio capped at 99.0 via `max(_, 1)`. **Covers FR-021, invariant 24.**
- [ ] T053 [P] [US5] `processor/tests/test_attributions.py` — three-condition gate: any one missing → no attribution row; all three present → exactly one row per outlier player per battle; `playerSlot ∈ battles[battleIndex].sides.{teamA | teamB}`. **Covers FR-022, invariant 26.**
- [ ] T054 [P] [US5] `processor/tests/test_executive_summary.py` — length ≤ 3; sorted desc by `weightedSeverity`; ties broken by chronological order; `rank` is `1, 2, ..., len`. Every finding's `evidenceRef` resolves to a real index / name. **Covers FR-023, invariants 27, 28.**

**Checkpoint**: Phase 4 green ⇒ `processor/analyze.py` is feature-complete. The full JSON contract is enforced.

---

## Phase 5: Visualizer Team tab

**Goal**: Render the `team.*` block on a fifth tab between `Timelines` and `Analysis` in the React app. Plain HTML for the bulk of the tab; ECharts only on the per-battle TEI bar. After Phase 5, dropping a regenerated `*.analysis.json` shows the executive summary, the per-battle list with split-engagement / focus-fire / pings / TEI / attributions, the resource-cooperation tables, the item-transfer log, and the shared-control banner.

**Depends on**: Phases 1b–4 (the JSON the tab reads must be feature-complete).

**Independent Test**: `cd visualizer && npm run dev`; load `sample_replays/base_1.w3g.analysis.json`; the new Team tab is visible between Timelines and Analysis; clicking it shows the executive summary, battle list, and resource-cooperation table; switching tabs preserves state.

- [ ] T055 [P] [US6] Extend `visualizer/src/types/analysis.ts` — add full TypeScript types for `TeamBlock`, `Battle`, `Centroid`, `AlliedDistance`, `SplitEngagement`, `FocusFire`, `Ping`, `KillEstimate`, `ItemTransfer`, `SupportEvent` (discriminated union by `type`), `AnnotatedTransfer`, `GenerosityRow`, `TeamPlayer`, `BattleSummary`, `BattleTEI`, `Attribution`, `ExecutiveFinding`, `EvidenceRef` (discriminated union by `kind`). Mirror `data-model.md` § Outputs verbatim.
- [ ] T056 [P] [US6] Implement `visualizer/src/data/teamFormat.ts` pure helpers: `formatDistance(units)`, `formatTei(value)` (renders `99.0` as `"≥ 99"`), `formatPercent(0..100)`, `formatPurposeHint`, `formatRecipientFitClass` with color-class mapping.
- [ ] T057 [P] [US6] Implement `visualizer/src/data/teamSeverity.ts` pure helpers — `rankExecutive(findings)` (deterministic re-rank for client-side display, mirroring the analyzer's logic for tooltip parity); `findingKindLabel(kind)` for human-readable headers.
- [ ] T058 [P] [US6] `visualizer/tests/teamFormat.test.ts` — unit tests for each formatter against representative inputs. **Vitest, pure logic.**
- [ ] T059 [P] [US6] `visualizer/tests/teamSeverity.test.ts` — `rankExecutive` produces deterministic top-3; tie-breakers behave correctly; unknown `kind` values render gracefully. **Covers Visualizer-side enum-extension robustness.**
- [ ] T060 [US6] Implement `visualizer/src/components/team/ExecutiveSummary.tsx` — renders `team.battleSummary.executive[]` as a top-of-tab card; click on a finding scrolls / highlights the corresponding row via `evidenceRef`. CSS module co-located.
- [ ] T061 [US6] Implement `visualizer/src/components/team/BattleList.tsx` — list of `BattleRow` components, one per `team.battles[i]`. Plain HTML + CSS; no virtualization (battle counts < 50).
- [ ] T062 [US6] Implement `visualizer/src/components/team/BattleRow.tsx` — one battle's findings: timestamp `mm:ss`, sides as colored chips, `SplitEngagementCallout` (when flagged), focus-fire dominant target with cohesion %, ping count summary, TEI per side, attribution rows (when present).
- [ ] T063 [US6] Implement `visualizer/src/components/team/SplitEngagementCallout.tsx` — when flagged, displays the two slot names, the centroid distance, the reference aura name + radius (or "default 900u"), and a colored bar comparing distance vs. radius.
- [ ] T064 [US6] Implement `visualizer/src/components/team/ItemTransfersTable.tsx` — table of `team.itemTransfers[]` with sender / recipient / item / `recipientFitClass` color-coded chip. Plain HTML table.
- [ ] T065 [US6] Implement `visualizer/src/components/team/ResourceCooperation.tsx` — banner for `team.sharedControl.enabled`, list of `AnnotatedTransfer` with `purposeHint` chip, sortable generosity table.
- [ ] T066 [US6] Implement `visualizer/src/components/team/PingReactions.tsx` — renders `team.battles[i].pings[]` with responded / engaged-elsewhere / ignored chips per ally per ping.
- [ ] T067 [US6] Implement `visualizer/src/tabs/TeamTab.tsx` — the tab orchestrator: applicability empty-state branch, populated branch with `<ExecutiveSummary>`, `<BattleList>`, `<ResourceCooperation>`, `<ItemTransfersTable>`. Reads `pageState.analysis.team`. CSS module.
- [ ] T068 [US6] Extend `visualizer/src/App.tsx` — tab strip grows from 4 to 5 (`Summary / Timelines / Team / Analysis / Map`); tab routing dispatches to `TeamTab` for the new key; tab order is stable across loads.
- [ ] T069 [US6] Visualizer empty-state branch for old `*.analysis.json` files — when `analysis.team === undefined`, render the Team tab with `reason: "preFeature006File"` empty state. Verified by an explicit Vitest case loading a fixture stripped of `team`.

**Checkpoint**: Manual quickstart walkthrough on both fixtures passes — see Phase 6.

---

## Phase 6: Non-regression and quickstart (US6 final gate)

**Goal**: Confirm features 001–005 still work, JSON output is a strict superset, and the manual review on both fixtures matches expectations.

**Depends on**: All previous phases.

- [ ] T070 [P] [US6] Author `specs/006-team-cohesion-analysis/quickstart.md` — manual walkthrough on both committed fixtures with explicit expected values: battle counts, splitEngagement counts, top-3 executive findings, `sharedControl.enabled` value per fixture. Mirror `specs/004-visualizer-tabs/quickstart.md`'s structure.
- [ ] T071 [P] [US6] `processor/tests/test_existing_fields_unchanged.py` — diff `*.analysis.json` produced before-and-after this feature: every key under `match`, `settings`, `map`, `players`, `observers`, `chat`, `diagnostics` (except the two new arrays) is unchanged. **Covers invariant 37.**
- [ ] T072 [P] [US6] `processor/tests/test_team_block_shape.py` — top-level keys are exactly the eight; Shape A vs Shape B mutual exclusivity; `team.applicable === false ⇒ no other team.* fields`; closed `findings[]` enum; closed `Attribution.reason` enum. **Covers invariants 1, 2, 3, 11, 23.**
- [ ] T073 [P] [US6] `processor/tests/test_cohesion_metric_gaps.py` — every numeric `null` in the `team.*` output has a corresponding `diagnostics.cohesionMetricGaps[]` entry; every entry refers to a real degraded field. **Covers invariant 35 (bidirectional diagnostics ⇔ degradation).**
- [ ] T074 [P] [US6] `processor/tests/test_lookup_table_shape.py` — auras / item_attributes / unit_costs / rescue_items JSON files conform to the schemas in `data-model.md` § Inputs; no orphan keys; rescue_items derived list agrees with item_attributes filtered.
- [ ] T075 [US6] **Determinism check** — re-run `python3 processor/analyze.py sample_replays/base_1.w3g.json` and `base_2.w3g.json` twice each; diff outputs; only `diagnostics.parserParseTimeMs` may differ. **Covers invariant 36 / SC-content-determinism.**
- [ ] T076 [US6] **Performance check** — measure analyzer wall-clock on `base_1.w3g.json` before-and-after the feature; ratio MUST be ≤ 1.25× per SC-002. Document before/after numbers in `quickstart.md`.
- [ ] T077 [US6] **JSON size check** — compare `base_1.w3g.analysis.json` size before-and-after; absolute size MUST be < 6 MB per SC-003.
- [ ] T078 [US6] **Run all existing test suites** — `cd parser && npm test` (unchanged), `cd processor && pytest` (67 + ≥24 = ≥91 cases all green), `cd visualizer && npm test` (35 + ≥6 = ≥41 cases all green). Zero edits to any pre-existing assertion.
- [ ] T079 [US6] **Manual quickstart walkthrough** — execute `quickstart.md` § 1–5 against both committed fixtures via `docker compose up` and via `npm run dev`. Record any deviations and either tune Phase-1b heuristic constants OR amend `quickstart.md`'s expected values.

**Checkpoint**: Phase 6 green ⇒ feature 006 is shippable.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 0** (Setup): No dependencies — start immediately.
- **Phase 1a** (Tier 2 foundation): Depends on Phase 0 (`team/events.py` constants).
- **Phase 1b** (US1): Depends on Phase 1a + Phase 0 lookup tables.
- **Phase 2** (US2 + US3): Depends on Phase 1b for the `team.*` envelope; can ship US2 and US3 in parallel.
- **Phase 3** (US4): Depends on Phase 1b (battle windows).
- **Phase 4** (US5): Depends on Phase 1b (battles), Phase 3 (kills).
- **Phase 5** (Visualizer): Depends on Phases 1b–4 (the JSON it reads must be complete).
- **Phase 6** (Non-regression): Depends on all prior phases.

### Within-Phase Parallelism

- All Phase 0 build-`*.py` scripts (T002, T004, T006) can run in parallel; T008 (probe) is independent.
- T010 / T011 / T012 in Phase 1a can be partially parallel (T011 before T012 because of class definition); tests T013 / T014 are parallel after.
- Phase 1b implementations (T015 → T020) are sequential; tests (T021 → T025) are parallel after.
- Phase 2 US2 (T026–T031) and US3 (T032–T037) are independent and parallelizable.
- Phase 5 component implementations (T060–T066) are mostly file-disjoint and parallelizable; T067 / T068 integrate them.

### Critical Path

`T001 → T002+T004+T006 → T009 → T010 → T011 → T012 → T013/T014 → T015 → T016 → T017 → T018 → T019 → T020 → T021–T025 → (Phase 2 US2 in parallel with US3) → T034 → T038–T041 → T042 → T046–T049 → T050 → T067 → T068 → T079`. Approximately 25 sequential checkpoints.

---

## Test coverage map

Mapping from `contracts/output-shape.md` invariants to test tasks. Every invariant 1–35 has at least one test; cross-cutting invariants 36–38 are covered by T075 / T071 / T079.

| Invariant | Covered by test task(s) |
|---|---|
| 1 (key set exactly 8) | T072 |
| 2 (empty-state minimality) | T072, T025 |
| 3 (populated-state completeness) | T072 |
| 4 (sides disjoint, non-empty) | T021 |
| 5 (battle indices contiguous) | T021 |
| 6 (battle time bounds) | T021 |
| 7 (centroid coordinate consistency) | T022 |
| 8 (allied distance pair canonicalization) | T022 |
| 9 (split-engagement biconditional) | T023 |
| 10 (aura reference resolved) | T024 |
| 11 (focus-fire null-or-complete) | T043 |
| 12 (cohesion percent range) | T043 |
| 13 (ping membership disjointness) | T044 |
| 14 (ping origin teammate) | T044 |
| 15 (kill credit fractions sum) | T045 |
| 16 (item-transfer mirror) | T029 |
| 17 (resource-transfer mirror) | T035 / T036 |
| 18 (recipient-fit-class enum) | T030 |
| 19 (support-event type enum) | T031 (+ T028 conditional) |
| 20 (missed-save ranges) | T031 |
| 21 (purpose-hint enum) | T035 |
| 22 (generosity null-pair coupling) | T037 |
| 23 (findings closed enum) | T036, T072 |
| 24 (TEI sentinel + bounds) | T051, T052 |
| 25 (kill emission gating) | T045 |
| 26 (attribution validity) | T053 |
| 27 (executive ordering + length) | T054 |
| 28 (executive evidence resolves) | T054 |
| 29 (entity reference resolution) | T030, T072 |
| 30 (player-slot consistency) | T021, T072 |
| 31 (time fields are ms ints) | T021, T072 |
| 32 (`unmappedEntityIds` extended categories) | T037, T074 |
| 33 (`cohesionMetricGaps` shape) | T073 |
| 34 (`itemAttributeGaps` shape) | T030, T073 |
| 35 (diagnostics ⇔ degradation bidirectional) | T073 |
| 36 (content determinism) | T075 |
| 37 (strict superset diff) | T071 |
| 38 (no re-derivation) | code review on T049 (manual gate, not a pytest case — tracked in PR template) |

---

## Implementation Strategy

### MVP first

1. Phases 0 + 1a (T001–T014) — committed lookup tables + position state machine.
2. Phase 1b (T015–T025) — US1 alone is already a usable demo. After this checkpoint, the analyzer JSON has team.battles[] + splitEngagement; manual review on `base_1` reveals the team's split engagements.
3. **STOP and VALIDATE**: open `base_1.w3g.analysis.json` in a JSON viewer, eyeball `team.battles[]` against the replay's recorded fights. If split-engagement values disagree with a manual review, tune the heuristic constants in `team/battles.py` / `team/centroids.py` BEFORE proceeding to Phase 2.

### Incremental delivery

After Phase 1b green: ship Phase 2 (US2 + US3) and Phase 3 (US4) in parallel if multiple developers; otherwise sequentially in priority order. Phase 4 (US5) builds on top. Phase 5 (Visualizer) is the final user-visible deliverable. Phase 6 is the non-regression gate before the merge button.

### Hard gates between phases

- Phase 1a does NOT progress to Phase 1b unless `test_unit_ownership.py` and `test_position_tracking.py` are green AND coverage on `base_2` meets the bar in T013 / T014.
- Phase 1b does NOT progress to Phase 2 unless SC-001 (zero false-flag rate on both fixtures) is met, validated against `quickstart.md`'s expected battle counts.
- Phase 5 does NOT progress to Phase 6 unless SC-006 (Team-tab paint ≤ 150 ms) is met on both fixtures.
- Phase 6 is the merge gate: T078 (all three test suites green) and T079 (manual quickstart) MUST both pass.

---

## Notes

- **Task IDs are stable** — once assigned, T-ids are not renumbered. New tasks discovered during implementation get appended T080+.
- **`[P]` means file-disjoint** — different source / test files, no incomplete-task dependency. Two `[P]` tasks can run in parallel by different developers (or the same developer in different branches). `[P]` does NOT mean "easy."
- **No commit-after-each-task discipline is enforced**, but the phase checkpoints are natural commit boundaries.
- **Heuristic constants live as module-top constants** in `processor/team/*.py` (`MIN_RESPONSE_DELTA`, the 5-s pre-death window, etc.). They are tunable in `tasks.md` after the first pytest run; tuning does not require new tasks.
- **Avoid same-file conflicts** — when two `[P]` tasks touch the same file (e.g., both extend `analyze.py`), drop the `[P]` and serialize them. This applies especially to T020, T034, T042, T050 (all wire into `analyze.py`).
- **Pytest invocation** — `cd processor && pytest` runs everything. Run subsets via `pytest tests/test_X.py`. The conftest auto-loads both committed fixtures.
- **Vitest invocation** — `cd visualizer && npm test`. Only `*.test.ts` files in `tests/` are picked up.
