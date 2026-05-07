import { describe, expect, it } from 'vitest';
import { applyZoomHistoryAction } from '../src/state/zoomHistory';
import { EMPTY_ZOOM_HISTORY } from '../src/state/types';

const A = { visibleStartMs: 0, visibleEndMs: 100 };
const B = { visibleStartMs: 10, visibleEndMs: 50 };
const C = { visibleStartMs: 20, visibleEndMs: 30 };

describe('applyZoomHistoryAction', () => {
  it('BRUSH pushes prior view onto back; clears forward', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BRUSH', previous: A });
    expect(s1.back).toEqual([A]);
    expect(s1.forward).toEqual([]);

    const s2 = applyZoomHistoryAction(s1, { type: 'BRUSH', previous: B });
    expect(s2.back).toEqual([A, B]);
    expect(s2.forward).toEqual([]);
  });

  it('BACK pops back-stack and pushes current onto forward', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BRUSH', previous: A });
    const s2 = applyZoomHistoryAction(s1, { type: 'BACK', current: B });
    expect(s2.back).toEqual([]);
    expect(s2.forward).toEqual([B]);
  });

  it('BACK on empty stack is a no-op', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BACK', current: A });
    expect(s1).toBe(EMPTY_ZOOM_HISTORY);
  });

  it('FORWARD pops forward-stack and pushes current onto back', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BRUSH', previous: A });
    const s2 = applyZoomHistoryAction(s1, { type: 'BACK', current: B });
    const s3 = applyZoomHistoryAction(s2, { type: 'FORWARD', current: A });
    expect(s3.back).toEqual([A]);
    expect(s3.forward).toEqual([]);
  });

  it('BRUSH after BACK clears forward (browser-back semantics)', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BRUSH', previous: A });
    const s2 = applyZoomHistoryAction(s1, { type: 'BACK', current: B });
    expect(s2.forward.length).toBe(1);
    const s3 = applyZoomHistoryAction(s2, { type: 'BRUSH', previous: C });
    expect(s3.forward).toEqual([]);
  });

  it('RESET clears both stacks', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BRUSH', previous: A });
    const s2 = applyZoomHistoryAction(s1, { type: 'BACK', current: B });
    const s3 = applyZoomHistoryAction(s2, { type: 'RESET' });
    expect(s3).toEqual(EMPTY_ZOOM_HISTORY);
  });

  it('LOAD_FILE clears both stacks', () => {
    const s1 = applyZoomHistoryAction(EMPTY_ZOOM_HISTORY, { type: 'BRUSH', previous: A });
    const s2 = applyZoomHistoryAction(s1, { type: 'LOAD_FILE' });
    expect(s2).toEqual(EMPTY_ZOOM_HISTORY);
  });
});
