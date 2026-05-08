# Feature Specification: Team Cohesion Analysis (Spatial, Support, Economic, Tactical)

**Feature Branch**: `006-team-cohesion-analysis`
**Created**: 2026-05-08
**Status**: Draft
**Input**: User description: "Now that base parsing is done, focus on team-play synergy and tactical-misalignment detection between allies — split engagement (centroid distance vs. aura radius), support items / rescues used vs. missed, resource transfers and shared-control posture, focus-fire cohesion + ping reactions + kill participation, and a per-battle Trade-Efficiency Index that attributes losses to specific players."

## User Scenarios & Testing *(mandatory)*

### User Story 1 — Spotting Split Engagement (Priority: P1)

A reviewer is watching a 4v4 replay where their team lost a midgame fight. Looking at the Summary tab they only see APM and individual action totals — nothing tells them *why* the fight was lost. They want the report to call out: at the moment the fight started, two allied armies were 1800 in-game units apart, well outside Paladin Devotion Aura's 900 range, so the auras + heal coverage that should have applied to both fronts only applied to one. They want the offender named, the timestamp clickable, and the centroid distance shown next to the aura radius they were *supposed* to be inside.

**Why this priority**: Split-engagement is the single highest-impact team-game error and the requirements call it out as «наиболее критичная ошибка» in team modes. Detecting it changes the report from "what each player did" into "what the team did wrong." Without this story, the rest of the cohesion suite is decoration around an absent core finding.

**Independent Test**: Run the analyzer against `sample_replays/base_1.w3g.json` and inspect the resulting analysis JSON for a `team.battles[].splitEngagement` block per detected battle. For each battle, the centroid coordinates and pairwise centroid distance for every allied pair MUST be present, and pairs whose distance exceeds the team's largest active-aura radius MUST be flagged. Open the visualizer's Team tab and confirm the flagged battles render with a "Split engagement" callout naming the two ally slots, the distance, the closest aura radius, and the in-game `mm:ss` timestamp.

**Acceptance Scenarios**:

1. **Given** a replay containing a sustained team fight, **When** the analyzer runs, **Then** the analysis JSON contains a `team.battles[]` entry covering that fight with start/end times in milliseconds and per-side army centroids `{x, y}` in map coordinates.
2. **Given** an `team.battles[]` entry where two allied centroids are farther apart than the largest aura radius active in that battle window, **Then** the entry's `splitEngagement.flagged` is `true`, `splitEngagement.distance` reports the Euclidean centroid distance, and `splitEngagement.referenceAuraId` names the aura that *would* have been the bound (e.g., `"Hpal_devotion"`).
3. **Given** the same fight where allies stayed within aura radius, **Then** `splitEngagement.flagged` is `false` and the report does not surface a callout.
4. **Given** the visualizer Team tab is open with this analysis loaded, **When** the user looks at flagged battles, **Then** each row shows the two ally names, the centroid distance and the aura radius, the timestamp, and a clickable affordance that jumps the Timelines tab to that exact `[startMs, endMs]` window.
5. **Given** a 1v1 replay (no allies) is loaded, **Then** the Team tab renders an empty state ("No teammates — split-engagement analysis is not applicable") and no battles are flagged. No crash, no NaN, no silent skip.

---

### User Story 2 — Catching Missed Saves and Mis-Targeted Items (Priority: P1)

A reviewer's hero died in a fight and they want to know whether anyone *could* have saved them. They expect the report to surface: ally hero died at `t=0:34:17`; teammate had an unused Staff of Preservation in inventory and was within map range of the dying hero; this is a missed save. They also want the report to call out item-give events `0x13` whose recipient looked wrong — e.g., an Orb of Lightning given to the Paladin hero whose primary attribute is Strength, when the Sorceress on the team would have benefited more.

**Why this priority**: Missed-save and wrong-recipient findings translate directly to actionable feedback ("you should have used the staff" / "give the int item to the int hero"). The required signals — hero deaths, inventory at time-of-death, item-give events `0x13`, and recipient hero attributes — are derivable from existing parser output plus modest enrichment (item-attribute mapping in `entity_names.json`). High value, modest cost. P1.

**Independent Test**: Load a fixture where a hero dies in combat (revives at altar). The analysis JSON's `team.supportEvents[]` MUST contain an entry with `type: "missedSave"` if any ally held one of the catalogued rescue items at the moment of death AND was within rescue-eligible range. The analysis JSON's `team.itemTransfers[]` MUST contain entries for every `0x13` action with sender / recipient slots, the item entity reference, and a `recipientFitClass` of `"good" | "questionable" | "wrong"` derived from item-attribute fit.

