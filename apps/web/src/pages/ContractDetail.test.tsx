import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import ContractDetail from './ContractDetail';

function renderDetail(url = '/signals/EUR-USD/1.0850') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/signals/:instrument/:strike" element={<ContractDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ContractDetail', () => {
  it('renders instrument and recommendation chip', async () => {
    renderDetail();
    expect(await screen.findByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('TAKE')).toBeInTheDocument();
  });

  it('renders 4-up metric strip', async () => {
    renderDetail();
    await screen.findByText('EUR/USD');
    expect(screen.getByText('$42')).toBeInTheDocument();
    expect(screen.getByText('$100')).toBeInTheDocument();
    expect(screen.getByText('68%')).toBeInTheDocument();
    expect(screen.getByText('+26%')).toBeInTheDocument();
  });

  it('renders reason codes', async () => {
    renderDetail();
    expect(await screen.findByText(/Bullish regime confirmed/)).toBeInTheDocument();
  });

  it('renders back link to Daily Signals', async () => {
    renderDetail();
    await screen.findByText('EUR/USD');
    expect(screen.getByRole('link', { name: /Daily Signals/i })).toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/signals/:instrument/:strike', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderDetail();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
