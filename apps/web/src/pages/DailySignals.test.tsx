import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import DailySignals from './DailySignals';

function renderPage() {
  return render(
    <MemoryRouter>
      <DailySignals />
    </MemoryRouter>
  );
}

describe('DailySignals', () => {
  it('renders contract cards after load', async () => {
    renderPage();
    expect(await screen.findByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('GBP/USD')).toBeInTheDocument();
    expect(screen.getByText('USD/JPY')).toBeInTheDocument();
  });

  it('shows spinner while loading', () => {
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('status filter reduces visible cards', async () => {
    renderPage();
    await screen.findByText('EUR/USD');

    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'Open' }));

    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('GBP/USD')).toBeInTheDocument();
    expect(screen.queryByText('USD/JPY')).not.toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/signals', () => HttpResponse.json({ message: 'error' }, { status: 500 }))
    );
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });

  it('filter reset to All shows all cards', async () => {
    renderPage();
    await screen.findByText('EUR/USD');

    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'Review' }));
    expect(screen.queryByText('EUR/USD')).not.toBeInTheDocument();

    fireEvent.mouseDown(screen.getByRole('combobox'));
    fireEvent.click(await screen.findByRole('option', { name: 'All' }));
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('GBP/USD')).toBeInTheDocument();
    expect(screen.getByText('USD/JPY')).toBeInTheDocument();
  });
});
