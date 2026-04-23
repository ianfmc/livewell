# Contract Detail Page — Design Spec

## Context

LIVEWELL is a decision-support UI for NADEX binary options. The Daily Signals page lists contract candidates as cards. This spec adds a Contract Detail page: a dedicated view that explains one contract deeply — economics, model probability, edge, regime context, reason codes, and a clear Take / Watch / Pass recommendation.

The goal is interpretability: the Dashboard says "here are the candidates," Contract Detail says "here's why."

---

## Decisions Made

| Question | Decision |
|---|---|
| Navigation trigger | Entire `ContractCard` is clickable — navigates to detail page |
| Info dialog | Removed — card click replaces it |
| URL structure | `/signals/:instrument/:strike` (e.g. `/signals/EUR-USD/1.0850`) |
| Data source | Dedicated `GET /api/signals/:instrument/:strike` MSW handler + `useContractDetail` hook |
| Layout | C — Header + context chips + 4-up metric strip + reason codes |

---

## Layout (C)

```
┌─────────────────────────────────────────────────┐
│ ← Daily Signals                                 │
│                                                 │
│  EUR/USD                              [TAKE]    │
│  Strike 1.0850 · Expires 10:00 AM              │
│                                                 │
│  [Bullish] [High confidence] [Event risk]       │
│                                                 │
│  ┌──────┐ ┌────────┐ ┌────────┐ ┌──────┐      │
│  │ $42  │ │  $100  │ │  68%   │ │ +14% │      │
│  │ Cost │ │ Payout │ │ Model  │ │ Edge │      │
│  └──────┘ └────────┘ └────────┘ └──────┘      │
│                                                 │
│  WHY THIS SETUP                                 │
│  ✓ Bullish regime confirmed                    │
│  ✓ RSI momentum favourable                     │
│  ✗ Event risk flag active                      │
│                                                 │
│  Rationale: Strong directional setup with       │
│  acceptable event risk.                         │
└─────────────────────────────────────────────────┘
```

Sections top to bottom:
1. Back link + instrument header + recommendation chip (right-aligned)
2. Strike and expiry subtitle
3. Context chips row (regime, confidence, no-trade flag if active)
4. 4-up metric strip (Cost / Payout / Model % / Edge)
5. Reason codes list (✓ / ✗ per item)
6. One-line rationale

---

## Data Model

Add `ContractDetail` type to `src/data/mockData.ts`:

```ts
export type ContractDetail = {
  instrument: string
  strike: string
  expiry: string
  status: string
  recommendation: 'Take' | 'Watch' | 'Pass'
  rationale: string
  economics: {
    cost: number
    payout: number
    breakeven: number
  }
  modelProbability: number   // 0–1, e.g. 0.68
  edge: number               // 0–1, e.g. 0.14 (+14%)
  confidence: 'High' | 'Medium' | 'Low'
  regime: string             // e.g. 'Bullish'
  noTradeFlag: boolean
  reasonCodes: Array<{
    label: string
    positive: boolean
  }>
}
```

Add `mockContractDetails: ContractDetail[]` array with 3 entries matching the existing mock instruments (EUR/USD, GBP/USD, USD/JPY).

The EUR/USD entry must use these exact values (the page tests assert against them):
- `economics: { cost: 42, payout: 100, breakeven: 0.42 }`
- `modelProbability: 0.68`
- `edge: 0.14`
- `recommendation: 'Take'`

---

## URL Encoding

Instrument names contain `/` which is not safe in URL path segments. Convention: replace `/` with `-` when building the URL, reverse when reading params.

- EUR/USD → `EUR-USD`
- `/signals/EUR-USD/1.0850` → instrument `EUR/USD`, strike `1.0850`

Encode in `ContractCard` when building the `to` prop. Decode in the MSW handler and `useContractDetail` hook when matching.

---

## Files

| File | Action | Purpose |
|---|---|---|
| `src/data/mockData.ts` | Modify | Add `ContractDetail` type + `mockContractDetails` array |
| `src/mocks/handlers.ts` | Modify | Add `GET /api/signals/:instrument/:strike` handler |
| `src/hooks/useContractDetail.ts` | Create | Fetch + return `{ data, loading, error }` |
| `src/hooks/useContractDetail.test.ts` | Create | 3 hook tests |
| `src/pages/ContractDetail.tsx` | Create | Layout C page component |
| `src/pages/ContractDetail.test.tsx` | Create | 5 page tests |
| `src/components/contract-card.tsx` | Modify | Wrap card in router `Link`, remove Info dialog |
| `src/components/contract-card.test.tsx` | Modify | Replace dialog tests with navigation test |
| `src/App.tsx` | Modify | Add `/signals/:instrument/:strike` route |

