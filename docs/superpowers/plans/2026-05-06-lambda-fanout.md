# Lambda Fan-Out Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the pipeline Lambda from sequential single-invocation to fan-out: a coordinator invocation fires 19 async worker invocations in parallel, one per instrument, eliminating the 600s timeout.

**Architecture:** The same Docker image handles both modes. `handler()` routes on event shape — no `s3_key` means coordinator, presence of `s3_key` means worker. The coordinator creates a DynamoDB run record, invokes itself asynchronously for each instrument, and returns immediately. Each worker runs the full pipeline for its instrument and writes its signal to DynamoDB. Failed workers are routed to an SQS DLQ, which triggers a CloudWatch alarm wired to the existing SNS alert topic.

**Tech Stack:** Python 3.12, boto3 (Lambda client for async invoke), AWS CDK v2 (TypeScript), SQS, CloudWatch, SNS.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `apps/api/livewell/pipeline/handler.py` | Modify | Route coordinator vs worker; coordinator fans out; worker runs one instrument |
| `apps/api/tests/pipeline/test_handler.py` | Modify | Replace old sequential tests with coordinator and worker tests |
| `infra/lib/livewell-stack.ts` | Modify | Add SQS DLQ, reduce timeout to 300s, add IAM self-invoke, add DLQ alarm |

---

## Task 1: Rewrite handler tests for fan-out

The existing tests patch `run_instrument` and assert on `update_run` — that model no longer applies. Replace them with tests for the new coordinator and worker contracts.

**Files:**
- Modify: `apps/api/tests/pipeline/test_handler.py`

- [ ] **Step 1: Replace the test file contents**

Replace the entire file with the following:

```python
from __future__ import annotations
import json
from unittest.mock import patch, MagicMock
import pytest


@pytest.fixture(autouse=True)
def env(monkeypatch):
    monkeypatch.setenv("LIVEWELL_BUCKET", "test-bucket")
    monkeypatch.setenv("LIVEWELL_ENV", "test")
    monkeypatch.setenv("AWS_DEFAULT_REGION", "us-east-1")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test")
    monkeypatch.setenv("AWS_LAMBDA_FUNCTION_NAME", "livewell-pipeline-fn-test")


def _make_signal(s3_key: str) -> dict:
    return {
        "signal_id": f"{s3_key}__2026-05-05",
        "s3_key": s3_key,
        "run_id": "run-1",
        "direction": "buy",
        "signal_valid": True,
        "score": None,
        "model_version": None,
        "created_at": "2026-05-05T00:05:00Z",
    }


# ── Coordinator tests ─────────────────────────────────────────────────────────

def test_coordinator_creates_run_record():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run") as mock_create, \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        from livewell.pipeline.handler import handler
        handler({}, None)
    mock_create.assert_called_once()
    run_id, started_at = mock_create.call_args.args
    assert isinstance(run_id, str) and len(run_id) == 36  # uuid4


def test_coordinator_invokes_one_worker_per_instrument():
    from livewell.ingestion.constants import INSTRUMENTS
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        from livewell.pipeline.handler import handler
        handler({}, None)
    assert mock_lambda.invoke.call_count == len(INSTRUMENTS)


def test_coordinator_passes_s3_key_and_run_id_to_workers():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run") as mock_create, \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        from livewell.pipeline.handler import handler
        handler({}, None)
    run_id = mock_create.call_args.args[0]
    first_call_payload = json.loads(
        mock_lambda.invoke.call_args_list[0].kwargs["Payload"]
    )
    assert first_call_payload["run_id"] == run_id
    assert "s3_key" in first_call_payload
    assert first_call_payload["backfill"] is False


def test_coordinator_passes_backfill_flag():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        from livewell.pipeline.handler import handler
        handler({"backfill": True}, None)
    payload = json.loads(
        mock_lambda.invoke.call_args_list[0].kwargs["Payload"]
    )
    assert payload["backfill"] is True


def test_coordinator_returns_running_status():
    mock_lambda = MagicMock()
    mock_lambda.invoke.return_value = {"StatusCode": 202}
    with patch("livewell.pipeline.handler.create_run"), \
         patch("livewell.pipeline.handler._lambda_client", mock_lambda):
        from livewell.pipeline.handler import handler
        result = handler({}, None)
    assert result["status"] == "running"
    assert "run_id" in result


# ── Worker tests ──────────────────────────────────────────────────────────────

def test_worker_calls_run_instrument_and_puts_signal():
    signal = _make_signal("EURUSD")
    with patch("livewell.pipeline.handler.run_instrument", return_value=signal) as mock_run, \
         patch("livewell.pipeline.handler.put_signal") as mock_put:
        from livewell.pipeline.handler import handler
        handler({"s3_key": "EURUSD", "run_id": "run-1", "backfill": False}, None)
    mock_run.assert_called_once_with("EURUSD", "run-1", backfill=False)
    mock_put.assert_called_once_with(signal)


def test_worker_raises_on_run_instrument_failure():
    with patch("livewell.pipeline.handler.run_instrument", side_effect=RuntimeError("yfinance down")):
        from livewell.pipeline.handler import handler
        with pytest.raises(RuntimeError, match="yfinance down"):
            handler({"s3_key": "EURUSD", "run_id": "run-1", "backfill": False}, None)


def test_worker_returns_signal_id():
    signal = _make_signal("GBPUSD")
    with patch("livewell.pipeline.handler.run_instrument", return_value=signal), \
         patch("livewell.pipeline.handler.put_signal"):
        from livewell.pipeline.handler import handler
        result = handler({"s3_key": "GBPUSD", "run_id": "run-1", "backfill": False}, None)
    assert result["signal_id"] == signal["signal_id"]
    assert result["s3_key"] == "GBPUSD"
```

