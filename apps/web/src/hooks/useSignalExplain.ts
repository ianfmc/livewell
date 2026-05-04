import { useEffect, useState, useRef } from 'react';
import type { SurfaceModel } from '@a2ui/web_core/v0_9';
import type { ReactComponentImplementation } from '@a2ui/react/v0_9';
import { useA2ui } from '../a2ui/useA2ui';

type UseSignalExplainResult = {
  surface: SurfaceModel<ReactComponentImplementation> | null;
  loading: boolean;
  error: string | null;
};

export function useSignalExplain(signalId: string | null): UseSignalExplainResult {
  const processor = useA2ui();
  const [surface, setSurface] = useState<SurfaceModel<ReactComponentImplementation> | null>(null);
  const [loading, setLoading] = useState(signalId !== null);
  const [error, setError] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!signalId) {
      setLoading(false);
      setSurface(null);
      setError(null);
      return;
    }

    const surfaceId = `explain-${signalId}`;
    setLoading(true);
    setError(null);
    setSurface(null);

    const es = new EventSource(`/api/explain/${signalId}`);
    esRef.current = es;

    es.onmessage = (event: MessageEvent) => {
      try {
        const msg = JSON.parse(event.data as string);
        processor.processMessages([msg]);

        if ('createSurface' in msg) {
          const s = processor.model.getSurface(surfaceId);
          if (s) setSurface(s);
          setLoading(false);
        }
      } catch {
        setError('Failed to parse SSE message');
        setLoading(false);
      }
    };

    es.onerror = () => {
      setError('Connection error');
      setLoading(false);
      es.close();
    };

    return () => {
      es.close();
      esRef.current = null;
      // Clean up surface in processor
      try {
        processor.processMessages([{ version: 'v0.9', deleteSurface: { surfaceId } }]);
      } catch {
        // Surface may not exist if stream didn't start
      }
      setSurface(null);
    };
  }, [signalId, processor]);

  return { surface, loading, error };
}
