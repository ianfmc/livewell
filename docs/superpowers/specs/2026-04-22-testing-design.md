# Testing Design — LIVEWELL UI

**Date:** 2026-04-22
**Status:** Approved

---

## Goal

Add a test suite to the LIVEWELL UI so that hooks and components are verified against their contracts before every merge. The suite must be fast enough to run on every commit and honest enough to catch real regressions.

---

## Stack

| Tool | Role |
|---|---|
| Vitest | Test runner (Vite-native, same transforms as the app) |
| @testing-library/react | Component rendering and DOM queries |
| @testing-library/user-event | Simulated user interactions (clicks, typing) |
| @testing-library/jest-dom | Extended matchers (toBeInTheDocument, toHaveTextContent, etc.) |
| @vitest/coverage-v8 | Istanbul-compatible coverage reports |
| MSW (already installed) | HTTP interception via Node server — reuses existing handlers |

---

## Architecture

### MSW in tests

MSW has two runtimes that serve the same purpose in different environments:

- `msw/browser` — service worker, used in the running dev app (`src/mocks/browser.ts`, already exists)
- `msw/node` — intercepts Node's `fetch`, used in tests (`src/mocks/server.ts`, new)

Both import from the same `src/mocks/handlers.ts`. This means mock API responses are defined once and shared between dev and test environments.

### Setup file

`src/test/setup.ts` runs before every test file. It:
1. Imports `@testing-library/jest-dom` to register extended matchers globally
2. Calls `server.listen()` before all tests, `server.resetHandlers()` after each test, and `server.close()` after all tests

`resetHandlers()` after each test ensures that a test which overrides a handler (e.g. to simulate a 500 error) cannot leak into the next test.

### Vite config

The `test` block added to `vite.config.ts`:
- `environment: 'jsdom'` — provides a browser-like DOM in Node (equivalent to Angular's JSDOM TestBed environment)
- `setupFiles: ['./src/test/setup.ts']` — runs the setup file before each test file
- `globals: true` — makes `describe`, `it`, `expect` available without explicit imports (matches Mocha's global style)

---

## File Structure

Test files live next to the code they test:

```
src/
  hooks/
    useSignals.ts
    useSignals.test.ts
    useDashboard.ts
    useDashboard.test.ts
  components/
    contract-card.tsx
    contract-card.test.tsx
  pages/
    Dashboard.tsx
    Dashboard.test.tsx
    DailySignals.tsx
    DailySignals.test.tsx
  mocks/
    handlers.ts              (unchanged)
    browser.ts               (unchanged)
    server.ts                (new — MSW Node server)
  test/
    setup.ts                 (new — jest-dom + MSW lifecycle)
```

---

## Test Specifications

### `useSignals.test.ts`

| Test | Assertion |
|---|---|
| returns loading:true initially | `result.current.loading === true` before fetch resolves |
| populates data after successful fetch | `result.current.data` has length matching mock handler; `loading === false`; `error === null` |
| sets error on failed fetch | MSW returns HTTP error; `error` is non-null; `data` is empty array; `loading === false` |

### `useDashboard.test.ts`

| Test | Assertion |
|---|---|
| returns loading:true initially | `result.current.loading === true` |
| populates data after successful fetch | `result.current.data` is non-null and matches mock shape; `loading === false` |
| sets error on failed fetch | MSW returns HTTP error; `error` is non-null; `data === null` |

### `contract-card.test.tsx`

| Test | Assertion |
|---|---|
| renders instrument, strike, expiry, status | All four values visible via `screen.getByText` |
| Info button opens detail dialog | Click Info → dialog with instrument name appears |
| dialog closes on Close button | Click Close → dialog no longer in document |

### `Dashboard.test.tsx`

| Test | Assertion |
|---|---|
| shows spinner while loading | `screen.getByRole('progressbar')` present before fetch resolves |
| renders Market Conditions section | `screen.findByText('Market Conditions')` resolves after load |
| renders Opportunity Summary section | Total, passing, and review counts visible |
| renders Top Candidates section | Candidate instruments visible |
| renders Model Health section | Training date and status visible |
| shows no-trade warning when passing is zero | Override handler to return `passing: 0`; Alert with "No valid setups" appears |
| shows error alert on fetch failure | MSW returns error; `screen.findByRole('alert')` resolves |

### `DailySignals.test.tsx`

| Test | Assertion |
|---|---|
| renders contract cards after load | Mock data instruments appear in the document |
| shows spinner while loading | `screen.getByRole('progressbar')` present initially |
| status filter reduces visible cards | Change filter to "Open" → only Open cards remain visible |
| shows error alert on fetch failure | MSW returns error; error alert appears |

---

## npm Scripts

```json
"test": "vitest",
"test:coverage": "vitest run --coverage"
```

`npm test` runs in watch mode (reruns on file save — useful during development).
`npm run test:coverage` runs once and outputs coverage to `coverage/`.

---

## Coverage Target

80% line coverage on `src/hooks/` and `src/components/` and `src/pages/`. Enforced via Vitest's `coverage.thresholds` config. The remaining 20% is typically difficult-to-trigger error branches that are not worth the test complexity at this stage.

---

## What is explicitly not tested

- `App.tsx` routing and navigation — better verified by running the app
- `ThemeProvider` — pure infrastructure with no product logic
- `src/mocks/` files — test infrastructure, not product code
- `src/data/` mock data files — static data, no logic to test
