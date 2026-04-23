import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { mockDashboard } from '../data/mockDashboard';
import Dashboard from './Dashboard';

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>
  );
}

describe('Dashboard', () => {
  it('shows spinner while loading', () => {
    renderDashboard();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders Market Conditions section', async () => {
    renderDashboard();
    expect(await screen.findByText('Market Conditions')).toBeInTheDocument();
  });

  it('renders Opportunity Summary section', async () => {
    renderDashboard();
    await screen.findByText('Market Conditions');
    expect(screen.getByText('Total Candidates')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
    expect(screen.getByText('Passing Rules')).toBeInTheDocument();
    expect(screen.getByText('2')).toBeInTheDocument();
    expect(screen.getByText('Flagged for Review')).toBeInTheDocument();
    expect(screen.getByText('1')).toBeInTheDocument();
  });

  it('renders Top Candidates section', async () => {
    renderDashboard();
    expect(await screen.findByText('Top Contract Candidates')).toBeInTheDocument();
    expect(screen.getAllByText('EUR/USD').length).toBeGreaterThan(0);
    expect(screen.getAllByText('USD/JPY').length).toBeGreaterThan(0);
  });

  it('renders Model Health section', async () => {
    renderDashboard();
    expect(await screen.findByText(/2026-04-21/)).toBeInTheDocument();
    expect(screen.getByText('Healthy')).toBeInTheDocument();
  });

  it('shows no-trade warning when passing is zero', async () => {
    server.use(
      http.get('/api/dashboard', () =>
        HttpResponse.json({
          ...mockDashboard,
          opportunities: { ...mockDashboard.opportunities, passing: 0 },
        })
      )
    );
    renderDashboard();
    expect(await screen.findByText(/No valid setups/)).toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/dashboard', () => HttpResponse.json({ message: 'error' }, { status: 500 }))
    );
    renderDashboard();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
