import type { AnalysisJson, Player } from '../types/analysis';
import { ActionTotals } from './ActionTotals';
import { GroupHotkeys } from './GroupHotkeys';
import { ProductionAggregationView } from './ProductionAggregationView';
import { HeroAggregationView } from './HeroAggregationView';
import { TransferAggregationView } from './TransferAggregationView';
import styles from './PlayerPanel.module.css';

const RACE_NAMES: Record<string, string> = {
  H: 'Human', O: 'Orc', U: 'Undead', N: 'Night Elf', R: 'Random',
};

function raceLabel(player: Player): string {
  const chosen = RACE_NAMES[player.race] || player.race;
  if (player.race === 'R' && player.raceDetected && player.raceDetected !== ('R' as unknown)) {
    const detected = RACE_NAMES[player.raceDetected] || player.raceDetected;
    return `Random → ${detected}`;
  }
  return chosen;
}

interface Props { player: Player; analysis: AnalysisJson; }

export function PlayerPanel({ player, analysis }: Props) {
  return (
    <article
      className={styles.panel}
      style={{ borderLeftColor: player.color || '#888' }}
    >
      <header className={styles.header}>
        <span className={styles.name}>{player.name}</span>
        <span className={styles.race}>{raceLabel(player)}</span>
        <span className={styles.apm}>{player.apm} APM</span>
        {player.isWinner && <span className={styles.winnerBadge}>Winner</span>}
      </header>
      <div className={styles.meta}>
        <span
          className={styles.swatch}
          style={{ backgroundColor: player.color || '#888' }}
          title={player.color}
        />
        <span>Slot {player.id}</span>
        <span>Team {player.teamId}</span>
      </div>
      <ActionTotals player={player} />
      <GroupHotkeys player={player} />
      <ProductionAggregationView player={player} />
      <HeroAggregationView player={player} />
      <TransferAggregationView player={player} analysis={analysis} />
    </article>
  );
}
