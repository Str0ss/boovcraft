#!/usr/bin/env node
const fs = require('fs');
const W3GReplay = require('w3gjs').default;

async function main() {
  const args = process.argv.slice(2);
  if (args.length !== 1) {
    process.stderr.write('usage: parse.js <path-to-replay.w3g>\n');
    process.exit(1);
  }
  const inputPath = args[0];
  const outputPath = `${inputPath}.json`;

  let result;
  try {
    const w = new W3GReplay();
    const events = [];
    w.on('gamedatablock', (block) => events.push(block));
    result = await w.parse(inputPath);
    result.events = events;
  } catch (err) {
    process.stderr.write(`${inputPath}: ${err.message || err}\n`);
    process.exit(1);
  }

  try {
    fs.writeFileSync(outputPath, JSON.stringify(result, null, 1) + '\n');
  } catch (err) {
    try { fs.unlinkSync(outputPath); } catch (_) { /* nothing to clean up */ }
    process.stderr.write(`${inputPath}: failed to write ${outputPath}: ${err.message || err}\n`);
    process.exit(1);
  }
}

main().catch((err) => {
  process.stderr.write(`unexpected error: ${err.message || err}\n`);
  process.exit(1);
});
