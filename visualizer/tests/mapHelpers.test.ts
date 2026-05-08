import { describe, expect, it } from 'vitest';
import type { Battle, CentroidTimeline } from '../src/types/analysis';
import {
  computeBounds,
  currentBattleLabel,
  formatCombatFood,
  pingsInWindow,
} from '../src/data/mapHelpers';

const mkBattle = (overrides: Partial<Battle> = {}): Battle => ({
  index: 0,
  startMs: 0,
  endMs: 60_000,
  sides: { teamA: [1, 2], teamB: [3, 4] },
  centroids: [],
  alliedDistances: [],
  splitEngagement: { flagged: false, distance: 0, referenceAuraId: 'default', referenceAuraName: 'default 900u', flaggedSlots: [] },
  focusFire: null,
  pings: [],
  kills: [],
  ...overrides,
});

const mkTimeline = (centroidsAtT0: Array<{ slot: number; x: number | null; y: number | null }>): CentroidTimeline => ({
  bucketWidthMs: 5000,
  buckets: [
    {
      tMs: 0,
      centroids: centroidsAtT0.map((c) => ({
        slot: c.slot, x: c.x, y: c.y,
        source: c.x === null ? 'missing' : 'commanded',
        combatFood: 0, combatUnitCount: 0,
      })),
    },
  ],
});

describe('computeBounds', () => {
  it('returns default viewport for empty input', () => {
    const b = computeBounds(undefined, []);
    expect(b.minX).toBeLessThan(0);
    expect(b.maxX).toBeGreaterThan(0);
    expect(b.minY).toBeLessThan(0);
    expect(b.maxY).toBeGreaterThan(0);
  });

  it('expands single-point input to a 1000-unit box', () => {
    const tl = mkTimeline([{ slot: 1, x: 100, y: 200 }]);
    const b = computeBounds(tl, []);
    expect(b.maxX - b.minX).toBeGreaterThanOrEqual(1000);
    expect(b.maxY - b.minY).toBeGreaterThanOrEqual(1000);
  });

  it('covers all centroids with at least 10% padding', () => {
    const tl = mkTimeline([
      { slot: 1, x: 0, y: 0 },
      { slot: 2, x: 1000, y: 1000 },
    ]);
    const b = computeBounds(tl, []);
    expect(b.minX).toBeLessThanOrEqual(0 - 100);  // 10% of 1000
    expect(b.maxX).toBeGreaterThanOrEqual(1000 + 100);
    expect(b.minY).toBeLessThanOrEqual(0 - 100);
    expect(b.maxY).toBeGreaterThanOrEqual(1000 + 100);
  });

  it('includes ping coordinates from battles', () => {
    const battle = mkBattle({
      pings: [{ fromSlot: 1, x: -5000, y: 5000, timeMs: 0, duration: 5, respondedBySlot: [], engagedElsewhereSlot: [] }],
    });
    const b = computeBounds(undefined, [battle]);
    expect(b.minX).toBeLessThanOrEqual(-5000);
    expect(b.maxY).toBeGreaterThanOrEqual(5000);
  });

  it('excludes null centroids from bounds', () => {
    const tl = mkTimeline([
      { slot: 1, x: null, y: null },
      { slot: 2, x: 100, y: 100 },
    ]);
    const b = computeBounds(tl, []);
    // Only [100, 100] participates → degenerate single-point fallback
    // expands to a 1000-unit box centered on (100, 100). The bounds MUST
    // contain the only valid coordinate.
    expect(b.minX).toBeLessThanOrEqual(100);
    expect(b.maxX).toBeGreaterThanOrEqual(100);
    expect(b.minY).toBeLessThanOrEqual(100);
    expect(b.maxY).toBeGreaterThanOrEqual(100);
  });
});

describe('pingsInWindow', () => {
  const mkPing = (timeMs: number) => ({
    fromSlot: 1, x: 0, y: 0, timeMs, duration: 5,
    respondedBySlot: [], engagedElsewhereSlot: [],
  });

  it('includes pings exactly at the boundaries', () => {
    const battle = mkBattle({ pings: [mkPing(85_000), mkPing(100_000)] });
    const out = pingsInWindow([battle], 100_000, 15_000);
    // 85_000 == lo (100k - 15k), 100_000 == hi
    expect(out).toHaveLength(2);
  });

  it('excludes pings outside the window', () => {
    const battle = mkBattle({ pings: [mkPing(50_000), mkPing(200_000)] });
    const out = pingsInWindow([battle], 100_000, 15_000);
    expect(out).toHaveLength(0);
  });

  it('aggregates pings across multiple battles', () => {
    const b1 = mkBattle({ index: 0, pings: [mkPing(95_000)] });
    const b2 = mkBattle({ index: 1, pings: [mkPing(98_000)] });
    const out = pingsInWindow([b1, b2], 100_000, 15_000);
    expect(out).toHaveLength(2);
  });

  it('returns chronologically sorted pings', () => {
    const battle = mkBattle({ pings: [mkPing(99_000), mkPing(95_000), mkPing(97_000)] });
    const out = pingsInWindow([battle], 100_000, 15_000);
    expect(out.map((p) => p.timeMs)).toEqual([95_000, 97_000, 99_000]);
  });
});

describe('currentBattleLabel', () => {
  it('returns null when between battles', () => {
    const battles = [mkBattle({ index: 0, startMs: 0, endMs: 60_000 })];
    expect(currentBattleLabel(battles, 100_000)).toBeNull();
  });

  it('identifies the active battle', () => {
    const battles = [
      mkBattle({ index: 0, startMs: 0, endMs: 60_000 }),
      mkBattle({ index: 1, startMs: 100_000, endMs: 160_000 }),
    ];
    expect(currentBattleLabel(battles, 30_000)).toBe('Battle 0');
    expect(currentBattleLabel(battles, 130_000)).toBe('Battle 1');
  });

  it('returns null at exact-edge moment between battles', () => {
    const battles = [mkBattle({ startMs: 0, endMs: 60_000 })];
    expect(currentBattleLabel(battles, 60_001)).toBeNull();
  });
});

describe('formatCombatFood', () => {
  it('formats zero values', () => {
    expect(formatCombatFood(0, 0)).toBe('0f / 0u');
  });

  it('formats normal values', () => {
    expect(formatCombatFood(32, 14)).toBe('32f / 14u');
  });

  it('formats large values', () => {
    expect(formatCombatFood(98, 50)).toBe('98f / 50u');
  });
});
