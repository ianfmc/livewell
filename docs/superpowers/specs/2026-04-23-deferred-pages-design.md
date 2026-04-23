# Design: Phase 1C — Deferred Pages

**Date:** 2026-04-23  
**Status:** Approved  
**Scope:** Build the 5 deferred Phase 1A pages against mock data, following the existing hook/MSW/page pattern.

---

## Context

Phase 1A delivered Dashboard, Daily Signals, Contract Detail, sidebar navigation, and a test suite (97.87% statement coverage, 80% threshold). Phase 1B delivered the FastAPI backend skeleton at `apps/api/`. Five pages were deferred:

- Backtest Results
- Model Health
- How It Works
- Signal Tracker
- Options Advisor

This spec covers Phase 1C: building all five to production quality with realistic mock data, matching the existing pattern.

---

## Approach

**Option A — Pages first, integration later.**

All 5 pages are built against mock data. The frontend still uses MSW throughout this phase. Backend wiring (removing MSW, pointing at real FastAPI endpoints) is a separate subsequent phase.

---

## Architecture

### New files

```
src/data/
  mockBacktest.ts          — BacktestSummary type + mock data
  mockModelHealth.ts       — ModelHealth type + mock data
  mockSignalTracker.ts     — TrackedSignal type + mock data

src/hooks/
  useBacktest.ts           — fetches GET /api/backtest/summary
  useBacktest.test.ts
  useModelHealth.ts        — fetches GET /api/model/health
  useModelHealth.test.ts
  useSignalTracker.ts      — fetches GET /api/signals/tracker
  useSignalTracker.test.ts

src/pages/
  BacktestResults.tsx
  BacktestResults.test.tsx
  ModelHealth.tsx
  ModelHealth.test.tsx
  HowItWorks.tsx
  HowItWorks.test.tsx
  SignalTracker.tsx
  SignalTracker.test.tsx
  OptionsAdvisor.tsx
  OptionsAdvisor.test.tsx
```

### MSW handlers added (in `src/mocks/handlers.ts`)

| Endpoint | Page |
|---|---|
| `GET /api/backtest/summary` | Backtest Results |
| `GET /api/model/health` | Model Health |
| `GET /api/signals/tracker` | Signal Tracker |

Options Advisor has no backend fetch — the wizard runs entirely on local React state.

### Mock data files

One file per domain area. `mockData.ts` retains `ContractCard` and `ContractDetail`. New domain types live in their own files. `handlers.ts` imports from whichever file it needs.

---

## Page Designs

### Backtest Results

**Hook:** `useBacktest` — `{ data: BacktestSummary | null, loading, error }`  
**Endpoint:** `GET /api/backtest/summary`

**Layout:**
1. Summary metrics strip — 4 stat cards: total trades, win rate, avg edge, max drawdown
2. Filter bar — market selector, regime selector, expiry window selector
3. Results table — one row per market+regime combination: trades, win rate, avg edge, net return
4. Equity curve — Recharts `LineChart` with mock cumulative return data points

**Types:**
```ts
type BacktestRow = {
  market: string;
  regime: string;
  expiryWindow: string;
  trades: number;
  winRate: number;
  avgEdge: number;
  netReturn: number;
};

type BacktestSummary = {
  totalTrades: number;
  winRate: number;
  avgEdge: number;
  maxDrawdown: number;
  equityCurve: Array<{ date: string; value: number }>;
  rows: BacktestRow[];
};
```

**Mock data:** 3 markets × 2 regimes = 6 rows, 30-point equity curve.

---

### Model Health

**Hook:** `useModelHealth` — `{ data: ModelHealth | null, loading, error }`  
**Endpoint:** `GET /api/model/health`

**Layout:**
1. Status banner — chip/alert showing overall state: Healthy / Warning / Degraded
2. 4-card metric grid — training date, data freshness, calibration error (Brier score), validation accuracy
3. Feature availability table — feature name + status chip (Available / Stale / Missing)
4. Drift warnings section — "No issues detected" or list of flagged features with description

