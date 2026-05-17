import { useEffect, useState } from 'react';
import type {
  AnalysisJson,
  Attribution,
  Battle,
  BattleTEI,
  ExecutiveFinding,
} from '../types/analysis';
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
} from '../data/teamFormat';

const KILLS_TOP_N = 10;
const HIGHLIGHT_PULSE_MS = 2000;

interface TeamTabProps {
  analysis: AnalysisJson;
}

export function TeamTab({ analysis }: TeamTabProps) {
  const team = analysis.team;
  const players = analysis.players;
  const playerName = (slot: number): string =>
    players.find((p) => p.id === slot)?.name ?? `slot ${slot}`;

  // Highlight pulse state for click-to-scroll executive findings (US7).
  // Single highlight active at a time; auto-clears after HIGHLIGHT_PULSE_MS.
  const [highlightedId, setHighlightedId] = useState<string | null>(null);
  useEffect(() => {
    if (!highlightedId) return;
    const t = window.setTimeout(() => setHighlightedId(null), HIGHLIGHT_PULSE_MS);
    return () => window.clearTimeout(t);
  }, [highlightedId]);

  // Reset highlight when the analysis swaps (FR-024 — no bleed-through across files).
  useEffect(() => {
    setHighlightedId(null);
  }, [analysis]);

  const navigateToEvidence = (finding: ExecutiveFinding) => {
    const targetId = dispatchEvidenceRef(finding.evidenceRef);
    if (!targetId) return; // forward-compat: unknown ref kinds are no-ops (UI-19)
    const el = document.querySelector<HTMLElement>(`[data-evidence-id="${targetId}"]`);
    if (!el) return;
    el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setHighlightedId(targetId);
  };

  // === Empty-state branches ===============================================
  if (!team) {
    return (
      <section style={emptyStateStyle}>
        <h2>Team tab not available</h2>
        <p>This analysis JSON pre-dates feature 007. Re-run <code>python3 processor/analyze.py</code> on the parser output to regenerate it with team-cohesion analysis.</p>
      </section>
    );
  }

  if (!team.applicable) {
    const message = (() => {
      switch (team.reason) {
        case 'noAllies':           return 'No teammates — split-engagement analysis is not applicable to 1v1 replays.';
        case 'ffa':                return 'FFA replay — team-cohesion analysis applies only to fixed-team modes.';
        case 'noBattlesDetected':  return 'No team battles were detected in this replay.';
        case 'preFeature007File':  return 'This file pre-dates feature 007 — re-run the analyzer.';
        default:                   return 'Team-cohesion analysis is not applicable to this replay.';
      }
    })();
    return (
      <section style={emptyStateStyle}>
        <h2>Team analysis unavailable</h2>
        <p>{message}</p>
      </section>
    );
  }

  // === Populated state ====================================================
  return (
    <section style={containerStyle}>
      {/* Executive summary */}
      <div style={cardStyle}>
        <h2 style={cardHeaderStyle}>Executive summary</h2>
        {team.battleSummary.executive.length === 0 ? (
          <p style={mutedStyle}>No findings.</p>
        ) : (
          <ol style={{ paddingLeft: '1.25rem', margin: 0 }}>
            {team.battleSummary.executive.map((f) => (
              <ExecutiveItem key={`${f.rank}-${f.kind}`} finding={f} onClick={() => navigateToEvidence(f)} />
            ))}
          </ol>
        )}
      </div>

      {/* Shared control banner */}
      <div
        style={highlightStyle(highlightedId, 'globalFlag-sharedControlDisabled', cardStyle)}
        data-evidence-id="globalFlag-sharedControlDisabled"
      >
        <h2 style={cardHeaderStyle}>Shared control</h2>
        <p style={{ margin: 0 }}>
          {team.sharedControl.enabled ? (
            <span style={{ color: '#4ade80', fontWeight: 600 }}>ENABLED</span>
          ) : (
            <span style={{ color: '#f87171', fontWeight: 600 }}>DISABLED</span>
          )}
          {team.findings.includes('sharedControlDisabled') && (
            <span style={mutedStyle}> — flagged as a coordination concern.</span>
          )}
        </p>
      </div>

      {/* Per-battle list */}
      <div style={cardStyle}>
        <h2 style={cardHeaderStyle}>Battles ({team.battles.length})</h2>
        {team.battles.length === 0 ? (
          <p style={mutedStyle}>No battle windows detected.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {team.battles.map((b) => (
              <BattleRow
                key={`${analysis.diagnostics?.parserId ?? 'replay'}-${b.index}`}
                battle={b}
                tei={team.battleSummary.tei.find((t) => t.battleIndex === b.index)}
                attributions={team.battleSummary.attributions.filter((a) => a.battleIndex === b.index)}
                playerName={playerName}
                highlighted={highlightedId === `battle-${b.index}`}
              />
            ))}
          </div>
        )}
      </div>

      {/* Attributions empty-state (US6 / UI-15) */}
      {team.battleSummary.attributions.length === 0 && (
        <div style={cardStyle}>
          <h2 style={cardHeaderStyle}>Strategic blame attributions</h2>
          <p style={mutedStyle}>
            No strategic blame attributed (requires split engagement + lost trade + outlier centroid simultaneously).
          </p>
        </div>
      )}

      {/* Resource cooperation */}
      <div style={cardStyle}>
        <h2 style={cardHeaderStyle}>Resource cooperation</h2>
        <h3 style={subHeaderStyle}>Transfers ({team.resourceCooperation.transfers.length})</h3>
        {team.resourceCooperation.transfers.length === 0 ? (
          <p style={mutedStyle}>No allied transfers.</p>
        ) : (
          <table style={tableStyle}>
            <thead><tr><th style={thStyle}>Time</th><th style={thStyle}>From</th><th style={thStyle}>To</th><th style={thStyleRight}>Gold</th><th style={thStyleRight}>Lumber</th><th style={thStyle}>Purpose</th></tr></thead>
            <tbody>
              {team.resourceCooperation.transfers.map((t, i) => (
                <tr key={i}>
                  <td style={tdStyle}>{formatTimeMs(t.timeMs)}</td>
                  <td style={tdStyle}>{playerName(t.fromSlot)}</td>
                  <td style={tdStyle}>{t.toPlayerName}</td>
                  <td style={tdStyleRight}>{t.gold}</td>
                  <td style={tdStyleRight}>{t.lumber}</td>
                  <td style={tdStyle}>{purposeHintLabel(t.purposeHint)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <h3 style={subHeaderStyle}>Generosity</h3>
        <table style={tableStyle}>
          <thead><tr><th style={thStyle}>Player</th><th style={thStyleRight}>Sent gold</th><th style={thStyleRight}>Sent lumber</th><th style={thStyleRight}>Mined (est.)</th><th style={thStyleRight}>Generosity</th></tr></thead>
          <tbody>
            {team.resourceCooperation.generosity.map((g) => (
              <tr key={g.slot}>
                <td style={tdStyle}>{g.name}</td>
                <td style={tdStyleRight}>{g.sentGold}</td>
                <td style={tdStyleRight}>{g.sentLumber}</td>
                <td style={tdStyleRight}>{g.estimatedMinedGold !== null ? `${g.estimatedMinedGold}g/${g.estimatedMinedLumber}l` : '—'}</td>
                <td style={tdStyleRight}>{formatPercent(g.generosityPercent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Item transfers */}
      <div style={cardStyle}>
        <h2 style={cardHeaderStyle}>Item gives ({team.itemTransfers.length})</h2>
        {team.itemTransfers.length === 0 ? (
          <p style={mutedStyle}>No item transfers.</p>
        ) : (
          <table style={tableStyle}>
            <thead><tr><th style={thStyle}>Time</th><th style={thStyle}>From</th><th style={thStyle}>To</th><th style={thStyle}>Item</th><th style={thStyle}>Fit</th></tr></thead>
            <tbody>
              {team.itemTransfers.map((t, i) => (
                <tr key={i}>
                  <td style={tdStyle}>{formatTimeMs(t.timeMs)}</td>
                  <td style={tdStyle}>{playerName(t.fromSlot)}</td>
                  <td style={tdStyle}>{t.toSlot >= 0 ? playerName(t.toSlot) : '—'}</td>
                  <td style={tdStyle}>{t.item.name}{t.item.unknown ? ' (unmapped)' : ''}</td>
                  <td style={{ ...tdStyle, color: fitClassColor(t.recipientFitClass) }}>{fitClassLabel(t.recipientFitClass)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Per-player KP% */}
      <div style={cardStyle}>
        <h2 style={cardHeaderStyle}>Kill participation</h2>
        <table style={tableStyle}>
          <thead><tr><th style={thStyle}>Player</th><th style={thStyleRight}>KP%</th></tr></thead>
          <tbody>
            {team.players.map((p) => (
              <tr key={p.slot}>
                <td style={tdStyle}>{p.name}</td>
                <td style={tdStyleRight}>{formatPercent(p.killParticipationPercent)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Diagnostics */}
      {analysis.diagnostics.cohesionMetricGaps && analysis.diagnostics.cohesionMetricGaps.length > 0 && (
        <div style={cardStyle}>
          <h2 style={cardHeaderStyle}>Diagnostics</h2>
          <ul style={{ margin: 0, paddingLeft: '1.25rem' }}>
            {analysis.diagnostics.cohesionMetricGaps.map((g, i) => (
              <li key={i} style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#9ca3af' }}>
                <strong>{g.metric}</strong>: {g.reason}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

function ExecutiveItem({ finding, onClick }: { finding: ExecutiveFinding; onClick: () => void }) {
  return (
    <li style={{ marginBottom: '0.5rem' }}>
      <button type="button" onClick={onClick} style={execButtonStyle}>
        <strong>{findingKindLabel(finding.kind)}</strong> — {finding.summary}{' '}
        <span style={{ color: '#9ca3af', fontSize: '0.85rem' }}>(severity {finding.weightedSeverity.toFixed(1)})</span>
      </button>
    </li>
  );
}

function BattleRow({
  battle, tei, attributions, playerName, highlighted,
}: {
  battle: Battle;
  tei?: BattleTEI;
  attributions: Attribution[];
  playerName: (slot: number) => string;
  highlighted: boolean;
}) {
  const split = battle.splitEngagement;
  const baseStyle: React.CSSProperties = {
    padding: '0.75rem',
    background: '#1f2937',
    borderRadius: '0.4rem',
    borderLeft: split.flagged ? '3px solid #f87171' : '3px solid #374151',
  };
  const styled: React.CSSProperties = highlighted
    ? { ...baseStyle, boxShadow: '0 0 0 2px #fbbf24, 0 0 12px 4px rgba(251, 191, 36, 0.4)', transition: 'box-shadow 0.4s' }
    : { ...baseStyle, transition: 'box-shadow 0.4s' };

  return (
    <div data-evidence-id={`battle-${battle.index}`} style={styled}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem' }}>
        <strong>Battle {battle.index} — {formatTimeMs(battle.startMs)}–{formatTimeMs(battle.endMs)}</strong>
        {tei && (
          <span style={{ fontSize: '0.85rem', color: '#9ca3af' }}>
            TEI A: <span style={{ color: '#e5e7eb' }}>{formatTei(tei.teamSideTei.teamA)}</span> / B: <span style={{ color: '#e5e7eb' }}>{formatTei(tei.teamSideTei.teamB)}</span>
          </span>
        )}
      </div>
      <div style={{ fontSize: '0.85rem', color: '#9ca3af' }}>
        Sides: A={battle.sides.teamA.map(playerName).join(', ')} · B={battle.sides.teamB.map(playerName).join(', ')}
      </div>

      {split.flagged && split.flaggedSlots.length === 2 && (
        <div style={{ marginTop: '0.5rem', padding: '0.4rem', background: '#7f1d1d', borderRadius: '0.3rem', fontSize: '0.85rem' }}>
          🚩 <strong>Split engagement:</strong> {playerName(split.flaggedSlots[0]!)} ↔ {playerName(split.flaggedSlots[1]!)} —{' '}
          distance <strong>{formatDistance(split.distance)}</strong> exceeds <strong>{split.referenceAuraName}</strong>
        </div>
      )}

      {/* Focus fire — header + contributors breakdown (US2) */}
      {battle.focusFire ? (
        <div style={{ marginTop: '0.4rem', fontSize: '0.85rem', color: '#9ca3af' }}>
          Focus fire: <strong style={{ color: '#e5e7eb' }}>{battle.focusFire.cohesionPercent.toFixed(0)}%</strong>
          {' '}on {playerName(battle.focusFire.dominantTargetSlot ?? -1)}
          {battle.focusFire.contributingPlayers.length > 0 && (
            <div style={{ marginTop: '0.2rem', paddingLeft: '1rem' }}>
              Attacks: {battle.focusFire.contributingPlayers
                .map((c) => `${playerName(c.slot)} (${c.attackCount})`)
                .join(' · ')}
            </div>
          )}
        </div>
      ) : (
        <div style={{ marginTop: '0.4rem', fontSize: '0.85rem', color: '#9ca3af', fontStyle: 'italic' }}>
          Focus fire: no enemy unit-handle ownership inferable in window
        </div>
      )}

      {/* Pings drill-down (US1) */}
      <PingsDrillDown battle={battle} playerName={playerName} />

      {/* Kills drill-down (US3) */}
      <KillsDrillDown battle={battle} playerName={playerName} />

      {/* Geometry drill-down (US5) */}
      <GeometryDrillDown battle={battle} playerName={playerName} />

      {/* Per-player TEI (US4) */}
      {tei && (
        <details style={detailsStyle}>
          <summary style={summaryStyle}>Per-player TEI</summary>
          <table style={tableStyle}>
            <thead><tr><th style={thStyle}>Player</th><th style={thStyleRight}>TEI</th></tr></thead>
            <tbody>
              {tei.perPlayerTei.map((row) => (
                <tr key={row.slot}>
                  <td style={tdStyle}>{playerName(row.slot)}</td>
                  <td
                    style={tdStyleRight}
                    title={row.tei === null
                      ? 'Per-player TEI requires per-handle owner attribution; deferred to feature 010 (v1 limitation).'
                      : undefined}
                  >
                    {formatTei(row.tei)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </details>
      )}

      {attributions.length > 0 && (
        <div style={{ marginTop: '0.4rem', fontSize: '0.85rem' }}>
          {attributions.map((a, i) => (
            <span key={i} style={{ display: 'inline-block', padding: '0.1rem 0.4rem', background: '#7f1d1d', borderRadius: '0.2rem', marginRight: '0.4rem' }}>
              Likely cause: {playerName(a.playerSlot)} ({a.reason})
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function PingsDrillDown({ battle, playerName }: { battle: Battle; playerName: (slot: number) => string }) {
  if (battle.pings.length === 0) return null;
  return (
    <details style={detailsStyle}>
      <summary style={summaryStyle}>Pings ({battle.pings.length})</summary>
      <table style={tableStyle}>
        <thead><tr>
          <th style={thStyle}>Time</th>
          <th style={thStyle}>From</th>
          <th style={thStyle}>Responded</th>
          <th style={thStyle}>Busy</th>
          <th style={thStyle}>Ignored</th>
        </tr></thead>
        <tbody>
          {battle.pings.map((ping, i) => {
            const sideMembers = resolvePingSide(ping, battle);
            const { responded, busy, ignored } = classifyPingChips(ping, sideMembers);
            return (
              <tr key={i}>
                <td style={tdStyle}>{formatTimeMs(ping.timeMs)}</td>
                <td style={tdStyle}>{playerName(ping.fromSlot)}</td>
                <td style={tdStyle}>{chipGroup(responded, '#15803d', playerName)}</td>
                <td style={tdStyle}>{chipGroup(busy, '#a16207', playerName)}</td>
                <td style={tdStyle}>{chipGroup(ignored, '#991b1b', playerName)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </details>
  );
}

function KillsDrillDown({ battle, playerName }: { battle: Battle; playerName: (slot: number) => string }) {
  const total = battle.kills.length;
  if (total === 0) return null;
  const top = topNKillsByValue(battle.kills, KILLS_TOP_N);
  const truncated = total > KILLS_TOP_N;
  return (
    <details style={detailsStyle}>
      <summary style={summaryStyle}>
        Kills ({total}){truncated && <span style={mutedInlineStyle}> — showing top {KILLS_TOP_N}</span>}
      </summary>
      <table style={tableStyle}>
        <thead><tr>
          <th style={thStyle}>Time</th>
          <th style={thStyle}>Side</th>
          <th style={thStyleRight}>Value</th>
          <th style={thStyle}>Credits</th>
        </tr></thead>
        <tbody>
          {top.map((kill, i) => (
            <tr key={i}>
              <td style={tdStyle}>{formatTimeMs(kill.killTimeMs)}</td>
              <td style={tdStyle}>{kill.victimSide}</td>
              <td style={tdStyleRight}>{kill.victimValue}</td>
              <td style={tdStyle}>
                {kill.credits.map((c, ci) => (
                  <span key={ci} style={chipBaseStyle('#374151')}>
                    {playerName(c.slot)}: {(c.fraction * 100).toFixed(0)}%
                  </span>
                ))}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </details>
  );
}

function GeometryDrillDown({ battle, playerName }: { battle: Battle; playerName: (slot: number) => string }) {
  if (battle.centroids.length === 0) return null;

  const sideALabel = battle.sides.teamA;
  const sideBLabel = battle.sides.teamB;
  const isInSide = (slot: number, side: number[]) => side.includes(slot);

  const distancesA = battle.alliedDistances.filter(
    (d) => isInSide(d.fromSlot, sideALabel) && isInSide(d.toSlot, sideALabel),
  );
  const distancesB = battle.alliedDistances.filter(
    (d) => isInSide(d.fromSlot, sideBLabel) && isInSide(d.toSlot, sideBLabel),
  );

  return (
    <details style={detailsStyle}>
      <summary style={summaryStyle}>Geometry</summary>
      <h4 style={subSubHeaderStyle}>Centroids</h4>
      <table style={tableStyle}>
        <thead><tr>
          <th style={thStyle}>Player</th>
          <th style={thStyleRight}>x</th>
          <th style={thStyleRight}>y</th>
          <th style={thStyle}>Source</th>
        </tr></thead>
        <tbody>
          {battle.centroids.map((c) => (
            <tr key={c.slot}>
              <td style={tdStyle}>{playerName(c.slot)}</td>
              <td
                style={tdStyleRight}
                title={c.source === 'missing' ? 'No commands in centroid lookback window' : undefined}
              >
                {c.x === null ? '—' : Math.round(c.x).toLocaleString()}
              </td>
              <td
                style={tdStyleRight}
                title={c.source === 'missing' ? 'No commands in centroid lookback window' : undefined}
              >
                {c.y === null ? '—' : Math.round(c.y).toLocaleString()}
              </td>
              <td style={tdStyle}>{c.source}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h4 style={subSubHeaderStyle}>Allied distances</h4>
      <DistanceMatrix distances={distancesA} label="Side A" playerName={playerName} />
      <DistanceMatrix distances={distancesB} label="Side B" playerName={playerName} />
    </details>
  );
}

function DistanceMatrix({
  distances, label, playerName,
}: {
  distances: { fromSlot: number; toSlot: number; distance: number }[];
  label: string;
  playerName: (slot: number) => string;
}) {
  if (distances.length === 0) return <p style={mutedStyle}>{label}: no allied pairs.</p>;
  return (
    <table style={tableStyle}>
      <thead><tr><th style={thStyle}>{label} pair</th><th style={thStyleRight}>Distance</th></tr></thead>
      <tbody>
        {distances.map((d, i) => (
          <tr key={i}>
            <td style={tdStyle}>{playerName(d.fromSlot)} ↔ {playerName(d.toSlot)}</td>
            <td style={tdStyleRight}>{formatDistance(d.distance)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function chipGroup(slots: number[], color: string, playerName: (slot: number) => string) {
  if (slots.length === 0) return <span style={mutedInlineStyle}>—</span>;
  return (
    <>
      {slots.map((s) => (
        <span key={s} style={chipBaseStyle(color)}>{playerName(s)}</span>
      ))}
    </>
  );
}

function highlightStyle(highlightedId: string | null, thisId: string, baseStyle: React.CSSProperties): React.CSSProperties {
  if (highlightedId !== thisId) return { ...baseStyle, transition: 'box-shadow 0.4s' };
  return {
    ...baseStyle,
    boxShadow: '0 0 0 2px #fbbf24, 0 0 12px 4px rgba(251, 191, 36, 0.4)',
    transition: 'box-shadow 0.4s',
  };
}

// === Inline styles (CSS-in-JS keeps this single-file feature self-contained) ===

const containerStyle: React.CSSProperties = {
  display: 'flex', flexDirection: 'column', gap: '1rem',
  padding: '1rem 0',
};
const cardStyle: React.CSSProperties = {
  background: '#111827', padding: '1rem', borderRadius: '0.5rem',
};
const cardHeaderStyle: React.CSSProperties = {
  margin: '0 0 0.75rem', fontSize: '1rem', borderBottom: '1px solid #374151', paddingBottom: '0.4rem',
};
const subHeaderStyle: React.CSSProperties = {
  margin: '0.75rem 0 0.4rem', fontSize: '0.9rem', color: '#9ca3af',
};
const emptyStateStyle: React.CSSProperties = {
  padding: '2rem', textAlign: 'center', color: '#9ca3af',
};
const mutedStyle: React.CSSProperties = { color: '#6b7280', margin: 0 };
const tableStyle: React.CSSProperties = { width: '100%', borderCollapse: 'collapse', fontSize: '0.9rem' };
const thStyle: React.CSSProperties = { textAlign: 'left', padding: '0.3rem', borderBottom: '1px solid #374151', color: '#9ca3af' };
const thStyleRight: React.CSSProperties = { ...thStyle, textAlign: 'right' };
const tdStyle: React.CSSProperties = { padding: '0.3rem', borderBottom: '1px solid #1f2937' };
const tdStyleRight: React.CSSProperties = { ...tdStyle, textAlign: 'right' };
const detailsStyle: React.CSSProperties = {
  marginTop: '0.5rem',
  padding: '0.4rem',
  background: '#0f172a',
  borderRadius: '0.3rem',
  fontSize: '0.85rem',
};
const summaryStyle: React.CSSProperties = {
  cursor: 'pointer',
  color: '#9ca3af',
  fontWeight: 500,
  userSelect: 'none',
};
const subSubHeaderStyle: React.CSSProperties = {
  margin: '0.6rem 0 0.3rem',
  fontSize: '0.85rem',
  color: '#9ca3af',
  fontWeight: 400,
};
const mutedInlineStyle: React.CSSProperties = { color: '#6b7280', fontSize: '0.85rem' };
const execButtonStyle: React.CSSProperties = {
  background: 'none',
  border: 'none',
  padding: 0,
  color: '#e5e7eb',
  cursor: 'pointer',
  textAlign: 'left',
  font: 'inherit',
  width: '100%',
};
function chipBaseStyle(bg: string): React.CSSProperties {
  return {
    display: 'inline-block',
    padding: '0.1rem 0.4rem',
    background: bg,
    color: '#e5e7eb',
    borderRadius: '0.2rem',
    marginRight: '0.25rem',
    marginBottom: '0.15rem',
    fontSize: '0.8rem',
  };
}
