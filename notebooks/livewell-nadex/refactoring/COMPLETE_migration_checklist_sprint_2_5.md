# LIVEWELL / Nadex — Monorepo Migration Checklist (Sprint 2.5)

Use this checklist as you move from the multi-repo setup into the `livewell-nadex` monorepo.  
You can update this file as you go — check off items, add notes, or record small deviations.

---

## 1. Monorepo Bootstrap

- [X] Create new repo: `livewell-nadex` on GitHub.
- [X] Clone locally and create base folder structure:
  - [X] `src/nadex_common/`
  - [X] `notebooks/`
  - [X] `configs/`
  - [X] `sprints/`

- [X] Add `pyproject.toml` to repo root.
- [X] Add `requirements.txt` (copy from current primary repo or consolidate later).
- [X] Add `.gitignore` tailored for Python + notebooks.

---

## 2. Shared Library (`nadex_common`)

- [X] Copy `strategy_rsi.py` from existing `lib/` into `src/nadex_common/strategy_rsi.py`.
- [X] Copy `utils_s3.py` from existing `lib/` into `src/nadex_common/utils_s3.py`.
- [X] Create `src/nadex_common/__init__.py` that re-exports core functions:
  - [X] `generate_rsi_signals`
  - [X] `append_runlog_s3`
  - [X] `save_dataframe_to_s3`, `save_text_to_s3` (if present)
- [X] From repo root, run `pip install -e .` to enable imports:
  ```bash
  pip install -e .
  ```

---

## 3. Notebooks

- [X] Copy `nadex-results.ipynb` into `notebooks/`.
- [X] Copy `nadex-recommendation.ipynb` into `notebooks/`.
- [X] Copy `nadex-backtesting.ipynb` into `notebooks/`.

- [X] In each notebook, update imports to use `nadex_common` instead of local `lib/`:
  - [X] Remove any `sys.path.append("../lib")` or similar.
  - [X] Replace with:
    ```python
    from nadex_common import generate_rsi_signals, append_runlog_s3
    ```

---

## 4. Configuration

- [X] Create `configs/` folder in the monorepo.
- [X] Copy `s3.yaml` into `configs/s3.yaml`.
- [X] Copy `strategy.yaml` into `configs/strategy.yaml`.
- [X] Verify notebooks load config from `configs/*.yaml` using the existing loader.

---

## 5. Sprints & Documentation

- [X] Create `sprints/` folder.
- [X] Add existing sprint files:
  - [X] `sprint_1.md`
  - [X] `sprint_2.md`
  - [X] `sprint_2_5.md`
  - [X] `sprint_3.md`
- [X] Add root `README.md` explaining the new structure (this file).

- [X] Optional: update the LIVEWELL Canvas to reference the new monorepo structure and URL.

---

## 6. Validation

For each notebook:

- [X] `notebooks/nadex-results.ipynb` runs end-to-end using `configs/s3.yaml`:
  - [X] Reads PDFs / historical inputs.
  - [X] Writes cleaned CSVs to the correct S3 prefixes.
  - [X] Updates manifest and run log as before.

- [X] `notebooks/nadex-recommendation.ipynb` runs end-to-end:
  - [X] Reads cleaned history from S3.
  - [X] Uses `nadex_common.generate_rsi_signals` correctly.
  - [X] Writes recommendation artifacts and summary.
  - [X] Appends to run log.

- [ ] `notebooks/nadex-backtesting.ipynb` runs correctly (once wired to shared lib in Sprint 3).

---

## 7. Legacy Repos

- [X] In `Nadex-results` repo:
  - [X] Update `README` to point to `livewell-nadex`.
  - [X] Optionally mark the repo as archived in GitHub settings.

- [X] In `Nadex-backtesting` repo:
  - [X] Update `README` to point to `livewell-nadex`.
  - [X] Optionally mark the repo as archived.

---

## Notes / Variations

Use this space to capture any deviations from the plan (for example, if you decide to keep one repo active as a staging area or you introduce additional shared modules):

