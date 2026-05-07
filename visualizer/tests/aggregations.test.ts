import { describe, expect, it } from 'vitest';
import {
  aggregateProduction,
  aggregateHeroes,
  aggregateTransfers,
} from '../src/data/aggregations';
import { loadBase1, loadBase2 } from './fixtures';

describe('aggregateProduction', () => {
  for (const [name, load] of [['base_1', loadBase1], ['base_2', loadBase2]] as const) {
    it(`${name}: counts equal sum of order entries per category`, () => {
      const a = load();
      for (const player of a.players) {
        const agg = aggregateProduction(player);
        for (const cat of ['buildings', 'units', 'upgrades', 'items'] as const) {
          const orderLen = (player.production[cat]?.order ?? []).length;
          const aggSum = agg[cat].reduce((s, r) => s + r.count, 0);
          expect(aggSum).toBe(orderLen);
        }
      }
    });

    it(`${name}: rows are sorted alphabetically by display name within a category`, () => {
      const a = load();
      const player = a.players[0];
      if (!player) throw new Error('no player');
      const agg = aggregateProduction(player);
      for (const cat of ['buildings', 'units', 'upgrades', 'items'] as const) {
        for (let i = 1; i < agg[cat].length; i++) {
          const prev = agg[cat][i - 1]!.name;
          const cur = agg[cat][i]!.name;
          expect(prev.localeCompare(cur)).toBeLessThanOrEqual(0);
        }
      }
    });
  }
});

describe('aggregateHeroes', () => {
  it('preserves abilityOrder ordering and final levels', () => {
    const a = loadBase1();
    for (const player of a.players) {
      const heroes = aggregateHeroes(player);
      heroes.forEach((h, i) => {
        const sourceHero = player.heroes[i];
        if (!sourceHero) throw new Error('hero index mismatch');
        expect(h.id).toBe(sourceHero.id);
        expect(h.finalLevel).toBe(sourceHero.level);
        expect(h.abilityChain.length).toBe(sourceHero.abilityOrder.length);
        h.abilityChain.forEach((seg, j) => {
          const source = sourceHero.abilityOrder[j];
          if (!source) throw new Error('ability index mismatch');
          expect(seg.id).toBe(source.id);
          expect(seg.level).toBe(source.level);
        });
      });
    }
  });
});

describe('aggregateTransfers', () => {
  it('groups by (recipient, resource); sums match raw transfers', () => {
    const a = loadBase1();
    for (const player of a.players) {
      const agg = aggregateTransfers(player, a);
      let goldTotal = 0;
      let lumberTotal = 0;
      for (const t of player.resourceTransfers) {
        goldTotal += t.gold || 0;
        lumberTotal += t.lumber || 0;
      }
      const aggGold = agg.filter((r) => r.resource === 'gold').reduce((s, r) => s + r.total, 0);
      const aggLumber = agg.filter((r) => r.resource === 'lumber').reduce((s, r) => s + r.total, 0);
      expect(aggGold).toBe(goldTotal);
      expect(aggLumber).toBe(lumberTotal);
    }
  });

  it('returns empty array when there are no transfers', () => {
    const a = loadBase2();
    for (const player of a.players) {
      const agg = aggregateTransfers(player, a);
      if ((player.resourceTransfers ?? []).length === 0) {
        expect(agg).toEqual([]);
      }
    }
  });

  it('sorts rows by total amount descending', () => {
    const a = loadBase1();
    for (const player of a.players) {
      const agg = aggregateTransfers(player, a);
      for (let i = 1; i < agg.length; i++) {
        expect(agg[i - 1]!.total).toBeGreaterThanOrEqual(agg[i]!.total);
      }
    }
  });
});
