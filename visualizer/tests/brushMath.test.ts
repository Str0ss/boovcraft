import { describe, expect, it } from 'vitest';
import { clampBrushedRange, MIN_BUCKET_MS } from '../src/data/timelineEvents';

describe('clampBrushedRange', () => {
  it('passes through a normal in-range brush', () => {
    const out = clampBrushedRange({ startMs: 5_000, endMs: 10_000 }, 60_000);
    expect(out).toEqual({ visibleStartMs: 5_000, visibleEndMs: 10_000 });
  });

  it('flips reversed input (drag right-to-left)', () => {
    const out = clampBrushedRange({ startMs: 10_000, endMs: 5_000 }, 60_000);
    expect(out).toEqual({ visibleStartMs: 5_000, visibleEndMs: 10_000 });
  });

  it('clamps end past durationMs', () => {
    const out = clampBrushedRange({ startMs: 50_000, endMs: 80_000 }, 60_000);
    expect(out.visibleEndMs).toBe(60_000);
    expect(out.visibleStartMs).toBe(50_000);
  });

  it('clamps start before zero', () => {
    const out = clampBrushedRange({ startMs: -2_000, endMs: 5_000 }, 60_000);
    expect(out.visibleStartMs).toBe(0);
    expect(out.visibleEndMs).toBe(5_000);
  });

  it('expands a sub-MIN brush around the midpoint', () => {
    const out = clampBrushedRange({ startMs: 10_000, endMs: 10_050 }, 60_000);
    expect(out.visibleEndMs - out.visibleStartMs).toBeGreaterThanOrEqual(MIN_BUCKET_MS);
    const center = (out.visibleStartMs + out.visibleEndMs) / 2;
    expect(Math.abs(center - 10_025)).toBeLessThan(MIN_BUCKET_MS);
  });

  it('handles zero-width brush near zero edge', () => {
    const out = clampBrushedRange({ startMs: 0, endMs: 0 }, 60_000);
    expect(out.visibleStartMs).toBe(0);
    expect(out.visibleEndMs).toBeGreaterThanOrEqual(MIN_BUCKET_MS);
  });
});
