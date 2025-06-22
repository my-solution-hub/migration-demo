#!/usr/bin/env python3
"""
Debug script to see the actual VPC response from Alibaba Cloud
"""
import asyncio
import json
import os
from aliyun_mcp_client import AliyunMCPClient

async def main():
    access_key_id = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_ID', '')
    access_key_secret = os.getenv('ALIBABA_CLOUD_ACCESS_KEY_SECRET', '')
    
    client = AliyunMCPClient(access_key_id, access_key_secret)
    
    try:
        if await client.connect_to_server():
            # Make the raw API call
            result = await client.session.call_tool("VPC_DescribeVpcs", {
                "VpcId": "vpc-t4ng98cerrsiy4ntplbfp",
                "RegionId": "ap-southeast-1"
            })
            
            # Print the raw response
            for content in result.content:
                if hasattr(content, 'text'):
                    print("=== RAW RESPONSE ===")
                    print(content.text)
                    print("=== END RAW RESPONSE ===")
                    
                    # Try to parse as JSON and pretty print
                    try:
                        parsed = json.loads(content.text)
                        print("\n=== PARSED JSON ===")
                        print(json.dumps(parsed, indent=2))
                        print("=== END PARSED JSON ===")
                    except json.JSONDecodeError as e:
                        print(f"JSON parsing failed: {e}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
