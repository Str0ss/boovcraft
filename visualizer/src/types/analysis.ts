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
  // Feature 007 additive extensions (optional for forward compatibility
  // with pre-007 *.analysis.json files).
  cohesionMetricGaps?: { metric: string; reason: string }[];
  itemAttributeGaps?: { id: string; category: 'item' | 'hero' }[];
}

// === Feature 007: team cohesion analysis types ============================
// See specs/007-team-cohesion-analysis/data-model.md § Outputs

export interface Centroid {
  slot: number;
  x: number | null;
  y: number | null;
  source: 'commanded' | 'missing';
}

export interface AlliedDistance {
  fromSlot: number;
  toSlot: number;
  distance: number;
}

export interface SplitEngagement {
  flagged: boolean;
  distance: number;
  referenceAuraId: string;
  referenceAuraName: string;
  flaggedSlots: number[];
}

export interface FocusFire {
  dominantTargetSlot: number | null;
  dominantTargetEntity: EntityRef;
  cohesionPercent: number;
  contributingPlayers: { slot: number; attackCount: number }[];
}

export interface Ping {
  fromSlot: number;
  x: number;
  y: number;
  timeMs: number;
  duration: number;
  respondedBySlot: number[];
  engagedElsewhereSlot: number[];
}

export interface KillEstimate {
  victimHandle: number[];
  victimEntity: EntityRef;
  victimSide: 'teamA' | 'teamB';
  victimValue: number;
  killTimeMs: number;
  credits: { slot: number; fraction: number }[];
}

export interface Battle {
  index: number;
  startMs: number;
  endMs: number;
  sides: { teamA: number[]; teamB: number[] };
  centroids: Centroid[];
  alliedDistances: AlliedDistance[];
  splitEngagement: SplitEngagement;
  focusFire: FocusFire | null;
  pings: Ping[];
  kills: KillEstimate[];
}

export interface ItemTransfer {
  fromSlot: number;
  toSlot: number;
  item: EntityRef;
  timeMs: number;
  recipientFitClass: 'good' | 'wrong' | 'neutral' | 'unknown';
  recipientHero: EntityRef;
}

export type SupportEvent =
  | {
      type: 'missedSave';
      deceasedSlot: number;
      deceasedHero: EntityRef;
      holderSlot: number;
      holderHero: EntityRef;
      itemId: string;
      itemName: string;
      deathTimeMs: number;
      distanceAtDeath: number;
    }
  | {
      type: 'supportSpellCast';
      casterSlot: number;
      casterHero: EntityRef;
      targetSlot: number;
      targetEntity: EntityRef;
      spell: EntityRef;
      timeMs: number;
    };

export interface AnnotatedTransfer {
  fromSlot: number;
  toPlayerId: number;
  toPlayerName: string;
  gold: number;
  lumber: number;
  timeMs: number;
  purposeHint: 'tierUpAssist' | 'baseDefense' | 'lateGameTopUp' | 'none';
}

export interface GenerosityRow {
  slot: number;
  name: string;
  sentGold: number;
  sentLumber: number;
  estimatedMinedGold: number | null;
  estimatedMinedLumber: number | null;
  generosityPercent: number | null;
}

export interface TeamPlayer {
  slot: number;
  name: string;
  killParticipationPercent: number | null;
}

export interface BattleTEI {
  battleIndex: number;
  teamSideTei: { teamA: number | null; teamB: number | null };
  perPlayerTei: { slot: number; tei: number | null }[];
}

export interface Attribution {
  playerSlot: number;
  battleIndex: number;
  reason: 'splitEngagement';
}

export type EvidenceRef =
  | { kind: 'battle'; battleIndex: number }
  | { kind: 'supportEvent'; index: number }
  | { kind: 'itemTransfer'; index: number }
  | { kind: 'globalFlag'; name: string };

export interface ExecutiveFinding {
  rank: number;
  weightedSeverity: number;
  kind:
    | 'splitEngagement'
    | 'missedSave'
    | 'lowTei'
    | 'sharedControlDisabled'
    | 'wrongItemTransfer'
    | 'ignoredPing';
  battleIndex: number | null;
  summary: string;
  evidenceRef: EvidenceRef;
}

// Feature 009 — Map Tab centroid timeline
export interface TimelineCentroid {
  slot: number;
  x: number | null;
  y: number | null;
  // 'commanded' = fresh centroid in last 60s window
  // 'stale'     = fallback to last-known position (any age) so the
  //               player remains visible on the map between commands
  // 'starting'  = forward-look fallback: player hasn't moved yet, but
  //               here's where they'll first appear (their start spot)
  // 'missing'   = no commanded position has ever existed for this slot
  source: 'commanded' | 'stale' | 'starting' | 'missing';
  combatFood: number;
  combatUnitCount: number;
}

export interface CentroidTimelineBucket {
  tMs: number;
  centroids: TimelineCentroid[];
}

export interface CentroidTimeline {
  bucketWidthMs: number;
  buckets: CentroidTimelineBucket[];
}

export type TeamBlock =
  | {
      applicable: false;
      reason: 'noAllies' | 'ffa' | 'noBattlesDetected' | 'preFeature007File';
    }
  | {
      applicable: true;
      sharedControl: { enabled: boolean };
      findings: string[];
      battles: Battle[];
      itemTransfers: ItemTransfer[];
      supportEvents: SupportEvent[];
      resourceCooperation: {
        transfers: AnnotatedTransfer[];
        generosity: GenerosityRow[];
      };
      players: TeamPlayer[];
      battleSummary: {
        tei: BattleTEI[];
        attributions: Attribution[];
        executive: ExecutiveFinding[];
      };
      // Feature 009 — Map Tab. Optional for forward/backward compat
      // with files produced before feature 009's processor lands.
      centroidTimeline?: CentroidTimeline;
    };

// =========================================================================

export interface AnalysisJson {
  match: Match;
  settings: Settings;
  map: MapInfo;
  players: Player[];
  observers: string[];
  chat: ChatMessage[];
  diagnostics: Diagnostics;
  // `team` is OPTIONAL for backward compatibility with pre-feature-006
  // *.analysis.json files. Absence triggers the "preFeature007File"
  // empty-state in the Visualizer.
  team?: TeamBlock;
}
