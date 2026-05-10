---
description: "Tasks for feature 008: Team Tab Data Drill-Downs"
---

# Tasks: Team Tab Data Drill-Downs

**Input**: Design documents from `/specs/008-team-tab-drill-downs/`
**Prerequisites**: spec.md, plan.md, contracts/ui-contract.md (no data-model — pointer to feature 007)

**Tests**: Vitest pure-logic only (chip classifier, ping side resolver, kills top-N sorter, evidence-ref dispatcher). Visual correctness via `quickstart.md` manual walkthrough on `base_2`.

**Organization**: Tasks grouped by user story. Single feature, three phases.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: file-disjoint, parallelizable.
- **[Story]**: US1–US8 from spec.md.

## Path Conventions

- **Visualizer source**: `visualizer/src/{tabs,data}/`.
- **Visualizer tests**: `visualizer/tests/`.
- All work additive — no file deletions.

---

## Phase 1: P1 stories — pings, focus-fire contributors, non-regression

**Goal**: Buy back the highest-value missing data from the original problem statement (requirements 4.1 + 4.2). After Phase 1, every ping and every contributor's attack count is visible.

- [ ] T001 [P] [US1] Add `classifyPingChips(ping, sideMembers)` pure helper to `visualizer/src/data/teamFormat.ts`. Returns `{responded, busy, ignored}` as `Set<number>` triples. The Ignored set is `sideMembers − responded − busy`, where `sideMembers` excludes the pinger.
- [ ] T002 [P] [US1] Add `resolvePingSide(ping, battle)` pure helper that returns the array of slot ids on the same side as `ping.fromSlot` (excluding the pinger), used as input to `classifyPingChips`.
- [ ] T003 [P] [US1] Vitest cases for `classifyPingChips` + `resolvePingSide` in `visualizer/tests/teamFormat.test.ts` (or new `team-derive.test.ts`). Cover: all responded, all busy, mixed, all ignored, fromSlot on teamA vs teamB.
- [ ] T004 [US1] Extend `BattleRow` in `visualizer/src/tabs/TeamTab.tsx` — render Pings sub-section listing every ping row with `mm:ss`, pinger name, and three chip groups (Responded green, Busy yellow, Ignored red). Battles with `pings.length === 0` render no sub-section (FR-004).
- [ ] T005 [US2] Extend `BattleRow` — render `focusFire.contributingPlayers[*]` as an inline list ("Attacks: name (count) · name (count)"). When `focusFire === null`, render the explanatory copy referring to the diagnostic (FR-006).
- [ ] T006 [US8] Spot-check `quickstart.md` § 3.2 of feature 007 still passes — open visualizer on `base_2`, confirm executive summary, shared control banner, battle list, resource cooperation, item gives, KP%, diagnostics all render as before.

**Checkpoint**: After Phase 1, base_2's Team tab shows full ping reaction breakdown for 79 pings and full attacker contribution for 4 battles.

---

## Phase 2: P2 stories — kills drill-down, per-player TEI surface

**Goal**: Surface the data behind TEI calculations. After Phase 2, kills are visible (top-10 by value) and per-player TEI table is rendered (all "—" with explanatory tooltip for v1).

- [ ] T007 [P] [US3] Add `topNKillsByValue(kills, n)` pure helper to `teamFormat.ts`. Returns sorted-and-sliced array; preserves original order on ties.
- [ ] T008 [P] [US3] Vitest case for `topNKillsByValue` covering: empty list, fewer-than-N, exactly-N, more-than-N, ties.
- [ ] T009 [US3] Extend `BattleRow` — render a `<details>` collapsible "Kills (N)" section. Body: top-10 sorted by victimValue desc, each row showing `mm:ss`, victimSide chip, value (gold + lumber sum), credits as chips. Truncation hint when `N > 10`.
- [ ] T010 [US4] Add Per-player TEI sub-table inside the BattleSummary section. One row per `perPlayerTei[*].slot`, render value via existing `formatTei`. Null values get a `title` attribute (HTML tooltip) explaining the v1 limitation.

**Checkpoint**: After Phase 2, every battle has a kills drill-down + per-player TEI table.

---

## Phase 3: P3 stories — geometry, attributions empty-state, click-to-scroll

**Goal**: Polish the surface — coordinates panel, explanatory empty-states, navigable executive findings.

