# Contract Detail Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Contract Detail page at `/signals/:instrument/:strike` that shows full contract information (economics, model probability, reason codes, Take/Watch/Pass recommendation) linked from ContractCard clicks.

**Architecture:** `ContractCard` becomes fully clickable via `CardActionArea + RouterLink` (dialog removed). A new `useContractDetail` hook fetches from a new MSW handler returning the richer `ContractDetail` type. The `ContractDetail` page renders Layout C: bold header with recommendation chip, context chips row, 4-up metric strip, reason codes, rationale.

**Tech Stack:** React, React Router v6, MUI v5, MSW v2, Vitest, React Testing Library

---

## File Map

| File | Action | Purpose |
|---|---|---|
| `src/data/mockData.ts` | Modify | Add `ContractDetail` type and `mockContractDetails` array |
| `src/mocks/handlers.ts` | Modify | Add `GET /api/signals/:instrument/:strike` handler |
| `src/hooks/useContractDetail.ts` | Create | Hook: fetch single contract, return `{ data, loading, error }` |
| `src/hooks/useContractDetail.test.ts` | Create | 3 hook tests |
| `src/components/contract-card.tsx` | Modify | Replace Info dialog with `CardActionArea + RouterLink` |
| `src/components/contract-card.test.tsx` | Modify | Remove 2 dialog tests; add navigation test + `MemoryRouter` wrapper |
| `src/pages/ContractDetail.tsx` | Create | Layout C page component |
| `src/pages/ContractDetail.test.tsx` | Create | 5 page tests |
| `src/App.tsx` | Modify | Add `/signals/:instrument/:strike` route |

---

### Task 1: Extend mock data with ContractDetail type

**Files:**
- Modify: `src/data/mockData.ts`

The existing `ContractCard` type and `mockData` array are unchanged. Add `ContractDetail` (the richer type) and `mockContractDetails` (3 entries). The EUR/USD entry uses the exact values the page tests assert against.

- [ ] **Step 1: Replace `src/data/mockData.ts`**

```ts
export type ContractCard = {
  instrument: string;
  strike: string;
  expiry: string;
  status: string;
};

export type ContractDetail = {
  instrument: string;
  strike: string;
  expiry: string;
  status: string;
  recommendation: 'Take' | 'Watch' | 'Pass';
  rationale: string;
  economics: {
    cost: number;
    payout: number;
    breakeven: number;
  };
  modelProbability: number;
  edge: number;
  confidence: 'High' | 'Medium' | 'Low';
  regime: string;
  noTradeFlag: boolean;
  reasonCodes: Array<{
    label: string;
    positive: boolean;
  }>;
};

export const mockData: ContractCard[] = [
  { instrument: 'EUR/USD', strike: '1.0850', expiry: '10:00 AM', status: 'Open' },
  { instrument: 'GBP/USD', strike: '1.2650', expiry: '11:00 AM', status: 'Open' },
  { instrument: 'USD/JPY', strike: '150.00', expiry: '09:30 AM', status: 'Review' },
];

export const mockContractDetails: ContractDetail[] = [
  {
    instrument: 'EUR/USD',
    strike: '1.0850',
    expiry: '10:00 AM',
    status: 'Open',
    recommendation: 'Take',
    rationale: 'Strong directional setup with acceptable event risk.',
    economics: { cost: 42, payout: 100, breakeven: 0.42 },
    modelProbability: 0.68,
    edge: 0.26,
    confidence: 'High',
    regime: 'Bullish',
    noTradeFlag: false,
    reasonCodes: [
      { label: 'Bullish regime confirmed', positive: true },
      { label: 'RSI momentum favourable', positive: true },
      { label: 'Event risk flag active', positive: false },
    ],
  },
  {
    instrument: 'GBP/USD',
    strike: '1.2650',
    expiry: '11:00 AM',
    status: 'Open',
    recommendation: 'Watch',
    rationale: 'Setup is developing but lacks regime confirmation.',
    economics: { cost: 38, payout: 100, breakeven: 0.38 },
    modelProbability: 0.52,
    edge: 0.14,
    confidence: 'Medium',
    regime: 'Neutral',
    noTradeFlag: false,
    reasonCodes: [
      { label: 'Price near key level', positive: true },
      { label: 'Regime not confirmed', positive: false },
      { label: 'Low volatility environment', positive: false },
    ],
  },
  {
    instrument: 'USD/JPY',
    strike: '150.00',
    expiry: '09:30 AM',
    status: 'Review',
    recommendation: 'Pass',
    rationale: 'No-trade flag active — intervention risk too high.',
    economics: { cost: 55, payout: 100, breakeven: 0.55 },
    modelProbability: 0.48,
    edge: -0.07,
    confidence: 'Low',
    regime: 'Bearish',
    noTradeFlag: true,
    reasonCodes: [
      { label: 'Intervention risk elevated', positive: false },
      { label: 'Bearish momentum weakening', positive: false },
      { label: 'High volatility — spread risk', positive: false },
    ],
  },
];
```

