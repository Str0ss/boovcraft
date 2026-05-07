// TypeScript types for the Processor's *.analysis.json contract.
// Mirrors processor/DATA.md and specs/004-visualizer-tabs/contracts/input-contract.md.

export const ALL_ACTION_CATEGORIES = [
  'buildtrain', 'ability', 'item', 'removeunit', 'esc',
  'rightclick', 'select', 'selecthotkey', 'basic', 'assigngroup', 'subgroup',
] as const;

export type ActionCategory = (typeof ALL_ACTION_CATEGORIES)[number];

// 'transfer' is a synthetic category emitted by the visualizer when it folds
// player.resourceTransfers into the timeline event stream. It does NOT appear
// in the analysis JSON's actions.totals.
export const TIMELINE_CATEGORIES = [...ALL_ACTION_CATEGORIES, 'transfer'] as const;
export type TimelineCategory = (typeof TIMELINE_CATEGORIES)[number];

export const MAJOR_TIMELINE_CATEGORIES: readonly TimelineCategory[] = [
  'buildtrain', 'ability', 'item', 'removeunit', 'esc', 'transfer',
];
export const MINOR_TIMELINE_CATEGORIES: readonly TimelineCategory[] = [
  'rightclick', 'select', 'selecthotkey', 'basic', 'assigngroup', 'subgroup',
];

export interface MatchWinner { teamId: number; }

export interface Match {
  version: string;
  buildNumber: number;
  durationMs: number;
  gameType: string;
  matchup: string;
  startSpots: number;
  expansion: boolean;
  gameName: string;
  creator: string;
  randomSeed: number;
  winner: MatchWinner | null;
}

export interface Settings {
  speed?: string;
  observerMode?: string;
  fixedTeams?: boolean;
  teamsTogether?: boolean;
  randomRaces?: boolean;
  randomHero?: boolean;
  [key: string]: unknown;
}

export interface MapInfo {
  path?: string;
  file?: string;
  [key: string]: unknown;
}

export interface EntityRef {
  id: string;
  name: string;
  unknown: boolean;
}

export interface ProductionEntry extends EntityRef {
  timeMs: number;
}

export interface ProductionSummaryEntry extends EntityRef {
  count: number;
}

export interface ProductionCategoryBlock {
  order: ProductionEntry[];
  summary: Record<string, ProductionSummaryEntry>;
}

export interface Production {
  buildings: ProductionCategoryBlock;
  units: ProductionCategoryBlock;
  upgrades: ProductionCategoryBlock;
  items: ProductionCategoryBlock;
}

export interface AbilityLearn extends EntityRef {
  timeMs: number;
  level: number;
}

export interface Hero extends EntityRef {
  level: number;
  abilityOrder: AbilityLearn[];
  abilitySummary: Record<string, EntityRef & { level: number }>;
}

export interface ResourceTransfer {
  fromSlot: number;
  toPlayerId: number;
  toPlayerName: string;
  gold: number;
  lumber: number;
  timeMs: number;
}

export interface TimedAction {
  timeMs: number;
  category: ActionCategory;
}

export interface ApmTimeline {
  bucketWidthMs: number;
  buckets: number[];
}

export interface PlayerActions {
  apmTimeline: ApmTimeline;
  totals: Record<string, number>;
  timedActions: TimedAction[];
}

export interface GroupHotkeyCell {
  assigned: number;
  used: number;
}

export interface Player {
  id: number;
  name: string;
  teamId: number;
  color: string;
  race: 'H' | 'O' | 'U' | 'N' | 'R';
  raceDetected: 'H' | 'O' | 'U' | 'N';
  apm: number;
  isWinner: boolean;
  actions: PlayerActions;
  groupHotkeys: Record<string, GroupHotkeyCell>;
  heroes: Hero[];
  production: Production;
  resourceTransfers: ResourceTransfer[];
}

export interface ChatMessage {
  playerId: number;
  playerName: string;
  mode: string;
  text: string;
  timeMs: number;
}

export interface Diagnostics {
  parserId: string;
  parserParseTimeMs: number;
  unmappedEntityIds: { category: string; id: string }[];
  analyzerVersion: string;
}

export interface AnalysisJson {
  match: Match;
  settings: Settings;
  map: MapInfo;
  players: Player[];
  observers: string[];
  chat: ChatMessage[];
  diagnostics: Diagnostics;
}
