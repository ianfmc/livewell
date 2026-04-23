import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useModelHealth } from './useModelHealth';

describe('useModelHealth', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useModelHealth());
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('populates data after successful fetch', async () => {
    const { result } = renderHook(() => useModelHealth());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.overallStatus).toBe('Warning');
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/model/health', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useModelHealth());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBeNull();
  });
});
