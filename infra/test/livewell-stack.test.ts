import * as cdk from 'aws-cdk-lib';
import { Match, Template } from 'aws-cdk-lib/assertions';
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

  it('has RETAIN removal policy', () => {
    template.hasResource('AWS::S3::Bucket', {
      DeletionPolicy: 'Retain',
      UpdateReplacePolicy: 'Retain',
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

  it('signals table has RETAIN removal policy', () => {
    template.hasResource('AWS::DynamoDB::Table', {
      Properties: { TableName: 'livewell-signals-test' },
      DeletionPolicy: 'Retain',
      UpdateReplacePolicy: 'Retain',
    });
  });

  it('model-runs table has RETAIN removal policy', () => {
    template.hasResource('AWS::DynamoDB::Table', {
      Properties: { TableName: 'livewell-model-runs-test' },
      DeletionPolicy: 'Retain',
      UpdateReplacePolicy: 'Retain',
    });
  });

  it('model-registry table has RETAIN removal policy', () => {
    template.hasResource('AWS::DynamoDB::Table', {
      Properties: { TableName: 'livewell-model-registry-test' },
      DeletionPolicy: 'Retain',
      UpdateReplacePolicy: 'Retain',
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

  it('pipeline role has S3 permissions scoped to data bucket', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Action: ['s3:GetObject', 's3:PutObject', 's3:DeleteObject'],
            Resource: Match.objectLike({ 'Fn::Join': Match.anyValue() }),
          }),
        ]),
      },
    });
  });

  it('pipeline role has DynamoDB permissions', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Action: [
              'dynamodb:PutItem',
              'dynamodb:GetItem',
              'dynamodb:UpdateItem',
              'dynamodb:Query',
            ],
          }),
        ]),
      },
    });
  });

  it('pipeline role has CloudWatch Logs permissions', () => {
    template.hasResourceProperties('AWS::IAM::Policy', {
      PolicyDocument: {
        Statement: Match.arrayWith([
          Match.objectLike({
            Effect: 'Allow',
            Action: [
              'logs:CreateLogGroup',
              'logs:CreateLogStream',
              'logs:PutLogEvents',
            ],
          }),
        ]),
      },
    });
  });
});

describe('Pipeline Lambda', () => {
  const template = makeTemplate();

  it('exists with correct memory and timeout', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      MemorySize: 512,
      Timeout: 600,
    });
  });

  it('has correct environment variables', () => {
    template.hasResourceProperties('AWS::Lambda::Function', {
      Environment: {
        Variables: Match.objectLike({
          LIVEWELL_ENV: 'test',
          AWS_DEFAULT_REGION: 'us-west-1',
        }),
      },
    });
  });
});

describe('EventBridge schedule', () => {
  const template = makeTemplate();

  it('has cron rule targeting Lambda', () => {
    template.hasResourceProperties('AWS::Events::Rule', {
      ScheduleExpression: 'cron(0 0 * * ? *)',
      State: 'ENABLED',
    });
  });
});

describe('SNS and CloudWatch alarm', () => {
  const template = makeTemplate();

  it('creates SNS topic', () => {
    template.resourceCountIs('AWS::SNS::Topic', 1);
  });

  it('creates CloudWatch alarm on Lambda errors', () => {
    template.hasResourceProperties('AWS::CloudWatch::Alarm', {
      MetricName: 'Errors',
      Namespace: 'AWS/Lambda',
      ComparisonOperator: 'GreaterThanThreshold',
      Threshold: 0,
    });
  });
});
