import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import OptionsAdvisor from './OptionsAdvisor';

function renderPage() {
  return render(<MemoryRouter><OptionsAdvisor /></MemoryRouter>);
}

describe('OptionsAdvisor', () => {
  it('renders Step 1 heading on load', () => {
    renderPage();
    expect(screen.getByText('Step 1: Select a Market')).toBeInTheDocument();
  });

  it('advances to Step 2 after selecting a market', () => {
    renderPage();
    fireEvent.click(screen.getByLabelText('EUR/USD'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Step 2: Select Expiry Window')).toBeInTheDocument();
  });

  it('advances to Step 3 after selecting expiry', () => {
    renderPage();
    fireEvent.click(screen.getByLabelText('EUR/USD'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    fireEvent.click(screen.getByLabelText('2-hour'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    expect(screen.getByText('Step 3: Describe Current Regime')).toBeInTheDocument();
  });

  it('shows results panel after completing all steps', () => {
    renderPage();
    fireEvent.click(screen.getByLabelText('EUR/USD'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    fireEvent.click(screen.getByLabelText('2-hour'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    fireEvent.click(screen.getByLabelText('Bullish'));
    fireEvent.click(screen.getByLabelText('Normal'));
    fireEvent.click(screen.getByLabelText('None'));
    fireEvent.click(screen.getByRole('button', { name: /view candidates/i }));
    expect(screen.getByText('Matching Candidates')).toBeInTheDocument();
  });

  it('Start over resets to Step 1', () => {
    renderPage();
    fireEvent.click(screen.getByLabelText('EUR/USD'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    fireEvent.click(screen.getByLabelText('2-hour'));
    fireEvent.click(screen.getByRole('button', { name: /next/i }));
    fireEvent.click(screen.getByLabelText('Bullish'));
    fireEvent.click(screen.getByLabelText('Normal'));
    fireEvent.click(screen.getByLabelText('None'));
    fireEvent.click(screen.getByRole('button', { name: /view candidates/i }));
    fireEvent.click(screen.getByRole('button', { name: /start over/i }));
    expect(screen.getByText('Step 1: Select a Market')).toBeInTheDocument();
  });
});
