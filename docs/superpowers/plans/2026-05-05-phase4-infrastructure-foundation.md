# Phase 4 Infrastructure Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create the CDK TypeScript app in `infra/` that provisions the LIVEWELL S3 bucket, three DynamoDB tables, and a pipeline IAM role in AWS `us-west-1`.

**Architecture:** Single CDK stack (`LivewellStack`) parameterised by `env` context variable (default `prod`). All resources are named `livewell-*-{env}`. Tests use `@aws-cdk/assertions` to verify construct properties without deploying.

**Tech Stack:** AWS CDK v2 (TypeScript), `aws-cdk-lib`, `@aws-cdk/assertions` (test), Node 20, Jest (CDK default test runner).

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `infra/package.json` | Create | CDK app dependencies |
| `infra/tsconfig.json` | Create | TypeScript config for CDK |
| `infra/cdk.json` | Create | CDK app config |
| `infra/bin/livewell.ts` | Create | CDK entry point, reads `env` context |
| `infra/lib/livewell-stack.ts` | Create | All constructs: S3, DynamoDB ×3, IAM role |
| `infra/test/livewell-stack.test.ts` | Create | CDK assertions tests |
| `infra/README.md` | Create | Bootstrap and deploy instructions |
| `infra/.gitignore` | Create | Ignore node_modules, cdk.out |

---

## Task 1: Scaffold the CDK app

**Files:**
- Create: `infra/package.json`
- Create: `infra/tsconfig.json`
- Create: `infra/cdk.json`
- Create: `infra/.gitignore`

- [ ] **Step 1: Create `infra/package.json`**

```json
{
  "name": "livewell-infra",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "build": "tsc",
    "test": "jest",
    "cdk": "cdk"
  },
  "devDependencies": {
    "@types/jest": "^29.5.12",
    "@types/node": "22.13.9",
    "aws-cdk": "2.1120.0",
    "jest": "^29.7.0",
    "ts-jest": "^29.2.5",
    "ts-node": "^10.9.2",
    "typescript": "~5.7.2"
  },
  "dependencies": {
    "aws-cdk-lib": "2.1120.0",
    "constructs": "^10.0.0"
  },
  "jest": {
    "testEnvironment": "node",
    "roots": ["<rootDir>/test"],
    "testMatch": ["**/*.test.ts"],
    "transform": {
      "^.+\\.tsx?$": "ts-jest"
    }
  }
}
```

- [ ] **Step 2: Create `infra/tsconfig.json`**

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "module": "commonjs",
    "lib": ["es2020"],
    "declaration": true,
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noImplicitThis": true,
    "alwaysStrict": true,
    "outDir": "./dist",
    "rootDir": "./",
    "esModuleInterop": true,
    "skipLibCheck": true,
    "forceConsistentCasingInFileNames": true
  },
  "exclude": ["node_modules", "cdk.out", "dist"]
}
```

- [ ] **Step 3: Create `infra/cdk.json`**

```json
{
  "app": "npx ts-node --prefer-ts-exts bin/livewell.ts",
  "watch": {
    "include": ["**"],
    "exclude": [
      "README.md",
      "cdk*.json",
      "**/*.d.ts",
      "**/*.js",
      "tsconfig.json",
      "package*.json",
      "node_modules",
      "test"
    ]
  },
  "context": {
    "env": "prod"
  }
}
```

- [ ] **Step 4: Create `infra/.gitignore`**

```
node_modules/
cdk.out/
dist/
*.js
*.d.ts
!jest.config.js
```

- [ ] **Step 5: Install dependencies**

```bash
export NVM_DIR="$HOME/.nvm" && source "$NVM_DIR/nvm.sh" && nvm use 20
cd infra
npm install
```

Expected: `node_modules/` created, no errors.

- [ ] **Step 6: Commit scaffold**

```bash
git add infra/package.json infra/package-lock.json infra/tsconfig.json infra/cdk.json infra/.gitignore
git rm infra/.gitkeep
git commit -m "chore: scaffold CDK app in infra/"
```

---

## Task 2: Write the failing CDK assertions tests

**Files:**
- Create: `infra/test/livewell-stack.test.ts`

- [ ] **Step 1: Create the test file**

Create `infra/test/livewell-stack.test.ts`:

```typescript
import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import { LivewellStack } from '../lib/livewell-stack';

