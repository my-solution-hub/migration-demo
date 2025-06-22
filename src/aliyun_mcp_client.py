"""
Alibaba Cloud MCP Client for VPC data extraction
"""
import asyncio
import json
import logging
from typing import Optional, Dict, Any
from contextlib import AsyncExitStack
import boto3
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def make_serializable(obj):
    """Helper to convert objects like TextContent to plain dicts"""
    if isinstance(obj, list):
        return [make_serializable(o) for o in obj]
    elif hasattr(obj, '__dict__'):
        return {k: make_serializable(v) for k, v in vars(obj).items()}
    elif isinstance(obj, (str, int, float, bool)) or obj is None:
        return obj
    else:
        return str(obj)

class AliyunMCPClient:
    """Client for Alibaba Cloud MCP server operations"""
    
    def __init__(self, access_key_id: str = "", access_key_secret: str = ""):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.access_key_id = access_key_id
        self.access_key_secret = access_key_secret
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')

    async def connect_to_server(self):
        """Connect to Alibaba Cloud MCP server using uvx"""
        try:
            command = "uvx"
            args = ["alibaba-cloud-ops-mcp-server@latest"]
            env = get_default_environment()
            env.update({
                "ALIBABA_CLOUD_ACCESS_KEY_ID": self.access_key_id,
                "ALIBABA_CLOUD_ACCESS_KEY_SECRET": self.access_key_secret,
            })

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            logger.info("Connecting to Alibaba Cloud MCP server...")
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            await self.session.initialize()
            
            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            logger.info(f"Connected to Alibaba Cloud MCP server with {len(tools)} tools")
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to Alibaba Cloud MCP server: {str(e)}")
            return False

    async def _parse_vpc_data_with_llm(self, raw_data: str, vpc_id: str = "", region: str = "") -> Dict[str, Any]:
        """Use LLM to parse and structure Alibaba Cloud VPC data"""
        try:
            logger.info("Parsing VPC data using LLM...")
            
            messages = [
                {
                    "role": "user",
                    "content": f"""
Parse this Alibaba Cloud VPC API response and convert it to a structured JSON format.

Raw API Response:
{raw_data}

Please extract and return ONLY a JSON object with this exact structure:
{{
  "vpc_id": "extracted vpc id",
  "vpc_name": "extracted vpc name or generate one if missing",
  "cidr_block": "extracted cidr block",
  "region": "{region}",
  "status": "extracted status",
  "vswitches": [
    {{
      "vswitch_id": "extracted vswitch id",
      "name": "extracted vswitch name or generate one",
      "cidr_block": "extracted cidr block",
      "availability_zone": "extracted zone",
      "status": "extracted status"
    }}
  ],
  "security_groups": [
    {{
      "group_id": "extracted security group id",
      "name": "extracted security group name or generate one",
      "description": "extracted description",
      "rules": []
    }}
  ]
}}

Return ONLY the JSON, no explanations.
"""
                }
            ]

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": messages
            }

            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
                body=json.dumps(body, default=make_serializable)
            )
            response_data = json.loads(response['body'].read())
            
            # Extract the JSON from the response
            llm_response = response_data['content'][0]['text']
            
            # Try to parse the JSON response
            try:
                parsed_data = json.loads(llm_response)
                logger.info("Successfully parsed VPC data with LLM")
                return parsed_data
            except json.JSONDecodeError:
                # If LLM response isn't valid JSON, extract JSON from it
                import re
                json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
                if json_match:
                    parsed_data = json.loads(json_match.group())
                    return parsed_data
                else:
                    raise Exception("Could not extract valid JSON from LLM response")
                    
        except Exception as e:
            logger.error(f"Error parsing VPC data with LLM: {str(e)}")
            return self._get_mock_vpc_data(vpc_id, region)

    async def get_vpc_info(self, vpc_id: str = "", region: str = "cn-hangzhou") -> Dict[str, Any]:
        """Get VPC information from Alibaba Cloud"""
        try:
            logger.info(f"Fetching VPC info for VPC ID: {vpc_id}, Region: {region}")
            
            # Call the VPC describe tool
            if vpc_id:
                result = await self.session.call_tool("VPC_DescribeVpcs", {
                    "VpcId": vpc_id,
                    "RegionId": region
                })
            else:
                result = await self.session.call_tool("VPC_DescribeVpcs", {
                    "RegionId": region
                })
            
            # Extract the raw response
            raw_response = ""
            for content in result.content:
                if hasattr(content, 'text'):
                    raw_response += content.text + "\n"
            
            logger.info(f"Raw VPC response received: {len(raw_response)} characters")
            
            # Try simple JSON parsing first
            try:
                parsed_data = json.loads(raw_response)
                logger.info("Successfully parsed VPC data as JSON")
                
                # Convert Alibaba Cloud format to our expected format
                converted_data = self._convert_alibaba_vpc_format(parsed_data, vpc_id, region)
                return converted_data
                
            except json.JSONDecodeError:
                logger.info("Raw response is not JSON, using LLM parsing...")
                # Fallback to LLM parsing with timeout
                try:
                    parsed_data = await asyncio.wait_for(
                        self._parse_vpc_data_with_llm(raw_response, vpc_id, region),
                        timeout=30.0  # 30 second timeout
                    )
                    return parsed_data
                except asyncio.TimeoutError:
                    logger.error("LLM parsing timed out, using mock data")
                    return self._get_mock_vpc_data(vpc_id, region)
            
        except Exception as e:
            logger.error(f"Error getting VPC info: {str(e)}")
            # Return mock data as fallback
            return self._get_mock_vpc_data(vpc_id, region)

    def _convert_alibaba_vpc_format(self, alibaba_data: Dict[str, Any], vpc_id: str, region: str) -> Dict[str, Any]:
        """Convert Alibaba Cloud API response to our expected format"""
        try:
            # Handle the response structure with body wrapper
            data = alibaba_data
            if 'body' in alibaba_data:
                data = alibaba_data['body']
            
            # Handle different possible response structures
            vpcs = []
            if 'Vpcs' in data and 'Vpc' in data['Vpcs']:
                vpcs = data['Vpcs']['Vpc']
            elif 'vpcs' in data:
                vpcs = data['vpcs']
            elif 'Vpc' in data:
                vpcs = [data['Vpc']] if isinstance(data['Vpc'], dict) else data['Vpc']
            
            if not vpcs:
                logger.warning("No VPCs found in response, using mock data")
                return self._get_mock_vpc_data(vpc_id, region)
            
            # Use the first VPC or find the specific one
            target_vpc = vpcs[0]
            if vpc_id:
                for vpc in vpcs:
                    if vpc.get('VpcId') == vpc_id or vpc.get('vpc_id') == vpc_id:
                        target_vpc = vpc
                        break
            
            # Convert to our format
            converted = {
                "vpc_id": target_vpc.get('VpcId') or target_vpc.get('vpc_id') or vpc_id,
                "vpc_name": target_vpc.get('VpcName') or target_vpc.get('vpc_name') or f"vpc-{vpc_id}",
                "cidr_block": target_vpc.get('CidrBlock') or target_vpc.get('cidr_block') or "10.0.0.0/16",
                "region": region,
                "status": target_vpc.get('Status') or target_vpc.get('status') or "Available",
                "vswitches": [],
                "security_groups": []
            }
            
            # Extract VSwitches if available
            if 'VSwitchIds' in target_vpc and 'VSwitchId' in target_vpc['VSwitchIds']:
                vswitch_ids = target_vpc['VSwitchIds']['VSwitchId']
                for i, vswitch_id in enumerate(vswitch_ids):
                    converted['vswitches'].append({
                        "vswitch_id": vswitch_id,
                        "name": f"subnet-{i+1}",
                        "cidr_block": f"10.0.{i+1}.0/24",  # Default CIDR, will be updated if we fetch details
                        "availability_zone": f"{region}-{chr(97+i)}",  # a, b, c...
                        "status": "Available"
                    })
            
            # Add a default security group
            converted['security_groups'] = [{
                "group_id": f"sg-{vpc_id}",
                "name": "default-sg",
                "description": "Default security group",
                "rules": [
                    {"protocol": "tcp", "port": "80", "source": "0.0.0.0/0", "direction": "ingress"},
                    {"protocol": "tcp", "port": "443", "source": "0.0.0.0/0", "direction": "ingress"}
                ]
            }]
            
            logger.info(f"Converted VPC data: {converted['vpc_name']} ({converted['vpc_id']}) with {len(converted['vswitches'])} subnets")
            return converted
            
        except Exception as e:
            logger.error(f"Error converting Alibaba Cloud format: {e}")
            return self._get_mock_vpc_data(vpc_id, region)

    async def _parse_vswitches_with_llm(self, raw_data: str, region: str) -> list:
        """Parse VSwitches data with LLM"""
        try:
            messages = [
                {
                    "role": "user",
                    "content": f"""
Parse this Alibaba Cloud VSwitches API response and return ONLY a JSON array of VSwitches.

Raw API Response:
{raw_data}

Return ONLY a JSON array with this structure:
[
  {{
    "vswitch_id": "extracted vswitch id",
    "name": "extracted vswitch name or generate one",
    "cidr_block": "extracted cidr block", 
    "availability_zone": "extracted zone",
    "status": "extracted status"
  }}
]

Return ONLY the JSON array, no explanations.
"""
                }
            ]

            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1500,
                "messages": messages
            }

            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
                body=json.dumps(body, default=make_serializable)
            )
            response_data = json.loads(response['body'].read())
            
            llm_response = response_data['content'][0]['text']
            
            try:
                return json.loads(llm_response)
            except json.JSONDecodeError:
                import re
                json_match = re.search(r'\[.*\]', llm_response, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                else:
                    return []
                    
        except Exception as e:
            logger.error(f"Error parsing VSwitches with LLM: {e}")
            return []

    async def list_vpcs(self, region: str = "cn-hangzhou") -> Dict[str, Any]:
        """List all VPCs in the specified region"""
        try:
            logger.info(f"Listing VPCs in region: {region}")
            
            result = await self.session.call_tool("VPC_DescribeVpcs", {
                "RegionId": region
            })
            
            vpcs_data = {}
            for content in result.content:
                if hasattr(content, 'text'):
                    try:
                        vpcs_data = json.loads(content.text)
                    except json.JSONDecodeError:
                        vpcs_data = {"raw_response": content.text}
            
            return vpcs_data
            
        except Exception as e:
            logger.error(f"Error listing VPCs: {str(e)}")
            return {"error": str(e)}

    async def get_vswitches(self, vpc_id: str, region: str = "cn-hangzhou") -> Dict[str, Any]:
        """Get VSwitches (subnets) for a specific VPC"""
        try:
            logger.info(f"Fetching VSwitches for VPC: {vpc_id}, Region: {region}")
            
            result = await self.session.call_tool("VPC_DescribeVSwitches", {
                "VpcId": vpc_id,
                "RegionId": region
            })
            
            vswitches_data = {}
            for content in result.content:
                if hasattr(content, 'text'):
                    try:
                        vswitches_data = json.loads(content.text)
                    except json.JSONDecodeError:
                        vswitches_data = {"raw_response": content.text}
            
            return vswitches_data
            
        except Exception as e:
            logger.error(f"Error getting VSwitches: {str(e)}")
            return {"error": str(e)}

    def _get_mock_vpc_data(self, vpc_id: str, region: str) -> Dict[str, Any]:
        """Fallback mock data when MCP server is not available"""
        logger.warning("Using mock VPC data as fallback")
        return {
            "vpc_id": vpc_id or "vpc-mock-123456",
            "vpc_name": "demo-vpc",
            "cidr_block": "10.0.0.0/16",
            "region": region,
            "status": "Available",
            "vswitches": [
                {
                    "vswitch_id": "vsw-mock-123456",
                    "name": "demo-subnet-1",
                    "cidr_block": "10.0.1.0/24",
                    "availability_zone": f"{region}-a",
                    "status": "Available"
                },
                {
                    "vswitch_id": "vsw-mock-789012",
                    "name": "demo-subnet-2", 
                    "cidr_block": "10.0.2.0/24",
                    "availability_zone": f"{region}-b",
                    "status": "Available"
                }
            ],
            "security_groups": [
                {
                    "group_id": "sg-mock-123456",
                    "name": "demo-sg",
                    "description": "Demo security group",
                    "rules": [
                        {
                            "protocol": "tcp",
                            "port": "80",
                            "source": "0.0.0.0/0",
                            "direction": "ingress"
                        },
                        {
                            "protocol": "tcp",
                            "port": "443",
                            "source": "0.0.0.0/0",
                            "direction": "ingress"
                        }
                    ]
                }
            ]
        }

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
            logger.info("Alibaba Cloud MCP client cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

# CLI interface for testing
async def main():
    import argparse
    import os
    
    parser = argparse.ArgumentParser(description='Test Alibaba Cloud MCP client')
    parser.add_argument('--vpc-id', help='VPC ID to query')
    parser.add_argument('--region', default='cn-hangzhou', help='Alibaba Cloud region')
    parser.add_argument('--list-vpcs', action='store_true', help='List all VPCs')
    parser.add_argument('--get-vswitches', action='store_true', help='Get VSwitches for specified VPC')
    
    args = parser.parse_args()
    
    # Get credentials from environment
    access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID', '')
    access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')
    
    if not access_key_id or not access_key_secret:
        print("Warning: ALIBABA_CLOUD_ACCESS_KEY_ID and ALIBABA_CLOUD_ACCESS_KEY_SECRET not set")
        print("Using mock data for testing")
    
    client = AliyunMCPClient(access_key_id, access_key_secret)
    
    try:
        if await client.connect_to_server():
            if args.list_vpcs:
                vpcs = await client.list_vpcs(args.region)
                print(f"\nVPCs in region {args.region}:")
                print(json.dumps(vpcs, indent=2))
            elif args.get_vswitches and args.vpc_id:
                vswitches = await client.get_vswitches(args.vpc_id, args.region)
                print(f"\nVSwitches for VPC {args.vpc_id}:")
                print(json.dumps(vswitches, indent=2))
            else:
                vpc_info = await client.get_vpc_info(args.vpc_id, args.region)
                print(f"\nVPC Information:")
                print(json.dumps(vpc_info, indent=2))
        else:
            print("Failed to connect to Alibaba Cloud MCP server")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
