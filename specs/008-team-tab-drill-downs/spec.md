# Feature Specification: Team Tab Data Drill-Downs

**Feature Branch**: `008-team-tab-drill-downs`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "Team-tab post-007 audit found that ~40% of the JSON content the analyzer emits is not surfaced in the UI — pings drill-down, focus-fire contributors, kills, per-player TEI, centroids, attributions empty-state, evidence-ref click navigation. JSON contract is correct; the visualizer just doesn't read all of it."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Per-ping reaction drill-down (Priority: P1)

A reviewer wants to see exactly which teammates ignored which pings. Today the Team tab shows "Pings: 44" without context. They want a per-ping table inside each battle: time, who pinged, target coordinates, who responded (green chip), who was busy elsewhere (yellow chip), who ignored (red chip). This directly buys back requirement 4.2 of the original team-cohesion problem statement ("ignored pings classified as serious team error").

**Why this priority**: The data already lives in `team.battles[i].pings[*]` — `respondedBySlot[]`, `engagedElsewhereSlot[]`, plus the implicit "ignored" set computable as `allies − responded − busy`. Surfacing it requires UI work only, no analyzer change. Highest ROI of any drill-down.

**Independent Test**: Open Team tab on `base_2.w3g.analysis.json`. Each battle row has a Pings sub-section listing 44/17/18/0 pings respectively. Each ping row shows time `mm:ss`, pinger name, three chip groups labelled "Responded", "Busy", "Ignored" with player names.

**Acceptance Scenarios**:

1. **Given** Team tab is open on `base_2`, **When** user looks at battle 0, **Then** a "Pings (44)" sub-section is visible within the battle card; each ping row shows the four documented data points.
2. **Given** a ping where one teammate is in `respondedBySlot` and another in `engagedElsewhereSlot`, **When** user views the ping row, **Then** the responding ally appears in a green chip, the busy ally in a yellow chip, and any remaining ally on the same side appears in a red "Ignored" chip.
3. **Given** a battle with `pings.length === 0`, **When** user views the battle card, **Then** the Pings sub-section is either omitted or shows an explicit "No pings" empty state — never a dangling "Pings: 0" with no breakdown.
4. **Given** a ping whose `fromSlot` is on `teamA`, **When** classifying allies for chip rendering, **Then** only the other `teamA` members appear in chips (not opposing-team players).

---

### User Story 2 — Focus-fire contributors breakdown (Priority: P1)

The Team tab shows "Focus fire: 15% on BlackObelisk#2428" but hides who actually contributed. The reviewer wants to see the breakdown: which teammates attacked the dominant target and how many times each. Buys back actionable detail behind requirement 4.1 of the original problem statement.

**Why this priority**: Same JSON-already-has-it pattern as US1. `battle.focusFire.contributingPlayers[]` is a sorted list of `{slot, attackCount}` per battle. Currently rendered as nothing. Surfacing it needs ~20 LOC.

**Independent Test**: On battle 0 of `base_2`, the focus-fire line is followed by a contributor list: "Attacks: Blayed#2127 (224) · tomulle#2354 (133) · kir#2613 (95) · BlackObelisk#2428 (76) · velimix#2364 (60) · SharkHbc#2882 (25)".

**Acceptance Scenarios**:

1. **Given** a battle with `focusFire !== null`, **When** user views the battle card, **Then** the contributors list is visible with each player's attack count.
2. **Given** a battle with `focusFire === null`, **When** user views the card, **Then** the focus-fire section shows "no enemy unit-handle ownership inferable" or similar empty-state copy — no broken render.
3. **Given** the contributors list, **When** sorted, **Then** the highest `attackCount` appears first (already sorted by analyzer per data-model.md § FocusFire).

---

### User Story 3 — Per-battle kills drill-down (Priority: P2)

The TEI numbers on a battle row don't show their inputs. A reviewer wants to expand a battle and see top-N kills sorted by `victimValue` with credits chips per slot — concrete evidence behind the trade-efficiency calculation.