- [ ] **Step 2: Run the new tests to confirm they all fail (handler not yet updated)**

```bash
cd apps/api && uv run pytest tests/pipeline/test_handler.py -v
```

Expected: multiple FAILs — `_lambda_client` not defined, coordinator/worker routing not implemented.

- [ ] **Step 3: Commit the failing tests**

```bash
git add apps/api/tests/pipeline/test_handler.py
git commit -m "test: replace handler tests for fan-out coordinator/worker"
```

---

## Task 2: Rewrite handler.py for fan-out

Replace the sequential loop with coordinator/worker routing.

**Files:**
- Modify: `apps/api/livewell/pipeline/handler.py`

- [ ] **Step 1: Replace handler.py**

```python
from __future__ import annotations
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import boto3

from livewell.ingestion.constants import INSTRUMENTS
from livewell.pipeline.dynamodb import create_run, put_signal
from livewell.pipeline.runner import run_instrument

logger = logging.getLogger(__name__)

_lambda_client = boto3.client("lambda")


def handler(event: dict, context) -> dict:
    if "s3_key" in event:
        return _run_worker(event)
    return _run_coordinator(event)


def _run_coordinator(event: dict) -> dict:
    backfill = bool(event.get("backfill", False))
    run_id = str(uuid.uuid4())
    started_at = datetime.now(timezone.utc).isoformat()
    function_name = os.environ["AWS_LAMBDA_FUNCTION_NAME"]

    create_run(run_id, started_at)

    for instrument in INSTRUMENTS:
        payload = json.dumps({
            "s3_key": instrument["s3_key"],
            "run_id": run_id,
            "backfill": backfill,
        })
        _lambda_client.invoke(
            FunctionName=function_name,
            InvocationType="Event",
            Payload=payload,
        )
        logger.info("dispatched worker for %s (run %s)", instrument["s3_key"], run_id)

    logger.info("coordinator done — run_id=%s, backfill=%s", run_id, backfill)
    return {"run_id": run_id, "status": "running"}


def _run_worker(event: dict) -> dict:
    s3_key = event["s3_key"]
    run_id = event["run_id"]
    backfill = bool(event.get("backfill", False))

    record = run_instrument(s3_key, run_id, backfill=backfill)
    put_signal(record)
    logger.info("worker done — %s (run %s)", s3_key, run_id)
    return {"signal_id": record["signal_id"], "s3_key": s3_key}
```

- [ ] **Step 2: Run the tests**

```bash
cd apps/api && uv run pytest tests/pipeline/test_handler.py -v
```

Expected: all PASS.

- [ ] **Step 3: Run the full test suite to check for regressions**

