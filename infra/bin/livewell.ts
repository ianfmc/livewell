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
