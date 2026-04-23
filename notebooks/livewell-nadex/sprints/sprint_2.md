# Sprint 2 — Configuration, Shared Library, and Recommendation Pipeline  
*Planned: Oct 1–Oct 8, 2025 · Actual: Oct 1–Oct 9, 2025*

## Sprint Goal
Align **Nadex-recommendation** with Sprint 1 architecture: externalize configuration, add a shared library, add run logging, remove hard‑coded S3 values, and prepare for Sprint 3 backtesting.

## User Stories Targeted
- **B-2 (Externalize configuration):** move all buckets, prefixes, mapping file paths, and strategy parameters into `configs/s3.yaml` and `configs/strategy.yaml`.
- **C-1 (Run metadata logging):** mirror Sprint 1’s run log structure in the recommendation repo.
- **C-2 (Operator metrics):** capture baseline runtime metrics in notebook outputs.
- **B-1 (Refactor for purity):** create shared `lib/` for strategy + S3 utilities.

## Definition of Done
- `configs/s3.yaml` exists with `bucket`, `public_bucket`, `prefixes`, and `mapping_file`.
- `configs/strategy.yaml` exists with RSI mode, thresholds, and guardrails.
- Shared library implemented: `lib/strategy_rsi.py`, `lib/utils_s3.py`.
- Notebook imports shared library and no longer contains duplicated strategy/S3 logic.
- All bucket names sourced from `configs/*.yaml` (no literals in code).
- Run log append helper added; writes entries to `logs/run_log.csv` in S3.
- Requirements updated; repo matches canonical format (README, LICENSE, notebooks/, configs/, lib/, tests/).

## Status (End of Sprint)
- ✅ Config loader present (`load_config()`).
- ✅ Run log helper added (`append_runlog_s3()` from shared lib).
- ✅ Report artifact cell added (RSI summary + recommendation summary).
- ✅ Strategy config externalized in `configs/strategy.yaml` (including guardrail params for confidence and max positions).
- ✅ S3 paths externalized in `configs/s3.yaml`.
- ✅ Shared library implemented (`lib/strategy_rsi.py`, `lib/utils_s3.py`).
- ⚠️ Runtime bucket guard deferred to Sprint 3 (moved deliberately to next sprint).

## Backlog
*None — all Sprint 2 scope complete; remaining guard work explicitly moved to Sprint 3.*

## Sprint 2 Notes
- Shared library + config pattern is now in place for both **Nadex-results** and **Nadex-recommendation**.
- Recommendation notebook uses a shared `generate_rsi_signals` implementation.
- Guardrails (confidence threshold, max positions per day) are now driven from `configs/strategy.yaml`.
