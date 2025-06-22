import { Stack, StackProps } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as ec2 from 'aws-cdk-lib/aws-ec2';

export class MyVpcMigrationStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const vpc = new ec2.Vpc(this, 'TestVpc', {
      vpcName: 'test',
      cidr: '10.0.0.0/16',
      enableDnsHostnames: true,
      enableDnsSupport: true,
      maxAzs: 2,
      subnetConfiguration: [
        {
          cidrMask: 24,
          name: 'subnet_1',
          subnetType: ec2.SubnetType.PUBLIC,
        },
        {
          cidrMask: 24,
          name: 'subnet_2',
          subnetType: ec2.SubnetType.PUBLIC,
        }
      ]
    });

    const securityGroup = new ec2.SecurityGroup(this, 'DefaultSecurityGroup', {
      vpc,
      allowAllOutbound: true,
      description: 'Default security group with web ports'
    });

    securityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(80),
      'Allow HTTP traffic'
    );

    securityGroup.addIngressRule(
      ec2.Peer.anyIpv4(),
      ec2.Port.tcp(443),
      'Allow HTTPS traffic'
    );
  }
}