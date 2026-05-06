# Phase 4 Batch Pipeline Design

## Goal

Deploy a daily batch pipeline that runs at midnight UTC, processes 18 instruments through three existing stages (ingestion → features → signals), persists scored signals to DynamoDB, and surfaces them through the `/api/signals` endpoint. CloudWatch + SNS alert on failures.

## Scope

This is sub-project 2 of Phase 4. It wires the existing Python pipeline stages into a scheduled Lambda, adds a DynamoDB write layer, and replaces the mock signals endpoint with a real DynamoDB read. Model scoring (ML probability) is out of scope — signals are persisted with `score: null` until sub-project 3.

## Architecture

A single Lambda function packaged as a Docker container is triggered by an EventBridge Cron rule at `cron(0 0 * * ? *)` (midnight UTC). The function assumes the existing `livewell-pipeline-{env}` IAM role. Per-instrument errors are caught and logged; the run continues for remaining instruments. Run metadata and signal records are written to DynamoDB. A CloudWatch alarm on Lambda errors and on `completed_with_errors` log events triggers an SNS topic that emails the operator.

The `/api/signals` endpoint is updated to read from `livewell-signals-{env}` DynamoDB table instead of returning hardcoded mock data.

## Repository Structure Changes

```
apps/api/
  livewell/pipeline/
    __init__.py
    handler.py          ← Lambda entry point
    runner.py           ← per-instrument orchestration (ingest → features → signals)
    dynamodb.py         ← DynamoDB write layer (runs + signals)
  routers/
    signals.py          ← replace mock with DynamoDB read
  Dockerfile.pipeline   ← container image for Lambda

infra/
  lib/livewell-stack.ts ← add Lambda, EventBridge rule, SNS, CloudWatch alarm
  test/livewell-stack.test.ts ← add CDK assertions for new constructs
```

## Pipeline Handler (`handler.py`)

Entry point called by Lambda runtime with `event` and `context` arguments (both unused — trigger is time-based).

**Flow:**
1. Generate `run_id` (UUID4), record `started_at` (ISO UTC timestamp)
2. Call `create_run(run_id, started_at)` — writes `status: "running"` to `livewell-model-runs-{env}`
3. For each instrument in `INSTRUMENTS` (18 total):
   - Call `run_instrument(instrument, run_id)` from `runner.py`
   - On success: append signal record to results list
   - On exception: log error, append `{instrument, error}` to errors list — continue
4. Determine final status:
   - 0 errors → `completed`
   - 1–17 errors → `completed_with_errors`
   - 18 errors → `failed`
5. Call `update_run(run_id, status, instruments_processed, errors, completed_at)`
6. For each successful signal: call `put_signal(signal_record)`
7. Log final summary line: `"run {run_id} {status}: {n_ok} ok, {n_err} errors"`
8. Return `{"run_id": run_id, "status": status}`

Lambda timeout: 10 minutes. Memory: 512 MB.

Environment variables: `LIVEWELL_BUCKET`, `LIVEWELL_ENV` (default `prod`).

## Per-Instrument Runner (`runner.py`)

`run_instrument(s3_key: str, run_id: str) -> dict` — processes one instrument through all three stages and returns the signal record for DynamoDB persistence.

**Flow:**
1. Call `ingest_instrument(s3_key, bucket, incremental=True)` — fetches latest 7 days (1d) and 30 days (1h), merges with existing S3 data
2. Call `generate_features(s3_key, bucket)` — reads full price history, computes indicators, writes features to S3
3. Call `generate_signals(s3_key, bucket)` — reads features+prices, applies 5-stage rule pipeline, writes signals to S3
4. Read the most recent signal row for `s3_key` from the signals S3 output
5. Return a dict with all `SIGNAL_COLUMNS` fields plus: `signal_id` (`{s3_key}__{iso_date}`), `s3_key`, `run_id`, `score: None`, `model_version: None`, `created_at` (ISO UTC)

Any exception propagates to the handler — runner does not catch.

## DynamoDB Write Layer (`dynamodb.py`)

Three functions, each using `boto3.resource('dynamodb')`. Table names read from env: `livewell-model-runs-{LIVEWELL_ENV}` and `livewell-signals-{LIVEWELL_ENV}`.

**`create_run(run_id, started_at)`**
Writes to `livewell-model-runs-{env}`:
```
{
  run_id: str,           # partition key
  started_at: str,       # sort key (ISO UTC)
  status: "running",
  instruments: [],
  errors: [],
  completed_at: None
}
```

**`update_run(run_id, started_at, status, instruments, errors, completed_at)`**
Updates the run record with final status, instrument list, error list, and completion timestamp.

