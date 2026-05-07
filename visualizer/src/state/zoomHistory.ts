import type { ZoomHistory, ZoomHistoryEntry } from './types';

export type ZoomHistoryAction =
  | { type: 'BRUSH'; previous: ZoomHistoryEntry }
  | { type: 'BACK'; current: ZoomHistoryEntry }
  | { type: 'FORWARD'; current: ZoomHistoryEntry }
  | { type: 'RESET' }
  | { type: 'LOAD_FILE' };

export function applyZoomHistoryAction(state: ZoomHistory, action: ZoomHistoryAction): ZoomHistory {
  switch (action.type) {
    case 'BRUSH':
      // Push the prior view onto back; clear forward (browser-back semantics).
      return { back: [...state.back, action.previous], forward: [] };
    case 'BACK': {
      // Pop from back; push current onto forward.
      if (state.back.length === 0) return state;
      const back = state.back.slice(0, -1);
      return { back, forward: [...state.forward, action.current] };
    }
    case 'FORWARD': {
      if (state.forward.length === 0) return state;
      const forward = state.forward.slice(0, -1);
      return { back: [...state.back, action.current], forward };
    }
    case 'RESET':
    case 'LOAD_FILE':
      return { back: [], forward: [] };
  }
}
