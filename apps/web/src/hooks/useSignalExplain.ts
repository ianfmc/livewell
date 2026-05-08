import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';

export type ExplainData = {
  header: string;
  trend: string;
  momentum: string;
  session: string;
  timing: string;
};

type UseSignalExplainResult = {
  data: ExplainData | null;
  loading: boolean;
  error: string | null;
};

export function useSignalExplain(signalId: string | null): UseSignalExplainResult {
  const [data, setData] = useState<ExplainData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!signalId) {
      setData(null);
      setError(null);
      setLoading(false);
      return;
    }

    let cancelled = false;
    setLoading(true);
    setError(null);
    setData(null);

    fetch(`${API_BASE}/api/explain/${signalId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json() as Promise<ExplainData>;
      })
      .then((json) => {
        if (!cancelled) {
          setData(json);
          setLoading(false);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load explanation');
          setLoading(false);
        }
      });

    return () => { cancelled = true; };
  }, [signalId]);

  return { data, loading, error };
}
