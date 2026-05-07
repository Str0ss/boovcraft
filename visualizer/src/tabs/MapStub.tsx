import { usePageState } from '../state/PageStateContext';
import styles from './stub.module.css';

export function MapStub() {
  const { pageState } = usePageState();
  const map = pageState.analysis?.map ?? {};
  const mapName = map.file || map.path || '(unknown map)';
  return (
    <section className={styles.stub}>
      <h2 className={styles.heading}>Map (coming soon)</h2>
      <p className={styles.body}>
        This tab will visualize per-player actions on the match map — also
        not yet implemented.
      </p>
      <p className={styles.body}>Map for this match: {mapName}</p>
    </section>
  );
}
