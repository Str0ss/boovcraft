// Pure formatting helpers for the Team tab.
// Vitest-tested in tests/teamFormat.test.ts.

export function formatDistance(units: number): string {
  return `${Math.round(units).toLocaleString()} u`;
}

export function formatTei(value: number | null): string {
  if (value === null) return '—';
  if (value >= 99) return '≥ 99';
  return value.toFixed(2);
}

export function formatPercent(value: number | null): string {
  if (value === null) return '—';
  return `${value.toFixed(1)}%`;
}

export function formatTimeMs(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${s.toString().padStart(2, '0')}`;
}

export function purposeHintLabel(hint: string): string {
  switch (hint) {
    case 'tierUpAssist':   return 'Tier-up assist';
    case 'baseDefense':    return 'Base defense';
    case 'lateGameTopUp':  return 'Late-game top-up';
    case 'none':           return '—';
    default:               return hint;
  }
}

export function fitClassLabel(cls: string): string {
  switch (cls) {
    case 'good':     return 'Good fit';
    case 'wrong':    return 'Wrong fit';
    case 'neutral':  return 'Neutral';
    case 'unknown':  return 'Unknown';
    default:         return cls;
  }
}

export function fitClassColor(cls: string): string {
  switch (cls) {
    case 'good':     return '#4ade80';  // green
    case 'wrong':    return '#f87171';  // red
    case 'neutral':  return '#9ca3af';  // gray
    case 'unknown':  return '#facc15';  // yellow
    default:         return '#9ca3af';
  }
}

export function findingKindLabel(kind: string): string {
  switch (kind) {
    case 'splitEngagement':       return 'Split engagement';
    case 'missedSave':            return 'Missed save';
    case 'lowTei':                return 'Lopsided trade';
    case 'sharedControlDisabled': return 'Shared control off';
    case 'wrongItemTransfer':     return 'Item misallocation';
    case 'ignoredPing':           return 'Ignored ping';
    default:                      return kind;
  }
}

// =========================================================================
// Feature 008 — Team Tab data drill-down helpers.
// Pure functions; covered by Vitest. See specs/008-team-tab-drill-downs/.
// =========================================================================

import type {
  Battle,
  EvidenceRef,
  KillEstimate,
  Ping,
} from '../types/analysis';

/**
 * Resolve the side a ping belongs to. Returns the slot ids of the
 * pinger's same-side teammates EXCLUDING the pinger themselves. Used
 * as the input set for the chip classifier.
 */
export function resolvePingSide(ping: Ping, battle: Battle): number[] {
  const a = battle.sides.teamA;
  const b = battle.sides.teamB;
  if (a.includes(ping.fromSlot)) return a.filter((s) => s !== ping.fromSlot);
  if (b.includes(ping.fromSlot)) return b.filter((s) => s !== ping.fromSlot);
  return [];
}

/**
 * Classify a ping's same-side teammates into three groups — those who
 * responded, those who were busy elsewhere, and those who simply
 * ignored it.
 *
 * The ignored set is computed as `sideMembers - responded - busy`.
 * No mutation; arrays are copied.
 */
export function classifyPingChips(
  ping: Ping,
  sideMembers: number[],
): { responded: number[]; busy: number[]; ignored: number[] } {
  const respondedSet = new Set(ping.respondedBySlot);
  const busySet = new Set(ping.engagedElsewhereSlot);
  const responded: number[] = [];
  const busy: number[] = [];
  const ignored: number[] = [];
  for (const slot of sideMembers) {
    if (respondedSet.has(slot)) responded.push(slot);
    else if (busySet.has(slot)) busy.push(slot);
    else ignored.push(slot);
  }
  return { responded, busy, ignored };
}

/**
 * Top-N kills sorted by victimValue descending. Stable on ties — the
 * analyzer's emission order is preserved for equal-value entries.
 */
export function topNKillsByValue(kills: KillEstimate[], n: number): KillEstimate[] {
  if (n <= 0) return [];
  // Stable sort by victimValue desc — Array.prototype.sort is stable per ES2019.
  const sorted = [...kills].sort((x, y) => y.victimValue - x.victimValue);
  return sorted.slice(0, n);
}

/**
 * Resolve an EvidenceRef to a DOM data-evidence-id string. Returns
 * null when the ref's kind is not in v1's closed enum (forward-compat
 * graceful degradation).
 */
export function dispatchEvidenceRef(ref: EvidenceRef): string | null {
  switch (ref.kind) {
    case 'battle':       return `battle-${ref.battleIndex}`;
    case 'supportEvent': return `supportEvent-${ref.index}`;
    case 'itemTransfer': return `itemTransfer-${ref.index}`;
    case 'globalFlag':   return `globalFlag-${ref.name}`;
    default:             return null;
  }
}
