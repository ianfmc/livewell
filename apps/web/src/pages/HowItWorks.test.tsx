import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import HowItWorks from './HowItWorks';

function renderPage() {
  return render(<MemoryRouter><HowItWorks /></MemoryRouter>);
}

describe('HowItWorks', () => {
  it('renders page heading', () => {
    renderPage();
    expect(screen.getByRole('heading', { name: /how it works/i })).toBeInTheDocument();
  });

  it('renders all four section headings', () => {
    renderPage();
    expect(screen.getByText('What LIVEWELL Predicts')).toBeInTheDocument();
    expect(screen.getByText('How Edge Is Calculated')).toBeInTheDocument();
    expect(screen.getByText('What the Confidence Tiers Mean')).toBeInTheDocument();
    expect(screen.getByText('When Not to Trade')).toBeInTheDocument();
  });

  it('accordion panel expands on click', () => {
    renderPage();
    const panel = screen.getByText('What LIVEWELL Predicts');
    fireEvent.click(panel);
    expect(screen.getByText(/binary contract/i)).toBeVisible();
  });
});
