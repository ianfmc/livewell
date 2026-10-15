import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SignalExplainPanel } from './SignalExplainPanel';

// Mock useSignalExplain so we control what it returns
vi.mock('../hooks/useSignalExplain');
import { useSignalExplain } from '../hooks/useSignalExplain';
const mockUseSignalExplain = vi.mocked(useSignalExplain);

beforeEach(() => {
  mockUseSignalExplain.mockReturnValue({ data: null, loading: false, error: null });
});

afterEach(() => vi.clearAllMocks());

describe('SignalExplainPanel', () => {
  it('renders nothing when signalId is null', () => {
    const { container } = render(
      <SignalExplainPanel signalId={null} onClose={() => {}} />
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows loading spinner when loading=true', () => {
    mockUseSignalExplain.mockReturnValue({ data: null, loading: true, error: null });
    render(<SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />);
    expect(screen.getByRole('progressbar')).toBeDefined();
  });

  it('shows error message when error is set', () => {
    mockUseSignalExplain.mockReturnValue({ data: null, loading: false, error: 'Connection error' });
    render(<SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />);
    expect(screen.getByText(/connection error/i)).toBeDefined();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={onClose} />);
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders explanation sections when data is available', () => {
    mockUseSignalExplain.mockReturnValue({
      data: {
        header: 'EUR/USD — model probability 0.62',
        trend: 'EMA-20 above EMA-50 (bullish).',
        momentum: 'RSI > 50, MACD histogram positive.',
        session: 'London session, high quality.',
        timing: 'Within the morning slot.',
      },
      loading: false,
      error: null,
    });

    render(<SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />);
    expect(screen.getByTestId('signal-explain-panel')).toBeDefined();
    expect(screen.getByText(/model probability 0.62/i)).toBeDefined();
    expect(screen.getByText(/EMA-20 above EMA-50/i)).toBeDefined();
    expect(screen.getByText(/RSI > 50/i)).toBeDefined();
    expect(screen.getByText('Trend')).toBeDefined();
    expect(screen.getByText('Momentum')).toBeDefined();
  });
});