**Why this priority**: P2 because TEI per side is already visible; the kills drill-down adds explanation but is not a missing core finding. The data is in `battle.kills[*]` (60 kills on `base_2` battle 0).

**Independent Test**: On battle 0 of `base_2`, click a "Show kills" affordance to reveal a table of the top-10 kills by `victimValue`, each row showing time, victim side (teamA/teamB), value (gold + lumber), and credits as `slot:fraction%` chips.

**Acceptance Scenarios**:

1. **Given** a battle with `kills.length > 0`, **When** user clicks "Show kills" (or expands by default if scope is small), **Then** a kills table renders with at least 10 rows or all kills if fewer.
2. **Given** a kill with three credit fractions summing to 1.0, **When** the row renders, **Then** each credit appears as a chip showing the slot and the percentage.
3. **Given** the kills are sorted by `victimValue` descending, **When** the table renders, **Then** the highest-value victim is the first row.

---

### User Story 4 — Per-player TEI structural surface (Priority: P2)

The `team.battleSummary.tei[i].perPlayerTei[*]` block lives in the JSON. Per-player values are `null` in v1 (documented limitation), but the *table itself* is invisible — users have no way to know the metric was designed. The reviewer wants the table rendered with `null` values shown as "—" and a tooltip explaining why.

**Why this priority**: P2 because the metric is degraded — but rendering an empty table with explanation is more honest than hiding the entire structure. Sets up forward compatibility: when feature 010 lands per-handle ownership, no UI change is needed.

**Independent Test**: On any battle's TEI section, a "Per-player TEI" sub-table appears with one row per slot. Each cell shows "—" with a tooltip: "Per-player TEI requires per-handle owner attribution; deferred to feature 010."

**Acceptance Scenarios**:

1. **Given** a battle with `perPlayerTei` populated (all-null values), **When** user views the battle, **Then** a table with one row per player slot is visible.
2. **Given** a `null` per-player TEI cell, **When** user hovers, **Then** the documented v1-limitation tooltip appears.
3. **Given** a future replay with non-null per-player TEI, **When** rendered, **Then** the same table shows numeric values without code change. (Forward-compatibility test using a synthetic fixture.)

---

### User Story 5 — Centroids and allied-distance panel (Priority: P3)

A reviewer who saw a flagged split engagement wants to drill into the geometry: where exactly are the centroids? What's the full pairwise distance matrix on each side? The data is already in `battle.centroids[]` and `battle.alliedDistances[]`.

**Why this priority**: P3 because raw coordinates are not directly meaningful without map visualization (which is a future Map-tab feature). But the *distance matrix* is human-readable and useful for understanding "why" the split flag fired.

**Independent Test**: Each battle card has a collapsed "Geometry" section. Expanded, it shows a small table of all centroids `{slot, x, y, source}` and a per-side distance matrix.

**Acceptance Scenarios**:

1. **Given** a battle with non-null centroids, **When** user expands "Geometry", **Then** the table shows each player's `(x, y)` rounded to integer.
2. **Given** a centroid with `source === "missing"`, **When** rendered, **Then** the row shows "—" for x/y with a "no commands in lookback window" tooltip.
3. **Given** the distance matrix, **When** rendered, **Then** intra-side pairs are visible with formatted distances (e.g., "8,830 u").

---

### User Story 6 — Empty-state copy for zero-attribution case (Priority: P3)

When `team.battleSummary.attributions[]` is empty (the case on both committed fixtures), today nothing renders. The reviewer doesn't know the metric exists. They want an explanatory empty-state.

**Why this priority**: P3 polish — adds clarity without delivering new functionality. ~10 LOC.

**Independent Test**: On `base_2`, the BattleSummary section includes an Attributions sub-section with text: "No strategic blame attributed (requires split engagement + lost trade + outlier centroid simultaneously)."

**Acceptance Scenarios**:

