import { useEffect, useMemo, useRef } from 'react';
import ReactECharts from 'echarts-for-react';
import * as echarts from 'echarts';
import type { EChartsOption } from 'echarts';
import type { Player, TimelineCategory } from '../types/analysis';
import { MAJOR_TIMELINE_CATEGORIES, MINOR_TIMELINE_CATEGORIES } from '../types/analysis';
import {
  bucketEvents,
  chooseBucketWidth,
  clampBrushedRange,
  collectPlayerEvents,
  filterBuckets,
} from '../data/timelineEvents';
import { formatTimeMs } from '../data/format';
import type { FilterState, ZoomState } from '../state/types';
import { usePageState } from '../state/PageStateContext';
import styles from './PlayerHistogram.module.css';

export const CATEGORY_COLOR: Record<TimelineCategory, string> = {
  buildtrain: '#3a86ff',
  ability: '#9d4edd',
  item: '#ffb703',
  removeunit: '#fb5607',
  esc: '#8d99ae',
  transfer: '#06d6a0',
  rightclick: '#cad2c5',
  select: '#a8b5a0',
  selecthotkey: '#84a98c',
  basic: '#bdb2a7',
  assigngroup: '#dda15e',
  subgroup: '#bdb2a7',
};

export const CATEGORY_LABEL: Record<TimelineCategory, string> = {
  buildtrain: 'Build / train',
  ability: 'Ability',
  item: 'Item',
  removeunit: 'Remove unit',
  esc: 'Esc',
  transfer: 'Transfer',
  rightclick: 'Right-click',
  select: 'Select',
  selecthotkey: 'Hotkey select',
  basic: 'Basic',
  assigngroup: 'Assign group',
  subgroup: 'Subgroup',
};

const CHART_GROUP_ID = 'boovcraft-timelines';
const CHART_HEIGHT_PX = 88;

interface Props {
  player: Player;
  zoomState: ZoomState;
  filterState: FilterState;
  durationMs: number;
  chartWidthPx: number;
}

const ALL_CATEGORIES_ORDERED: TimelineCategory[] = [
  ...MINOR_TIMELINE_CATEGORIES,
  ...MAJOR_TIMELINE_CATEGORIES,
];

