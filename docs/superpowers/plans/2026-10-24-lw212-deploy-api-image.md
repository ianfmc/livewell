# LW-212 — Deploy current LIVEWELL API image and verify GSI/Explain

**Task:** LW-212 (governance rev 224, release-gate, `ready`, deps `[LW-208]` done).
Deploy the committed API image (`7dc45419...`) carrying the LW-208 GSI-query code +
the Explain fix (`cf6f0c4`) to `livewell-api-fn-prod`, then verify live.

**Governance-approved sequence (rev 224):** API deploy (LW-212) FIRST, then
resolver recovery + CDK reconciliation (LW-211). The additive GSI is already
accepted as a live interim step.

**Eng-review decision D1 → A (decision `b33caf0c`):** deploy via `cdk-assets publish`
of the staged image + surgical `lambda update-function-code`. NOT `cdk deploy`
(would destroy the untracked resolver subsystem — `livewell-prod-cdk-drift-trades-resolver`).
Fallback B = manual `docker build --platform linux/arm64` + push if the CDK
image-publishing-role is not assumable.

## Why this is a deploy-only task

Zero application code changes. The image content is commit `f3935d1`, already
through `/plan-eng-review` + `/review`. LW-212 only changes WHICH image the live
Lambda runs. The "test" is live production verification, below.

## Current prod state (verified this session)

- `livewell-api-fn-prod` runs the **2026-05-14 image `45b57b04...`** — predates
  LW-208 and the Explain fix.
- `/api/signals` → 200 but ~8.9s + intermittent 502 (old full-table scan over
  17,221 items; the GSI exists but unused).
- `/api/explain/{live-id}` → 404 (pre-`cf6f0c4` S3-read bug).
- Target image `7dc45419...` is staged in `infra/cdk.out/asset.7dc4541.../`
  (ARM64, `Dockerfile.api`) with publish recipe in `LivewellStack-prod.assets.json`.

## Execution plan

### 0. Preconditions
- AWS creds valid (temp assume-role creds expire ~17:18 UTC; re-mint via
  `aws sts assume-role ... --serial-number arn:aws:iam::715853571315:mfa/iPhone
  --token-code <code>` if expired — `livewell-admin-profile-assume-role-mfa`).
