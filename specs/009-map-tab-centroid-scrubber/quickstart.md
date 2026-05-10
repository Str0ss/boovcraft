# Quickstart: Map Tab Centroid Scrubber (Feature 009)

Manual walkthrough verifying feature 009's scrubber against `sample_replays/base_2.w3g.analysis.json`.

## 0. Setup

Inherits from feature 008. Run `cd visualizer && npm run dev`, open http://127.0.0.1:5173.

## 1. Regenerate analysis JSON

```sh
node parser/parse.js sample_replays/base_2.w3g
python3 processor/analyze.py sample_replays/base_2.w3g.json
```

Inspect the output:

```sh
jq '.team.centroidTimeline.bucketWidthMs, (.team.centroidTimeline.buckets | length)' sample_replays/base_2.w3g.analysis.json
```

Expected: `5000` and approximately `198` (16:30 / 5s ≈ 198).

## 2. Open Map tab

1. Reload http://127.0.0.1:5173.
2. Pick `sample_replays/base_2.w3g.analysis.json`.
3. Click the **Map** tab (rightmost).

Expected:
- Time slider at top, currently at 0:00.
- An SVG canvas below, mostly empty (no commands yet at t=0).
- Two text labels: "Time: 0:00" and "no active battle".

## 3. Scrub through the match

Drag the slider to the right. Expected:

- Each bucket-step (5s), six colored dots reposition on the canvas.
- Each dot shows the player's nickname AND a two-line annotation `Xf / Yu` (combat food / combat units).
- At ~4:00 the indicator switches to "in Battle 0 (4:05–10:34)".
- Pings appear/disappear as the scrub time enters/exits the 15-second window after each ping.
- At ~10:30 (end of Battle 0), kir#2613's annotation shows roughly "29f / 10u" reflecting cumulative non-worker production.

## 4. Inspect specific moments

**At 0:30** — dots are mostly missing (no commands yet). Combat-food labels show `0f / 0u`.

**At 4:30** (inside Battle 0) — most dots visible; battle indicator shows "in Battle 0". Multiple ping markers visible from preceding 15s.

**At 11:00** — battle indicator shows "no active battle"; player food counts are higher than at 4:30.

**At end of match (~16:24)** — player food counts at maximum; some pings still in window if Battle 3 was active recently.

## 5. Combat-food spot check

Per US2 acceptance: at end of match, kir#2613 should have `combatFood ≈ sum(supply for unit in production.units.order if unit.id != "opeo")`. Compute manually:

```sh
jq '.players[] | select(.name == "kir#2613") | .production.units.summary' sample_replays/base_2.w3g.analysis.json
```

Sum the supply of non-`opeo` entries — that should match the final-bucket annotation in the UI.

## 6. Auto-fit viewport

Verify the dots are not bunched in one corner. The viewport should reasonably fill the canvas with ~10% margin around the dots' bounding box.

If you see all dots in the corner with massive empty space — `computeBounds` regression.

## 7. Empty-state for pre-008 file

Run `python3 processor/analyze.py sample_replays/base_2.w3g.json` with the analyzer at the feature-007 commit (or `jq 'del(.team.centroidTimeline)'` on a current file). Load the resulting file. Click Map tab.

Expected: empty-state copy "Map tab requires re-analyzing this replay with the post-feature-008 processor."

## 8. File-swap reset

1. Load `base_2`, scrub to 8:00.
2. Switch the file picker to `base_1.w3g.analysis.json`.
3. Verify Map tab now shows base_1 data with slider at position 0:00 (reset, not carrying 8:00 from base_2).

## 9. Non-regression — features 003-007

Re-run feature 008's quickstart §3. Every check still passes. Team tab still shows pings drill-down, kills, geometry, etc.

## 10. Performance

Drag slider rapidly end-to-end. UI should remain responsive (no UI lag).

## 11. Test sweeps

```sh
cd processor && pytest
cd visualizer && npm test
```

Expected: pytest ≥ 136 cases all green; vitest ≥ 69 cases all green.

## 12. Calibration checklist

- [ ] `team.centroidTimeline.bucketWidthMs === 5000` on regenerated `*.analysis.json`.
- [ ] Slider scrubs through ~198 buckets on `base_2` smoothly.
- [ ] Each visible dot shows nickname + `Xf / Yu` annotation.
- [ ] Battle indicator switches on entering/exiting battle windows.
- [ ] Ping markers appear in 15-second window.
- [ ] Auto-fit viewport keeps dots visible with margin.
- [ ] Empty-state for pre-008 files renders documented copy.
- [ ] File-swap resets scrub position to 0.
- [ ] All test suites green.