export function PlayerHistogram({
  player, zoomState, filterState, durationMs, chartWidthPx,
}: Props) {
  const { dispatchers } = usePageState();
  const chartRef = useRef<ReactECharts | null>(null);

  const events = useMemo(() => collectPlayerEvents(player), [player]);

  const option: EChartsOption = useMemo(() => {
    const visibleMs = zoomState.visibleEndMs - zoomState.visibleStartMs;
    const bucketWidthMs = chooseBucketWidth(visibleMs, chartWidthPx);
    const rawBuckets = bucketEvents(
      events, zoomState.visibleStartMs, zoomState.visibleEndMs, bucketWidthMs,
    );
    const buckets = filterBuckets(rawBuckets, filterState);
    const xCategories = buckets.map((b) => (b.start + b.end) / 2);

    const series: EChartsOption['series'] = ALL_CATEGORIES_ORDERED
      .filter((c) => filterState.enabled[c])
      .map((cat) => ({
        name: CATEGORY_LABEL[cat],
        type: 'bar',
        stack: 'total',
        data: buckets.map((b) => b.counts[cat] ?? 0),
        itemStyle: { color: CATEGORY_COLOR[cat], borderWidth: 0 },
        barCategoryGap: '5%',
        emphasis: { focus: 'series' as const },
      }));

    return {
      animation: false,
      grid: { left: 8, right: 8, top: 6, bottom: 28 },
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'shadow' },
        confine: true,
        formatter: (params: unknown) => {
          if (!Array.isArray(params) || params.length === 0) return '';
          const first = params[0] as { dataIndex: number };
          const idx = first.dataIndex;
          const b = buckets[idx];
          if (!b) return '';
          const lines: string[] = [];
          lines.push(`${formatTimeMs(b.start, durationMs)} – ${formatTimeMs(b.end, durationMs)}`);
          lines.push(`Total: ${b.total}`);
          for (const p of params as { color: string; seriesName: string; value: number }[]) {
            if (!p.value) continue;
            lines.push(
              `<span style="display:inline-block;width:10px;height:10px;background:${p.color};margin-right:6px;border-radius:2px;"></span>${p.seriesName}: ${p.value}`,
            );
          }
          return lines.join('<br/>');
        },
      },
      xAxis: {
        type: 'category',
        data: xCategories,
        axisLine: { lineStyle: { color: '#4a5160' } },
        axisTick: { alignWithLabel: true },
        axisLabel: {
          color: '#9aa0a6',
          fontSize: 10,
          formatter: (value: string) => formatTimeMs(Number(value), durationMs),
          interval: 'auto',
        },
        splitLine: { show: false },
      },
      yAxis: {
        type: 'value',
        show: false,
        max: (v: { max: number }) => Math.max(1, v.max),
      },
      brush: {
        toolbox: ['lineX', 'clear'],
        xAxisIndex: 0,
        brushType: 'lineX',
        brushMode: 'single',
        throttleType: 'debounce',
        throttleDelay: 30,
        brushStyle: {
          color: 'rgba(127, 168, 223, 0.18)',
          borderColor: '#7fa8df',
          borderWidth: 1,
        },
      },
      series,
    } satisfies EChartsOption;
  }, [events, zoomState, filterState, chartWidthPx, durationMs]);

  // Wire the ECharts brush event → brushZoom dispatcher.
  useEffect(() => {
    const inst = chartRef.current?.getEchartsInstance();
    if (!inst) return;

    const handleBrush = (params: unknown) => {
      // ECharts dispatches "brushEnd" / "brushSelected" with batch info; we listen for brushEnd.
      const evt = params as { areas?: { coordRange?: [number, number] }[] };
      const area = evt.areas?.[0];
      if (!area || !area.coordRange) return;
      const [a, b] = area.coordRange;
      // coordRange values are *category-index numbers* on a category axis.
      const visibleMs = zoomState.visibleEndMs - zoomState.visibleStartMs;
      const visibleMsPerIndex = visibleMs / Math.max(1, ((option.xAxis as { data: number[] }).data?.length ?? 1));
      const startMs = zoomState.visibleStartMs + a * visibleMsPerIndex;
      const endMs = zoomState.visibleStartMs + b * visibleMsPerIndex;
      const range = clampBrushedRange({ startMs, endMs }, durationMs);
      // Dead-zone: if the brushed pixel range is < 5px, treat as click.
      const pxPerMs = chartWidthPx / Math.max(1, visibleMs);
      const brushedPx = (range.visibleEndMs - range.visibleStartMs) * pxPerMs;
      if (brushedPx < 5) {
        inst.dispatchAction({ type: 'brush', areas: [] });
        return;
      }
      dispatchers.brushZoom(range);
      inst.dispatchAction({ type: 'brush', areas: [] });
    };

    inst.on('brushEnd', handleBrush);
    return () => {
      inst.off('brushEnd', handleBrush);
    };
  }, [dispatchers, zoomState, durationMs, chartWidthPx, option]);

  // Connect this chart instance to the synchronized group.
  const onChartReady = (inst: echarts.ECharts) => {
    inst.group = CHART_GROUP_ID;
    echarts.connect(CHART_GROUP_ID);
  };

  // Escape cancels in-progress brush.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== 'Escape') return;
      const inst = chartRef.current?.getEchartsInstance();
      inst?.dispatchAction({ type: 'brush', areas: [] });
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, []);

  return (
    <div className={styles.host} style={{ height: CHART_HEIGHT_PX }}>
      <ReactECharts
        ref={chartRef}
        option={option}
        style={{ height: '100%', width: '100%' }}
        notMerge
        lazyUpdate={false}
        onChartReady={onChartReady}
      />
    </div>
  );
}
