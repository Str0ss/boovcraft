import type { Player, TimelineCategory } from '../types/analysis';
import type { FilterState, ZoomState } from '../state/types';

export interface PlayerEvent {
  timeMs: number;
  category: TimelineCategory;
}

export interface Bucket {
  start: number;
  end: number;
  counts: Partial<Record<TimelineCategory, number>>;
  total: number;
}

const NICE_INTERVALS_MS = [
  250, 500, 1000, 2000, 5000, 10000, 15000, 30000,
  60000, 120000, 300000, 600000, 900000, 1800000, 3600000,
];

export const TARGET_BUCKET_PX = 10;
export const MIN_BUCKET_MS = 250;
export const MAX_BARS_HARD_CAP = 1000;

export function collectPlayerEvents(player: Player): PlayerEvent[] {
  const events: PlayerEvent[] = [];
  for (const ev of player.actions?.timedActions ?? []) {
    events.push({ timeMs: ev.timeMs, category: ev.category });
  }
  for (const t of player.resourceTransfers ?? []) {
    events.push({ timeMs: t.timeMs, category: 'transfer' });
  }
  events.sort((a, b) => a.timeMs - b.timeMs);
  return events;
}

export function chooseBucketWidth(visibleMs: number, viewportPx: number): number {
  const target = Math.max(8, Math.floor(viewportPx / TARGET_BUCKET_PX));
  const ideal = Math.max(1, visibleMs / target);
  let chosen = NICE_INTERVALS_MS[NICE_INTERVALS_MS.length - 1] ?? 60000;
  for (const v of NICE_INTERVALS_MS) {
    if (v >= ideal) {
      chosen = v;
      break;
    }
  }
  if (chosen < MIN_BUCKET_MS) chosen = MIN_BUCKET_MS;
  const bars = Math.ceil(visibleMs / chosen);
  if (bars > MAX_BARS_HARD_CAP) {
    const minWidth = visibleMs / MAX_BARS_HARD_CAP;
    for (const v of NICE_INTERVALS_MS) {
      if (v >= minWidth) return v;
    }
    return NICE_INTERVALS_MS[NICE_INTERVALS_MS.length - 1] ?? 60000;
  }
  return chosen;
}

export function bucketEvents(
  events: PlayerEvent[],
  startMs: number,
  endMs: number,
  bucketWidthMs: number,
): Bucket[] {
  if (bucketWidthMs <= 0 || endMs <= startMs) return [];
  const bucketCount = Math.max(1, Math.ceil((endMs - startMs) / bucketWidthMs));
  const buckets: Bucket[] = [];
  for (let i = 0; i < bucketCount; i++) {
    buckets.push({
      start: startMs + i * bucketWidthMs,
      end: Math.min(endMs, startMs + (i + 1) * bucketWidthMs),
      counts: {},
      total: 0,
    });
  }
  for (const ev of events) {
    if (ev.timeMs < startMs || ev.timeMs >= endMs) continue;
    const idx = Math.min(bucketCount - 1, Math.floor((ev.timeMs - startMs) / bucketWidthMs));
    const b = buckets[idx];
    if (!b) continue;
    b.counts[ev.category] = (b.counts[ev.category] ?? 0) + 1;
    b.total += 1;
  }
  return buckets;
}

export function filterBuckets(buckets: Bucket[], filterState: FilterState): Bucket[] {
  return buckets.map((b) => {
    const counts: Partial<Record<TimelineCategory, number>> = {};
    let total = 0;
    for (const [cat, n] of Object.entries(b.counts) as [TimelineCategory, number][]) {
      if (!filterState.enabled[cat]) continue;
      counts[cat] = n;
      total += n;
    }
    return { start: b.start, end: b.end, counts, total };
  });
}

export function clampBrushedRange(
  raw: { startMs: number; endMs: number },
  durationMs: number,
  minBucketMs: number = MIN_BUCKET_MS,
): ZoomState {
  let startMs = Math.max(0, Math.min(raw.startMs, raw.endMs));
  let endMs = Math.min(durationMs, Math.max(raw.startMs, raw.endMs));
  if (endMs - startMs < minBucketMs) {
    const center = (startMs + endMs) / 2;
    startMs = Math.max(0, center - minBucketMs / 2);
    endMs = Math.min(durationMs, startMs + minBucketMs);
    if (endMs - startMs < minBucketMs) {
      startMs = Math.max(0, endMs - minBucketMs);
    }
  }
  return { visibleStartMs: startMs, visibleEndMs: endMs };
}
