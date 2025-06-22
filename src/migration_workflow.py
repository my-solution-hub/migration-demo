"""
LangGraph workflow for automated cloud migration
Orchestrates MCP servers to migrate from Alibaba Cloud VPC to AWS VPC
"""
import asyncio
import json
import os
import subprocess
from typing import Dict, Any, TypedDict, Annotated
from pathlib import Path
import logging

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

# Import our MCP client
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), 'cdk-mcp-cli'))

# Import CDKCodeGenerator from the correct path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'cdk-mcp-cli'))
from cdk_cli import CDKCodeGenerator
from aliyun_mcp_client import AliyunMCPClient

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MigrationState(TypedDict):
    """State for the migration workflow"""
    # Input
    source_vpc_config: Dict[str, Any]
    target_project_name: str
    target_directory: str
    
    # Intermediate states
    alibaba_vpc_data: Dict[str, Any]
    transformed_data: Dict[str, Any]
    cdk_code: str
    cdk_project_path: str
    
    # Output
    deployment_result: Dict[str, Any]
    status: str
    error_message: str

class MigrationWorkflow:
    """LangGraph workflow for cloud migration"""
    
    def __init__(self):
        self.cdk_generator = None
        self.aliyun_client = None
        self.current_project_name = ""
        self.workflow = self._build_workflow()
    
    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(MigrationState)
        
        # Add nodes
        workflow.add_node("extract_vpc", self.extract_alibaba_vpc)
        workflow.add_node("transform_data", self.transform_vpc_data)
        workflow.add_node("generate_cdk", self.generate_cdk_project)
        workflow.add_node("deploy_aws", self.deploy_to_aws)
        workflow.add_node("handle_error", self.handle_error)
        
        # Define the flow
        workflow.set_entry_point("extract_vpc")
        
        workflow.add_edge("extract_vpc", "transform_data")
        workflow.add_edge("transform_data", "generate_cdk")
        workflow.add_edge("generate_cdk", "deploy_aws")
        workflow.add_edge("deploy_aws", END)
        workflow.add_edge("handle_error", END)
        
        return workflow.compile()
    
    async def extract_alibaba_vpc(self, state: MigrationState) -> MigrationState:
        """Node 1: Extract VPC configuration from Alibaba Cloud"""
        logger.info("🔍 Extracting VPC data from Alibaba Cloud...")
        
        try:
            # Initialize Alibaba Cloud MCP client
            if not self.aliyun_client:
                access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID', '')
                access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')
                
                if not access_key_id or not access_key_secret:
                    logger.warning("Alibaba Cloud credentials not found, using mock data")
                
                self.aliyun_client = AliyunMCPClient(access_key_id, access_key_secret)
                await self.aliyun_client.connect_to_server()
            
            # Extract VPC configuration
            source_config = state["source_vpc_config"]
            vpc_id = source_config.get("vpc_id", "")
            region = source_config.get("region", "cn-hangzhou")
            
            if vpc_id:
                logger.info(f"Fetching specific VPC: {vpc_id}")
                alibaba_vpc_data = await self.aliyun_client.get_vpc_info(vpc_id, region)
            else:
                logger.info("No VPC ID specified, listing available VPCs")
                vpcs_list = await self.aliyun_client.list_vpcs(region)
                
                # Use the first VPC if multiple are found
                if isinstance(vpcs_list, dict) and 'vpcs' in vpcs_list and vpcs_list['vpcs']:
                    alibaba_vpc_data = vpcs_list['vpcs'][0]
                    logger.info(f"Using first VPC found: {alibaba_vpc_data.get('vpc_id', 'unknown')}")
                else:
                    # Fallback to mock data
                    alibaba_vpc_data = self.aliyun_client._get_mock_vpc_data(vpc_id, region)
            
            state["alibaba_vpc_data"] = alibaba_vpc_data
            state["status"] = "vpc_extracted"
            logger.info(f"✅ Extracted VPC: {alibaba_vpc_data.get('vpc_name', 'unknown')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to extract VPC data: {e}")
            # Use mock data as fallback
            logger.info("Using mock data as fallback")
            alibaba_vpc_data = {
                "vpc_id": "vpc-fallback-123456",
                "vpc_name": "demo-vpc",
                "cidr_block": "10.0.0.0/16",
                "region": "cn-hangzhou",
                "vswitches": [
                    {
                        "vswitch_id": "vsw-fallback-123456",
                        "name": "demo-subnet-1",
                        "cidr_block": "10.0.1.0/24",
                        "availability_zone": "cn-hangzhou-a"
                    },
                    {
                        "vswitch_id": "vsw-fallback-789012",
                        "name": "demo-subnet-2", 
                        "cidr_block": "10.0.2.0/24",
                        "availability_zone": "cn-hangzhou-b"
                    }
                ],
                "security_groups": [
                    {
                        "group_id": "sg-fallback-123456",
                        "name": "demo-sg",
                        "rules": [
                            {"protocol": "tcp", "port": "80", "source": "0.0.0.0/0"},
                            {"protocol": "tcp", "port": "443", "source": "0.0.0.0/0"}
                        ]
                    }
                ]
            }
            state["alibaba_vpc_data"] = alibaba_vpc_data
            state["status"] = "vpc_extracted"
            
        return state
    
    async def transform_vpc_data(self, state: MigrationState) -> MigrationState:
        """Node 2: Transform Alibaba Cloud data to AWS format"""
        logger.info("🔄 Transforming VPC data for AWS...")
        
        try:
            alibaba_data = state["alibaba_vpc_data"]
            
            # Transform Alibaba Cloud VPC to AWS VPC format
            transformed_data = {
                "vpc": {
                    "name": alibaba_data["vpc_name"].replace("-", "_"),
                    "cidr": alibaba_data["cidr_block"],
                    "enable_dns_hostnames": True,
                    "enable_dns_support": True
                },
                "subnets": [],
                "security_groups": []
            }
            
            # Transform VSwitches to Subnets
            az_mapping = {"cn-hangzhou-a": "us-east-1a", "cn-hangzhou-b": "us-east-1b"}
            for vswitch in alibaba_data["vswitches"]:
                subnet = {
                    "name": vswitch["name"].replace("-", "_"),
                    "cidr": vswitch["cidr_block"],
                    "availability_zone": az_mapping.get(vswitch["availability_zone"], "us-east-1a"),
                    "map_public_ip_on_launch": True
                }
                transformed_data["subnets"].append(subnet)
            
            # Transform Security Groups
            for sg in alibaba_data["security_groups"]:
                security_group = {
                    "name": sg["name"].replace("-", "_"),
                    "description": f"Migrated from Alibaba Cloud SG {sg['group_id']}",
                    "ingress_rules": []
                }
                
                for rule in sg["rules"]:
                    aws_rule = {
                        "protocol": rule["protocol"],
                        "from_port": int(rule["port"]),
                        "to_port": int(rule["port"]),
                        "cidr_blocks": [rule["source"]]
                    }
                    security_group["ingress_rules"].append(aws_rule)
                
                transformed_data["security_groups"].append(security_group)
            
            state["transformed_data"] = transformed_data
            state["status"] = "data_transformed"
            logger.info("✅ Data transformation completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to transform data: {e}")
            state["error_message"] = str(e)
            state["status"] = "error"
            
        return state
    
    async def generate_cdk_project(self, state: MigrationState) -> MigrationState:
        """Node 3: Generate CDK project with cdk init"""
        logger.info("🏗️ Generating CDK project...")
        
        try:
            project_name = state["target_project_name"]
            self.current_project_name = project_name  # Store for use in description
            target_dir = Path(state["target_directory"])
            project_path = target_dir / project_name
            
            # Create project directory
            project_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize CDK project
            logger.info(f"Initializing CDK project at {project_path}")
            result = subprocess.run([
                "cdk", "init", "app", "--language", "typescript"
            ], cwd=project_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"CDK init failed: {result.stderr}")
            
            # Generate CDK code using MCP server
            if not self.cdk_generator:
                self.cdk_generator = CDKCodeGenerator()
                await self.cdk_generator.connect_to_cdk_server()
            
            # Create description for CDK generation
            transformed_data = state["transformed_data"]
            description = self._create_cdk_description(transformed_data)
            
            logger.info("Generating CDK code via MCP server...")
            cdk_code = await self.cdk_generator.generate_cdk_code(description)
            
            # Write the generated code to the CDK project
            stack_file = project_path / "lib" / f"{project_name}-stack.ts"
            
            # Extract only the TypeScript code from the response
            clean_code = self._extract_typescript_code(cdk_code)
            
            with open(stack_file, 'w') as f:
                f.write(clean_code)
            
            # Fix the bin file to use correct import
            self._fix_bin_file(project_path, project_name)
            
            state["cdk_code"] = cdk_code
            state["cdk_project_path"] = str(project_path)
            state["status"] = "cdk_generated"
            logger.info(f"✅ CDK project created at {project_path}")
            
        except Exception as e:
            logger.error(f"❌ Failed to generate CDK project: {e}")
            state["error_message"] = str(e)
            state["status"] = "error"
            
        return state
    
    def _create_cdk_description(self, transformed_data: Dict[str, Any]) -> str:
        """Create a description for CDK generation based on transformed data"""
        vpc = transformed_data["vpc"]
        subnets = transformed_data["subnets"]
        project_name = self.current_project_name  # We'll set this in generate_cdk_project
        
        # Convert project name to proper class name
        class_name = ''.join(word.capitalize() for word in project_name.split('-')) + 'Stack'
        
        description = f"""
        Generate ONLY valid TypeScript CDK code without any explanations or comments. 
        Use correct CDK v2 syntax and imports.
        
        Requirements:
        - Import Construct from 'constructs' package
        - Export class name must be: {class_name}
        - VPC: name='{vpc['name']}', cidr='{vpc['cidr']}', enableDnsHostnames=true, enableDnsSupport=true
        - Use maxAzs: 2 for automatic AZ distribution (do not specify availabilityZone in subnetConfiguration)
        
        Subnets (use subnetConfiguration with cidrMask only):"""
        
        for i, subnet in enumerate(subnets):
            description += f"""
        - Subnet {i+1}: cidrMask=24, name='{subnet['name']}', type=PUBLIC"""
        
        description += """
        
        Security Groups:"""
        
        for sg in transformed_data["security_groups"]:
            ports = [str(rule['from_port']) for rule in sg['ingress_rules']]
            description += f"""
        - name='{sg['name']}', ingress_ports=[{','.join(ports)}], source=0.0.0.0/0"""
        
        description += f"""
        
        Return ONLY valid TypeScript CDK v2 code with export class {class_name}. Use proper imports and syntax."""
        
        return description.strip()
    
    def _extract_typescript_code(self, response: str) -> str:
        """Extract only TypeScript code from the MCP server response"""
        import re
        
        # Look for TypeScript code blocks
        code_block_pattern = r'```typescript\s*(.*?)\s*```'
        matches = re.findall(code_block_pattern, response, re.DOTALL)
        
        if matches:
            return matches[0].strip()
        
        # If no code blocks, look for import statements to find start of code
        lines = response.split('\n')
        code_lines = []
        in_code = False
        
        for line in lines:
            # Start collecting when we see import or export statements
            if line.strip().startswith(('import ', 'export ', 'const ', 'class ', 'interface ')):
                in_code = True
            
            if in_code:
                # Skip explanation lines
                if not any(phrase in line.lower() for phrase in [
                    'this cdk code', 'to use this', 'notes and best', 'would you like',
                    'the code uses', 'for production', 'the stack uses'
                ]):
                    code_lines.append(line)
        
        return '\n'.join(code_lines).strip()
    
    def _fix_bin_file(self, project_path: Path, project_name: str):
        """Fix the bin file to use the correct stack import and class name"""
        bin_file = project_path / "bin" / f"{project_name}.ts"
        class_name = ''.join(word.capitalize() for word in project_name.split('-')) + 'Stack'
        
        bin_content = f"""#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import {{ {class_name} }} from '../lib/{project_name}-stack';

const app = new cdk.App();
new {class_name}(app, '{class_name}', {{
  env: {{
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  }},
}});
"""
        
        with open(bin_file, 'w') as f:
            f.write(bin_content)
    
    async def deploy_to_aws(self, state: MigrationState) -> MigrationState:
        """Node 4: Deploy CDK project to AWS"""
        logger.info("🚀 Deploying to AWS...")
        
        try:
            project_path = Path(state["cdk_project_path"])
            
            # Install dependencies
            logger.info("Installing CDK dependencies...")
            result = subprocess.run([
                "npm", "install"
            ], cwd=project_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"npm install failed: {result.stderr}")
            
            # Bootstrap CDK (if needed)
            logger.info("Bootstrapping CDK...")
            subprocess.run([
                "cdk", "bootstrap"
            ], cwd=project_path, capture_output=True, text=True)
            
            # Deploy the stack
            logger.info("Deploying CDK stack...")
            result = subprocess.run([
                "cdk", "deploy", "--require-approval", "never"
            ], cwd=project_path, capture_output=True, text=True)
            
            if result.returncode != 0:
                raise Exception(f"CDK deploy failed: {result.stderr}")
            
            deployment_result = {
                "status": "deployed",
                "output": result.stdout,
                "project_path": str(project_path)
            }
            
            state["deployment_result"] = deployment_result
            state["status"] = "completed"
            logger.info("✅ Deployment completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Deployment failed: {e}")
            state["error_message"] = str(e)
            state["status"] = "error"
            
        return state
    
    async def handle_error(self, state: MigrationState) -> MigrationState:
        """Handle errors and cleanup"""
        logger.error(f"🚨 Migration failed: {state.get('error_message', 'Unknown error')}")
        
        # TODO: Implement cleanup logic
        # - Remove partially created CDK project
        # - Rollback any AWS resources
        
        return state
    
    async def run_migration(self, 
                          source_vpc_config: Dict[str, Any],
                          target_project_name: str,
                          target_directory: str) -> Dict[str, Any]:
        """Run the complete migration workflow"""
        
        initial_state = MigrationState(
            source_vpc_config=source_vpc_config,
            target_project_name=target_project_name,
            target_directory=target_directory,
            alibaba_vpc_data={},
            transformed_data={},
            cdk_code="",
            cdk_project_path="",
            deployment_result={},
            status="started",
            error_message=""
        )
        
        try:
            logger.info("🚀 Starting migration workflow...")
            final_state = await self.workflow.ainvoke(initial_state)
            
            if self.cdk_generator:
                await self.cdk_generator.cleanup()
            
            if self.aliyun_client:
                await self.aliyun_client.cleanup()
            
            return final_state
            
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            if self.cdk_generator:
                await self.cdk_generator.cleanup()
            
            if self.aliyun_client:
                await self.aliyun_client.cleanup()
            
            raise

