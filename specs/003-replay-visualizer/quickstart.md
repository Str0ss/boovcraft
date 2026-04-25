# Quickstart: Replay Visualizer

**Feature**: 003 Replay Visualizer
**Branch**: `003-replay-visualizer`

This is the developer-facing quickstart for working on, and manually
reviewing, the replay visualizer.

## What you need

- A modern desktop browser (last two versions of Chrome, Firefox,
  Safari, or Edge).
- A working clone of this repository.
- Python 3.11+ and the Processor's dev environment from feature 002
  set up at least once (`pip install -e processor[dev]`).
- Node 18+ for regenerating Parser output (only needed if you wipe
  the committed `*.w3g.json` fixtures).

## Open the visualizer

Once `visualizer/` exists (post-implementation):

```bash
# from the repo root, on Linux:
xdg-open visualizer/index.html
# on macOS:
open visualizer/index.html
# on Windows (PowerShell):
Start-Process visualizer/index.html
```

Or simply double-click `visualizer/index.html` in a file manager.
The page must load and present its landing state with no console
errors.

If your browser blocks `file://` JavaScript by default (rare on
desktop), enable it for local files in browser preferences. No
server is required and none is supported.

## Generate the analysis JSON for the committed fixtures

The two committed fixtures are in `sample_replays/`. The visualizer
consumes Processor output, not Parser output, so generate analysis
JSONs first:

```bash
python processor/analyze.py sample_replays/base_1.w3g.json
python processor/analyze.py sample_replays/base_2.w3g.json
```

Outputs:

- `sample_replays/base_1.w3g.analysis.json` (~270 KB)
- `sample_replays/base_2.w3g.analysis.json` (~115 KB)

These files are `.gitignore`d (regenerable, deterministic). Re-run
the commands above whenever the analyzer or its mapping changes.

## Smoke-test the visualizer

1. Open `visualizer/index.html` (per "Open the visualizer" above).
2. Click the file picker and select
   `sample_replays/base_1.w3g.analysis.json`.
3. Verify the report renders within ~3 seconds.
4. Walk the §SC-004 manual checklist below.
5. Repeat with `sample_replays/base_2.w3g.analysis.json`.
6. Verify FR-009: with `base_1`'s report on screen, pick `base_2` and
   confirm the prior report is fully replaced (no leftover panels or
   names).

## Manual SC-004 review checklist (one pass per fixture)

Each line is one quick scan; total walkthrough should take under
five minutes per fixture.

- [ ] **Match header** is present with: outcome (or "Undetermined"),
      version + build, game type, matchup, map filename, duration.
- [ ] **Per-team grouping** is visible (a team header above each
      group of player panels).
- [ ] **Each player panel** has: name, accent color, race label, APM,
      winner badge if applicable.
- [ ] **Each player's build-order section** has Buildings / Units /
      Upgrades / Items, each rendered chronologically with display
      name + time.
- [ ] **Each player's hero section** has every hero used, with final
      level and chronological ability-learn list (ability name +
      time).
- [ ] **Each player's resource-transfers section** is present (with
      its empty state when applicable).
- [ ] **Each player's timeline** is present with axis ticks, five
      category rows, and markers; hovering or tabbing to a marker
      reveals the tooltip.
- [ ] **Chat section** is present (with its empty state for base_2).
- [ ] **Observers section** is present (base_1 has 1 observer,
      base_2 has 1 observer).
- [ ] **Unknown-entity marker**: locate base_1's `UNKN`-id hero
      entry; verify it renders in italic with `[?]` and a tooltip
      showing `"Unknown entity id: UNKN"`.
- [ ] **`match.winner === null`** renders as "Undetermined" (both
      committed fixtures have `winner: null`).

## Manual SC-003 spot-check (per fixture)

Time yourself locating each fact. Each should take ≤ 30 seconds:

- [ ] The winner (or "Undetermined").
- [ ] A named player's race.
- [ ] A named player's final APM.
- [ ] The time of a named hero's first ability learn.
- [ ] The total number of chat messages.

## Manual SC-005 timeline-completeness spot-check

For at least one player in each fixture:

- [ ] Pick the player. Open the analysis JSON in a text editor.
- [ ] Count the entries in
      `players[<n>].production.buildings.order` plus
      `production.units.order` plus `production.upgrades.order` plus
      `production.items.order` plus the sum of every
      `heroes[].abilityOrder.length`. Call this `N`.
- [ ] Count the markers across all five timeline rows in the
      rendered report for that player.
- [ ] Confirm the two counts are equal. (Allow zero tolerance — every
      timestamped event in the JSON appears as exactly one timeline
      marker.)

## Performance spot-check (SC-002)

On commodity laptop hardware:

- [ ] base_1 (~270 KB, ~88-minute 4v4): from clicking the picker to
      a fully-rendered report — under 3 seconds.
- [ ] base_2 (~115 KB, ~16-minute 3v3): under 1 second.

If a render takes materially longer, profile the hot path before
adding architectural complexity (per `research.md §R11`).

## Edge-case sanity checks

- [ ] Pick a non-JSON file (e.g., a `.txt`): the page shows the
      "Couldn't parse this file as JSON." message and stays in the
      landing state.
- [ ] Pick a `.w3g.json` Parser-output (not analysis): the page
      shows "This file doesn't look like a replay analysis." and
      stays in the landing state.
- [ ] Pick a malformed JSON file (e.g., truncated): the page shows
      "Couldn't parse this file as JSON." and stays in landing.
- [ ] Drop a folder onto the page: "Please select a single .json
      file." appears.

## Iterating during development

The visualizer is plain HTML + CSS + JS — there is nothing to build
and no watcher. Edit any of the three files in `visualizer/`, then
reload the page (Ctrl+R / Cmd+R). The current loaded analysis is not
preserved across reloads (no `localStorage` by design); re-pick the
file after a reload.

To debug, open the browser devtools (F12). The console MUST be silent
during a successful render (no warnings, no errors). Treat any console
output as a defect.
