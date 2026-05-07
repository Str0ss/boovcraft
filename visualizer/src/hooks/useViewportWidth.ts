import { useEffect, useRef, useState } from 'react';

const TIMELINES_CHART_INSET_PX = 192; // left-column meta width + gutters

export interface UseViewportWidthResult {
  containerRef: (el: HTMLDivElement | null) => void;
  chartWidthPx: number;
}

export function useViewportWidth(): UseViewportWidthResult {
  const [chartWidthPx, setChartWidthPx] = useState<number>(900);
  const observerRef = useRef<ResizeObserver | null>(null);

  const containerRef = (el: HTMLDivElement | null) => {
    if (observerRef.current) {
      observerRef.current.disconnect();
      observerRef.current = null;
    }
    if (!el) return;
    const update = () => {
      const w = el.getBoundingClientRect().width;
      const candidate = Math.max(640, w - TIMELINES_CHART_INSET_PX);
      setChartWidthPx(candidate);
    };
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    observerRef.current = ro;
  };

  useEffect(() => () => observerRef.current?.disconnect(), []);

  return { containerRef, chartWidthPx };
}
