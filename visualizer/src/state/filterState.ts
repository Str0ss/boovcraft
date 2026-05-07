import {
  MAJOR_TIMELINE_CATEGORIES,
  MINOR_TIMELINE_CATEGORIES,
  TIMELINE_CATEGORIES,
  type TimelineCategory,
} from '../types/analysis';
import { makeAllEnabledFilterState, type FilterState } from './types';

export type FilterAction =
  | { type: 'TOGGLE'; category: TimelineCategory }
  | { type: 'SET_GROUP'; group: 'major' | 'minor' | 'all'; enabled: boolean }
  | { type: 'RESET' };

function categoriesInGroup(group: 'major' | 'minor' | 'all'): readonly TimelineCategory[] {
  if (group === 'major') return MAJOR_TIMELINE_CATEGORIES;
  if (group === 'minor') return MINOR_TIMELINE_CATEGORIES;
  return TIMELINE_CATEGORIES;
}

export function applyFilterAction(state: FilterState, action: FilterAction): FilterState {
  switch (action.type) {
    case 'TOGGLE': {
      return {
        enabled: { ...state.enabled, [action.category]: !state.enabled[action.category] },
      };
    }
    case 'SET_GROUP': {
      const cats = categoriesInGroup(action.group);
      const next = { ...state.enabled };
      for (const c of cats) next[c] = action.enabled;
      return { enabled: next };
    }
    case 'RESET':
      return makeAllEnabledFilterState();
  }
}
