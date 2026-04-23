# Phase 1C — Deferred Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 5 deferred Phase 1A pages (Backtest Results, Model Health, How It Works, Signal Tracker, Options Advisor) with realistic mock data against the existing hook/MSW pattern, and wire all 5 into the app navigation.

**Architecture:** Each data-fetching page gets its own mock data file (`src/data/`), hook (`src/hooks/`), and page component + test (`src/pages/`). MSW handlers for 3 new GET endpoints are added to `src/mocks/handlers.ts`. How It Works and Options Advisor have no fetch — static content and local state respectively.

**Tech Stack:** React 19, TypeScript, MUI v7, MSW v2, Vitest + React Testing Library, react-router-dom v7. All MUI imports are individual (e.g. `import Box from '@mui/material/Box'`), never barrel imports.

---

## File Map

**Created:**
- `apps/web/src/data/mockBacktest.ts` — `BacktestRow`, `BacktestSummary` types + mock data
- `apps/web/src/data/mockModelHealth.ts` — `FeatureStatus`, `DriftWarning`, `ModelHealth` types + mock data
- `apps/web/src/data/mockSignalTracker.ts` — `TrackedSignal` type + mock data
- `apps/web/src/hooks/useBacktest.ts` — fetches `GET /api/backtest/summary`
- `apps/web/src/hooks/useBacktest.test.ts`
- `apps/web/src/hooks/useModelHealth.ts` — fetches `GET /api/model/health`
- `apps/web/src/hooks/useModelHealth.test.ts`
- `apps/web/src/hooks/useSignalTracker.ts` — fetches `GET /api/signals/tracker`
- `apps/web/src/hooks/useSignalTracker.test.ts`
- `apps/web/src/pages/BacktestResults.tsx`
- `apps/web/src/pages/BacktestResults.test.tsx`
- `apps/web/src/pages/ModelHealth.tsx`
- `apps/web/src/pages/ModelHealth.test.tsx`
- `apps/web/src/pages/HowItWorks.tsx`
- `apps/web/src/pages/HowItWorks.test.tsx`
- `apps/web/src/pages/SignalTracker.tsx`
- `apps/web/src/pages/SignalTracker.test.tsx`
- `apps/web/src/pages/OptionsAdvisor.tsx`
- `apps/web/src/pages/OptionsAdvisor.test.tsx`

**Modified:**
- `apps/web/src/mocks/handlers.ts` — add 3 new GET handlers
- `apps/web/src/App.tsx` — add 5 routes and 5 nav items

---

## Task 1: Mock data — Backtest

**Files:**
- Create: `apps/web/src/data/mockBacktest.ts`

- [ ] **Step 1: Create the file**

```typescript
// apps/web/src/data/mockBacktest.ts

export type BacktestRow = {
  market: string;
  regime: string;
  expiryWindow: string;
  trades: number;
  winRate: number;
  avgEdge: number;
  netReturn: number;
};

export type BacktestSummary = {
  totalTrades: number;
  winRate: number;
  avgEdge: number;
  maxDrawdown: number;
  equityCurve: Array<{ date: string; value: number }>;
  rows: BacktestRow[];
};

export const mockBacktest: BacktestSummary = {
  totalTrades: 84,
  winRate: 0.61,
  avgEdge: 0.14,
  maxDrawdown: -0.09,
  equityCurve: [
    { date: '2026-03-01', value: 1000 },
    { date: '2026-03-03', value: 1018 },
    { date: '2026-03-05', value: 1009 },
    { date: '2026-03-07', value: 1031 },
    { date: '2026-03-10', value: 1024 },
    { date: '2026-03-12', value: 1047 },
    { date: '2026-03-14', value: 1039 },
    { date: '2026-03-17', value: 1062 },
    { date: '2026-03-19', value: 1055 },
    { date: '2026-03-21', value: 1078 },
    { date: '2026-03-24', value: 1070 },
    { date: '2026-03-26', value: 1093 },
    { date: '2026-03-28', value: 1085 },
    { date: '2026-03-31', value: 1108 },
    { date: '2026-04-02', value: 1099 },
    { date: '2026-04-04', value: 1122 },
    { date: '2026-04-07', value: 1113 },
    { date: '2026-04-09', value: 1136 },
    { date: '2026-04-11', value: 1128 },
    { date: '2026-04-14', value: 1151 },
    { date: '2026-04-16', value: 1143 },
    { date: '2026-04-18', value: 1134 },
    { date: '2026-04-19', value: 1157 },
    { date: '2026-04-20', value: 1149 },
    { date: '2026-04-21', value: 1172 },
    { date: '2026-04-22', value: 1163 },
    { date: '2026-04-23', value: 1186 },
    { date: '2026-04-24', value: 1177 },
    { date: '2026-04-25', value: 1200 },
    { date: '2026-04-26', value: 1191 },
  ],
  rows: [
    { market: 'EUR/USD', regime: 'Bullish', expiryWindow: '2-hour', trades: 18, winRate: 0.67, avgEdge: 0.18, netReturn: 0.21 },
    { market: 'EUR/USD', regime: 'Bearish', expiryWindow: '2-hour', trades: 12, winRate: 0.58, avgEdge: 0.11, netReturn: 0.09 },
    { market: 'GBP/USD', regime: 'Bullish', expiryWindow: 'Daily',  trades: 15, winRate: 0.60, avgEdge: 0.14, netReturn: 0.12 },
    { market: 'GBP/USD', regime: 'Bearish', expiryWindow: 'Daily',  trades: 11, winRate: 0.55, avgEdge: 0.09, netReturn: 0.06 },
    { market: 'USD/JPY', regime: 'Bullish', expiryWindow: '2-hour', trades: 16, winRate: 0.63, avgEdge: 0.15, netReturn: 0.14 },
    { market: 'USD/JPY', regime: 'Bearish', expiryWindow: 'Daily',  trades: 12, winRate: 0.50, avgEdge: 0.08, netReturn: 0.02 },
  ],
};
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/data/mockBacktest.ts
git commit -m "feat: add BacktestSummary type and mock data"
```

---

## Task 2: Mock data — Model Health

**Files:**
- Create: `apps/web/src/data/mockModelHealth.ts`

- [ ] **Step 1: Create the file**

