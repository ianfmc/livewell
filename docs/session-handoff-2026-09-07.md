# Session Handoff — 2026-09-07

## Where we are

### Security transformation (LW-613) — DONE, verified
Account `715853571315` moved from all-root operation to scoped non-root identities. Verified `RootAccessKeys=0, RootMFAEnabled=1`.
- `ianfmc` — everyday human identity (console password + MFA `mfa/iPhone`; key rotated after in-session exposure). Standing perms: `AWSBillingReadOnlyAccess` + `AssumeAdminRole`.
- `Admin` role — `AdministratorAccess`, assumed with MFA. CLI profile `admin`; console via Switch Role.
- `livewell-ro` — read-only inspection (ReadOnlyAccess). Use this for AWS checks (no MFA prompt on reads).
- `checklist-tools` — Codex/deploy.sh identity: S3 (Get/Put/Delete+List) on `innovation-tournament-2026` + `three-program-recovery-715853571315-us-west-2`, plus read-only `cloudformation:DescribeStacks` + `lambda:GetFunctionConfiguration`. Verified working.
- `default` CLI profile → repointed to `ianfmc` (not root).
- Root: no access key, MFA console-only, break-glass.

### AWS profiles on this machine
- `default` → ianfmc | `admin` → assume Admin role (MFA) | `livewell-ro` → read-only | `checklist-tools` → scoped tool | `livewell` / `livewell-dev` (pre-existing)

### Pipeline verified operational (this weekend)
- Ingest→features→signals→score→persist runs end-to-end (live S3 + DynamoDB).
- Scheduled: EventBridge `livewell-pipeline-schedule-prod` = `cron(0 0 ? * MON-FRI *)`, ENABLED. Plus 4 resolver crons (settlement) — worth understanding what they write (possible Phase-5 progress).
- `livewell-signals-prod` ~16,588 items. Active model `rf_tuned@20260507T144919` (win 0.859 / EV 0.795).

## Artifacts created (uncommitted in working tree)
- `.kiro/steering/project.md`, `.kiro/settings/mcp.json`
- `docs/adr/0001-congressional-trading-signal.md` (LW-101 — reframed to personal early-warning scope; awaiting accept)
- `docs/designs/congressional-trading-signal.md` (office-hours: bridge A sector/index rollup, curated map B, ablation gate)
- `docs/baseline-v1-manifest.md` (LW-301 freeze plan)
- Local git tag `baseline-v1` (annotated, not pushed)

## Resume next session
1. **LW-301 finish** — run the S3 freeze steps in `docs/baseline-v1-manifest.md` (snapshot prices/features/signals + model + results export to `frozen/baseline-v1/`), push tag, flip manifest DRAFT→FROZEN. Use `--profile admin` for writes.
2. **LW-101** — accept the ADR (or request edits) to close the release gate.
3. **24h pipeline confirm** — verify next 00:00 UTC run wrote a fresh signal (proves root-key deletion broke nothing):
   `aws dynamodb query --table-name livewell-signals-prod --profile livewell-ro --region us-west-1 --key-condition-expression "signal_id = :s" --expression-attribute-values '{":s":{"S":"EURUSD__<tomorrow>"}}'`
4. **Congressional signal (LW-W1)** — deferred behind verified core (now verified). Discovery-contract items: schema/lineage, asset resolution, leakage-safe clock (LW-107), join+ablation (LW-206).

## Follow-ups (tracked, not urgent)
- Delete legacy `amplify-elys` IAM user after confirming it powers nothing live.
- Back up or confirm-dead the elys CodeCommit repos before removing access.
- RUNWELL: run the account-isolation ADR prompt in a RUNWELL session; escalate identity/transferability to a human at AWS (decision C) before any irreversible payment/ownership step; build parallel `runwell-ro` + deploy role.

## In flight (paused 2026-09-09, traveling)
- **LW-101 DONE** — ADR committed (2b28404), accepted. Not yet pushed.
- **LW-103 (Confirm disclosure access method + terms)** — IN PROGRESS, status `ready`, NOT complete (evidence empty). Reconciled against decision LW-D02 ("Official disclosure sources OR licensed feed", resolved): scope is broader than Capitol Trades — official House Clerk + Senate EFD filings are first-class options; Capitol Trades is the licensed-aggregator path. **Open question to answer on return:** pull from official House/Senate filings directly, use an aggregator (Capitol Trades), or both? Then read the actual source terms (automation/storage/reuse) and record cited evidence + any unresolved restriction w/ follow-up. Also recommend to checklist agent: LW-103 title over-narrows to Capitol Trades vs. the broader resolved LW-D02.
- Checklist source URLs for LW-103: capitoltrades.com/terms-and-conditions, capitoltrades.com/about-us; official: House Clerk disclosures + Senate EFD.
- checklist-tools presigned URLs are scoped-key signed (AKIA...VY64SRPP), NOT root — leaked link = read-only to those objects, no rotation needed.

## Env gotchas (save time next session)
- `bun` lives at `~/.bun/bin/bun` — needs to be on PATH for the gstack browse daemon.
- IAM policy files must start with `{` at byte 0 (no leading whitespace) or IAM "legacy parsing" rejects them.
- Long ARNs pasted via terminal can pick up a stray space (bit us: `71 5853571315`) — console JSON paste or verified local file avoids it.
- `--profile admin` prompts for MFA (can't run non-interactively); use `--profile livewell-ro` for read-only checks.
