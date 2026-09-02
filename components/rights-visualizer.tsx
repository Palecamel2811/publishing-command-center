'use client';

import { useMemo } from 'react';
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { formatCurrency } from '@/types';

interface RightsVisualizerProps {
  data?: any;
  isLoading: boolean;
  error?: Error | null;
}

const COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'];

export function RightsVisualizer({ data, isLoading, error }: RightsVisualizerProps) {
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

  const workChartData = useMemo(() => {
    if (!data?.works) return [];
    return data.works.slice(0, 6).map((w: any) => ({
      name: w.title,
      value: Number(w.total_earnings || 0),
    }));
  }, [data?.works]);

  const platformChartData = useMemo(() => {
    if (!data?.summary?.by_platform) return [];
    return Object.entries(data.summary.by_platform as Record<string, number>)
      .map(([platform, amount]) => ({
        name: platform.replace(/_/g, ' '),
        value: Number(amount),
      }))
      .sort((a, b) => b.value - a.value);
  }, [data?.summary?.by_platform]);

  const syncLicenses = useMemo(() => data?.sync_licenses || [], [data?.sync_licenses]);
  const pendingSplits = useMemo(() => data?.pending_splits || [], [data?.pending_splits]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
          <span className="text-sm text-white/50">Loading Rights Map...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Rights Map</h1>
          <p className="text-sm text-white/50">Work ownership, revenue distribution, and licensing status.</p>
        </div>
        <div className="flex items-center gap-2">
          <span className="px-2 py-1 text-xs font-mono bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 rounded">
            {data?.works?.length || 0} Works
          </span>
          <span className="px-2 py-1 text-xs font-mono bg-purple-500/10 text-purple-400 border border-purple-500/20 rounded">
            {syncLicenses.length} Licenses
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Revenue by Work */}
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <h3 className="text-sm font-medium text-white/70 mb-4">Revenue by Work</h3>
          <div className="h-64">
            {workChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={workChartData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {workChartData.map((_: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    content={({ active, payload }) => {
                      if (!active || !payload?.[0]) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="bg-[#0d1322] border border-cyan-500/40 p-3 rounded-xl shadow-2xl backdrop-blur-xl space-y-1">
                          <div className="text-white font-semibold text-xs border-b border-white/10 pb-1">{d.name}</div>
                          <div className="text-cyan-400 font-bold font-mono text-sm">{formatCurrency(d.value)}</div>
                        </div>
                      );
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-white/30 text-sm">No work data available</div>
            )}
          </div>
        </div>

        {/* Revenue by Platform */}
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <h3 className="text-sm font-medium text-white/70 mb-4">Revenue by Platform</h3>
          <div className="h-64">
            {platformChartData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={platformChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
                  <XAxis dataKey="name" tick={{ fill: '#ffffff60', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <YAxis tick={{ fill: '#ffffff60', fontSize: 12 }} axisLine={false} tickLine={false} />
                  <Tooltip
                    cursor={{ fill: 'rgba(255, 255, 255, 0.03)' }}
                    content={({ active, payload }) => {
                      if (!active || !payload?.[0]) return null;
                      const d = payload[0].payload;
                      return (
                        <div className="bg-[#0d1322] border border-cyan-500/40 p-3 rounded-xl shadow-2xl backdrop-blur-xl space-y-1">
                          <div className="text-white font-semibold text-xs border-b border-white/10 pb-1">{d.name}</div>
                          <div className="text-cyan-400 font-bold font-mono text-sm">{formatCurrency(d.value)}</div>
                        </div>
                      );
                    }}
                  />
                  <Bar dataKey="value" fill="#06b6d4" radius={[4, 4, 0, 0]} barSize={40} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-white/30 text-sm">No platform data available</div>
            )}
          </div>
        </div>
      </div>

      {/* Active Rights & Splits */}
      {data?.works?.some((w: any) => w.splits && w.splits.length > 0) && (
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <h3 className="text-sm font-medium text-white/70 mb-4">Active Rights & Splits</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-white/50 uppercase border-b border-white/10">
                <tr>
                  <th className="px-4 py-2">Work</th>
                  <th className="px-4 py-2">Rightsholder</th>
                  <th className="px-4 py-2">PRO / Affiliation</th>
                  <th className="px-4 py-2">Share</th>
                  <th className="px-4 py-2">Role</th>
                </tr>
              </thead>
              <tbody className="text-white/70">
                {data.works.flatMap((work: any) => 
                  (work.splits || []).map((split: any, idx: number) => (
                    <tr key={`${work.id}-${idx}`} className="border-b border-white/5 hover:bg-white/5">
                      <td className="px-4 py-2 font-medium text-white/90">{work.title}</td>
                      <td className="px-4 py-2">{split.party}</td>
                      <td className="px-4 py-2 uppercase">{split.pro}</td>
                      <td className="px-4 py-2 font-mono text-cyan-400">{split.share}%</td>
                      <td className="px-4 py-2 capitalize">{split.type}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Sync Licenses */}
      {syncLicenses.length > 0 && (
        <div className="p-4 bg-black/20 border border-white/10 rounded-lg">
          <h3 className="text-sm font-medium text-white/70 mb-4">Active Sync Licenses</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="text-xs text-white/50 uppercase border-b border-white/10">
                <tr>
                  <th className="px-4 py-2">Work</th>
                  <th className="px-4 py-2">Licensee</th>
                  <th className="px-4 py-2">Media</th>
                  <th className="px-4 py-2">Fee</th>
                  <th className="px-4 py-2">Status</th>
                </tr>
              </thead>
              <tbody className="text-white/70">
                {syncLicenses.map((license: any) => (
                  <tr key={license.id} className="border-b border-white/5 hover:bg-white/5">
                    <td className="px-4 py-2">{license.work}</td>
                    <td className="px-4 py-2">{license.licensee}</td>
                    <td className="px-4 py-2 capitalize">{license.media_type}</td>
                    <td className="px-4 py-2 font-mono">{formatCurrency(license.fee)}</td>
                    <td className="px-4 py-2">
                      <span className={`px-2 py-0.5 rounded text-xs font-medium capitalize ${
                        license.status === 'active' ? 'bg-emerald-500/20 text-emerald-400' : 'bg-yellow-500/20 text-yellow-400'
                      }`}>
                        {license.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

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
