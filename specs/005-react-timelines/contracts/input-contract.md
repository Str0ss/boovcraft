# Input Contract: Interactive Timelines (Feature 005)

## TL;DR

**The input contract is unchanged from feature 004.** This document
exists so reviewers don't have to read across feature directories to
verify that statement.

## Inherited contract

The migrated React visualizer consumes the same `*.analysis.json`
document the static visualizer of features 003 and 004 consumed:

- Top-level keys: `match`, `settings`, `map`, `players`, `observers`,
  `chat`, `diagnostics` (per `processor/DATA.md`).
- Per-player shape: `id`, `name`, `teamId`, `color`, `race`,
  `raceDetected`, `apm`, `isWinner`, `actions`, `groupHotkeys`,
  `heroes`, `production`, `resourceTransfers` (per
  `specs/004-visualizer-tabs/contracts/input-contract.md`).
- Per-player `actions` includes `apmTimeline`, `totals`, and
  `timedActions[]` (per feature 004's additive change, now part of
  the v1 contract).

No fields are added, removed, renamed, restructured, or made
optional in this feature. The Processor and Parser layers are
**not modified** by feature 005.

## Compatibility guarantees

- Per **Principle V (a) of constitution v1.1.0**: the migrated
  visualizer MUST consume `*.analysis.json` exactly as the static
  implementation did. A regenerated fixture must load successfully
  in the migrated visualizer with no Parser or Processor change
  required.
- Per **FR-025 of the spec**: the visualizer's input contract
  remains `*.analysis.json` documents produced by the existing
  Processor.
- Per **FR-024**: every functional requirement of feature 004's
  spec (FR-001 through FR-022) continues to hold.

## Verification

The non-regression check (T047 in feature 004's tasks, ported into
this feature's quickstart) is run in reverse: load a fixture that
the migrated visualizer renders, then load the same fixture in the
unmodified static visualizer of feature 004 (for example via
`git checkout <feature-004-merge> -- visualizer/`) — same data, same
result. Both visualizers MUST render the same Summary aggregations
and the same per-player histograms (with the new feature 005
brush + filter capabilities being additive — they don't change what
the histogram represents at any given zoom level).
