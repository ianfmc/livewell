import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import ModelHealth from './ModelHealth';

function renderPage() {
  return render(<MemoryRouter><ModelHealth /></MemoryRouter>);
}

describe('ModelHealth', () => {
  it('shows spinner while loading', () => {
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders status banner after load', async () => {
    renderPage();
    expect(await screen.findByText('Warning')).toBeInTheDocument();
  });

  it('renders metric cards', async () => {
    renderPage();
    await screen.findByText('Warning');
    expect(screen.getByText('Training Date')).toBeInTheDocument();
    expect(screen.getByText('Data Freshness')).toBeInTheDocument();
    expect(screen.getByText('Calibration Error')).toBeInTheDocument();
    expect(screen.getByText('Validation Accuracy')).toBeInTheDocument();
  });

  it('renders feature availability table', async () => {
    renderPage();
    await screen.findByText('Warning');
    expect(screen.getByText('EMA-20')).toBeInTheDocument();
    expect(screen.getByText('Event Risk Flag')).toBeInTheDocument();
  });

  it('renders drift warning', async () => {
    renderPage();
    await screen.findByText('Warning');
    expect(screen.getByText(/Volatility Reg/)).toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/model/health', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
