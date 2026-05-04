import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { A2uiProvider } from '../a2ui/A2uiProvider';
import { SignalExplainPanel } from './SignalExplainPanel';

// Mock A2uiSurface to avoid React version mismatch from a2ui package
vi.mock('@a2ui/react/v0_9', async () => {
  const actual = await vi.importActual('@a2ui/react/v0_9');
  return {
    ...actual,
    A2uiSurface: ({ surface }: any) => <div data-testid="a2ui-surface">{surface.id}</div>,
  };
});

// Mock useSignalExplain so we control what it returns
vi.mock('../hooks/useSignalExplain');
import { useSignalExplain } from '../hooks/useSignalExplain';
const mockUseSignalExplain = vi.mocked(useSignalExplain);

const wrapper = ({ children }: { children: React.ReactNode }) => (
  <A2uiProvider>{children}</A2uiProvider>
);

beforeEach(() => {
  mockUseSignalExplain.mockReturnValue({ surface: null, loading: false, error: null });
});

afterEach(() => vi.clearAllMocks());

describe('SignalExplainPanel', () => {
  it('renders nothing when signalId is null', () => {
    const { container } = render(
      <SignalExplainPanel signalId={null} onClose={() => {}} />,
      { wrapper }
    );
    expect(container.firstChild).toBeNull();
  });

  it('shows loading spinner when loading=true', () => {
    mockUseSignalExplain.mockReturnValue({ surface: null, loading: true, error: null });
    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />,
      { wrapper }
    );
    expect(screen.getByRole('progressbar')).toBeDefined();
  });

  it('shows error message when error is set', () => {
    mockUseSignalExplain.mockReturnValue({ surface: null, loading: false, error: 'Connection error' });
    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />,
      { wrapper }
    );
    expect(screen.getByText(/connection error/i)).toBeDefined();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={onClose} />,
      { wrapper }
    );
    fireEvent.click(screen.getByRole('button', { name: /close/i }));
    expect(onClose).toHaveBeenCalledOnce();
  });

  it('renders surface container when surface is available', () => {
    // Provide a minimal surface mock — A2uiSurface will handle rendering
    const mockSurface = { id: 'explain-EURUSD__2026-05-04' } as any;
    mockUseSignalExplain.mockReturnValue({ surface: mockSurface, loading: false, error: null });

    render(
      <SignalExplainPanel signalId="EURUSD__2026-05-04" onClose={() => {}} />,
      { wrapper }
    );
    // The panel wrapper should be present (identified by data-testid)
    expect(screen.getByTestId('signal-explain-panel')).toBeDefined();
  });
});
