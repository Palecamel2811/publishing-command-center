'use client';

import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { queryRAG } from '@/lib/api';
import { DocumentViewerModal } from '@/components/document-viewer-modal';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: Source[];
  loading?: boolean;
}

interface Source {
  filename: string;
  content: string;
  score: number;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [previewFilename, setPreviewFilename] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Focus input on mount and Cmd+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        inputRef.current?.focus();
      }
      if (e.key === '/' && document.activeElement !== inputRef.current) {
        e.preventDefault();
        inputRef.current?.focus();
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsTyping(true);

    try {
      // Try real RAG API, fall back to mock if unavailable
      const response = await getFallbackResponse(userMessage.content);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.content,
        timestamp: new Date().toISOString(),
        sources: response.sources,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } catch {
      // Ultimate fallback
      const fallback = generateMockResponse(userMessage.content);
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: fallback.content,
        timestamp: new Date().toISOString(),
        sources: fallback.sources,
      };
      setMessages(prev => [...prev, assistantMessage]);
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="flex flex-col h-full max-w-4xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-4 pb-3 border-b border-white/10">
        <div>
          <h2 className="text-lg font-semibold text-white">AI Query Assistant</h2>
          <p className="text-sm text-white/50">
            Ask about your publishing data, splits, royalties, and rights
          </p>
        </div>
        <div className="flex items-center gap-2">
          {messages.length > 0 && (
            <button
              onClick={() => setMessages([])}
              className="text-xs text-white/40 hover:text-white/80 px-2 py-1 rounded bg-white/5 hover:bg-white/10 transition-colors"
            >
              Clear conversation
            </button>
          )}
          <kbd className="px-2 py-1 text-xs bg-white/10 rounded font-mono text-white/40">
            ⌘K
          </kbd>
          <span className="text-xs text-white/30">to focus</span>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pr-2">
        <AnimatePresence>
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onSelectSource={(fn) => setPreviewFilename(fn)}
            />
          ))}
          {isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-start gap-3"
            >
              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-cyan-400 to-blue-600 flex items-center justify-center flex-shrink-0">
                <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
              </div>
              <div className="glass rounded-2xl px-4 py-3 flex items-center gap-3">
                <div className="flex gap-1.5">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
                <span className="text-xs text-cyan-300/80 font-mono animate-pulse">
                  Searching vector store & synthesizing answer...
                </span>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
        <div ref={messagesEndRef} />

        {/* Empty state */}
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center py-20">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/20 flex items-center justify-center mb-6">
              <svg className="w-8 h-8 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-white mb-2">Ask about your publishing data</h3>
            <p className="text-sm text-white/50 max-w-md mb-8">
              Try asking about your royalties, splits, sync licenses, or upload documents for AI-powered analysis
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-w-2xl w-full">
              {[
                'How much did I earn from Spotify last quarter?',
                'Who has publishing rights for Midnight Echoes?',
                'Show my top earning works',
                'Are there any reconciliation issues?',
                'What are my sync license terms?',
              ].map((suggestion) => (
                <button
                  key={suggestion}
                  onClick={() => {
                    setInput(suggestion);
                    inputRef.current?.focus();
                  }}
                  className="text-left p-3 rounded-xl bg-white/5 border border-white/10 text-sm text-white/60 hover:text-white hover:bg-white/10 hover:border-cyan-500/30 transition-all"
                >
                  {suggestion}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="mt-4">
        <div className="glass rounded-2xl p-2">
          <div className="flex items-end gap-2">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e);
                }
              }}
              placeholder="Ask about your publishing data... (Press Enter to send, Shift+Enter for new line)"
              className="flex-1 bg-transparent border-none outline-none resize-none text-white text-sm placeholder:text-white/30 max-h-32 min-h-[44px]"
              rows={1}
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="w-10 h-10 rounded-xl bg-cyan-500 hover:bg-cyan-400 disabled:bg-white/10 disabled:cursor-not-allowed flex items-center justify-center transition-all flex-shrink-0"
            >
              <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
              </svg>
            </button>
          </div>
        </div>
      </form>
      {/* In-App Document Preview Modal */}
      <DocumentViewerModal
        filename={previewFilename}
        isOpen={!!previewFilename}
        onClose={() => setPreviewFilename(null)}
      />
    </div>
  );
}

