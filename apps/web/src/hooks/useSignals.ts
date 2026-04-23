import { useEffect, useState } from 'react';
import type { ContractCard } from '../data/mockData';

type UseSignalsResult = {
  data: ContractCard[];
  loading: boolean;
  error: string | null;
};

export function useSignals(): UseSignalsResult {
  const [data, setData] = useState<ContractCard[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/signals', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<ContractCard[]>;
      })
      .then((json) => {
        setData(json);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        setLoading(false);
      });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
