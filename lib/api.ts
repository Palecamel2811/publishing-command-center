/**
 * API client for the Publishing & Rights Command Center backend.
 */

import { API_BASE } from './config';


async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  const url = `${API_BASE}${cleanEndpoint}`;
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// ── Dashboard ───────────────────────────────────────────────────────────────

export async function getDashboard() {
  return request<DashboardData>('/api/dashboard');
}

// ── Works ───────────────────────────────────────────────────────────────────

export async function getWorks(status?: string) {
  const params = status ? `?status=${status}` : '';
  return request<WorksList>(`/api/works${params}`);
}

export async function createWork(work: Omit<Work, 'id' | 'created_at' | 'updated_at'>) {
  return request<{ work: Work; created: boolean }>('/api/works', {
    method: 'POST',
    body: JSON.stringify(work),
  });
}

// ── Sync Licenses ───────────────────────────────────────────────────────────

export async function getSyncLicenses(status?: string) {
  const params = status ? `?status=${status}` : '';
  return request<SyncLicenseList>(`/api/sync-licenses${params}`);
}

// ── Ingestion ───────────────────────────────────────────────────────────────

export async function uploadFile(
  file: File,
  docType?: string,
  workId?: string
) {
  const formData = new FormData();
  formData.append('file', file);
  if (docType) formData.append('doc_type', docType);
  if (workId) formData.append('work_id', workId);

  const response = await fetch(`${API_BASE}/api/ingest/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Upload failed');
  }

  return response.json();
}

export async function uploadFiles(files: File[], docType?: string) {
  const formData = new FormData();
  // Append each file to the FormData
  for (const file of files) {
    formData.append('files', file);
  }
  if (docType) formData.append('doc_type', docType);

  const response = await fetch(`${API_BASE}/api/ingest/batch`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || 'Batch upload failed');
  }
  return response.json();
}

export async function getIngestionHistory(limit: number = 20) {
  return request<{ history: Array<{ id: string; filename: string; doc_type: string; work_title: string; created_at: string }>; count: number }>(`/api/ingest/history?limit=${limit}`);
}

export async function deleteDocument(filename: string) {
  return request<{ status: string; filename: string; vector_chunks_deleted: number; relational_records_deleted: number }>(`/api/documents/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
}

export async function bulkDeleteDocuments(filenames: string[]) {
  return request<{ status: string; deleted_count: number; total_chunks_deleted: number; total_records_deleted: number }>('/api/documents-bulk/delete', {
    method: 'POST',
    body: JSON.stringify({ filenames }),
  });
}



// ── RAG Query ───────────────────────────────────────────────────────────────

export async function queryRAG(query: string, options?: {
  filters?: Record<string, any>;
  top_k?: number;
  score_threshold?: number;
}) {
  return request<RAGResponse>('/api/query', {
    method: 'POST',
    body: JSON.stringify({
      query,
      filters: options?.filters,
      top_k: options?.top_k,
      score_threshold: options?.score_threshold,
    }),
  });
}

export async function queryRAGStream(
  query: string,
  callbacks: {
    onSources?: (sources: any[]) => void;
    onToken?: (token: string) => void;
    onDone?: (confidence: number) => void;
    onError?: (err: any) => void;
  },
  options?: {
    filters?: Record<string, any>;
    top_k?: number;
    score_threshold?: number;
  }
) {
  try {
    const cleanEndpoint = '/api/query/stream';
    const url = `${API_BASE}${cleanEndpoint}`;
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        query,
        filters: options?.filters,
        top_k: options?.top_k,
        score_threshold: options?.score_threshold,
      }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`HTTP Error ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });

      const events = buffer.split('\n\n');
      buffer = events.pop() || '';

      for (const rawEvent of events) {
        if (!rawEvent.trim()) continue;
        const lines = rawEvent.split('\n');
        let eventName = '';
        let dataStr = '';

        for (const line of lines) {
          if (line.startsWith('event: ')) {
            eventName = line.slice(7).trim();
          } else if (line.startsWith('data: ')) {
            dataStr = line.slice(6).trim();
          }
        }

        if (eventName === 'sources' && dataStr) {
          try { callbacks.onSources?.(JSON.parse(dataStr)); } catch {}
        } else if (eventName === 'token' && dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            if (parsed.token) callbacks.onToken?.(parsed.token);
          } catch {}
        } else if (eventName === 'done' && dataStr) {
          try {
            const parsed = JSON.parse(dataStr);
            callbacks.onDone?.(parsed.confidence || 0);
          } catch {}
        }
      }
    }
  } catch (err) {
    callbacks.onError?.(err);
  }
}

// ── Reconciliation ──────────────────────────────────────────────────────────

export async function runReconciliation(data: {
  data_sources: Record<string, any>[];
  splits?: Record<string, any>[];
  period_start?: string;
  period_end?: string;
}) {
  return request<ReconciliationResult>('/api/reconcile/run', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

// ── Store Management ────────────────────────────────────────────────────────

export async function getStoreStats() {
  return request<Record<string, any>>('/api/store/stats');
}

export async function clearStore() {
  return request<{ message: string; success: boolean }>('/api/store/clear', {
    method: 'POST',
  });
}

// ── Types ───────────────────────────────────────────────────────────────────

interface DashboardData {
  summary: any;
  recent_royalties: any[];
  works: any[];
  sync_licenses: any[];
  reconciliation_status: any;
  pending_splits: any[];
  alerts: any[];
  revenue_trend: { month: string; amount: number }[];
}

interface WorksList {
  works: any[];
  count: number;
}

interface SyncLicenseList {
  sync_licenses: any[];
  count: number;
}

interface RAGResponse {
  query: string;
  response: string;
  sources: any[];
  intent: string;
  confidence: number;
  metadata: any;
  follow_up_suggestions: string[];
}

interface ReconciliationResult {
  period_start: string;
  period_end: string;
  total_platforms_compared: number;
  total_discrepancies: number;
  total_discrepancy_amount: number;
  discrepancies: any[];
  summary: any;
}

interface Work {
  id: string;
  title: string;
  isrc?: string;
  iswc?: string;
  splits_count: number;
  total_earnings: number;
  platforms: string[];
  status: string;
  created_at?: string;
  updated_at?: string;
}

interface SyncLicense {
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
