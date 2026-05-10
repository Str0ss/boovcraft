# Quickstart: Team Cohesion Analysis (Feature 007)

Manual walkthrough for verifying feature 007 end-to-end against the two committed replay fixtures. This is the acceptance script for **SC-001 (zero false-flag rate on both fixtures)**, **SC-002 (analyzer runtime ≤ 1.25× baseline)**, **SC-003 (JSON output ≤ 2× baseline size)**, and **SC-006 (Team-tab paint ≤ 150 ms)**.

Numbers in `[CALIBRATE-T079]` placeholders are filled in during T079 (the final non-regression task) after the heuristic constants have been tuned per `research.md` § R5. Until T079 lands, the values below are predictions — discrepancies between prediction and observation drive constant tuning.

## 0. One-time setup (host machine)

```sh
# Parser — unchanged from feature 001
cd parser && npm install && cd -

# Processor — extended in feature 007 (no new runtime deps; pytest is the only dev dep)
cd processor && pip install -e '.[dev]' && cd -

# Visualizer (React app) — extended in feature 007
cd visualizer && npm install && cd -
```

Prerequisites: Node.js 20+, Python 3.11+, Docker Engine + Compose plugin (for production mode).

## 1. Regenerate parser + analysis JSON fixtures

```sh
node parser/parse.js sample_replays/base_1.w3g
node parser/parse.js sample_replays/base_2.w3g
python3 processor/analyze.py sample_replays/base_1.w3g.json
python3 processor/analyze.py sample_replays/base_2.w3g.json
```

The `*.w3g.json` and `*.analysis.json` files remain `.gitignore`d. After this step, both `*.analysis.json` files contain the new `team` top-level key.

Sanity check the Processor pytest is fully green:

```sh
cd processor && pytest && cd -
```

Expect: **≥ 91 passed** (67 baseline + ≥ 24 new feature 007 tests). Zero failures, zero edits to existing assertions.

## 2. Inspect the new `team.*` block via `jq`

Before opening the visualizer, eyeball the JSON. This is the fastest way to spot a misclassified battle window or an obviously-wrong split-engagement flag.

### 2.1 Top-level keys are exactly eight

```sh
jq 'keys' sample_replays/base_1.w3g.analysis.json
```

Expect:

```json
[
  "chat",
  "diagnostics",
  "map",
  "match",
  "observers",
  "players",
  "settings",
  "team"
]
```

### 2.2 `team.applicable` and battle counts

```sh
jq '.team.applicable, (.team.battles | length)' sample_replays/base_1.w3g.analysis.json
```

Expect (`base_1`, 4v4, 88-min match):

```text
true
[CALIBRATE-T079: expected battle count, e.g. 12]
```

Same for `base_2`:

```sh
jq '.team.applicable, (.team.battles | length)' sample_replays/base_2.w3g.analysis.json
```

Expect (`base_2`, 3v3, ~25-min match):

```text
true
[CALIBRATE-T079: expected battle count, e.g. 5]
```

### 2.3 Split-engagement flags

```sh
jq '[.team.battles[] | select(.splitEngagement.flagged) | { idx: .index, t: .startMs, dist: .splitEngagement.distance, aura: .splitEngagement.referenceAuraName }]' sample_replays/base_1.w3g.analysis.json
```

