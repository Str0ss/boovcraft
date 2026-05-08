# Contract: Team Tab UI Surface

Structural contract for the Team-tab user-facing rendering. The authoritative field-level documentation of the underlying JSON lives in `specs/006-team-cohesion-analysis/data-model.md`; this contract captures the **MUST UI** invariants enforced by feature 007.

This is the **first UI-level contract** in the project. Features 003–006 surfaced UI rules inside their `quickstart.md` walkthroughs (qualitative); feature 007 makes them programmatically auditable so future features can extend the Team tab without silently dropping a drill-down.

## UI invariants

The following MUST hold in the rendered Team tab whenever an applicable analysis JSON is loaded:

### Pings

**UI-1.** For every `team.battles[i].pings[*]`, the rendered DOM MUST include a row showing all four data points: `timeMs` (formatted `mm:ss`), `fromSlot` (resolved to player name from `analysis.players[].name`), `respondedBySlot` (rendered as a list of player-name chips), `engagedElsewhereSlot` (rendered as chips). The "Ignored" set, computed as `(allies on the same side) − responded − busy`, MUST also be rendered as chips.

**UI-2.** A battle with `pings.length === 0` MUST either omit the pings sub-section entirely OR render an explicit empty-state copy. A header reading "Pings: 0" with no body content is a contract violation.

**UI-3.** The chip color coding for a ping's three groups MUST be visually distinct AND order-stable across battles: Responded comes first, Busy second, Ignored third. The exact hex / class names are not part of this contract.

### Focus fire

**UI-4.** When `battle.focusFire !== null`, the rendered DOM MUST include `contributingPlayers[*]` as a per-attacker breakdown — each entry showing `slot` (resolved to player name) and `attackCount`. The list MUST preserve the analyzer's sort (descending by `attackCount`).

**UI-5.** When `battle.focusFire === null`, the rendered DOM MUST include the explanatory copy referring to the corresponding `diagnostics.cohesionMetricGaps[]` reason (or a generic "no enemy unit-handle ownership" message). Silent absence is a contract violation.

### Kills

**UI-6.** When `battle.kills.length > 0`, the Team tab MUST provide an affordance to view the kills list (expand button, accordion, or always-on table — implementation choice). Hidden absence with no affordance is a contract violation.

**UI-7.** The kills list — when rendered — MUST be sorted by `victimValue` descending. When more than 10 entries exist, the rendering MAY truncate to the top-10; truncation MUST be indicated by a "showing top 10 of N" hint.

**UI-8.** Each kill row MUST surface: `killTimeMs` (`mm:ss`), `victimSide` (text "teamA" / "teamB"), `victimValue` (numeric), and every entry in `credits[*]` rendered as a chip showing `<player name>: <fraction × 100>%`.

### Per-player TEI

**UI-9.** For every `battleSummary.tei[i]`, the rendered DOM MUST include a per-player TEI sub-table with one row per `perPlayerTei[*].slot`. The table MUST render even when all values are `null`.

**UI-10.** A `null` per-player TEI value MUST render as "—" (em-dash). When a tooltip mechanism is available (cursor hover), the tooltip MUST explain the v1 limitation.

**UI-11.** A non-null per-player TEI value MUST render as a number using the existing `formatTei` helper. Forward-compat: future analyzer versions may produce non-null values; the UI MUST NOT crash or hide them.

### Geometry panel

**UI-12.** Each battle MUST provide an expandable Geometry section. Its expanded body MUST contain at minimum: a centroids table (one row per `battle.centroids[*]`) and a per-side allied-distance matrix.

**UI-13.** A `centroid` with `source === "missing"` MUST render `(x, y)` as "—" / "—" with a tooltip explaining "no commands in centroid lookback window" or equivalent.

**UI-14.** Distances MUST be formatted using the `formatDistance` helper from feature 006 (e.g., "8,830 u").

### Attributions empty-state

**UI-15.** When `team.battleSummary.attributions === []`, the rendered DOM MUST include an Attributions sub-section with explanatory copy. Silent absence is a contract violation.

**UI-16.** When `attributions.length > 0`, the existing rendering from feature 006 MUST continue (each attribution attached to its battle row). The empty-state copy MUST disappear.

### Executive summary click-to-scroll

**UI-17.** Each `executive[*]` finding MUST be rendered as a clickable element with a pointer-cursor affordance.

**UI-18.** On click, the page MUST execute `scrollIntoView({behavior: 'smooth', block: 'center'})` on the matching evidence target AND apply a brief visual highlight for ~2 seconds.

**UI-19.** An `evidenceRef.kind` value not in v1's enum (`battle | supportEvent | itemTransfer | globalFlag`) MUST render the finding as static text without a click handler. Forward-compat: future analyzer versions may emit new ref kinds; the UI MUST NOT crash.

### Non-regression

**UI-20.** Every rendering element from feature 006's `quickstart.md` § 3.2 MUST continue to appear. Drill-down content is *additive* — it appears within or below existing sections, not in their place.

**UI-21.** Loading a different file mid-session MUST clear all expansion state — no battle remains "expanded" carrying forward to the new replay.

**UI-22.** A pre-006 `*.analysis.json` (no `team` block) MUST continue to render the documented empty-state from feature 006. None of the new drill-down code may dereference a missing field.

## Test mapping

These UI invariants are partially testable via Vitest pure-logic helpers (the chip classifier, kills sorter, evidence-ref dispatcher) and partially via `quickstart.md` manual walkthrough. The Vitest tests cover correctness of the data transformations; the manual walkthrough covers the rendered-output side.

| Invariant | Coverage |
|---|---|
| UI-1, UI-2 | Vitest: chip classifier function. Manual: `quickstart.md` § Pings. |
| UI-3 | Manual: visual inspection. (No automated assertion on color hex.) |
| UI-4, UI-5 | Manual: `quickstart.md` § Focus fire. |
| UI-6, UI-7, UI-8 | Vitest: kills top-N sort + slice. Manual: `quickstart.md` § Kills. |
| UI-9, UI-10, UI-11 | Manual: visual inspection. |
| UI-12, UI-13, UI-14 | Manual: visual inspection. |
| UI-15, UI-16 | Manual: visual inspection on `base_2`. |
| UI-17, UI-18, UI-19 | Vitest: evidence-ref dispatcher (returns target id from a ref). Manual: click test in `quickstart.md`. |
| UI-20, UI-21, UI-22 | Manual: full feature 006 quickstart re-run + file-swap test. |

## Compatibility

- **Adding a new drill-down section** is non-breaking when it appears below existing sections and doesn't reshape DOM IDs that pre-existing CSS or test selectors rely on.
- **Removing a UI invariant** is breaking — invalidates this contract version and requires a feature-spec amendment.
- **Changing chip colors** (the hex values, not the order) is non-breaking — colors are intentionally outside the contract.
- **Tightening the top-N limit on kills** is non-breaking when the truncation hint is preserved per UI-7.
- **Forward-compat enum extensions** (new `evidenceRef.kind`, new `executive.kind`, new `purposeHint`) MUST be tolerated by the UI per UI-19 and the corresponding feature 006 enum-extension policy.
