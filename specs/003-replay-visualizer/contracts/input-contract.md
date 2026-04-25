# Input Contract: Visualizer

**Feature**: 003 Replay Visualizer
**Branch**: `003-replay-visualizer`

## Definition

The visualizer's sole input is a single JSON file that conforms to the
Processor layer's analysis-output contract. The Visualizer does not
define this shape; it consumes it.

**Authoritative shape**: `processor/DATA.md` and
`specs/002-replay-analyzer/contracts/output-shape.md`.

A well-formed input is the output of:

```bash
python processor/analyze.py <some>.w3g.json
# → writes <some>.w3g.analysis.json
```

The visualizer does not invoke the analyzer. The user runs the analyzer
out-of-band, then loads the resulting `.analysis.json` via the picker
or by drag-and-drop.

## What the visualizer assumes

By contract:

- The root is a JSON object with seven top-level keys: `match`,
  `settings`, `map`, `players`, `observers`, `chat`, `diagnostics`.
- `match.winner` is either `null` or `{ "teamId": <number> }`.
- `players` is an array; each element has `id`, `name`, `teamId`,
  `color`, `race`, `raceDetected`, `apm`, `isWinner`, `actions`,
  `groupHotkeys`, `heroes`, `production`, `resourceTransfers`.
- Every entity reference (`{ id, name, unknown }`) carries a display
  `name` already; when `unknown === true`, `name === id`.
- Every timestamp is an integer milliseconds field
  (`timeMs` on production order entries, hero abilityOrder entries,
  resource transfers, chat messages; `durationMs` on the match object).
- `observers` is an array of strings (possibly empty).
- `chat` is an array of objects (possibly empty).

The visualizer relies on these guarantees and does NOT defensively
re-validate them per-row. Verifying the Processor's contract is the
Processor layer's responsibility (covered by feature 002's pytest
suite).

## What the visualizer validates

After `JSON.parse`, the visualizer performs a single shallow
structural check before rendering:

1. Parsed value is an object (not an array, not a primitive, not
   `null`).
2. All seven top-level keys are present.
3. `match` is an object.
4. `players`, `observers`, `chat` are arrays.

If any check fails, the visualizer aborts the load with the FR-004
error path:

> **"This file doesn't look like a replay analysis."**
> *(plain English, no stack trace, no JSON snippet)*

The pre-load landing state is restored. The user can pick / drop a
different file.

## What the visualizer does NOT do

- **Does NOT fetch `processor/entity_names.json`** or any remote
  resource (FR-008). All display names are read from inside the
  loaded analysis JSON itself.
- **Does NOT invoke the Parser or the Analyzer** at runtime
  (Principle I, Principle II's scope is parser-only and the Visualizer
  does no parsing).
- **Does NOT re-run any analysis or recompute APM, build orders, or
  hero-ability ordinals**. All of those values are read from the JSON
  verbatim.
- **Does NOT support inputs from other tools** (e.g., a third-party
  `.w3g` analyzer). Other input shapes will fail the seven-key check
  and surface the FR-004 error.

## Failure modes & messages

| Condition | User-facing message | Behavior |
|---|---|---|
| File is not valid UTF-8 / `FileReader` rejects | "Couldn't read this file." | Pre-load state restored. |
| `JSON.parse` throws | "Couldn't parse this file as JSON." | Pre-load state restored. |
| Top-level structural check fails | "This file doesn't look like a replay analysis." | Pre-load state restored. |
| Drag-dropped a directory or zero-length selection | "Please select a single .json file." | Pre-load state restored. |

In every failure path, no partial render appears. Any prior render is
cleared as part of the error-display step.
