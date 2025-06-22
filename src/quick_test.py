#!/usr/bin/env python3
"""
Quick test to see what the Alibaba Cloud MCP server returns
"""
import asyncio
import os
from aliyun_mcp_client import AliyunMCPClient

async def main():
    access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID', '')
    access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')
    
    print(f"Using credentials: {access_key_id[:10]}...")
    
    client = AliyunMCPClient(access_key_id, access_key_secret)
    
    try:
        print("Connecting to Alibaba Cloud MCP server...")
        if await client.connect_to_server():
            print("Connected successfully!")
            
            print("Fetching VPC info...")
            vpc_info = await client.get_vpc_info("vpc-t4ng98cerrsiy4ntplbfp", "ap-southeast-1")
            print(f"VPC Info: {vpc_info}")
            
        else:
            print("Failed to connect")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
