# LIVEWELL / Nadex — Monorepo

This repository contains the **LIVEWELL Nadex workflow**:

- Historical results extraction from Nadex Daily Results PDFs
- Daily recommendation generation based on technical indicators (e.g., RSI)
- Backtesting of strategies to evaluate performance and choose parameters

It consolidates prior repos (`Nadex-results`, `Nadex-recommendation`, `Nadex-backtesting`) into a single monorepo so that shared code, configuration, and documentation live in one place.

---

## Repository Layout

```text
livewell-nadex/
  pyproject.toml        # project definition (for pip install -e .)
  requirements.txt      # Python dependencies
  .gitignore            # ignore rules for Python, notebooks, etc.
  README.md             # this file

  src/
    nadex_common/
      __init__.py
      strategy_rsi.py   # shared RSI/indicator logic
      utils_s3.py       # shared S3 helpers, run log append, etc.

  notebooks/
    nadex-results.ipynb         # historical results extraction
    nadex-recommendation.ipynb  # daily recommendation pipeline
    nadex-backtesting.ipynb     # backtesting / research

  configs/
    s3.yaml             # bucket, prefixes, mapping file
    strategy.yaml       # RSI modes, thresholds, guardrails

  sprints/
    sprint_1.md         # Historical Results MVP
    sprint_2.md         # Config + shared lib + recommendation
    sprint_2_5.md       # Monorepo consolidation
    sprint_3.md         # Bucket guards + backtesting baseline
```

---

## Getting Started

### 1. Create and activate a virtual environment

You can use `venv`, `conda`, or any other tool. Example with `python -m venv`:

```bash
python -m venv .venv
source .venv/bin/activate  # on macOS/Linux
# .venv\Scripts\activate  # on Windows
```

### 2. Install dependencies

If you are using `requirements.txt`:

```bash
pip install -r requirements.txt
```

### 3. Install the project in editable mode

From the repository root:

```bash
pip install -e .
```

This makes the `nadex_common` package importable from notebooks and scripts.

---

## Notebooks

- **`notebooks/nadex-results.ipynb`**  
  Extracts and normalizes Nadex Daily Results PDFs and writes cleaned CSVs to S3.  
  Uses configuration from `configs/s3.yaml` and a mapping file to standardize columns.

- **`notebooks/nadex-recommendation.ipynb`**  
  Loads cleaned historical data, computes indicators (RSI, trend filters), and emits daily recommendations.  
  Uses shared logic from `src/nadex_common/strategy_rsi.py` and runtime settings from `configs/strategy.yaml`.

- **`notebooks/nadex-backtesting.ipynb`**  
  Reuses the same shared strategy logic to backtest different RSI modes/thresholds and fee assumptions.  
  Produces win rate, gross/net P&L, and summary artifacts to S3.

Each notebook is designed as a **scriptable workflow** rather than a long-lived analysis scratchpad. The goal is to keep the logic refactor-friendly so that future services/agents can call the same shared functions.

---

## Configuration

Configuration is externalized to keep code portable and environment-agnostic:

- **`configs/s3.yaml`**  
  - `bucket`: primary S3 bucket for private artifacts  
  - `public_bucket` (optional): bucket for public/HTML reports  
  - `prefixes`: subfolder prefixes (historical, recommendations, reports, logs, etc.)  
  - `mapping_file`: key/path for any symbol or ticker mapping CSVs

- **`configs/strategy.yaml`**  
  - RSI mode: `centerline` or `reversal`  
  - RSI thresholds for entries/exits  
  - Guardrails: confidence threshold, max positions per day, etc.

The goal is that the **same code** can run in different environments (local, SageMaker, containers) by only changing config files.

---

## Shared Library (`nadex_common`)

The `src/nadex_common` package contains shared logic, for example:

- **`strategy_rsi.py`**  
  - RSI calculation and signal generation  
  - Trend filters (MACD/SMA)  
  - Parameterized modes (centerline/reversal) driven by `strategy.yaml`

- **`utils_s3.py`**  
  - S3 helpers for reading/writing DataFrames and text  
  - Run-log append helpers for `logs/run_log.csv`  
  - Safe wrappers around bucket/prefix access (guards added in later sprints)

By installing the repo in editable mode (`pip install -e .`), all notebooks and future services can import these functions without manipulating `sys.path`.

---

## Sprints

Track the evolution of the project in the `sprints/` folder:

- **`sprint_1.md`** — Historical Results MVP (Nadex-results)  
- **`sprint_2.md`** — Config + shared library + recommendation pipeline  
- **`sprint_2_5.md`** — Monorepo consolidation and `nadex_common` setup  
- **`sprint_3.md`** — Bucket guards + backtesting baseline
- **`sprint_3.5.md`** — KPI Reporting (HTML dashboard, S3 persistence)

Each sprint file includes:

- Sprint goal  
- User stories targeted  
- Definition of done  
- End-of-sprint status and notes

This acts as a NATOPS-style logbook for how the LIVEWELL Nadex system changes over time.

---

## Next Steps

- Proceed to **Sprint 4** for ML feature engineering and out-of-sample validation.
