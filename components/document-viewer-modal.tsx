'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';

interface DocumentViewerModalProps {
  filename: string | null;
  isOpen: boolean;
  onClose: () => void;
}

export function DocumentViewerModal({ filename, isOpen, onClose }: DocumentViewerModalProps) {
  const [content, setContent] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<boolean>(false);

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
  const fileUrl = filename ? `${apiUrl}/api/documents/view/${encodeURIComponent(filename)}` : '';
  const downloadUrl = filename ? `${apiUrl}/api/documents/view/${encodeURIComponent(filename)}?download=true` : '';

  useEffect(() => {
    if (!filename || !isOpen) {
      setContent(null);
      setError(null);
      return;
    }

    const fetchDocument = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(fileUrl);
        if (!res.ok) throw new Error(`HTTP Error ${res.status}: ${res.statusText}`);
        
        const contentType = res.headers.get('content-type') || '';
        if (contentType.includes('application/pdf')) {
          // PDFs rendered via iframe/embed
          setContent('pdf');
        } else {
          // Text/CSV documents fetched as plain text
          const text = await res.text();
          setContent(text);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to fetch document contents');
      } finally {
        setLoading(false);
      }
    };

    fetchDocument();
  }, [filename, isOpen, fileUrl]);

  if (!isOpen || !filename) return null;

  const isPdf = filename.toLowerCase().endsWith('.pdf');

  const handleCopyText = () => {
    if (content && content !== 'pdf') {
      navigator.clipboard.writeText(content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 md:p-10 bg-black/80 backdrop-blur-md">
        <motion.div
          initial={{ opacity: 0, scale: 0.95, y: 15 }}
          animate={{ opacity: 1, scale: 1, y: 0 }}
          exit={{ opacity: 0, scale: 0.95, y: 15 }}
          className="relative w-full max-w-5xl h-[85vh] bg-[#0d1322] border border-white/20 rounded-2xl shadow-2xl flex flex-col overflow-hidden"
        >
          {/* Top Bar Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 bg-black/40">
            <div className="flex items-center gap-3 min-w-0">
              <div className="w-9 h-9 rounded-xl bg-cyan-500/20 border border-cyan-500/30 flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <div className="min-w-0">
                <h3 className="text-sm font-semibold text-white truncate" title={filename}>
                  {filename}
                </h3>
                <p className="text-xs text-white/50">Frontend Document Previewer</p>
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-shrink-0">
              {content && content !== 'pdf' && (
                <button
                  onClick={handleCopyText}
                  className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-medium text-white/80 transition-all flex items-center gap-1.5"
                >
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                  </svg>
                  {copied ? 'Copied!' : 'Copy Text'}
                </button>
              )}

              <a
                href={downloadUrl}
                download
                className="px-3 py-1.5 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-black font-semibold text-xs transition-all flex items-center gap-1.5 shadow-md shadow-cyan-500/20"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download File
              </a>

              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-white/50 hover:text-white hover:bg-white/10 transition-colors"
                aria-label="Close modal"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>
          </div>

          {/* Main Viewer Body */}
          <div className="flex-1 overflow-auto p-6 bg-[#0a0e1a]">
            {loading ? (
              <div className="flex flex-col items-center justify-center h-full gap-3">
                <div className="w-8 h-8 border-2 border-cyan-400/30 border-t-cyan-400 rounded-full animate-spin" />
                <span className="text-sm text-white/50">Fetching document contents...</span>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full text-center p-6">
                <div className="w-12 h-12 rounded-full bg-red-500/10 border border-red-500/20 flex items-center justify-center mb-3">
                  <svg className="w-6 h-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-white mb-1">Could not display document</h4>
                <p className="text-xs text-white/50 max-w-md mb-4">{error}</p>
                <a
                  href={downloadUrl}
                  download
                  className="btn-secondary text-xs"
                >
                  Download File Instead
                </a>
              </div>
            ) : isPdf ? (
              <iframe
                src={fileUrl}
                className="w-full h-full rounded-lg border border-white/10 bg-white"
                title={`Preview ${filename}`}
              />
            ) : content ? (
              <div className="p-4 rounded-xl bg-black/40 border border-white/10 font-mono text-xs text-white/90 whitespace-pre-wrap leading-relaxed overflow-x-auto selection:bg-cyan-500/30">
                {content}
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-white/40 text-sm">
                No document content available
              </div>
            )}
          </div>

          {/* Footer Bar */}
          <div className="px-6 py-3 border-t border-white/10 bg-black/40 flex items-center justify-between text-xs text-white/40">
            <span>Status: Document Ingested & Verified</span>
            <a
              href={fileUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="text-cyan-400/80 hover:text-cyan-300 hover:underline transition-colors flex items-center gap-1 font-medium"
            >
              Open in Full Browser Tab ↗
            </a>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  );
}
