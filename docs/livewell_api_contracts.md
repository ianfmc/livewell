# LIVEWELL API Contracts

## Purpose

This document defines the initial API contract surface for LIVEWELL. It is intended to be the bridge between:

- the React front end,
- the Python/FastAPI backend,
- scheduled jobs,
- and future agent/tool callers.

The goal is not to define every eventual endpoint. The goal is to define the **minimum stable contract set** needed to support the first production-capable paper-trading version of LIVEWELL.

## Contract Design Principles

1. **Backend is authoritative**
   - The UI should not recompute financial logic.
   - The API should return already-computed values such as implied breakeven probability, model probability, expected edge, recommendation status, and reason codes.

2. **Explainability is first-class**
   - Recommendation endpoints should return both numeric outputs and structured explanation fields.

3. **Every signal is reconstructable**
   - Responses should include model version, feature version, and run identifiers wherever relevant.

4. **No-trade is a real outcome**
   - APIs must support “pass” and “no valid setup,” not just bullish/bearish candidate lists.

5. **Contracts should be front-end friendly**
   - The first version should optimize for clarity and usability over over-generalization.

---

## API Surface Overview

Recommended first endpoint families:

1. `GET /api/v1/health`
2. `GET /api/v1/dashboard/summary`
3. `GET /api/v1/signals`
4. `GET /api/v1/signals/{signal_id}`
5. `GET /api/v1/model-health`
6. `GET /api/v1/backtests/summary`
7. `GET /api/v1/backtests/{backtest_id}`
8. `GET /api/v1/tracker/signals`
9. `GET /api/v1/markets/snapshot`
10. `POST /api/v1/options-advisor/query`

These support the first UI surfaces:
- Dashboard
- Daily Signals
- Contract Detail
- Model Health
- Backtest Results
- Signal Tracker
- Options Advisor

---

## Common Envelope Patterns

### Success response pattern

```json
{
  "status": "ok",
  "data": {}
}
```

### Error response pattern

```json
{
  "status": "error",
  "error": {
    "code": "MODEL_NOT_READY",
    "message": "No production model is available for the requested market."
  }
}
```

### Metadata pattern

Where useful, include:

```json
{
  "generated_at": "2026-04-22T13:00:00Z",
  "run_id": "run_20260422_0600_pt",
  "model_version": "rf_v2026_04_20",
  "feature_version": "features_v3"
}
```

---

## Shared Domain Objects

## MarketSnapshot

```json
{
  "market": "EUR/USD",
  "spot_price": 1.1042,
  "trend_state": "bullish",
  "momentum_state": "improving",
  "volatility_state": "normal",
  "session_context": "london_new_york_overlap",
  "event_risk_flag": false,
  "updated_at": "2026-04-22T12:55:00Z"
}
```

## ContractCandidate

```json
{
  "signal_id": "sig_20260422_eurusd_1",
  "market": "EUR/USD",
  "direction": "buy",
  "contract_type": "binary_call",
  "strike": 1.1060,
  "expiry": "2026-04-22T20:00:00Z",
  "entry_price": 46.0,
  "payout": 100.0,
  "implied_breakeven_probability": 0.46,
  "model_probability": 0.61,
  "estimated_edge": 0.15,
  "confidence_tier": "A",
  "recommendation_status": "take",
  "regime": "trend_continuation",
  "reason_codes": [
    "EMA_FAST_ABOVE_SLOW",
    "RSI_ABOVE_50",
    "MACD_HIST_RISING",
    "STRIKE_WITHIN_ATR_RANGE"
  ]
}
```

## RecommendationDecision

```json
{
  "recommendation_status": "take",
  "decision_label": "Buy EUR/USD 1.1060 EOD binary at <= 46",
  "expected_value": 15.0,
  "watch_conditions": [],
  "risk_flags": [],
  "pass_reason": null
}
```

## ModelMetadata

```json
{
  "model_version": "rf_v2026_04_20",
  "model_type": "random_forest",
  "trained_at": "2026-04-20T18:00:00Z",
  "training_window_start": "2024-01-01",
  "training_window_end": "2026-04-15",
  "feature_version": "features_v3",
  "calibration_method": "isotonic"
}
```

---

## 1. Health Endpoint

### `GET /api/v1/health`

Purpose:
- basic backend readiness,
- front-end bootstrapping,
- deployment verification.