```typescript
// apps/web/src/data/mockModelHealth.ts

export type FeatureStatus = {
  name: string;
  status: 'Available' | 'Stale' | 'Missing';
};

export type DriftWarning = {
  feature: string;
  description: string;
};

export type ModelHealth = {
  overallStatus: 'Healthy' | 'Warning' | 'Degraded';
  trainingDate: string;
  dataFreshness: string;
  calibrationError: number;
  validationAccuracy: number;
  features: FeatureStatus[];
  driftWarnings: DriftWarning[];
};

export const mockModelHealth: ModelHealth = {
  overallStatus: 'Warning',
  trainingDate: '2026-04-18',
  dataFreshness: '5 days ago',
  calibrationError: 0.043,
  validationAccuracy: 0.64,
  features: [
    { name: 'EMA-20',         status: 'Available' },
    { name: 'EMA-50',         status: 'Available' },
    { name: 'RSI-14',         status: 'Available' },
    { name: 'MACD Signal',    status: 'Available' },
    { name: 'ATR-14',         status: 'Available' },
    { name: 'Session Flag',   status: 'Available' },
    { name: 'Volatility Reg', status: 'Stale' },
    { name: 'Event Risk Flag', status: 'Missing' },
  ],
  driftWarnings: [
    {
      feature: 'Volatility Reg',
      description: 'Last computed 6 days ago — refresh recommended before next scoring run.',
    },
  ],
};
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/data/mockModelHealth.ts
git commit -m "feat: add ModelHealth type and mock data"
```

---

## Task 3: Mock data — Signal Tracker

**Files:**
- Create: `apps/web/src/data/mockSignalTracker.ts`

- [ ] **Step 1: Create the file**

```typescript
// apps/web/src/data/mockSignalTracker.ts

export type TrackedSignal = {
  date: string;
  market: string;
  strike: string;
  expiry: string;
  recommendation: 'Take' | 'Watch' | 'Pass';
  actionTaken: 'Taken' | 'Skipped' | null;
  outcome: 'Win' | 'Loss' | 'Pending';
  edge: number;
  modelProbability: number;
};

export const mockSignals: TrackedSignal[] = [
  { date: '2026-04-23', market: 'EUR/USD', strike: '1.0880', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Pending', edge: 0.18, modelProbability: 0.70 },
  { date: '2026-04-22', market: 'GBP/USD', strike: '1.2680', expiry: '11:00', recommendation: 'Watch', actionTaken: 'Skipped', outcome: 'Win',     edge: 0.11, modelProbability: 0.58 },
  { date: '2026-04-22', market: 'USD/JPY', strike: '154.50', expiry: '16:00', recommendation: 'Pass',  actionTaken: null,      outcome: 'Loss',    edge: -0.04, modelProbability: 0.44 },
  { date: '2026-04-21', market: 'EUR/USD', strike: '1.0860', expiry: '12:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.22, modelProbability: 0.72 },
  { date: '2026-04-21', market: 'GBP/USD', strike: '1.2650', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Loss',    edge: 0.15, modelProbability: 0.65 },
  { date: '2026-04-19', market: 'USD/JPY', strike: '154.00', expiry: '10:00', recommendation: 'Watch', actionTaken: 'Skipped', outcome: 'Win',     edge: 0.09, modelProbability: 0.55 },
  { date: '2026-04-18', market: 'EUR/USD', strike: '1.0840', expiry: '11:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.20, modelProbability: 0.69 },
  { date: '2026-04-18', market: 'GBP/USD', strike: '1.2700', expiry: '16:00', recommendation: 'Pass',  actionTaken: null,      outcome: 'Win',     edge: -0.02, modelProbability: 0.45 },
  { date: '2026-04-17', market: 'EUR/USD', strike: '1.0870', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Loss',    edge: 0.13, modelProbability: 0.61 },
  { date: '2026-04-16', market: 'USD/JPY', strike: '153.50', expiry: '12:00', recommendation: 'Watch', actionTaken: 'Taken',   outcome: 'Win',     edge: 0.10, modelProbability: 0.57 },
  { date: '2026-04-15', market: 'EUR/USD', strike: '1.0855', expiry: '10:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.19, modelProbability: 0.68 },
  { date: '2026-04-14', market: 'GBP/USD', strike: '1.2660', expiry: '11:00', recommendation: 'Pass',  actionTaken: null,      outcome: 'Loss',    edge: -0.06, modelProbability: 0.42 },
  { date: '2026-04-12', market: 'USD/JPY', strike: '153.00', expiry: '14:00', recommendation: 'Take',  actionTaken: 'Skipped', outcome: 'Win',     edge: 0.16, modelProbability: 0.64 },
  { date: '2026-04-11', market: 'EUR/USD', strike: '1.0830', expiry: '16:00', recommendation: 'Watch', actionTaken: 'Skipped', outcome: 'Loss',    edge: 0.07, modelProbability: 0.53 },
  { date: '2026-04-10', market: 'GBP/USD', strike: '1.2640', expiry: '12:00', recommendation: 'Take',  actionTaken: 'Taken',   outcome: 'Win',     edge: 0.21, modelProbability: 0.71 },
];
```

- [ ] **Step 2: Commit**

```bash
git add apps/web/src/data/mockSignalTracker.ts
git commit -m "feat: add TrackedSignal type and mock data"
```

---

## Task 4: MSW handlers — 3 new endpoints

**Files:**
- Modify: `apps/web/src/mocks/handlers.ts`

- [ ] **Step 1: Update handlers.ts**

Replace the entire file with:

```typescript
import { http, HttpResponse } from 'msw';
import { mockData, mockContractDetails } from '../data/mockData';
import { mockDashboard } from '../data/mockDashboard';
import { mockBacktest } from '../data/mockBacktest';
import { mockModelHealth } from '../data/mockModelHealth';
import { mockSignals } from '../data/mockSignalTracker';

export const handlers = [
  http.get('/api/signals', () => {
    return HttpResponse.json(mockData);
  }),
  http.get('/api/dashboard', () => {
    return HttpResponse.json(mockDashboard);
  }),
  http.get<{ instrument: string; strike: string }>(
    '/api/signals/:instrument/:strike',
    ({ params }) => {
      const instrument = params.instrument.replace(/-/g, '/');
      const strike = params.strike;
      const detail = mockContractDetails.find(
        (d) => d.instrument === instrument && d.strike === strike
      );
      if (!detail) {
        return HttpResponse.json({ message: 'Not found' }, { status: 404 });
      }
      return HttpResponse.json(detail);
    }),
  http.get('/api/backtest/summary', () => {
    return HttpResponse.json(mockBacktest);
  }),
  http.get('/api/model/health', () => {
    return HttpResponse.json(mockModelHealth);
  }),
  http.get('/api/signals/tracker', () => {
    return HttpResponse.json(mockSignals);
  }),
];
```

