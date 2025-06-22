"""
MCP Server Configuration
"""

# MCP Server configurations for different environments
SERVER_CONFIGS = {
    'development': {
        'alibaba-cloud': {
            'server_script_path': '../provider-mcp/alibaba-cloud/server.py',
            'server_script_args': [],
            'server_script_envs': {
                'ALIBABA_ACCESS_KEY_ID': '',  # Set via environment
                'ALIBABA_ACCESS_KEY_SECRET': '',  # Set via environment
                'ALIBABA_REGION': 'cn-hangzhou'
            }
        },
        'data-processor': {
            'server_script_path': '../provider-mcp/common/data_processor.py',
            'server_script_args': [],
            'server_script_envs': {}
        },
        'aws-cdk': {
            'server_url': 'http://localhost:8000/mcp',  # Local CDK MCP server
            'http_type': 'streamable_http',
            'token': ''
        },
        'aws-deploy': {
            'server_script_path': '../provider-mcp/aws/deploy_server.py',
            'server_script_args': [],
            'server_script_envs': {
                'AWS_REGION': 'us-east-1'
            }
        }
    },
    'production': {
        'alibaba-cloud': {
            'server_url': 'https://your-alibaba-mcp-server.com/mcp',
            'http_type': 'streamable_http',
            'token': ''  # Set via environment
        },
        'data-processor': {
            'server_url': 'https://your-processor-server.com/mcp',
            'http_type': 'streamable_http',
            'token': ''
        },
        'aws-cdk': {
            'server_url': 'https://your-cdk-server.com/mcp',
            'http_type': 'streamable_http',
            'token': ''
        },
        'aws-deploy': {
            'server_url': 'https://your-deploy-server.com/mcp',
            'http_type': 'streamable_http',
            'token': ''
        }
    }
}

# Migration workflow configuration
MIGRATION_CONFIG = {
    'vpc_migration': {
        'source_provider': 'alibaba-cloud',
        'target_provider': 'aws',
        'steps': [
            'extract_vpc_config',
            'transform_data',
            'generate_cdk_code',
            'deploy_infrastructure'
        ],
        'rollback_enabled': True,
        'validation_enabled': True
    }
}