```bash
cd apps/api && uv run pytest -v
```

Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
git add apps/api/livewell/pipeline/handler.py
git commit -m "feat: refactor pipeline handler into coordinator/worker fan-out"
```

---

## Task 3: Update CDK stack — DLQ, timeout, IAM, alarm

**Files:**
- Modify: `infra/lib/livewell-stack.ts`

- [ ] **Step 1: Add SQS import at the top of livewell-stack.ts**

Add `* as sqs from 'aws-cdk-lib/aws-sqs'` to the imports block. The full import section becomes:

```typescript
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import * as events from 'aws-cdk-lib/aws-events';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as subscriptions from 'aws-cdk-lib/aws-sns-subscriptions';
import * as cloudwatch from 'aws-cdk-lib/aws-cloudwatch';
import * as cloudwatchActions from 'aws-cdk-lib/aws-cloudwatch-actions';
import * as path from 'path';
```

- [ ] **Step 2: Create the DLQ before the Lambda definition**

Insert this block immediately before the `const pipelineLambda = ...` line (line ~143):

```typescript
// ── DLQ ───────────────────────────────────────────────────────────────────────
const dlq = new sqs.Queue(this, 'PipelineDLQ', {
  queueName: `livewell-pipeline-dlq-${env}`,
  retentionPeriod: cdk.Duration.days(14),
});
```

- [ ] **Step 3: Update the Lambda definition**

Replace the existing `pipelineLambda` definition with one that reduces the timeout to 300s and wires the DLQ:

```typescript
const pipelineLambda = new lambda.DockerImageFunction(this, 'PipelineLambda', {
  functionName: `livewell-pipeline-fn-${env}`,
  code: lambda.DockerImageCode.fromImageAsset(
    path.join(__dirname, '../../apps/api'),
    { file: 'Dockerfile.pipeline' }
  ),
  role: pipelineRole,
  architecture: lambda.Architecture.ARM_64,
  memorySize: 512,
  timeout: cdk.Duration.seconds(300),
  deadLetterQueue: dlq,
  environment: {
    LIVEWELL_BUCKET: bucket.bucketName,
    LIVEWELL_ENV: env,
    NUMBA_CACHE_DIR: '/tmp',
  },
});
```

- [ ] **Step 4: Add IAM self-invoke permission**

Insert this block immediately after the `pipelineLambda` definition (before the EventBridge schedule block):

```typescript
// Allow the coordinator to invoke itself as workers
pipelineLambda.addToRolePolicy(new iam.PolicyStatement({
  effect: iam.Effect.ALLOW,
  actions: ['lambda:InvokeFunction'],
  resources: [pipelineLambda.functionArn],
}));
```

- [ ] **Step 5: Add DLQ CloudWatch alarm**

Insert this block after the existing `errorAlarm` definition and before the outputs section:

```typescript
// ── DLQ alarm ─────────────────────────────────────────────────────────────────
const dlqAlarm = new cloudwatch.Alarm(this, 'PipelineDLQAlarm', {
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
dlqAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));
```

- [ ] **Step 6: Build the CDK stack to check for TypeScript errors**

```bash
cd infra && npm run build
```

Expected: exits 0, no TypeScript errors.

- [ ] **Step 7: Synthesize the stack to verify CloudFormation output**

```bash
cd infra && npx cdk synth --context env=prod 2>&1 | tail -20
```

Expected: exits 0, prints CloudFormation YAML tail without errors. You should see `livewell-pipeline-dlq-prod` in the output.

- [ ] **Step 8: Commit**

```bash
git add infra/lib/livewell-stack.ts
git commit -m "feat: add DLQ, reduce Lambda timeout to 300s, add IAM self-invoke and DLQ alarm"
```

---

## Task 4: Deploy and smoke test

- [ ] **Step 1: Deploy the updated stack**

```bash
cd infra && npx cdk deploy --context env=prod --require-approval never
```

Expected: exits 0. Note the outputs — confirm `livewell-pipeline-dlq-prod` queue appears in the CloudFormation outputs or AWS console.

- [ ] **Step 2: Invoke the coordinator with an empty event**

```bash
aws lambda invoke \
  --function-name livewell-pipeline-fn-prod \
  --payload '{}' \
  --cli-binary-format raw-in-base64-out \
  /tmp/coordinator-response.json \
  --region us-west-1 && cat /tmp/coordinator-response.json
```

Expected output: `{"run_id": "<uuid>", "status": "running"}`

- [ ] **Step 3: Wait 60 seconds, then check DynamoDB for today's signals**

```bash
aws dynamodb scan \
  --table-name livewell-signals-prod \
  --filter-expression "begins_with(signal_id, :prefix)" \
  --expression-attribute-values '{":prefix": {"S": "EURUSD__2026"}}' \
  --region us-west-1 \
  --query "Items[0]" \
  --output json
```

Expected: a signal record for EURUSD with today's date.

- [ ] **Step 4: Verify all 19 signals were written**

```bash
aws dynamodb scan \
  --table-name livewell-signals-prod \
  --select COUNT \
  --region us-west-1 \
  --query "Count"
```

Expected: at least 19 (may be higher if previous runs wrote records).

- [ ] **Step 5: Check DLQ is empty**

```bash
aws sqs get-queue-attributes \
  --queue-url $(aws sqs get-queue-url --queue-name livewell-pipeline-dlq-prod --region us-west-1 --query QueueUrl --output text) \
  --attribute-names ApproximateNumberOfMessages \
  --region us-west-1
```

Expected: `"ApproximateNumberOfMessages": "0"`
