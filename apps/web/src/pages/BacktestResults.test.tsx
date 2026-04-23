import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import BacktestResults from './BacktestResults';

function renderPage() {
  return render(<MemoryRouter><BacktestResults /></MemoryRouter>);
}

describe('BacktestResults', () => {
  it('shows spinner while loading', () => {
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders summary metrics after load', async () => {
    renderPage();
    expect(await screen.findByText('84')).toBeInTheDocument();
    expect(screen.getByText('Total Trades')).toBeInTheDocument();
  });

  it('renders results table rows', async () => {
    renderPage();
    await screen.findByText('Total Trades');
    expect(screen.getAllByText('EUR/USD').length).toBeGreaterThan(0);
    expect(screen.getAllByText('GBP/USD').length).toBeGreaterThan(0);
    expect(screen.getAllByText('USD/JPY').length).toBeGreaterThan(0);
  });

  it('market filter reduces visible rows', async () => {
    renderPage();
    await screen.findByText('Total Trades');
    fireEvent.mouseDown(screen.getByLabelText('Market'));
    fireEvent.click(await screen.findByRole('option', { name: 'EUR/USD' }));
    expect(screen.getAllByRole('cell', { name: 'EUR/USD' }).length).toBeGreaterThan(0);
    expect(screen.queryByRole('cell', { name: 'GBP/USD' })).not.toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/backtest/summary', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
