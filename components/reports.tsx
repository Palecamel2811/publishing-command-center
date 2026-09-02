'use client';

import { useMemo } from 'react';
import { formatCurrency } from '@/types';

interface ReportsProps {
  data?: any;
  isLoading: boolean;
  error?: Error | null;
}

export function Reports({ data, isLoading, error }: ReportsProps) {
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-1">Failed to load data</h3>
          <p className="text-sm text-white/50">{error.message}</p>
        </div>
      </div>
    );
  }

  const reconciliation = useMemo(() => data?.reconciliation_status || {}, [data?.reconciliation_status]);
  const recentRoyalties = useMemo(() => data?.recent_royalties || [], [data?.recent_royalties]);
  const pendingSplits = useMemo(() => data?.pending_splits || [], [data?.pending_splits]);
  const alerts = useMemo(() => data?.alerts || [], [data?.alerts]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-sm text-white/50">Loading Reports...</span>
        </div>
      </div>
    );
  }

  const handleExportCSV = (type: string = 'royalties') => {
    const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    window.open(`${apiUrl}/api/reports/export?report_type=${type}`, '_blank');
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Audit & Reconciliation Reports</h1>
          <p className="text-sm text-white/50">Discrepancy analysis, royalty reconciliation, and audit logs.</p>
        </div>
        <div className="flex items-center gap-2">
          <button 
            onClick={() => handleExportCSV('royalties')} 
            className="btn-secondary flex items-center gap-2 text-xs hover:bg-white/10 transition-colors"
            title="Export full royalty statement ledger"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export Royalties
          </button>
          <button 
            onClick={() => handleExportCSV('works')} 
            className="btn-secondary flex items-center gap-2 text-xs hover:bg-white/10 transition-colors"
            title="Export work catalog"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            Export Catalog
          </button>
        </div>
      </div>

      {/* Reconciliation Summary */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <div className="text-sm text-white/50 mb-1">Total Discrepancies</div>
          <div className="text-2xl font-bold text-white">{reconciliation.total_discrepancies || 0}</div>
        </div>
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <div className="text-sm text-white/50 mb-1">Critical</div>
          <div className={`text-2xl font-bold ${reconciliation.critical ? 'text-red-400' : 'text-white'}`}>
            {reconciliation.critical || 0}
          </div>
        </div>
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <div className="text-sm text-white/50 mb-1">High</div>
          <div className={`text-2xl font-bold ${reconciliation.high ? 'text-yellow-400' : 'text-white'}`}>
            {reconciliation.high || 0}
          </div>
        </div>
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <div className="text-sm text-white/50 mb-1">Last Run</div>
          <div className="text-sm font-mono text-white/70">{reconciliation.last_run || 'N/A'}</div>
        </div>
      </div>

      {/* Alerts */}
      {alerts.length > 0 && (
        <div className="space-y-2">
          {alerts.map((alert: any, idx: number) => (
            <div key={idx} className={`p-3 border rounded flex items-center gap-3 ${
              alert.type === 'warning' ? 'bg-yellow-500/5 border-yellow-500/20' : 'bg-cyan-500/5 border-cyan-500/20'
            }`}>
              <div className={`w-2 h-2 rounded-full ${
                alert.type === 'warning' ? 'bg-yellow-400' : 'bg-cyan-400'
              }`} />
              <div className="flex-1 text-sm text-white/80">{alert.message}</div>
              <div className="text-xs text-white/40 font-mono">{alert.date}</div>
            </div>
          ))}
        </div>
      )}

      {/* Recent Royalties */}
      <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
        <h3 className="text-sm font-medium text-white/70 mb-4">Recent Royalty Entries</h3>
        {recentRoyalties.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-white/50 uppercase border-b border-white/10">
                <tr>
                  <th className="px-4 py-2">Work</th>
                  <th className="px-4 py-2">Platform</th>
                  <th className="px-4 py-2">Type</th>
                  <th className="px-4 py-2">Period</th>
                  <th className="px-4 py-2 text-right">Amount</th>
                </tr>
              </thead>
              <tbody className="text-white/70">
                {recentRoyalties.map((entry: any) => (
                  <tr key={entry.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-2">{entry.work}</td>
                    <td className="px-4 py-2 capitalize">{entry.platform}</td>
                    <td className="px-4 py-2 capitalize">{entry.type}</td>
                    <td className="px-4 py-2">{entry.period}</td>
                    <td className="px-4 py-2 text-right font-mono">{formatCurrency(entry.amount)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="text-center py-8 text-white/30 text-sm">No royalty entries found</div>
        )}
      </div>

      {/* Pending Splits */}
      {pendingSplits.length > 0 && (
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <h3 className="text-sm font-medium text-white/70 mb-4">Pending Splits</h3>
          <div className="space-y-2">
            {pendingSplits.map((split: any, idx: number) => (
              <div key={idx} className="flex items-center justify-between p-3 bg-white/5 border border-white/10 rounded">
                <div>
                  <div className="text-sm font-medium text-white">{split.work || 'Unknown Work'}</div>
                  <div className="text-xs text-white/50">{split.missing}</div>
                </div>
                <span className={`px-2 py-1 text-xs font-medium capitalize ${
                  split.priority === 'high' ? 'bg-red-500/20 text-red-400' : 'bg-yellow-500/20 text-yellow-400'
                }`}>
                  {split.priority}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
