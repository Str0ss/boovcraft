import { useEffect, useState } from 'react';
import type { AnalysisJson, Battle, CentroidTimeline, Ping, TimelineCentroid } from '../types/analysis';
import { computeBounds, currentBattleLabel, formatCombatFood, pingsInWindow } from '../data/mapHelpers';
import { formatTimeMs } from '../data/format';

const PING_WINDOW_MS = 15_000;
const DOT_RADIUS = 8;
const PING_RADIUS = 5;
const SVG_WIDTH = 800;
const SVG_HEIGHT = 600;

// Stable per-slot color palette mirroring WC3 player colors approximately.
const SLOT_COLORS: Record<number, string> = {
  1: '#ff0303', 2: '#0042ff', 3: '#1ce6b9', 4: '#540081',
  5: '#fffc01', 6: '#fe8a0e', 7: '#20c000', 8: '#e55bb0',
  9: '#959697', 10: '#7ebff1', 11: '#106246', 12: '#4e2a04',
};
const fallbackColor = '#9ca3af';

interface MapTabProps {
  analysis: AnalysisJson;
}

export function MapTab({ analysis }: MapTabProps) {
  const team = analysis.team;
  const [bucketIdx, setBucketIdx] = useState(0);

  // Reset scrub position when a new analysis loads (FR-021 / UM-11)
  useEffect(() => {
    setBucketIdx(0);
  }, [analysis]);

  // === Empty-state branches ==============================================
  if (!team) {
    return (
      <section style={emptyStateStyle}>
        <h2>Map tab not available</h2>
        <p>This analysis JSON pre-dates feature 006. Re-run <code>python3 processor/analyze.py</code> on the parser output.</p>
      </section>
    );
  }
  if (!team.applicable) {
    const message = (() => {
      switch (team.reason) {
        case 'noAllies':           return 'No teammates — Map analysis is not applicable to 1v1 replays.';
        case 'ffa':                return 'FFA replay — Map analysis applies to fixed-team modes only.';
        case 'noBattlesDetected':  return 'No team battles detected.';
        default:                   return 'Map analysis is not applicable to this replay.';
      }
    })();
    return (
      <section style={emptyStateStyle}>
        <h2>Map analysis unavailable</h2>
        <p>{message}</p>
      </section>
    );
  }
  const timeline = team.centroidTimeline;
  if (!timeline || timeline.buckets.length === 0) {
    return (
      <section style={emptyStateStyle}>
        <h2>Map tab requires re-analysis</h2>
        <p>This analysis JSON was produced before feature 008's centroid-timeline emitter. Re-run <code>python3 processor/analyze.py</code> on the parser output to regenerate it.</p>
      </section>
    );
  }

  // === Populated state ====================================================
  const safeIdx = Math.min(bucketIdx, timeline.buckets.length - 1);
  const bucket = timeline.buckets[safeIdx]!;
  const tMs = bucket.tMs;
  const bounds = computeBounds(timeline, team.battles);
  const battleLabel = currentBattleLabel(team.battles, tMs);
  const pings = pingsInWindow(team.battles, tMs, PING_WINDOW_MS);

  const playerName = (slot: number) =>
    analysis.players.find((p) => p.id === slot)?.name ?? `slot ${slot}`;

  // Project (x, y) in WC3 map units into SVG viewport coordinates.
  // Note: WC3's y increases northward (up), but SVG's y increases downward.
  // We flip y so the rendering feels "geographic" (north = up).
  const project = (x: number, y: number) => {
    const sx = ((x - bounds.minX) / (bounds.maxX - bounds.minX)) * SVG_WIDTH;
    const sy = SVG_HEIGHT - ((y - bounds.minY) / (bounds.maxY - bounds.minY)) * SVG_HEIGHT;
    return { sx, sy };
  };

  return (
    <section style={containerStyle}>
      {/* Time + battle indicator */}
      <div style={cardStyle}>
        <h2 style={cardHeaderStyle}>Map — Centroid scrubber</h2>
        <div style={{ display: 'flex', gap: '1rem', marginBottom: '0.5rem', alignItems: 'center' }}>
          <strong style={{ color: '#e5e7eb' }}>Time: {formatTimeMs(tMs)}</strong>
          <span style={battleLabel ? activeBattleStyle : noBattleStyle}>
            {battleLabel ? `🚩 in ${battleLabel}` : 'no active battle'}
          </span>
          <span style={{ color: '#6b7280', fontSize: '0.85rem' }}>
            bucket {safeIdx + 1} / {timeline.buckets.length}  •  pings in last 15s: {pings.length}
          </span>
        </div>
        <input
          type="range"
          min={0}
          max={timeline.buckets.length - 1}
          step={1}
          value={safeIdx}
          onChange={(e) => setBucketIdx(parseInt(e.target.value, 10))}
          style={{ width: '100%' }}
        />
      </div>

      {/* SVG canvas */}
      <div style={cardStyle}>
        <svg
          viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
          style={{ width: '100%', height: 'auto', background: '#0f172a', borderRadius: '0.4rem' }}
        >
          {/* Coordinate grid backdrop */}
          <GridLines bounds={bounds} project={project} />

          {/* Pings (last 15s) */}
          {pings.map((p, i) => (
            <PingMarker key={`p${i}`} ping={p} project={project} playerName={playerName} />
          ))}

          {/* Player centroids */}
          {bucket.centroids.map((c) => (
            <CentroidDot
              key={c.slot}
              centroid={c}
              name={playerName(c.slot)}
              project={project}
            />
          ))}
        </svg>
      </div>

      {/* Legend / per-player annotation table */}
      <div style={cardStyle}>
        <h3 style={subHeaderStyle}>At time {formatTimeMs(tMs)}</h3>
        <table style={tableStyle}>
          <thead><tr>
            <th style={thStyle}>Player</th>
            <th style={thStyle}>Position</th>
            <th style={thStyleRight}>Combat food</th>
            <th style={thStyleRight}>Combat units</th>
          </tr></thead>
          <tbody>
            {bucket.centroids.map((c) => (
              <tr key={c.slot}>
                <td style={tdStyle}>
                  <ColorChip color={SLOT_COLORS[c.slot] ?? fallbackColor} />
                  {playerName(c.slot)}
                </td>
                <td style={tdStyle}>
                  {c.x !== null && c.y !== null
                    ? <>
                        ({Math.round(c.x).toLocaleString()}, {Math.round(c.y).toLocaleString()})
                        {c.source === 'stale' && <span style={{ color: '#a16207', marginLeft: '0.4rem' }}>(stale)</span>}
                        {c.source === 'starting' && <span style={{ color: '#6366f1', marginLeft: '0.4rem' }}>(starting)</span>}
                      </>
                    : <span style={{ color: '#6b7280' }}>—</span>}
                </td>
                <td style={tdStyleRight}>{c.combatFood}</td>
                <td style={tdStyleRight}>{c.combatUnitCount}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// === Sub-components =======================================================

function GridLines({
  bounds, project,
}: { bounds: { minX: number; maxX: number; minY: number; maxY: number };
     project: (x: number, y: number) => { sx: number; sy: number } }) {
  // Simple cross at origin to anchor the user's sense of map orientation.
  const origin = project(0, 0);
  const inViewportX = origin.sx >= 0 && origin.sx <= SVG_WIDTH;
  const inViewportY = origin.sy >= 0 && origin.sy <= SVG_HEIGHT;
  return (
    <>
      <rect x={0} y={0} width={SVG_WIDTH} height={SVG_HEIGHT} fill="none" stroke="#1f2937" strokeWidth={1} />
      {inViewportX && inViewportY && (
        <>
          <line x1={origin.sx} y1={0} x2={origin.sx} y2={SVG_HEIGHT} stroke="#374151" strokeWidth={0.5} strokeDasharray="2,4" />
          <line x1={0} y1={origin.sy} x2={SVG_WIDTH} y2={origin.sy} stroke="#374151" strokeWidth={0.5} strokeDasharray="2,4" />
        </>
      )}
    </>
  );
}

function CentroidDot({
  centroid, name, project,
}: { centroid: TimelineCentroid; name: string; project: (x: number, y: number) => { sx: number; sy: number } }) {
  if (centroid.x === null || centroid.y === null) return null;
  const { sx, sy } = project(centroid.x, centroid.y);
  const color = SLOT_COLORS[centroid.slot] ?? fallbackColor;
  const isStale = centroid.source === 'stale';
  const isStarting = centroid.source === 'starting';
  // Source-aware visual treatment:
  //   commanded → solid, opaque (the truth as of now)
  //   stale     → dashed outline, 0.55 opacity (last-known location)
  //   starting  → dotted outline, 0.4 opacity (placeholder before player
  //               first issues a command — shown at their early spawn point)
  let dotOpacity = 1;
  let labelOpacity = 1;
  let strokeDash: string | undefined;
  let suffix = '';
  if (isStale) {
    dotOpacity = 0.55;
    labelOpacity = 0.65;
    strokeDash = '2,2';
    suffix = ' (stale)';
  } else if (isStarting) {
    dotOpacity = 0.4;
    labelOpacity = 0.55;
    strokeDash = '1,3';
    suffix = ' (starting)';
  }
  return (
    <g opacity={dotOpacity}>
      <circle
        cx={sx} cy={sy} r={DOT_RADIUS}
        fill={color}
        stroke={isStale || isStarting ? color : '#0f172a'}
        strokeWidth={2}
        strokeDasharray={strokeDash}
      />
      <text x={sx + DOT_RADIUS + 4} y={sy - 2} fill="#e5e7eb" fontSize={11} fontWeight={600} opacity={labelOpacity}>
        {name}{suffix}
      </text>
      <text x={sx + DOT_RADIUS + 4} y={sy + 11} fill="#9ca3af" fontSize={10} opacity={labelOpacity}>
        {formatCombatFood(centroid.combatFood, centroid.combatUnitCount)}
      </text>
    </g>
  );
}

function PingMarker({
  ping, project, playerName,
}: { ping: Ping; project: (x: number, y: number) => { sx: number; sy: number }; playerName: (slot: number) => string }) {
  const { sx, sy } = project(ping.x, ping.y);
  return (
    <g>
      <circle cx={sx} cy={sy} r={PING_RADIUS} fill="none" stroke="#facc15" strokeWidth={1.5} opacity={0.7} />
      <circle cx={sx} cy={sy} r={1.5} fill="#facc15" />
      <title>{`Ping from ${playerName(ping.fromSlot)} at ${(ping.timeMs / 1000).toFixed(1)}s`}</title>
    </g>
  );
}

function ColorChip({ color }: { color: string }) {
  return (
    <span style={{
      display: 'inline-block', width: '0.7rem', height: '0.7rem',
      backgroundColor: color, borderRadius: '0.15rem', marginRight: '0.4rem',
      verticalAlign: 'middle',
    }} />
  );
}

// === Styles ===============================================================

const containerStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: '1rem', padding: '1rem 0',
};
const cardStyle: React.CSSProperties = {
  background: '#111827', padding: '1rem', borderRadius: '0.5rem',
};
const cardHeaderStyle: React.CSSProperties = {
  margin: '0 0 0.75rem', fontSize: '1rem', borderBottom: '1px solid #374151', paddingBottom: '0.4rem',
};
const subHeaderStyle: React.CSSProperties = {
  margin: '0 0 0.5rem', fontSize: '0.95rem', color: '#9ca3af',
};
const emptyStateStyle: React.CSSProperties = {
  padding: '2rem', textAlign: 'center', color: '#9ca3af',
};
const activeBattleStyle: React.CSSProperties = {
  background: '#7f1d1d', color: '#fee2e2', padding: '0.2rem 0.5rem',
  borderRadius: '0.3rem', fontSize: '0.85rem', fontWeight: 500,
};
const noBattleStyle: React.CSSProperties = {
  color: '#6b7280', fontSize: '0.85rem',
};
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' };
const thStyle: React.CSSProperties = { textAlign: 'left', padding: '0.3rem', borderBottom: '1px solid #374151', color: '#9ca3af' };
const thStyleRight: React.CSSProperties = { ...thStyle, textAlign: 'right' };
const tdStyle: React.CSSProperties = { padding: '0.3rem', borderBottom: '1px solid #1f2937' };
const tdStyleRight: React.CSSProperties = { ...tdStyle, textAlign: 'right' };
