---
name: governance-handoff
description: >-
  Submit a LIVEWELL governance handoff. Encodes WORKFLOW step 3: create a new
  immutable LW-<date>-<slug>.md file in the governance inbox from the handoff
  template, with precisely-reported source state, the data.json sourceRevision,
  and sanitized evidence only. Use when asked to "submit a handoff", "write a
  governance handoff", "hand off to the checklist agent", or after finishing a
  bounded LIVEWELL task that governance should review.
---

# LIVEWELL governance handoff

Encodes **step 3** of the governance workflow
(`/Users/i802235/Development/project-governance/WORKFLOW.md`) for LIVEWELL.
Read the `governance` steering file and the authoritative governance docs first;
this skill operationalizes them, it does not replace them.

A handoff is a **proposal**, not an applied change. See the critical caveat:
nothing happens until Ian says "Review the inbox" in the governance
conversation. There is no watcher.

## Before you write anything

1. **Read the authoritative sources** (defer to them, do not restate):
   - `/Users/i802235/Development/project-governance/AGENTS.md`
   - `/Users/i802235/Development/project-governance/templates/handoff.md`
   - `/Users/i802235/Development/project-governance/nbas/LIVEWELL.md`
   - The `responses/` reply to the previous LW handoff (avoid duplicate updates).

2. **Capture the snapshot revision** — read `sourceRevision` and
   `_governanceSnapshot.retrievedAt` from
   `/Users/i802235/Development/project-governance/data.json`. Cite the revision
   in the handoff and note "snapshot; S3 authoritative".

3. **Verify real source state from git — do not assert from memory.** These are
   distinct states and must be reported distinctly:
   - **local** — uncommitted working-tree changes (`git status --porcelain`).
   - **committed** — in local history (`git log`, record the commit SHA).
   - **pushed** — on `origin/main` (`git log origin/main..HEAD` empty ⇒ pushed;
     this repo is solo, remote `github.com/ianfmc/livewell`, default branch `main`).
   - **merged** — relevant only if a feature branch / PR exists.
   - **deployed** — only if an actual deploy happened; a plan or CDK code that
     exists is NOT deployed. Deploy only on Ian's explicit request.

## Create the handoff file

4. **Pick the request ID and filename.** Format matches existing LW entries:

   ```
   LW-<YYYYMMDD>-<slug>.md
   ```

   `<YYYYMMDD>` is today's UTC date; `<slug>` is a short kebab-case summary
   (e.g. `LW-20261002-replay-verification-result`). The Request ID inside the
   file is the filename without `.md`.

   **Uniqueness / immutability:** never overwrite a submitted handoff. If the
   slug/date collides with an existing file in `inbox/`, choose a distinct slug.
   A **correction** is a brand-new file whose `Related prior request:` field
   references the earlier Request ID — never an edit of the original.

   Check for collisions:
   ```bash
   ls /Users/i802235/Development/project-governance/inbox/LW-*.md
   ```

5. **Fill in `templates/handoff.md`** and write it to
   `/Users/i802235/Development/project-governance/inbox/<request-id>.md`.
   - `Project:` is `LW`.
   - `Based on checklist revision:` is the `data.json` sourceRevision from step 2.
   - For each task ID, give requested status, work completed, sanitized
     evidence, **source state** (step 3), verification *actually performed*
     (not planned), remaining work/blockers, and next action.
   - Use the real task IDs from the NBA / snapshot (LW-301, LW-302, LW-110, …).

## Sanitize

6. **Sanitized evidence only.** Never include keys, tokens, signed URLs,
   customer data, or proprietary SAP implementation details. Reference S3 by
   prefix (`s3://livewell-data-prod/frozen/baseline-v1/`), not signed URLs.
   Prefer commit SHAs, counts, and pass/fail results over raw dumps.

## Honesty rules (from AGENTS.md)

7. Distinguish verified execution from planned work. Do **not** request a task
   be marked `done` on the strength of a plan or a partial sub-claim. If only a
   sub-claim is verified, say so and request `unchanged`, listing what remains.
8. List explicit exclusions: other-agent work, unrun checks, unmerged changes,
   outcomes not claimed.

## After writing

9. Do **not** edit `data.json`, `responses/`, or canonical S3. The handoff is
   now a proposal sitting in `inbox/`.
10. Tell Ian the file path and that **nothing is applied until he asks
    governance to "Review the inbox."** Then (optionally) `/context-save`.

## Do NOT

- Do not modify anything in the governance repo except adding your new
  `inbox/` file.
- Do not overwrite or edit an already-submitted handoff.
- Do not claim pushed/merged/deployed without verifying it from git / reality.
- Do not include secrets or unsanitized evidence.
- Do not treat the handoff as authorization to deploy or to change infrastructure.
