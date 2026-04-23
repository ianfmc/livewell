# Sprint 3.5 — KPI Reporting (1 week)

**Goal:**  
Deliver User Story **A-3** by producing a concise KPI report (win rate, net P&L, drawdown) with notebook output and an S3-exported summary artifact.

---

## User Story Targeted
- **A-3 (Product Owner):** View concise results (win rate, net P&L, drawdown) in one place.  
  *Success criteria:* Summary cell/notebook section renders KPIs over a selected date range and uploads a summary CSV to S3.

---

## Definition of Done
- A single consolidated KPI block exists in the notebook showing:  
  - Win rate  
  - Gross & net P&L  
  - Max drawdown  
- KPI block renders cleanly and works for any valid date range.  
- KPI summary is exported to S3 under:  
  `reports/<date>/summary.csv`  
- Notebook includes minimal visualization (table or markdown).  
- RUNBOOK.md is updated with instructions for KPI reporting and S3 export.  
- Validation performed on at least two date windows.

---

## 1-Week Plan (5 × 30-minute tasks)

### **Week Plan / Task List**

1. Build consolidated KPI reporting block (win rate, net P&L, drawdown) in notebook.  
2. Validate KPI correctness across multiple date ranges.  
3. Export KPI summary to S3 under `reports/<date>/summary.csv`.  
4. Add minimal KPI visualization (table or markdown block).  
5. Update RUNBOOK.md with KPI reporting instructions.

---

## Notes
- This sprint isolates A-3 to avoid expanding Sprint 4.  
- KPI work supports ML feature evaluation later in Sprint 4.  
- Output will become part of the ML-vs-RSI comparison workflow in future sprints.
