# Kiro 606 / 607 — completed evaluation evidence

Prepared 2026-10-16. Owner: Ian. Completes the governance worksheet
`project-governance/docs/Kiro-606-completion-evidence.md` for the shared
platform-level closure of the Kiro `606` (setup/efficacy) and `607` (two-week
usefulness) evaluation items across AT / LW / RW, under the approved
parallel-closure rule.

> **Attribution discipline.** Fields are labeled **[agent-verified]** (facts I
> observed directly this session) or **[operator attestation — Ian]** (Ian's
> stated experience, which the agent relays but did not itself observe over
> time). This separation is deliberate so no longitudinal claim is presented as
> agent observation.

---

## 1. Evaluation slice already accepted  [agent-verified]

- Representative project: **LIVEWELL**
- Bounded task: **LW-605** — backtest summary contract + frozen-fixture validation
- Kiro surface: **Kiro CLI (`kiro-cli chat`)**
- Model selection: **`Auto`** (server-selected)
- Commits: **`7dcb15f`**, **`e825710`**
- Verification: **46 backtest tests passed**, including **10 new contract tests**
- Correction loops: **0**
- Production changes: **none**
- Production data or secrets: **none**
- Agent limitation observed: long-running servers / background processes must be
  started by Ian; the agent exec environment blocks launching them.

## 2. Setup review

- **Kiro remains the default development platform: Yes.** [operator attestation — Ian]
  Rationale (Ian): after a ~6-week trial among alternatives, the time/effort of
  moving to a different harness is not worth it.
- Recommended model-selection guidance: **`Auto`** — used across LW-304, LW-605,
  and the LW-104/105/107/111 wave with no model-related issue. [agent-verified]
- gstack workflow used and retained: governance-sync → bounded task via gstack
  review skills → governance-handoff; retained. [agent-verified]
- Skills/tools retained: `governance-sync`, `governance-handoff`,
  `plan-eng-review`, `browse`; code intelligence + test runners. [agent-verified]
- Skills/tools removed or avoided: none removed; server-launching avoided by the
  environment (handed to Ian). [agent-verified]
- Configuration changes made this session: none. [agent-verified]

## 3. Usage and efficacy

- Elapsed time to useful result (LW-605): **one working session.** [agent-verified]
- Time to green / accepted result: LW-605 test passed first run; governance
  accepted it (revision 183). [agent-verified]
- Usage or cost: **Not surfaced to the agent by this surface.** Operator reports
  the credit budget was **never exhausted** over ~6 weeks. [cost: agent — not
  exposed; budget: operator attestation — Ian]
- Human rework required: **none** — no governance handoff this session required
  rework; all were accepted as submitted. [agent-verified]
- Additional correction loops since the LW-605 handoff: **0**. [agent-verified]

## 4. Fallback triggers — confirmed  [agent-verified, observed in-session]

The setup escalated / changed approach, or is designed to, on each condition:

- **Uncertain architecture/scope** → paused for Ian's decision (e.g. LW-104
  grain/supersedence split; LW-107 clock defaults).
- **Personal-account security / credential handling** → used least-privilege
  `livewell-ro`; MFA/no-stored-keys posture respected; never echoed secrets.
- **Non-deterministic numerical correctness** → relied on deterministic checks
  (byte-identical backtest reruns; 16 fixture checks) rather than asserting.
- **Required runtime services unavailable** → handed server starts to Ian;
  verified via `/browse` + curl once up.
- **Two failed repair attempts** → policy to stop and change approach (not
  triggered this session; no repair loop recurred).
- **Explicit human approval / irreversible action** → gated: deploy and scratch
  teardown left to Ian; handoffs propose, never mutate canonical state.

## 5. Two-week usefulness review  [operator attestation — Ian]

> The `607` items are the two-week usefulness review. The agent cannot observe a
> multi-week span; the following is Ian's attestation as operator, which the
> agent relays. The ~6-week duration satisfies (and exceeds) the two-week bar.

- Trial duration: **~6 weeks.**
- Representative tasks: among several harness alternatives evaluated; LIVEWELL
  development including the governance-driven checklist work.
- Credit consumption: **never consumed all credits.**
- Rework after a run: **never had to refactor after a run.**
- Overall usefulness judgment: pleased enough that switching harnesses is not
  worth the time/effort.
- Operator statement (verbatim, approved for the handoff):
  > "~6 weeks of use; credit budget never exhausted; never had to refactor after
  > a run; chose to stay on Kiro because switching harnesses isn't worth the
  > time/effort."
- Session-to-date corroboration [agent-verified]: today's work (LW-304, LW-605,
  LW-104/105/107/111) produced multiple governance-accepted handoffs with zero
  rework demanded and deterministic verification throughout — consistent with
  the attestation, though not itself a two-week measurement.

## 6. Closure recommendation

Propose, under the approved parallel-closure rule, based on one representative
LIVEWELL evaluation plus Ian's ~6-week operator attestation:

- `AT-606` → done, `LW-606` → done, `RW-606` → done
- `AT-607` → done, `LW-607` → done, `RW-607` → done (two-week usefulness,
  satisfied by the ~6-week operator attestation)

All `608` router-fallback items remain **deferred** unless the fallback is
actually activated.