**Types:**
```ts
type FeatureStatus = {
  name: string;
  status: 'Available' | 'Stale' | 'Missing';
};

type DriftWarning = {
  feature: string;
  description: string;
};

type ModelHealth = {
  overallStatus: 'Healthy' | 'Warning' | 'Degraded';
  trainingDate: string;
  dataFreshness: string;
  calibrationError: number;
  validationAccuracy: number;
  features: FeatureStatus[];
  driftWarnings: DriftWarning[];
};
```

**Mock data:** 8 features (6 Available, 1 Stale, 1 Missing), 1 drift warning, overall status Warning.

---

### How It Works

**No hook, no MSW handler.** Static content only.

**Layout:** Four MUI `Accordion` sections:

1. **What LIVEWELL predicts** — explains binary contract outcome prediction, model probability vs breakeven probability
2. **How edge is calculated** — payout-aware edge formula, concrete NADEX example with numbers
3. **What the confidence tiers mean** — High / Medium / Low definitions with typical edge ranges
4. **When not to trade** — no-trade flag conditions: event risk, low volatility, regime ambiguity, negative edge

Each section: 2–4 sentences of prose + one concrete NADEX example where relevant.

**Tests:** renders without crashing; each accordion panel expands when clicked.

---

### Signal Tracker

**Hook:** `useSignalTracker` — `{ data: TrackedSignal[], loading, error }`  
**Endpoint:** `GET /api/signals/tracker`

**Layout:**
1. Summary strip — 4 stat cards: total signals, taken count, win rate on taken, pending count
2. Filter bar — date range (Last 7 / 30 / 90 days), recommendation filter, outcome filter
3. Signals table — columns: date, market, strike, expiry, recommendation, action taken, outcome, edge, model probability

**Types:**
```ts
type TrackedSignal = {
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
```

**Mock data:** 15 signals across the last 30 days, mix of all recommendation types and outcomes.

---

### Options Advisor

**No hook, no MSW handler.** Wizard runs entirely on local React state.

**Layout:** 3-step wizard with a result panel.

**Step 1 — Market**  
Radio group: EUR/USD, GBP/USD, USD/JPY, Gold, US 500.

**Step 2 — Expiry window**  
Radio group: 2-hour, Daily.

**Step 3 — Regime questions** (3 radio groups)  
- Trend direction: Bullish / Bearish / Neutral  
- Volatility: Low / Normal / High  
- Event risk: None / Low / High

**Result panel**  
Filters the existing `mockContractDetails` (from `mockData.ts`) by instrument matching the selected market. Displays matching `ContractCard` candidates with a one-line explanation of why each passes or fails the regime selections. A "Start over" button resets wizard state to Step 1.

**State type:**
```ts
type AdvisorState = {
  step: 1 | 2 | 3 | 'result';
  market: string | null;
  expiryWindow: '2-hour' | 'Daily' | null;
  trend: 'Bullish' | 'Bearish' | 'Neutral' | null;
  volatility: 'Low' | 'Normal' | 'High' | null;
  eventRisk: 'None' | 'Low' | 'High' | null;
};
```

---

## Testing

All pages and hooks follow the existing pattern:
- Hooks: `renderHook` + MSW server intercept, test loading → data → error states
- Pages: `render` + `screen` queries, `MemoryRouter` wrapper where `Link` is used
- How It Works: renders without crashing, accordion interaction
- Options Advisor: wizard step progression, result panel rendering, "Start over" reset
- 80% statement coverage threshold enforced (existing `vite.config.ts` threshold unchanged)

---

## Out of Scope

- Backend wiring (removing MSW, pointing at real FastAPI) — subsequent phase
- Real data (DynamoDB, S3, ML models) — Phase 2
- Drill-down row detail on Backtest Results — Phase 2
- Live agent/LLM in Options Advisor — Phase 2+
