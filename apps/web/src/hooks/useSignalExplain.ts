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

type FetchState = {
  signalId: string | null;
  data: ExplainData | null;
  loading: boolean;
  error: string | null;
};

const EMPTY: FetchState = { signalId: null, data: null, loading: false, error: null };

export function useSignalExplain(signalId: string | null): UseSignalExplainResult {
  // Single state object keyed by the signalId it describes. The async fetch
  // writes it from callbacks (never synchronously in the effect body), so the
  // "no signal" and "loading" states are derived during render instead of being
  // set synchronously inside the effect (react-hooks/set-state-in-effect).
  const [state, setState] = useState<FetchState>(EMPTY);

  useEffect(() => {
    if (!signalId) return;

    let cancelled = false;
    fetch(`${API_BASE}/api/explain/${signalId}`)
      .then((res) => {
        if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
        return res.json() as Promise<ExplainData>;
      })
      .then((json) => {
        if (!cancelled) setState({ signalId, data: json, loading: false, error: null });
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setState({
            signalId,
            data: null,
            loading: false,
            error: err instanceof Error ? err.message : 'Failed to load explanation',
          });
        }
      });

    return () => { cancelled = true; };
  }, [signalId]);

  // Derive the result for the current signalId during render:
  //  - no signal  -> empty, not loading
  //  - fetched state matches current signalId -> use it
  //  - otherwise (new signalId, fetch not yet resolved) -> loading
  if (!signalId) return { data: null, loading: false, error: null };
  if (state.signalId === signalId) {
    return { data: state.data, loading: state.loading, error: state.error };
  }
  return { data: null, loading: true, error: null };
}