- [ ] **Step 2: Verify existing tests still pass**

```bash
cd apps/web && npm run test:coverage
```

Expected: all existing tests pass, coverage ≥ 80%.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/mocks/handlers.ts
git commit -m "feat: add MSW handlers for backtest, model health, signal tracker"
```

---

## Task 5: useBacktest hook

**Files:**
- Create: `apps/web/src/hooks/useBacktest.ts`
- Create: `apps/web/src/hooks/useBacktest.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/hooks/useBacktest.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useBacktest } from './useBacktest';

describe('useBacktest', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useBacktest());
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('populates data after successful fetch', async () => {
    const { result } = renderHook(() => useBacktest());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.totalTrades).toBe(84);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/backtest/summary', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useBacktest());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/hooks/useBacktest.test.ts
```

Expected: FAIL — `useBacktest` not found.

- [ ] **Step 3: Implement the hook**

```typescript
// apps/web/src/hooks/useBacktest.ts
import { useEffect, useState } from 'react';
import type { BacktestSummary } from '../data/mockBacktest';

type UseBacktestResult = {
  data: BacktestSummary | null;
  loading: boolean;
  error: string | null;
};

export function useBacktest(): UseBacktestResult {
  const [data, setData] = useState<BacktestSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/backtest/summary', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<BacktestSummary>;
      })
      .then((json) => { setData(json); })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { setLoading(false); });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/hooks/useBacktest.test.ts
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/hooks/useBacktest.ts apps/web/src/hooks/useBacktest.test.ts
git commit -m "feat: add useBacktest hook"
```

---

## Task 6: useModelHealth hook

**Files:**
- Create: `apps/web/src/hooks/useModelHealth.ts`
- Create: `apps/web/src/hooks/useModelHealth.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/hooks/useModelHealth.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useModelHealth } from './useModelHealth';

describe('useModelHealth', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useModelHealth());
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('populates data after successful fetch', async () => {
    const { result } = renderHook(() => useModelHealth());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).not.toBeNull();
    expect(result.current.data?.overallStatus).toBe('Warning');
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/model/health', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useModelHealth());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toBeNull();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/hooks/useModelHealth.test.ts
```

Expected: FAIL — `useModelHealth` not found.

- [ ] **Step 3: Implement the hook**

```typescript
// apps/web/src/hooks/useModelHealth.ts
import { useEffect, useState } from 'react';
import type { ModelHealth } from '../data/mockModelHealth';

type UseModelHealthResult = {
  data: ModelHealth | null;
  loading: boolean;
  error: string | null;
};

export function useModelHealth(): UseModelHealthResult {
  const [data, setData] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/model/health', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<ModelHealth>;
      })
      .then((json) => { setData(json); })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { setLoading(false); });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/hooks/useModelHealth.test.ts
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/hooks/useModelHealth.ts apps/web/src/hooks/useModelHealth.test.ts
git commit -m "feat: add useModelHealth hook"
```

---

## Task 7: useSignalTracker hook

**Files:**
- Create: `apps/web/src/hooks/useSignalTracker.ts`
- Create: `apps/web/src/hooks/useSignalTracker.test.ts`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/hooks/useSignalTracker.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import { useSignalTracker } from './useSignalTracker';

describe('useSignalTracker', () => {
  it('returns loading:true initially', () => {
    const { result, unmount } = renderHook(() => useSignalTracker());
    expect(result.current.loading).toBe(true);
    unmount();
  });

  it('populates data after successful fetch', async () => {
    const { result } = renderHook(() => useSignalTracker());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.data).toHaveLength(15);
    expect(result.current.error).toBeNull();
  });

  it('sets error on failed fetch', async () => {
    server.use(
      http.get('/api/signals/tracker', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    const { result } = renderHook(() => useSignalTracker());
    await waitFor(() => expect(result.current.loading).toBe(false));
    expect(result.current.error).not.toBeNull();
    expect(result.current.data).toHaveLength(0);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/hooks/useSignalTracker.test.ts
```

Expected: FAIL — `useSignalTracker` not found.

- [ ] **Step 3: Implement the hook**

```typescript
// apps/web/src/hooks/useSignalTracker.ts
import { useEffect, useState } from 'react';
import type { TrackedSignal } from '../data/mockSignalTracker';

type UseSignalTrackerResult = {
  data: TrackedSignal[];
  loading: boolean;
  error: string | null;
};

export function useSignalTracker(): UseSignalTrackerResult {
  const [data, setData] = useState<TrackedSignal[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const controller = new AbortController();
    fetch('/api/signals/tracker', { signal: controller.signal })
      .then((res) => {
        if (!res.ok) throw new Error(`Request failed: ${res.status}`);
        return res.json() as Promise<TrackedSignal[]>;
      })
      .then((json) => { setData(json); })
      .catch((err: unknown) => {
        if (err instanceof Error && err.name === 'AbortError') return;
        setError(err instanceof Error ? err.message : 'Unknown error');
      })
      .finally(() => { setLoading(false); });
    return () => controller.abort();
  }, []);

  return { data, loading, error };
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/hooks/useSignalTracker.test.ts
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/hooks/useSignalTracker.ts apps/web/src/hooks/useSignalTracker.test.ts
git commit -m "feat: add useSignalTracker hook"
```

---

## Task 8: BacktestResults page

**Files:**
- Create: `apps/web/src/pages/BacktestResults.tsx`
- Create: `apps/web/src/pages/BacktestResults.test.tsx`

The equity curve is rendered as an inline SVG polyline — no chart library required.

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/pages/BacktestResults.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import BacktestResults from './BacktestResults';