- [ ] **Step 2: Verify TypeScript compiles**

```bash
npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Verify existing tests still pass**

```bash
npx vitest run
```

Expected: 21 tests, 0 failures.

- [ ] **Step 4: Commit**

```bash
git add src/data/mockData.ts
git commit -m "feat: add ContractDetail type and mock data"
```

---

### Task 2: Add MSW handler for contract detail endpoint

**Files:**
- Modify: `src/mocks/handlers.ts`

URL encoding convention: `/` in instrument names is replaced with `-` in the URL. The handler receives the hyphen-encoded param and decodes it back before matching mock data.

- [ ] **Step 1: Replace `src/mocks/handlers.ts`**

```ts
import { http, HttpResponse } from 'msw';
import { mockData, mockContractDetails } from '../data/mockData';
import { mockDashboard } from '../data/mockDashboard';

export const handlers = [
  http.get('/api/signals', () => {
    return HttpResponse.json(mockData);
  }),
  http.get('/api/dashboard', () => {
    return HttpResponse.json(mockDashboard);
  }),
  http.get('/api/signals/:instrument/:strike', ({ params }) => {
    const instrument = (params.instrument as string).replace(/-/g, '/');
    const strike = params.strike as string;
    const detail = mockContractDetails.find(
      (d) => d.instrument === instrument && d.strike === strike
    );
    if (!detail) {
      return HttpResponse.json({ message: 'Not found' }, { status: 404 });
    }
    return HttpResponse.json(detail);
  }),
];
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
npx vitest run
```

Expected: 21 tests, 0 failures.

- [ ] **Step 3: Commit**

```bash
git add src/mocks/handlers.ts
git commit -m "feat: add GET /api/signals/:instrument/:strike MSW handler"
```

---

### Task 3: Create useContractDetail hook + tests (TDD)

**Files:**
- Create: `src/hooks/useContractDetail.test.ts`
- Create: `src/hooks/useContractDetail.ts`

The hook mirrors `useSignals` exactly — same `AbortController` pattern, same `{ data, loading, error }` shape — except it fetches a single object and the instrument is URL-encoded before the fetch (`EUR/USD` → `EUR-USD`).

The `unmount()` call in the loading test is required: without it, the in-flight MSW fetch resolves after the test ends, triggering act() warnings because state updates happen outside a React act() boundary. `unmount()` triggers the cleanup function which calls `controller.abort()`, cancelling the fetch before it resolves.

- [ ] **Step 1: Write the failing tests**

Create `src/hooks/useContractDetail.test.ts`:

```ts
import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useContractDetail } from './useContractDetail';

