# Sprint 1 — Historical Results MVP  
*Planned: Sep 15–Sep 19, 2025 · Actual: Sep 15–Sep 22, 2025*

## Sprint Goal
From **Nadex-results**, extract & normalize historical Nadex Daily Results PDFs and write clean CSVs to S3, with a processed-manifest and a simple run log. This becomes the upstream source for **Nadex-recommendation**.

## User Stories Targeted
- **B-2 (Externalize configuration):** `s3.yaml`, mapping file path.  
- **C-1 (Run metadata logging):** append `logs/run_log.csv` on S3.  
- **D-1 (Typed interfaces/schemas):** consistent cleaned columns.  
- **E-2 (Docs/runbook):** steps & aborts.

## Definition of Done
- Notebook reads `configs/s3.yaml` (no hard‑coded bucket names).
- For each PDF in the date window, a **cleaned CSV** is uploaded to S3 under the configured `historical/` prefix.
- A **processed manifest** (e.g., `manifests/processed_files.json`) is updated to avoid reprocessing.
- `logs/run_log.csv` on S3 is appended with `date,start_time,end_time,status,files_processed,files_skipped,files_error,run_id,notes`.
- Columns standardized: `Date, Exp Value, Strike Price, In the Money, Ticker, exp time, ...` (as produced by the notebook’s transforms).

## Status (End of Sprint)
- ✅ PDF page find & table extract (`fitz`, `pdfplumber`).
- ✅ Transform helpers: `find_in_the_money`, `clean_and_rename`, ticker mapping from CSV.
- ✅ S3 upload helper (`upload_df_to_s3`) & manifest load/save.
- ✅ Orchestrator (`run_nadex_pipeline`) with date filtering and skip‑already‑processed.
- ✅ **No hard‑coded bucket names** — all buckets now sourced from `configs/s3.yaml`.
- ✅ **S3 prefixes finalized**.
- ✅ **Run log append** implemented and verified — S3 `logs/run_log.csv` updated after run.
- ✅ **Dry run completed for last 90 days**; outputs validated in S3.
- ✅ Requirements verified — `requirements.txt` includes `pymupdf` (PyMuPDF), `pdfplumber`, `tqdm`, `pyyaml`, and `boto3`.

## Backlog
*None — all remaining work for this area moved into Sprint 2.*

## Sprint 1 Retrospective (Brief)
- **Went well:** repos aligned; config externalized; 90‑day dry run successful; run log + manifest working; S3 prefixes finalized.
- **Didn’t go well:** estimate slipped (planned 4 days → actual 7); Todoist importer stacked tasks on the same day, creating overdue noise.
- **Adjustments:**
  - Keep the **one‑sprint‑ahead** rule (already in Next Steps loop).
  - Plan **1 × 30‑min task/day** (max 2); stagger due dates in Todoist.
  - Use **MoSCoW** (Must/Should/Could) to trim scope mid‑sprint if needed.
  - Add a mini **DoD checklist** at the top of each notebook (S3 writes, manifest update, run log) to prevent “almost done” states.
