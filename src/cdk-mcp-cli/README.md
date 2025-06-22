# MCP CLI Test Tools

This directory contains CLI tools for testing and interacting with MCP (Model Context Protocol) servers, specifically designed for CDK code generation and cloud migration workflows.

## Architecture Overview

### MCP Client-Server Architecture

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Bedrock LLM   │◄──►│   MCP Client    │◄──►│   MCP Server    │
│   (Claude)      │    │   (This CLI)    │    │   (CDK Tools)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘

### Components

#### 1. **CDK MCP Server**

- **Server**: `uvx awslabs.cdk-mcp-server@latest`
- **Tools Available**:
  - `CDKGeneralGuidance` - General CDK best practices and code generation
  - `SearchGenAICDKConstructs` - Search for GenAI CDK constructs
  - `CheckCDKNagSuppressions` - Validate CDK Nag suppressions
  - `ExplainCDKNagRule` - Explain specific CDK Nag rules

#### 2. **Bedrock LLM Client**

- **Model**: `anthropic.claude-3-5-haiku-20241022-v1:0`
- **Region**: `us-west-2`
- **Role**: Processes plaintext input and orchestrates MCP tool calls

#### 3. **CLI Interface**

- **Interactive Mode**: Continuous conversation with the MCP server
- **Command Mode**: Single command execution with output

## Files

### `cdk_cli.py`

Main CLI application that:

- Connects to CDK MCP server using uvx
- Uses Bedrock LLM to process plaintext descriptions
- Orchestrates tool calls between LLM and MCP server
- Returns generated CDK code

### `test_cdk_mcp.py`

Direct MCP server testing tool for:

- Testing MCP server connectivity
- Exploring available tools
- Direct tool invocation without LLM

### `generate-cdk`

Bash wrapper script for easier CLI usage

### `pyproject.toml`

UV project configuration with dependencies:

- `mcp>=1.0.0` - Model Context Protocol
- `boto3` - AWS SDK for Bedrock
- `python-dotenv` - Environment variable management
- `pydantic` - Data validation

## Usage

### Prerequisites

```bash
# Ensure you have AWS credentials configured
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
export AWS_REGION=us-west-2

# Install UV if not already installed
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Installation

```bash
cd /path/to/migration-demo/src/cdk-mcp-cli
uv sync
```

### Interactive Mode

```bash
# Start interactive session
uv run cdk_cli.py --interactive

# Example interactions:
> generate a VPC with 2 subnets in 2 AZs
> create a Lambda function with API Gateway
> add DynamoDB table with GSI
```

### Command Mode

```bash
# Single command execution
uv run cdk_cli.py generate a VPC with 2 subnets in 2 AZs

# Using wrapper script
./generate-cdk create an S3 bucket with CloudFront distribution
```

### Direct MCP Testing

```bash
# Test MCP server connectivity
uv run test_cdk_mcp.py

# Available commands in test mode:
# - 'guidance' - Get general CDK guidance
# - 'search <query>' - Search GenAI constructs
# - 'quit' - Exit
```

## Error Handling

- **Connection Errors**: Automatic retry and cleanup
- **Tool Call Failures**: Graceful error messages
- **Bedrock Limits**: Rate limiting and timeout handling
- **MCP Server Issues**: Fallback mechanisms

## Extending the CLI

### Adding New MCP Servers

1. Update `connect_to_cdk_server()` method
2. Add server configuration to tool discovery
3. Update tool orchestration logic

### Custom Tool Integration

1. Implement new tool handlers
2. Add to available tools list
3. Update LLM prompt context

## Troubleshooting

### Common Issues

#### MCP Server Connection Failed

```bash
# Check uvx installation
uvx --version

# Verify MCP server availability
uvx awslabs.cdk-mcp-server@latest --help
```

#### Bedrock Access Denied

```bash
# Verify AWS credentials
aws sts get-caller-identity

# Check Bedrock model access
aws bedrock list-foundation-models --region us-west-2
```

#### Tool Call Timeouts

- Increase timeout values in `generate_cdk_code()`
- Check network connectivity
- Verify MCP server responsiveness

### Debug Mode

```bash
# Enable debug logging
export FASTMCP_LOG_LEVEL=DEBUG
uv run cdk_cli.py --interactive
```

## Architecture Benefits

1. **Separation of Concerns**: LLM handles natural language, MCP server handles CDK expertise
2. **Reusability**: CLI can be used standalone or integrated into workflows
3. **Extensibility**: Easy to add new MCP servers and tools
4. **Testability**: Each component can be tested independently
5. **Scalability**: Can handle multiple concurrent requests through MCP protocol
