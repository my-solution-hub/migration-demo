# CDK Infrastructure

This directory contains AWS CDK code for deploying the Alibaba Cloud MCP server in the cloud.

## Structure
- `lib/` - CDK stack definitions
- `bin/` - CDK app entry points
- `test/` - CDK unit tests
- `config/` - Environment-specific configurations

## Stacks
1. **MCP Server Stack** - Deploys Alibaba Cloud MCP server as Lambda/Container
2. **Networking Stack** - VPC and networking for MCP server infrastructure
3. **Security Stack** - IAM roles, security groups, and access controls
4. **Monitoring Stack** - CloudWatch logs, metrics, and alarms

## Deployment
- Supports multiple environments (dev, staging, prod)
- Uses CDK context for environment-specific configurations
- Includes proper tagging and resource naming conventions
