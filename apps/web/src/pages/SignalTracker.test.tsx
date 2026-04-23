import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import SignalTracker from './SignalTracker';

function renderPage() {
  return render(<MemoryRouter><SignalTracker /></MemoryRouter>);
}

describe('SignalTracker', () => {
  it('shows spinner while loading', () => {
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders summary strip after load', async () => {
    renderPage();
    expect(await screen.findByText('Total Signals')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
  });

  it('renders signal table rows', async () => {
    renderPage();
    await screen.findByText('Total Signals');
    expect(screen.getAllByText('EUR/USD').length).toBeGreaterThan(0);
    expect(screen.getAllByText('GBP/USD').length).toBeGreaterThan(0);
  });

  it('recommendation filter reduces visible rows', async () => {
    renderPage();
    await screen.findByText('Total Signals');
    fireEvent.mouseDown(screen.getByLabelText('Recommendation'));
    fireEvent.click(await screen.findByRole('option', { name: 'Take' }));
    const rows = screen.getAllByRole('row');
    // header row + 8 "Take" rows in mock data
    expect(rows.length).toBe(9);
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/signals/tracker', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
