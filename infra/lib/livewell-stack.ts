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
