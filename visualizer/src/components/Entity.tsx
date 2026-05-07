import type { EntityRef } from '../types/analysis';
import styles from './Entity.module.css';

interface EntityProps {
  entity: Pick<EntityRef, 'id' | 'name' | 'unknown'>;
  className?: string;
}

export function Entity({ entity, className }: EntityProps) {
  const cls = entity.unknown
    ? `${styles.entity} ${styles.unknown} ${className ?? ''}`
    : `${styles.entity} ${className ?? ''}`;
  return (
    <span className={cls.trim()} title={entity.unknown ? `Unknown entity id: ${entity.id}` : undefined}>
      {entity.name}
      {entity.unknown && <span className={styles.badge}>[?]</span>}
    </span>
  );
}
