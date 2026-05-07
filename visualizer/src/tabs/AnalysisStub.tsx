import styles from './stub.module.css';

export function AnalysisStub() {
  return (
    <section className={styles.stub}>
      <h2 className={styles.heading}>Analysis (coming soon)</h2>
      <p className={styles.body}>
        This tab will host an LLM-ready textual analysis of the loaded replay
        — a separate analysis pipeline that has not yet been implemented.
      </p>
      <p className={styles.body}>
        Switch back to the Summary or Timelines tab for the data the
        visualizer currently surfaces.
      </p>
    </section>
  );
}
