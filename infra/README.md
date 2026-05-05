# LIVEWELL Infrastructure

AWS CDK app that provisions the LIVEWELL production AWS resources.

## Prerequisites

- Node 20+
- AWS CLI configured with default profile pointing to the LIVEWELL account
- CDK CLI: already in devDependencies, no global install needed

## First-time setup (bootstrap)

CDK bootstrap creates a CDK toolkit stack in your account. Run once per account/region:

```bash
npm install
npx cdk bootstrap aws://ACCOUNT_ID/us-west-1
```

Replace `ACCOUNT_ID` with your AWS account ID:
```bash
aws sts get-caller-identity --query Account --output text
```

## Deploy

```bash
npx cdk deploy --context env=prod
```

## What gets created

| Resource | Name |
|---|---|
| S3 bucket | `livewell-data-prod` |
| DynamoDB table | `livewell-signals-prod` |
| DynamoDB table | `livewell-model-runs-prod` |
| DynamoDB table | `livewell-model-registry-prod` |
| IAM role | `livewell-pipeline-prod` |

## Tests

```bash
npm test
```

Tests use CDK assertions to verify construct properties without deploying.

## Teardown

Resources use `RemovalPolicy.RETAIN` — destroying the stack does **not** delete the S3 bucket or DynamoDB tables. Delete them manually if needed.