1. **Given** `attributions === []`, **When** user views BattleSummary, **Then** the empty-state copy is visible.
2. **Given** at least one attribution, **When** rendered, **Then** the empty-state copy is replaced by the populated list.

---

### User Story 7 — Click-to-scroll executive evidence refs (Priority: P3)

Each `ExecutiveFinding.evidenceRef` was designed as a clickable pointer (kind: "battle"/"supportEvent"/"itemTransfer"/"globalFlag"). Currently the executive summary renders findings as static text. The reviewer wants to click a finding and have the page scroll to the evidence row, briefly highlighting it.

**Why this priority**: P3 UX polish. The data structure was designed for this (data-model.md § EvidenceRef) but the UI never used it.

**Independent Test**: Click "Split engagement at 4:05" in the executive summary. The Battle 0 card scrolls into view and is briefly highlighted (e.g., 2-second outline pulse).

**Acceptance Scenarios**:

1. **Given** an executive finding with `evidenceRef.kind === "battle"`, **When** user clicks the finding row, **Then** the matching battle card scrolls into view and pulses briefly.
2. **Given** an evidence ref of kind `"globalFlag"`, **When** user clicks the finding, **Then** the Shared Control banner is the highlighted target.
3. **Given** an unknown evidence ref kind (forward-compat), **When** rendered, **Then** the finding remains visible but click is a no-op (no crash).

---

### User Story 8 — Existing Team tab capabilities still work (Priority: P1)

Every assertion of feature 007's `quickstart.md` against the Team tab MUST continue to hold. New drill-downs are *additive* — they don't replace, hide, or reshape existing rendering.

**Why this priority**: P1 by definition. No new feature ships if it regresses 006.

**Independent Test**: Run feature 007's quickstart § 3.2 against the post-007 visualizer. Every check passes — Executive summary still renders top-3, Shared control banner still toggles, Battles list still shows the 4 battles, Resource cooperation tables still populate, Item gives still color-code Fit, KP% still appears.

**Acceptance Scenarios**:

1. **Given** the Team tab loads after feature 008 ships, **When** rendering on `base_2`, **Then** all 7 sections from feature 007 still appear.
2. **Given** a pre-007 `*.analysis.json` (no `team` block), **When** loaded, **Then** the empty-state copy still appears identically.
3. **Given** the Vitest suite runs, **When** counted, **Then** all 48 pre-007 cases pass plus the new ones.

---

### Edge Cases

- A battle with **zero pings**: pings sub-section either omitted or shows "No pings" copy — never a misleading "Pings: 0" without explanation.
- A ping where **all allies responded**: the "Ignored" chip group renders empty (no chips), not a false "Ignored: none" header — group is just absent from that ping's row.
- A battle with `focusFire === null`: focus-fire sub-section shows the analyzer's degradation reason from `diagnostics.cohesionMetricGaps`, not silent absence.
- A battle with `kills.length === 0`: kills drill-down is collapsed by default and shows a "No attributable kills" copy when expanded — the TEI numbers may also be 0 / null.
- An **executive finding with `evidenceRef.kind === "globalFlag"` but the named flag absent from `team.findings[]`**: per US7 graceful no-op, do not crash.
- A **forward-compat `EvidenceRef.kind`** value not in v1's enum: render the finding as static (no click handler), do not crash.
- **Pre-007 `*.analysis.json`** (entire `team` block missing): existing empty-state from feature 007 continues to render. None of the new drill-downs attempt to query a missing block.
- A ping whose `respondedBySlot ∪ engagedElsewhereSlot` covers every ally: "Ignored" group is empty.
- Per-player TEI with **mixed null + numeric values** (a future scenario when feature 010 ships partial owner tracking): table renders correctly mixing "—" and numbers.

## Requirements *(mandatory)*

### Functional Requirements

#### Pings drill-down (US1)

