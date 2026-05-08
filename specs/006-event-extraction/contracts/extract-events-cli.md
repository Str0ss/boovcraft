# Contract: `extract_events.py` CLI

Describes the command-line interface of `processor/extract_events.py`,
the second Processor-layer entry point introduced by feature 006.
Mirrors `specs/002-replay-analyzer/contracts/analyzer-cli.md`.

## Invocation

```text
python processor/extract_events.py <analyzer-output.json>
```

Exactly one positional argument: a filesystem path to a JSON document
produced by `processor/analyze.py` after the feature 006 coord-retention
extension landed (see `analyzer-coord-extension.md`).

No option flags, no environment variables, no stdin input, no
configuration file. Principle III applies: additional CLI surface is
forbidden until a concrete user need justifies it.

## Preconditions

1. The input path exists and is readable.
2. The input file is valid JSON.
3. The input JSON is the post-feature-006 analyzer-output shape
   (`processor/DATA.md` updated). Specifically: at least one
   `players[].actions.timedActions[]` entry MUST carry coordinate
   fields, OR (if the replay genuinely contained zero positioned
   actions, e.g., an instant disconnect) the metadata block must be
   present and valid. A pre-006 analyzer-output is detected by the
   extractor checking for the documented coord fields and exiting
   non-zero with a clear diagnostic (FR-033, US1 acceptance scenario
   5).
4. The target output path (derived per §Output below) is writable
   (or does not yet exist in a writable directory).

## Output

On success, a single JSON file is written, replacing any existing
file at the same path:

- If the input path ends in `.analysis.json`, those 14 characters are
  stripped and `.events.json` is appended:
  `sample_replays/base_1.w3g.analysis.json` → `sample_replays/base_1.w3g.events.json`.
- If the input path ends in `.json` but not `.analysis.json`, the
  `.json` suffix is stripped and `.events.json` is appended.
- Otherwise, `.events.json` is appended directly.

The output file's structural contract is in `events-output-shape.md`
(and the same content lives at `processor/EVENTS.md` for use without
spec context).

## Exit codes

| Code | Meaning |
|---|---|
| `0` | Extraction succeeded; output file was written. |
| `1` | Generic failure — input path missing/unreadable, invalid JSON, malformed analyzer output (top-level keys missing, wrong types), pre-006 analyzer output detected (no coord fields where expected), output path not writable. See stderr for the specific reason. No partial output file is left behind (the extractor writes to a temp file in the same directory and atomically renames it on success; on failure the temp file is removed). |
| `2` | CLI misuse — wrong number of arguments. Standard `argparse` behavior. |

## Stdout / stderr contract

- **Stdout**: silent on success. No progress indicators, no echoed
  paths. A test harness or downstream tool can rely on the output
  file being the sole signal.
- **Stderr**: reserved for operator-visible diagnostics and error
  messages.
  - Diagnostic (warn) lines have the form
    `[extract_events] warn: <message>` and are emitted at most once
    per condition per run. Examples: a player whose home derivation
    fell back to the secondary heuristic (R2), a teleport item id
    that resolved to `unknown=true` in the analyzer's mapping.
  - Error lines have the form `[extract_events] error: <reason>` and
    accompany a non-zero exit.

## Idempotency

Running the extractor twice with the same input produces
**byte-identical** output (FR-035 / SC-006). Unlike the analyzer's
output, the events output has no volatile field analogous to
`parserParseTimeMs` — the extractor does not record its own
wall-clock time on the document. (The diagnostics block records the
extractor version; that's a build-time constant, not wall-clock.)

## No network, no spawn, no upstream re-read

The extractor MUST NOT:

- Open network sockets.
- Spawn subprocesses.
- Invoke `node` or load `w3gjs` (Principle II).
- Read any file other than the one positional argument.

In particular, it MUST NOT re-open the parser-output `.w3g.json` or
the original `.w3g` (FR-036). All required information lives in the
analyzer output it was given.
