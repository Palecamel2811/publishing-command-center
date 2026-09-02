'use client';

import { useMemo, useState } from 'react';
import {
  AreaChart,
  Area,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import { formatCurrency, formatCompactNumber } from '@/types';
import { runReconciliation } from '@/lib/api';
import { CalendarRangePicker } from '@/components/calendar-range-picker';

interface DashboardProps {
  data?: any;
  isLoading: boolean;
  error: Error | null;
  onRefresh?: () => void;
  onNavigate?: (page: string) => void;
  selectedPeriod?: string;
  onPeriodChange?: (period: string) => void;
  startDate?: string;
  endDate?: string;
  onStartDateChange?: (date: string) => void;
  onEndDateChange?: (date: string) => void;
}

// Chart color palette - optimized for dark mode
const CHART_COLORS = ['#06b6d4', '#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#ec4899', '#14b8a6'];

export function Dashboard({
  data,
  isLoading,
  error,
  onRefresh,
  onNavigate,
  selectedPeriod = 'all',
  onPeriodChange,
  startDate = '',
  endDate = '',
  onStartDateChange,
  onEndDateChange,
}: DashboardProps) {
  const [isReconciling, setIsReconciling] = useState(false);
  const [timeframe, setTimeframe] = useState<'7D' | '1M' | '3M' | '1Y'>('1Y');
  const [showDatePicker, setShowDatePicker] = useState(false);

  const trendData = useMemo(() => {
    if (!data?.revenue_trend) return [];
    let sliceCount = data.revenue_trend.length;
    if (timeframe === '7D') sliceCount = Math.min(1, data.revenue_trend.length);
    else if (timeframe === '1M') sliceCount = Math.min(2, data.revenue_trend.length);
    else if (timeframe === '3M') sliceCount = Math.min(3, data.revenue_trend.length);
    
    return data.revenue_trend.slice(-sliceCount).map((d: any) => ({
      ...d,
      amount: Number(d.amount),
    }));
  }, [data?.revenue_trend, timeframe]);

  const platformData = useMemo(() => {
    if (!data?.summary?.by_platform) return [];
    return Object.entries(data.summary.by_platform as Record<string, number>).map(([platform, amount]) => ({
      name: platform.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      value: Number(amount),
    })).sort((a, b) => b.value - a.value);
  }, [data?.summary?.by_platform]);

  const typeData = useMemo(() => {
    if (!data?.summary?.by_type) return [];
    return Object.entries(data.summary.by_type as Record<string, number>).map(([type, amount]) => ({
      name: type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
      value: Number(amount),
    })).sort((a, b) => b.value - a.value);
  }, [data?.summary?.by_type]);

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <div className="w-12 h-12 mx-auto mb-4 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center">
            <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
          </div>
          <h3 className="text-lg font-medium text-white mb-1">Failed to load dashboard</h3>
          <p className="text-sm text-white/50">{error.message}</p>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return <DashboardSkeleton />;
  }

  const availablePeriods: string[] = data?.available_periods || [];

  return (
    <div className="space-y-4 max-w-[1600px] mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-white">Publishing Overview</h1>
          <p className="text-sm text-white/50">
            {data?.summary?.period_start && data?.summary?.period_end
              ? `${data.summary.period_start} to ${data.summary.period_end}`
              : 'Real-time data'}
          </p>
        </div>
        <div className="flex items-center gap-3">
          {/* Quarter / Preset Dropdown */}
          <div className="flex items-center gap-2 bg-black/40 border border-white/10 rounded-lg px-3 py-1.5">
            <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
            <span className="text-xs text-white/50">Preset:</span>
            <select
              value={selectedPeriod}
              onChange={(e) => {
                onPeriodChange?.(e.target.value);
                if (e.target.value !== 'custom') {
                  onStartDateChange?.('');
                  onEndDateChange?.('');
                }
              }}
              className="bg-transparent text-xs text-white font-medium focus:outline-none cursor-pointer"
            >
              <option value="all" className="bg-gray-900 text-white">All Time</option>
              {availablePeriods.map((p) => (
                <option key={p} value={p} className="bg-gray-900 text-white">
                  {p}
                </option>
              ))}
              <option value="custom" className="bg-gray-900 text-white">Custom Date Range...</option>
            </select>
          </div>

          {/* Calendar Date Range Picker */}
          <div className="relative">
            <button
              onClick={() => setShowDatePicker(!showDatePicker)}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                startDate || endDate || selectedPeriod === 'custom'
                  ? 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40'
                  : 'bg-black/40 text-white/70 border-white/10 hover:text-white'
              }`}
            >
              <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
              <span>
                {startDate && endDate
                  ? `${startDate} → ${endDate}`
                  : startDate
                  ? `From ${startDate}`
                  : endDate
                  ? `Until ${endDate}`
                  : 'Select Date Range'}
              </span>
            </button>

            {showDatePicker && (
              <CalendarRangePicker
                startDate={startDate}
                endDate={endDate}
                onSelectRange={(start, end) => {
                  onStartDateChange?.(start);
                  onEndDateChange?.(end);
                  if (start || end) {
                    onPeriodChange?.('custom');
                  } else {
                    onPeriodChange?.('all');
                  }
                }}
                onClose={() => setShowDatePicker(false)}
              />
            )}
          </div>

          <button 
            onClick={() => onRefresh ? onRefresh() : window.location.reload()}
            disabled={isLoading}
            className="btn-primary flex items-center gap-2 text-sm hover:scale-[1.02] active:scale-[0.98] transition-all"
          >
            <svg className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {isLoading ? 'Syncing...' : 'Refresh'}
          </button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        <SummaryCard
          label="Total Gross"
          value={data?.summary?.total_gross}
          color="cyan"
          trend={"+12.4%"}
          trendUp
        />
        <SummaryCard
          label="Total Net"
          value={data?.summary?.total_net}
          color="emerald"
          trend={"+8.2%"}
          trendUp
        />
        <div className="panel-card">
          <div className="panel-body">
            <p className="text-xs text-white/50 mb-1">Royalty Entries</p>
            <p className="text-2xl font-semibold text-white">{formatCompactNumber(data?.summary?.count || 0)}</p>
          </div>
        </div>
        <div className="panel-card">
          <div className="panel-body">
            <p className="text-xs text-white/50 mb-1">Active Works</p>
            <p className="text-2xl font-semibold text-white">{data?.works?.length || 0}</p>
          </div>
        </div>
      </div>

      {/* Revenue Trend Chart */}
      <div className="panel-card">
        <div className="panel-header">
          <span className="panel-title">Revenue Trend</span>
          <div className="flex items-center gap-2">
            {(['7D', '1M', '3M', '1Y'] as const).map((period) => (
              <button
                key={period}
                onClick={() => setTimeframe(period)}
                className={`text-xs px-2 py-1 rounded transition-colors ${
                  timeframe === period ? 'bg-cyan-500/20 text-cyan-400 font-semibold' : 'text-white/40 hover:text-white/60'
                }`}
              >
                {period}
              </button>
            ))}
          </div>
        </div>
        <div className="panel-body pt-2">
          <div className="h-[250px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData}>
                <defs>
                  <linearGradient id="colorRevenue" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                <XAxis
                  dataKey="month"
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                />
                <YAxis
                  stroke="rgba(255,255,255,0.3)"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`}
                  width={50}
                />
                <Tooltip
                  cursor={{ stroke: 'rgba(6, 182, 212, 0.4)', strokeWidth: 1, strokeDasharray: '3 3' }}
                  content={({ active, payload, label }) => {
                    if (!active || !payload?.[0]) return null;
                    const value = Number(payload[0].value);
                    return (
                      <div className="bg-[#0d1322] border border-cyan-500/40 p-3 rounded-xl shadow-2xl backdrop-blur-xl space-y-1">
                        <div className="text-white font-semibold text-xs border-b border-white/10 pb-1">{label}</div>
                        <div className="text-cyan-400 font-bold font-mono text-sm">{formatCurrency(value)}</div>
                      </div>
                    );
                  }}
                />
                <Area
                  type="monotone"
                  dataKey="amount"
                  stroke="#06b6d4"
                  strokeWidth={2}
                  fill="url(#colorRevenue)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Platform Breakdown */}
        <div className="panel-card">
          <div className="panel-header">
            <span className="panel-title">By Platform</span>
            <span className="panel-subtitle">Revenue share</span>
          </div>
          <div className="panel-body">
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={platformData}
                    cx="50%"
                    cy="50%"
                    innerRadius={50}
                    outerRadius={75}
                    paddingAngle={2}
                    dataKey="value"
                  >
                    {platformData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
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
            </div>
            <div className="space-y-1.5 mt-2">
              {platformData.slice(0, 5).map((d: any, i: number) => (
                <div key={d.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: CHART_COLORS[i % CHART_COLORS.length] }} />
                    <span className="text-xs text-white/60">{d.name}</span>
                  </div>
                  <span className="text-xs font-mono text-white/80">{formatCurrency(d.value)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Royalty Type Breakdown */}
        <div className="panel-card">
          <div className="panel-header">
            <span className="panel-title">By Type</span>
            <span className="panel-subtitle">Revenue by source</span>
          </div>
          <div className="panel-body">
            <div className="h-[200px]">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={typeData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis
                    type="number"
                    stroke="rgba(255,255,255,0.3)"
                    tick={{ fontSize: 10 }}
                    tickLine={false}
                    tickFormatter={(v: number) => `$${(v / 1000).toFixed(0)}K`}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    stroke="rgba(255,255,255,0.5)"
                    tick={{ fontSize: 11 }}
                    width={100}
                    tickLine={false}
                  />
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
                  <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                    {typeData.map((_entry, index) => (
                      <Cell key={`cell-${index}`} fill={CHART_COLORS[index % CHART_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        </div>

        {/* Top Works */}
        <div className="panel-card">
          <div className="panel-header">
            <span className="panel-title">Top Works</span>
            <span className="panel-subtitle">By earnings</span>
          </div>
          <div className="panel-body">
            <div className="space-y-3">
              {(data?.works || []).slice(0, 5).map((work: any, i: number) => (
                <div key={work.id} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center text-xs font-bold ${
                      i === 0 ? 'bg-amber-500/20 text-amber-400' :
                      i === 1 ? 'bg-gray-400/20 text-gray-400' :
                      i === 2 ? 'bg-amber-700/20 text-amber-600' :
                      'bg-white/5 text-white/40'
                    }`}>
                      {i + 1}
                    </div>
                    <div>
                      <p className="text-sm font-medium text-white">{work.title}</p>
                      <p className="text-xs text-white/40">{work.platforms.length} platforms</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-white">{formatCurrency(work.total_earnings)}</p>
                    <p className="text-xs text-white/30">{work.splits_count} splits</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {/* Recent Royalties */}
        <div className="panel-card lg:col-span-2">
          <div className="panel-header">
            <span className="panel-title">Recent Royalties</span>
            <button 
              onClick={() => onNavigate?.('reports')}
              className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors"
            >
              View all
            </button>
          </div>
          <div className="panel-body p-0">
            <div className="overflow-x-auto">
              <table className="w-full data-dense">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="text-left text-xs font-medium text-white/40 uppercase tracking-wider px-4 py-3">Work</th>
                    <th className="text-left text-xs font-medium text-white/40 uppercase tracking-wider px-4 py-3">Platform</th>
                    <th className="text-left text-xs font-medium text-white/40 uppercase tracking-wider px-4 py-3">Type</th>
                    <th className="text-left text-xs font-medium text-white/40 uppercase tracking-wider px-4 py-3">Period</th>
                    <th className="text-right text-xs font-medium text-white/40 uppercase tracking-wider px-4 py-3">Amount</th>
                  </tr>
                </thead>
                <tbody>
                  {(data?.recent_royalties || []).slice(0, 8).map((royalty: any) => (
                    <tr key={royalty.id} className="border-b border-white/[0.03] hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-3 text-sm text-white">
                        {royalty.work}
                      </td>
                      <td className="px-4 py-3">
                        <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400">
                          {royalty.platform}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-white/60">{royalty.type}</td>
                      <td className="px-4 py-3 text-xs text-white/50 font-mono">{royalty.period}</td>
                      <td className="px-4 py-3 text-right text-sm font-mono text-white font-medium">
                        {formatCurrency(royalty.amount)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Alerts & Actions */}
        <div className="space-y-3">
          {/* Reconciliation Status */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">Reconciliation</span>
              <span className={`badge ${
                data?.reconciliation_status?.total_discrepancies === 0 ? 'badge-active' : 'badge-pending'
              }`}>
                {data?.reconciliation_status?.total_discrepancies || 0} issues
              </span>
            </div>
            <div className="panel-body">
              <div className="space-y-2">
                {[
                  { label: 'Critical', count: data?.reconciliation_status?.critical },
                  { label: 'High', count: data?.reconciliation_status?.high },
                  { label: 'Medium', count: data?.reconciliation_status?.medium },
                  { label: 'Low', count: data?.reconciliation_status?.low },
                ].map((item) => (
                  <div key={item.label} className="flex items-center justify-between text-xs">
                    <span className="text-white/50">{item.label}</span>
                    <span className={`font-mono ${
                      item.count > 0
                        ? item.label === 'Critical' ? 'text-red-400' :
                          item.label === 'High' ? 'text-amber-400' :
                          'text-amber-300/70'
                        : 'text-white/30'
                    }`}>
                      {item.count}
                    </span>
                  </div>
                ))}
              </div>
              <button 
                onClick={async () => {
                  try {
                    setIsReconciling(true);
                    await runReconciliation({ data_sources: [] });
                    onRefresh?.();
                  } catch (e: any) {
                    alert(`Reconciliation error: ${e.message}`);
                  } finally {
                    setIsReconciling(false);
                  }
                }}
                disabled={isReconciling}
                className="btn-secondary w-full mt-3 text-xs flex items-center justify-center gap-2 hover:bg-white/10 transition-all"
              >
                {isReconciling ? (
                  <>
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Reconciling...
                  </>
                ) : (
                  'Run Reconciliation'
                )}
              </button>
            </div>
          </div>

          {/* Pending Actions */}
          <div className="panel-card">
            <div className="panel-header">
              <span className="panel-title">Pending Actions</span>
            </div>
            <div className="panel-body space-y-2">
              {(data?.pending_splits || []).map((split: any) => (
                <div key={split.work} className="flex items-start gap-2 p-2 rounded-lg bg-white/[0.02]">
                  <div className="w-1.5 h-1.5 rounded-full bg-amber-400 mt-1.5 flex-shrink-0" />
                  <div className="min-w-0">
                    <p className="text-xs text-white/70 truncate">{split.work}</p>
                    <p className="text-[11px] text-white/40">{split.missing}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function SummaryCard({ label, value, color, trend, trendUp }: {
  label: string;
  value?: number;
  color: 'cyan' | 'emerald' | 'amber' | 'purple';
  trend?: string;
  trendUp?: boolean;
}) {
  const colorMap = {
    cyan: { bg: 'bg-cyan-500/10', border: 'border-cyan-500/20', text: 'text-cyan-400', dot: 'bg-cyan-400' },
    emerald: { bg: 'bg-emerald-500/10', border: 'border-emerald-500/20', text: 'text-emerald-400', dot: 'bg-emerald-400' },
    amber: { bg: 'bg-amber-500/10', border: 'border-amber-500/20', text: 'text-amber-400', dot: 'bg-amber-400' },
    purple: { bg: 'bg-purple-500/10', border: 'border-purple-500/20', text: 'text-purple-400', dot: 'bg-purple-400' },
  };
  const c = colorMap[color];

  return (
    <div className={`panel-card ${c.bg} ${c.border} border`}>
      <div className="panel-body">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs text-white/50">{label}</span>
          <div className={`w-2 h-2 rounded-full ${c.dot} animate-pulse-glow`} />
        </div>
        <p className="text-2xl font-semibold text-white">{value ? formatCurrency(value) : '--'}</p>
        {trend && (
          <div className="flex items-center gap-1 mt-1">
            <svg className={`w-3 h-3 ${trendUp ? 'text-emerald-400' : 'text-red-400'}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d={trendUp ? "M7 11l5-5m0 0l5 5m-5-5v12" : "M17 13l-5 5m0 0l-5-5m5 5v-12"} />
            </svg>
            <span className={`text-xs font-medium ${trendUp ? 'text-emerald-400' : 'text-red-400'}`}>{trend}</span>
          </div>
        )}
      </div>
    </div>
  );
}

function DashboardSkeleton() {
  return (
    <div className="space-y-4 max-w-[1600px] mx-auto">
      <div className="flex items-center justify-between">
        <div className="space-y-2">
          <div className="h-6 w-40 bg-white/10 rounded shimmer" />
          <div className="h-4 w-60 bg-white/5 rounded shimmer" />
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-3">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="panel-card p-4">
            <div className="h-3 w-20 bg-white/10 rounded mb-3 shimmer" />
            <div className="h-7 w-28 bg-white/10 rounded shimmer" />
          </div>
        ))}
      </div>
      <div className="panel-card p-4 h-[350px]">
        <div className="h-5 w-32 bg-white/10 rounded mb-4 shimmer" />
        <div className="h-[280px] w-full bg-white/5 rounded shimmer" />
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-3">
        {[1, 2, 3].map((i) => (
          <div key={i} className="panel-card p-4 h-[280px]">
            <div className="h-5 w-24 bg-white/10 rounded mb-4 shimmer" />
            <div className="h-[200px] w-full bg-white/5 rounded shimmer" />
          </div>
        ))}
      </div>
    </div>
  );
}
