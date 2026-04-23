# Sprint 2.5 — Monorepo Consolidation  
*Planned: TBD · Actual: TBD*

## Sprint Goal
Consolidate all Nadex repositories into a single **livewell-nadex** monorepo.  
Create the shared library `src/nadex_common/`, move notebooks into a unified `notebooks/` folder, update imports, and ensure full functional parity with the prior multi‑repo layout.

---

## User Stories Targeted
- **B‑1 (System Developer):** Refactor toward a portable core with a shared library + centralized structure.
- **C‑1 (Researcher):** Maintain correct run logging paths after consolidation.
- **B‑2 (System Developer):** Ensure all configuration remains externalized and stable post‑migration.

---

## Definition of Done
- New monorepo structure created:
  ```
  livewell-nadex/
    src/nadex_common/
      __init__.py
      strategy_rsi.py
      utils_s3.py
    notebooks/
      nadex-results.ipynb
      nadex-recommendation.ipynb
      nadex-backtesting.ipynb
    configs/
      s3.yaml
      strategy.yaml
    sprints/
      sprint_1.md
      sprint_2.md
      sprint_2_5.md
      sprint_3.md
  ```
- Shared library functions imported using:
  ```python
  from nadex_common import generate_rsi_signals, append_runlog_s3
  ```
- No behavior changes from migration (all notebooks run identically).
- Old repos marked read‑only or README updated to point to the monorepo.
- Canvas updated to reflect the new layout.

---

## Backlog (Sprint 2.5 Tasks)
1. Create `livewell-nadex` repo with target folder structure.
2. Move `strategy_rsi.py` and `utils_s3.py` into `src/nadex_common/`.
3. Add minimal `__init__.py` exporting shared functions.
4. Move all three notebooks into `notebooks/`.
5. Update notebook imports to use `nadex_common`.
6. Move `s3.yaml` and `strategy.yaml` into a shared `configs/` folder.
7. Create `sprints/` folder and add `sprint_1`, `sprint_2`, `sprint_2_5`, and `sprint_3`.
8. Update main README to reflect monorepo layout.
9. Mark legacy repos read‑only or point them to the monorepo.
10. Validate that all notebooks run identically after consolidation.

---

## Notes
- Sprints 1 and 2 are fully complete and archived.
- Sprint 2.5 establishes the long‑term repo foundation.
- Sprint 3 will build directly on this structure for bucket guards + backtesting baseline.
