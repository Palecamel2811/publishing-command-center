'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface SidebarItem {
  id: string;
  label: string;
  icon: string;
  shortcut: string;
}

interface SidebarProps {
  items: SidebarItem[];
  activePage: string;
  onNavigate: (id: string) => void;
  isOpen: boolean;
}

export function Sidebar({ items, activePage, onNavigate, isOpen }: SidebarProps) {
  const [hoveredId, setHoveredId] = useState<string | null>(null);

  return (
    <motion.aside
      initial={false}
      animate={{ width: isOpen ? 240 : 64 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="flex flex-col border-r border-white/10 bg-black/30 backdrop-blur-xl flex-shrink-0 overflow-hidden"
    >
      {/* Logo */}
      <div className="h-14 flex items-center px-4 border-b border-white/10 flex-shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center flex-shrink-0">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 6l12-3" />
            </svg>
          </div>
          <AnimatePresence>
            {isOpen && (
              <motion.div
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="overflow-hidden whitespace-nowrap"
              >
                <span className="text-sm font-bold text-white">PCC</span>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-3 px-2 space-y-1">
        {items.map((item) => {
          const isActive = activePage === item.id;
          const isHovered = hoveredId === item.id;
          
          return (
            <button
              key={item.id}
              onClick={() => onNavigate(item.id)}
              onMouseEnter={() => setHoveredId(item.id)}
              onMouseLeave={() => setHoveredId(null)}
              className={`w-full flex items-center gap-3 rounded-lg transition-all duration-150 group
                ${isActive 
                  ? 'bg-cyan-500/15 text-cyan-400' 
                  : 'text-white/60 hover:text-white hover:bg-white/5'
                }`}
              style={{ height: '40px' }}
              aria-label={item.label}
              title={`${item.label} (${item.shortcut})`}
            >
              {/* Icon */}
              <div className={`flex-shrink-0 w-5 h-5 transition-colors
                ${isActive ? 'text-cyan-400' : isHovered ? 'text-white/80' : ''}`}>
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                  <path strokeLinecap="round" strokeLinejoin="round" d={item.icon} />
                </svg>
              </div>
              
              {/* Label + shortcut */}
              <AnimatePresence>
                {isOpen && (
                  <motion.div
                    initial={{ opacity: 0, width: 0 }}
                    animate={{ opacity: 1, width: 'auto' }}
                    exit={{ opacity: 0, width: 0 }}
                    className="flex items-center gap-2 overflow-hidden whitespace-nowrap"
                  >
                    <span className="text-sm font-medium flex-1 text-left">{item.label}</span>
                    <span className="text-[10px] text-white/20 font-mono bg-white/5 px-1.5 py-0.5 rounded">
                      {item.shortcut}
                    </span>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Tooltip when collapsed */}
              {!isOpen && isHovered && (
                <div className="absolute left-16 z-50 px-2 py-1 bg-gray-900 border border-white/20 rounded-md text-xs text-white whitespace-nowrap shadow-lg">
                  {item.label} <span className="text-white/40 ml-1">({item.shortcut})</span>
                </div>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Section */}
      <div className="p-2 border-t border-white/10">
        <button 
          onClick={() => onNavigate('assets')}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg text-white/40 hover:text-white/80 hover:bg-white/5 transition-all text-sm group"
          title="Manage Documents & Assets"
        >
          <svg className="w-5 h-5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <AnimatePresence>
            {isOpen && (
              <motion.span
                initial={{ opacity: 0, width: 0 }}
                animate={{ opacity: 1, width: 'auto' }}
                exit={{ opacity: 0, width: 0 }}
                className="overflow-hidden whitespace-nowrap text-sm"
              >
                Settings
              </motion.span>
            )}
          </AnimatePresence>
        </button>
      </div>
    </motion.aside>
  );
}