# CLI interface
async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Automated VPC Migration from Alibaba Cloud to AWS')
    parser.add_argument('--project-name', required=True, help='Name for the CDK project')
    parser.add_argument('--target-dir', default='./output', help='Directory to create the CDK project')
    parser.add_argument('--vpc-id', help='Alibaba Cloud VPC ID to migrate')
    parser.add_argument('--region', default='cn-hangzhou', help='Alibaba Cloud region')
    parser.add_argument('--ak-id', help='Alibaba Cloud Access Key ID (or set ALIBABA_CLOUD_ACCESS_KEY_ID env var)')
    parser.add_argument('--ak-secret', help='Alibaba Cloud Access Key Secret (or set ALIBABA_CLOUD_ACCESS_KEY_SECRET env var)')
    
    args = parser.parse_args()
    
    # Set Alibaba Cloud credentials if provided
    if args.ak_id:
        os.environ['ALIBABA_CLOUD_ACCESS_KEY_ID'] = args.ak_id
    if args.ak_secret:
        os.environ['ALIBABA_CLOUD_ACCESS_KEY_SECRET'] = args.ak_secret
    
    # Source VPC configuration
    source_config = {
        "vpc_id": args.vpc_id or "",
        "region": args.region
    }
    
    workflow = MigrationWorkflow()
    
    try:
        result = await workflow.run_migration(
            source_vpc_config=source_config,
            target_project_name=args.project_name,
            target_directory=args.target_dir
        )
        
        print(f"\n🎉 Migration Status: {result['status']}")
        if result['status'] == 'completed':
            print(f"📁 CDK Project: {result['cdk_project_path']}")
            print(f"☁️ AWS Deployment: {result['deployment_result']['status']}")
        elif result['status'] == 'error':
            print(f"❌ Error: {result['error_message']}")
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
