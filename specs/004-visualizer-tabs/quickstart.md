# Quickstart: Visualizer Tabs (Feature 004)

A short manual walkthrough for verifying the four-tab visualizer
end-to-end against the two committed replay fixtures. Run after
implementation; this is the primary acceptance check (per Principle
IV scope: presentation correctness is eyeball-checked, parsing /
analysis correctness is fixture-asserted).

## 0. One-time setup

From the repo root:

```sh
# Parser layer (Node) — install once. No change in this feature.
cd parser && npm install && cd -

# Processor layer (Python) — install once. No new deps in this
# feature; just makes the analyze CLI importable.
cd processor && pip install -e . && cd -
```

## 1. Regenerate analysis JSONs

After the Processor change is shipped, regenerate both fixtures so
the new `players[].actions.timedActions` field is present:

```sh
# Parser → produces *.w3g.json (already committed; re-run only if
# parser changed — feature 004 does not change it).
node parser/parse.js sample_replays/base_1.w3g
node parser/parse.js sample_replays/base_2.w3g

# Processor → produces *.w3g.analysis.json (regenerable; .gitignored)
python processor/analyze.py sample_replays/base_1.w3g.json
python processor/analyze.py sample_replays/base_2.w3g.json
```

Sanity-check the output:

```sh
# Confirm the new field exists for every player and is non-empty
python -c "
import json
for f in ('sample_replays/base_1.w3g.analysis.json',
          'sample_replays/base_2.w3g.analysis.json'):
    d = json.load(open(f))
    for p in d['players']:
        ta = p['actions']['timedActions']
        tot = p['actions']['totals']
        cat_counts = {}
        for a in ta:
            cat_counts[a['category']] = cat_counts.get(a['category'], 0) + 1
        for c, n in tot.items():
            if cat_counts.get(c, 0) != n:
                raise SystemExit(f'{f} player {p[\"id\"]}: {c} mismatch')
print('OK')
"
```

The Processor pytest suite will assert the same invariant
automatically:

```sh
cd processor && pytest && cd -
```

## 2. Open the visualizer

Double-click `visualizer/index.html` in your file manager (or
`xdg-open visualizer/index.html` / `open visualizer/index.html`).
The page loads from `file://` — no server, no network.

## 3. Smoke test against base_1

Pick `sample_replays/base_1.w3g.analysis.json` via the file picker
(or drag-drop, per feature 003 US3).

### Tab strip

- A horizontal tab strip is visible above the report content.
- Exactly four tabs: **Summary**, **Timelines**, **Analysis**, **Map**.
- **Summary** is active by default.

### Summary tab — verify

- Match header: version, duration (~88 minutes), 4v4, map path,
  winner = "undetermined".
- Eight per-team-grouped player panels.
- For player 0 (or any player you pick):
  - Action totals visible (rightclick, select, selecthotkey, ...).
  - Group hotkeys visible.
  - **Production aggregation**: rows like `Ziggurat (×N)`, no
    timestamps anywhere.
  - **Hero aggregation**: rows like
    `Crypt Lord — Level 4: Carrion Beetles (L1) → Impale (L1) →
    Impale (L2) → Spiked Carapace (L1)`, no timestamps.
  - **Resource transfer aggregation**: per-recipient + per-resource
    rows like `PlayerName: 500 gold (1 transfer)`, no timestamps.
- Chat section renders messages with sender / channel / time / text.
- Observers section lists every observer.
- The base_1 sentinel-hero entry (an entity flagged `unknown: true`
  somewhere in the analysis) is visible with its raw id and a
  marker.

### Timelines tab — verify

- Switch to the **Timelines** tab.
- All eight players are stacked top-to-bottom; each row spans the
  full content width (no two-column team layout).
- Each row is a histogram (bars), not a strip of points.
- A zoom control is discoverable and labelled (or has a tooltip).
- At default zoom: full match (0:00 → ~88:00) visible; bars are
  legible (none sub-pixel, none wider than 25% of the row).
- Zoom in: every row's bars get finer simultaneously; every row
  stays aligned on the time axis.
- Pan: every row pans together.
- Hover a bar: tooltip shows `start–end time`, per-category
  counts, total count.
- Minor events (rightclick / select / etc.) are visually
  distinguishable from major events (build / hero / transfer /
  buildtrain / ability / item).
- Switch to Summary, then back to Timelines: the zoom + pan state
  persists.

### Analysis tab — verify

- Switch to the **Analysis** tab.
- A clearly-labelled placeholder explains it's a future feature.
- Switch back to Summary: report still works.

### Map tab — verify

- Switch to the **Map** tab.
- Same shape — clearly-labelled placeholder.
- Optionally surfaces the loaded match's map name.
- Switch back to Summary: report still works.

## 4. Smoke test against base_2

Re-load `sample_replays/base_2.w3g.analysis.json` via the file
picker. Confirm:

- The page replaces the prior report cleanly (no base_1 data
  leaks).
- Match header shows ~16-minute duration, 3v3, "undetermined".
- Empty states render where applicable: no chat (empty state), no
  resource transfers for some players (empty state).
- Timelines tab fits the shorter duration; default zoom shows the
  full ~16 minutes; bars are legible.
- Loading a new file reset the zoom (full match visible) and the
  active tab (Summary).

## 5. Edge-case spot checks

- **Reload mid-zoom**: zoom in on base_1, then load base_2.
  Confirm zoom resets to full match for base_2.
- **Resize the window**: drop the window from full-screen to
  ~1280 px wide. The histogram bucket width re-snaps to keep
  bars legible — no sub-pixel bars after the resize.
- **Stub tab from cold load**: load base_2, immediately click the
  Map tab without visiting other tabs. Placeholder renders
  cleanly.
- **Unknown entity check**: locate base_1's flagged-unknown entry
  in the Summary aggregations. It appears with the raw id and a
  marker; switching to the Timelines tab keeps it represented.

## Acceptance

If every check above passes, feature 004's user-facing scope is
verified. Combined with the Processor pytest pass on the
`timedActions == totals` invariant for both fixtures, this is the
acceptance gate for the feature.
