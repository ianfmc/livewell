import { useEffect, useState } from 'react';
import type { BacktestSummary } from '../data/mockBacktest';

type UseBacktestResult = {
  data: BacktestSummary | null;
  loading: boolean;
  error: string | null;
};

export function useBacktest(): UseBacktestResult {
  const [data, setData] = useState<BacktestSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/backtest/summary', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<BacktestSummary>;
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
