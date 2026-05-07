import type { AnalysisJson, Player } from '../types/analysis';

export interface ProdRow {
  id: string;
  name: string;
  unknown: boolean;
  count: number;
}

export interface ProductionAggregation {
  buildings: ProdRow[];
  units: ProdRow[];
  upgrades: ProdRow[];
  items: ProdRow[];
}

export interface HeroAggregation {
  id: string;
  name: string;
  unknown: boolean;
  finalLevel: number;
  abilityChain: { id: string; name: string; unknown: boolean; level: number }[];
}

export interface TransferAggregation {
  recipientName: string;
  recipientId: number;
  resource: 'gold' | 'lumber';
  total: number;
  count: number;
}

const PRODUCTION_KEYS: (keyof ProductionAggregation)[] = [
  'buildings', 'units', 'upgrades', 'items',
];

export function aggregateProduction(player: Player): ProductionAggregation {
  const out: ProductionAggregation = { buildings: [], units: [], upgrades: [], items: [] };
  for (const key of PRODUCTION_KEYS) {
    const block = player.production?.[key];
    if (!block) continue;
    const rows: ProdRow[] = Object.values(block.summary || {}).map((entry) => ({
      id: entry.id,
      name: entry.name,
      unknown: entry.unknown === true,
      count: entry.count || 0,
    }));
    rows.sort((a, b) => a.name.localeCompare(b.name));
    out[key] = rows;
  }
  return out;
}

export function aggregateHeroes(player: Player): HeroAggregation[] {
  return (player.heroes || []).map((hero) => ({
    id: hero.id,
    name: hero.name,
    unknown: hero.unknown === true,
    finalLevel: hero.level || 0,
    abilityChain: (hero.abilityOrder || []).map((ab) => ({
      id: ab.id,
      name: ab.name,
      unknown: ab.unknown === true,
      level: ab.level,
    })),
  }));
}

function playerNameFromId(playerId: number, analysis: AnalysisJson | null): string | null {
  if (!analysis) return null;
  const found = (analysis.players || []).find((p) => p.id === playerId);
  return found ? found.name : null;
}

export function aggregateTransfers(player: Player, analysis: AnalysisJson | null): TransferAggregation[] {
  const map = new Map<string, TransferAggregation>();
  for (const t of player.resourceTransfers || []) {
    const recipientName =
      t.toPlayerName || playerNameFromId(t.toPlayerId, analysis) || `Player ${t.toPlayerId}`;
    for (const resource of ['gold', 'lumber'] as const) {
      const amount = t[resource] || 0;
      if (amount <= 0) continue;
      const key = `${t.toPlayerId}|${resource}`;
      const cur =
        map.get(key) ?? {
          recipientName,
          recipientId: t.toPlayerId,
          resource,
          total: 0,
          count: 0,
        };
      cur.total += amount;
      cur.count += 1;
      map.set(key, cur);
    }
  }
  return [...map.values()].sort((a, b) => b.total - a.total);
}
