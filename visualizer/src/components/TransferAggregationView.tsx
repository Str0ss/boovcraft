import type { AnalysisJson, Player } from '../types/analysis';
import { aggregateTransfers } from '../data/aggregations';
import { formatInt } from '../data/format';
import section from './PanelSection.module.css';
import styles from './AggregationViews.module.css';

interface Props { player: Player; analysis: AnalysisJson; }

export function TransferAggregationView({ player, analysis }: Props) {
  const rows = aggregateTransfers(player, analysis);
  return (
    <section className={`${section.section} ${styles.transfers}`}>
      <h3 className={section.title}>Resource transfers</h3>
      {rows.length === 0
        ? <p className={section.empty}>No allied resource transfers.</p>
        : (
          <ul className={section.list}>
            {rows.map((r, i) => (
              <li key={`${r.recipientId}-${r.resource}-${i}`}>
                <span className={styles.recipient}>{r.recipientName}</span>
                {': '}
                <span className={styles.amount}>{formatInt(r.total)} {r.resource}</span>
                <span className={section.count}>
                  {' '}({r.count} transfer{r.count === 1 ? '' : 's'})
                </span>
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}