### Response

```json
{
  "status": "ok",
  "data": {
    "service": "livewell-api",
    "environment": "dev",
    "api_version": "v1",
    "uptime_status": "healthy",
    "model_ready": true,
    "latest_run_id": "run_20260422_0600_pt",
    "timestamp": "2026-04-22T13:00:00Z"
  }
}
```

---

## 2. Dashboard Summary

### `GET /api/v1/dashboard/summary`

Purpose:
- populate the home dashboard with today’s top-level information.

### Query params
Optional:
- `market`
- `session_date`

### Response

```json
{
  "status": "ok",
  "data": {
    "generated_at": "2026-04-22T13:00:00Z",
    "run_id": "run_20260422_0600_pt",
    "market_regime_banner": "Risk-on, USD mixed, EUR/USD momentum improving",
    "opportunity_count": 3,
    "top_candidates": [
      {
        "signal_id": "sig_20260422_eurusd_1",
        "market": "EUR/USD",
        "direction": "buy",
        "strike": 1.1060,
        "expiry": "2026-04-22T20:00:00Z",
        "entry_price": 46.0,
        "model_probability": 0.61,
        "estimated_edge": 0.15,
        "recommendation_status": "take",
        "confidence_tier": "A"
      }
    ],
    "no_trade_warnings": [
      "GBP/USD blocked by event risk window"
    ],
    "performance_snapshot": {
      "last_20_signals_win_rate": 0.55,
      "last_20_signals_avg_edge": 0.08,
      "paper_trades_open": 2
    },
    "model_status_summary": {
      "current_model_version": "rf_v2026_04_20",
      "data_freshness_status": "fresh",
      "drift_warning": false
    }
  }
}
```

---

## 3. Daily Signals List

### `GET /api/v1/signals`

Purpose:
- provide the filterable signal table for the Daily Signals page.

### Query params

- `market` (optional)
- `expiry_window` (optional)
- `minimum_edge` (optional)
- `minimum_confidence` (optional)
- `recommendation_status` (optional: take/watch/pass)
- `include_event_risk` (optional boolean)
- `date` (optional)

### Response

```json
{
  "status": "ok",
  "data": {
    "generated_at": "2026-04-22T13:00:00Z",
    "run_id": "run_20260422_0600_pt",
    "items": [
      {
        "signal_id": "sig_20260422_eurusd_1",
        "market": "EUR/USD",
        "direction": "buy",
        "contract_type": "binary_call",
        "strike": 1.1060,
        "expiry": "2026-04-22T20:00:00Z",
        "entry_price": 46.0,
        "payout": 100.0,
        "implied_breakeven_probability": 0.46,
        "model_probability": 0.61,
        "estimated_edge": 0.15,
        "confidence_tier": "A",
        "recommendation_status": "take",
        "regime": "trend_continuation",
        "event_risk_flag": false,
        "has_explanation": true
      }
    ],
    "summary": {
      "total_items": 5,
      "take_count": 2,
      "watch_count": 1,
      "pass_count": 2
    }
  }
}
```

---

## 4. Signal Detail / Contract Detail

### `GET /api/v1/signals/{signal_id}`

Purpose:
- power the Contract Detail page.

### Response

```json
{
  "status": "ok",
  "data": {
    "signal_id": "sig_20260422_eurusd_1",
    "market_snapshot": {
      "market": "EUR/USD",
      "spot_price": 1.1042,
      "trend_state": "bullish",
      "momentum_state": "improving",
      "volatility_state": "normal",
      "session_context": "london_new_york_overlap",
      "event_risk_flag": false,
      "updated_at": "2026-04-22T12:55:00Z"
    },
    "contract_candidate": {
      "market": "EUR/USD",
      "direction": "buy",
      "contract_type": "binary_call",
      "strike": 1.1060,
      "expiry": "2026-04-22T20:00:00Z",
      "entry_price": 46.0,
      "payout": 100.0,
      "implied_breakeven_probability": 0.46,
      "model_probability": 0.61,
      "estimated_edge": 0.15,
      "confidence_tier": "A",
      "recommendation_status": "take",
      "regime": "trend_continuation",
      "reason_codes": [
        "EMA_FAST_ABOVE_SLOW",
        "RSI_ABOVE_50",
        "MACD_HIST_RISING",
        "STRIKE_WITHIN_ATR_RANGE"
      ]
    },
    "decision": {
      "recommendation_status": "take",
      "decision_label": "Buy EUR/USD 1.1060 EOD binary at <= 46",
      "expected_value": 15.0,
      "watch_conditions": [],
      "risk_flags": [],
      "pass_reason": null
    },
    "feature_snapshot": {
      "ema_fast": 1.1038,
      "ema_slow": 1.1027,
      "rsi_14": 56.3,
      "macd_line": 0.0008,
      "macd_signal": 0.0005,
      "macd_hist": 0.0003,
      "atr_14": 0.0047
    },
    "historical_analogs": [
      {
        "date": "2026-03-12",
        "market": "EUR/USD",
        "similarity_score": 0.87,
        "outcome": "win"
      }
    ],
    "model_metadata": {
      "model_version": "rf_v2026_04_20",
      "model_type": "random_forest",
      "trained_at": "2026-04-20T18:00:00Z",
      "training_window_start": "2024-01-01",
      "training_window_end": "2026-04-15",
      "feature_version": "features_v3",
      "calibration_method": "isotonic"
    }
  }
}
```

