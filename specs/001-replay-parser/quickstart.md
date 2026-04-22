# Quickstart: Replay Parser

**Feature**: Replay Parser (`specs/001-replay-parser`)

This is the shortest path from a fresh clone to a parsed replay JSON
on disk. It is what the README for the parser layer will eventually
distill.

## Prerequisites

- Node.js 20 LTS installed and on `PATH`.
- Clone of this repository, on branch `001-replay-parser` or any
  branch where the parser has landed.

## Install

```bash
cd parser
npm install
```

This installs `w3gjs` (the sole runtime dependency). No other tools
are required.

## Parse a sample replay

From the repository root:

```bash
node parser/parse.js sample_replays/base_1.w3g
```

On success, the parser writes:

```
sample_replays/base_1.w3g.json
```

The file is the complete `w3gjs` parse output, serialized as JSON.
Open it with any JSON viewer, or pipe it into a downstream tool.

## Parse your own replay

```bash
node parser/parse.js /path/to/your-replay.w3g
```

The JSON appears next to the input as `/path/to/your-replay.w3g.json`.

## Understand the output

Read `parser/DATA.md`. It lists every field in the output JSON with
its type, origin (replay-native vs. derived by `w3gjs`), and
meaning. If you cannot find a field there, the documentation is
out of date — file a PR updating `DATA.md`.

## Verify behavior

Run the fixture-based test suite:

```bash
cd parser
npm test
```

The tests parse both committed replays
(`sample_replays/base_1.w3g`, `sample_replays/base_2.w3g`) and check
that the written JSON round-trips through `JSON.parse` and matches
the library's in-memory return value.

## Expected failures

- **Missing file**: non-zero exit, stderr names the missing path.
- **Not a `.w3g` file** (wrong format, truncated header): non-zero
  exit, stderr reports the parse error from `w3gjs`.
- **Output path not writable**: non-zero exit, stderr reports the
  write error.

In all failure cases no `.json` file is created (FR-005).

## What this tool is NOT

- NOT an analyzer. Computing APM, action counts, build orders, or
  anything else derived from the replay happens in the Processor
  layer, which is a separate feature. The parser's one job is to
  faithfully surface what `w3gjs` extracts.
- NOT a batch tool. One replay per invocation. If you need to parse
  many, drive the CLI from a shell loop — for now.
- NOT a server or daemon. It runs, writes a file, and exits.