function makeTemplate(env = 'test'): Template {
  const app = new cdk.App({ context: { env } });
  const stack = new LivewellStack(app, 'TestStack', {
    env: { account: '123456789012', region: 'us-west-1' },
  });
  return Template.fromStack(stack);
}

describe('S3 bucket', () => {
  const template = makeTemplate();

  it('exists with versioning enabled', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketName: 'livewell-data-test',
      VersioningConfiguration: { Status: 'Enabled' },
    });
  });

  it('blocks all public access', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      PublicAccessBlockConfiguration: {
        BlockPublicAcls: true,
        BlockPublicPolicy: true,
        IgnorePublicAcls: true,
        RestrictPublicBuckets: true,
      },
    });
  });

  it('has SSE-S3 encryption', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      BucketEncryption: {
        ServerSideEncryptionConfiguration: [
          {
            ServerSideEncryptionByDefault: {
              SSEAlgorithm: 'AES256',
            },
          },
        ],
      },
    });
  });

  it('has lifecycle rule transitioning to IA after 90 days', () => {
    template.hasResourceProperties('AWS::S3::Bucket', {
      LifecycleConfiguration: {
        Rules: [
          {
            Status: 'Enabled',
            Transitions: [
              {
                StorageClass: 'STANDARD_IA',
                TransitionInDays: 90,
              },
            ],
          },
        ],
      },
    });
  });
});

describe('DynamoDB tables', () => {
  const template = makeTemplate();

  it('creates livewell-signals-test with correct key schema', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'livewell-signals-test',
      KeySchema: [{ AttributeName: 'signal_id', KeyType: 'HASH' }],
      AttributeDefinitions: [{ AttributeName: 'signal_id', AttributeType: 'S' }],
      BillingMode: 'PAY_PER_REQUEST',
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });

  it('creates livewell-model-runs-test with partition and sort key', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'livewell-model-runs-test',
      KeySchema: [
        { AttributeName: 'run_id', KeyType: 'HASH' },
        { AttributeName: 'started_at', KeyType: 'RANGE' },
      ],
      AttributeDefinitions: [
        { AttributeName: 'run_id', AttributeType: 'S' },
        { AttributeName: 'started_at', AttributeType: 'S' },
      ],
      BillingMode: 'PAY_PER_REQUEST',
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });

  it('creates livewell-model-registry-test with partition and sort key', () => {
    template.hasResourceProperties('AWS::DynamoDB::Table', {
      TableName: 'livewell-model-registry-test',
      KeySchema: [
        { AttributeName: 'model_name', KeyType: 'HASH' },
        { AttributeName: 'version', KeyType: 'RANGE' },
      ],
      AttributeDefinitions: [
        { AttributeName: 'model_name', AttributeType: 'S' },
        { AttributeName: 'version', AttributeType: 'S' },
      ],
      BillingMode: 'PAY_PER_REQUEST',
      PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true },
    });
  });
});

describe('IAM role', () => {
  const template = makeTemplate();

  it('creates pipeline role with correct name', () => {
    template.hasResourceProperties('AWS::IAM::Role', {
      RoleName: 'livewell-pipeline-test',
    });
  });

  it('pipeline role has S3 permissions on data bucket', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: [
          {
            Effect: 'Allow',
            Action: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
          },
        ],
      },
    });
  });

  it('pipeline role has DynamoDB permissions', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: [
          {
            Effect: 'Allow',
            Action: [
              'dynamodb:PutItem',
              'dynamodb:GetItem',
              'dynamodb:UpdateItem',
              'dynamodb:Query',
            ],
          },
        ],
      },
    });
  });

  it('pipeline role has CloudWatch Logs permissions', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: [
          {
            Effect: 'Allow',
            Action: [
              'logs:CreateLogGroup',
              'logs:CreateLogStream',
              'logs:PutLogEvents',
            ],
          },
        ],
      },
    });
  });
});
```

- [ ] **Step 2: Run the tests — verify they fail**

```bash
cd infra
npm test
```

Expected: compile error — `../lib/livewell-stack` not found.

---

## Task 3: Implement the CDK stack

**Files:**
- Create: `infra/bin/livewell.ts`
- Create: `infra/lib/livewell-stack.ts`

- [ ] **Step 1: Create `infra/bin/livewell.ts`**

```typescript
#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { LivewellStack } from '../lib/livewell-stack';

