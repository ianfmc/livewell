import { useEffect, useState } from 'react';
import type { ModelHealth } from '../data/mockModelHealth';

type UseModelHealthResult = {
  data: ModelHealth | null;
  loading: boolean;
  error: string | null;
};

export function useModelHealth(): UseModelHealthResult {
  const [data, setData] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/model/health', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<ModelHealth>;
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
