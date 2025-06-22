#!/usr/bin/env python3
"""
CLI to generate CDK code using MCP server with plaintext input via Bedrock LLM
"""
import asyncio
import argparse
import sys
import json
import logging
from typing import Optional, Dict
from contextlib import AsyncExitStack
import boto3
from dotenv import load_dotenv
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.WARNING)
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

class CDKCodeGenerator:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()
        self.bedrock = boto3.client('bedrock-runtime', region_name='us-west-2')

    async def connect_to_cdk_server(self):
        """Connect to CDK MCP server using uvx command"""
        try:
            command = "uvx"
            args = ["awslabs.cdk-mcp-server@latest"]
            env = get_default_environment()
            env.update({
                "FASTMCP_LOG_LEVEL": "ERROR"
            })

            server_params = StdioServerParameters(
                command=command,
                args=args,
                env=env
            )
            
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            await self.session.initialize()
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to CDK MCP server: {str(e)}")
            return False

    async def generate_cdk_code(self, description: str) -> str:
        """Generate CDK code based on plaintext description using Bedrock LLM"""
        try:
            # Get available tools from MCP server
            response = await self.session.list_tools()
            available_tools = [{
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.inputSchema.dict() if hasattr(tool.inputSchema, "dict") else tool.inputSchema
            } for tool in response.tools]

            # Create messages for Bedrock
            messages = [
                {
                    "role": "user",
                    "content": f"Generate AWS CDK code for: {description}. IMPORTANT: The output should only have CDK code, without any additional comments.I will directly replace all output into a typescript file for CDK project and run it, therefore do not add env variables that requires code update."
                }
            ]

            # Initial Bedrock API call
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": messages,
                "tools": available_tools
            }

            response = self.bedrock.invoke_model(
                modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
                body=json.dumps(body, default=make_serializable)
            )
            response = json.loads(response['body'].read())

            final_text = []
            assistant_message_content = []

            while True:
                for content in response['content']:
                    if content['type'] == 'text':
                        final_text.append(content['text'])
                        assistant_message_content.append(content)
                    elif content['type'] == 'tool_use':
                        tool_name = content['name']
                        tool_args = content['input']
                        
                        # Execute tool call via MCP server
                        result = await self.session.call_tool(tool_name, tool_args)
                        
                        assistant_message_content.append(content)
                        messages.append({
                            "role": "assistant",
                            "content": assistant_message_content
                        })
                        messages.append({
                            "role": "user",
                            "content": [
                                {
                                    "type": "tool_result",
                                    "tool_use_id": content['id'],
                                    "content": [
                                        {
                                            "type": item.type,
                                            "text": item.text
                                        } for item in result.content if item.type == "text"
                                    ]
                                }
                            ]
                        })
                        
                        # Get next response from Bedrock
                        body = {
                            "anthropic_version": "bedrock-2023-05-31",
                            "max_tokens": 2000,
                            "messages": messages,
                            "tools": available_tools
                        }
                        
                        response = self.bedrock.invoke_model(
                            modelId='anthropic.claude-3-5-haiku-20241022-v1:0',
                            body=json.dumps(body, default=make_serializable)
                        )
                        response = json.loads(response['body'].read())
                        assistant_message_content = []
                        break
                else:
                    break

            return "\n".join(final_text)
            
        except Exception as e:
            logger.error(f"Error generating CDK code: {str(e)}")
            return f"Error: {str(e)}"

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

async def main():
    parser = argparse.ArgumentParser(description='Generate CDK code from plaintext description')
    parser.add_argument('description', nargs='*', help='Description of what to generate (e.g., "generate a VPC with 2 subnets in 2 AZs")')
    parser.add_argument('--interactive', '-i', action='store_true', help='Run in interactive mode')
    
    args = parser.parse_args()
    
    generator = CDKCodeGenerator()
    
    try:
        # Connect to CDK MCP server
        if not await generator.connect_to_cdk_server():
            print("Error: Failed to connect to CDK MCP server", file=sys.stderr)
            sys.exit(1)
        
        if args.interactive:
            # Interactive mode
            print("CDK Code Generator (Interactive Mode)")
            print("Enter your description or 'quit' to exit")
            
            while True:
                try:
                    description = input("\nDescribe what you want to generate: ").strip()
                    
                    if description.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    if not description:
                        continue
                    
                    print("\nGenerating CDK code...")
                    code = await generator.generate_cdk_code(description)
                    print("\n" + "="*50)
                    print("Generated CDK Code:")
                    print("="*50)
                    print(code)
                    print("="*50)
                    
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {str(e)}", file=sys.stderr)
        
        else:
            # Command line mode
            if not args.description:
                print("Error: Please provide a description or use --interactive mode", file=sys.stderr)
                parser.print_help()
                sys.exit(1)
            
            description = ' '.join(args.description)
            code = await generator.generate_cdk_code(description)
            print(code)
    
    except Exception as e:
        print(f"Error: {str(e)}", file=sys.stderr)
        sys.exit(1)
    
    finally:
        await generator.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
