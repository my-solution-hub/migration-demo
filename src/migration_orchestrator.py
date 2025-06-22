"""
Migration Orchestrator - Coordinates the end-to-end migration workflow
"""
import asyncio
import logging
from typing import Dict, Any, List
from mcp_client import MCPClient

logger = logging.getLogger(__name__)

class MigrationOrchestrator:
    """Orchestrates the complete migration workflow using multiple MCP servers"""
    
    def __init__(self):
        self.servers: Dict[str, MCPClient] = {}
        self.migration_state = {}
        
    async def initialize_servers(self, server_configs: Dict[str, Dict]):
        """Initialize all required MCP servers"""
        for server_name, config in server_configs.items():
            client = MCPClient(server_name)
            await client.connect_to_server(**config)
            self.servers[server_name] = client
            logger.info(f"Initialized MCP server: {server_name}")
    
    async def execute_migration(self, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the complete migration workflow"""
        try:
            # Step 1: Extract source cloud configuration
            source_data = await self._extract_source_config(source_config)
            
            # Step 2: Transform data for target cloud
            transformed_data = await self._transform_data(source_data)
            
            # Step 3: Generate target cloud infrastructure code
            infrastructure_code = await self._generate_infrastructure_code(transformed_data)
            
            # Step 4: Deploy to target cloud
            deployment_result = await self._deploy_infrastructure(infrastructure_code)
            
            return {
                'status': 'success',
                'source_data': source_data,
                'transformed_data': transformed_data,
                'infrastructure_code': infrastructure_code,
                'deployment_result': deployment_result
            }
            
        except Exception as e:
            logger.error(f"Migration failed: {e}")
            await self._rollback_migration()
            raise
    
    async def _extract_source_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract configuration from source cloud provider"""
        alibaba_client = self.servers.get('alibaba-cloud')
        if not alibaba_client:
            raise ValueError("Alibaba Cloud MCP server not initialized")
        
        # Call Alibaba Cloud MCP server tools
        vpc_result = await alibaba_client.call_tool('get_vpc_config', config)
        return vpc_result.content[0].text if vpc_result.content else {}
    
    async def _transform_data(self, source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform source data to target cloud format"""
        processor_client = self.servers.get('data-processor')
        if not processor_client:
            raise ValueError("Data processor MCP server not initialized")
        
        transform_result = await processor_client.call_tool('transform_vpc_config', source_data)
        return transform_result.content[0].text if transform_result.content else {}
    
    async def _generate_infrastructure_code(self, data: Dict[str, Any]) -> str:
        """Generate AWS CDK code"""
        cdk_client = self.servers.get('aws-cdk')
        if not cdk_client:
            raise ValueError("AWS CDK MCP server not initialized")
        
        code_result = await cdk_client.call_tool('generate_vpc_stack', data)
        return code_result.content[0].text if code_result.content else ""
    
    async def _deploy_infrastructure(self, code: str) -> Dict[str, Any]:
        """Deploy the generated infrastructure"""
        deploy_client = self.servers.get('aws-deploy')
        if not deploy_client:
            raise ValueError("AWS Deploy MCP server not initialized")
        
        deploy_result = await deploy_client.call_tool('deploy_stack', {'code': code})
        return deploy_result.content[0].text if deploy_result.content else {}
    
    async def _rollback_migration(self):
        """Rollback migration in case of failure"""
        logger.info("Initiating migration rollback...")
        # Implement rollback logic based on migration state
        pass
    
    async def cleanup(self):
        """Clean up all MCP server connections"""
        for server_name, client in self.servers.items():
            await client.disconnect_to_server()
            logger.info(f"Disconnected from {server_name}")