**Acceptance Scenarios**:

1. **Given** a replay where an allied hero dies while a teammate's hero holds an unused Staff of Preservation within rescue range, **When** the analyzer runs, **Then** `team.supportEvents[]` contains `{ type: "missedSave", deceasedSlot, holderSlot, itemId: "stwp", deathTimeMs, distanceAtDeath }`.
2. **Given** a replay containing one or more `0x13` give-item events, **Then** every event appears in `team.itemTransfers[]` with `fromSlot`, `toSlot`, `item: { id, name, unknown }`, `timeMs`, and `recipientFitClass` based on a mapping between the item's primary attribute (Int / Str / Agi / Universal) and the receiving hero's primary attribute.
3. **Given** an item is transferred to an ally whose hero has matching primary attribute, **Then** `recipientFitClass: "good"`. Mismatched attribute on a strictly-attribute-typed item: `recipientFitClass: "wrong"`. Items with no clear attribute fit (potions, generic charges): `recipientFitClass: "neutral"` (special label for the indifferent case).
4. **Given** a replay with no rescue-class items in any inventory at any death, **Then** `team.supportEvents[]` contains no `"missedSave"` rows for that fight (a missed save requires the item to *have existed*).
5. **Given** w3gjs cannot resolve the item id (`unknown: true`), **Then** the entry still appears, the `recipientFitClass` is `"unknown"`, and the diagnostics record the unresolved id (consistent with feature 002's existing unmapped-id reporting in `diagnostics.unmappedEntityIds`).

---

### User Story 3 — Resource Cooperation and Shared Control Posture (Priority: P1)

A reviewer wants to understand whether the team's economy worked as one machine or as four solo accounts. They want the report to: list every gold/lumber transfer between allies with timestamp, sender, recipient, amount, and a derived label of *what it likely enabled* — a tier-up, a base rebuild after a tower attack, or "no obvious purpose"; show whether full shared unit control was active in the lobby (`settings.fullSharedUnitControl`) and, if not, surface this as a "team did not enable shared control" finding for high-tier matches; and rank players by a simple "economic generosity" metric (lumber+gold sent / lumber+gold mined) so the over-greedy can be named.

**Why this priority**: Resource transfers (`0x51`) and shared control are already exposed in the analyzer output (`players[].resourceTransfers`, `settings.fullSharedUnitControl`). The work is annotation, not extraction. Low-cost, high-clarity — qualifies for P1 alongside US1 / US2.

**Independent Test**: Load `sample_replays/base_1.w3g.analysis.json` (already contains transfers) into the visualizer Team tab. Confirm: a chronological list of transfers each annotated with a likely purpose (heuristic, not certainty); a top-of-tab banner labelled "Shared control: ENABLED" or "Shared control: DISABLED"; a per-player "generosity score" sortable column showing `(gold sent + lumber sent) / (gold mined + lumber mined)` as a percentage.

**Acceptance Scenarios**:

1. **Given** the analysis JSON contains `players[].resourceTransfers`, **When** the analyzer runs, **Then** `team.resourceCooperation.transfers[]` mirrors the per-player transfers but adds an `purposeHint` field with values `"tierUpAssist" | "baseDefense" | "lateGameTopUp" | "none"` derived from heuristic timing windows (transfer within ±60s of the recipient's tier-up keyword event = `"tierUpAssist"`, etc.).
2. **Given** the lobby setting `fullSharedUnitControl` is `true`, **Then** `team.sharedControl.enabled` is `true`. When `false`, `team.sharedControl.enabled` is `false` and the finding `team.findings[]` includes `"sharedControlDisabled"`.
3. **Given** the analyzer can compute resources mined (from existing aggregate fields, or — if not present — a documented YAGNI fallback noted in the plan), **Then** `team.resourceCooperation.generosity[]` lists each player with `{ slot, name, sentGold, sentLumber, generosityPercent }`. If the source data does not support `generosityPercent` on the first iteration, the field is `null` and a single-line `[NEEDS CLARIFICATION: total-mined source]` is recorded in `diagnostics`.
4. **Given** a 1v1 replay loads, **Then** `team.resourceCooperation.transfers[]` is empty, `team.sharedControl` is `null`, no "sharedControlDisabled" finding is emitted, and the Team tab shows the same 1v1 empty state as US1.
5. **Given** a transfer purpose cannot be classified, **Then** `purposeHint` is `"none"`. The analyzer never throws on classifier failure; it backs off to `"none"`.

---

### User Story 4 — Tactical Cohesion: Focus Fire, Pings, Kill Participation (Priority: P2)

A reviewer wants the deeper combat-tactics layer that requires per-event spatial / target inspection: in each detected battle, did the team focus fire on one target (and which one), or did the four armies attack four different units? Were minimap pings (`0x68`) sent during the fight, and if so, did the addressed ally re-task their army within a reasonable reaction window? What was each player's share of the team's total kills (kill participation, KP%)?

**Why this priority**: P2 because (a) US1–US3 already deliver a usable report and (b) focus-fire and ping-reaction extraction depend on richer event consumption (right-click target ids, attack-move target, minimap signals) that is not currently surfaced by the processor. The analytics are valuable but their cost is materially higher than US1–US3, so they ship as the second wave once the core team-tab is in place.

**Independent Test**: With the Team tab open on a replay containing at least one fight with a clear focus target, the per-battle entry MUST display: `focusFire.dominantTargetSlot` (the enemy unit/hero most-attacked across the team in that battle window), `focusFire.cohesionPercent` (share of team attack actions targeting the dominant target), and a list of minimap pings during the battle window with their target coordinates and the eligible-responder ally's reaction within the next 15 in-game seconds (`responded: bool`). KP% appears in the per-player Team-tab row alongside APM.

**Acceptance Scenarios**:

1. **Given** an analysis JSON containing a `team.battles[]` entry, **When** the visualizer renders the Team tab, **Then** the battle row shows the dominant focus target's entity reference, the team's cohesion percent (0–100), and a list of contributing players ordered by attack count.
2. **Given** a minimap signal (`0x68`) is fired during a battle window, **Then** `team.battles[].pings[]` records `{ fromSlot, x, y, timeMs }` and a derived `respondedBySlot` set listing allies whose army re-tasked toward (x,y) within 15 seconds; allies whose army was already engaged elsewhere are surfaced as `engagedElsewhere: true` rather than `respondedBySlot: false` (the difference between "ignored" and "couldn't help").
3. **Given** the analyzer identifies kills (own-side minus enemy-side unit-count delta over the battle window, or direct kill-credit if w3gjs surfaces it; the chosen heuristic is documented in the plan), **Then** every player has a `team.players[].killParticipationPercent` field for the match and per-battle.
4. **Given** the input replay does NOT carry the spatial / target detail required for a metric (e.g., w3gjs does not expose attack-target ids in the version being parsed), **Then** the field is set to `null` and the diagnostics record a single named gap (`diagnostics.cohesionMetricGaps[]`); the rest of the report still ships. Partial degradation, not crash.
5. **Given** an FFA replay (no fixed teams), **Then** focus-fire and ping-reaction analyses are not emitted (Team tab shows the same "not applicable" empty state). No false flags.

---

### User Story 5 — Team Battle Summary with Trade-Efficiency Index (Priority: P2)

The reviewer wants a single, opinionated finishing section that ties everything together. For each battle (and for the match overall), they want: a Trade-Efficiency Index (TEI) computed as `(value of enemy units removed) / (value of own-side units lost)`, rendered both per player and per battle; a "Strategic blame" annotation that — when an individual player has a high own-Unit Score but the team's per-battle TEI is low and that player's army centroid was outside aura range during the fight — surfaces them as the likely cause regardless of personal performance; and an executive summary at the top of the Team tab listing the top 3 team errors of the match in ranked order ("Split engagement at 0:34:17", "Missed save at 0:42:09", "Greed transfer never sent at 0:51:30").

**Why this priority**: This is the finishing layer that makes the report read like a coach's note, not a list of metrics. P2 because it depends on US1 + US4 having shipped (you can't compute TEI without battle windows + kill estimates, you can't blame anyone without split-engagement detection). High polish, builds *on top of* the core.

**Independent Test**: Load `base_1.w3g.analysis.json` after this feature ships. Open the Team tab. Confirm: an executive summary with up to 3 ranked findings; per-battle TEI rendered per side and per player; for each flagged battle a "Likely cause" attribution citing the responsible player's slot + reason. Rebuild against `base_2.w3g.analysis.json` and confirm independent values, not bleed-through.

**Acceptance Scenarios**:

1. **Given** the analyzer has produced battles, transfers, support events and pings, **Then** the analysis JSON contains `team.battleSummary.tei[]` with one entry per battle: `{ battleIndex, teamSideTei, perPlayerTei[] }`. Per-player TEI is `(sum value enemy units removed weighted by this player's attack share) / (this player's units lost)` — exact formula recorded in the plan.
2. **Given** at least one battle is flagged for `splitEngagement.flagged === true` AND the per-battle TEI is below a documented threshold AND one specific player's centroid is the outlier farthest from the rest of the team, **Then** `team.battleSummary.attributions[]` records that player's slot with `reason: "splitEngagement"` and the battle index. If multiple cohesion misses contribute, multiple attribution rows are emitted (not collapsed).
3. **Given** the Team tab loads, **Then** the executive summary renders the top up-to-3 highest-severity team findings ranked by a documented weight scheme (severity = base weight × duration of the affected battle window, weights recorded in the plan).
4. **Given** the analyzer cannot estimate kills with sufficient confidence (per US4 acceptance #4), **Then** TEI fields are `null` and the executive summary excludes TEI-derived findings. Other findings (split engagement, missed saves, transfer purposes) still render.
5. **Given** the same replay is analyzed twice with the same `entity_names.json`, **Then** `team.*` fields are byte-identical (same content-determinism guarantee feature 002 already provides for the rest of the analysis output).

---

### User Story 6 — Existing Pipeline Behavior Is Unchanged (Priority: P1)

The Parser, Processor, and Visualizer all carry shipped features (001–005). A reviewer running the *new* feature against the already-committed fixtures expects every previously-passing test to still pass, every previously-rendered tab to still render, every previously-emitted JSON field to still appear with the same value, and the existing single-command deploy of the visualizer to still work in both production and development modes.

**Why this priority**: No team-cohesion field is worth a regression in the 102 tests already covering features 001–005. P1 by definition.

**Independent Test**: After this feature ships, the existing test suites — `cd parser && npm test` (parser), `cd processor && pytest` (processor, 67 cases), `cd visualizer && npm test` (visualizer, 35 cases) — MUST all continue to pass against both committed fixtures with no edits to existing assertions, only additive coverage. The four-tab visualizer must still render Summary / Timelines / Analysis / Map tabs identically; the new Team tab is in addition to, not replacing, existing content.

**Acceptance Scenarios**:

1. **Given** the analyzer is run on `base_1.w3g.json` and `base_2.w3g.json`, **When** the diff is taken between the previous and the new `*.analysis.json`, **Then** every previously-existing top-level key, sub-key, and value is unchanged (a strict superset is the only allowed diff).
2. **Given** the visualizer is brought up with the new `*.analysis.json`, **When** the user clicks Summary, Timelines, Analysis, Map in turn, **Then** each tab renders identically to feature 005's behavior.
3. **Given** an *old* `*.analysis.json` (one that does not contain the new `team.*` block) is loaded into the new visualizer, **Then** the Team tab renders the same "not applicable" empty state as a 1v1 replay, with copy that says the file pre-dates this feature; the other four tabs render normally.
4. **Given** every existing functional requirement of features 001–005 is enumerated in a checklist, **When** the new feature ships, **Then** every item passes against both committed fixtures.

---

### Edge Cases

- **No allies (1v1 or FFA)**: every team-level metric returns the empty-state object documented in US1/US3/US4. No crash, no NaN, no silent skip.
- **Replay with one team that has only one human + AI / observers**: AI slots are excluded from cohesion analytics; the lone human's cohesion section renders the same empty state.
- **Battle-window detection produces zero battles** (e.g., the players never meaningfully engaged): `team.battles[]` is `[]`, `tei[]` is `[]`, executive summary may be empty; the Team tab renders a "no team fights detected" copy rather than blank.
- **Very long match (>2 h)**: cohesion analytics still complete in under the documented analyzer time budget; no per-event O(n²) spatial scans.
- **Replay version where w3gjs does not expose right-click target coordinates**: spatial fields degrade per US4 acceptance #4 — `null` + diagnostic gap entry, not crash.
- **An ally is killed by neutral creeps / leaver disconnect, not a real fight**: this MUST NOT trigger a "missed save" finding. Battle-window detection requires sustained engagement between opposing player units, not neutral / creep deaths.
- **Item id is in `entity_names.json` but not yet attribute-classified**: `recipientFitClass: "unknown"` and a one-time entry in a new `diagnostics.itemAttributeGaps[]`.
- **Cooperative spell cast on an ally** (Spirit Link, Inner Fire, Bloodlust, Heal): present in `team.supportEvents[]` with `type: "supportSpellCast"` ONLY if the casting feature lands as part of US2 — otherwise out of scope and re-spec'd later.
- **Two transfers in close succession** that together cross the tier-up threshold: classified as a single `"tierUpAssist"` group, not two.
- **Re-running the analyzer on the same input**: outputs are byte-identical except for the existing volatile `parserParseTimeMs` field (per feature 002's invariant).

## Requirements *(mandatory)*

### Functional Requirements

#### Spatial cohesion (US1)

- **FR-001**: The Processor MUST detect "battle windows" — contiguous time ranges in which both opposing teams are actively dealing damage to each other (operationalised in the plan; the heuristic MUST be documented and reproducible). Each window has `startMs`, `endMs`, and the participating player slots per side.
- **FR-002**: For every battle window, the Processor MUST compute a per-player army centroid `{x, y}` in map coordinates at the start of the window. The centroid is the simple arithmetic mean of the player's commanded-unit positions at that instant.
- **FR-003**: For every pair of allies within a battle window, the Processor MUST compute the Euclidean centroid distance and emit it as `team.battles[i].alliedDistances[]`.
- **FR-004**: For each battle window, the Processor MUST identify the largest *active* support-aura radius across the team (e.g., Devotion Aura, Brilliance Aura, Unholy Aura), looked up from a small committed table keyed on hero / ability id. The radius is the threshold for the split-engagement flag.
- **FR-005**: The Processor MUST set `team.battles[i].splitEngagement.flagged = true` when the **maximum** allied centroid distance in that battle exceeds the active aura radius identified in FR-004. The flag carries `distance`, `referenceAuraId`, and the two flagged ally slots.
- **FR-006**: When no support aura is active in a battle (none of the team's heroes carries an aura ability), the Processor MUST fall back to a documented default radius (e.g., 900 units, the canonical Devotion Aura range) and record `splitEngagement.referenceAuraId: "default"`.

#### Support events and item-give (US2)

- **FR-007**: The Processor MUST consume the events stream from the parser output to extract `0x13` (give-item) events. Each event is emitted in `team.itemTransfers[]` with `{ fromSlot, toSlot, item: { id, name, unknown }, timeMs, recipientFitClass }`.
- **FR-008**: The Processor MUST maintain — co-committed with `entity_names.json` — an item-attribute table mapping item ids to their primary attribute (`int | str | agi | universal | none`). The table is referenced by FR-009; gaps in coverage are diagnosed, not fatal.
- **FR-009**: For every entry in `team.itemTransfers[]`, the Processor MUST set `recipientFitClass` based on the table from FR-008 and the recipient hero's primary attribute. Categories: `"good"` (attribute matches), `"wrong"` (attribute mismatches a strictly-typed item), `"neutral"` (item has no attribute affinity), `"unknown"` (item or hero attribute not in table — recorded in diagnostics).
- **FR-010**: The Processor MUST detect missed-save opportunities: for every hero death in a battle window, scan all allies' inventories at that timestamp for any entry in a committed rescue-item id list (Staff of Preservation `stwp`, Scroll of Healing, Scroll of Town Portal, etc.). When found AND the holder is within rescue-eligible range (radius documented in plan), emit `team.supportEvents[]` with `type: "missedSave"`.
- **FR-011**: The Processor MUST surface every entry in `team.supportEvents[]` and `team.itemTransfers[]` on the Visualizer's new Team tab, with timestamps, named entities, and ally name resolution. No raw slot ids without name annotation.

#### Resource cooperation and shared control (US3)

- **FR-012**: The Processor MUST forward / annotate every `players[].resourceTransfers[]` entry into `team.resourceCooperation.transfers[]` with an additional `purposeHint` field of `"tierUpAssist" | "baseDefense" | "lateGameTopUp" | "none"`. The classifier rule is documented in the plan and is a heuristic, not a guarantee.
- **FR-013**: The Processor MUST surface `team.sharedControl.enabled` directly from `settings.fullSharedUnitControl`. When `false`, the Processor MUST add `"sharedControlDisabled"` to `team.findings[]`.
- **FR-014**: The Processor MUST emit per-player `generosityPercent` rows in `team.resourceCooperation.generosity[]` derived from `(sentGold + sentLumber) / (totalMinedGold + totalMinedLumber)`. If the underlying mined-resource totals are not currently produced by feature 002's analyzer, the field is `null` and a single `[NEEDS CLARIFICATION]` line is recorded in diagnostics until the data source is settled in the plan.
- **FR-015**: The Visualizer's new Team tab MUST render the resource-cooperation table sortable by amount and by purpose, render the shared-control banner, and surface the generosity column with sensible empty-state copy when null.

#### Tactical cohesion (US4)

- **FR-016**: The Processor MUST consume right-click / attack-move events from the parser stream to extract attack-target slot ids in each battle window, and compute `team.battles[i].focusFire.dominantTargetSlot` (the most-attacked enemy slot) and `cohesionPercent` (share of team attack actions targeting that slot).
- **FR-017**: The Processor MUST extract minimap-signal events (`0x68`) within battle windows and emit `team.battles[i].pings[]` with `{ fromSlot, x, y, timeMs }`.
- **FR-018**: For every ping, the Processor MUST compute `respondedBySlot[]` (allies whose army centroid moved toward `(x,y)` within 15 in-game seconds) and `engagedElsewhereSlot[]` (allies whose army was actively dealing damage in another battle window at the time of the ping). The remainder are implicit non-responders.
- **FR-019**: The Processor MUST estimate per-player kill participation. The estimation method is recorded in the plan; if the available data does not support it, the field is `null` per FR-029.
- **FR-020**: The Visualizer's Team tab MUST render the focus-fire dominant target, cohesion percent, ping reactions per battle, and KP% per player.

#### Battle summary and attribution (US5)

- **FR-021**: The Processor MUST emit `team.battleSummary.tei[]` with per-battle Trade-Efficiency Index per side and per player. The exact formula is recorded in the plan; valid values are `≥ 0` numeric or `null` (insufficient data).
- **FR-022**: The Processor MUST emit `team.battleSummary.attributions[]` rows when a battle has `splitEngagement.flagged === true` AND its team-side TEI is below a documented threshold AND a single player's centroid is the outlier in that battle. The row identifies the player's slot, the battle index, and the reason (initial reason set: `"splitEngagement"`).
- **FR-023**: The Processor MUST emit `team.battleSummary.executive[]` — an ordered list (max 3) of the highest-severity findings. Severity weighting and the cap are recorded in the plan.
- **FR-024**: The Visualizer's Team tab MUST render the executive summary at the top of the tab, the per-battle TEI as a sortable column on the battle list, and the attribution rows attached to their corresponding battle row.

#### JSON output and contract preservation (US6)

- **FR-025**: All new fields MUST live under a single new top-level key `team` on the analysis JSON (peer of `match`, `players`, etc.). Existing top-level keys MUST NOT be reshaped, renamed, removed, or have their values' meaning changed.
- **FR-026**: When the input replay is 1v1, FFA, or otherwise has no allied pairs, the Processor MUST emit `team: { applicable: false, reason: <enum> }` and skip every per-battle / per-pair computation. The Visualizer MUST render a single empty-state explanation; not blank, not error.
- **FR-027**: An old `*.analysis.json` (produced before this feature ships) loaded into the new Visualizer MUST render every previously-shipped tab identically to feature 005 and a single "Team tab not available — file pre-dates feature 006" empty state on the Team tab. No crash, no schema mismatch.
- **FR-028**: The Processor's content-determinism guarantee from feature 002 MUST extend to the new `team.*` block: same input + same `entity_names.json` + same item-attribute table + same aura/rescue tables → byte-identical `team.*` output across runs.
- **FR-029**: For every metric that requires data the parser does not surface in the current `w3gjs` version, the field MUST be `null` and a structured entry MUST appear in `diagnostics.cohesionMetricGaps[]` describing the metric and the reason. Partial degradation, never an exception.
- **FR-030**: Every new external dependency (chart library, geometry helper, attribute table fetcher, etc.) MUST satisfy Principle VI's four "well-established" criteria (active maintenance ≤ 12 months, broad adoption, MIT/BSD/Apache-2.0/ISC, API-stability track record), OR carry a documented escape-hatch justification in the feature plan. A handwritten Euclidean distance is well within Principle VI's YAGNI escape hatch and does not require a library.
- **FR-031**: All new computation MUST live in the Processor layer; the Visualizer MUST treat `team.*` as read-only data. No recomputation in the browser. (Principle I.)
- **FR-032**: The new Team tab MUST satisfy Principle V's three preserve clauses already met by feature 005 (JSON-on-disk contract, single-command deploy in both production and development, zero runtime network egress).

### Key Entities

- **Battle window**: A `{ startMs, endMs, sides: [...] }` object describing a contiguous time range in which both opposing teams dealt damage. Detected by the Processor via a documented heuristic.
- **Army centroid**: Per-player `{x, y}` arithmetic mean of commanded-unit positions, computed at battle start and emitted under `team.battles[i].centroids[]`.
- **Aura coverage record**: A small committed table mapping hero / ability ids to their effective radius. Used by the Processor to set the split-engagement threshold per battle.
- **Item-attribute table**: A small committed mapping from item id → primary attribute. Co-located with `entity_names.json`. Drives `recipientFitClass`.
- **Rescue-item list**: A committed list of item ids treated as rescue tools (Staff of Preservation, Scroll of Healing, etc.). Drives missed-save detection.
- **Support event**: An entry in `team.supportEvents[]` describing a discrete cooperative or missed-cooperative action (`missedSave`, `supportSpellCast`, etc., extensible).
- **Item transfer**: An entry in `team.itemTransfers[]` derived from `0x13` give-item events, annotated with `recipientFitClass`.
- **Resource transfer with purpose hint**: An entry in `team.resourceCooperation.transfers[]` mirroring the per-player transfer with an added `purposeHint` heuristic label.
- **Ping**: An entry in `team.battles[i].pings[]` derived from `0x68` minimap-signal events, with response classification.
- **Trade-Efficiency Index (TEI)**: A per-battle, per-side, per-player number ≥ 0 (or `null`) representing `(value of enemy units removed) / (value of own-side units lost)`.
- **Attribution**: A `{ playerSlot, battleIndex, reason }` row identifying a player as the likely cause of a poor team-side TEI.
- **Executive finding**: A short text + structured payload entry in `team.battleSummary.executive[]`, ranked by a documented severity weight, capped at 3.
- **Team applicability flag**: `team.applicable: bool` plus `team.reason` enum for the empty-state path (1v1, FFA, no detected battles).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On `sample_replays/base_1.w3g.json`, the Processor produces `team.battles[]` with at least one battle window detected. The first battle's `splitEngagement.flagged` value matches the manual review of the replay (recorded in `quickstart.md` as the acceptance bar). False-positive and false-negative rates against the two committed fixtures are 0 — the spec ships only when the heuristic agrees with manual review on both replays.
- **SC-002**: The Processor's runtime on `base_1.w3g.json` (the 88-minute fixture) is **within 1.25× the existing analyzer runtime** measured before this feature lands. The benchmark + comparison method is documented in the plan.
- **SC-003**: The new `team.*` block adds **no more than 2× the size** of the existing analysis JSON for the largest fixture. (`base_1.w3g.analysis.json` is currently ~3 MB; the post-feature size MUST be < 6 MB.)
- **SC-004**: The processor test suite grows from 67 cases to **at least 67 + N**, where N is the number of new functional requirements that describe a discrete deterministic computation (FR-001 through FR-024 — at minimum 24 new fixture-based pytest cases, one per FR, more if a single FR has multiple branches).
- **SC-005**: 100% of feature 001–005 functional requirements pass on both committed fixtures after this feature ships — measured by a regression checklist that explicitly enumerates each prior FR (the same non-regression bar feature 005 set against features 003 / 004).
- **SC-006**: The Visualizer's Team tab renders fully on both committed fixtures within **150 ms** of perceived latency from tab click to first paint on commodity laptop hardware. (The Timelines tab's 100 ms budget set in feature 004 SC-005 is the precedent; Team is allowed 50 ms of additional headroom because per-battle rendering is heavier.)
- **SC-007**: Every metric that depends on parser data the current `w3gjs` version does not expose has a corresponding entry in `diagnostics.cohesionMetricGaps[]` AND a non-null fallback of "render the empty state" — measured by intentionally analyzing a replay produced by an older `w3gjs` version and confirming no exceptions, partial output, and a populated diagnostics list.
- **SC-008**: A reviewer encountering the Team tab for the first time on `base_1.w3g.analysis.json` can identify the team's most-impactful error of the match (the executive summary's top finding) **within 15 seconds** of opening the tab. Qualitative test: "is the top-of-tab finding visible without scrolling, and is it phrased as an actionable observation rather than a metric dump?"
- **SC-009**: A reviewer can compare two replays' team-cohesion findings side-by-side using the existing two-fixture flow (open one, swap the file, open the other). The Team tab's findings are clearly attributed to the loaded file — no bleed-through from the prior file. (Same property feature 005 enforces for zoom + filter state.)

## Assumptions

- **Spatial data availability**: The current `w3gjs` version exposes enough position data on right-click / attack-move / unit-train events to estimate army centroids. If a specific event class lacks coordinates in some replay versions, the affected metric falls back per FR-029. The plan inventories which events carry coordinates today.
- **Battle window detection is a heuristic, not a ground truth**: The Processor's "are these armies fighting?" classifier will mis-classify some edge cases (creep aggro, single-shot harass). As a starting sketch the plan will explore: bucket the match timeline at ~5-second resolution, mark a bucket as `engaged` when at least one player-vs-player attack action targets an opposing-team unit, treat a run of ≥ 3 consecutive `engaged` buckets as a battle window, and close the window after ≥ 2 consecutive non-engaged buckets. Single-shot harass and creep aggro are excluded by the run-length floor; the gap tolerance keeps a fight intact across brief disengagements. Final bucket size, run length, and gap tolerance are recorded in the plan and validated against both fixtures per SC-001.
- **Aura radius lookup is finite and committed**: Aura radii are constants in the WC3 game engine. A small committed table — co-located with `entity_names.json` — covers Devotion, Brilliance, Unholy, Vampiric, Endurance, and Trueshot at minimum. Adding to the table is a one-line PR; no plug-in framework is required (Principle III).
- **Item-attribute mapping is finite and committed**: Same shape as aura table — small JSON, one row per item id, regenerable from `w3gjs` if `w3gjs` ever surfaces attribute data.
- **Rescue-item list is finite and committed**: A small list (`stwp` Staff of Preservation, healing scrolls, town portal scrolls). New entries are added when a fixture surfaces them.
- **TEI uses unit gold-cost as the value proxy**: Killed unit gold cost is the simplest credible proxy for "value removed." The plan can refine to a dual gold + lumber + supply value if needed; spec only requires *a* documented monotonic value function. **Worked example (gold-only proxy):** a battle window in which the team kills 2 enemy Knights (245 g each) and 1 Paladin (425 g) and loses 3 Footmen (135 g each) yields a team-side TEI of `(2·245 + 425) / (3·135) = 915 / 405 ≈ 2.26`. Per-player TEI is `(this player's attack-action share within the window) · 915 / (this player's gold-cost units lost)`; a player contributing 50% of the team's attack actions and losing 1 Footman in that window has TEI `0.5·915 / 135 ≈ 3.39`. Edge cases (zero own-side losses → numerator value preserved as a winrate-style "∞" fallback or a documented cap; the choice is recorded in the plan).
- **Kill participation uses an estimated kill-credit heuristic**: w3gjs does not authoritatively credit kills. The plan documents the heuristic (e.g., last-attacker-with-line-of-sight); SC-001 covers fixture validation.
- **No per-player UI customization**: The Team tab is a single, fixed view per replay — no theme switcher, no metric toggle (beyond category filter on the existing Timelines tab). Customization, if it ever lands, is a future feature.
- **No cross-replay comparison**: Per feature 003 / 004 / 005's same boundary, the report is per-replay only. Multi-replay comparison views are out of scope.
- **No telemetry**: Per Principle V (c), nothing this feature ships sends data anywhere. The Team tab is rendered locally and computed locally.
- **Visualizer migration constraints from feature 005 still apply**: The Team tab is a new tab in the existing four-tab layout (becoming five tabs); the chart / interaction library choice continues to satisfy Principle V's three preserve clauses and Principle VI's four well-established criteria.

## Out of Scope

- **Cross-replay aggregation** (team trends across many matches). Per-replay only.
- **Real-time analysis** (mid-match overlay). The pipeline is JSON-on-disk after-the-fact.
- **Coaching prose** ("you should have done X"). The Team tab surfaces *findings*, not generated advice. The Analysis tab's eventual LLM-ready text export (feature TBD) is the natural home for prose; this spec does not commit it.
- **Map-tab integration of cohesion data** (rendering centroids on the actual map). The Map tab remains a placeholder per features 003 / 004 / 005's existing scope. Geometry data is in the JSON; rendering it on a tile map is a separate feature.
- **Cooperative spell casts on allies (Spirit Link, Inner Fire, Bloodlust, Heal)**: detection requires per-event spell-target inspection that may not be exposed in `w3gjs`'s current event shape. Listed in the requirements as a stretch goal; ships only if US2's data probe (recorded in the plan) confirms feasibility within this feature's scope. Otherwise re-spec'd later.
- **Modeling of unit movement between centroid samples**: the centroid is computed at battle start. Mid-battle drift, rotations, or arc movement are not modeled.
- **Per-team chat-channel sentiment / coordination quality**: chat is already surfaced in the Summary tab; analyzing its sentiment or coordination signal is a separate feature, not part of cohesion analytics.
- **Identifying disconnects, leaver penalties, drop-hacks**: orthogonal to team cohesion. The replay-side analysis surfaces what the players *did*, not why they stopped.
- **Multi-language UI in the Visualizer**: copy in the Team tab is English, consistent with features 003 / 004 / 005.
- **Persisting cohesion findings to disk between page loads**: in-session state only, mirroring feature 005's filter / zoom-state scope.
- **Mobile / touch-first layouts** for the Team tab. Desktop-first remains.
- **Automated upstream PRs to `w3gjs`** for missing event fields. If such a gap is found, the plan records it and someone files an upstream issue manually; the spec does not commit to that work.
