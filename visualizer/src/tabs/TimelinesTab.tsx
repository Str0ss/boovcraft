import { usePageState } from '../state/PageStateContext';
import { ZoomControls } from '../components/ZoomControls';
import { TimelineLegend } from '../components/TimelineLegend';
import { PlayerHistogram } from '../components/PlayerHistogram';
import { useViewportWidth } from '../hooks/useViewportWidth';
import styles from './TimelinesTab.module.css';

const RACE_NAMES: Record<string, string> = {
  H: 'Human', O: 'Orc', U: 'Undead', N: 'Night Elf', R: 'Random',
};

function raceLabel(player: { race: string; raceDetected: string }): string {
  const chosen = RACE_NAMES[player.race] || player.race;
  if (player.race === 'R' && player.raceDetected && player.raceDetected !== 'R') {
    const detected = RACE_NAMES[player.raceDetected] || player.raceDetected;
    return `Random → ${detected}`;
  }
  return chosen;
}

export function TimelinesTab() {
  const { pageState } = usePageState();
  const { containerRef, chartWidthPx } = useViewportWidth();
  if (!pageState.analysis || !pageState.zoomState) return null;
  const a = pageState.analysis;

  return (
    <section ref={containerRef} className={styles.tab}>
      <ZoomControls chartWidthPx={chartWidthPx} />
      <TimelineLegend />
      <p className={styles.hint}>
        Drag horizontally on any chart to zoom into that time range.
        Press <kbd>Esc</kbd> to cancel an in-progress brush.
      </p>
      <div className={styles.stack}>
        {a.players.map((player) => (
          <article
            key={player.id}
            className={styles.row}
            style={{ borderLeftColor: player.color || '#888' }}
          >
            <div className={styles.labelCol}>
              <span
                className={styles.swatch}
                style={{ backgroundColor: player.color || '#888' }}
                title={player.color}
              />
              <div className={styles.nameBlock}>
                <span className={styles.name}>{player.name}</span>
                <span className={styles.meta}>
                  {raceLabel(player)} · {player.apm} APM
                  {player.isWinner ? ' · Winner' : ''}
                </span>
              </div>
            </div>
            <div className={styles.chartCol}>
              <PlayerHistogram
                player={player}
                zoomState={pageState.zoomState!}
                filterState={pageState.filterState}
                durationMs={a.match.durationMs}
                chartWidthPx={chartWidthPx}
              />
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
