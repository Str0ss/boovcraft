import type { Player } from '../types/analysis';
import { aggregateProduction } from '../data/aggregations';
import { Entity } from './Entity';
import section from './PanelSection.module.css';
import styles from './AggregationViews.module.css';

const CATEGORIES = [
  { key: 'buildings' as const, label: 'Buildings', empty: 'No buildings recorded.' },
  { key: 'units' as const, label: 'Units', empty: 'No units recorded.' },
  { key: 'upgrades' as const, label: 'Upgrades', empty: 'No upgrades recorded.' },
  { key: 'items' as const, label: 'Items', empty: 'No items recorded.' },
];

interface Props { player: Player; }

export function ProductionAggregationView({ player }: Props) {
  const agg = aggregateProduction(player);
  return (
    <section className={`${section.section} ${styles.production}`}>
      <h3 className={section.title}>Production</h3>
      {CATEGORIES.map((cat) => {
        const rows = agg[cat.key];
        const total = rows.reduce((s, r) => s + r.count, 0);
        return (
          <section key={cat.key} className={styles.prodCat}>
            <h4 className={styles.prodCatTitle}>{cat.label} ({total})</h4>
            {rows.length === 0
              ? <p className={section.empty}>{cat.empty}</p>
              : (
                <ul className={section.list}>
                  {rows.map((r) => (
                    <li key={r.id}>
                      <Entity entity={r} />
                      <span className={section.count}> (×{r.count})</span>
                    </li>
                  ))}
                </ul>
              )}
          </section>
        );
      })}
    </section>
  );
}
