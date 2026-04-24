# Contract: Analyzer CLI

Describes the command-line interface of `processor/analyze.py`.

## Invocation

```text
python processor/analyze.py <parser-output.json>
```

Exactly one positional argument is accepted: a filesystem path to a
JSON document produced by the Parser layer (see `parser/DATA.md`).

No option flags, no environment variables, no stdin input, no
configuration file. Principle III applies: additional CLI surface is
forbidden until a concrete user need justifies it.

## Preconditions

1. The input path exists and is readable.
2. The input file is valid JSON.
3. The input JSON has the top-level key set documented in
   `parser/DATA.md` (`apm`, `buildNumber`, `chat`, `creator`,
   `duration`, `events`, `expansion`, `gamename`, `id`, `map`,
   `matchup`, `observers`, `parseTime`, `players`, `randomseed`,
   `settings`, `startSpots`, `type`, `version`, `winningTeamId`).
4. `processor/entity_names.json` exists, is valid JSON, and matches
   the shape in `mapping-shape.md`.
5. The target output path (derived per §Output below) is writable
   (or does not yet exist in a writable directory).

## Output

On success, a single JSON file is written, replacing any existing
file at the same path:

- If the input path ends in `.json`, the `.json` suffix is stripped
  and `.analysis.json` is appended:
  `sample_replays/base_1.w3g.json` → `sample_replays/base_1.w3g.analysis.json`.
- Otherwise, `.analysis.json` is appended directly.

The output file's structural contract is in `output-shape.md`.

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Analysis succeeded; output file was written. Diagnostics (if any) appeared on stderr and did NOT cause failure. |
| `1` | Generic failure — input path missing/unreadable, invalid JSON, malformed parser output (missing required keys or wrong types at the top level), mapping file missing/malformed, output path not writable. See stderr for the specific reason. No partial output file is left behind (if partial-write is possible, the analyzer writes to a temp file in the same directory and atomically renames it into place on success; on failure the temp file is removed). |
| `2` | CLI misuse — wrong number of arguments, `--help`-style parse error from `argparse`. Standard `argparse` behavior. |

## Stdout / stderr contract

- **Stdout**: silent on success. The analyzer does NOT echo the
  input, the output path, or progress indicators. A Visualizer or
  test harness can safely run the analyzer and rely on the output
  file being the sole signal.
- **Stderr**: reserved for operator-visible diagnostics and error
  messages.
  - Diagnostic (warn) lines have the form
    `[analyze] warn: unmapped <category> id "<id>"` and are emitted
    at most once per `(category, id)` tuple per run.
  - Error lines have the form `[analyze] error: <reason>` and
    accompany a non-zero exit.

## Idempotency

Running the analyzer twice with the same input produces
byte-identical output EXCEPT for the
`diagnostics.parserParseTimeMs` field, which is forwarded verbatim
from the parser's non-deterministic `parseTime`. See SC-007 and R9.

## No network, no spawn

The analyzer MUST NOT open network sockets, spawn subprocesses,
invoke `node`, load `w3gjs`, or read files outside:

1. The input parser-output file (read-only).
2. `processor/entity_names.json`, colocated with the analyzer
   (read-only).
3. The computed output path (write).

This is enforced socially (review, Principle I) rather than
sandboxed. Violations are blocker-severity in code review.
