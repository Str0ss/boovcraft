import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import type { AnalysisJson } from '../src/types/analysis';

const REPO_ROOT = resolve(__dirname, '..', '..');
const FIXTURE_DIR = resolve(REPO_ROOT, 'sample_replays');

function load(name: string): AnalysisJson {
  const txt = readFileSync(resolve(FIXTURE_DIR, name), 'utf8');
  return JSON.parse(txt) as AnalysisJson;
}

export function loadBase1(): AnalysisJson {
  return load('base_1.w3g.analysis.json');
}

export function loadBase2(): AnalysisJson {
  return load('base_2.w3g.analysis.json');
}