---

## 5. Model Health

### `GET /api/v1/model-health`

Purpose:
- populate the Model Health page.

### Query params
Optional:
- `market`
- `model_version`

### Response

```json
{
  "status": "ok",
  "data": {
    "current_model_version": "rf_v2026_04_20",
    "model_type": "random_forest",
    "trained_at": "2026-04-20T18:00:00Z",
    "feature_version": "features_v3",
    "data_freshness_status": "fresh",
    "validation_metrics": {
      "auc": 0.61,
      "brier_score": 0.22,
      "log_loss": 0.64,
      "calibration_error": 0.03
    },
    "drift_indicators": {
      "feature_drift_warning": false,
      "prediction_distribution_warning": false
    },
    "feature_availability": {
      "missing_required_features": [],
      "optional_feature_gaps": ["news_sentiment"]
    },
    "recent_runs": [
      {
        "run_id": "run_20260422_0600_pt",
        "status": "completed",
        "generated_at": "2026-04-22T13:00:00Z"
      }
    ]
  }
}
```

---

## 6. Backtest Summary

### `GET /api/v1/backtests/summary`

Purpose:
- show available backtest runs and topline metrics.

### Query params
Optional:
- `market`
- `model_version`

### Response

```json
{
  "status": "ok",
  "data": {
    "items": [
      {
        "backtest_id": "bt_20260420_rf_v3",
        "label": "RF v3 — walk-forward OOS",
        "market_scope": ["EUR/USD", "GBP/USD"],
        "date_range_start": "2025-01-01",
        "date_range_end": "2026-04-15",
        "signal_count": 184,
        "win_rate": 0.54,
        "avg_edge": 0.07,
        "max_drawdown": 0.11,
        "pass_rate": 0.63
      }
    ]
  }
}
```

---

## 7. Backtest Detail

### `GET /api/v1/backtests/{backtest_id}`

Purpose:
- populate the Backtest Results detail page.

### Response

```json
{
  "status": "ok",
  "data": {
    "backtest_id": "bt_20260420_rf_v3",
    "summary_metrics": {
      "signal_count": 184,
      "win_rate": 0.54,
      "avg_edge": 0.07,
      "avg_expected_value": 6.2,
      "max_drawdown": 0.11,
      "pass_rate": 0.63
    },
    "breakdowns": {
      "by_market": [
        {"market": "EUR/USD", "win_rate": 0.56, "signal_count": 110},
        {"market": "GBP/USD", "win_rate": 0.50, "signal_count": 74}
      ],
      "by_regime": [
        {"regime": "trend_continuation", "win_rate": 0.59, "signal_count": 90},
        {"regime": "event_risk", "win_rate": 0.42, "signal_count": 18}
      ],
      "by_expiry_window": [
        {"expiry_window": "eod", "win_rate": 0.55, "signal_count": 140}
      ]
    },
    "charts": {
      "equity_curve_points": [
        {"x": "2025-01-01", "y": 0.0},
        {"x": "2025-01-15", "y": 12.5}
      ],
      "calibration_curve_points": [
        {"predicted_bin": 0.4, "observed_rate": 0.38},
        {"predicted_bin": 0.6, "observed_rate": 0.58}
      ]
    }
  }
}
```

---