function MessageBubble({ message, onSelectSource }: { message: Message; onSelectSource?: (filename: string) => void }) {
  const isUser = message.role === 'user';

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex items-start gap-3 ${isUser ? 'flex-row-reverse' : ''}`}
    >
      {/* Avatar */}
      <div className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
        isUser 
          ? 'bg-gradient-to-br from-purple-500 to-pink-600' 
          : 'bg-gradient-to-br from-cyan-400 to-blue-600'
      }`}>
        <svg className="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          {isUser ? (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
          ) : (
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
          )}
        </svg>
      </div>

      {/* Content */}
      <div className={`max-w-[80%] ${isUser ? 'items-end' : 'items-start'}`}>
        <div className={`rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-cyan-500/20 border border-cyan-500/20'
            : 'glass rounded-tl-md'
        }`}>
          <p className="text-sm text-white/90 whitespace-pre-wrap leading-relaxed">
            {message.content}
          </p>
        </div>

        {/* Sources */}
        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-2 space-y-1.5">
            {message.sources.slice(0, 3).map((source, i) => (
              <button
                key={i}
                onClick={() => onSelectSource?.(source.filename)}
                className="w-full flex items-center gap-2 text-xs text-white/50 hover:text-cyan-300 px-3 py-1.5 rounded-lg bg-white/[0.02] hover:bg-cyan-500/10 border border-white/5 hover:border-cyan-500/30 transition-all text-left group"
                title={`Click to preview ${source.filename} inside app`}
              >
                <svg className="w-3 h-3 flex-shrink-0 text-cyan-400/70 group-hover:text-cyan-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 01-2-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                <span className="truncate flex-1 font-mono">{source.filename}</span>
                <span className="text-cyan-400/60 font-mono text-[11px]">{(source.score * 100).toFixed(0)}%</span>
              </button>
            ))}
          </div>
        )}

        {/* Timestamp */}
        <span className="text-[10px] text-white/30 mt-1 block">
          {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </div>
    </motion.div>
  );
}

// Fallback mock responses for when the backend is unavailable
function generateMockResponse(query: string): { content: string; sources?: Source[] } {
  const q = query.toLowerCase();
  
  if (q.includes('spotify') && q.includes('earn')) {
    return {
      content: `Based on your publishing data, here's your Spotify earnings breakdown:\n\n**Q4 2024 (Oct-Dec)**\n• Gross revenue: $42,389.12\n• Net revenue: $38,150.21\n• Streaming revenue: $35,678.90\n• Download revenue: $2,471.31\n\n**Top performing tracks:**\n1. Midnight Echoes - $18,234.56 (43%)\n2. Golden Hour - $12,456.78 (29%)\n3. Neon Dreams - $8,901.23 (21%)\n\nThis represents a 12.4% increase from Q3 2024.`,
      sources: [
        { filename: 'spotify_q4_2024_statement.pdf', content: 'Spotify royalty report Q4 2024...', score: 0.95 },
        { filename: 'monthly_summary_oct.docx', content: 'October monthly summary...', score: 0.82 },
      ],
    };
  }
  
  if (q.includes('midnight echo') || q.includes('rights')) {
    return {
      content: `**Midnight Echoes - Rights & Ownership**\n\n**Publishing Split:**\n• You (Writer): 50%\n• Alex Rivers (Writer): 25%\n• Sunset Publishing (Publisher): 25%\n\n**Rights Administration:**\n• ASCAP: Performance rights registered\n• Admin: Your Publishing LLC\n• ISRC: USRC17607839\n• ISWC: T-901.234.567-8\n\n**Sync Licenses:**\n• Netflix - TV Series (active through Dec 2026) - $50,000\n\n**Royalty Collection Points:**\n• Spotify, Apple Music, YouTube, Amazon Music`,
      sources: [
        { filename: 'midnight_echoes_split_sheet.pdf', content: 'Split sheet for Midnight Echoes...', score: 0.97 },
        { filename: 'netflix_sync_contract.pdf', content: 'Netflix licensing agreement...', score: 0.89 },
        { filename: 'pro_registrations.csv', content: 'PRO registration data...', score: 0.76 },
      ],
    };
  }

  if (q.includes('reconcil') || q.includes('discrepan')) {
    return {
      content: `**Reconciliation Status**\n\nI found 3 discrepancies in your data:\n\n🔴 **High Priority:**\n• Apple Music reported 1.2M streams vs your distributor's 980K for Golden Hour (Q4 2024)\n  - Difference: ~$1,240 in reported revenue\n  - Action: Contact Apple Music support or verify with distributor\n\n🟡 **Medium Priority:**\n• YouTube Content ID shows 45K views not reflected in AdSense report\n• ASCAP statement not yet received for Q4 2024\n\nAll other platform data is reconciled and consistent.`,
      sources: [
        { filename: 'apple_music_q4.csv', content: 'Apple Music royalty data Q4...', score: 0.88 },
        { filename: 'distributor_report_q4.xlsx', content: 'Distributor quarterly report...', score: 0.85 },
      ],
    };
  }

  // Default response
  return {
    content: `I've analyzed your publishing data. Here's what I found:\n\nYour total earnings across all platforms for the current period are $284,563.42 (net: $241,879.18).\n\nSpotify remains your top platform with $142,389.12 in gross revenue. Your top earning work is "Midnight Echoes" with $89,234.50 across 3 platforms.\n\nWould you like me to dive deeper into any specific area - platform breakdown, work analysis, split verification, or sync license tracking?`,
    sources: [],
  };
}

// Fallback: use mock response when API is unavailable
async function getFallbackResponse(query: string): Promise<{ content: string; sources?: Source[] }> {
  try {
    const result = await queryRAG(query, { top_k: 5, score_threshold: 0.3 });
    // Transform RAGResponse to expected format
    return {
      content: result.response,
      sources: result.sources?.map((s: any) => ({
        filename: s.filename || s.metadata?.source_filename || 'Unknown',
        content: s.content || '',
        score: s.score || 0,
      })),
    };
  } catch {
    return generateMockResponse(query);
  }
}