describe('useContractDetail', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useContractDetail('EUR/USD', '1.0850'));
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('returns data after successful fetch', async () => {
    const { result } = renderHook(() => useContractDetail('EUR/USD', '1.0850'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.instrument).toBe('EUR/USD');
    expect(result.current.data?.recommendation).toBe('Take');
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/signals/:instrument/:strike', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useContractDetail('EUR/USD', '1.0850'));
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBeNull();
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
npx vitest run src/hooks/useContractDetail.test.ts
```

Expected: FAIL — `Cannot find module './useContractDetail'`.

- [ ] **Step 3: Create `src/hooks/useContractDetail.ts`**

```ts
import { useEffect, useState } from 'react';
import type { ContractDetail } from '../data/mockData';

type UseContractDetailResult = {
  data: ContractDetail | null;
  loading: boolean;
  error: string | null;
};

export function useContractDetail(instrument: string, strike: string): UseContractDetailResult {
  const [data, setData] = useState<ContractDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    const encodedInstrument = instrument.replace(/\//g, '-');
    fetch(`/api/signals/${encodedInstrument}/${strike}`, { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<ContractDetail>;
      })
      .then((json) => {
        setData(json);
      })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => {
        setLoading(false);
      });
    return () => controller.abort();
  }, [instrument, strike]);

  return { data, loading, error };
}
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
npx vitest run src/hooks/useContractDetail.test.ts
```

Expected: 3 passed.

- [ ] **Step 5: Run full suite**

```bash
npx vitest run
```

Expected: 24 tests, 0 failures.

- [ ] **Step 6: Commit**

```bash
git add src/hooks/useContractDetail.ts src/hooks/useContractDetail.test.ts
git commit -m "feat: add useContractDetail hook and tests"
```

---

### Task 4: Refactor ContractCard — replace dialog with clickable card

**Files:**
- Modify: `src/components/contract-card.test.tsx`
- Modify: `src/components/contract-card.tsx`

The Info button and dialog are removed entirely. The whole card becomes a router link. `CardActionArea<typeof RouterLink>` provides the MUI clickable surface; `RouterLink` provides the anchor. The URL uses hyphens for the instrument: `EUR/USD` → `/signals/EUR-USD/1.0850`.

Because the card now renders a `RouterLink` (which needs a router context), all tests must wrap renders in `MemoryRouter`.

Write the updated tests first — the navigation test will fail because no link exists yet. Then implement the refactor.

- [ ] **Step 1: Replace `src/components/contract-card.test.tsx`**

```tsx
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
```

- [ ] **Step 2: Run tests to confirm the navigation test fails**

```bash
npx vitest run src/components/contract-card.test.tsx
```

Expected: 1 pass (renders test), 1 fail (link test — no link exists yet). The old dialog tests are gone.

- [ ] **Step 3: Replace `src/components/contract-card.tsx`**

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
          <Stack spacing={0.5} alignItems="flex-end">
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

- [ ] **Step 4: Run tests to confirm both pass**

```bash
npx vitest run src/components/contract-card.test.tsx
```

Expected: 2 passed.

- [ ] **Step 5: Run full suite**

```bash
npx vitest run
```

Expected: 23 tests, 0 failures. (Net change: removed 2 dialog tests, added 1 navigation test = −1 from previous total of 24.)

- [ ] **Step 6: Commit**

```bash
git add src/components/contract-card.tsx src/components/contract-card.test.tsx
git commit -m "feat: make ContractCard clickable — navigate to detail page"
```

---

### Task 5: Create ContractDetail page + tests (TDD)

**Files:**
- Create: `src/pages/ContractDetail.test.tsx`
- Create: `src/pages/ContractDetail.tsx`

The page reads `instrument` and `strike` from `useParams`. `instrument` arrives hyphen-encoded (`EUR-USD`) and is decoded back to slash form (`EUR/USD`) before passing to the hook. The hook encodes it again before fetching — this round-trip is intentional and consistent.

Layout C top to bottom: back link → instrument header + recommendation chip → context chips → 4-up metric strip → reason codes → rationale.

Formatting: `modelProbability: 0.68` → `"68%"` (multiply by 100, round, append `%`). `edge: 0.26` → `"+26%"` (same, prefix `+` if non-negative). `edge: -0.07` → `"-7%"`.

Recommendation chip colours: `Take` → MUI `success`, `Watch` → MUI `warning`, `Pass` → MUI `default`.

The back link uses `RouterLink` directly (renders an `<a>` tag, satisfies `getByRole('link')`).

The tests wrap in `MemoryRouter initialEntries` + `Routes` + `Route` so `useParams` receives real values.

- [ ] **Step 1: Write the failing tests**

Create `src/pages/ContractDetail.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import ContractDetail from './ContractDetail';

function renderDetail(url = '/signals/EUR-USD/1.0850') {
  return render(
    <MemoryRouter initialEntries={[url]}>
      <Routes>
        <Route path="/signals/:instrument/:strike" element={<ContractDetail />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('ContractDetail', () => {
  it('renders instrument and recommendation chip', async () => {
    renderDetail();
    expect(await screen.findByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('TAKE')).toBeInTheDocument();
  });

  it('renders 4-up metric strip', async () => {
    renderDetail();
    await screen.findByText('EUR/USD');
    expect(screen.getByText('$42')).toBeInTheDocument();
    expect(screen.getByText('$100')).toBeInTheDocument();
    expect(screen.getByText('68%')).toBeInTheDocument();
    expect(screen.getByText('+26%')).toBeInTheDocument();
  });

  it('renders reason codes', async () => {
    renderDetail();
    expect(await screen.findByText(/Bullish regime confirmed/)).toBeInTheDocument();
  });

  it('renders back link to Daily Signals', async () => {
    renderDetail();
    await screen.findByText('EUR/USD');
    expect(screen.getByRole('link', { name: /Daily Signals/i })).toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/signals/:instrument/:strike', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderDetail();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
npx vitest run src/pages/ContractDetail.test.tsx
```

Expected: FAIL — `Cannot find module './ContractDetail'`.

- [ ] **Step 3: Create `src/pages/ContractDetail.tsx`**

```tsx
import { Link as RouterLink, useParams } from 'react-router-dom';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';

import { useContractDetail } from '../hooks/useContractDetail';

const ContractDetail = () => {
  const { instrument: encodedInstrument = '', strike = '' } = useParams();
  const instrument = encodedInstrument.replace(/-/g, '/');
  const { data, loading, error } = useContractDetail(instrument, strike);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box sx={{ maxWidth: 600, mx: 'auto', mt: 3, px: 2 }}>
        <Alert severity="error">{error}</Alert>
      </Box>
    );
  }

  if (!data) return null;

  const recommendationColor =
    data.recommendation === 'Take' ? 'success' :
    data.recommendation === 'Watch' ? 'warning' : 'default';

  const confidenceColor =
    data.confidence === 'High' ? 'success' :
    data.confidence === 'Medium' ? 'warning' : 'default';

  const edgeFormatted =
    data.edge >= 0
      ? `+${Math.round(data.edge * 100)}%`
      : `${Math.round(data.edge * 100)}%`;

  const modelFormatted = `${Math.round(data.modelProbability * 100)}%`;

  return (
    <Box sx={{ maxWidth: 600, mx: 'auto', mt: 3, px: 2 }}>
      <RouterLink
        to="/signals"
        style={{ display: 'block', marginBottom: '16px', textDecoration: 'none' }}
      >
        ← Daily Signals
      </RouterLink>

      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="flex-start"
        sx={{ mb: 1 }}
      >
        <Box>
          <Typography variant="h4">{data.instrument}</Typography>
          <Typography variant="body2" color="text.secondary">
            Strike {data.strike} · Expires {data.expiry}
          </Typography>
        </Box>
        <Chip
          label={data.recommendation.toUpperCase()}
          color={recommendationColor as 'success' | 'warning' | 'default'}
          sx={{ fontWeight: 'bold' }}
        />
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap' }}>
        <Chip label={data.regime} size="small" color="info" />
        <Chip
          label={`${data.confidence} confidence`}
          size="small"
          color={confidenceColor as 'success' | 'warning' | 'default'}
        />
        {data.noTradeFlag && <Chip label="No Trade" size="small" color="error" />}
      </Stack>

      <Stack direction="row" spacing={1} sx={{ mb: 3 }}>
        {[
          { value: `$${data.economics.cost}`, label: 'Cost' },
          { value: `$${data.economics.payout}`, label: 'Payout' },
          { value: modelFormatted, label: 'Model' },
          { value: edgeFormatted, label: 'Edge' },
        ].map(({ value, label }) => (
          <Box
            key={label}
            sx={{
              flex: 1,
              bgcolor: 'action.hover',
              borderRadius: 1,
              p: 1.5,
              textAlign: 'center',
            }}
          >
            <Typography
              variant="h6"
              sx={{
                color:
                  label === 'Edge'
                    ? data.edge < 0
                      ? 'error.main'
                      : 'success.main'
                    : 'inherit',
              }}
            >
              {value}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
          </Box>
        ))}
      </Stack>

      <Box sx={{ mb: 2 }}>
        <Typography variant="overline" color="text.secondary">
          Why this setup
        </Typography>
        <Stack spacing={0.5} sx={{ mt: 0.5 }}>
          {data.reasonCodes.map((r) => (
            <Typography key={r.label} variant="body2">
              {r.positive ? '✓' : '✗'} {r.label}
            </Typography>
          ))}
        </Stack>
      </Box>

      <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
        {data.rationale}
      </Typography>
    </Box>
  );
};

export default ContractDetail;
```

- [ ] **Step 4: Run tests to confirm they pass**

```bash
npx vitest run src/pages/ContractDetail.test.tsx
```

Expected: 5 passed.

- [ ] **Step 5: Run full suite**

```bash
npx vitest run
```

Expected: 28 tests, 0 failures.

- [ ] **Step 6: Commit**

```bash
git add src/pages/ContractDetail.tsx src/pages/ContractDetail.test.tsx
git commit -m "feat: add ContractDetail page (Layout C)"
```

---

### Task 6: Add route and verify end-to-end

**Files:**
- Modify: `src/App.tsx`

- [ ] **Step 1: Replace `src/App.tsx` with the updated version**

```tsx
import AppBar from "@mui/material/AppBar";
import Button from "@mui/material/Button";
import Box from "@mui/material/Box";
import CssBaseline from "@mui/material/CssBaseline";
import Toolbar from "@mui/material/Toolbar";
import Typography from "@mui/material/Typography";
import { Link, Route, Routes } from "react-router-dom";

import ContractDetail from "./pages/ContractDetail";
import Dashboard from "./pages/Dashboard";
import DailySignals from "./pages/DailySignals";
import { useTheme } from "./components/theme-provider";

const App = () => {
  const { theme, setTheme } = useTheme();

  return (
    <>
      <CssBaseline />

      <Box
        sx={{
          flexGrow: 1,
          minHeight: "100vh",
          bgcolor: theme === "light" ? "grey.100" : "grey.900",
          color: theme === "light" ? "text.primary" : "#fff",
        }}
      >
        <AppBar
          position="static"
          color="transparent"
          sx={{
            bgcolor: theme === "light" ? "primary.main" : "grey.900",
          }}
        >
          <Toolbar>
            <Typography variant="h6" component="div" sx={{ color: "#FFFFFF", mr: 2 }}>
              LIVEWELL
            </Typography>

            <Button<typeof Link> component={Link} to="/" sx={{ color: "#FFFFFF" }}>
              Dashboard
            </Button>
            <Button<typeof Link> component={Link} to="/signals" sx={{ color: "#FFFFFF" }}>
              Daily Signals
            </Button>

            <Box sx={{ flexGrow: 1 }} />

            <Button
              variant="contained"
              onClick={() => setTheme(theme === "light" ? "dark" : "light")}
            >
              Toggle Theme ({theme})
            </Button>
          </Toolbar>
        </AppBar>

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

- [ ] **Step 2: Run full test suite**

```bash
npx vitest run
```

Expected: 28 tests, 0 failures.

- [ ] **Step 3: Verify build passes**

```bash
npm run build
```

Expected: `tsc -b` completes, vite bundle completes, no errors.

- [ ] **Step 4: Verify coverage stays above 80%**

```bash
npm run test:coverage
```

Expected: all coverage thresholds met.

- [ ] **Step 5: Start dev server and verify end-to-end**

```bash
npm run dev
```

Open http://localhost:5173/signals. Verify:
- EUR/USD card is clickable (cursor changes on hover)
- Clicking EUR/USD card navigates to `/signals/EUR-USD/1.0850`
- Page shows `EUR/USD` header with `TAKE` chip (green)
- 4 metric tiles display `$42`, `$100`, `68%`, `+26%`
- Reason codes show ✓ Bullish regime confirmed, ✓ RSI momentum favourable, ✗ Event risk flag active
- Back link `← Daily Signals` navigates back to `/signals`
- Clicking USD/JPY card navigates to its detail page and shows `PASS` chip and `No Trade` chip

- [ ] **Step 6: Commit**

```bash
git add src/App.tsx
git commit -m "feat: wire ContractDetail route into App"
```
