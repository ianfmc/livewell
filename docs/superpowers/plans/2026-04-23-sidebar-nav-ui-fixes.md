# Sidebar Navigation & UI Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the top nav buttons with a collapsible left sidebar drawer, and left-justify the Strike/Expiry lines in contract cards.

**Architecture:** Two independent changes — a one-line alignment fix in `contract-card.tsx`, and a full rework of `App.tsx` that replaces nav `Button` links with a MUI `Drawer variant="temporary"` toggled by a hamburger `IconButton`. The drawer overlays page content and disappears completely when closed. No page components change.

**Tech Stack:** React, MUI (AppBar, Drawer, IconButton, List, ListItemButton, ListItemText, Divider, MenuIcon), React Router DOM

**Working directory:** `/Users/i802235/Library/CloudStorage/OneDrive-SAPSE/Development/livewell-ui/.worktrees/sidebar-nav`

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `src/components/contract-card.tsx` | Modify line 29 | Left-justify Strike/Expiry Stack |
| `src/App.tsx` | Modify | Replace nav buttons with hamburger + Drawer |
| `src/App.test.tsx` | Create | Tests for sidebar open/close/navigate behaviour |

---

## Task 1: Left-justify contract card details

**Files:**
- Modify: `src/components/contract-card.tsx:29`
- Test: `src/components/contract-card.test.tsx` (existing — no changes needed)

> No TDD cycle needed — this is a visual alignment change. The existing tests verify rendered text, not alignment. Run the suite to confirm nothing breaks.

- [ ] **Step 1: Make the change**

In `src/components/contract-card.tsx`, find the second `Stack` (line 29) and change `alignItems`:

```tsx
// Before
<Stack spacing={0.5} alignItems="flex-end">

// After
<Stack spacing={0.5} alignItems="flex-start">
```

Full updated `contract-card.tsx` for reference:

```tsx
import Card from '@mui/material/Card';
import CardActionArea from '@mui/material/CardActionArea';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { Link as RouterLink } from 'react-router-dom';

import type { ContractCard as ContractCardData } from '../data/mockData';

type CardProps = ContractCardData;

const ContractCard = ({ instrument, strike, expiry, status }: CardProps) => {
  const to = `/signals/${instrument.replace(/\//g, '-')}/${strike}`;

  return (
    <Card elevation={3} sx={{ borderRadius: 3 }}>
      <CardActionArea<typeof RouterLink> component={RouterLink} to={to}>
        <CardContent>
          <Stack
            direction="row"
            justifyContent="space-between"
            alignItems="center"
            sx={{ mb: 2 }}
          >
            <Typography variant="h5">{instrument}</Typography>
            <Chip label={status} size="small" />
          </Stack>
          <Stack spacing={0.5} alignItems="flex-start">
            <Typography variant="body1">Strike: {strike}</Typography>
            <Typography variant="body2" color="text.secondary">
              Expires: {expiry}
            </Typography>
          </Stack>
        </CardContent>
      </CardActionArea>
    </Card>
  );
};

export default ContractCard;
```

- [ ] **Step 2: Run full test suite — confirm no regressions**

```bash
source ~/.nvm/nvm.sh && nvm use 20 && npx vitest run
```

Expected: all tests pass (same count as baseline — 28 tests).

- [ ] **Step 3: Commit**

```bash
git add src/components/contract-card.tsx
git commit -m "fix: left-justify strike and expiry in contract card"
```

---

## Task 2: Sidebar navigation

**Files:**
- Create: `src/App.test.tsx`
- Modify: `src/App.tsx`

- [ ] **Step 1: Write the failing tests**

Create `src/App.test.tsx`:

```tsx
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
```

- [ ] **Step 2: Run tests — verify they fail**

```bash
source ~/.nvm/nvm.sh && nvm use 20 && npx vitest run src/App.test.tsx
```

Expected failures:
- `shows hamburger menu button` — no button with aria-label "menu" in current App
- `clicking hamburger opens navigation drawer` — no hamburger to click, no drawer
- `clicking a nav link closes the drawer` — same

The `renders LIVEWELL title` test may pass (LIVEWELL already exists in App). The other three must fail.

- [ ] **Step 3: Implement new `App.tsx`**

Replace the entire contents of `src/App.tsx`:

```tsx
import { useState } from 'react';
import AppBar from '@mui/material/AppBar';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CssBaseline from '@mui/material/CssBaseline';
import Divider from '@mui/material/Divider';
import Drawer from '@mui/material/Drawer';
import IconButton from '@mui/material/IconButton';
import List from '@mui/material/List';
import ListItemButton from '@mui/material/ListItemButton';
import ListItemText from '@mui/material/ListItemText';
import Toolbar from '@mui/material/Toolbar';
import Typography from '@mui/material/Typography';
import MenuIcon from '@mui/icons-material/Menu';
import { Link, Route, Routes } from 'react-router-dom';

import ContractDetail from './pages/ContractDetail';
import Dashboard from './pages/Dashboard';
import DailySignals from './pages/DailySignals';
import { useTheme } from './components/theme-provider';

const NAV_ITEMS = [
  { label: 'Dashboard', path: '/' },
  { label: 'Daily Signals', path: '/signals' },
];

const App = () => {
  const { theme, setTheme } = useTheme();
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <>
      <CssBaseline />
      <Box
        sx={{
          flexGrow: 1,
          minHeight: '100vh',
          bgcolor: theme === 'light' ? 'grey.100' : 'grey.900',
          color: theme === 'light' ? 'text.primary' : '#fff',
        }}
      >
        <AppBar
          position="static"
          color="transparent"
          sx={{ bgcolor: theme === 'light' ? 'primary.main' : 'grey.900' }}
        >
          <Toolbar>
            <IconButton
              edge="start"
              aria-label="menu"
              onClick={() => setDrawerOpen(true)}
              sx={{ mr: 2, color: '#FFFFFF' }}
            >
              <MenuIcon />
            </IconButton>
            <Typography variant="h6" component="div" sx={{ color: '#FFFFFF', flexGrow: 1 }}>
              LIVEWELL
            </Typography>
            <Button
              variant="contained"
              onClick={() => setTheme(theme === 'light' ? 'dark' : 'light')}
            >
              Toggle Theme ({theme})
            </Button>
          </Toolbar>
        </AppBar>

        <Drawer
          variant="temporary"
          open={drawerOpen}
          onClose={() => setDrawerOpen(false)}
        >
          <Box sx={{ width: 240, pt: 1 }} aria-label="navigation drawer">
            <Divider />
            <List>
              {NAV_ITEMS.map(({ label, path }) => (
                <ListItemButton<typeof Link>
                  key={path}
                  component={Link}
                  to={path}
                  onClick={() => setDrawerOpen(false)}
                >
                  <ListItemText primary={label} />
                </ListItemButton>
              ))}
            </List>
          </Box>
        </Drawer>

        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/signals" element={<DailySignals />} />
          <Route path="/signals/:instrument/:strike" element={<ContractDetail />} />
        </Routes>
      </Box>
    </>
  );
};

export default App;
```

- [ ] **Step 4: Run the App tests — verify they pass**

```bash
source ~/.nvm/nvm.sh && nvm use 20 && npx vitest run src/App.test.tsx
```

Expected:
```
App > renders LIVEWELL title                                        PASS
App > shows hamburger menu button                                   PASS
App > clicking hamburger opens navigation drawer with nav links     PASS
App > clicking a nav link closes the drawer                         PASS
4 passed
```

- [ ] **Step 5: Run the full test suite — confirm no regressions**

```bash
source ~/.nvm/nvm.sh && nvm use 20 && npx vitest run
```

Expected: all tests pass. The previous 28 tests plus 4 new App tests = 32 passed.

- [ ] **Step 6: Verify in browser**

```bash
source ~/.nvm/nvm.sh && nvm use 20 && npm run dev
```

Open `http://localhost:5173` and verify:
- Hamburger icon is visible in top-left of AppBar
- Clicking it opens a sidebar from the left with "Dashboard" and "Daily Signals"
- Clicking either nav item closes the sidebar and navigates
- Clicking outside the drawer (the backdrop) also closes it
- Theme toggle still works
- Contract card Strike/Expiry lines are left-aligned on the Daily Signals page
- The "Daily Signals" arrow that was visible in the old top nav is gone

Stop the dev server with `Ctrl+C`.

- [ ] **Step 7: Commit**

```bash
git add src/App.tsx src/App.test.tsx
git commit -m "feat: replace top nav with collapsible sidebar drawer"
```