- `cdk.out` asset `7dc4541...` present (it is, from this session's synth).

### 1. Pre-flight — record rollback target
```
aws lambda get-function --function-name livewell-api-fn-prod --region us-west-1 \
  --query 'Code.ImageUri' --output text    # expect ...:45b57b04...  (ROLLBACK TARGET)
```

### 2. Publish the staged image to ECR (no rebuild — reuse the reviewed asset)
```
cd infra
npx cdk-assets -p cdk.out/LivewellStack-prod.assets.json publish \
  "7dc454199968649737fd714c7bed967a9bbcdac75a256d3589af016a9ebf46e6:715853571315-us-west-1-0d97ffdf"
```
If the image-publishing-role is not assumable → FALLBACK B:
```
cd infra/cdk.out/asset.7dc454199968649737fd714c7bed967a9bbcdac75a256d3589af016a9ebf46e6
aws ecr get-login-password --region us-west-1 | docker login --username AWS --password-stdin 715853571315.dkr.ecr.us-west-1.amazonaws.com
docker build --platform linux/arm64 -f Dockerfile.api -t <repo>:7dc4541... .
docker push <repo>:7dc4541...
```
(Prefer A; B risks a non-identical rebuild — verify the resulting digest in step 4.)

### 3. Point the Lambda at the new image
```
ECR=715853571315.dkr.ecr.us-west-1.amazonaws.com/cdk-hnb659fds-container-assets-715853571315-us-west-1
aws lambda update-function-code --function-name livewell-api-fn-prod --region us-west-1 \
  --image-uri ${ECR}:7dc454199968649737fd714c7bed967a9bbcdac75a256d3589af016a9ebf46e6
aws lambda wait function-updated --function-name livewell-api-fn-prod --region us-west-1
```

### 4. Confirm the deployed digest changed
```
aws lambda get-function --function-name livewell-api-fn-prod --region us-west-1 \
  --query 'Code.ImageUri' --output text   # expect ...:7dc4541..., NOT 45b57b04
```

### 5. Live verification (warm first, then measure)
```
URL=https://3rxkdcbg4w2yshiyzoqsnd6c6q0cjjoo.lambda-url.us-west-1.on.aws
curl -s -o /dev/null -w "%{http_code} %{time_total}s\n" "$URL/api/signals"   # warm (discard)
curl -s -w "\n%{http_code} | %{time_total}s\n" "$URL/api/signals" -o /tmp/sig.json  # measure: expect 200, SUB-SECOND
python3 -c "import json;d=json.load(open('/tmp/sig.json'));print('rows',len(d));print(d[0]['signalId'])"
# use a REAL signalId from above (do not guess a date):
curl -s -w "\n%{http_code} | %{time_total}s\n" "$URL/api/explain/<real-signalId>"  # expect 200
```
Pass criteria: `/api/signals` 200 + **sub-second** (down from ~9s) = GSI query path
live; `/api/explain/{real-id}` 200 = Explain fix live.

### 6. Rollback (if any pass criterion fails)
```
aws lambda update-function-code --function-name livewell-api-fn-prod --region us-west-1 \
  --image-uri ${ECR}:45b57b04cd601e66b2fcd07556bf24c2e4d84fef0c4f72a0a42574bfe30c74e3
aws lambda wait function-updated --function-name livewell-api-fn-prod --region us-west-1
```
Then diagnose before retrying. `update-function-code` is fully reversible; the old
image stays in ECR.

### 7. Handoff
Report deployed digest, before/after `/api/signals` latency, Explain status.
Request LW-212 `done` ONLY on verified-live evidence (not on the update call
returning success). Note this is an out-of-band-from-CDK deploy (governance-approved);
LW-211 reconciles CDK so future deploys are clean.

## Failure modes guarded

| Mode | Guard |
|------|-------|
| GSI not used (still ~9s) | Step 5 measures latency; sub-second is the gate, not just 200 |
| Wrong arch (x86 on ARM64 fn) | Path A preserves `linux/arm64` from assets.json; B must `--platform linux/arm64` |
| Cold-start 502 misread as failure | Step 5 warms first, discards the cold call |
| Explain 404 on guessed date | Use a real `signalId` from the live `/api/signals` response |
| Publishing-role not assumable | Fallback B |
| Deploy didn't take | Step 4 asserts the digest actually changed |
| Bad deploy | Step 6 rollback to recorded `45b57b04...` |

## NOT in scope
- `cdk deploy` / any CloudFormation op (blocked until LW-211 reconciles drift).
- Resolver subsystem (LW-211).
- App code changes (none — image is `f3935d1`).

---

## GSTACK REVIEW REPORT

**Skill:** /plan-eng-review · **Target:** LW-212 (governance task) · **Date:** 2026-10-24 · **Reviewer model:** claude

### Scope outcome
Deploy-only task, 0 code changes, 0 new resources. No complexity smell. Scope held.

### Decisions
| ID | Decision | Chosen | Recommended | Confidence |
|----|----------|--------|-------------|------------|
| D1 | Deploy method | **A** cdk-assets publish + surgical update-function-code | A | 8/10 |

D1 logged `b33caf0c`. Fallback B (manual docker build/push) if publishing-role not assumable.

### Findings by section
1. **Architecture** — none. No code change; image already reviewed (`f3935d1`).
2. **Code quality** — none. Deploy op only.
3. **Tests** — code tests already green (266 API, 7-arm gate). LW-212's verification IS live production checks (plan step 5).
4. **Deploy/failure/rollback** — the substance. Rollback target recorded pre-deploy; latency is the pass gate (not HTTP 200 alone); warm-before-measure; real signalId for Explain; digest-changed assertion; surgical surface avoids the drifted stack. 7 failure modes guarded (table above).

### Prior learnings applied
- `livewell-prod-cdk-drift-trades-resolver` (9) — mandated NON-cdk-deploy surgical path. Verified.
- `livewell-prod-lambdas-deployed-manually-not-from-main` (9) — verify deployed digest before/after; commit ≠ live. Built into steps 1 & 4.
- `livewell-admin-profile-assume-role-mfa` (9) — creds mechanics in step 0.
- `mangum-direct-invoke-needs-sourceip` (8) — verify via the real Function URL (step 5), not synthetic invoke.

### Suppressed findings
None.

### Risk / watch
- Out-of-band-from-CDK deploy (governance-approved rev 224). Creates a transient "CFN thinks old image" drift on the API Lambda until LW-211 reconciles — acceptable and expected.
- Temp AWS creds expire ~17:18 UTC; re-mint if needed.

### Status
**DONE** — plan written, deploy method decided + logged, verification/rollback specified. Ready to execute on go. No code changed during review.