**`put_signal(record: dict)`**
Writes to `livewell-signals-{env}`. `signal_id` is the partition key (`{s3_key}__{iso_date}`). All `SIGNAL_COLUMNS` fields included, plus `s3_key`, `run_id`, `score` (None), `model_version` (None), `created_at`.

## Signals Endpoint Update (`routers/signals.py`)

Replace hardcoded mock data with a DynamoDB scan of the most recent run's signals.

**`GET /api/signals`** — scan `livewell-signals-{env}` and return all records whose `created_at` date matches today's UTC date. If no records exist for today, return the most recent day's records (scan all, group by date, return the latest group). Return all records (both `signal_valid: true` and `signal_valid: false`) mapped to `ContractCard`.

**`ContractCard` mapping from DynamoDB record:**
```
instrument: s3_key formatted as display string (e.g. "EURUSD" → "EUR/USD")
strike:     strike_candidate (formatted as string)
expiry:     timing_slot
status:     "Open" if signal_valid else "Invalid"
signalId:   signal_id
```

Note: `ContractCard` in `schemas/contract.py` must have `signalId: str` added as a field.

The `GET /api/signals/{instrument}/{strike}` detail endpoint remains mock for now — it requires `ContractDetail` fields (recommendation, economics, edge) that the pipeline does not yet produce.

**Fallback:** If DynamoDB returns no results (pipeline hasn't run yet or `LIVEWELL_ENV` not set), return an empty list — do not raise an error.

## Docker Container (`Dockerfile.pipeline`)

```dockerfile
FROM python:3.12-slim
RUN pip install boto3 pandas pandas-ta yfinance awslambdaric
COPY apps/api /app
WORKDIR /app
ENTRYPOINT ["python", "-m", "awslambdaric", "--handler", "livewell.pipeline.handler.handler"]
```

Built and pushed to ECR as part of CDK deployment. ECR repository named `livewell-pipeline-{env}`.

## CDK Changes (`infra/lib/livewell-stack.ts`)

Four new constructs added to `LivewellStack`:

**Lambda function:** `livewell-pipeline-{env}`
- Image: `DockerImageCode.fromImageAsset('../', { file: 'apps/api/Dockerfile.pipeline' })` — CDK builds and pushes the image to ECR during `cdk deploy`
- Role: existing `pipelineRole`
- Memory: 512 MB
- Timeout: 10 minutes
- Environment: `LIVEWELL_BUCKET: bucket.bucketName`, `LIVEWELL_ENV: env`

**EventBridge rule:** `livewell-pipeline-schedule-{env}`
- Schedule: `cron(0 0 * * ? *)` (midnight UTC daily)
- Target: the Lambda function

**SNS topic + email subscription:** `livewell-alerts-{env}`
- Subscription email read from CDK context variable `alertEmail` (required at deploy time)

**CloudWatch alarm:** `livewell-pipeline-errors-{env}`
- Metric: Lambda `Errors` > 0 in a 5-minute window
- Action: publish to SNS topic

## Testing

**Unit tests (`apps/api/tests/pipeline/`):**

- `test_handler.py` — mock `run_instrument` and DynamoDB layer; verify run status logic (all pass → `completed`, partial → `completed_with_errors`, all fail → `failed`); verify `put_signal` called once per successful instrument
- `test_runner.py` — mock `ingest_instrument`, `generate_features`, `generate_signals`, S3 read; verify returned record shape; verify exception propagation
- `test_dynamodb.py` — mock boto3 resource; verify `create_run`, `update_run`, `put_signal` write correct item shapes and use correct table names

**CDK assertions (`infra/test/livewell-stack.test.ts`):**
- Lambda function exists with correct memory, timeout, environment variables
- EventBridge rule targets the Lambda with cron schedule `cron(0 0 * * ? *)`
- SNS topic exists
- CloudWatch alarm monitors Lambda Errors metric

**Integration test (manual):**
- `cdk deploy --context env=test --context alertEmail=you@example.com`
- Invoke Lambda manually via AWS Console with empty event `{}`
- Verify DynamoDB `livewell-model-runs-test` has a completed run record
- Verify DynamoDB `livewell-signals-test` has signal records
- Verify `/api/signals` returns those records (run API locally with `LIVEWELL_ENV=test`)

## What This Does Not Include

- ML model scoring (sub-project 3) — `score` field is always `null`
- `GET /api/signals/{instrument}/{strike}` detail endpoint wired to DynamoDB
- Model registry reads
- Backfill mode (pipeline always runs incremental)
