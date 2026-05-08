// Pure helpers for the Map tab. Vitest-tested in tests/mapHelpers.test.ts.

import type {
  Battle,
  CentroidTimeline,
  Ping,
} from '../types/analysis';

export interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

const DEFAULT_VIEWPORT_HALF = 500;
const PADDING_RATIO = 0.1;

/**
 * Auto-fit bounding box over every coordinate observed in the timeline +
 * battle centroids + battle pings, with 10% padding.
 *
 * Degenerate single-point input returns a 1000x1000 box centered on it.
 */
export function computeBounds(timeline: CentroidTimeline | undefined, battles: Battle[]): Bounds {
  const xs: number[] = [];
  const ys: number[] = [];

  if (timeline) {
    for (const bucket of timeline.buckets) {
      for (const c of bucket.centroids) {
        if (c.x !== null && c.y !== null) {
          xs.push(c.x);
          ys.push(c.y);
        }
      }
    }
  }
  for (const b of battles) {
    for (const c of b.centroids) {
      if (c.x !== null && c.y !== null) {
        xs.push(c.x);
        ys.push(c.y);
      }
    }
    for (const p of b.pings) {
      xs.push(p.x);
      ys.push(p.y);
    }
  }

  if (xs.length === 0) {
    return { minX: -DEFAULT_VIEWPORT_HALF, maxX: DEFAULT_VIEWPORT_HALF,
             minY: -DEFAULT_VIEWPORT_HALF, maxY: DEFAULT_VIEWPORT_HALF };
  }

  let minX = Math.min(...xs);
  let maxX = Math.max(...xs);
  let minY = Math.min(...ys);
  let maxY = Math.max(...ys);

  // Degenerate (single coordinate) — expand to a sensible default
  if (minX === maxX && minY === maxY) {
    return {
      minX: minX - DEFAULT_VIEWPORT_HALF, maxX: maxX + DEFAULT_VIEWPORT_HALF,
      minY: minY - DEFAULT_VIEWPORT_HALF, maxY: maxY + DEFAULT_VIEWPORT_HALF,
    };
  }

  const width = maxX - minX;
  const height = maxY - minY;
  const padX = (width || DEFAULT_VIEWPORT_HALF * 2) * PADDING_RATIO;
  const padY = (height || DEFAULT_VIEWPORT_HALF * 2) * PADDING_RATIO;
  return { minX: minX - padX, maxX: maxX + padX, minY: minY - padY, maxY: maxY + padY };
}

/**
 * Pings active in [tMs - windowMs, tMs] across all battles, returned
 * with battle index for highlighting. Order is chronological.
 */
export function pingsInWindow(battles: Battle[], tMs: number, windowMs: number): Ping[] {
  const out: Ping[] = [];
  const lo = tMs - windowMs;
  for (const b of battles) {
    for (const p of b.pings) {
      if (p.timeMs >= lo && p.timeMs <= tMs) {
        out.push(p);
      }
    }
  }
  out.sort((a, b) => a.timeMs - b.timeMs);
  return out;
}

/**
 * Returns the human-readable label for the current scrub time relative
 * to detected battle windows. Returns null if not inside any battle.
 */
export function currentBattleLabel(battles: Battle[], tMs: number): string | null {
  for (const b of battles) {
    if (b.startMs <= tMs && tMs <= b.endMs) {
      return `Battle ${b.index}`;
    }
  }
  return null;
}

/** Format combat-food annotation: "32f / 14u". Edge case: zero values. */
export function formatCombatFood(food: number, count: number): string {
  return `${food}f / ${count}u`;
}
