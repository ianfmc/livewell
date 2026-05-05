# Phase 4 Infrastructure Foundation Design

## Goal

Create the AWS infrastructure foundation for LIVEWELL's production batch pipeline: an S3 bucket for analytical data, three DynamoDB tables for operational records, an IAM role for the pipeline, and a CDK TypeScript app to deploy it all.

## Scope

This is sub-project 1 of Phase 4. It builds the storage and identity layer only — no compute (Lambda/Fargate), no scheduling (EventBridge), no pipeline code. Those are sub-projects 2 and 3.

## Architecture

Single AWS CDK stack (`LivewellStack`) in `infra/`, parameterised by `env` (default: `prod`). Deployed to `us-west-1` using the default AWS credentials profile. Bootstrap is one-time; subsequent changes use `cdk deploy`.

## Repository Structure

```
infra/
  bin/livewell.ts          ← CDK app entry point
  lib/livewell-stack.ts    ← single stack: S3 + DynamoDB + IAM
  cdk.json
  package.json
  tsconfig.json
  README.md                ← bootstrap and deploy instructions
```

## S3 Bucket

**Name:** `livewell-data-{env}`

**Configuration:**
- Versioning enabled
- Server-side encryption: SSE-S3 (S3-managed keys)
- Block all public access
- Lifecycle rule: transition to S3 Infrequent Access after 90 days

**Key prefixes:**
```
raw/{s3_key}/1d/{year}.parquet           ← ingested price data
features/{s3_key}/1d/{year}.parquet      ← computed indicators
signals/{s3_key}/1d/{year}.parquet       ← scored signals
models/{model_name}/{version}/           ← serialized model artifacts
training/datasets/                       ← feature tables for training runs
training/metrics/                        ← validation results
```

## DynamoDB Tables

All tables use on-demand billing and have point-in-time recovery enabled. No TTL — records are kept indefinitely.

### `livewell-signals-{env}`

One record per scored signal per instrument per day.

| Attribute | Type | Role |
|---|---|---|
| `signal_id` | String | Partition key (`{s3_key}__{iso_date}`) |
| `s3_key` | String | Instrument identifier |
| `date` | String | ISO date |
| `direction` | String | `buy` / `sell` / `none` |
| `signal_valid` | Boolean | Whether signal passed all pipeline stages |
| `score` | Number | Model probability score |
| `model_version` | String | Version of model used |
| `run_id` | String | FK to model-runs table |
| `created_at` | String | ISO timestamp |

### `livewell-model-runs-{env}`

One record per pipeline execution (ingestion → features → inference → signals).

| Attribute | Type | Role |
|---|---|---|
| `run_id` | String | Partition key (UUID) |
| `started_at` | String | Sort key (ISO timestamp) |
| `status` | String | `running` / `completed` / `failed` |
| `model_version` | String | Model version used |
| `instruments` | List | Instruments processed |
| `error` | String | Error message if failed |
| `completed_at` | String | ISO timestamp |

### `livewell-model-registry-{env}`

One record per promoted model version.

| Attribute | Type | Role |
|---|---|---|
| `model_name` | String | Partition key (e.g. `logistic_regression`) |
| `version` | String | Sort key (e.g. `v1`) |
| `s3_path` | String | S3 URI to serialized artifact |
| `promoted_at` | String | ISO timestamp |
| `metrics` | Map | Brier score, win rate, EV |
| `status` | String | `active` / `archived` |

## IAM Role

**Name:** `livewell-pipeline-{env}`

Assumed by the batch pipeline compute (Lambda or Fargate — wired in sub-project 2). Permissions:

- **S3:** `GetObject`, `PutObject`, `DeleteObject` on `livewell-data-{env}/*`
- **DynamoDB:** `PutItem`, `GetItem`, `UpdateItem`, `Query` on all three tables
- **CloudWatch Logs:** `CreateLogGroup`, `CreateLogStream`, `PutLogEvents`

No wildcard actions. No cross-account access.

## Bootstrap and Deployment

One-time bootstrap (creates CDK toolkit stack in the account):
```bash
cd infra
npm install
npx cdk bootstrap aws://ACCOUNT_ID/us-west-1
```

Deploy (first time and all subsequent changes):
```bash
npx cdk deploy --context env=prod
```

Uses the default AWS credentials profile. Account ID goes in `README.md`.

## Testing

CDK constructs are tested with `@aws-cdk/assertions`. Tests verify:
- S3 bucket has versioning enabled, public access blocked, SSE-S3 encryption, lifecycle rule
- All three DynamoDB tables exist with correct key schema, on-demand billing, PITR enabled
- IAM role exists with correct trust policy and permission boundaries

## What This Does Not Include

- Lambda/Fargate compute (sub-project 2)
- EventBridge scheduling (sub-project 2)
- Model serialization and artifact upload (sub-project 3)
- Monitoring/alerting (sub-project 2)
