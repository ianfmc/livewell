import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ContractCard from './contract-card';

const props = {
  instrument: 'EUR/USD',
  strike: '1.0850',
  expiry: '10:00 AM',
  status: 'Open',
  signalId: 'EURUSD__2026-05-04',
  direction: 'buy',
  date: '2026-05-04',
  recommendation: 'Take' as const,
  confidence: 'High' as const,
  scoreAvailable: true,
  edge: 0.42,
  supportingSignals: { ema20: 1.085, ema50: 1.08, rsi14: 58, macdHist: 0.0002, atr14: 0.005 },
  reasonCodes: [{ label: 'All stages passed', positive: true }],
};

function renderCard(overrides = {}) {
  return render(
    <MemoryRouter>
      <ContractCard {...props} {...overrides} />
    </MemoryRouter>
  );
}

describe('ContractCard', () => {
  it('renders instrument, strike, expiry, and status', () => {
    renderCard();
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText(/Strike: 1.0850/)).toBeInTheDocument();
    expect(screen.getByText(/10:00 AM/)).toBeInTheDocument();
    expect(screen.getByText('Open')).toBeInTheDocument();
  });

  it('card links to the contract detail URL', () => {
    renderCard();
    const link = screen.getByRole('link');
    expect(link).toHaveAttribute('href', '/signals/EUR-USD/1.0850');
  });

  it('shows direction, timestamp, and supporting signals (AC-1)', () => {
    renderCard();
    expect(screen.getByText('BUY')).toBeInTheDocument();
    expect(screen.getByText(/As of 2026-05-04/)).toBeInTheDocument();
    expect(screen.getByText(/RSI 58.0/)).toBeInTheDocument();
  });

  it('shows reason codes and model confidence when scored (AC-2)', () => {
    renderCard();
    expect(screen.getByText('High confidence')).toBeInTheDocument();
    expect(screen.getByText(/All stages passed/)).toBeInTheDocument();
  });

  it('labels confidence as rule-based when no model score (AC-2 / frozen baseline)', () => {
    renderCard({ scoreAvailable: false, confidence: 'Low' });
    expect(screen.getByText('Low · rule-based')).toBeInTheDocument();
  });
});
