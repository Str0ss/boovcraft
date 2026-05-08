# Quickstart: Event Extraction

This walkthrough verifies the feature 006 implementation end-to-end on
the two committed fixture replays. It covers (1) the extended
analyzer's coord-retention output, (2) the new `extract_events.py`
stage, and (3) the test suite.

All commands are run from the repository root.

## Prerequisites

- Python 3.11+ on PATH.
- The Processor's runtime dependencies installed:
  ```bash
  python -m pip install -e processor[dev]
  ```
  This installs `pandas`, `scikit-learn`, and `pytest` per the
  updated `processor/pyproject.toml`.
- The fixture replays' parser outputs already exist:
  - `sample_replays/base_1.w3g.json`
  - `sample_replays/base_2.w3g.json`
  (If they don't, regenerate with `node parser/parse.js
  sample_replays/base_1.w3g` and the same for `base_2`.)

## Step 1 — Re-emit the analyzer output (coord-retention check)

Run the extended analyzer on each fixture:

```bash
python processor/analyze.py sample_replays/base_1.w3g.json
python processor/analyze.py sample_replays/base_2.w3g.json
```

**Expected**: silent success, exit code 0, `*.analysis.json` rewritten
in place.

Spot-check the new coordinate fields with `jq`:

```bash
# A right-click action should now have x, y:
jq '.players[0].actions.timedActions[] | select(.category == "rightclick") | first(.)' \
   sample_replays/base_1.w3g.analysis.json
# Expected: { "timeMs": ..., "category": "rightclick", "x": ..., "y": ... }

# A hotkey-assignment action should NOT have x, y:
jq '.players[0].actions.timedActions[] | select(.category == "assigngroup") | first(.)' \
   sample_replays/base_1.w3g.analysis.json
# Expected: { "timeMs": ..., "category": "assigngroup" }   (no x, no y)

# A building placement in the production order should have x, y:
jq '.players[0].production.buildings.order[0]' sample_replays/base_1.w3g.analysis.json
# Expected: { "id": "...", "name": "...", "unknown": false, "timeMs": ..., "x": ..., "y": ... }
```

**Verify byte-additivity (SC-005)**. If you saved a copy of the
pre-006 analyzer output (e.g., from `main` before this branch), diff
the two files with the new keys filtered out:

```bash
jq 'walk(if type == "object" then del(.x, .y) else . end)' \
   sample_replays/base_1.w3g.analysis.json > /tmp/post006-stripped.json
# Expected: byte-identical to the pre-006 file.
```

## Step 2 — Run the events extractor

```bash
python processor/extract_events.py sample_replays/base_1.w3g.analysis.json
python processor/extract_events.py sample_replays/base_2.w3g.analysis.json
```

**Expected**: silent success, exit code 0, `*.events.json` files
written next to the analyzer outputs.

Spot-check the events document:

```bash
# Top-level keys:
jq 'keys' sample_replays/base_1.w3g.events.json
# Expected: ["diagnostics", "events", "match"]

# Distribution of event kinds:
jq '.diagnostics.eventCounts' sample_replays/base_1.w3g.events.json
# Expected: a map of kind → count, all 13 kinds present (some may be 0).

# An event of each inferred kind has its hedge label:
jq '[.events[] | select(.kind == "jointEngagement")][0].inferenceLabel' \
   sample_replays/base_1.w3g.events.json
# Expected: "jointEngagementCandidate"

# Determinism check — re-run and diff:
python processor/extract_events.py sample_replays/base_1.w3g.analysis.json
diff <(jq -S . sample_replays/base_1.w3g.events.json) \
     <(jq -S . sample_replays/base_1.w3g.events.json.bak 2>/dev/null \
       || jq -S . sample_replays/base_1.w3g.events.json)
# Expected: empty output (byte-identical).
```

## Step 3 — Run the test suite

```bash
python -m pytest processor/tests -v
```

**Expected**:
- Every feature 002 test still passes (`test_cli.py`, `test_entity_names.py`,
  `test_fixture_facts.py`, `test_output_shape.py`, `test_timed_actions.py`).
- The new feature 006 tests pass:
  - `test_coord_retention.py` — coord fields appear on the right
    categories and are absent on others.
  - `test_events_cli.py` — extract_events.py CLI surface and exit codes.
  - `test_events_shape.py` — top-level shape, kind discriminator,
    stable ids, diagnostics block.
  - `test_events_kinds.py` — at least one event of every kind that
    the underlying replay actually exhibits is emitted, no fabrication
    for kinds that didn't occur.
  - `test_events_helpers.py` — pure helper functions.
  - `test_events_determinism.py` — re-run produces byte-identical
    events JSON.

## Step 4 — Sanity-check the LLM narrative path (manual)

This is the SC-001 acceptance check. Hand the
`sample_replays/base_1.w3g.events.json` document to an LLM with a
prompt like:

> "Here is an events document for a 4v4 Warcraft 3 replay. Write a
> 6–10 sentence summary of the match. Cite event ids when you make
> specific claims. You do not have access to any other artifact."

**Expected**: the summary names at least one expo, one creeping
departure, one joint engagement, and one idle period (SC-001), with
event-id citations on each. No outcome vocabulary appears as a
factual claim (SC-008): the summary may say "consistent with an
attack" but not "Player B killed Player A's hero".

## Failure modes to verify

These should be smoke-tested when the work lands:

| Scenario | Command | Expected |
|---|---|---|
| Missing input file | `python processor/extract_events.py /nonexistent.json` | Exit 1, stderr `[extract_events] error: ...`, no output written. |
| Pre-006 analyzer output | `python processor/extract_events.py <a fixture without coord fields>` | Exit 1, stderr identifying the missing coord fields. |
| Wrong number of args | `python processor/extract_events.py` | Exit 2, argparse usage line. |
| Output already exists | (re-run a successful invocation) | Exit 0, output overwritten deterministically. |

## What this quickstart does NOT cover

- Visualizer integration. There is none — see plan §Summary. A
  follow-up feature will wire a "Story" tab or annotations onto the
  feature 005 visualizer.
- Schema-version field on the events document. v1 has none; future
  breaking shape changes will introduce one.
- Performance benchmarking. The 30 s budget in the plan's Technical
  Context is a generous upper bound; actual runs are typically <10 s.
  No benchmark suite ships with v1.