## 8. Signal Tracker

### `GET /api/v1/tracker/signals`

Purpose:
- support paper-trading review and outcome tracking.

### Query params
Optional:
- `market`
- `date_start`
- `date_end`
- `taken_status` (taken/skipped/all)

### Response

```json
{
  "status": "ok",
  "data": {
    "items": [
      {
        "signal_id": "sig_20260422_eurusd_1",
        "market": "EUR/USD",
        "generated_at": "2026-04-22T13:00:00Z",
        "recommendation_status": "take",
        "taken_status": "paper_taken",
        "entry_price": 46.0,
        "model_probability": 0.61,
        "estimated_edge": 0.15,
        "outcome_status": "resolved",
        "outcome": "win",
        "actual_settlement_value": 100.0,
        "notes": null
      }
    ],
    "summary": {
      "total_tracked": 47,
      "paper_taken_count": 20,
      "skipped_count": 27,
      "resolved_count": 38
    }
  }
}
```

---

## 9. Market Snapshot List

### `GET /api/v1/markets/snapshot`

Purpose:
- provide current market state for dashboard banners and filters.

### Query params
Optional:
- `market`

### Response

```json
{
  "status": "ok",
  "data": {
    "items": [
      {
        "market": "EUR/USD",
        "spot_price": 1.1042,
        "trend_state": "bullish",
        "momentum_state": "improving",
        "volatility_state": "normal",
        "session_context": "london_new_york_overlap",
        "event_risk_flag": false,
        "updated_at": "2026-04-22T12:55:00Z"
      },
      {
        "market": "GBP/USD",
        "spot_price": 1.2874,
        "trend_state": "neutral",
        "momentum_state": "mixed",
        "volatility_state": "elevated",
        "session_context": "london_new_york_overlap",
        "event_risk_flag": true,
        "updated_at": "2026-04-22T12:55:00Z"
      }
    ]
  }
}
```

---

## 10. Options Advisor

### `POST /api/v1/options-advisor/query`

Purpose:
- provide structured advisory responses for guided reasoning.
- this can later sit behind a richer conversational or agentic layer.

### Request

```json
{
  "market": "EUR/USD",
  "question_type": "should_i_consider_this_contract",
  "strike": 1.1060,
  "expiry": "2026-04-22T20:00:00Z"
}
```

### Response

```json
{
  "status": "ok",
  "data": {
    "answer_type": "structured_advice",
    "recommendation_status": "take",
    "summary": "This contract is viable because model probability exceeds breakeven and the setup passes technical filters.",
    "key_points": [
      "Trend is bullish",
      "Momentum is improving",
      "Strike is within ATR-adjusted feasible range",
      "No event-risk block is active"
    ],
    "risk_flags": [],
    "linked_signal_id": "sig_20260422_eurusd_1"
  }
}
```

---

## Recommended FastAPI Schema Strategy

Use explicit Pydantic models for:

- `HealthResponse`
- `DashboardSummaryResponse`
- `SignalListResponse`
- `SignalDetailResponse`
- `ModelHealthResponse`
- `BacktestSummaryResponse`
- `BacktestDetailResponse`
- `TrackerSignalsResponse`
- `MarketSnapshotResponse`
- `OptionsAdvisorRequest`
- `OptionsAdvisorResponse`

This keeps:
- front-end contracts stable,
- backend validation explicit,
- and future agent/tool integrations safe.

---

## Recommended Versioning Policy

- Prefix all routes with `/api/v1`
- Avoid breaking field renames inside v1 once UI is wired
- Add fields conservatively
- If major shape changes are needed later, create `/api/v2`

---

## Suggested Next Implementation Order

1. implement `/api/v1/health`
2. implement `/api/v1/dashboard/summary`
3. implement `/api/v1/signals`
4. implement `/api/v1/signals/{signal_id}`
5. implement `/api/v1/model-health`
6. implement `/api/v1/backtests/summary`
7. implement `/api/v1/tracker/signals`
8. implement `/api/v1/markets/snapshot`
9. implement `/api/v1/options-advisor/query`

That order matches the likely UI build pressure.

---

## Bottom Line

These contracts are designed to make LIVEWELL:

- easier for Claude Code to implement,
- easier for the React app to consume,
- easier to evolve into a tracked, explainable paper-trading system,
- and easier to expose later to agents without changing the core backend authority.
