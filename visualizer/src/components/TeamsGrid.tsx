import type { AnalysisJson, Player } from '../types/analysis';
import { PlayerPanel } from './PlayerPanel';
import styles from './TeamsGrid.module.css';

function groupByTeam(players: Player[]): Map<number, Player[]> {
  const m = new Map<number, Player[]>();
  for (const p of players) {
    const arr = m.get(p.teamId) ?? [];
    arr.push(p);
    m.set(p.teamId, arr);
  }
  return new Map([...m.entries()].sort((a, b) => a[0] - b[0]));
}

interface Props { analysis: AnalysisJson; }

export function TeamsGrid({ analysis }: Props) {
  const grouping = groupByTeam(analysis.players);
  return (
    <section className={styles.teams}>
      {[...grouping.entries()].map(([teamId, players]) => {
        const isWinningTeam = players.length > 0 && players.every((p) => p.isWinner);
        const headerCls = isWinningTeam
          ? `${styles.teamHeader} ${styles.teamHeaderWinner}`
          : styles.teamHeader;
        return (
          <section key={teamId} className={styles.team}>
            <h2 className={headerCls}>
              {isWinningTeam ? `Team ${teamId} — winners` : `Team ${teamId}`}
            </h2>
            <div className={styles.grid}>
              {players.map((p) => (
                <PlayerPanel key={p.id} player={p} analysis={analysis} />
              ))}
            </div>
          </section>
        );
      })}
    </section>
  );
}
