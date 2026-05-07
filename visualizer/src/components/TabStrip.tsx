import { usePageState } from '../state/PageStateContext';
import { TABS } from '../state/types';
import styles from './TabStrip.module.css';

export function TabStrip() {
  const { pageState, dispatchers } = usePageState();
  if (!pageState.analysis) return null;
  return (
    <nav className={styles.strip} role="tablist" aria-label="Replay views">
      {TABS.map((tab) => {
        const isActive = pageState.activeTab === tab.id;
        return (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            data-tab={tab.id}
            className={`${styles.tab} ${isActive ? styles.active : ''}`}
            onClick={() => dispatchers.setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        );
      })}
    </nav>
  );
}
