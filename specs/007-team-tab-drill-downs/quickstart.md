# Quickstart: Team Tab Data Drill-Downs (Feature 007)

Manual walkthrough verifying feature 007's UI surfaces against `sample_replays/base_2.w3g.analysis.json` (3v3, 16-min match). Inherits the dev/prod bring-up from feature 006 — no setup changes.

## 0. Setup

Inherits from feature 006. `cd visualizer && npm run dev` opens http://127.0.0.1:5173.

## 1. Bring up + load fixture

1. Run `node parser/parse.js sample_replays/base_2.w3g` (skip if `*.w3g.json` already present).
2. Run `python3 processor/analyze.py sample_replays/base_2.w3g.json`.
3. Open http://127.0.0.1:5173 and pick `sample_replays/base_2.w3g.analysis.json`.
4. Click the Team tab.

## 2. Pings drill-down (US1)

For each of the 4 battles, find the Pings sub-section. Expected pings per battle: **44 / 17 / 18 / 0**. The 0-ping battle (battle 3) MUST either omit the sub-section or show "No pings" copy — never a misleading "Pings: 0".

For battle 0's first ping (around 4:20):
- Time formatted `mm:ss`.
- Pinger's resolved name visible (one of the 6 players).
- Three chip groups: **Responded** (green), **Busy** (yellow), **Ignored** (red).
- Chip names are player names (e.g., "Blayed#2127"), not raw slot ids.

Check: hovering a chip surfaces no broken state. Reload the page and verify the same data renders identically (idempotency).

## 3. Focus fire contributors (US2)

For battle 0:
- Header line: "Focus fire: 15% on BlackObelisk#2428".
- Below it: contributor list with each player's attack count.
- Expected order (descending): **Blayed#2127 (224) · tomulle#2354 (133) · kir#2613 (95) · BlackObelisk#2428 (76) · velimix#2364 (60) · SharkHbc#2882 (25)**.

If the order is wrong or any player is missing, the analyzer's `contributingPlayers` array deviates from the rendered list — file as a regression.

## 4. Kills drill-down (US3)

For battle 0, click the "Kills (60)" disclosure (or whatever affordance the implementation chose). Expected:
- Top-10 entries by `victimValue`, sorted descending.
- Each row: `mm:ss`, victim side ("teamA" or "teamB"), value (gold + lumber), credits as chips like "Blayed#2127: 50%".
- Truncation hint: "showing top 10 of 60" or similar.

Verify the highest-value kill appears first.

## 5. Per-player TEI surface (US4)

In the BattleSummary section, find the per-player TEI sub-table. Expected:
- One row per player (6 rows on `base_2`).
- All values render as "—" (em-dash).
- Hovering a "—" cell reveals a tooltip explaining the v1 limitation.

When feature 010 ships, the same UI MUST render numeric values without code change.

## 6. Geometry panel (US5)

For each battle, expand the "Geometry" disclosure. Expected:
- Centroids table: 6 rows (battle 0 / 1 / 3) or 4 rows (battle 2's smaller side). Each row shows `slot`, `x`, `y`, `source`.
- Per-side distance matrix: numeric distances formatted "X,XXX u".
- Centroids with `source === "missing"` (rare on `base_2`) render "—".

Spot-check: the maximum distance in the matrix matches `splitEngagement.distance` rendered earlier in the same battle row.

## 7. Attributions empty-state (US6)

In BattleSummary, find the Attributions sub-section. On `base_2`, `attributions === []` — expect explanatory copy:

> No strategic blame attributed (requires split engagement + lost trade + outlier centroid simultaneously).

The copy MUST be visible. Silent absence is a regression.

## 8. Click-to-scroll executive findings (US7)

In the Executive summary at the top of the tab, click "Split engagement at 4:05".

Expected behavior:
- Page smooth-scrolls to Battle 0's card.
- Battle 0 card pulses for ~2 seconds (outline / box-shadow flash).
- Pulse fades; card remains in view.

Repeat for findings 2 and 3 — they should land on Battle 3 (14:50) and Battle 1 (12:15) respectively.

If clicking does nothing or scrolls to the wrong battle, the `evidenceRef` dispatch is broken.

## 9. Non-regression — feature 006 surfaces (US8)

Re-execute every check in `specs/006-team-cohesion-analysis/quickstart.md` § 3.2 against the same `base_2` fixture. Every assertion MUST continue to pass:

- Executive summary top-3 still renders.
- Shared control banner still shows ENABLED/DISABLED.
- Battles list still has 4 rows.
- Resource cooperation tables still populate.
- Item gives still show 7 entries (all UNKN per known v1 limitation).
- Diagnostics still surface `cohesionMetricGaps`.

## 10. File-swap test (FR-024)

1. With base_2 loaded and Battle 0 expanded, switch the file picker to `base_1.w3g.analysis.json`.
2. Verify: Team tab navigates back to base_1 with all drill-downs collapsed (no "Battle 0 expanded" carrying over).
3. Switch back to base_2 — drill-downs are still collapsed (reset).

## 11. Performance — SC-003

Open DevTools Performance, click Record, click the Team tab on base_2 (clean page state). Stop recording when content paints. Inspect the paint event near the click — first paint MUST complete within **150 ms**.

Then expand all four battles' Geometry + Kills disclosures. Repeat the measurement — interaction latency MUST remain perceptible (< 100 ms per click).

## 12. Vitest sweep

```sh
cd visualizer && npm test
```

Expected: ≥ 56 cases (48 baseline + ≥ 8 new). Zero failures, zero edits to existing assertions.

## 13. Pre-006 file empty-state (UI-22 / FR-023)

Load a `*.analysis.json` that lacks the `team` block (regenerate with the analyzer at the pre-006 commit, or manually `jq 'del(.team)'`). The Team tab MUST show the "Team tab not available — pre-006 file" empty state, identical to feature 006's behavior. None of the new drill-downs may dereference the missing block.

## 14. Calibration checklist

When all sections of this quickstart pass cleanly:

- [ ] Pings drill-down visible on 3 of 4 battles.
- [ ] Focus-fire contributors list visible on all 4 battles.
- [ ] Kills drill-down expands without errors.
- [ ] Per-player TEI table renders 6 rows of "—".
- [ ] Geometry panel expands; coordinates and distance matrix visible.
- [ ] Attributions empty-state copy visible.
- [ ] All 3 executive findings navigate correctly with pulse.
- [ ] File swap clears expansion state.
- [ ] Feature 006 quickstart still passes.
- [ ] Vitest count ≥ 56, all green.
- [ ] First paint ≤ 150 ms.
- [ ] Pre-006 fallback still renders.

When all 12 checkboxes are checked, feature 007 is shippable.
