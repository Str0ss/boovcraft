import styles from './ObserversSection.module.css';

interface Props { observers: string[]; }

export function ObserversSection({ observers }: Props) {
  return (
    <section className={styles.section}>
      <h2 className={styles.header}>Observers ({observers?.length ?? 0})</h2>
      {!observers || observers.length === 0
        ? <p className={styles.empty}>No observers.</p>
        : <p className={styles.list}>{observers.join(', ')}</p>}
    </section>
  );
}
