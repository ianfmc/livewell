import { useEffect, useState } from 'react';
import type { ContractDetail } from '../data/mockData';

type UseContractDetailResult = {
  data: ContractDetail | null;
  loading: boolean;
  error: string | null;
};

export function useContractDetail(instrument: string, strike: string): UseContractDetailResult {
  const [data, setData] = useState<ContractDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const encodedInstrument = instrument.replace(/\//g, '-');
    fetch(`/api/signals/${encodedInstrument}/${strike}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<ContractDetail>;
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
  }, [instrument, strike]);

  return { data, loading, error };
}
