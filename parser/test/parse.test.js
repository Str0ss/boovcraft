const { test } = require('node:test');
const assert = require('node:assert');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const W3GReplay = require('w3gjs').default;

const REPO_ROOT = path.resolve(__dirname, '..', '..');
const PARSE_JS = path.resolve(__dirname, '..', 'parse.js');
const FIXTURES = [
  path.join(REPO_ROOT, 'sample_replays', 'base_1.w3g'),
  path.join(REPO_ROOT, 'sample_replays', 'base_2.w3g'),
];

// parseTime is wall-clock parse duration inside w3gjs, so it differs across runs
// and is not content-derived. See specs/001-replay-parser/contracts/output-shape.md.
const VOLATILE_KEYS = new Set(['parseTime']);

function stripVolatile(obj) {
  const copy = { ...obj };
  for (const k of VOLATILE_KEYS) delete copy[k];
  return copy;
}

function runCli(inputPath) {
  return spawnSync(process.execPath, [PARSE_JS, inputPath], { encoding: 'utf8' });
}

function cleanOutput(p) {
  try { fs.unlinkSync(p); } catch (_) { /* not there, fine */ }
}

for (const fixture of FIXTURES) {
  test(`round-trip: ${path.basename(fixture)}`, async () => {
    const outPath = `${fixture}.json`;
    cleanOutput(outPath);

    const cli = runCli(fixture);
    assert.strictEqual(cli.status, 0, `cli failed with stderr: ${cli.stderr}`);
    assert.ok(fs.existsSync(outPath), `expected output at ${outPath}`);

    const fromFile = JSON.parse(fs.readFileSync(outPath, 'utf8'));
    assert.ok(fromFile && typeof fromFile === 'object' && !Array.isArray(fromFile),
      'output root must be a non-null object');

    const inMemory = await new W3GReplay().parse(fixture);
    const inMemoryJSON = JSON.parse(JSON.stringify(inMemory));

    // Top-level key sets must match exactly (contract: no injection, no stripping).
    assert.deepStrictEqual(
      Object.keys(fromFile).sort(),
      Object.keys(inMemoryJSON).sort(),
      'top-level keys must match w3gjs output exactly',
    );

    // Values must match after stripping fields that w3gjs computes non-deterministically.
    assert.deepStrictEqual(
      stripVolatile(fromFile),
      stripVolatile(inMemoryJSON),
      'parse output must deep-equal w3gjs return value (modulo volatile fields)',
    );

    cleanOutput(outPath);
  });
}

test('fails on non-existent input', () => {
  const bogusInput = path.join(REPO_ROOT, 'sample_replays', '__does_not_exist__.w3g');
  const bogusOutput = `${bogusInput}.json`;
  cleanOutput(bogusOutput);

  const cli = runCli(bogusInput);

  assert.notStrictEqual(cli.status, 0, 'cli should exit non-zero on missing input');
  assert.ok(cli.stderr.length > 0, 'cli should emit a stderr diagnostic');
  assert.strictEqual(fs.existsSync(bogusOutput), false,
    'no output file should be created on failure');
});

test('rejects wrong argument count', () => {
  const zeroArg = spawnSync(process.execPath, [PARSE_JS], { encoding: 'utf8' });
  assert.notStrictEqual(zeroArg.status, 0);
  assert.ok(zeroArg.stderr.length > 0);

  const twoArgs = spawnSync(process.execPath, [PARSE_JS, 'a', 'b'], { encoding: 'utf8' });
  assert.notStrictEqual(twoArgs.status, 0);
  assert.ok(twoArgs.stderr.length > 0);
});