---

## API

### `GET /api/signals/:instrument/:strike`

- Params: `instrument` (hyphen-encoded, e.g. `EUR-USD`), `strike` (e.g. `1.0850`)
- Returns: `ContractDetail` (200) or `{ message: string }` (404 if not found)
- MSW handler decodes instrument param (replace `-` → `/`) and finds match in `mockContractDetails`

---

## Hook

```ts
// src/hooks/useContractDetail.ts
function useContractDetail(instrument: string, strike: string): {
  data: ContractDetail | null
  loading: boolean
  error: string | null
}
```

Fetches `GET /api/signals/${encodedInstrument}/${strike}`. Encodes instrument before fetch (replace `/` → `-`). Returns standard `{ data, loading, error }` shape.

---

## ContractCard Changes

- Remove the Info button and dialog
- Wrap the entire card content in a MUI `CardActionArea`
- Add `component={Link}` from react-router-dom with `to={/signals/${instrument.replace('/', '-')}/${strike}}`
- `contract-card.test.tsx`: replace the 2 dialog tests with 1 navigation test (clicking card navigates to the correct URL, verified via `MemoryRouter` + `useLocation` or `screen.getByRole('link')`)

---

## ContractDetail Page

Uses Layout C. Recommendation chip colour:
- `Take` → green (`success.main`)
- `Watch` → amber (`warning.main`)
- `Pass` → grey (`text.secondary`)

Context chips:
- Regime chip: blue tint
- Confidence chip: green tint if High, amber if Medium, grey if Low
- No-trade flag chip: red tint, only shown if `noTradeFlag === true`
- Event risk shown as a reason code (✗), not a chip — unless it triggers the no-trade flag

Edge displayed as a signed percentage: `+14%` in green, `-3%` in red. `modelProbability` also renders as a percentage: `0.68` → `68%`. Both are formatted in the page component (not in the data layer).

Back link: MUI `Link` component using `component={RouterLink}` pointing to `/signals`.

---

## Routing

```tsx
// src/App.tsx additions
import ContractDetail from './pages/ContractDetail'

// Inside <Routes>:
<Route path="/signals/:instrument/:strike" element={<ContractDetail />} />
```

Existing routes unchanged: `/` → Dashboard, `/signals` → DailySignals.

---

## Testing

### `useContractDetail.test.ts` (3 tests)

1. `returns loading:true initially` — sync check, unmount to prevent act() warning
2. `returns data after successful fetch` — waitFor loading false, check instrument + recommendation
3. `sets error on 404` — server.use override returns 404, check error not null + data null

### `ContractDetail.test.tsx` (5 tests)

All wrapped in `MemoryRouter` with `initialEntries={['/signals/EUR-USD/1.0850']}` and the matching route.

1. `renders instrument and recommendation chip` — findByText('EUR/USD'), getByText('TAKE')
2. `renders 4-up metric strip` — getByText('$42'), getByText('$100'), getByText('68%'), getByText('+14%')
3. `renders reason codes` — findByText matching a known reason label
4. `renders back link to Daily Signals` — getByRole('link', { name: /Daily Signals/i })
5. `shows error alert on fetch failure` — server.use 500 override, findByRole('alert')

### `contract-card.test.tsx` updates

Remove the 2 dialog tests. Add:
- `clicking card navigates to detail URL` — render in MemoryRouter, click card, assert URL contains instrument and strike

---

## Definition of Done

- [ ] Navigating to `/signals/EUR-USD/1.0850` renders the full Layout C page
- [ ] All 5 page sections render with mock data
- [ ] Take/Watch/Pass chip is visible and correctly coloured
- [ ] ContractCard click navigates to the detail page (no Info dialog)
- [ ] `useContractDetail` hook encapsulates fetch logic
- [ ] Tests cover rendering, navigation, and error state
- [ ] `npm run build` passes
- [ ] `npm test` passes with coverage above 80%
