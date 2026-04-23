import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useSignals } from './useSignals';

describe('useSignals', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useSignals());
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('populates data after successful fetch', async () => {
    const { result } = renderHook(() => useSignals());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toHaveLength(3);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/signals', () => HttpResponse.json({ message: 'error' }, { status: 500 }))
    );
    const { result } = renderHook(() => useSignals());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toHaveLength(0);
  });
});
