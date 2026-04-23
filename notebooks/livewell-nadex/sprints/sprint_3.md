# Sprint 3 — Bucket Guards + Backtesting Baseline (3 weeks)

**Goal:**  
1) Add runtime S3 bucket guards across *Nadex-results* and *Nadex-recommendation*.  
2) Stand up the **A‑2 backtesting baseline** using the shared library (`lib/strategy_rsi.py`) so we can compare RSI modes/thresholds and pick defaults for daily use.

---

## User Stories Targeted
- **A‑2 (Researcher):** Backtest daily contract strategy with fees and produce a baseline report.  
- **C‑1 (Researcher):** Keep run metadata logging intact during backtest runs.  
- **B‑1 (System Developer):** Small refactors to keep shared lib functions pure/testable (only as needed for A‑2 and guards).

---

## Definition of Done
- Bucket guard in place in both repos: all S3 reads/writes call  
  `assert_allowed_bucket(cfg['bucket'])` (and `public_bucket` where applicable).  
- Grep shows **no hard‑coded bucket names** in either repo (outside `configs/`).  
- Backtesting notebook uses shared `lib/strategy_rsi.py` over the same instruments and period.  
- Outputs include: **win rate**, **gross vs net P&L** (with \$1/side fees), **sample trade log**.  
- Backtest artifact saved to S3 (CSV + optional HTML summary) with dated key.  
- Run log rows appended for each backtest execution.

---

## 3‑Week Plan (15 × 30‑minute tasks)

### **Week 1 — Guards & Wiring**
1. Add/import `assert_allowed_bucket` in **Nadex-results** and wrap all S3 puts/gets.  
2. Add/import `assert_allowed_bucket` in **Nadex-recommendation** and wrap all S3 puts/gets.  
3. Grep both repos for literal buckets/prefixes; replace with config values.  
4. Perform smoke runs on both notebooks (small date window); confirm run_log updated.  
5. Update both RUNBOOK.md files with a “Bucket guard active” note.

---

### **Week 2 — Backtesting Baseline (A‑2)**
6. Create/refresh a **Backtest** notebook or section that imports `generate_rsi_signals` from `lib`.  
7. Add \$1/side fee model and compute **gross** and **net** P&L.  
8. Produce **win rate** + **PnL summary** for a recent 30‑day window and upload CSV to S3.  
9. Create sample trade log (10–20 rows) and upload to S3; include in HTML summary.  
10. Append run log entries; validate `files_processed/skipped/error` counters.

---

### **Week 3 — Parameter Sweep & Defaults**
11. Run small RSI grid (centerline: 45/50/55, reversal: 25/30/35 & 65/70/75).  
12. Summarize grid results into a single CSV (win rate + net P&L).  
13. Select **default parameters** for daily use; update `configs/strategy.yaml`.  
14. Light refactors: ensure lib functions stay pure; add/adjust unit tests.  
15. Sprint review: validate artifacts and update Canvas + sprints folder.

---

## Notes
- Sprints 1 & 2 completed: A‑1, B‑2, C‑1, C‑2, E‑2.  
- Next natural focus: **A‑3** (PO daily KPI report) or **D‑1** (typed I/O schema).  
