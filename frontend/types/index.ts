// ── Dashboard Types ─────────────────────────────────────────────────────────

export interface RoyaltySummary {
  total_gross: number;
  total_net: number;
  total_fees: number;
  count: number;
  period_start: string | null;
  period_end: string | null;
  by_platform: Record<string, number>;
  by_type: Record<string, number>;
  by_work: Record<string, number>;
}

export interface RecentRoyalty {
  id: string;
  work: string;
  platform: string;
  type: string;
  amount: number;
  period: string;
  date: string;
}

export interface Work {
  id: string;
  title: string;
  isrc?: string;
  iswc?: string;
  splits_count: number;
  total_earnings: number;
  platforms: string[];
  status: string;
}

export interface SyncLicense {
  id: string;
  work: string;
  title: string;
  licensee: string;
  media_type: string;
  fee: number;
  currency: string;
  status: string;
  term_end: string | null;
}

export interface ReconciliationStatus {
  total_discrepancies: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  last_run: string;
}

export interface PendingSplit {
  work: string;
  missing: string;
  status: string;
  priority: string;
}

export interface Alert {
  type: string;
  message: string;
  date: string;
}

export interface DashboardData {
  summary: RoyaltySummary;
  recent_royalties: RecentRoyalty[];
  works: Work[];
  sync_licenses: SyncLicense[];
  reconciliation_status: ReconciliationStatus;
  pending_splits: PendingSplit[];
  alerts: Alert[];
  revenue_trend: { month: string; amount: number }[];
}

// ── Query/Chat Types ────────────────────────────────────────────────────────

export interface RAGQuery {
  query: string;
  filters?: Record<string, any>;
  top_k?: number;
  score_threshold?: number;
  include_raw_chunks?: boolean;
}

export interface Source {
  id: string;
  filename: string;
  doc_type: string;
  content: string;
  score: number;
  rank: number;
  metadata: Record<string, any>;
}

export interface RAGResponse {
  query: string;
  response: string;
  sources: Source[];
  intent: string;
  confidence: number;
  metadata: Record<string, any>;
  follow_up_suggestions: string[];
}

// ── Ingestion Types ─────────────────────────────────────────────────────────

export interface IngestResult {
  document_id: string;
  chunks_created: number;
  works_found: string[];
  splits_found: Record<string, any>[];
  royalties_found: Record<string, any>[];
  warnings: string[];
}

// ── Chat Message Types ──────────────────────────────────────────────────────

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  sources?: Source[];
  metadata?: Record<string, any>;
}

// ── Utility Types ───────────────────────────────────────────────────────────

export type Platform = 'spotify' | 'apple_music' | 'youtube' | 'tiktok' | 'amazon_music' | 'deezer' | 'pandora' | 'other';

export type RoyaltyType = 'mechanical' | 'performance' | 'sync' | 'neighboring_rights' | 'print' | 'other';

export type DocStatus = 'active' | 'pending' | 'resolved' | 'ignored';

export const PLATFORM_LABELS: Record<string, string> = {
  spotify: 'Spotify',
  apple_music: 'Apple Music',
  youtube: 'YouTube',
  tiktok: 'TikTok',
  amazon_music: 'Amazon Music',
  deezer: 'Deezer',
  pandora: 'Pandora',
  ascap: 'ASCAP',
  bmi: 'BMI',
  sesac: 'SESAC',
  gema: 'GEMA',
  prs: 'PRS',
  socan: 'SOCAN',
};

export const ROYALTY_TYPE_LABELS: Record<string, string> = {
  mechanical: 'Mechanical',
  performance: 'Performance',
  sync: 'Synchronization',
  neighboring_rights: 'Neighboring Rights',
  print: 'Print',
  other: 'Other',
};

export function formatCurrency(amount: number, currency = 'USD'): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

export function formatPercentage(value: number, decimals = 1): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatCompactNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}