- [ ] T011 [US5] Add Geometry `<details>` section inside each battle. Body: centroids table (slot / x / y / source) + per-side allied-distance matrix using `formatDistance`. Missing centroids render "—" with a tooltip.
- [ ] T012 [US6] Replace the silent absence of attributions with an empty-state row when `team.battleSummary.attributions === []`. Copy: "No strategic blame attributed (requires split engagement + lost trade + outlier centroid simultaneously)."
- [ ] T013 [P] [US7] Add `dispatchEvidenceRef(ref, refsMap)` pure helper to `teamFormat.ts`. Given an `EvidenceRef` and a map of `(kind, index|name) → DOM-id`, returns the target DOM id or `null` for unknown kinds.
- [ ] T014 [P] [US7] Vitest case for `dispatchEvidenceRef` covering all four v1 kinds plus a forward-compat unknown kind.
- [ ] T015 [US7] Wire executive findings as buttons. On click, scroll the matching DOM element into view (`scrollIntoView({behavior:'smooth', block:'center'})`) and apply a 2-second highlight class. Use refs/data attributes to identify targets: `data-evidence-id="battle-N"`, `data-evidence-id="supportEvent-N"`, etc.
- [ ] T016 [US7] Add CSS keyframe animation for the highlight pulse (2-second box-shadow / outline cycle). Apply via class toggle managed by `useState` + `setTimeout`.

**Checkpoint**: After Phase 3, every executive finding becomes a navigable button; geometry and attribution surfaces are visible.

---

## Phase 4: Final review

- [ ] T017 [US8] Run full Vitest suite — count new cases ≥ 8, total cases ≥ 56 (48 baseline + ≥ 8 new). Zero edits to existing assertions.
- [ ] T018 [US8] Author `quickstart.md` — manual walkthrough on `base_2` covering each US's Independent Test plus feature 007 non-regression spot-check. Calibration: confirm 4 battle drill-downs render correctly, 7 item gives still show as `UNKN` per documented limitation, 6 generosity rows still rank correctly.
- [ ] T019 [US8] Performance check — measure Team-tab paint via DevTools Performance after expanding all drill-downs. ≤ 150 ms first paint target unchanged from feature 007 SC-006.
- [ ] T020 [US8] File-swap check — load `base_2`, expand a drill-down, load `base_1` (or vice versa). Verify no expansion state leaks across files (FR-024).

**Checkpoint**: Phase 4 green ⇒ feature 008 shippable.

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1: starts immediately, no prerequisites.
- Phase 2: depends on Phase 1's `BattleRow` skeleton being extended (kills sub-section adds another collapsible).
- Phase 3: depends on Phase 1 for the same reason.

### Within-Phase Parallelism

- T001 / T002 / T003: pure-helper work, file-disjoint, parallelizable.
- T007 / T008: same — kills sorter helper + test.
- T013 / T014: evidence-ref dispatcher helper + test.
- Implementation tasks (T004, T005, T009, T010, T011, T012, T015, T016) all touch `TeamTab.tsx` and serialize against each other.

### Critical Path

`T001 → T002 → T003 → T004 → T005 → T006 → T007 → T009 → T010 → T011 → T012 → T013 → T015 → T016 → T017 → T018`. ~16 sequential nodes; trivial to ship in one developer-day.

## Test coverage map

| UI invariant | Covered by |
|---|---|
| UI-1, UI-2 (pings) | T003 (Vitest classifier) + T004 (manual UI in quickstart) |
| UI-3 (chip color order) | Manual visual inspection (T018) |
| UI-4, UI-5 (focus fire contributors) | T005 + manual (T018) |
| UI-6, UI-7, UI-8 (kills) | T008 (Vitest sort) + T009 (manual T018) |
| UI-9, UI-10, UI-11 (per-player TEI) | T010 + manual (T018) |
| UI-12, UI-13, UI-14 (geometry) | T011 + manual (T018) |
| UI-15, UI-16 (attributions) | T012 + manual (T018) |
| UI-17, UI-18, UI-19 (click-to-scroll) | T014 (Vitest dispatcher) + T015 + manual (T018) |
| UI-20, UI-21, UI-22 (non-regression) | T006, T020 + full feature 007 quickstart re-run |

## Notes

- **TeamTab.tsx grows additively.** Hard cap at ~700 LOC; if exceeded, plan.md mandates refactor into `components/team/` per feature 007's planned-but-skipped structure.
- **No new files in source tree.** All new code in `TeamTab.tsx` + `teamFormat.ts`; new tests stay in `teamFormat.test.ts` (or split into `team-derive.test.ts` if growing past comfort).
- **`<details>` HTML element** is the disclosure widget of choice — zero JS, zero deps, native ARIA. React state for the highlight pulse only.
- **No test for `<details>` toggle behavior** — that's browser-native; tests cover pure helpers only.
