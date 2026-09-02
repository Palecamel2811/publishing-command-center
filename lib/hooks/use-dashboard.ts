'use client';

import { useQuery } from '@tanstack/react-query';

export function useDashboardData(period?: string, startDate?: string, endDate?: string) {
  return useQuery({
    queryKey: ['dashboard', period || 'all', startDate || '', endDate || ''],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (period && period !== 'all') params.append('period', period);
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      
      const queryString = params.toString();
      const url = `http://localhost:8000/api/dashboard${queryString ? `?${queryString}` : ''}`;
      
      const res = await fetch(url);
      if (!res.ok) throw new Error('Failed to fetch dashboard');
      return res.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });
}
