import type { Player } from '../types/analysis';
import { formatInt } from '../data/format';
import section from './PanelSection.module.css';
import styles from './GroupHotkeys.module.css';

interface Props { player: Player; }

export function GroupHotkeys({ player }: Props) {
  const hk = player.groupHotkeys || {};
  const rows = [];
  for (let k = 0; k <= 9; k++) {
    const cell = hk[String(k)] || hk[k as unknown as string] || { assigned: 0, used: 0 };
    rows.push(
      <tr key={k}>
        <td>{k}</td>
        <td>{formatInt(cell.assigned || 0)}</td>
        <td>{formatInt(cell.used || 0)}</td>
      </tr>,
    );
  }
  return (
    <section className={section.section}>
      <h3 className={section.title}>Group hotkeys</h3>
      <table className={styles.table}>
        <thead>
          <tr>
            <th>Key</th>
            <th>Assigned</th>
            <th>Used</th>
          </tr>
        </thead>
        <tbody>{rows}</tbody>
      </table>
    </section>
  );
}
