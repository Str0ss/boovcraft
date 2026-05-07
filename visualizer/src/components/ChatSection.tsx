import type { ChatMessage } from '../types/analysis';
import { formatTimeMs } from '../data/format';
import styles from './ChatSection.module.css';

interface Props { chat: ChatMessage[]; durationMs: number; }

export function ChatSection({ chat, durationMs }: Props) {
  return (
    <section className={styles.section}>
      <h2 className={styles.header}>Chat ({chat?.length ?? 0})</h2>
      {!chat || chat.length === 0 ? (
        <p className={styles.empty}>No in-game chat in this replay.</p>
      ) : (
        <ol className={styles.list}>
          {chat.map((msg, i) => {
            const channel = (msg.mode || 'all').toLowerCase();
            return (
              <li key={i} className={styles.row}>
                <span className={styles.time}>{formatTimeMs(msg.timeMs, durationMs)}</span>
                <span className={`${styles.channel} ${styles[`channel_${channel}`] ?? ''}`}>
                  {msg.mode || 'All'}
                </span>
                <span className={styles.sender}>
                  {msg.playerName || `(player ${msg.playerId})`}
                </span>
                <span className={styles.text}>{msg.text || ''}</span>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
