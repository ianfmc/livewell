# Sprint 4A — Feature Engineering & Dataset Creation

**Sprint Duration:** 2 weeks

## Sprint Goal
Create a deterministic, typed feature pipeline and produce a high-quality ML-ready
training dataset stored in S3. This sprint intentionally stops before model training.

---

## User Stories Targeted
- **D-1 (Developer):** Define typed I/O schemas for Prices → Features → Signals → P&L  
- **F-1 (Platform Engineer):** Establish clean, service-ready feature boundaries

---

## Definition of Done
- Feature schema defined and validated (`features.yaml`)
- Deterministic feature pipeline implemented (`features.py`)
- Normalization and rolling statistics added
- Supervised target labels defined
- ML-ready dataset generated and validated
- Data quality checks in place (NaNs, warm-up handling, alignment)
- Feature and label datasets written to S3 under `features/`
- RUNBOOK.md updated with feature and dataset generation steps
- Repository tagged `sprint-4a`

---

## Backlog
1. Define full feature schema (`features.yaml`)
2. Implement deterministic feature extraction pipeline (`features.py`)
3. Add normalization utilities (z-score, min-max, rolling)
4. Implement ATR-like volatility and rolling window statistics
5. Define supervised target labels
6. Build ML training dataset generator
7. Add data quality checks
8. Write feature and label datasets to S3
9. Update RUNBOOK.md
10. Sprint review and version tagging

---

## Notes
- This sprint produces the **only input** for Sprint 4B (modeling).
- No ML training occurs in this sprint.
- Output artifacts must be reusable without modification by future services.
