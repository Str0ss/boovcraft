import { describe, expect, it } from 'vitest';
import { applyFilterAction } from '../src/state/filterState';
import { makeAllEnabledFilterState } from '../src/state/types';

describe('applyFilterAction', () => {
  it('TOGGLE flips a single category', () => {
    const s = makeAllEnabledFilterState();
    const after = applyFilterAction(s, { type: 'TOGGLE', category: 'rightclick' });
    expect(after.enabled.rightclick).toBe(false);
    expect(after.enabled.select).toBe(true); // others unchanged
  });

  it('TOGGLE applied twice restores prior state', () => {
    const s = makeAllEnabledFilterState();
    const t1 = applyFilterAction(s, { type: 'TOGGLE', category: 'rightclick' });
    const t2 = applyFilterAction(t1, { type: 'TOGGLE', category: 'rightclick' });
    expect(t2.enabled.rightclick).toBe(true);
  });

  it('SET_GROUP major flips all major categories atomically', () => {
    const s = makeAllEnabledFilterState();
    const after = applyFilterAction(s, { type: 'SET_GROUP', group: 'major', enabled: false });
    for (const cat of ['buildtrain', 'ability', 'item', 'removeunit', 'esc', 'transfer'] as const) {
      expect(after.enabled[cat]).toBe(false);
    }
    for (const cat of ['rightclick', 'select', 'selecthotkey', 'basic', 'assigngroup', 'subgroup'] as const) {
      expect(after.enabled[cat]).toBe(true);
    }
  });

  it('SET_GROUP minor flips all minor categories', () => {
    const s = makeAllEnabledFilterState();
    const after = applyFilterAction(s, { type: 'SET_GROUP', group: 'minor', enabled: false });
    for (const cat of ['rightclick', 'select', 'selecthotkey', 'basic', 'assigngroup', 'subgroup'] as const) {
      expect(after.enabled[cat]).toBe(false);
    }
  });

  it('SET_GROUP all flips every category', () => {
    const s = makeAllEnabledFilterState();
    const after = applyFilterAction(s, { type: 'SET_GROUP', group: 'all', enabled: false });
    for (const v of Object.values(after.enabled)) expect(v).toBe(false);
  });

  it('RESET returns to all-enabled', () => {
    const s = makeAllEnabledFilterState();
    const off = applyFilterAction(s, { type: 'SET_GROUP', group: 'all', enabled: false });
    const reset = applyFilterAction(off, { type: 'RESET' });
    for (const v of Object.values(reset.enabled)) expect(v).toBe(true);
  });
});
