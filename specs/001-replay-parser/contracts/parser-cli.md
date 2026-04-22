# Contract: Parser CLI

**Feature**: Replay Parser (`specs/001-replay-parser`)
**Layer**: Parser (Node.js)

This document defines the command-line interface of the parser. It is
the boundary across which the Processor layer (or a human operator)
drives the parser. The Parser layer MUST conform to this contract.

## Invocation

```bash
node parser/parse.js <path-to-replay>
```

- **Working directory**: Any. Paths are interpreted as provided
  (absolute or relative to the current working directory).
- **Arguments**: Exactly one positional argument, the filesystem path
  to a `.w3g` replay file. Any other argument count is an error.
- **Flags**: None in v1. No `--output`, no `--verbose`, no
  `--format`. (Introducing flags requires an explicit revisit under
  Principle III.)
- **Environment variables**: None consumed.
- **Stdin**: Not read.

## Success behavior

- **Preconditions**: The argument points to a file that `w3gjs` can
  parse.
- **Effects**:
  1. `w3gjs` parses the file in-process.
  2. The complete parse result is written to
     `<input-path>.json` via `fs.writeFileSync` using
     `JSON.stringify(result)`. Any existing file at that path is
     overwritten (FR-006).
- **Stdout**: Empty, or at most one single-line informational message
  naming the output path. Not relied upon by downstream consumers.
- **Stderr**: Empty.
- **Exit code**: `0`.

## Failure behavior

- **Triggers**:
  - Argument count is not exactly 1.
  - Input path does not exist or is not readable.
  - `w3gjs` throws during parse.
  - The output path is not writable (permissions, read-only disk).
- **Effects**:
  - No output `.json` file is created. If parsing fails mid-write,
    any partial file MUST be removed before exit (FR-005).
- **Stdout**: Empty.
- **Stderr**: A single-line diagnostic naming the input file and the
  underlying error message.
- **Exit code**: Non-zero. A single non-zero code (e.g., `1`) is
  sufficient for v1; finer-grained exit codes are out of scope.

## Idempotence

Running the parser twice on the same input, with no changes to
`w3gjs` in between, produces the same output file (modulo fields
that `w3gjs` itself may compute non-deterministically — those are
documented in `parser/DATA.md` if and when they are observed).

## Non-behavior (guarantees of what the parser does NOT do)

- Does NOT traverse directories or accept multiple inputs.
- Does NOT watch for file changes.
- Does NOT compute analytical values of its own (FR-003).
- Does NOT prompt for input.
- Does NOT read or write any file outside the input's directory.
- Does NOT read configuration files.
- Does NOT emit structured logs.
- Does NOT call into the Processor or Visualizer layers (Principle
  I).
