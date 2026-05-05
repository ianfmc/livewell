import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import React from 'react';
import { A2uiProvider } from '../a2ui/A2uiProvider';
import { useSignalExplain } from './useSignalExplain';

// ── EventSource mock ──────────────────────────────────────────────────────────
type ESHandler = (event: MessageEvent) => void;

class MockEventSource {
  static instances: MockEventSource[] = [];
  url: string;
  onmessage: ESHandler | null = null;
  onerror: ((e: Event) => void) | null = null;
  readyState = 0;
  private _closed = false;

  constructor(url: string) {
    this.url = url;
    MockEventSource.instances.push(this);
  }

  dispatchMessage(data: string) {
    this.onmessage?.(new MessageEvent('message', { data }));
  }

  close() { this._closed = true; this.readyState = 2; }
  get closed() { return this._closed; }
}

// ── Tests ─────────────────────────────────────────────────────────────────────

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <A2uiProvider>{children}</A2uiProvider>
);

beforeEach(() => {
  MockEventSource.instances = [];
  global.EventSource = MockEventSource as any;
});

afterEach(() => {
  delete (global as any).EventSource;
});

describe('useSignalExplain', () => {
  it('starts loading when signalId is provided', () => {
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    expect(result.current.loading).toBe(true);
    expect(result.current.surface).toBeNull();
  });

  it('returns null surface and loading=false when signalId is null', () => {
    const { result } = renderHook(() => useSignalExplain(null), { wrapper });
    expect(result.current.loading).toBe(false);
    expect(result.current.surface).toBeNull();
  });

  it('opens EventSource to correct URL', () => {
    renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    expect(MockEventSource.instances).toHaveLength(1);
    expect(MockEventSource.instances[0].url).toBe('/api/explain/EURUSD__2026-05-04');
  });

  it('processes SSE messages through MessageProcessor', async () => {
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    const es = MockEventSource.instances[0];

    await act(async () => {
      es.dispatchMessage(JSON.stringify({
        version: 'v0.9',
        createSurface: {
          surfaceId: 'explain-EURUSD__2026-05-04',
          catalogId: 'https://a2ui.org/specification/v0_9/basic_catalog.json',
        },
      }));
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.surface).not.toBeNull();
  });

  it('sets error when EventSource fires onerror', async () => {
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    const es = MockEventSource.instances[0];

    await act(async () => {
      es.onerror?.(new Event('error'));
    });

    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
  });

  it('closes EventSource on unmount', () => {
    const { result, unmount } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'), { wrapper });
    const es = MockEventSource.instances[0];
    unmount();
    expect(es.closed).toBe(true);
  });
});
