# LIVEWELL

## Overview

LIVEWELL is a decision-support system for trading NADEX binary options.

The goal is to move from:

* raw market data
  → to structured signals
  → to evaluated opportunities
  → to disciplined decision-making

This project will evolve from a front-end prototype into a full system with:

* backend APIs
* machine learning models
* and eventually agent-driven workflows

---

## Current Status

```
[✓] UI scaffold
[✓] Global state (theme)
[✓] First real product page
[✓] API integration (MSW)
[ ] Backend extraction
[ ] ML pipeline
[ ] Agents
```

---

## Tech Stack

### Frontend

* React (TypeScript)
* Vite
* Material UI (MUI)

### State Management

* React Context (ThemeProvider)

### Data (current)

* Mock data (local)

---

## Project Structure

```
src/
  components/
    contract-card.tsx
    mode-toggle.tsx
    theme-provider.tsx
  data/
    mockData.ts
  pages/
    DailySignals.tsx
  App.tsx
```

---

## Development

### Install

```
npm install
```

### Run locally

```
npm run dev
```

Then open:

```
http://localhost:5173
```

---

## Guiding Principles

* Build **product-first**, not architecture-first
* Always have a **clear next executable step**
* Prefer **simple working code** over premature abstraction
* Separate **UI, API, and ML concerns** cleanly
* Design for **eventual portability and decoupling**

---

## Next Step

Replace mock data with real FastAPI endpoints and begin backend skeleton (Phase 1B).

---

## Long-Term Vision

LIVEWELL will evolve into:

* A full decision system for NADEX trading
* With explainable signals and edge calculations
* Backed by ML models and historical validation
* Extended with agent-based workflows

---

## Notes

This project is intentionally built incrementally to maintain momentum and clarity.

When returning after time away:

1. Check **Current Status**
2. Execute **Next Step**
3. Avoid jumping ahead