function renderPage() {
  return render(<MemoryRouter><BacktestResults /></MemoryRouter>);
}

describe('BacktestResults', () => {
  it('shows spinner while loading', () => {
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders summary metrics after load', async () => {
    renderPage();
    expect(await screen.findByText('84')).toBeInTheDocument();
    expect(screen.getByText('Total Trades')).toBeInTheDocument();
  });

  it('renders results table rows', async () => {
    renderPage();
    await screen.findByText('Total Trades');
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.getByText('GBP/USD')).toBeInTheDocument();
    expect(screen.getByText('USD/JPY')).toBeInTheDocument();
  });

  it('market filter reduces visible rows', async () => {
    renderPage();
    await screen.findByText('Total Trades');
    fireEvent.mouseDown(screen.getByLabelText('Market'));
    fireEvent.click(await screen.findByRole('option', { name: 'EUR/USD' }));
    expect(screen.getByText('EUR/USD')).toBeInTheDocument();
    expect(screen.queryByText('GBP/USD')).not.toBeInTheDocument();
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/backtest/summary', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/pages/BacktestResults.test.tsx
```

Expected: FAIL — `BacktestResults` not found.

- [ ] **Step 3: Implement the page**

```typescript
// apps/web/src/pages/BacktestResults.tsx
import { useState, useMemo } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import { useBacktest } from '../hooks/useBacktest';

function pct(n: number) {
  return `${(n * 100).toFixed(1)}%`;
}

function EquityCurve({ points }: { points: Array<{ date: string; value: number }> }) {
  const W = 600;
  const H = 120;
  const values = points.map((p) => p.value);
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;
  const coords = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * W;
      const y = H - ((p.value - min) / range) * H;
      return `${x},${y}`;
    })
    .join(' ');
  return (
    <Box sx={{ overflowX: 'auto', mt: 1 }}>
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} aria-label="Equity curve">
        <polyline points={coords} fill="none" stroke="#1976d2" strokeWidth="2" />
      </svg>
    </Box>
  );
}

