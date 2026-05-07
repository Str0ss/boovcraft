import type { AnalysisJson } from '../types/analysis';
import { formatTimeMs } from '../data/format';
import styles from './MatchHeader.module.css';

interface Props {
  analysis: AnalysisJson;
}

export function MatchHeader({ analysis }: Props) {
  const m = analysis.match;
  const settings = analysis.settings || {};
  const winnerLabel = m.winner === null ? 'Undetermined' : `Team ${m.winner.teamId}`;
  const winnerCls = m.winner === null
    ? `${styles.outcome} ${styles.outcomeUndetermined}`
    : `${styles.outcome} ${styles.outcomeWinner}`;

  const map = analysis.map || {};
  const mapName = map.file || map.path || '(unknown map)';

  const settingsRow = (label: string, value: unknown) => {
    if (value === null || value === undefined || value === '') return null;
    return (
      <>
        <dt>{label}</dt>
        <dd>{String(value)}</dd>
      </>
    );
  };

  return (
    <section className={styles.header}>
      <div className={styles.line}>
        <span className={winnerCls}>Outcome: {winnerLabel}</span>
        <span className={styles.sep}>·</span>
        <span className={styles.duration}>Duration {formatTimeMs(m.durationMs, m.durationMs)}</span>
        <span className={styles.sep}>·</span>
        <span className={styles.gametype}>{m.gameType} — {m.matchup}</span>
        <span className={styles.sep}>·</span>
        <span className={styles.mapname} title={map.path || mapName}>{mapName}</span>
        <span className={styles.sep}>·</span>
        <span className={styles.version}>v{m.version} (build {m.buildNumber})</span>
      </div>
      <dl className={styles.settings}>
        {settingsRow('Game', m.gameName)}
        {settingsRow('Creator', m.creator)}
        {settingsRow('Speed', settings.speed)}
        {settingsRow('Observer mode', settings.observerMode)}
        {settingsRow('Fixed teams', settings.fixedTeams ? 'yes' : 'no')}
        {settingsRow('Teams together', settings.teamsTogether ? 'yes' : 'no')}
        {settingsRow('Random races', settings.randomRaces ? 'yes' : 'no')}
        {settingsRow('Random heroes', settings.randomHero ? 'yes' : 'no')}
      </dl>
    </section>
  );
}
