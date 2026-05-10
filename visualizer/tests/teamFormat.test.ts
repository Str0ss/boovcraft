import { describe, expect, it } from 'vitest';
import type { Battle, EvidenceRef, KillEstimate, Ping } from '../src/types/analysis';
import {
  classifyPingChips,
  dispatchEvidenceRef,
  fitClassColor,
  fitClassLabel,
  findingKindLabel,
  formatDistance,
  formatPercent,
  formatTei,
  formatTimeMs,
  purposeHintLabel,
  resolvePingSide,
  topNKillsByValue,
} from '../src/data/teamFormat';

describe('teamFormat', () => {
  describe('formatTei', () => {
    it('renders null as em-dash', () => {
      expect(formatTei(null)).toBe('—');
    });
    it('renders 99-cap as ≥ 99', () => {
      expect(formatTei(99)).toBe('≥ 99');
      expect(formatTei(99.5)).toBe('≥ 99');
    });
    it('renders normal values with 2 decimals', () => {
      expect(formatTei(1.5)).toBe('1.50');
      expect(formatTei(0)).toBe('0.00');
    });
  });

  describe('formatPercent', () => {
    it('renders null', () => {
      expect(formatPercent(null)).toBe('—');
    });
    it('renders with one decimal', () => {
      expect(formatPercent(13.456)).toBe('13.5%');
      expect(formatPercent(0)).toBe('0.0%');
    });
  });

  describe('formatTimeMs', () => {
    it('renders mm:ss', () => {
      expect(formatTimeMs(0)).toBe('0:00');
      expect(formatTimeMs(60_000)).toBe('1:00');
      expect(formatTimeMs(125_000)).toBe('2:05');
      expect(formatTimeMs(3_900_000)).toBe('65:00');
    });
  });

  describe('formatDistance', () => {
    it('rounds and adds units suffix', () => {
      expect(formatDistance(900.5)).toBe('901 u');
      expect(formatDistance(0)).toBe('0 u');
    });
  });

  describe('purposeHintLabel', () => {
    it('translates closed enum', () => {
      expect(purposeHintLabel('tierUpAssist')).toBe('Tier-up assist');
      expect(purposeHintLabel('baseDefense')).toBe('Base defense');
      expect(purposeHintLabel('lateGameTopUp')).toBe('Late-game top-up');
      expect(purposeHintLabel('none')).toBe('—');
    });
    it('passes through unknown values gracefully', () => {
      expect(purposeHintLabel('newKind')).toBe('newKind');
    });
  });

  describe('fitClassLabel & fitClassColor', () => {
    it('covers the closed enum', () => {
      for (const cls of ['good', 'wrong', 'neutral', 'unknown']) {
        expect(fitClassLabel(cls)).not.toBe(cls);
        expect(fitClassColor(cls)).toMatch(/^#/);
      }
    });
    it('passes through unknown enum values gracefully (forward-compat)', () => {
      expect(fitClassLabel('newKind')).toBe('newKind');
      expect(fitClassColor('newKind')).toMatch(/^#/);
    });
  });

  describe('findingKindLabel', () => {
    it('covers the v1 closed enum', () => {
      for (const kind of [
        'splitEngagement', 'missedSave', 'lowTei',
        'sharedControlDisabled', 'wrongItemTransfer', 'ignoredPing',
      ]) {
        expect(findingKindLabel(kind)).not.toBe(kind);
      }
    });
    it('passes through unknown values', () => {
      expect(findingKindLabel('futureKind')).toBe('futureKind');
    });
  });
});

// =========================================================================
// Feature 008 — drill-down helpers
// =========================================================================

const mkBattle = (sides: { teamA: number[]; teamB: number[] }): Battle => ({
  index: 0,
  startMs: 0,
  endMs: 60_000,
  sides,
  centroids: [],
  alliedDistances: [],
  splitEngagement: { flagged: false, distance: 0, referenceAuraId: 'default', referenceAuraName: 'default 900u', flaggedSlots: [] },
  focusFire: null,
  pings: [],
  kills: [],
});

const mkPing = (overrides: Partial<Ping>): Ping => ({
  fromSlot: 1, x: 0, y: 0, timeMs: 0, duration: 5,
  respondedBySlot: [], engagedElsewhereSlot: [],
  ...overrides,
});

describe('resolvePingSide', () => {
  it('returns teamA members minus pinger when pinger is on teamA', () => {
    const battle = mkBattle({ teamA: [1, 2, 3], teamB: [4, 5, 6] });
    const ping = mkPing({ fromSlot: 1 });
    expect(resolvePingSide(ping, battle).sort()).toEqual([2, 3]);
  });
  it('returns teamB members minus pinger when pinger is on teamB', () => {
    const battle = mkBattle({ teamA: [1, 2, 3], teamB: [4, 5, 6] });
    const ping = mkPing({ fromSlot: 5 });
    expect(resolvePingSide(ping, battle).sort()).toEqual([4, 6]);
  });
  it('returns empty when pinger is not on either side', () => {
    const battle = mkBattle({ teamA: [1, 2], teamB: [3, 4] });
    const ping = mkPing({ fromSlot: 99 });
    expect(resolvePingSide(ping, battle)).toEqual([]);
  });
});

describe('classifyPingChips', () => {
  it('classifies a mix correctly', () => {
    const ping = mkPing({ respondedBySlot: [2], engagedElsewhereSlot: [3] });
    const result = classifyPingChips(ping, [2, 3, 4, 5]);
    expect(result.responded).toEqual([2]);
    expect(result.busy).toEqual([3]);
    expect(result.ignored).toEqual([4, 5]);
  });
  it('all responded ⇒ ignored is empty', () => {
    const ping = mkPing({ respondedBySlot: [2, 3, 4] });
    const result = classifyPingChips(ping, [2, 3, 4]);
    expect(result.responded).toEqual([2, 3, 4]);
    expect(result.ignored).toEqual([]);
  });
  it('all ignored ⇒ responded and busy are empty', () => {
    const ping = mkPing({});
    const result = classifyPingChips(ping, [2, 3, 4]);
    expect(result.ignored).toEqual([2, 3, 4]);
    expect(result.responded).toEqual([]);
    expect(result.busy).toEqual([]);
  });
  it('responded set takes precedence over busy when overlap occurs', () => {
    // Edge: a slot listed in both arrays is classified as responded
    const ping = mkPing({ respondedBySlot: [2], engagedElsewhereSlot: [2] });
    const result = classifyPingChips(ping, [2]);
    expect(result.responded).toEqual([2]);
    expect(result.busy).toEqual([]);
  });
});

describe('topNKillsByValue', () => {
  const mkKill = (value: number, time = 0): KillEstimate => ({
    victimHandle: [0, 0],
    victimEntity: { id: 'UNKN', name: 'UNKN', unknown: true },
    victimSide: 'teamA',
    victimValue: value,
    killTimeMs: time,
    credits: [{ slot: 1, fraction: 1 }],
  });
  it('returns empty for empty input', () => {
    expect(topNKillsByValue([], 10)).toEqual([]);
  });
  it('returns empty for n <= 0', () => {
    expect(topNKillsByValue([mkKill(100)], 0)).toEqual([]);
  });
  it('returns all when n exceeds length', () => {
    const kills = [mkKill(50), mkKill(100), mkKill(75)];
    const out = topNKillsByValue(kills, 10);
    expect(out).toHaveLength(3);
    expect(out.map((k) => k.victimValue)).toEqual([100, 75, 50]);
  });
  it('truncates to top-N by value desc', () => {
    const kills = [mkKill(10), mkKill(50), mkKill(100), mkKill(25), mkKill(75)];
    const out = topNKillsByValue(kills, 3);
    expect(out.map((k) => k.victimValue)).toEqual([100, 75, 50]);
  });
  it('preserves emission order on ties (stable sort)', () => {
    const kills = [mkKill(50, 1), mkKill(50, 2), mkKill(50, 3)];
    const out = topNKillsByValue(kills, 5);
    expect(out.map((k) => k.killTimeMs)).toEqual([1, 2, 3]);
  });
});

describe('dispatchEvidenceRef', () => {
  it('dispatches battle kind', () => {
    expect(dispatchEvidenceRef({ kind: 'battle', battleIndex: 4 })).toBe('battle-4');
  });
  it('dispatches supportEvent kind', () => {
    expect(dispatchEvidenceRef({ kind: 'supportEvent', index: 2 })).toBe('supportEvent-2');
  });
  it('dispatches itemTransfer kind', () => {
    expect(dispatchEvidenceRef({ kind: 'itemTransfer', index: 0 })).toBe('itemTransfer-0');
  });
  it('dispatches globalFlag kind', () => {
    expect(dispatchEvidenceRef({ kind: 'globalFlag', name: 'sharedControlDisabled' }))
      .toBe('globalFlag-sharedControlDisabled');
  });
  it('returns null for forward-compat unknown kinds', () => {
    // Cast to bypass TypeScript's exhaustive check — simulating a future analyzer
    // emitting a new kind that this UI version does not recognize.
    const ref = { kind: 'futureKind', someField: 42 } as unknown as EvidenceRef;
    expect(dispatchEvidenceRef(ref)).toBeNull();
  });
});
