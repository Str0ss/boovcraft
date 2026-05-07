import { useRef } from 'react';
import { usePageState } from '../state/PageStateContext';
import styles from './FilePicker.module.css';

export function FilePicker() {
  const { pageState, dispatchers } = usePageState();
  const ref = useRef<HTMLInputElement | null>(null);

  return (
    <p className={styles.picker}>
      <label htmlFor="picker" className={styles.label}>Choose analysis file:</label>
      <input
        type="file"
        id="picker"
        ref={ref}
        accept=".json,application/json"
        onChange={(e) => {
          const file = e.target.files?.[0] ?? null;
          dispatchers.loadFile(file);
        }}
      />
      {pageState.loadedFile && (
        <span className={styles.loaded}>{pageState.loadedFile.name}</span>
      )}
    </p>
  );
}
