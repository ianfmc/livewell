import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { useSignalExplain } from './useSignalExplain';

const SAMPLE = {
  header: 'EUR/USD — model probability 0.62',
  trend: 'EMA-20 above EMA-50 (bullish).',
  momentum: 'RSI > 50, MACD histogram positive.',
  session: 'London session, high quality.',
  timing: 'Within the morning slot.',
};

beforeEach(() => {
  vi.restoreAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('useSignalExplain', () => {
  it('starts loading when signalId is provided', () => {
    vi.spyOn(globalThis, 'fetch').mockReturnValue(new Promise(() => {}) as unknown as Promise<Response>);
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'));
    expect(result.current.loading).toBe(true);
    expect(result.current.data).toBeNull();
  });

  it('returns null data and loading=false when signalId is null', () => {
    const { result } = renderHook(() => useSignalExplain(null));
    expect(result.current.loading).toBe(false);
    expect(result.current.data).toBeNull();
  });

  it('fetches the correct URL', () => {
    const spy = vi
      .spyOn(globalThis, 'fetch')
      .mockResolvedValue({ ok: true, json: async () => SAMPLE } as unknown as Response);
    renderHook(() => useSignalExplain('EURUSD__2026-05-04'));
    expect(spy).toHaveBeenCalledWith(expect.stringContaining('/api/explain/EURUSD__2026-05-04'));
  });

  it('populates data on success', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({ ok: true, json: async () => SAMPLE } as unknown as Response);
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toEqual(SAMPLE);
    expect(result.current.error).toBeNull();
  });

  it('sets error on non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false, status: 500, statusText: 'Internal Server Error',
    } as unknown as Response);
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBeNull();
  });

  it('sets error on fetch rejection', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('network down'));
    const { result } = renderHook(() => useSignalExplain('EURUSD__2026-05-04'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).toBe('network down');
  });
});
