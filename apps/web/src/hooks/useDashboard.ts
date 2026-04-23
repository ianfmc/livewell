import { useEffect, useState } from 'react';
import type { DashboardData } from '../data/mockDashboard';

type UseDashboardResult = {
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
};

export function useDashboard(): UseDashboardResult {
  const [data, setData] = useState<DashboardData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/dashboard', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<DashboardData>;
      })
      .then((json) => { setData(json); })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { setLoading(false); });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
