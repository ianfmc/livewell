import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useContractDetail } from './useContractDetail';

describe('useContractDetail', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useContractDetail('EUR/USD', '1.0850'));
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('returns data after successful fetch', async () => {
    const { result } = renderHook(() => useContractDetail('EUR/USD', '1.0850'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.instrument).toBe('EUR/USD');
    expect(result.current.data?.recommendation).toBe('Take');
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/signals/:instrument/:strike', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useContractDetail('EUR/USD', '1.0850'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBeNull();
  });
});
