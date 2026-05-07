import type { Player } from '../types/analysis';
import { aggregateHeroes } from '../data/aggregations';
import { Entity } from './Entity';
import section from './PanelSection.module.css';
import styles from './AggregationViews.module.css';

interface Props { player: Player; }

export function HeroAggregationView({ player }: Props) {
  const heroes = aggregateHeroes(player);
  return (
    <section className={`${section.section} ${styles.heroes}`}>
      <h3 className={section.title}>Heroes</h3>
      {heroes.length === 0
        ? <p className={section.empty}>No heroes used.</p>
        : (
          <ul className={`${section.list} ${styles.heroList}`}>
            {heroes.map((hero) => (
              <li key={hero.id} className={styles.heroAgg}>
                <Entity entity={hero} />
                <span className={styles.heroLevel}> — Level {hero.finalLevel}</span>
                {hero.abilityChain.length === 0
                  ? <span className={styles.emptyInline}> (no abilities learned)</span>
                  : (
                    <>
                      {': '}
                      <span className={styles.abilityChain}>
                        {hero.abilityChain.map((ab, idx) => (
                          <span key={`${ab.id}-${idx}`} className={styles.abilitySeg}>
                            {idx > 0 && <span className={styles.arrow}> → </span>}
                            <Entity entity={ab} />
                            <span className={styles.abilityLevel}> (L{ab.level})</span>
                          </span>
                        ))}
                      </span>
                    </>
                  )}
              </li>
            ))}
          </ul>
        )}
    </section>
  );
}