const BacktestResults = () => {
  const { data, loading, error } = useBacktest();
  const [marketFilter, setMarketFilter] = useState('All');
  const [regimeFilter, setRegimeFilter] = useState('All');

  const markets = useMemo(() => {
    if (!data) return [];
    return ['All', ...Array.from(new Set(data.rows.map((r) => r.market)))];
  }, [data]);

  const regimes = useMemo(() => {
    if (!data) return [];
    return ['All', ...Array.from(new Set(data.rows.map((r) => r.regime)))];
  }, [data]);

  const filteredRows = useMemo(() => {
    if (!data) return [];
    return data.rows.filter(
      (r) =>
        (marketFilter === 'All' || r.market === marketFilter) &&
        (regimeFilter === 'All' || r.regime === regimeFilter)
    );
  }, [data, marketFilter, regimeFilter]);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Backtest Results
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Out-of-sample performance by market and regime
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load backtest: {error}</Alert>}

      {!loading && !error && data && (
        <>
          <Grid container spacing={2} sx={{ mb: 4 }}>
            {[
              { label: 'Total Trades', value: String(data.totalTrades) },
              { label: 'Win Rate',     value: pct(data.winRate) },
              { label: 'Avg Edge',     value: pct(data.avgEdge) },
              { label: 'Max Drawdown', value: pct(data.maxDrawdown) },
            ].map((item) => (
              <Grid key={item.label} size={{ xs: 6, sm: 3 }}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="h4" component="p">{item.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Paper sx={{ p: 2, mb: 4 }}>
            <Typography variant="h6" gutterBottom>Equity Curve</Typography>
            <EquityCurve points={data.equityCurve} />
          </Paper>

          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="market-filter-label">Market</InputLabel>
              <Select
                labelId="market-filter-label"
                value={marketFilter}
                label="Market"
                onChange={(e) => setMarketFilter(e.target.value)}
              >
                {markets.map((m) => <MenuItem key={m} value={m}>{m}</MenuItem>)}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="regime-filter-label">Regime</InputLabel>
              <Select
                labelId="regime-filter-label"
                value={regimeFilter}
                label="Regime"
                onChange={(e) => setRegimeFilter(e.target.value)}
              >
                {regimes.map((r) => <MenuItem key={r} value={r}>{r}</MenuItem>)}
              </Select>
            </FormControl>
          </Box>

          <Paper>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Market</TableCell>
                  <TableCell>Regime</TableCell>
                  <TableCell>Expiry Window</TableCell>
                  <TableCell align="right">Trades</TableCell>
                  <TableCell align="right">Win Rate</TableCell>
                  <TableCell align="right">Avg Edge</TableCell>
                  <TableCell align="right">Net Return</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredRows.map((row) => (
                  <TableRow key={`${row.market}-${row.regime}-${row.expiryWindow}`}>
                    <TableCell>{row.market}</TableCell>
                    <TableCell>{row.regime}</TableCell>
                    <TableCell>{row.expiryWindow}</TableCell>
                    <TableCell align="right">{row.trades}</TableCell>
                    <TableCell align="right">{pct(row.winRate)}</TableCell>
                    <TableCell align="right">{pct(row.avgEdge)}</TableCell>
                    <TableCell align="right">{pct(row.netReturn)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </Container>
  );
};

export default BacktestResults;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/pages/BacktestResults.test.tsx
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/BacktestResults.tsx apps/web/src/pages/BacktestResults.test.tsx
git commit -m "feat: add BacktestResults page"
```

---

## Task 9: ModelHealth page

**Files:**
- Create: `apps/web/src/pages/ModelHealth.tsx`
- Create: `apps/web/src/pages/ModelHealth.test.tsx`

Note: a `ModelHealth` type is already defined in `apps/web/src/data/mockDashboard.ts` for the Dashboard's summary widget. The new `ModelHealth` in `apps/web/src/data/mockModelHealth.ts` is a richer, separate type for this dedicated page. The page imports from `mockModelHealth.ts`, not `mockDashboard.ts`.

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/pages/ModelHealth.test.tsx
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/pages/ModelHealth.test.tsx
```

Expected: FAIL — `ModelHealth` page not found.

- [ ] **Step 3: Implement the page**

```typescript
// apps/web/src/pages/ModelHealth.tsx
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import { useModelHealth } from '../hooks/useModelHealth';

const statusColor = (s: 'Healthy' | 'Warning' | 'Degraded') =>
  s === 'Healthy' ? 'success' : s === 'Warning' ? 'warning' : 'error';

const featureColor = (s: 'Available' | 'Stale' | 'Missing') =>
  s === 'Available' ? 'success' : s === 'Stale' ? 'warning' : 'error';

const ModelHealth = () => {
  const { data, loading, error } = useModelHealth();

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Model Health
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Current model status, feature availability, and drift indicators
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load model health: {error}</Alert>}

      {!loading && !error && data && (
        <>
          <Paper sx={{ p: 2, mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
            <Typography variant="h6">Overall Status</Typography>
            <Chip
              label={data.overallStatus}
              color={statusColor(data.overallStatus)}
            />
          </Paper>

          <Grid container spacing={2} sx={{ mb: 4 }}>
            {[
              { label: 'Training Date',       value: data.trainingDate },
              { label: 'Data Freshness',       value: data.dataFreshness },
              { label: 'Calibration Error',    value: data.calibrationError.toFixed(3) },
              { label: 'Validation Accuracy',  value: `${(data.validationAccuracy * 100).toFixed(1)}%` },
            ].map((item) => (
              <Grid key={item.label} size={{ xs: 6, sm: 3 }}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="h5" component="p">{item.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Paper sx={{ mb: 4 }}>
            <Typography variant="h6" sx={{ p: 2, pb: 0 }}>Feature Availability</Typography>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Feature</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {data.features.map((f) => (
                  <TableRow key={f.name}>
                    <TableCell>{f.name}</TableCell>
                    <TableCell>
                      <Chip label={f.status} color={featureColor(f.status)} size="small" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>

          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" gutterBottom>Drift Warnings</Typography>
            {data.driftWarnings.length === 0 ? (
              <Typography variant="body2" color="text.secondary">No issues detected.</Typography>
            ) : (
              data.driftWarnings.map((w) => (
                <Alert key={w.feature} severity="warning" sx={{ mb: 1 }}>
                  <strong>{w.feature}:</strong> {w.description}
                </Alert>
              ))
            )}
          </Paper>
        </>
      )}
    </Container>
  );
};

export default ModelHealth;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/pages/ModelHealth.test.tsx
```

Expected: 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/ModelHealth.tsx apps/web/src/pages/ModelHealth.test.tsx
git commit -m "feat: add ModelHealth page"
```

---

## Task 10: HowItWorks page

**Files:**
- Create: `apps/web/src/pages/HowItWorks.tsx`
- Create: `apps/web/src/pages/HowItWorks.test.tsx`

No hook or MSW handler. Static content only.

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/pages/HowItWorks.test.tsx
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/pages/HowItWorks.test.tsx
```

Expected: FAIL — `HowItWorks` not found.

- [ ] **Step 3: Implement the page**

```typescript
// apps/web/src/pages/HowItWorks.tsx
import Accordion from '@mui/material/Accordion';
import AccordionDetails from '@mui/material/AccordionDetails';
import AccordionSummary from '@mui/material/AccordionSummary';
import Container from '@mui/material/Container';
import Typography from '@mui/material/Typography';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';

const SECTIONS = [
  {
    title: 'What LIVEWELL Predicts',
    content: `LIVEWELL predicts whether a NADEX binary contract will expire in the money. Each contract has a fixed payout (usually $100) and a cost set by the market. The model estimates the probability that the underlying price will be above or below the contract's strike at expiry. A model probability of 0.68 means the model believes there is a 68% chance the contract expires in the money. The breakeven probability is the cost divided by the payout — if you pay $42 for a $100 contract, breakeven is 42%. Edge is the difference: 68% − 42% = 26%.`,
    example: 'Example: EUR/USD > 1.0850 by 14:00. Cost $42. Payout $100. Breakeven 42%. Model probability 68%. Estimated edge +26%.',
  },
  {
    title: 'How Edge Is Calculated',
    content: `Edge is payout-aware expected value. It is not raw model accuracy. A model with 60% accuracy on a 50% breakeven contract has edge. The same model on a 65% breakeven contract does not. The formula is: Edge = Model Probability − Breakeven Probability. Positive edge means the model believes the contract is underpriced by the market. LIVEWELL only recommends contracts where edge clears a minimum threshold after accounting for transaction costs.`,
    example: 'Example: Model probability 0.62. Contract cost $55. Payout $100. Breakeven 55%. Edge = 62% − 55% = 7%. This is positive but below the High confidence threshold.',
  },
  {
    title: 'What the Confidence Tiers Mean',
    content: `Confidence tiers summarise the strength of a signal. High confidence means edge is above 15% and the regime is clearly confirmed. Medium means edge is between 8% and 15%, or regime confirmation is partial. Low means edge is between 0% and 8%, or one or more supporting conditions are weak. Low confidence signals appear in Signal Tracker but are rarely recommended as Take.`,
    example: 'Example: Edge +22%, Bullish regime confirmed, RSI momentum favourable → High confidence. Edge +10%, Neutral regime → Medium confidence.',
  },
  {
    title: 'When Not to Trade',
    content: `LIVEWELL issues a no-trade flag when one or more blocking conditions are met. These include: a scheduled high-impact economic event within the expiry window (NFP, CPI, FOMC), abnormally low volatility that compresses edge below meaningful levels, regime ambiguity where trend direction is unclear across timeframes, and negative or near-zero model edge after costs. A no-trade day is not a failure — it is the system working as intended.`,
    example: 'Example: NFP release at 13:30. Any contract expiring at 14:00 is flagged no-trade regardless of model probability.',
  },
];

const HowItWorks = () => (
  <Container maxWidth="md" sx={{ py: 4 }}>
    <Typography variant="h4" component="h1" gutterBottom>
      How It Works
    </Typography>
    <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
      Understand what LIVEWELL computes, how decisions are made, and when not to trade.
    </Typography>
    {SECTIONS.map((s) => (
      <Accordion key={s.title}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography fontWeight="bold">{s.title}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Typography variant="body2" paragraph>{s.content}</Typography>
          <Typography variant="body2" color="text.secondary" fontStyle="italic">{s.example}</Typography>
        </AccordionDetails>
      </Accordion>
    ))}
  </Container>
);

export default HowItWorks;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/pages/HowItWorks.test.tsx
```

Expected: 3 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/HowItWorks.tsx apps/web/src/pages/HowItWorks.test.tsx
git commit -m "feat: add HowItWorks page"
```

---

## Task 11: SignalTracker page

**Files:**
- Create: `apps/web/src/pages/SignalTracker.tsx`
- Create: `apps/web/src/pages/SignalTracker.test.tsx`

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/pages/SignalTracker.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { server } from '../mocks/server';
import { http, HttpResponse } from 'msw';
import SignalTracker from './SignalTracker';

function renderPage() {
  return render(<MemoryRouter><SignalTracker /></MemoryRouter>);
}

describe('SignalTracker', () => {
  it('shows spinner while loading', () => {
    renderPage();
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders summary strip after load', async () => {
    renderPage();
    expect(await screen.findByText('Total Signals')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
  });

  it('renders signal table rows', async () => {
    renderPage();
    await screen.findByText('Total Signals');
    expect(screen.getAllByText('EUR/USD').length).toBeGreaterThan(0);
    expect(screen.getAllByText('GBP/USD').length).toBeGreaterThan(0);
  });

  it('recommendation filter reduces visible rows', async () => {
    renderPage();
    await screen.findByText('Total Signals');
    fireEvent.mouseDown(screen.getByLabelText('Recommendation'));
    fireEvent.click(await screen.findByRole('option', { name: 'Take' }));
    const rows = screen.getAllByRole('row');
    // header row + only "Take" rows (7 in mock data)
    expect(rows.length).toBe(8);
  });

  it('shows error alert on fetch failure', async () => {
    server.use(
      http.get('/api/signals/tracker', () =>
        HttpResponse.json({ message: 'error' }, { status: 500 })
      )
    );
    renderPage();
    expect(await screen.findByRole('alert')).toBeInTheDocument();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/pages/SignalTracker.test.tsx
```

Expected: FAIL — `SignalTracker` not found.

- [ ] **Step 3: Implement the page**

```typescript
// apps/web/src/pages/SignalTracker.tsx
import { useState, useMemo } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import Grid from '@mui/material/Grid';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Paper from '@mui/material/Paper';
import Select from '@mui/material/Select';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Typography from '@mui/material/Typography';
import { useSignalTracker } from '../hooks/useSignalTracker';
import type { TrackedSignal } from '../data/mockSignalTracker';

const recColor = (r: TrackedSignal['recommendation']) =>
  r === 'Take' ? 'success' : r === 'Watch' ? 'warning' : 'default';

const outcomeColor = (o: TrackedSignal['outcome']) =>
  o === 'Win' ? 'success' : o === 'Loss' ? 'error' : 'default';

const SignalTracker = () => {
  const { data, loading, error } = useSignalTracker();
  const [recFilter, setRecFilter] = useState('All');
  const [outcomeFilter, setOutcomeFilter] = useState('All');

  const filteredData = useMemo(() => {
    return data.filter(
      (s) =>
        (recFilter === 'All' || s.recommendation === recFilter) &&
        (outcomeFilter === 'All' || s.outcome === outcomeFilter)
    );
  }, [data, recFilter, outcomeFilter]);

  const taken = data.filter((s) => s.actionTaken === 'Taken');
  const wins = taken.filter((s) => s.outcome === 'Win');
  const pending = data.filter((s) => s.outcome === 'Pending');
  const winRate = taken.length > 0 ? `${Math.round((wins.length / taken.length) * 100)}%` : '—';

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Signal Tracker
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Every scored opportunity, what was taken, and realized outcomes
      </Typography>

      {loading && (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
          <CircularProgress />
        </Box>
      )}

      {error && <Alert severity="error" sx={{ mb: 3 }}>Failed to load tracker: {error}</Alert>}

      {!loading && !error && (
        <>
          <Grid container spacing={2} sx={{ mb: 4 }}>
            {[
              { label: 'Total Signals',       value: String(data.length) },
              { label: 'Taken',               value: String(taken.length) },
              { label: 'Win Rate (Taken)',     value: winRate },
              { label: 'Pending',             value: String(pending.length) },
            ].map((item) => (
              <Grid key={item.label} size={{ xs: 6, sm: 3 }}>
                <Paper sx={{ p: 3, textAlign: 'center' }}>
                  <Typography variant="h4" component="p">{item.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{item.label}</Typography>
                </Paper>
              </Grid>
            ))}
          </Grid>

          <Box sx={{ display: 'flex', gap: 2, mb: 3, flexWrap: 'wrap' }}>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="rec-filter-label">Recommendation</InputLabel>
              <Select
                labelId="rec-filter-label"
                value={recFilter}
                label="Recommendation"
                onChange={(e) => setRecFilter(e.target.value)}
              >
                {['All', 'Take', 'Watch', 'Pass'].map((v) => (
                  <MenuItem key={v} value={v}>{v}</MenuItem>
                ))}
              </Select>
            </FormControl>
            <FormControl size="small" sx={{ minWidth: 160 }}>
              <InputLabel id="outcome-filter-label">Outcome</InputLabel>
              <Select
                labelId="outcome-filter-label"
                value={outcomeFilter}
                label="Outcome"
                onChange={(e) => setOutcomeFilter(e.target.value)}
              >
                {['All', 'Win', 'Loss', 'Pending'].map((v) => (
                  <MenuItem key={v} value={v}>{v}</MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Paper>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Date</TableCell>
                  <TableCell>Market</TableCell>
                  <TableCell>Strike</TableCell>
                  <TableCell>Expiry</TableCell>
                  <TableCell>Recommendation</TableCell>
                  <TableCell>Action</TableCell>
                  <TableCell>Outcome</TableCell>
                  <TableCell align="right">Edge</TableCell>
                  <TableCell align="right">Model Prob</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {filteredData.map((s, i) => (
                  <TableRow key={i}>
                    <TableCell>{s.date}</TableCell>
                    <TableCell>{s.market}</TableCell>
                    <TableCell>{s.strike}</TableCell>
                    <TableCell>{s.expiry}</TableCell>
                    <TableCell>
                      <Chip label={s.recommendation} color={recColor(s.recommendation)} size="small" />
                    </TableCell>
                    <TableCell>{s.actionTaken ?? '—'}</TableCell>
                    <TableCell>
                      <Chip label={s.outcome} color={outcomeColor(s.outcome)} size="small" />
                    </TableCell>
                    <TableCell align="right">{(s.edge * 100).toFixed(0)}%</TableCell>
                    <TableCell align="right">{(s.modelProbability * 100).toFixed(0)}%</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Paper>
        </>
      )}
    </Container>
  );
};

export default SignalTracker;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/pages/SignalTracker.test.tsx
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/SignalTracker.tsx apps/web/src/pages/SignalTracker.test.tsx
git commit -m "feat: add SignalTracker page"
```

---

## Task 12: OptionsAdvisor page

**Files:**
- Create: `apps/web/src/pages/OptionsAdvisor.tsx`
- Create: `apps/web/src/pages/OptionsAdvisor.test.tsx`

No hook or MSW handler. Wizard runs on local React state. Filters `mockContractDetails` from `src/data/mockData.ts` by instrument.

- [ ] **Step 1: Write the failing test**

```typescript
// apps/web/src/pages/OptionsAdvisor.test.tsx
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
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd apps/web && npx vitest run src/pages/OptionsAdvisor.test.tsx
```

Expected: FAIL — `OptionsAdvisor` not found.

- [ ] **Step 3: Implement the page**

```typescript
// apps/web/src/pages/OptionsAdvisor.tsx
import { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Container from '@mui/material/Container';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import FormLabel from '@mui/material/FormLabel';
import Paper from '@mui/material/Paper';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { mockContractDetails } from '../data/mockData';

type AdvisorState = {
  step: 1 | 2 | 3 | 'result';
  market: string | null;
  expiryWindow: '2-hour' | 'Daily' | null;
  trend: 'Bullish' | 'Bearish' | 'Neutral' | null;
  volatility: 'Low' | 'Normal' | 'High' | null;
  eventRisk: 'None' | 'Low' | 'High' | null;
};

const INITIAL: AdvisorState = {
  step: 1,
  market: null,
  expiryWindow: null,
  trend: null,
  volatility: null,
  eventRisk: null,
};

const MARKETS = ['EUR/USD', 'GBP/USD', 'USD/JPY', 'Gold', 'US 500'];

function candidateExplanation(
  regime: string,
  trend: string | null,
  volatility: string | null,
  eventRisk: string | null
): string {
  const notes: string[] = [];
  if (regime === trend) notes.push(`regime matches selected trend (${trend})`);
  else notes.push(`regime (${regime}) differs from selected trend (${trend})`);
  if (volatility === 'High') notes.push('high volatility selected — spread risk elevated');
  if (eventRisk === 'High') notes.push('high event risk — no-trade conditions may apply');
  return notes.join('; ');
}

const OptionsAdvisor = () => {
  const [state, setState] = useState<AdvisorState>(INITIAL);

  const update = (partial: Partial<AdvisorState>) =>
    setState((s) => ({ ...s, ...partial }));

  const candidates = mockContractDetails.filter(
    (c) => c.instrument === state.market
  );

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        Options Advisor
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
        Answer a few questions to get filtered contract candidates for your current setup.
      </Typography>

      {state.step === 1 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Step 1: Select a Market</Typography>
          <FormControl component="fieldset">
            <RadioGroup
              value={state.market ?? ''}
              onChange={(e) => update({ market: e.target.value })}
            >
              {MARKETS.map((m) => (
                <FormControlLabel key={m} value={m} control={<Radio />} label={m} />
              ))}
            </RadioGroup>
          </FormControl>
          <Box sx={{ mt: 3 }}>
            <Button
              variant="contained"
              disabled={!state.market}
              onClick={() => update({ step: 2 })}
            >
              Next
            </Button>
          </Box>
        </Paper>
      )}

      {state.step === 2 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Step 2: Select Expiry Window</Typography>
          <FormControl component="fieldset">
            <RadioGroup
              value={state.expiryWindow ?? ''}
              onChange={(e) => update({ expiryWindow: e.target.value as '2-hour' | 'Daily' })}
            >
              <FormControlLabel value="2-hour" control={<Radio />} label="2-hour" />
              <FormControlLabel value="Daily"  control={<Radio />} label="Daily" />
            </RadioGroup>
          </FormControl>
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => update({ step: 1 })}>Back</Button>
            <Button
              variant="contained"
              disabled={!state.expiryWindow}
              onClick={() => update({ step: 3 })}
            >
              Next
            </Button>
          </Box>
        </Paper>
      )}

      {state.step === 3 && (
        <Paper sx={{ p: 3 }}>
          <Typography variant="h6" gutterBottom>Step 3: Describe Current Regime</Typography>
          <Stack spacing={3}>
            <FormControl component="fieldset">
              <FormLabel component="legend">Trend Direction</FormLabel>
              <RadioGroup
                row
                value={state.trend ?? ''}
                onChange={(e) => update({ trend: e.target.value as AdvisorState['trend'] })}
              >
                {['Bullish', 'Bearish', 'Neutral'].map((v) => (
                  <FormControlLabel key={v} value={v} control={<Radio />} label={v} />
                ))}
              </RadioGroup>
            </FormControl>
            <FormControl component="fieldset">
              <FormLabel component="legend">Volatility</FormLabel>
              <RadioGroup
                row
                value={state.volatility ?? ''}
                onChange={(e) => update({ volatility: e.target.value as AdvisorState['volatility'] })}
              >
                {['Low', 'Normal', 'High'].map((v) => (
                  <FormControlLabel key={v} value={v} control={<Radio />} label={v} />
                ))}
              </RadioGroup>
            </FormControl>
            <FormControl component="fieldset">
              <FormLabel component="legend">Event Risk</FormLabel>
              <RadioGroup
                row
                value={state.eventRisk ?? ''}
                onChange={(e) => update({ eventRisk: e.target.value as AdvisorState['eventRisk'] })}
              >
                {['None', 'Low', 'High'].map((v) => (
                  <FormControlLabel key={v} value={v} control={<Radio />} label={v} />
                ))}
              </RadioGroup>
            </FormControl>
          </Stack>
          <Box sx={{ mt: 3, display: 'flex', gap: 2 }}>
            <Button variant="outlined" onClick={() => update({ step: 2 })}>Back</Button>
            <Button
              variant="contained"
              disabled={!state.trend || !state.volatility || !state.eventRisk}
              onClick={() => update({ step: 'result' })}
            >
              View Candidates
            </Button>
          </Box>
        </Paper>
      )}

      {state.step === 'result' && (
        <Box>
          <Typography variant="h6" gutterBottom>Matching Candidates</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Market: {state.market} | Expiry: {state.expiryWindow} | Trend: {state.trend} | Volatility: {state.volatility} | Event Risk: {state.eventRisk}
          </Typography>
          {candidates.length === 0 ? (
            <Paper sx={{ p: 3 }}>
              <Typography variant="body1">No candidates found for {state.market} in current mock data.</Typography>
            </Paper>
          ) : (
            <Stack spacing={2} sx={{ mb: 3 }}>
              {candidates.map((c) => (
                <Card key={`${c.instrument}-${c.strike}`}>
                  <CardContent>
                    <Stack direction="row" justifyContent="space-between" alignItems="flex-start" flexWrap="wrap" gap={1}>
                      <Box>
                        <Typography variant="subtitle1" fontWeight="bold">
                          {c.instrument} @ {c.strike} — {c.expiry}
                        </Typography>
                        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                          {candidateExplanation(c.regime, state.trend, state.volatility, state.eventRisk)}
                        </Typography>
                      </Box>
                      <Chip
                        label={c.recommendation}
                        color={c.recommendation === 'Take' ? 'success' : c.recommendation === 'Watch' ? 'warning' : 'default'}
                        size="small"
                      />
                    </Stack>
                  </CardContent>
                </Card>
              ))}
            </Stack>
          )}
          <Button variant="outlined" onClick={() => setState(INITIAL)}>Start Over</Button>
        </Box>
      )}
    </Container>
  );
};

export default OptionsAdvisor;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd apps/web && npx vitest run src/pages/OptionsAdvisor.test.tsx
```

Expected: 5 tests pass.

- [ ] **Step 5: Commit**

```bash
git add apps/web/src/pages/OptionsAdvisor.tsx apps/web/src/pages/OptionsAdvisor.test.tsx
git commit -m "feat: add OptionsAdvisor page"
```

---

## Task 13: Wire all 5 pages into App.tsx

**Files:**
- Modify: `apps/web/src/App.tsx`

- [ ] **Step 1: Update App.tsx**

Replace the entire file with:

```typescript
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
import BacktestResults from './pages/BacktestResults';
import ModelHealth from './pages/ModelHealth';
import HowItWorks from './pages/HowItWorks';
import SignalTracker from './pages/SignalTracker';
import OptionsAdvisor from './pages/OptionsAdvisor';
import { useTheme } from './components/theme-provider';

const NAV_ITEMS = [
  { label: 'Dashboard',       path: '/' },
  { label: 'Daily Signals',   path: '/signals' },
  { label: 'Backtest Results',path: '/backtest' },
  { label: 'Model Health',    path: '/model-health' },
  { label: 'How It Works',    path: '/how-it-works' },
  { label: 'Signal Tracker',  path: '/tracker' },
  { label: 'Options Advisor', path: '/advisor' },
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
          <Box component="nav" sx={{ width: 240, pt: 1 }} aria-label="navigation drawer">
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
          <Route path="/"             element={<Dashboard />} />
          <Route path="/signals"      element={<DailySignals />} />
          <Route path="/signals/:instrument/:strike" element={<ContractDetail />} />
          <Route path="/backtest"     element={<BacktestResults />} />
          <Route path="/model-health" element={<ModelHealth />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/tracker"      element={<SignalTracker />} />
          <Route path="/advisor"      element={<OptionsAdvisor />} />
        </Routes>
      </Box>
    </>
  );
};

export default App;
```

- [ ] **Step 2: Run the full test suite with coverage**

```bash
cd apps/web && npm run test:coverage
```

Expected: all tests pass, coverage ≥ 80%.

- [ ] **Step 3: Commit**

```bash
git add apps/web/src/App.tsx
git commit -m "feat: wire 5 deferred pages into app routing and navigation"
```

---

## Task 14: Smoke-test in the browser

- [ ] **Step 1: Start the dev server**

```bash
cd apps/web && npm run dev
```

- [ ] **Step 2: Visit each new page and verify it renders**

Open `http://localhost:5173`, open the nav drawer, and navigate to:
- `/backtest` — summary strip, table rows, equity curve visible
- `/model-health` — Warning banner, 8 feature rows, 1 drift warning
- `/how-it-works` — 4 accordion panels, each expands
- `/tracker` — 15 signal rows, filter dropdowns work
- `/advisor` — step 1 loads, full wizard flow reaches result panel

- [ ] **Step 3: Update `apps/web/current_step_plan.md`**

Replace the file contents with:

```markdown
# Current Step: Phase 1D — Frontend/Backend Integration

**Phase 1C status:** Complete
- Backtest Results page (useBacktest hook, BacktestResults page, 5 tests)
- Model Health page (useModelHealth hook, ModelHealth page, 6 tests)
- How It Works page (static accordion, 3 tests)
- Signal Tracker page (useSignalTracker hook, SignalTracker page, 5 tests)
- Options Advisor page (3-step wizard, local state, 5 tests)
- All 5 pages wired into App.tsx routing and sidebar navigation

---

## Next: Phase 1D — Frontend/Backend Integration

- Switch frontend off MSW; point fetch calls at real FastAPI backend (`localhost:8000`)
- Remove MSW service worker registration from `main.tsx` (or guard behind a flag)
- Verify all 5 existing routes work end-to-end against real FastAPI responses
- Add matching routes/stubs to `apps/api` for the 3 new endpoints:
  - `GET /api/backtest/summary`
  - `GET /api/model/health`
  - `GET /api/signals/tracker`
```

- [ ] **Step 4: Commit**

```bash
git add apps/web/current_step_plan.md
git commit -m "chore: update current_step_plan to Phase 1D"
```
