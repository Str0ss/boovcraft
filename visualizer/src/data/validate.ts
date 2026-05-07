import type { AnalysisJson } from '../types/analysis';

const REQUIRED_TOP_LEVEL_KEYS = [
  'match', 'settings', 'map', 'players',
  'observers', 'chat', 'diagnostics',
] as const;

export const ERR_PARSE = "Couldn't parse this file as JSON.";
export const ERR_SHAPE = "This file doesn't look like a replay analysis.";
export const ERR_READ = "Couldn't read this file.";
export const ERR_NO_FILE = 'Please select a single .json file.';

export type ValidationResult =
  | { ok: true; value: AnalysisJson }
  | { ok: false; message: string };

export function validateAnalysisShape(parsed: unknown): ValidationResult {
  if (parsed === null || typeof parsed !== 'object' || Array.isArray(parsed)) {
    return { ok: false, message: ERR_SHAPE };
  }
  const obj = parsed as Record<string, unknown>;
  for (const key of REQUIRED_TOP_LEVEL_KEYS) {
    if (!(key in obj)) return { ok: false, message: ERR_SHAPE };
  }
  if (
    obj['match'] === null ||
    typeof obj['match'] !== 'object' ||
    Array.isArray(obj['match'])
  ) {
    return { ok: false, message: ERR_SHAPE };
  }
  if (!Array.isArray(obj['players'])) return { ok: false, message: ERR_SHAPE };
  if (!Array.isArray(obj['observers'])) return { ok: false, message: ERR_SHAPE };
  if (!Array.isArray(obj['chat'])) return { ok: false, message: ERR_SHAPE };
  return { ok: true, value: obj as unknown as AnalysisJson };
}
