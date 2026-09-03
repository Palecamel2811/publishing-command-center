'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { uploadFiles, uploadFile, getIngestionHistory, deleteDocument } from '@/lib/api';

import { DocumentViewerModal } from '@/components/document-viewer-modal';

interface UploadZoneProps {
  onUploadComplete?: (result: any) => void;
}

interface UploadFile {
  file: File;
  status: 'idle' | 'uploading' | 'success' | 'error';
  result?: any;
  error?: string;
}

interface IngestedDocItem {
  id: string;
  filename: string;
  rawFilename: string;
  chunks: number;
  works: string[];
  date: string;
}

export function UploadZone({ onUploadComplete }: UploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [deletingFilename, setDeletingFilename] = useState<string | null>(null);
  const [previewFilename, setPreviewFilename] = useState<string | null>(null);
  const [uploadedDocs, setUploadedDocs] = useState<IngestedDocItem[]>([]);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchHistory = useCallback(async () => {
    setIsRefreshing(true);
    try {
      const res = await getIngestionHistory(100);
      if (res?.history) {
        setUploadedDocs(res.history.map((item: any) => ({
          id: item.id,
          filename: item.filename.replace('.pdf.txt', '').replace('.txt', ''),
          rawFilename: item.filename,
          chunks: 1,
          works: item.work_title ? [item.work_title] : [],
          date: item.created_at.split('T')[0],
        })));
      }
    } catch (err) {
      console.error('Failed to load ingestion history', err);
    } finally {
      setTimeout(() => setIsRefreshing(false), 400);
    }
  }, []);


  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback(() => {
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    
    const droppedFiles = Array.from(e.dataTransfer.files);
    addFiles(droppedFiles);
  }, []);

  const addFiles = (newFiles: File[]) => {
    const uploadFilesList: UploadFile[] = newFiles.map(file => {
      const isTooLarge = file.size > 15 * 1024 * 1024;
      return {
        file,
        status: isTooLarge ? 'error' : 'idle',
        error: isTooLarge ? 'File exceeds 15MB cloud limit' : undefined,
      };
    });
    setFiles(prev => [...prev, ...uploadFilesList]);
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const selectedFiles = Array.from(e.target.files);
      addFiles(selectedFiles);
    }
  };


  const handleUpload = async () => {
    if (files.length === 0 || isUploading) return;
    
    setIsUploading(true);
    const filesToUpload = files.filter(f => f.status === 'idle').map(f => f.file);
    
    if (filesToUpload.length === 0) {
      setIsUploading(false);
      return;
    }

    try {
      let result: any = null;
      try {
        result = await uploadFiles(filesToUpload, 'split_sheet');
      } catch (batchErr) {
        // Fallback: upload one by one if batch upload fails on mobile network
        const singleResults = [];
        for (const file of filesToUpload) {
          const res = await uploadFile(file, 'split_sheet');
          singleResults.push({ result: res?.result, chunks: res?.result?.chunks_created || 1 });
        }
        result = { results: singleResults };
      }
      
      setFiles(prev => prev.map((f, idx) => {
        if (f.status === 'idle' || f.status === 'uploading') {
          const batchResult = result?.results?.[idx] || result?.result || result;
          const hasError = !batchResult || batchResult.error || (batchResult.warnings && batchResult.warnings.length > 0 && (!batchResult.result && !batchResult.chunks_created));
          const errorMsg = batchResult?.error || batchResult?.warnings?.[0] || 'Upload processing error';
          return {
            ...f,
            status: hasError ? 'error' : 'success',
            error: hasError ? errorMsg : undefined,
          };
        }
        return f;
      }));

      // Instantly add successful files to staged uploadedDocs list
      const todayStr = new Date().toISOString().split('T')[0];
      const newlyUploadedItems: IngestedDocItem[] = filesToUpload.map((file, idx) => {
        const itemRes = result?.results?.[idx]?.result || result?.result || {};
        return {
          id: `new-${Date.now()}-${idx}`,
          filename: file.name.replace('.pdf.txt', '').replace('.txt', ''),
          rawFilename: file.name,
          chunks: itemRes.chunks_created || 1,
          works: itemRes.work_title ? [itemRes.work_title] : [],
          date: todayStr,
        };
      });

      setUploadedDocs(prev => {
        const existingNames = new Set(prev.map(d => d.rawFilename));
        const filteredNew = newlyUploadedItems.filter(item => !existingNames.has(item.rawFilename));
        return [...filteredNew, ...prev];
      });

      // Clear successful files from top queue so they transition smoothly down to staged list
      setTimeout(() => {
        setFiles(prev => prev.filter(f => f.status === 'error'));
      }, 600);

      await fetchHistory();
      onUploadComplete?.(result);
      
    } catch (error: any) {
      setFiles(prev => prev.map(f => 
        (f.status === 'idle' || f.status === 'uploading') ? { ...f, status: 'error', error: error.message || 'Upload failed' } : f
      ));
    } finally {
      setIsUploading(false);
    }
  };



  const removeFile = (index: number) => {
    setFiles(prev => prev.filter((_, i) => i !== index));
  };

  const clearQueue = () => {
    setFiles([]);
  };

  const handleDeleteDoc = async (rawFilename: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm(`Are you sure you want to remove "${rawFilename}"?\nThis will remove its vector embeddings and royalty data.`)) {
      return;
    }
    try {
      setDeletingFilename(rawFilename);
      await deleteDocument(rawFilename);
      setUploadedDocs(prev => prev.filter(d => d.rawFilename !== rawFilename && d.filename !== rawFilename));
      if (onUploadComplete) {
        onUploadComplete(null);
      }
    } catch (err: any) {
      alert(`Failed to delete document: ${err.message}`);
    } finally {
      setDeletingFilename(null);
    }
  };

  const progress = files.length > 0 
    ? Math.round((files.filter(f => f.status === 'success').length / files.length) * 100)
    : 0;

  const [selectedDocs, setSelectedDocs] = useState<string[]>([]);
  const [isBulkDeleting, setIsBulkDeleting] = useState(false);

  const toggleSelectDoc = (rawFilename: string) => {
    setSelectedDocs(prev => 
      prev.includes(rawFilename) 
        ? prev.filter(f => f !== rawFilename) 
        : [...prev, rawFilename]
    );
  };

  const toggleSelectAll = () => {
    if (selectedDocs.length === uploadedDocs.length) {
      setSelectedDocs([]);
    } else {
      setSelectedDocs(uploadedDocs.map(d => d.rawFilename));
    }
  };

  const handleBulkDelete = async () => {
    if (selectedDocs.length === 0) return;
    if (!confirm(`Are you sure you want to delete ${selectedDocs.length} selected document(s)?\nThis will remove all associated vector embeddings, splits, and royalty entries.`)) {
      return;
    }

    setIsBulkDeleting(true);
    try {
      await bulkDeleteDocuments(selectedDocs);
      setSelectedDocs([]);
      fetchHistory();
      if (onUploadComplete) {
        onUploadComplete(null);
      }
    } catch (err: any) {
      alert(`Bulk delete failed: ${err.message}`);
    } finally {
      setIsBulkDeleting(false);
    }
  };

  const handleBulkExport = () => {
    if (selectedDocs.length === 0) return;
    const selectedItems = uploadedDocs.filter(d => selectedDocs.includes(d.rawFilename));
    const csvContent = "data:text/csv;charset=utf-8," + 
      "Filename,Chunks,Associated Works,Date Added\n" +
      selectedItems.map(d => `"${d.rawFilename}",${d.chunks},"${d.works.join('; ')}",${d.date}`).join("\n");
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", `catalog_export_${new Date().toISOString().split('T')[0]}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="space-y-6">
      {/* Upload Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`
          relative border-2 border-dashed rounded-xl p-8 text-center cursor-pointer
          transition-all duration-200 group
          ${isDragging 
            ? 'border-cyan-400 bg-cyan-500/10' 
            : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/[0.05]'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.txt,.csv,.docx,.xlsx,application/pdf,text/plain,text/csv,application/vnd.openxmlformats-officedocument.wordprocessingml.document,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
          onChange={handleFileSelect}
          className="hidden"
        />
        
        <div className="flex flex-col items-center gap-3">
          <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-cyan-500/20 to-blue-600/20 border border-cyan-500/30 flex items-center justify-center group-hover:scale-110 transition-transform">
            <svg className="w-6 h-6 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
            </svg>
          </div>
          <div>
            <p className="text-sm font-medium text-white/90">
              Drop publishing documents here, or <span className="text-cyan-400">browse</span>
            </p>
            <p className="text-xs text-white/40 mt-1">
              Supports PDF, CSV, TXT, DOCX, XLSX (split sheets, royalty statements, sync contracts)
            </p>
          </div>
        </div>
      </div>

      {/* Selected File Queue Preview */}
      <AnimatePresence>
        {files.length > 0 && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="space-y-3"
          >
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-medium text-white/60">Selected Files Ready to Process ({files.length})</h3>
              <button
                onClick={clearQueue}
                className="text-xs text-white/40 hover:text-white/70 transition-colors"
              >
                Clear Queue
              </button>
            </div>

            <div className="space-y-2">
              {files.map((file, index) => (
                <motion.div
                  key={`${file.file.name}-${index}`}
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 10 }}
                  className="panel-card p-3 flex items-center justify-between"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <div className="w-8 h-8 rounded bg-white/5 flex items-center justify-center text-xs font-mono text-cyan-400">
                      {file.file.name.split('.').pop()?.toUpperCase()}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm text-white/80 truncate">{file.file.name}</p>
                      <p className="text-xs text-white/40">
                        {(file.file.size / 1024).toFixed(1)} KB
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3 flex-shrink-0">
                    {file.status === 'uploading' && (
                      <span className="text-xs text-cyan-400 flex items-center gap-1.5">
                        <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                        </svg>
                        Processing...
                      </span>
                    )}
                    {file.status === 'success' && (
                      <span className="text-xs text-emerald-400 flex items-center gap-1">
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Done
                      </span>
                    )}
                    {file.status === 'error' && (
                      <span className="text-xs text-red-400 flex items-center gap-1" title={file.error}>
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                        Failed
                      </span>
                    )}

                    <button
                      onClick={(e) => { e.stopPropagation(); removeFile(index); }}
                      className="text-white/30 hover:text-white/60 transition-colors"
                      title="Remove file from queue"
                    >
                      <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>

            {/* Upload Button */}
            <div className="flex items-center justify-between pt-2">
              <span className="text-sm text-white/60">
                Ready to upload: {files.filter(f => f.status === 'idle').length} file(s)
              </span>
              <button
                onClick={handleUpload}
                disabled={isUploading || files.filter(f => f.status === 'idle').length === 0}
                className={`
                  px-5 py-2 rounded-lg text-sm font-medium transition-all flex items-center gap-2
                  ${isUploading || files.filter(f => f.status === 'idle').length === 0
                    ? 'bg-white/10 text-white/40 cursor-not-allowed'
                    : 'bg-cyan-500 hover:bg-cyan-400 text-black font-semibold shadow-lg shadow-cyan-500/20'
                  }
                `}
              >
                {isUploading ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                    </svg>
                    Uploading...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Upload & Process
                  </>
                )}
              </button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Ingested Catalog Documents Header with Bulk Selection */}
      {uploadedDocs.length > 0 && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="space-y-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-3 bg-white/[0.02] p-3 rounded-xl border border-white/10">
            <div className="flex items-center gap-3">
              <label className="flex items-center gap-2 text-xs text-white/70 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={selectedDocs.length === uploadedDocs.length && uploadedDocs.length > 0}
                  onChange={toggleSelectAll}
                  className="rounded border-white/20 bg-black/40 text-cyan-500 focus:ring-cyan-500"
                />
                <span className="font-medium">
                  {selectedDocs.length > 0 ? `Selected (${selectedDocs.length}/${uploadedDocs.length})` : 'Select All'}
                </span>
              </label>
              <h3 className="text-xs text-white/40 border-l border-white/10 pl-3">
                Original Uploaded Assets ({uploadedDocs.length})
              </h3>
            </div>

            <div className="flex items-center gap-2">
              {selectedDocs.length > 0 && (
                <>
                  <button
                    onClick={handleBulkExport}
                    className="px-3 py-1.5 rounded-lg bg-cyan-500/10 hover:bg-cyan-500/20 text-cyan-400 text-xs font-medium border border-cyan-500/20 transition-all flex items-center gap-1.5"
                    title="Export selected document metadata as CSV"
                  >
                    <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                    </svg>
                    Export Metadata ({selectedDocs.length})
                  </button>

                  <button
                    onClick={handleBulkDelete}
                    disabled={isBulkDeleting}
                    className="px-3 py-1.5 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-400 text-xs font-medium border border-red-500/30 transition-all flex items-center gap-1.5"
                  >
                    {isBulkDeleting ? (
                      <svg className="w-3.5 h-3.5 animate-spin text-red-400" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                    ) : (
                      <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    )}
                    Delete Selected ({selectedDocs.length})
                  </button>
                </>
              )}

              <button
                onClick={fetchHistory}
                disabled={isRefreshing}
                className="text-xs text-cyan-400 hover:text-cyan-300 transition-colors flex items-center gap-1 px-2 py-1.5 rounded hover:bg-white/5 disabled:opacity-50"
              >
                <svg className={`w-3.5 h-3.5 ${isRefreshing ? 'animate-spin' : ''}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                {isRefreshing ? 'Refreshing...' : 'Refresh'}
              </button>

            </div>
          </div>
          
          {/* Document Asset Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {uploadedDocs.map((doc) => {
              const isSelected = selectedDocs.includes(doc.rawFilename);
              return (
                <motion.div
                  key={doc.id || doc.rawFilename}
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  className={`panel-card p-4 transition-all group ${isSelected ? 'border-cyan-500/50 bg-cyan-500/[0.03]' : 'hover:border-white/20'}`}
                >
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex items-center gap-3 min-w-0">
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={() => toggleSelectDoc(doc.rawFilename)}
                        className="rounded border-white/20 bg-black/40 text-cyan-500 focus:ring-cyan-500 cursor-pointer"
                      />
                      <div className="w-8 h-8 rounded-lg bg-cyan-500/10 flex items-center justify-center flex-shrink-0">
                        <svg className="w-4 h-4 text-cyan-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-white/80 truncate" title={doc.rawFilename}>{doc.filename}</p>
                        <p className="text-xs text-white/40">Added {doc.date}</p>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 flex-shrink-0">
                      <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded">
                        Indexed
                      </span>

                      {/* View Original Document */}
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setPreviewFilename(doc.rawFilename || doc.filename);
                        }}
                        className="p-1.5 rounded-lg text-white/40 hover:text-cyan-300 hover:bg-cyan-500/10 transition-all flex items-center gap-1 text-xs"
                        title="View original file"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                        <span className="hidden sm:inline">View</span>
                      </button>

                      {/* Download Original Document */}
                      <a
                        href={`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/documents/view/${encodeURIComponent(doc.rawFilename || doc.filename)}?download=true`}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="p-1.5 rounded-lg text-white/40 hover:text-emerald-300 hover:bg-emerald-500/10 transition-all flex items-center gap-1 text-xs"
                        title="Download file"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                        </svg>
                        <span className="hidden sm:inline">Download</span>
                      </a>

                      {/* Delete Document */}
                      <button
                        onClick={(e) => handleDeleteDoc(doc.rawFilename || doc.filename, e)}
                        disabled={deletingFilename === (doc.rawFilename || doc.filename)}
                        className="p-1.5 rounded-lg text-white/30 hover:text-red-400 hover:bg-red-500/10 transition-all"
                        title="Remove document"
                      >
                        {deletingFilename === (doc.rawFilename || doc.filename) ? (
                          <svg className="w-4 h-4 animate-spin text-red-400" fill="none" viewBox="0 0 24 24">
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {doc.works.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-2 pl-7">
                      {doc.works.slice(0, 3).map((work: string) => (
                        <span key={work} className="text-xs bg-white/5 text-cyan-300/80 px-2 py-0.5 rounded border border-white/5">
                          Work: {work}
                        </span>
                      ))}
                      {doc.works.length > 3 && (
                        <span className="text-xs bg-white/5 text-white/40 px-2 py-0.5 rounded">
                          +{doc.works.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </motion.div>
              );
            })}
          </div>
        </motion.div>
      )}

      {/* In-App Document Preview Modal */}
      <DocumentViewerModal
        filename={previewFilename}
        isOpen={!!previewFilename}
        onClose={() => setPreviewFilename(null)}
      />
    </div>
  );
}
