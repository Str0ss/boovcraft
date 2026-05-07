import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react';
import type { TimelineCategory } from '../types/analysis';
import {
  ERR_PARSE,
  ERR_READ,
  ERR_NO_FILE,
  validateAnalysisShape,
} from '../data/validate';
import {
  INITIAL_PAGE_STATE,
  EMPTY_ZOOM_HISTORY,
  makeAllEnabledFilterState,
  type PageState,
  type Tab,
  type ZoomState,
} from './types';
import { applyZoomHistoryAction, type ZoomHistoryAction } from './zoomHistory';
import { applyFilterAction, type FilterAction } from './filterState';

interface Dispatchers {
  loadFile(file: File | null): void;
  setActiveTab(tab: Tab): void;
  brushZoom(range: ZoomState): void;
  setSliderZoom(visibleMs: number): void;
  panBy(deltaMs: number): void;
  resetZoom(): void;
  zoomBack(): void;
  zoomForward(): void;
  toggleCategory(category: TimelineCategory): void;
  setBulkCategoryFilter(group: 'major' | 'minor' | 'all', enabled: boolean): void;
  clearError(): void;
}

interface ContextValue {
  pageState: PageState;
  dispatchers: Dispatchers;
}

const PageStateContext = createContext<ContextValue | null>(null);

export function PageStateProvider({ children }: { children: ReactNode }) {
  const [pageState, setPageState] = useState<PageState>(INITIAL_PAGE_STATE);

  const dispatchZoomHistory = useCallback((action: ZoomHistoryAction) => {
    setPageState((prev) => ({
      ...prev,
      zoomHistory: applyZoomHistoryAction(prev.zoomHistory, action),
    }));
  }, []);

  const dispatchFilter = useCallback((action: FilterAction) => {
    setPageState((prev) => ({
      ...prev,
      filterState: applyFilterAction(prev.filterState, action),
    }));
  }, []);

  const setError = useCallback((message: string) => {
    // Clear any stale data — error replaces the prior render entirely.
    setPageState({ ...INITIAL_PAGE_STATE, errorMessage: message });
  }, []);

  const loadFile = useCallback((file: File | null) => {
    if (!file) {
      setError(ERR_NO_FILE);
      return;
    }
    const reader = new FileReader();
    reader.onerror = () => setError(ERR_READ);
    reader.onload = () => {
      const text = String(reader.result ?? '');
      let parsed: unknown;
      try {
        parsed = JSON.parse(text);
      } catch {
        setError(ERR_PARSE);
        return;
      }
      const result = validateAnalysisShape(parsed);
      if (!result.ok) {
        setError(result.message);
        return;
      }
      const durationMs = result.value.match.durationMs;
      setPageState({
        loadedFile: { name: file.name, loadedAt: Date.now() },
        analysis: result.value,
        errorMessage: null,
        activeTab: 'summary',
        zoomState: { visibleStartMs: 0, visibleEndMs: durationMs },
        zoomHistory: EMPTY_ZOOM_HISTORY,
        filterState: makeAllEnabledFilterState(),
      });
    };
    reader.readAsText(file);
  }, []);

  const setActiveTab = useCallback((tab: Tab) => {
    setPageState((prev) => (prev.analysis ? { ...prev, activeTab: tab } : prev));
  }, []);

  const brushZoom = useCallback((range: ZoomState) => {
    setPageState((prev) => {
      if (!prev.zoomState) return prev;
      return {
        ...prev,
        zoomState: range,
        zoomHistory: applyZoomHistoryAction(prev.zoomHistory, {
          type: 'BRUSH',
          previous: prev.zoomState,
        }),
      };
    });
  }, []);

  const setSliderZoom = useCallback((visibleMs: number) => {
    setPageState((prev) => {
      if (!prev.analysis || !prev.zoomState) return prev;
      const durationMs = prev.analysis.match.durationMs;
      const center = (prev.zoomState.visibleStartMs + prev.zoomState.visibleEndMs) / 2;
      let start = Math.max(0, center - visibleMs / 2);
      const end = Math.min(durationMs, start + visibleMs);
      start = Math.max(0, end - visibleMs);
      return { ...prev, zoomState: { visibleStartMs: start, visibleEndMs: end } };
    });
  }, []);

  const panBy = useCallback((deltaMs: number) => {
    setPageState((prev) => {
      if (!prev.analysis || !prev.zoomState) return prev;
      const durationMs = prev.analysis.match.durationMs;
      const w = prev.zoomState.visibleEndMs - prev.zoomState.visibleStartMs;
      let start = Math.max(0, Math.min(durationMs - w, prev.zoomState.visibleStartMs + deltaMs));
      return { ...prev, zoomState: { visibleStartMs: start, visibleEndMs: start + w } };
    });
  }, []);

  const resetZoom = useCallback(() => {
    setPageState((prev) => {
      if (!prev.analysis) return prev;
      const durationMs = prev.analysis.match.durationMs;
      return {
        ...prev,
        zoomState: { visibleStartMs: 0, visibleEndMs: durationMs },
        zoomHistory: applyZoomHistoryAction(prev.zoomHistory, { type: 'RESET' }),
      };
    });
  }, []);

  const zoomBack = useCallback(() => {
    setPageState((prev) => {
      if (!prev.zoomState || prev.zoomHistory.back.length === 0) return prev;
      const target = prev.zoomHistory.back[prev.zoomHistory.back.length - 1];
      if (!target) return prev;
      return {
        ...prev,
        zoomState: { ...target },
        zoomHistory: applyZoomHistoryAction(prev.zoomHistory, {
          type: 'BACK',
          current: prev.zoomState,
        }),
      };
    });
  }, []);

  const zoomForward = useCallback(() => {
    setPageState((prev) => {
      if (!prev.zoomState || prev.zoomHistory.forward.length === 0) return prev;
      const target = prev.zoomHistory.forward[prev.zoomHistory.forward.length - 1];
      if (!target) return prev;
      return {
        ...prev,
        zoomState: { ...target },
        zoomHistory: applyZoomHistoryAction(prev.zoomHistory, {
          type: 'FORWARD',
          current: prev.zoomState,
        }),
      };
    });
  }, []);

  const toggleCategory = useCallback((category: TimelineCategory) => {
    dispatchFilter({ type: 'TOGGLE', category });
  }, [dispatchFilter]);

  const setBulkCategoryFilter = useCallback((group: 'major' | 'minor' | 'all', enabled: boolean) => {
    dispatchFilter({ type: 'SET_GROUP', group, enabled });
  }, [dispatchFilter]);

  const clearError = useCallback(() => {
    setPageState((prev) => (prev.errorMessage === null ? prev : { ...prev, errorMessage: null }));
  }, []);

  // Suppress unused-var warning (zoom-history dispatcher is exposed for future direct use).
  void dispatchZoomHistory;

  const value = useMemo<ContextValue>(() => ({
    pageState,
    dispatchers: {
      loadFile,
      setActiveTab,
      brushZoom,
      setSliderZoom,
      panBy,
      resetZoom,
      zoomBack,
      zoomForward,
      toggleCategory,
      setBulkCategoryFilter,
      clearError,
    },
  }), [
    pageState, loadFile, setActiveTab, brushZoom, setSliderZoom, panBy,
    resetZoom, zoomBack, zoomForward, toggleCategory, setBulkCategoryFilter,
    clearError,
  ]);

  return <PageStateContext.Provider value={value}>{children}</PageStateContext.Provider>;
}

export function usePageState(): ContextValue {
  const ctx = useContext(PageStateContext);
  if (!ctx) throw new Error('usePageState must be used within PageStateProvider');
  return ctx;
}
