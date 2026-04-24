# Quickstart — Replay Analyzer

This walkthrough exercises the end-to-end pipeline on a committed
fixture and covers the commands a developer runs during setup,
smoke-testing, and day-to-day work.

## Prerequisites

- Python 3.11 or newer on `PATH`.
- Node.js 20+ (only for running the Parser layer when regenerating
  fixtures; not needed for normal Analyzer work).
- This repository cloned, working directory at repo root.

## One-time setup

```bash
cd processor
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

Creates a virtual environment and installs `pytest` (the sole dev
dependency).

## Smoke test: analyze a committed fixture

From the repo root, with the venv active:

```bash
python processor/analyze.py sample_replays/base_1.w3g.json
```

Expected behavior:

- Exits `0`.
- Writes `sample_replays/base_1.w3g.analysis.json`.
- Produces no stdout output.
- Produces no stderr output (base_1 is fully covered by the
  mapping; unmapped-entity diagnostics would appear here if
  present).

Inspect the output:

```bash
python -c "import json, sys; d = json.load(open('sample_replays/base_1.w3g.analysis.json')); print(sorted(d))"
```

Should print:

```text
['chat', 'diagnostics', 'map', 'match', 'observers', 'players', 'settings']
```

## Running the test suite

```bash
cd processor
pytest -v
```

All tests should pass. Notable expectations:

- `test_analyze.py::test_topkeys_match_contract[base_1]`
- `test_analyze.py::test_every_entity_resolves_to_name[base_1]`
- `test_analyze.py::test_every_entity_resolves_to_name[base_2]`
- `test_analyze.py::test_rerun_is_byte_identical[base_1]`
- `test_analyze.py::test_chat_section_is_empty_array_when_no_chat[base_2]`
- `test_entity_names.py::test_mapping_shape_and_coverage`

## Regenerating a parser-output fixture

Only required if `base_2.w3g.json` needs to be (re)generated, or if
the Parser layer's output shape changes. Not a routine Analyzer
task.

```bash
cd parser
npm install             # once, if node_modules/ is empty
node parse.js ../sample_replays/base_2.w3g
# writes ../sample_replays/base_2.w3g.json
```

Commit the new `.json` alongside the `.w3g`.

## Regenerating `entity_names.json`

Only required after a `w3gjs` upgrade. Run the extraction task
(documented in `tasks.md` T00x once `/speckit.tasks` has produced
it) and review the diff:

```bash
git diff processor/entity_names.json
```

Coverage regressions (entries lost) require investigation before
merging. New entries (new game patch adds a hero/unit) are welcome;
smoke-test the fixture analyzers afterward.

## Using the analyzer from the future Visualizer layer

The Visualizer layer — not yet built — will consume the output of
this command by:

1. Loading `sample_replays/<replay>.w3g.analysis.json` for match
   data.
2. Optionally loading `processor/entity_names.json` directly if it
   needs display names for IDs that appear only in its own state
   (e.g., a filter control). Most rendering does not need the
   mapping because `name` is pre-attached to every entity reference
   in the analysis output.

The Visualizer MUST NOT re-invoke the Analyzer or Parser; it reads
pre-generated JSON artifacts per Principle I.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `[analyze] error: input file not found` | Wrong path or missing fixture | Check `ls sample_replays/` |
| `[analyze] error: mapping file missing or malformed` | `processor/entity_names.json` was deleted or broken | Restore from git; `git checkout processor/entity_names.json` |
| Many `[analyze] warn: unmapped <category> id "..."` lines | Replay contains entities outside mapped coverage (new patch, custom map, modded content) | If in declared coverage scope: add entries to `entity_names.json`; otherwise: ignore — the analysis is still valid |
| `pytest` collects zero tests | `pyproject.toml` not installed or venv inactive | `source .venv/bin/activate && pip install -e ".[dev]"` |
| Analysis output differs byte-for-byte across runs | Check `diagnostics.parserParseTimeMs` — it is expected to vary; no other field should | If other fields vary, file a bug — this violates SC-007 |
