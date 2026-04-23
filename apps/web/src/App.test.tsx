import { render, screen, fireEvent, within, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { ThemeProvider } from './components/theme-provider';
import App from './App';

function renderApp() {
  return render(
    <MemoryRouter>
      <ThemeProvider>
        <App />
      </ThemeProvider>
    </MemoryRouter>
  );
}

describe('App', () => {
  it('renders LIVEWELL title', () => {
    renderApp();
    expect(screen.getByText('LIVEWELL')).toBeInTheDocument();
  });

  it('shows hamburger menu button', () => {
    renderApp();
    expect(screen.getByRole('button', { name: /menu/i })).toBeInTheDocument();
  });

  it('clicking hamburger opens navigation drawer with nav links', async () => {
    renderApp();
    fireEvent.click(screen.getByRole('button', { name: /menu/i }));
    const drawer = await screen.findByLabelText('navigation drawer');
    expect(within(drawer).getByText('Dashboard')).toBeInTheDocument();
    expect(within(drawer).getByText('Daily Signals')).toBeInTheDocument();
  });

  it('clicking a nav link closes the drawer', async () => {
    renderApp();
    fireEvent.click(screen.getByRole('button', { name: /menu/i }));
    const drawer = await screen.findByLabelText('navigation drawer');
    fireEvent.click(within(drawer).getByText('Daily Signals'));
    await waitFor(() => {
      expect(screen.queryByLabelText('navigation drawer')).not.toBeInTheDocument();
    });
  });
});