- **FR-001**: For every `battle.pings[*]`, the Team tab MUST render a row showing: `timeMs` formatted `mm:ss`, `fromSlot` resolved to player name, the three classification groups (Responded / Busy / Ignored), each rendered as a list of player-name chips.
- **FR-002**: The Ignored set MUST be computed as `(allies on the same side as fromSlot) − respondedBySlot − engagedElsewhereSlot`. The Visualizer derives this on the fly; it is NOT in the JSON.
- **FR-003**: Chip color coding: Responded → green family, Busy → yellow family, Ignored → red family. Exact hex values are not part of the contract.
- **FR-004**: Battles with zero pings MUST either omit the pings sub-section entirely OR render an explicit empty-state copy. They MUST NOT render a "Pings: 0" header with nothing under it.

#### Focus fire contributors (US2)

- **FR-005**: For every `battle.focusFire !== null`, the Team tab MUST render `contributingPlayers[*]` as a visible per-attacker breakdown showing each `{slot resolved to name, attackCount}`.
- **FR-006**: When `focusFire === null`, the Team tab MUST render an explanatory copy referring to the corresponding `diagnostics.cohesionMetricGaps` entry (e.g., "no enemy unit-handle ownership inferable").

#### Kills drill-down (US3)

- **FR-007**: For every battle with `kills.length > 0`, the Team tab MUST provide an affordance to show the kills list — either expanded by default or behind a click-to-expand toggle.
- **FR-008**: The kills list MUST be sorted by `victimValue` descending and limited to a top-N (default N=10; configurable in code is fine, not exposed in UI).
- **FR-009**: Each kill row MUST show `killTimeMs` (`mm:ss`), `victimSide` (teamA/teamB), `victimValue` (numeric), and `credits[*]` rendered as chips of the form `<slot resolved to name>: <fraction × 100>%`.

#### Per-player TEI surface (US4)

- **FR-010**: For every `battleSummary.tei[i]`, the Team tab MUST render a "Per-player TEI" sub-table with one row per `perPlayerTei[*].slot`.
- **FR-011**: A `null` per-player TEI value MUST render as "—" with a tooltip explaining the v1 limitation.
- **FR-012**: A non-null per-player TEI value (forward-compat) MUST render as a numeric formatted by the existing `formatTei` helper, without a tooltip.

#### Geometry panel (US5)

- **FR-013**: For every battle, the Team tab MUST provide an expandable "Geometry" section containing: a centroids table (one row per `battle.centroids[*].slot`) and a per-side allied-distance matrix.
- **FR-014**: A `centroid` with `source === "missing"` MUST render with "—" for `x`/`y` and a tooltip "no commands in centroid lookback window" or equivalent.
- **FR-015**: Distances MUST use the `formatDistance` helper from feature 007.

#### Attributions empty-state (US6)

- **FR-016**: When `team.battleSummary.attributions === []`, the Team tab MUST render an Attributions sub-section with explanatory copy. Hidden absence is forbidden.
- **FR-017**: When `attributions.length > 0`, the existing rendering from feature 007 (one row per attribution attached to its battle) MUST continue.

#### Click-to-scroll evidence refs (US7)

- **FR-018**: Each `executive[*]` finding MUST be rendered as a clickable element (cursor: pointer; `<button>` or `<a>`-like role).
- **FR-019**: On click, the page MUST scroll the matching evidence target into view (`scrollIntoView({ behavior: 'smooth', block: 'center' })`) AND apply a brief visual highlight (e.g., box-shadow pulse) for ~2 seconds.
- **FR-020**: An `evidenceRef.kind` value not in v1's closed enum MUST render the finding as plain text (no click handler), without a crash. Forward-compat per output-shape.md compatibility section.

#### Non-regression (US8)

- **FR-021**: Every UI element from feature 007's `quickstart.md` § 3.2 MUST continue to render identically. Drill-down additions are inside or below existing sections, not in place of them.
- **FR-022**: All existing Vitest cases (48 from features 003–006) MUST continue to pass with no edits to existing assertions.
- **FR-023**: A pre-007 `*.analysis.json` MUST continue to render the documented empty-state. None of the new drill-downs may dereference a missing `team.*` field.
- **FR-024**: Loading a different file mid-session MUST clear all expanded drill-down state — no bleed-through of "Battle 4 expanded" from a prior file.

