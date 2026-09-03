'use client';

import React from 'react';

interface SkeletonProps {
  className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-lg bg-gradient-to-r from-white/[0.05] via-white/[0.12] to-white/[0.05] bg-[length:200%_100%] ${className}`}
    />
  );
}

export function KPICardSkeleton() {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 backdrop-blur-md">
      <div className="flex items-center justify-between">
        <Skeleton className="h-4 w-28" />
        <Skeleton className="h-8 w-8 rounded-lg" />
      </div>
      <div className="mt-4 flex items-baseline justify-between">
        <Skeleton className="h-8 w-36" />
        <Skeleton className="h-4 w-16" />
      </div>
      <div className="mt-3">
        <Skeleton className="h-3 w-48" />
      </div>
    </div>
  );
}

export function ChartCardSkeleton({ height = 'h-72' }: { height?: string }) {
  return (
    <div className="rounded-xl border border-white/10 bg-white/[0.02] p-5 backdrop-blur-md">
      <div className="flex items-center justify-between mb-4">
        <Skeleton className="h-5 w-44" />
        <Skeleton className="h-8 w-24 rounded-lg" />
      </div>
      <div className={`${height} w-full flex items-end gap-3 pt-6`}>
        <Skeleton className="h-[40%] flex-1 rounded-t-sm" />
        <Skeleton className="h-[65%] flex-1 rounded-t-sm" />
        <Skeleton className="h-[85%] flex-1 rounded-t-sm" />
        <Skeleton className="h-[50%] flex-1 rounded-t-sm" />
        <Skeleton className="h-[75%] flex-1 rounded-t-sm" />
        <Skeleton className="h-[90%] flex-1 rounded-t-sm" />
      </div>
    </div>
  );
}

export function TableRowSkeleton({ columns = 5 }: { columns?: number }) {
  return (
    <div className="flex items-center justify-between gap-4 border-b border-white/5 py-4 px-2">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={i} className={`h-4 ${i === 0 ? 'w-44' : 'w-24'}`} />
      ))}
    </div>
  );
}
