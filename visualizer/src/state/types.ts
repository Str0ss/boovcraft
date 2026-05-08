import type { AnalysisJson, TimelineCategory } from '../types/analysis';

export type Tab = 'summary' | 'timelines' | 'team' | 'analysis' | 'map';

export interface ZoomState {
  visibleStartMs: number;
  visibleEndMs: number;
}

export interface ZoomHistoryEntry {
  visibleStartMs: number;
  visibleEndMs: number;
}

export interface ZoomHistory {
  back: ZoomHistoryEntry[];
  forward: ZoomHistoryEntry[];
}

export interface FilterState {
  enabled: Record<TimelineCategory, boolean>;
}

export interface PageState {
  loadedFile: { name: string; loadedAt: number } | null;
  analysis: AnalysisJson | null;
  errorMessage: string | null;
  activeTab: Tab;
  zoomState: ZoomState | null;
  zoomHistory: ZoomHistory;
  filterState: FilterState;
}

export const TABS: { id: Tab; label: string }[] = [
  { id: 'summary', label: 'Summary' },
  { id: 'timelines', label: 'Timelines' },
  { id: 'team', label: 'Team' },
  { id: 'analysis', label: 'Analysis' },
  { id: 'map', label: 'Map' },
];

export const EMPTY_ZOOM_HISTORY: ZoomHistory = { back: [], forward: [] };

export function makeAllEnabledFilterState(): FilterState {
  return {
    enabled: {
      buildtrain: true, ability: true, item: true, removeunit: true, esc: true,
      transfer: true, rightclick: true, select: true, selecthotkey: true,
      basic: true, assigngroup: true, subgroup: true,
    },
  };
}

export const INITIAL_PAGE_STATE: PageState = {
  loadedFile: null,
  analysis: null,
  errorMessage: null,
  activeTab: 'summary',
  zoomState: null,
  zoomHistory: EMPTY_ZOOM_HISTORY,
  filterState: makeAllEnabledFilterState(),
};
