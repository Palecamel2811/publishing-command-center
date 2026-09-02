'use client';

import { useState, useMemo } from 'react';

interface CalendarRangePickerProps {
  startDate: string; // YYYY-MM-DD
  endDate: string;   // YYYY-MM-DD
  onSelectRange: (start: string, end: string) => void;
  onClose: () => void;
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
];

export function CalendarRangePicker({
  startDate,
  endDate,
  onSelectRange,
  onClose,
}: CalendarRangePickerProps) {
  // Currently displayed month/year in the calendar
  const initialDate = startDate ? new Date(startDate) : new Date(2024, 0, 1);
  const [currentYear, setCurrentYear] = useState<number>(initialDate.getFullYear());
  const [currentMonth, setCurrentMonth] = useState<number>(initialDate.getMonth());

  // Transient selection states before hitting "Apply"
  const [tempStart, setTempStart] = useState<string>(startDate);
  const [tempEnd, setTempEnd] = useState<string>(endDate);

  // Generate years list (e.g. 2020 to 2030)
  const years = useMemo(() => {
    const arr = [];
    for (let y = 2020; y <= 2030; y++) arr.push(y);
    return arr;
  }, []);

  // Compute days grid for the current month
  const calendarDays = useMemo(() => {
    const firstDayOfMonth = new Date(currentYear, currentMonth, 1);
    const lastDayOfMonth = new Date(currentYear, currentMonth + 1, 0);
    const startDayOfWeek = firstDayOfMonth.getDay(); // 0 = Sun, 1 = Mon, etc.
    const totalDays = lastDayOfMonth.getDate();

    const days: ({ day: number; dateStr: string; isCurrentMonth: boolean } | null)[] = [];

    // Empty padding slots for days of previous month
    for (let i = 0; i < startDayOfWeek; i++) {
      days.push(null);
    }

    // Days of current month
    for (let d = 1; d <= totalDays; d++) {
      const monthStr = String(currentMonth + 1).padStart(2, '0');
      const dayStr = String(d).padStart(2, '0');
      const dateStr = `${currentYear}-${monthStr}-${dayStr}`;
      days.push({ day: d, dateStr, isCurrentMonth: true });
    }

    return days;
  }, [currentYear, currentMonth]);

  const handleDayClick = (dateStr: string) => {
    if (!tempStart || (tempStart && tempEnd)) {
      // Start a new selection
      setTempStart(dateStr);
      setTempEnd('');
    } else {
      // Complete range selection
      if (dateStr < tempStart) {
        setTempEnd(tempStart);
        setTempStart(dateStr);
      } else {
        setTempEnd(dateStr);
      }
    }
  };

  const isSelectedStart = (dateStr: string) => dateStr === tempStart;
  const isSelectedEnd = (dateStr: string) => dateStr === tempEnd;
  const isInRange = (dateStr: string) => {
    if (!tempStart || !tempEnd) return false;
    return dateStr > tempStart && dateStr < tempEnd;
  };

  const handlePrevMonth = () => {
    if (currentMonth === 0) {
      setCurrentMonth(11);
      setCurrentYear(prev => prev - 1);
    } else {
      setCurrentMonth(prev => prev - 1);
    }
  };

  const handleNextMonth = () => {
    if (currentMonth === 11) {
      setCurrentMonth(0);
      setCurrentYear(prev => prev + 1);
    } else {
      setCurrentMonth(prev => prev + 1);
    }
  };

  const handleQuickPreset = (preset: 'Q1' | 'Q2' | 'Q3' | 'Q4' | '2024') => {
    if (preset === 'Q1') {
      setTempStart(`${currentYear}-01-01`);
      setTempEnd(`${currentYear}-03-31`);
    } else if (preset === 'Q2') {
      setTempStart(`${currentYear}-04-01`);
      setTempEnd(`${currentYear}-06-30`);
    } else if (preset === 'Q3') {
      setTempStart(`${currentYear}-07-01`);
      setTempEnd(`${currentYear}-09-30`);
    } else if (preset === 'Q4') {
      setTempStart(`${currentYear}-10-01`);
      setTempEnd(`${currentYear}-12-31`);
    } else if (preset === '2024') {
      setTempStart(`2024-01-01`);
      setTempEnd(`2024-12-31`);
    }
  };

  return (
    <div className="absolute right-0 mt-2 z-50 p-4 w-80 bg-[#0d1322] border border-white/20 rounded-2xl shadow-2xl space-y-3 backdrop-blur-2xl">
      {/* Header with Title & Close */}
      <div className="flex items-center justify-between border-b border-white/10 pb-2">
        <div className="flex items-center gap-2">
          <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
          </svg>
          <span className="text-xs font-semibold text-white">Date Range Calendar</span>
        </div>
        <button
          onClick={onClose}
          className="text-white/40 hover:text-white text-xs p-1 rounded hover:bg-white/10 transition-colors"
        >
          ✕
        </button>
      </div>

      {/* Month & Year Selection Controls */}
      <div className="flex items-center justify-between gap-1">
        <button
          onClick={handlePrevMonth}
          className="p-1 text-white/60 hover:text-white hover:bg-white/10 rounded transition-colors"
          title="Previous Month"
        >
          ‹
        </button>

        <div className="flex items-center gap-1.5">
          {/* Month Dropdown */}
          <select
            value={currentMonth}
            onChange={(e) => setCurrentMonth(Number(e.target.value))}
            className="bg-black/40 border border-white/15 rounded text-xs text-white px-2 py-1 focus:outline-none cursor-pointer"
          >
            {MONTHS.map((m, idx) => (
              <option key={m} value={idx} className="bg-gray-900 text-white">
                {m}
              </option>
            ))}
          </select>

          {/* Year Dropdown */}
          <select
            value={currentYear}
            onChange={(e) => setCurrentYear(Number(e.target.value))}
            className="bg-black/40 border border-white/15 rounded text-xs text-white px-2 py-1 focus:outline-none cursor-pointer"
          >
            {years.map((y) => (
              <option key={y} value={y} className="bg-gray-900 text-white">
                {y}
              </option>
            ))}
          </select>
        </div>

        <button
          onClick={handleNextMonth}
          className="p-1 text-white/60 hover:text-white hover:bg-white/10 rounded transition-colors"
          title="Next Month"
        >
          ›
        </button>
      </div>

      {/* Days of Week Header */}
      <div className="grid grid-cols-7 text-center text-[10px] font-medium text-white/40 uppercase py-1">
        <span>Su</span>
        <span>Mo</span>
        <span>Tu</span>
        <span>We</span>
        <span>Th</span>
        <span>Fr</span>
        <span>Sa</span>
      </div>

      {/* Interactive Calendar Days Grid */}
      <div className="grid grid-cols-7 gap-1">
        {calendarDays.map((item, index) => {
          if (!item) {
            return <div key={`empty-${index}`} className="h-8" />;
          }

          const isStart = isSelectedStart(item.dateStr);
          const isEnd = isSelectedEnd(item.dateStr);
          const inRange = isInRange(item.dateStr);

          return (
            <button
              key={item.dateStr}
              onClick={() => handleDayClick(item.dateStr)}
              className={`h-8 text-xs rounded-lg font-medium transition-all flex items-center justify-center
                ${isStart || isEnd
                  ? 'bg-cyan-500 text-black font-bold shadow-lg scale-105 z-10'
                  : inRange
                  ? 'bg-cyan-500/20 text-cyan-300 rounded-none'
                  : 'text-white/80 hover:bg-white/10'
                }
              `}
            >
              {item.day}
            </button>
          );
        })}
      </div>

      {/* Selection Summary */}
      <div className="p-2 bg-black/30 border border-white/10 rounded-lg text-xs flex items-center justify-between text-white/70">
        <div>
          <span className="text-white/40">Range: </span>
          <span className="font-mono text-cyan-400 font-semibold">
            {tempStart || 'Start'} → {tempEnd || 'End'}
          </span>
        </div>
      </div>

      {/* Quick Quarter Presets */}
      <div className="flex items-center justify-between gap-1 pt-1 border-t border-white/10">
        {(['Q1', 'Q2', 'Q3', 'Q4'] as const).map((q) => (
          <button
            key={q}
            onClick={() => handleQuickPreset(q)}
            className="flex-1 py-1 bg-white/5 hover:bg-white/10 text-[11px] text-white/70 rounded transition-colors"
          >
            {q}
          </button>
        ))}
      </div>

      {/* Action Footer */}
      <div className="flex items-center justify-between pt-2">
        <button
          onClick={() => {
            setTempStart('');
            setTempEnd('');
            onSelectRange('', '');
            onClose();
          }}
          className="text-xs text-white/40 hover:text-white transition-colors"
        >
          Clear Filter
        </button>
        <button
          onClick={() => {
            onSelectRange(tempStart, tempEnd);
            onClose();
          }}
          className="px-3 py-1.5 bg-gradient-to-r from-cyan-500 to-blue-500 hover:from-cyan-400 hover:to-blue-400 text-black font-semibold text-xs rounded-lg transition-all shadow-md"
        >
          Apply Range
        </button>
      </div>
    </div>
  );
}
