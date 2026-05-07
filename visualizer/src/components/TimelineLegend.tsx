import { usePageState } from '../state/PageStateContext';
import {
  MAJOR_TIMELINE_CATEGORIES,
  MINOR_TIMELINE_CATEGORIES,
  type TimelineCategory,
} from '../types/analysis';
import { CATEGORY_COLOR, CATEGORY_LABEL } from './PlayerHistogram';
import styles from './TimelineLegend.module.css';

function Chip({
  category, enabled, onToggle,
}: {
  category: TimelineCategory;
  enabled: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      className={`${styles.chip} ${enabled ? '' : styles.chipDisabled}`}
      onClick={onToggle}
      aria-pressed={enabled}
      title={enabled ? `${CATEGORY_LABEL[category]} — click to hide` : `${CATEGORY_LABEL[category]} — click to show`}
    >
      <span
        className={styles.swatch}
        style={{ backgroundColor: CATEGORY_COLOR[category] }}
      />
      <span className={styles.label}>{CATEGORY_LABEL[category]}</span>
    </button>
  );
}

export function TimelineLegend() {
  const { pageState, dispatchers } = usePageState();
  const enabled = pageState.filterState.enabled;

  return (
    <section className={styles.legend}>
      <div className={styles.row}>
        <span className={styles.groupTitle}>Major</span>
        {MAJOR_TIMELINE_CATEGORIES.map((c) => (
          <Chip
            key={c}
            category={c}
            enabled={enabled[c]}
            onToggle={() => dispatchers.toggleCategory(c)}
          />
        ))}
      </div>
      <div className={styles.row}>
        <span className={styles.groupTitle}>Minor</span>
        {MINOR_TIMELINE_CATEGORIES.map((c) => (
          <Chip
            key={c}
            category={c}
            enabled={enabled[c]}
            onToggle={() => dispatchers.toggleCategory(c)}
          />
        ))}
      </div>
      <div className={styles.bulkRow}>
        <button type="button" className={styles.bulkBtn}
          onClick={() => dispatchers.setBulkCategoryFilter('all', true)}>All on</button>
        <button type="button" className={styles.bulkBtn}
          onClick={() => dispatchers.setBulkCategoryFilter('all', false)}>All off</button>
        <button type="button" className={styles.bulkBtn}
          onClick={() => dispatchers.setBulkCategoryFilter('major', true)}>Major on</button>
        <button type="button" className={styles.bulkBtn}
          onClick={() => dispatchers.setBulkCategoryFilter('major', false)}>Major off</button>
        <button type="button" className={styles.bulkBtn}
          onClick={() => dispatchers.setBulkCategoryFilter('minor', true)}>Minor on</button>
        <button type="button" className={styles.bulkBtn}
          onClick={() => dispatchers.setBulkCategoryFilter('minor', false)}>Minor off</button>
      </div>
    </section>
  );
}
