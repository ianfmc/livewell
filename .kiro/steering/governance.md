---
inclusion: always
---

# LIVEWELL — Governance layer

LIVEWELL's checklist is owned by a **separate governance process**, not by this
repo. The canonical three-program checklist lives in S3 and is authoritative.
This repo never edits that checklist directly. Development work here is reported
to governance via immutable handoff files, which Ian then asks governance to
review.

## Where governance lives

Handoff workspace (local clone, read the real files — do not rely on memory):
`/Users/i802235/Development/project-governance/`

Read these authoritative sources at the start of a governance-related task and
defer to them (this steering file is a pointer, not a copy):

- `AGENTS.md` — the rules for development-agent handoffs.
- `WORKFLOW.md` — the 7-step checklist/agent workflow.
- `templates/handoff.md` — the required handoff format.
- `nbas/LIVEWELL.md` — **this program's current next best actions.** Read it
  before starting work; it supersedes stale memory of what's next.
- `data.json` — read-only snapshot. Check `_governanceSnapshot.retrievedAt`
  and `sourceRevision`; it may be stale. S3 is authoritative, not this file.
- `responses/LW-*.md` — governance's reply to each prior handoff; check these
  for a handoff's disposition before assuming it was applied.

## The workflow (by reference — see WORKFLOW.md)

The full 7 steps are in `WORKFLOW.md`. The parts that bind work in this repo:

1. Start each session by reading `nbas/LIVEWELL.md`, `AGENTS.md`, the current
   `data.json` snapshot, and the response to the previous handoff.
2. Do the next bounded task through the appropriate gstack skills; record
   *actual* verification, reuse existing plans, respect approval/deploy gates.
3. Submit a handoff — a new file in `inbox/` (see the `governance-handoff`
   skill, which encodes this step).
4. **Ask governance to review** — Ian says "Review the inbox" in the governance
   conversation. See the critical caveat below.
5. Ian decides which proposed checklist changes are applied.
6. Governance publishes to S3, refreshes `data.json`, writes `responses/`, and
   updates the NBA.
7. Reread the response and the refreshed NBA before continuing.

## Critical caveat — a handoff does nothing on its own

There is **no watcher**. Writing a file into `inbox/` does not update the
checklist, does not notify governance, and does not change any canonical state.
Nothing happens until **Ian explicitly asks governance to "Review the inbox"**
in the governance conversation. Do not treat a submitted handoff as applied,
and do not treat an NBA file as completion evidence or deployment authorization.

## Hard rules (from AGENTS.md — defer to it)

- Never edit `data.json`, existing `responses/`, or canonical S3 state through
  this workflow. Propose changes only in `inbox/`.
- Report source state precisely: **local, committed, pushed, merged, deployed
  are different states.** Plans and partial evidence do not establish completion.
- Sanitized evidence only: never include keys, tokens, signed URLs, customer
  data, or proprietary SAP implementation details in a handoff.
- A handoff authorizes no deployment, infrastructure change, or message to
  anyone. Deploy only when Ian explicitly requests it.
