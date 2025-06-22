#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { MyVpcMigrationStack } from '../lib/my-vpc-migration-stack';

const app = new cdk.App();
new MyVpcMigrationStack(app, 'MyVpcMigrationStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});
