// Time / number formatting helpers — ports of feature 003's formatTimeMs / formatInt.

export function formatTimeMs(ms: number, totalMs: number): string {
  const safeMs = Math.max(0, Math.floor(Number(ms) || 0));
  const totalSeconds = Math.floor(safeMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (totalMs < 3_600_000) {
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  }
  const hours = Math.floor(minutes / 60);
  const remMinutes = minutes % 60;
  return `${hours}:${remMinutes.toString().padStart(2, '0')}:${seconds
    .toString()
    .padStart(2, '0')}`;
}

export function formatInt(n: number): string {
  return Number(n).toLocaleString('en-US');
}