Expect on `base_1`: at least one flagged battle (the team's worst engagement of the match). Manual review against the recorded fight in the replay should agree with the flag — if a flagged battle does not visually correspond to a split engagement, drop the run-length floor in `team/battles.py` and re-run.

`[CALIBRATE-T079: expected number of flagged battles per fixture, with battle indices and rough mm:ss timestamps]`

### 2.4 Mirror invariants

For every `0x13` (give-item) event, exactly one `team.itemTransfers[]` entry:

```sh
# Count 0x13 events in the parser output:
jq '[.events[] | select(.id == 31) | .commandBlocks[]?.actions[]? | select(.id == 19)] | length' sample_replays/base_1.w3g.json

# Should equal:
jq '.team.itemTransfers | length' sample_replays/base_1.w3g.analysis.json
```

The two numbers MUST match exactly (invariant 16). For `base_2`: expect `7` give-item events on each side per the Phase-0 probe.

For every `0x51` resource transfer, exactly one annotated transfer:

```sh
jq '[.players[].resourceTransfers[]] | length' sample_replays/base_1.w3g.analysis.json
jq '.team.resourceCooperation.transfers | length' sample_replays/base_1.w3g.analysis.json
```

MUST match (invariant 17).

### 2.5 Diagnostics

```sh
jq '.diagnostics.cohesionMetricGaps, .diagnostics.itemAttributeGaps, .diagnostics.unmappedEntityIds' sample_replays/base_1.w3g.analysis.json
```

Expect on both fixtures: `cohesionMetricGaps` and `itemAttributeGaps` are `[]` after T002 / T004 / T006 ship. If non-empty after the lookup tables are committed, the gap is a real coverage hole — add the missing id to the relevant table and re-run.

### 2.6 Top-3 executive summary (the human-facing take)

```sh
jq '.team.battleSummary.executive[] | { rank, kind, summary }' sample_replays/base_1.w3g.analysis.json
```

Expect: 1–3 ranked findings. The top-1 should match what a coach watching `base_1` would call out as the team's biggest mistake. Discrepancy between prediction and observation drives severity-weight tuning per `research.md` § R3.

`[CALIBRATE-T079: expected top-3 findings on each fixture]`

## 3. Visualizer — development mode

```sh
cd visualizer && npm run dev
```

Vite prints `Local: http://127.0.0.1:5173/`. Open it.

**SC-005 dev check**: from `npm run dev` to "ready" log line ≤ 10 seconds.

### 3.1 File pick + four pre-existing tabs unchanged

Pick `sample_replays/base_1.w3g.analysis.json` via the file picker (or drag-drop).

Walk through the four pre-existing tabs (Summary, Timelines, Analysis, Map) and confirm:

- Summary tab renders identically to feature 005 — match header, per-team panels, action totals, group hotkeys, aggregated production / heroes / transfers, chat, observers.
- Timelines tab renders 8 player rows with histograms, brush-zoom works, category filter works, slider zoom works.
- Analysis tab still shows the "coming soon" placeholder (unchanged from feature 005).
- Map tab still shows the placeholder with the map filename.

**Non-regression invariant 37 holds visually.** Any visible change to the four pre-existing tabs is a regression bug.

### 3.2 New Team tab

Click the **Team** tab — fifth in the strip, between Timelines and Analysis.

**Top-of-tab — Executive summary**

Up to 3 ranked findings. Each finding shows a short coach-style headline (e.g., "Split engagement at 0:34:17"), a severity bar, and a click affordance that scrolls the matching battle / item-transfer / global-flag row into view.

**Per-battle list**

One row per `team.battles[i]`, in chronological order:

- Timestamp (`mm:ss` startMs) and duration (`mm:ss`).
- Sides as colored chips (`teamA` / `teamB` arbitrary labels).
- Split-engagement callout (when flagged): two ally names, the centroid distance, and the reference aura name + radius. A horizontal bar visualizes distance vs. aura radius.
- Focus-fire chip: dominant target name + cohesion percent. `null` focusFire renders a "no target ownership data" tooltip.
- Ping count, with hover tooltip showing the count breakdown by responded / engaged-elsewhere / ignored.
- Per-side TEI as a small ECharts bar (or `≥ 99` chip when sentinel-capped).
- Attribution rows (when present): named player + reason.

**Resource cooperation panel**

- Banner: `Shared control: ENABLED` (green) or `Shared control: DISABLED` (red).
- Annotated transfer list: chronological, with `purposeHint` chips (`tierUpAssist` / `baseDefense` / `lateGameTopUp` / `none`).
- Sortable generosity table: per player, sent gold + lumber, estimated mined gold + lumber, generosity %.

**Item transfer log**

Table of every `0x13` give-item event: sender → recipient, item name, fit class chip color-coded (`good` green, `wrong` red, `neutral` gray, `unknown` yellow).

### 3.3 Tab switch persistence

Switch back to Timelines, brush-zoom into a 3-minute window, switch to Team. Verify the Team tab renders normally (tab state isolated; brush state preserved).

Switch back to Timelines — brush-zoom is still active. Switch to Team again — Team tab content is the same. State isolation works.

### 3.4 Empty-state handling

Pick a different file mid-session — load `sample_replays/base_2.w3g.analysis.json`. Active tab resets to Summary; navigate to Team; verify the Team tab renders for `base_2` independently of `base_1` (no bleed-through).

### 3.5 Old-file empty state

Take a `*.analysis.json` from before feature 007 (the easiest source: `git stash` your current `.analysis.json`, run the pre-feature analyzer with `git stash` applied to remove the team-block code, regenerate, then unstash). Load it into the new visualizer. The four pre-existing tabs render normally; the Team tab shows:

```
Team tab not available — this file pre-dates feature 007.
Re-run python3 processor/analyze.py to regenerate it.
```

(If running this in development without stashing, T069's Vitest case covers the same path automatically.)

## 4. Visualizer — production mode

In a fresh terminal:

```sh
cd visualizer && docker compose up
```

This rebuilds the multi-stage image (longer on first run; warm cache on second) and serves nginx-on-alpine on `http://localhost:8080`.

**SC-005 production check**: `docker compose up` → first-meaningful-paint ≤ 30 seconds (warm cache).

Repeat all steps from § 3 against the production page. Verify identical behavior — production is just a static-bundle deploy of the dev page.

To stop: `Ctrl-C` then `docker compose down`.

## 5. Performance and size measurements

### 5.1 Analyzer runtime — SC-002

Measure baseline (the analyzer at the feature-005 commit) vs. feature-006 against `base_1.w3g.json`:

```sh
# Baseline (checkout HEAD before this feature)
time python3 processor/analyze.py sample_replays/base_1.w3g.json

# Feature 007
git checkout 007-team-cohesion-analysis
time python3 processor/analyze.py sample_replays/base_1.w3g.json
```

Ratio `feature_006_seconds / baseline_seconds` MUST be ≤ 1.25.

`[CALIBRATE-T079: actual baseline, actual feature-006 runtime, ratio]`

### 5.2 JSON output size — SC-003

```sh
ls -la sample_replays/base_1.w3g.analysis.json
```

Compared to the baseline size (~3 MB at feature 005), feature 007 MUST be < 6 MB.

`[CALIBRATE-T079: actual size in MB]`

### 5.3 Team-tab paint — SC-006

Open Chrome DevTools Performance tab, click **Record**, click the Team tab, click **Stop** when content is fully visible. Inspect the paint event nearest to the click.

`first paint ≤ 150 ms` on `base_1` against commodity laptop hardware. The 150-ms budget is 50 ms above feature 005's per-tab budget because per-battle list rendering is heavier than a single histogram.

`[CALIBRATE-T079: actual measured paint time]`

## 6. Manual review checklist

The qualitative check that drives SC-001 (zero false-flag rate). For each fixture:

| Check | Expected on `base_1` | Expected on `base_2` |
|---|---|---|
| `team.applicable` | `true` | `true` |
| `team.battles[].length` | `[CALIBRATE]` | `[CALIBRATE]` |
| Number of flagged split engagements | `[CALIBRATE]` | `[CALIBRATE]` |
| `team.findings` includes `"sharedControlDisabled"` | `[CALIBRATE-T079: depends on lobby setting]` | `[CALIBRATE]` |
| `team.itemTransfers.length` | matches `0x13` event count | `7` (per Phase-0 probe) |
| `team.resourceCooperation.transfers.length` | matches `players[].resourceTransfers[]` total | `8` (per Phase-0 probe) |
| `team.battles[i].pings.length` (sum across battles) | ≤ total `0x68` events; only those inside battle windows | ≤ 86 (per Phase-0 probe) |
| Top-1 executive finding kind | `[CALIBRATE]` (likely `splitEngagement` or `missedSave`) | `[CALIBRATE]` |
| Cohesion metric gaps | `[]` after T002/T004/T006 | `[]` |
| Manual: does each flagged battle visually correspond to a split engagement in the replay? | YES (zero false flags) | YES |
| Manual: does the top-3 executive summary read like a coach's summary? | YES | YES |

If ANY row disagrees with observation, tune the heuristic constants per `research.md` § R5 and re-run.

## 7. Non-regression — features 003–005 walkthroughs

Re-execute `specs/004-visualizer-tabs/quickstart.md` § 3–5 and `specs/005-react-timelines/quickstart.md` § 4–6 against the feature-006 visualizer with the **regenerated `*.analysis.json` files**. Every assertion in those walkthroughs MUST continue to pass without edits. (This is the human-driven side of T078 / T071.)

## 8. Calibration checklist for T079

Before declaring T079 complete:

- [ ] All `[CALIBRATE-T079]` placeholders in this file are filled with measured values.
- [ ] All checks in § 6 pass (zero false flags on both fixtures).
- [ ] All performance / size checks in § 5 pass.
- [ ] All non-regression walkthroughs in § 7 pass.
- [ ] If any heuristic constant was tuned to make the above pass, the new value is in `processor/team/<module>.py` AND its rationale is in `research.md` § R3.
- [ ] All test suites are green (T078).
- [ ] The PR description points reviewers at this file as the acceptance evidence.

When all eight checkboxes are checked, feature 007 is shippable.