### Key Entities

This feature does NOT introduce new analysis-JSON entities. All work consumes `team.*` fields already documented in `specs/007-team-cohesion-analysis/data-model.md`. Three Visualizer-internal entities are introduced for UI state:

- **Drill-down expansion state**: per-battle booleans for "kills expanded" and "geometry expanded". In-memory only; reset on file reload.
- **Highlight pulse state**: a transient `{targetId, expiresAt}` triple driven by `useState` + `setTimeout(2000)`. Cleared after the pulse.
- **Chip classification**: a pure function `(ping, sideMembers) → {responded, busy, ignored}` that derives the three groups from the JSON's two arrays.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A reviewer encountering the Team tab on `base_2` for the first time can identify which ally ignored which ping in under **30 seconds** of inspection. Qualitative test against `quickstart.md`.
- **SC-002**: 100% of feature 007's quickstart § 3.2 checks continue to pass on the post-007 visualizer against both committed fixtures.
- **SC-003**: The Team tab paint budget (≤ 150 ms first paint per feature 007 SC-006) MUST hold. Measurement: same DevTools Performance technique as feature 007.
- **SC-004**: The Vitest case count grows from 48 by **at least 8** (pure-logic helpers for the chip classifier, ping-side resolver, kills sort + top-N, evidence-ref dispatcher).
- **SC-005**: Every JSON field enumerated in the audit table (`battle.centroids`, `alliedDistances`, `pings[*]` details, `focusFire.contributingPlayers`, `kills[*]`, `perPlayerTei[*]`) is visible in the UI on `base_2` after this feature ships. Auditable: a manual walkthrough of the data-model document checking each `team.battles[*]` sub-key against what the rendered DOM contains.
- **SC-006**: No new external dependencies are added. Princ. VI gate degenerate (already passes by inheritance from feature 005).
- **SC-007**: Clicking an executive finding on `base_2` brings the matching battle card into the viewport within **500 ms** of the click. Manual `quickstart.md` test.

## Assumptions

- **JSON contract is fixed.** Every drill-down reads existing fields. No analyzer change is part of this feature. If a field is missing or has unexpected shape, the v1 limitation documented in feature 007's `research.md` continues to apply (graceful degradation per FR-029 of feature 007).
- **No state-management library.** The new in-memory expansion state lives in plain `useState`, mirroring feature 005's posture (Princ. III — no premature abstractions).
- **No keyboard navigation.** Click-to-scroll is mouse-only in v1; keyboard accessibility is a polish concern for a later feature.
- **No persistent expansion state.** Closing and reopening the page resets all expansions to default. Same as feature 005's "no localStorage" stance.
- **Top-N for kills is N=10.** Hardcoded in the component; not exposed as a UI control. Tunable in code if `quickstart.md` review reveals a better default.
- **Visualizer-only feature.** Processor is unchanged. Parser is unchanged. No new analyzer fields, no new lookup tables, no `analyze.py` edits.

## Out of Scope

- **Per-handle item-id resolution.** That is feature 009. Until it ships, kills' `victimEntity` and item transfers' `item.id` continue to be `UNKN`.
- **Per-handle owner tracking for losses.** That is feature 010. Per-player TEI continues to render `null` for now.
- **Spell-cast on-ally detection.** That is feature 011 (or never, per Phase 0 probe outcome).
- **Map-tab integration.** Centroids panel renders raw coordinates; on-map visualization is the future Map tab's job.
- **Mobile / touch-first layouts.** Desktop-only.
- **Persistent expansion state.** No `localStorage`.
- **i18n.** English copy only.
- **Cross-replay comparison.** Per-replay only, mirroring features 003–006.
- **Telemetry / analytics.** Per Principle V (c).
