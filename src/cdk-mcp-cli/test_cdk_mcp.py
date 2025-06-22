"""
Simple test to connect to CDK MCP server using uvx command
"""
import asyncio
import sys
import json
from typing import Optional, Dict
from contextlib import AsyncExitStack
import logging
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client, get_default_environment

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CDKMCPTest:
    def __init__(self):
        self.session: Optional[ClientSession] = None
        self.exit_stack = AsyncExitStack()

    async def connect_to_cdk_server(self):
        """Connect to CDK MCP server using uvx command"""
        try:
            # Configuration matching your MCP server setup
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
            
            logger.info("Connecting to CDK MCP server...")
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            self.session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            await self.session.initialize()
            
            # List available tools
            response = await self.session.list_tools()
            tools = response.tools
            logger.info(f"Connected to CDK MCP server with {len(tools)} tools:")
            for tool in tools:
                logger.info(f"  - {tool.name}: {tool.description}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error connecting to CDK MCP server: {str(e)}")
            return False

    async def test_cdk_guidance(self, query: str):
        """Test CDK guidance functionality"""
        try:
            logger.info(f"Testing CDK guidance with query: {query}")
            
            # Call the CDK guidance tool
            result = await self.session.call_tool("CDKGeneralGuidance", {})
            
            logger.info("CDK Guidance Result:")
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)
                    
        except Exception as e:
            logger.error(f"Error testing CDK guidance: {str(e)}")

    async def test_search_constructs(self, query: str):
        """Test searching for CDK constructs"""
        try:
            logger.info(f"Searching for constructs: {query}")
            
            # Call the search constructs tool
            result = await self.session.call_tool("SearchGenAICDKConstructs", {
                "query": query
            })
            
            logger.info("Search Results:")
            for content in result.content:
                if hasattr(content, 'text'):
                    print(content.text)
                    
        except Exception as e:
            logger.error(f"Error searching constructs: {str(e)}")

    async def interactive_test(self):
        """Run interactive test session"""
        print("\nCDK MCP Server Test")
        print("Available commands:")
        print("1. 'guidance' - Get general CDK guidance")
        print("2. 'search <query>' - Search for GenAI CDK constructs")
        print("3. 'quit' - Exit")
        
        while True:
            try:
                user_input = input("\nEnter command: ").strip()
                
                if user_input.lower() == 'quit':
                    break
                elif user_input.lower() == 'guidance':
                    await self.test_cdk_guidance("How to create VPC with CDK")
                elif user_input.startswith('search '):
                    query = user_input[7:]  # Remove 'search ' prefix
                    await self.test_search_constructs(query)
                else:
                    print("Unknown command. Try 'guidance', 'search <query>', or 'quit'")
                    
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"Error in interactive test: {str(e)}")

    async def cleanup(self):
        """Clean up resources"""
        try:
            await self.exit_stack.aclose()
            logger.info("Cleanup completed")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")

async def main():
    test_client = CDKMCPTest()
    
    try:
        # Connect to CDK MCP server
        if await test_client.connect_to_cdk_server():
            # Run interactive test
            await test_client.interactive_test()
        else:
            logger.error("Failed to connect to CDK MCP server")
            
    except Exception as e:
        logger.error(f"Error in main: {str(e)}")
    finally:
        await test_client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
