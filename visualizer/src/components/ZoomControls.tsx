import { usePageState } from '../state/PageStateContext';
import { formatTimeMs } from '../data/format';
import { chooseBucketWidth } from '../data/timelineEvents';
import styles from './ZoomControls.module.css';

interface Props {
  chartWidthPx: number;
}

export function ZoomControls({ chartWidthPx }: Props) {
  const { pageState, dispatchers } = usePageState();
  const analysis = pageState.analysis;
  const zoom = pageState.zoomState;
  if (!analysis || !zoom) return null;
  const durationMs = analysis.match.durationMs;
  const visibleMs = zoom.visibleEndMs - zoom.visibleStartMs;
  const bucketWidthMs = chooseBucketWidth(visibleMs, chartWidthPx);

  // Logarithmic slider: ratio 0 = full match, ratio 1 = max zoom (1/1000 of match).
  const minVisible = Math.max(250, durationMs / 1000);
  const maxLog = Math.log(durationMs / minVisible);
  const curLog = Math.log(durationMs / Math.max(minVisible, visibleMs));
  const sliderValue = Math.round((curLog / maxLog) * 1000);

  const onSlider = (e: React.ChangeEvent<HTMLInputElement>) => {
    const ratio = Number(e.target.value) / 1000;
    const newVisible = Math.max(minVisible, durationMs * Math.exp(-maxLog * ratio));
    dispatchers.setSliderZoom(newVisible);
  };

  const onPan = (deltaFraction: number) =>
    dispatchers.panBy(visibleMs * deltaFraction);
  const onPanTo = (target: 'start' | 'end') => {
    if (target === 'start') dispatchers.panBy(-durationMs);
    else dispatchers.panBy(durationMs);
  };

  return (
    <section className={styles.controls}>
      <div className={styles.row}>
        <label htmlFor="tl-zoom" className={styles.lbl}>Zoom</label>
        <input
          id="tl-zoom"
          type="range"
          min={0}
          max={1000}
          step={1}
          value={sliderValue}
          onChange={onSlider}
          className={styles.slider}
        />
        <span className={styles.readout}>
          bucket {formatTimeMs(bucketWidthMs, durationMs)}
        </span>
      </div>
      <div className={styles.row}>
        <label className={styles.lbl}>Pan</label>
        <button type="button" className={styles.btn} onClick={() => onPanTo('start')}>⏮</button>
        <button type="button" className={styles.btn} onClick={() => onPan(-0.5)}>◀</button>
        <button type="button" className={styles.btn} onClick={() => onPan(0.5)}>▶</button>
        <button type="button" className={styles.btn} onClick={() => onPanTo('end')}>⏭</button>
        <button type="button" className={styles.btn} onClick={dispatchers.resetZoom}>Reset zoom</button>
        <span className={styles.readout}>
          view: {formatTimeMs(zoom.visibleStartMs, durationMs)} – {formatTimeMs(zoom.visibleEndMs, durationMs)}
        </span>
      </div>
    </section>
  );
}
