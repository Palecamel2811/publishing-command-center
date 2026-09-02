'use client';

import { useState, useEffect } from 'react';
import { Sidebar } from '@/components/sidebar';
import { Dashboard } from '@/components/dashboard';
import { ChatInterface } from '@/components/chat-interface';
import { RightsVisualizer } from '@/components/rights-visualizer';
import { Reports } from '@/components/reports';
import { UploadZone } from '@/components/upload-zone';
import { useDashboardData } from '@/lib/hooks/use-dashboard';

type Page = 'dashboard' | 'chat' | 'assets' | 'rights' | 'reports';

export const dynamic = 'force-dynamic';

export default function Home() {
  const [activePage, setActivePage] = useState<Page>('dashboard');
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedPeriod, setSelectedPeriod] = useState<string>('all');
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');

  const { data: dashboardData, isLoading, error, refetch } = useDashboardData(selectedPeriod, startDate, endDate);

  const handleNavigate = (id: string) => {
    setActivePage(id as Page);
  };

  const navItems: { id: Page; label: string; icon: string; shortcut: string }[] = [
    { id: 'dashboard', label: 'Dashboard', icon: 'M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6', shortcut: '1' },
    { id: 'chat', label: 'AI Query', icon: 'M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z', shortcut: '2' },
    { id: 'assets', label: 'Assets', icon: 'M9 19V6l12-3v13M9 6l12-3', shortcut: '3' },
    { id: 'rights', label: 'Rights Map', icon: 'M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1', shortcut: '4' },
    { id: 'reports', label: 'Reports', icon: 'M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', shortcut: '5' },
  ];

  const handleKeyDown = (e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;
    
    const key = e.key;
    const pageMap: Record<string, Page> = { '1': 'dashboard', '2': 'chat', '3': 'assets', '4': 'rights', '5': 'reports' };
    if (pageMap[key]) {
      e.preventDefault();
      setActivePage(pageMap[key]);
    }
    if (key === 'b' && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      setSidebarOpen(prev => !prev);
    }
  };

  return (
    <div className="flex h-[100dvh] max-w-full overflow-x-hidden bg-[#0a0e1a]">
      {/* Keyboard shortcuts handler */}
      <KeyboardHandler onKey={handleKeyDown} />

      {/* Sidebar */}
      <Sidebar
        items={navItems}
        activePage={activePage}
        onNavigate={handleNavigate}
        isOpen={sidebarOpen}
      />

      {/* Main Content */}
      <main className="flex-1 flex flex-col max-w-full overflow-x-hidden overflow-y-auto">
        {/* Top Bar */}
        <header className="flex items-center justify-between h-14 px-4 border-b border-white/10 bg-black/20 backdrop-blur-xl flex-shrink-0">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="btn-icon"
              aria-label="Toggle sidebar"
            >
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
              <span className="text-sm font-medium text-white/70">
                {navItems.find(n => n.id === activePage)?.label}
              </span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-white/30 font-mono">v1.0.0</span>
            <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 flex items-center justify-center text-xs font-bold">
              PCC
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div className="flex-1 overflow-y-auto overflow-x-hidden p-3 md:p-4 pb-20 md:pb-4">
          {activePage === 'dashboard' && (
            <Dashboard 
              data={dashboardData} 
              isLoading={isLoading} 
              error={error} 
              onRefresh={refetch}
              onNavigate={handleNavigate}
              selectedPeriod={selectedPeriod}
              onPeriodChange={setSelectedPeriod}
              startDate={startDate}
              endDate={endDate}
              onStartDateChange={setStartDate}
              onEndDateChange={setEndDate}
            />
          )}
          {activePage === 'chat' && (
            <ChatInterface />
          )}
          {activePage === 'assets' && (
            <div className="max-w-4xl mx-auto">
              <div className="mb-6">
                <h1 className="text-xl font-semibold text-white">Assets & Documents</h1>
                <p className="text-sm text-white/50 mt-1">Upload royalty statements, split sheets, and contracts to power your RAG system.</p>
              </div>
              <UploadZone onUploadComplete={() => refetch()} />
            </div>
          )}
          {activePage === 'rights' && (
            <RightsVisualizer data={dashboardData} isLoading={isLoading} error={error} />
          )}
          {activePage === 'reports' && (
            <Reports data={dashboardData} isLoading={isLoading} error={error} />
          )}
        </div>
      </main>
    </div>
  );
}

function KeyboardHandler({ onKey }: { onKey: (e: KeyboardEvent) => void }) {
  useEffect(() => {
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onKey]);
  return null;
}
