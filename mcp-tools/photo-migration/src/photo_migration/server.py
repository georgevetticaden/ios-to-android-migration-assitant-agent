#!/usr/bin/env python3.11
"""
Photo Migration MCP Server
Connects to privacy.apple.com to get real iCloud photo counts
"""

import asyncio
import logging
import os
from typing import Any, Dict
from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .icloud_client import ICloudClientWithSession

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

server = Server("photo-migration")
icloud_client = None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="check_icloud_status",
            description="Check iCloud photo library status via privacy.apple.com (with session persistence to avoid repeated 2FA)",
            inputSchema={
                "type": "object",
                "properties": {
                    "apple_id": {
                        "type": "string",
                        "description": "Apple ID email"
                    },
                    "password": {
                        "type": "string",
                        "description": "Apple ID password"
                    }
                },
                "required": []
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls"""
    global icloud_client
    
    if name == "check_icloud_status":
        try:
            if icloud_client is None:
                # Use session persistence to avoid repeated 2FA
                session_dir = os.path.expanduser("~/.icloud_session")
                icloud_client = ICloudClientWithSession(session_dir=session_dir)
                await icloud_client.initialize()
            
            # Use credentials from arguments or fall back to environment variables
            apple_id = arguments.get("apple_id") or os.getenv("APPLE_ID")
            password = arguments.get("password") or os.getenv("APPLE_PASSWORD")
            
            result = await icloud_client.get_photo_status(
                apple_id=apple_id,
                password=password
            )
            
            response = f"""iCloud Photo Library Status:
📸 Photos: {result['photos']:,}
🎬 Videos: {result['videos']:,}
💾 Storage: {result['storage_gb']:.1f} GB
📦 Total Items: {result['total_items']:,}

Session: {'Reused saved session (no 2FA)' if result.get('session_used') else 'New session created'}

Transfer History:
"""
            if result.get('existing_transfers'):
                for transfer in result['existing_transfers']:
                    status_emoji = {
                        'complete': '✅',
                        'cancelled': '❌', 
                        'failed': '⚠️',
                        'in_progress': '🔄'
                    }.get(transfer['status'], '❓')
                    response += f"{status_emoji} {transfer['status'].title()} - {transfer.get('date', 'Unknown')}\n"
            else:
                response += "No previous transfer requests found\n"
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Error: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

async def main():
    """Main entry point"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        logger.info("Photo Migration MCP Server starting...")
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="photo-migration",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())