const app = new cdk.App();
const env = app.node.tryGetContext('env') ?? 'prod';

new LivewellStack(app, `LivewellStack-${env}`, {
  env: { account: process.env.CDK_DEFAULT_ACCOUNT, region: 'us-west-1' },
  stackName: `livewell-${env}`,
});
```

- [ ] **Step 2: Create `infra/lib/livewell-stack.ts`**

```typescript
import * as cdk from 'aws-cdk-lib';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as iam from 'aws-cdk-lib/aws-iam';
import { Construct } from 'constructs';

export class LivewellStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    const env = this.node.tryGetContext('env') ?? 'prod';

    // ── S3 bucket ─────────────────────────────────────────────────────────────
    const bucket = new s3.Bucket(this, 'DataBucket', {
      bucketName: `livewell-data-${env}`,
      versioned: true,
      encryption: s3.BucketEncryption.S3_MANAGED,
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      lifecycleRules: [
        {
          enabled: true,
          transitions: [
            {
              storageClass: s3.StorageClass.INFREQUENT_ACCESS,
              transitionAfter: cdk.Duration.days(90),
            },
          ],
        },
      ],
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── DynamoDB: signals ─────────────────────────────────────────────────────
    const signalsTable = new dynamodb.Table(this, 'SignalsTable', {
      tableName: `livewell-signals-${env}`,
      partitionKey: { name: 'signal_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── DynamoDB: model runs ───────────────────────────────────────────────────
    const modelRunsTable = new dynamodb.Table(this, 'ModelRunsTable', {
      tableName: `livewell-model-runs-${env}`,
      partitionKey: { name: 'run_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'started_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── DynamoDB: model registry ───────────────────────────────────────────────
    const modelRegistryTable = new dynamodb.Table(this, 'ModelRegistryTable', {
      tableName: `livewell-model-registry-${env}`,
      partitionKey: { name: 'model_name', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'version', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecovery: true,
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── IAM role for pipeline compute ─────────────────────────────────────────
    const pipelineRole = new iam.Role(this, 'PipelineRole', {
      roleName: `livewell-pipeline-${env}`,
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      description: 'Assumed by LIVEWELL batch pipeline compute (Lambda or Fargate)',
    });

    // S3 permissions
    pipelineRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
      resources: [`${bucket.bucketArn}/*`],
    }));

    // DynamoDB permissions
    const tableArns = [
      signalsTable.tableArn,
      modelRunsTable.tableArn,
      modelRegistryTable.tableArn,
    ];
    pipelineRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'dynamodb:PutItem',
        'dynamodb:GetItem',
        'dynamodb:UpdateItem',
        'dynamodb:Query',
      ],
      resources: tableArns,
    }));

    // CloudWatch Logs permissions
    pipelineRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: ['*'],
    }));

    // ── Outputs ───────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'BucketName', { value: bucket.bucketName });
    new cdk.CfnOutput(this, 'SignalsTableName', { value: signalsTable.tableName });
    new cdk.CfnOutput(this, 'ModelRunsTableName', { value: modelRunsTable.tableName });
    new cdk.CfnOutput(this, 'ModelRegistryTableName', { value: modelRegistryTable.tableName });
    new cdk.CfnOutput(this, 'PipelineRoleArn', { value: pipelineRole.roleArn });
  }
}
```

- [ ] **Step 3: Run the tests — verify they pass**

```bash
cd infra
npm test
```

Expected: all tests pass. If any assertion test fails with a property mismatch, read the output carefully — CDK sometimes generates slightly different CloudFormation property names. Adjust the test assertion to match what CDK actually generates (e.g. `PointInTimeRecoveryEnabled` vs `PointInTimeRecoverySpecification`).

- [ ] **Step 4: Verify CDK synth succeeds (no AWS account needed)**

```bash
npx cdk synth --context env=prod 2>&1 | head -20
```

Expected: CloudFormation template printed to stdout, no errors.

- [ ] **Step 5: Commit**

```bash
git add infra/bin/ infra/lib/ infra/test/
git commit -m "feat: add LivewellStack — S3, DynamoDB, IAM role"
```

---

## Task 4: Write the README

**Files:**
- Create: `infra/README.md`

- [ ] **Step 1: Create `infra/README.md`**

You will need to fill in `ACCOUNT_ID` with your actual AWS account ID before running bootstrap. Find it with `aws sts get-caller-identity --query Account --output text`.

```markdown
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
```

- [ ] **Step 2: Commit**

```bash
git add infra/README.md
git commit -m "docs: add infra README with bootstrap and deploy instructions"
```

---

## Task 5: Deploy to AWS

> This task requires live AWS credentials. Run it once you are ready to provision real resources.

- [ ] **Step 1: Get your account ID**

```bash
aws sts get-caller-identity --query Account --output text
```

Copy the output — you'll need it in the next step.

- [ ] **Step 2: Update README with your account ID**

Open `infra/README.md` and replace `ACCOUNT_ID` with the actual value from Step 1.

```bash
git add infra/README.md
git commit -m "docs: fill in AWS account ID in infra README"
```

- [ ] **Step 3: Bootstrap CDK**

```bash
cd infra
npx cdk bootstrap aws://YOUR_ACCOUNT_ID/us-west-1
```

Expected output:
```
 ⏳  Bootstrapping environment aws://YOUR_ACCOUNT_ID/us-west-1...
 ✅  Environment aws://YOUR_ACCOUNT_ID/us-west-1 bootstrapped.
