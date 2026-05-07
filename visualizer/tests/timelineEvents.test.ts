import { describe, expect, it } from 'vitest';
import {
  bucketEvents,
  chooseBucketWidth,
  collectPlayerEvents,
  filterBuckets,
  MIN_BUCKET_MS,
} from '../src/data/timelineEvents';
import { makeAllEnabledFilterState } from '../src/state/types';
import { loadBase1, loadBase2 } from './fixtures';
import { ALL_ACTION_CATEGORIES } from '../src/types/analysis';

describe('collectPlayerEvents', () => {
  it('combines timedActions + resourceTransfers and sorts by timeMs', () => {
    const a = loadBase1();
    for (const player of a.players) {
      const events = collectPlayerEvents(player);
      const expected =
        (player.actions.timedActions?.length ?? 0) + (player.resourceTransfers?.length ?? 0);
      expect(events.length).toBe(expected);
      for (let i = 1; i < events.length; i++) {
        expect(events[i - 1]!.timeMs).toBeLessThanOrEqual(events[i]!.timeMs);
      }
    }
  });

  it('per-category counts of action categories match actions.totals', () => {
    const a = loadBase2();
    for (const player of a.players) {
      const events = collectPlayerEvents(player);
      for (const cat of ALL_ACTION_CATEGORIES) {
        const observed = events.filter((e) => e.category === cat).length;
        expect(observed).toBe(player.actions.totals[cat] ?? 0);
      }
    }
  });
});

describe('chooseBucketWidth', () => {
  it('snaps to a "nice" interval', () => {
    const w = chooseBucketWidth(60_000, 1000);
    // For 60s visible / target ~100 bars, ideal bucket ≈ 600ms; nice snap is 1000.
    expect([500, 1000, 2000].includes(w)).toBe(true);
  });

  it('never falls below MIN_BUCKET_MS', () => {
    const w = chooseBucketWidth(1000, 4000);
    expect(w).toBeGreaterThanOrEqual(MIN_BUCKET_MS);
  });

  it('caps bar count for very long visible ranges', () => {
    const visibleMs = 60 * 60 * 1000; // 1 hour
    const viewportPx = 800;
    const w = chooseBucketWidth(visibleMs, viewportPx);
    expect(visibleMs / w).toBeLessThanOrEqual(1000);
  });
});

describe('bucketEvents', () => {
  it('produces stable bucket count', () => {
    const a = loadBase1();
    const player = a.players[0];
    if (!player) throw new Error('no player');
    const events = collectPlayerEvents(player);
    const startMs = 0;
    const endMs = a.match.durationMs;
    const bucketWidthMs = 60_000;
    const buckets = bucketEvents(events, startMs, endMs, bucketWidthMs);
    expect(buckets.length).toBe(Math.ceil(endMs / bucketWidthMs));
  });

  it('total event count across buckets equals events in visible range', () => {
    const a = loadBase2();
    const player = a.players[0];
    if (!player) throw new Error('no player');
    const events = collectPlayerEvents(player);
    const startMs = 60_000;
    const endMs = 300_000;
    const buckets = bucketEvents(events, startMs, endMs, 1000);
    const sum = buckets.reduce((s, b) => s + b.total, 0);
    const inRange = events.filter((e) => e.timeMs >= startMs && e.timeMs < endMs).length;
    expect(sum).toBe(inRange);
  });
});

describe('filterBuckets', () => {
  it('zeroes counts for disabled categories and recomputes total', () => {
    const a = loadBase2();
    const player = a.players[0];
    if (!player) throw new Error('no player');
    const events = collectPlayerEvents(player);
    const buckets = bucketEvents(events, 0, a.match.durationMs, 60_000);
    const fs = makeAllEnabledFilterState();
    fs.enabled.rightclick = false;
    const filtered = filterBuckets(buckets, fs);
    for (const b of filtered) {
      expect(b.counts.rightclick).toBeUndefined();
    }
    const totalAfter = filtered.reduce((s, b) => s + b.total, 0);
    const totalBefore = buckets.reduce((s, b) => s + b.total, 0);
    const rightclicks = buckets.reduce((s, b) => s + (b.counts.rightclick ?? 0), 0);
    expect(totalAfter).toBe(totalBefore - rightclicks);
  });
});
