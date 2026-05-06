# Lambda Fan-Out Design

**Date:** 2026-05-06
**Status:** Approved

## Problem

The single pipeline Lambda (`livewell-pipeline-fn-{env}`) processes all 19 instruments sequentially. Each instrument runs ingestion (yfinance) + features + signals, taking ~20–30s. Total wall-clock time exceeds the 600s timeout configured in CDK, causing `Sandbox.Timedout` errors.

## Solution

Fan out: one coordinator invocation fires 19 async worker invocations in parallel, one per instrument. The coordinator returns immediately; workers run concurrently, each completing in well under 300s.

## Event Routing

The same Docker image and function handles both modes. `handler()` routes on event shape:

| Event | Mode |
|---|---|
| `{}` or `{"backfill": true}` | Coordinator |
| `{"s3_key": "EURUSD", "run_id": "...", "backfill": false}` | Worker |

Routing condition: `"s3_key" in event`.

## Coordinator Mode

1. Generate `run_id`, write `status=running` to `livewell-model-runs-{env}` DynamoDB table
2. For each of the 19 instruments, invoke the Lambda itself asynchronously (`InvocationType=Event`) with payload `{"s3_key": "<key>", "run_id": "<run_id>", "backfill": <bool>}`
3. Return `{"run_id": run_id, "status": "running"}` immediately

The run record stays `status=running` permanently — it is a coordinator breadcrumb, not a completion record. Completeness is checked by querying today's signal records.

## Worker Mode

1. Receive `{"s3_key": "...", "run_id": "...", "backfill": ...}`
2. Call `run_instrument(s3_key, run_id, backfill)` — no changes to `runner.py`
3. On success: call `put_signal(record)` to write signal to DynamoDB
4. On failure: raise — Lambda routes the event to the DLQ

No changes to `runner.py` or `dynamodb.py`.

## Visibility

- **Success**: 19 signal records written to `livewell-signals-{env}` for today's date
- **Infrastructure failure** (Lambda can't execute worker): event lands on DLQ → CloudWatch alarm fires → SNS alert email
- **Application failure** (worker raises): Lambda retries twice (async default), then routes to DLQ → same alarm path

## Infrastructure Changes (CDK `livewell-stack.ts`)

### 1. Lambda timeout
Change from 600s to **300s**. Workers are the bottleneck; coordinator finishes in ~5s. 300s is generous per-instrument.

### 2. IAM — self-invoke permission
Add `lambda:InvokeFunction` on the function's own ARN to `pipelineRole`:

```typescript
pipelineLambda.addToRolePolicy(new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: ['lambda:InvokeFunction'],
  resources: [pipelineLambda.functionArn],
}));
```

### 3. DLQ — SQS queue
Create an SQS queue and wire it as the Lambda's dead-letter queue:

Create the SQS queue before the Lambda, then pass it as a constructor prop:

```typescript
const dlq = new sqs.Queue(this, 'PipelineDLQ', {
  queueName: `livewell-pipeline-dlq-${env}`,
  retentionPeriod: cdk.Duration.days(14),
});

// dlq passed into DockerImageFunction constructor as deadLetterQueue prop
```

### 4. DLQ alarm
CloudWatch alarm on `ApproximateNumberOfMessagesVisible > 0`, wired to the existing SNS alert topic:

```typescript
new cloudwatch.Alarm(this, 'DLQAlarm', {
  alarmName: `livewell-pipeline-dlq-${env}`,
  metric: dlq.metricApproximateNumberOfMessagesVisible({
    period: cdk.Duration.minutes(5),
    statistic: 'Sum',
  }),
  threshold: 0,
  evaluationPeriods: 1,
  comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
  treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
});
```

## Code Changes (apps/api)

### `livewell/pipeline/handler.py`

Split into three functions:

- `handler(event, context)` — routes to coordinator or worker
- `_run_coordinator(run_id, backfill, lambda_arn)` — creates run record, fires 19 async invocations
- `_run_worker(event)` — calls `run_instrument`, calls `put_signal`

### No other files change

`runner.py`, `dynamodb.py`, `ingest.py`, `features.py`, `signals.py` — all unchanged.

## Files Touched

| File | Change |
|---|---|
| `apps/api/livewell/pipeline/handler.py` | Refactor into coordinator/worker modes |
| `infra/lib/livewell-stack.ts` | Timeout 300s, IAM self-invoke, SQS DLQ, DLQ alarm |
