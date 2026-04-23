import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ContractCard from './contract-card';

const props = {
  instrument: 'EUR/USD',
  strike: '1.0850',
  expiry: '10:00 AM',
  status: 'Open',
};

function renderCard() {
  return render(
    <MemoryRouter>
      <ContractCard {...props} />
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
});
