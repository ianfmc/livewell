# Configuration Files Documentation

This directory contains YAML configuration files for the Nadex trading system. Each file serves a specific purpose in the system.

## Configuration Files Overview

### 1. `ticker_mappings.yaml` - **SINGLE SOURCE OF TRUTH** for Tickers ⭐
**Purpose:** Central configuration for ALL ticker information - mappings, metadata, and active status.

**Structure:**
```yaml
tickers:
  CL=F:
    display_name: CRUDE    # Nadex display name
    description: Crude Oil  # Full description
    asset_class: Futures    # Asset class
    active: true            # Whether actively traded
  # ... etc
  
test_tickers:               # Subset for diagnostic tests
  - ES=F
  - NQ=F
  # ... etc
```

**Used by:**
- `notebooks/nadex-recommendation.ipynb` - Filters to active tickers only
- `notebooks/nadex-historical.ipynb` - Uses all tickers for display name mapping

**Contains:** All 19 known Nadex tickers with full metadata (15 active, 4 inactive)

**How to add a new ticker:**
1. Add the ticker to the `tickers` section with all metadata
2. Set `active: true` if it should be traded
3. Optionally add to `test_tickers` for diagnostic testing

**How to enable/disable trading:**
- Simply change the `active` flag from `true` to `false` (or vice versa)

---

### 2. `tickers.yaml` - DEPRECATED ⚠️
**Status:** This file has been deprecated and replaced by `ticker_mappings.yaml`

**Migration:** All functionality has been moved to `ticker_mappings.yaml` as a single source of truth. This file will be removed in a future sprint.

---

### 3. `strategy.yaml` - Trading Strategy Parameters
**Purpose:** Defines RSI strategy parameters, trend filters, and guardrails.

**Key Sections:**
- `rsi`: RSI calculation parameters (period, mode, thresholds)
- `trend`: Trend filter settings (MACD or SMA)
- `guardrails`: Risk management (confidence threshold, max positions)

**Used by:**
- `src/nadex_common/strategy_rsi.py` - Core strategy implementation
- Both recommendation and historical notebooks

---

### 4. `s3.yaml` - AWS S3 Configuration
**Purpose:** Defines S3 bucket names, prefixes, and file paths.

**Key Settings:**
- `bucket`: Private bucket for results
- `public_bucket`: Nadex public data source
- `prefixes`: Directory structure in S3
- `mapping_file`: Path to contracts CSV (for strike prices)

---

### 5. `risk.yaml` - Risk Management Parameters
**Purpose:** Defines position sizing and risk limits.

---

### 6. `experiment.yaml` - Experimental Features
**Purpose:** Configuration for testing new features.

---

### 7. `anonymization.yaml` - Data Privacy
**Purpose:** Settings for anonymizing sensitive data.

---

## Configuration Relationships

### Ticker Configuration Workflow

```
┌─────────────────────────────────────────────────────────────┐
│                    TICKER CONFIGURATION                      │
└─────────────────────────────────────────────────────────────┘

1. Historical Data Processing (nadex-historical.ipynb):
   ┌──────────────────────────┐
   │  Nadex PDF Files         │
   │  (Display Names:         │
   │   "CRUDE", "US500", etc) │
   └───────────┬──────────────┘
               │
               │ Uses ticker_mappings.yaml
               ▼
   ┌──────────────────────────┐
   │  Standardized Tickers    │
   │  (CL=F, ES=F, etc)       │
   │  → Historical CSVs       │
   └──────────────────────────┘

2. Recommendation Engine (nadex-recommendation.ipynb):
   ┌──────────────────────────┐
   │  tickers.yaml            │
   │  (Active trading list)   │
   └───────────┬──────────────┘
               │
               │ Loads subset of tickers
               ▼
   ┌──────────────────────────┐
   │  Daily Recommendations   │
   │  for 15 active tickers   │
   └──────────────────────────┘
```

### Single Source of Truth Benefits

**ticker_mappings.yaml** now serves as the **SINGLE SOURCE OF TRUTH** for all ticker information:

| Aspect | Description |
|--------|-------------|
| **All Tickers** | Contains all 19 tickers with complete metadata |
| **Active Flag** | Each ticker has an `active` field to control trading |
| **Historical Processing** | Uses ALL tickers (display_name mapping) |
| **Recommendation Engine** | Filters to `active: true` tickers only (15 total) |
| **Single Update Point** | Update one file to change ticker behavior |

**Why this approach?**
- ✅ **No duplication** - One file to maintain
- ✅ **Rich metadata** - Description, asset class, display name in one place
- ✅ **Easy toggling** - Change `active` flag to enable/disable trading
- ✅ **Comprehensive** - Historical processing handles all tickers seamlessly

---

## Best Practices

### Adding a New Ticker

Add to `ticker_mappings.yaml` with complete metadata:

```yaml
tickers:
  NEWSYMBOL=X:
    display_name: NEW-DISPLAY    # Nadex display name
    description: New Asset Name   # Full description
    asset_class: Futures          # or Forex
    active: true                  # Set to false if not trading yet
```

Optionally add to test_tickers:
```yaml
test_tickers:
  - NEWSYMBOL=X
```

**That's it!** One file update handles both historical processing and trading.

### Configuration Validation

Before committing configuration changes:
1. Run the recommendation notebook to verify ticker loading
2. Check that display name mappings are correct
3. Verify strategy parameters produce reasonable signals
4. Test with diagnostic tests enabled

### Version Control

- Always commit configuration changes with descriptive messages
- Document why tickers were added/removed
- Keep configurations synchronized across environments

---

## Migration Notes

### From CSV to YAML (Sprint 2.5)

**Previous:** Tickers were hard-coded in notebooks and CSV files  
**Current:** Centralized YAML configuration files

**Benefits:**
- Single source of truth for configuration
- Easy to modify without code changes
- Better documentation with inline comments
- Consistent configuration format across the project

**Deprecated Files:**
- `notebooks/ticker_from_description.csv` - Replaced by `configs/ticker_mappings.yaml` (Sprint 2.5)
- `configs/tickers.yaml` - Consolidated into `configs/ticker_mappings.yaml` (Sprint 2.5)

---

## Troubleshooting

### "Ticker not found" errors in historical processing
- Check that the Nadex display name is in `ticker_mappings.yaml`
- Verify the mapping is correct (display name → ticker symbol)

### "No trades recommended" in recommendation engine
- Verify tickers are listed in `tickers.yaml`
- Check strategy parameters in `strategy.yaml`
- Review guardrail settings (confidence threshold, max positions)

### Configuration not loading
- Ensure YAML syntax is valid (use a YAML validator)
- Check file paths are correct relative to notebook location
- Verify file permissions allow reading

---

## Future Enhancements

Potential improvements for future sprints:
1. Add configuration validation schemas
2. Create environment-specific configs (dev/prod)
3. Add configuration versioning
4. Implement configuration hot-reloading
5. Add more ticker metadata (asset class, trading hours, etc.)
