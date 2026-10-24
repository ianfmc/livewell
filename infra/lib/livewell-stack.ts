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
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // GSI "by-instrument-date" (LW-208: latest signal per instrument) is LIVE on
    // livewell-signals-prod but intentionally NOT declared here. It was created
    // out-of-band (dynamodb update-table) to unblock LW-208, and CloudFormation
    // cannot adopt an already-existing GSI via a normal deploy ("index already
    // exists" -> UPDATE_FAILED). Leaving it undeclared keeps CFN from touching the
    // live index. FOLLOW-UP: adopt it via a CloudFormation IMPORT operation, then
    // restore this block (s3_key HASH + date RANGE, projection ALL) so IaC manages
    // it. Until then this is documented, intentional drift — do NOT re-add the
    // addGlobalSecondaryIndex call without first importing, or the deploy fails.
    // gstack-shortcut(dec-68acb037): unmanaged GSI, upgrade when CFN-import done.

    // ── DynamoDB: model runs ───────────────────────────────────────────────────
    const modelRunsTable = new dynamodb.Table(this, 'ModelRunsTable', {
      tableName: `livewell-model-runs-${env}`,
      partitionKey: { name: 'run_id', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'started_at', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── DynamoDB: model registry ───────────────────────────────────────────────
    const modelRegistryTable = new dynamodb.Table(this, 'ModelRegistryTable', {
      tableName: `livewell-model-registry-${env}`,
      partitionKey: { name: 'model_name', type: dynamodb.AttributeType.STRING },
      sortKey: { name: 'version', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── IAM role for pipeline compute ─────────────────────────────────────────
    const pipelineRole = new iam.Role(this, 'PipelineRole', {
      roleName: `livewell-pipeline-${env}`,
      assumedBy: new iam.CompositePrincipal(
        new iam.ServicePrincipal('lambda.amazonaws.com'),
        new iam.ServicePrincipal('ecs-tasks.amazonaws.com'),
      ),
      description: 'Assumed by LIVEWELL batch pipeline compute (Lambda or Fargate)',
    });

    // S3 permissions
    pipelineRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['s3:ListBucket'],
      resources: [bucket.bucketArn],
    }));
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
      resources: [
        ...tableArns,
        ...tableArns.map(arn => `${arn}/index/*`),
      ],
    }));

    // CloudWatch Logs permissions
    pipelineRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: [
        'logs:CreateLogGroup',
        'logs:CreateLogStream',
        'logs:PutLogEvents',
      ],
      resources: [
        cdk.Stack.of(this).formatArn({
          service: 'logs',
          resource: 'log-group',
          resourceName: '/aws/lambda/livewell-*',
          arnFormat: cdk.ArnFormat.COLON_RESOURCE_NAME,
        }),
        cdk.Stack.of(this).formatArn({
          service: 'logs',
          resource: 'log-group',
          resourceName: '/ecs/livewell-*',
          arnFormat: cdk.ArnFormat.COLON_RESOURCE_NAME,
        }),
      ],
    }));

    // ── Outputs ───────────────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'BucketName', { value: bucket.bucketName });
    new cdk.CfnOutput(this, 'SignalsTableName', { value: signalsTable.tableName });
    new cdk.CfnOutput(this, 'ModelRunsTableName', { value: modelRunsTable.tableName });
    new cdk.CfnOutput(this, 'ModelRegistryTableName', { value: modelRegistryTable.tableName });
    new cdk.CfnOutput(this, 'PipelineRoleArn', { value: pipelineRole.roleArn });

    // ── DLQ ───────────────────────────────────────────────────────────────────────
    const dlq = new sqs.Queue(this, 'PipelineDLQ', {
      queueName: `livewell-pipeline-dlq-${env}`,
      retentionPeriod: cdk.Duration.days(14),
    });

    // ── Pipeline Lambda ───────────────────────────────────────────────────────
    const alertEmail = this.node.tryGetContext('alertEmail') as string | undefined;

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

    // Allow the coordinator to invoke itself as workers.
    // Use a static ARN to avoid a CloudFormation circular dependency
    // (PipelineLambda → PipelineRoleDefaultPolicy → PipelineLambda).
    const pipelineLambdaArn = cdk.Stack.of(this).formatArn({
      service: 'lambda',
      resource: 'function',
      resourceName: `livewell-pipeline-fn-${env}`,
      arnFormat: cdk.ArnFormat.COLON_RESOURCE_NAME,
    });
    pipelineRole.addToPolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['lambda:InvokeFunction'],
      resources: [pipelineLambdaArn],
    }));

    // ── EventBridge schedule ──────────────────────────────────────────────────
    new events.Rule(this, 'PipelineSchedule', {
      ruleName: `livewell-pipeline-schedule-${env}`,
      schedule: events.Schedule.expression('cron(0 0 ? * MON-FRI *)'),
      targets: [new targets.LambdaFunction(pipelineLambda)],
    });

    // ── SNS alerts ────────────────────────────────────────────────────────────
    const alertTopic = new sns.Topic(this, 'AlertTopic', {
      topicName: `livewell-alerts-${env}`,
    });

    if (alertEmail) {
      alertTopic.addSubscription(new subscriptions.EmailSubscription(alertEmail));
    }

    // ── CloudWatch alarm ──────────────────────────────────────────────────────
    const errorAlarm = new cloudwatch.Alarm(this, 'PipelineErrorAlarm', {
      alarmName: `livewell-pipeline-errors-${env}`,
      metric: pipelineLambda.metricErrors({
        period: cdk.Duration.minutes(5),
        statistic: 'Sum',
      }),
      threshold: 0,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    errorAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));

    // ── DLQ alarm ─────────────────────────────────────────────────────────────────
    const dlqAlarm = new cloudwatch.Alarm(this, 'PipelineDLQAlarm', {
      alarmName: `livewell-pipeline-dlq-${env}`,
      metric: dlq.metricApproximateNumberOfMessagesVisible({
        period: cdk.Duration.minutes(5),
        statistic: 'Maximum',
      }),
      threshold: 0,
      evaluationPeriods: 1,
      comparisonOperator: cloudwatch.ComparisonOperator.GREATER_THAN_THRESHOLD,
      treatMissingData: cloudwatch.TreatMissingData.NOT_BREACHING,
    });
    dlqAlarm.addAlarmAction(new cloudwatchActions.SnsAction(alertTopic));

    // ── API Lambda (FastAPI + Mangum) ─────────────────────────────────────────
    // ANTHROPIC_API_KEY is fetched at RUNTIME by the Lambda from an SSM
    // SecureString (CloudFormation cannot inject an ssm-secure value into a
    // Lambda env var). We pass only the parameter NAME; builder.py resolves and
    // caches the decrypted value per cold start. Stored out-of-band once:
    // /livewell/<env>/anthropic-api-key. Future deploys need no secret handling.
    const anthropicKeyParamName = `/livewell/${env}/anthropic-api-key`;

    const apiLambda = new lambda.DockerImageFunction(this, 'ApiLambda', {
      functionName: `livewell-api-fn-${env}`,
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, '../../apps/api'),
        { file: 'Dockerfile.api' }
      ),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 512,
      timeout: cdk.Duration.seconds(60),
      environment: {
        LIVEWELL_ENV: env,
        LIVEWELL_BUCKET: bucket.bucketName,
        CORS_ORIGINS: (this.node.tryGetContext('corsOrigins') as string | undefined) ?? '*',
        ANTHROPIC_API_KEY_SSM_PARAM: anthropicKeyParamName,
        // Explain model, overridable via context; default stays the pinned Haiku
        // snapshot (LW-211 folded-in configurable-model item).
        ANTHROPIC_MODEL:
          (this.node.tryGetContext('anthropicModel') as string | undefined) ??
          'claude-haiku-4-5-20251001',
      },
    });

    // Allow the API Lambda to read + decrypt the Anthropic key parameter.
    apiLambda.addToRolePolicy(new iam.PolicyStatement({
      effect: iam.Effect.ALLOW,
      actions: ['ssm:GetParameter'],
      resources: [
        `arn:aws:ssm:${this.region}:${this.account}:parameter${anthropicKeyParamName}`,
      ],
    }));

    signalsTable.grantReadData(apiLambda);
    modelRegistryTable.grantReadData(apiLambda);
    bucket.grantRead(apiLambda);

    const apiUrl = apiLambda.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: ['*'],
        allowedMethods: [lambda.HttpMethod.GET],
        allowedHeaders: ['*'],
      },
    });

    new cdk.CfnOutput(this, 'ApiUrl', { value: apiUrl.url });

    // ── DynamoDB: trades (outcome tracking) ────────────────────────────────────
    const tradesTable = new dynamodb.Table(this, 'TradesTable', {
      tableName: `livewell-trades-${env}`,
      partitionKey: { name: 'trade_id', type: dynamodb.AttributeType.STRING },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      pointInTimeRecoverySpecification: { pointInTimeRecoveryEnabled: true },
      removalPolicy: cdk.RemovalPolicy.RETAIN,
    });

    // ── Outcome-resolver Lambda (intraday disciplined-exit resolution) ─────────
    // Runs on a weekday intraday schedule; resolves open trades past expiry by
    // fetching the close price (yfinance) and marking won/lost vs strike.
    // Entry: livewell.tracking.handler.handler (see Dockerfile.resolver).
    const resolverLambda = new lambda.DockerImageFunction(this, 'ResolverLambda', {
      functionName: `livewell-outcome-resolver-fn-${env}`,
      code: lambda.DockerImageCode.fromImageAsset(
        path.join(__dirname, '../../apps/api'),
        { file: 'Dockerfile.resolver' }
      ),
      architecture: lambda.Architecture.ARM_64,
      memorySize: 256,
      timeout: cdk.Duration.seconds(300),
      environment: {
        LIVEWELL_ENV: env,
      },
    });

    tradesTable.grantReadWriteData(resolverLambda);
    signalsTable.grantReadData(resolverLambda);

    // Intraday resolution schedules (ET in the construct id; cron is UTC).
    // 11:05 ET = 16:05 UTC, 14:05 = 19:05, 16:05 = 21:05, 17:05 = 22:05.
    new events.Rule(this, 'Resolver1100ET', {
      ruleName: `livewell-resolver-resolver1100et-${env}`,
      schedule: events.Schedule.expression('cron(5 16 ? * MON-FRI *)'),
      targets: [new targets.LambdaFunction(resolverLambda)],
    });
    new events.Rule(this, 'Resolver1400ET', {
      ruleName: `livewell-resolver-resolver1400et-${env}`,
      schedule: events.Schedule.expression('cron(5 19 ? * MON-FRI *)'),
      targets: [new targets.LambdaFunction(resolverLambda)],
    });
    new events.Rule(this, 'Resolver1600ET', {
      ruleName: `livewell-resolver-resolver1600et-${env}`,
      schedule: events.Schedule.expression('cron(5 21 ? * MON-FRI *)'),
      targets: [new targets.LambdaFunction(resolverLambda)],
    });
    new events.Rule(this, 'Resolver1700ET', {
      ruleName: `livewell-resolver-resolver1700et-${env}`,
      schedule: events.Schedule.expression('cron(5 22 ? * MON-FRI *)'),
      targets: [new targets.LambdaFunction(resolverLambda)],
    });

    // ── Additional outputs ────────────────────────────────────────────────────
    new cdk.CfnOutput(this, 'PipelineLambdaArn', { value: pipelineLambda.functionArn });
    new cdk.CfnOutput(this, 'AlertTopicArn', { value: alertTopic.topicArn });
    new cdk.CfnOutput(this, 'TradesTableName', { value: tradesTable.tableName });
  }
}
