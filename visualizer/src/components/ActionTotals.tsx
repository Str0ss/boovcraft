import type { Player } from '../types/analysis';
import { formatInt } from '../data/format';
import section from './PanelSection.module.css';
import styles from './ActionTotals.module.css';

const ACTION_TOTAL_LABELS: [string, string][] = [
  ['buildtrain', 'Build / train'],
  ['ability', 'Ability'],
  ['item', 'Item'],
  ['rightclick', 'Right-click'],
  ['select', 'Select'],
  ['selecthotkey', 'Hotkey select'],
  ['assigngroup', 'Assign group'],
  ['subgroup', 'Subgroup'],
  ['basic', 'Basic'],
  ['removeunit', 'Remove unit'],
  ['esc', 'Esc'],
];

interface Props { player: Player; }

export function ActionTotals({ player }: Props) {
  const totals = player.actions?.totals ?? {};
  return (
    <section className={section.section}>
      <h3 className={section.title}>Action totals</h3>
      <dl className={styles.dl}>
        {ACTION_TOTAL_LABELS.map(([key, label]) => {
          const v = totals[key];
          if (v == null) return null;
          return (
            <div key={key} className={styles.row}>
              <dt>{label}</dt>
              <dd>{formatInt(v)}</dd>
            </div>
          );
        })}
      </dl>
    </section>
  );
}
