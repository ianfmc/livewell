# Session Handoff — 2026-09-26

Handover to the agent that creates and manages the Three-Program Recovery
checklist. Everything below is verified state, not assumption. This agent made
no modifications to the checklist S3 object; all checklist writes are left for
the checklist agent / Ian via the app UI.

## Theme

Completed **Track A** (freeze the core NADEX baseline) and finished the
congressional-signal research/documentation tasks. **Track B** (the congressional
signal itself) remains deferred behind an unresolved terms question. Ian's
stance: Track B is "nice to have" on a running LIVEWELL, not a priority.

## Checklist changes to record

### LW-301 — Freeze and reproduce the existing NADEX baseline → mark `done`
Release gate; gate LW-G01. Freeze executed and verified today. Suggested evidence:

> Baseline frozen and verified 2026-09-26 (gate LW-G01). Code tag baseline-v1
> (e5ec61e) pushed to origin. Inputs/model/results snapshotted to
> s3://livewell-data-prod/frozen/baseline-v1/ — 563 objects (~65MB):
> prices/features/signals (187 each), model v20260507T144919.joblib,
> results/signals-export.json. Manifest marked FROZEN in
> docs/baseline-v1-manifest.md (commit f77c0bd). Reproduce: git checkout
> baseline-v1, point pipeline at frozen prefix, use pinned model, compare
> against signals-export.json.

### LW-102 — Document disclosure delays and research limitations → already `done`
Release gate; gate LW-G12. Marked done earlier this cycle (checklist revision
124). Artifact: `docs/research/congressional-disclosure-limitations.md`
(commit 8e013a6).

### LW-103 — Confirm official-disclosure access method and terms
Release gate; gate LW-G02.
- Title already corrected earlier (was "Confirm Capitol Trades access method";
  now "Confirm official-disclosure access method and terms") to align with
  resolved decision LW-D02.
- Research artifact complete and committed:
  `docs/research/congressional-disclosure-access.md` (commit ff9efd0).
- **Status decision still pending Ian.** Acceptance criteria are technically met
  (workable acquisition method + terms documented; each unresolved restriction
  has a specific follow-up). BUT a **gating open question** remains: whether
  personal trading research counts as a prohibited "commercial purpose" is
  UNVERIFIED on both House and Senate sources. Recommend either (a) mark `done`
  and open a new task for the commercial-purpose determination, or (b) leave
  `doing` until the phone calls are made.

## Sequencing decision made this session

LIVEWELL now has two independent fronts, tracked via existing **milestones**
(Ian explicitly chose the milestone approach over splitting into two projects or
modifying the checklist engine):

- **Track A — finish core LIVEWELL (no congressional signal):** LW-301 freeze.
  **COMPLETE as of today.**
- **Track B — congressional signal research spike (notebooks-first):** LW-104–108
  definitions + a one-time bounded data pull + the LW-206 ablation, all in Jupyter
  before any production ingest chain (LW-201/202/204/208) is built. The ablation
  depends on the frozen baseline (LW-301, now met).

Formalized in committed planning notes:
- `docs/research/congressional-signal-track-plan.md`
- `docs/research/lw206-ablation-notebook-sketch.md`

## The one real blocker for Track B

The **commercial-purpose classification** (from LW-103) gates ALL of Track B —
even a one-time notebook data pull sits downstream of it. Follow-ups documented
in the LW-103 research note:
- House Legislative Resource Center: (202) 226-5200
- Senate Office of Public Records: (202) 224-0322
- Automation/retention questions: clerkweb@mail.house.gov + Senate Public Records

No calls made yet. Recommend answering before any Track B data acquisition.

## What is NOT yet verified (honest note on LW-301)

The freeze *captured* everything needed to reproduce the baseline, and the
frozen prefix, tag, and manifest were all verified to exist. What was NOT done is
an actual *reproduction run* — nobody has re-run the pipeline from `baseline-v1`
against the frozen prefix and confirmed it regenerates `signals-export.json`.
This is not required to close LW-301 (the gate asks for the frozen artifact,
which exists). A true reproduction check is best folded into the LW-206 ablation
harness later, which must reproduce the baseline (Arm A) anyway.

## Git state (branch `main`, all pushed to origin ianfmc/livewell)

- `f77c0bd` — mark baseline-v1 manifest FROZEN (LW-301, gate LW-G01)
- `ef6ceea` — track plan + LW-206 ablation notebook sketch
- `ff9efd0` — LW-103 access method + terms research
- `8e013a6` — LW-102 disclosure limitations research note
- `2b28404` — ADR-0001 (prior)
- Tag `baseline-v1` → `e5ec61e` pushed

## AWS state (account 715853571315, verified read-only)

- `s3://livewell-data-prod/frozen/baseline-v1/` populated: 563 objects, ~65 MB
  (prices/features/signals 187 each, pinned model, signals-export.json).
- All writes done via `--profile admin` (MFA) by Ian; verification reads via
  `livewell-ro`. No checklist S3 object was modified by this agent.
- IAM users: `ianfmc`, `livewell-dev`, `livewell-ro`, `checklist-tools`. Legacy
  `amplify-elys` user no longer present (earlier follow-up appears closed).
  `livewell-ro` = AWS-managed `ReadOnlyAccess`, no groups/inline policies.

## Proposed LIVEWELL `latestNote` (for the checklist agent to apply)

> As of 26 September 2026 — LIVEWELL remains a personal early-warning system for
> potential NADEX trades. LW-101 complete (ADR-0001: congressional disclosures =
> contextual signal, leakage-safe clock + ablation required before adoption).
> LW-102 complete (disclosure-limitations research note). LW-103 research complete
> (acquisition method + source terms documented over official House/Senate
> disclosures); the commercial-purpose classification for personal trading
> research is the gating open question with specific follow-ups. LW-301 COMPLETE
> (gate LW-G01): the NADEX baseline is frozen and reproducible — tag baseline-v1 +
> s3://livewell-data-prod/frozen/baseline-v1/.
>
> Two active fronts, tracked via milestones (see
> docs/research/congressional-signal-track-plan.md). Track A (core LIVEWELL,
> independent of the congressional signal): DONE — baseline frozen. Track B
> (congressional research spike, notebooks-first): explore
> acquisition/normalize/point-in-time-join and run the LW-206 ablation against the
> frozen baseline before building any production ingest chain; treated as
> nice-to-have on a running LIVEWELL. Resolve the LW-103 commercial-purpose
> question before any Track B data pull.

## Suggested next actions for the checklist

1. Mark LW-301 `done` with the evidence above (closes LW-G01, completes Track A).
2. Apply the updated `latestNote`.
3. Decide LW-103 `done` vs `doing` re: the commercial-purpose question; if `done`,
   consider a new task for the commercial-purpose determination as the Track B
   entry gate.
4. Track B (LW-104–108, LW-206) stays parked per Ian's priority; no action needed
   unless he chooses to pursue it.