```

- [ ] **Step 4: Deploy the stack**

```bash
npx cdk deploy --context env=prod
```

CDK will show the IAM changes it will make and ask for confirmation. Review them and type `y`.

Expected output ends with:
```
✅  livewell-prod

Outputs:
livewell-prod.BucketName = livewell-data-prod
livewell-prod.SignalsTableName = livewell-signals-prod
livewell-prod.ModelRunsTableName = livewell-model-runs-prod
livewell-prod.ModelRegistryTableName = livewell-model-registry-prod
livewell-prod.PipelineRoleArn = arn:aws:iam::ACCOUNT_ID:role/livewell-pipeline-prod
```

- [ ] **Step 5: Verify in AWS Console**

Check the following in the AWS Console (us-west-1):
- S3: `livewell-data-prod` bucket exists with versioning enabled
- DynamoDB: all three tables exist in `us-west-1`
- IAM: `livewell-pipeline-prod` role exists

---

## Self-Review

**Spec coverage:**
- ✅ S3 bucket with versioning, SSE-S3, block public access, lifecycle rule (Task 3)
- ✅ DynamoDB signals table (Task 3)
- ✅ DynamoDB model-runs table with sort key (Task 3)
- ✅ DynamoDB model-registry table with sort key (Task 3)
- ✅ IAM role with S3 + DynamoDB + CloudWatch permissions (Task 3)
- ✅ CDK assertions tests (Task 2)
- ✅ Bootstrap + deploy instructions (Task 4)
- ✅ `env` parameterisation (Task 1 + Task 3)

**Placeholder scan:** No TBD or TODO in implementation steps. `ACCOUNT_ID` in README is intentional — Task 5 Step 2 instructs the engineer to fill it in.

**Type consistency:** `LivewellStack` defined in Task 3 Step 2, imported in Task 3 Step 1 (bin) and Task 2 (tests) — consistent.
