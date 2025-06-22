# Migration Demo

Automated cloud migration using GenAI and MCP (Model Context Protocol) servers. This project demonstrates a 1-click migration tool that leverages multiple MCP servers to migrate VPC infrastructure from Alibaba Cloud to AWS.

## Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   LangGraph     │───▶│  Alibaba Cloud  │───▶│   CDK MCP       │───▶│   AWS Deploy    │
│   Workflow      │    │   MCP Server    │    │   Server        │    │                 │
│  Orchestrator   │    │ (Extract VPC)   │    │ (Generate CDK)  │    │ (cdk deploy)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Components

#### 1. **LangGraph Workflow Orchestrator**
- Coordinates the end-to-end migration process
- Manages state between different steps
- Handles error recovery and rollback

#### 2. **Alibaba Cloud MCP Server**
- **Server**: `uvx alibaba-cloud-ops-mcp-server@latest`
- **Purpose**: Extract VPC configurations from Alibaba Cloud
- **Authentication**: Uses AK/SK (Access Key ID/Secret)

#### 3. **CDK MCP Server**
- **Server**: `uvx awslabs.cdk-mcp-server@latest`
- **Purpose**: Generate AWS CDK TypeScript code
- **Integration**: Uses Bedrock LLM for intelligent code generation

#### 4. **Migration Workflow**
- **Node 1**: Extract VPC data from Alibaba Cloud
- **Node 2**: Transform data (Alibaba format → AWS format)
- **Node 3**: Generate CDK project with real code
- **Node 4**: Deploy infrastructure to AWS

## Quick Start

### Prerequisites

```bash
# Install UV
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install AWS CDK
npm install -g aws-cdk

# Configure AWS credentials
aws configure

# Set Alibaba Cloud credentials (optional - will use mock data if not provided)
export ALIBABA_CLOUD_ACCESS_KEY_ID="your_access_key_id"
export ALIBABA_CLOUD_ACCESS_KEY_SECRET="your_access_key_secret"
```

### Installation

```bash
git clone <repository>
cd migration-demo/src
uv sync
```

### Usage

#### Basic Migration
```bash
# Migrate with mock data (no Alibaba Cloud credentials needed)
uv run migration_workflow.py --project-name my-vpc-migration --target-dir ./output

# Migrate specific VPC from Alibaba Cloud
uv run migration_workflow.py \
  --project-name my-vpc-migration \
  --target-dir ./output \
  --vpc-id vpc-uf6f7l4fg90oxkcdtw0tn \
  --region cn-hangzhou

# Provide credentials via command line
uv run migration_workflow.py \
  --project-name my-vpc-migration \
  --target-dir ./output \
  --ak-id "your_access_key_id" \
  --ak-secret "your_access_key_secret"
```

#### Using the Wrapper Script
```bash
./migrate --project-name my-vpc-migration --target-dir ./output --vpc-id vpc-123
```

## Project Structure

```
migration-demo/
├── src/
│   ├── migration_workflow.py       # Main LangGraph workflow
│   ├── aliyun_mcp_client.py       # Alibaba Cloud MCP client
│   ├── cdk-mcp-cli/               # CDK MCP client tools
│   │   ├── cdk_cli.py             # CDK code generation CLI
│   │   └── test_cdk_mcp.py        # Direct MCP testing
│   ├── config/                    # Configuration files
│   └── utils/                     # Utility functions
├── architecture/                  # Design documents and diagrams
├── provider-mcp/                  # MCP server implementations
└── cdk/                          # CDK deployment infrastructure
```

## MCP Server Configuration

### Alibaba Cloud MCP Server
```json
{
  "mcpServers": {
    "alibaba-cloud-ops-mcp-server": {
      "timeout": 600,
      "command": "uvx",
      "args": ["alibaba-cloud-ops-mcp-server@latest"],
      "env": {
        "ALIBABA_CLOUD_ACCESS_KEY_ID": "Your Access Key ID",
        "ALIBABA_CLOUD_ACCESS_KEY_SECRET": "Your Access Key SECRET"
      }
    }
  }
}
```

### CDK MCP Server
```json
{
  "mcpServers": {
    "awslabs.cdk-mcp-server": {
      "command": "uvx",
      "args": ["awslabs.cdk-mcp-server@latest"],
      "env": {
        "FASTMCP_LOG_LEVEL": "ERROR"
      }
    }
  }
}
```

## Testing Individual Components

### Test Alibaba Cloud MCP Client
```bash
# List VPCs in a region
./test_aliyun_mcp --list-vpcs --region cn-hangzhou

# Get specific VPC info
./test_aliyun_mcp --vpc-id vpc-123 --region cn-hangzhou
```

### Test CDK MCP Client
```bash
cd cdk-mcp-cli

# Interactive mode
uv run cdk_cli.py --interactive

# Generate specific infrastructure
uv run cdk_cli.py generate a VPC with 2 subnets in 2 AZs
```

## Generated Output

The migration workflow creates:

1. **Complete CDK Project**
   - TypeScript CDK code
   - Proper project structure (`cdk init`)
   - Ready for deployment

2. **AWS Infrastructure**
   - VPC with proper CIDR blocks
   - Subnets distributed across AZs
   - Security groups with migrated rules
   - DNS settings enabled

3. **Example Output Structure**
   ```
   output/my-vpc-migration/
   ├── lib/my-vpc-migration-stack.ts    # Generated CDK code
   ├── bin/my-vpc-migration.ts          # CDK app entry point
   ├── cdk.out/                         # Deployment artifacts
   └── [standard CDK files]
   ```

## Features

### ✅ **Implemented**
- LangGraph workflow orchestration
- Real Alibaba Cloud VPC extraction via MCP server
- CDK code generation via MCP server + Bedrock LLM
- Automatic CDK project creation and deployment
- Error handling with fallback to mock data
- Clean TypeScript code generation (no explanations)

### 🚧 **Planned**
- Support for more AWS services (EC2, RDS, etc.)
- Multiple cloud provider sources
- Advanced networking features (NAT Gateway, VPN)
- Cost estimation integration
- Rollback mechanisms

## Troubleshooting

### Common Issues

**Alibaba Cloud MCP Server Not Found**
```bash
# Install the server manually
uvx alibaba-cloud-ops-mcp-server@latest --help
```

**AWS Deployment Fails**
```bash
# Check AWS credentials
aws sts get-caller-identity

# Bootstrap CDK if needed
cd output/my-vpc-migration
cdk bootstrap
```

**Mock Data Used Instead of Real Data**
- Ensure `ALIBABA_CLOUD_ACCESS_KEY_ID` and `ALIBABA_CLOUD_ACCESS_KEY_SECRET` are set
- Check network connectivity to Alibaba Cloud APIs
- Verify MCP server installation

### Debug Mode
```bash
export FASTMCP_LOG_LEVEL=DEBUG
uv run migration_workflow.py --project-name test --target-dir ./debug
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
