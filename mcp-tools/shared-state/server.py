#!/usr/bin/env python3
"""
Shared State MCP Server
Wraps the existing migration_db.py to expose database operations as MCP tools
Returns raw JSON for Claude to visualize
"""

import sys
import json
import asyncio
from pathlib import Path

# Add parent directories to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from shared.database.migration_db import MigrationDatabase
from datetime import datetime

# Initialize server and database
server = Server("shared-state")
db = MigrationDatabase()

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available database tools"""
    return [
        Tool(
            name="initialize_migration",
            description="Create a new migration record",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_email": {"type": "string"},
                    "user_name": {"type": "string"},
                    "source_device": {"type": "string"},
                    "target_device": {"type": "string"},
                    "family_id": {"type": "string", "nullable": True}
                },
                "required": ["user_email", "user_name", "source_device", "target_device"]
            }
        ),
        Tool(
            name="update_photo_progress",
            description="Update photo migration progress",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {"type": "string"},
                    "status": {"type": "string"},
                    "photos_count": {"type": "integer", "nullable": True},
                    "videos_count": {"type": "integer", "nullable": True},
                    "total_size_gb": {"type": "number", "nullable": True},
                    "apple_status": {"type": "string", "nullable": True},
                    "google_status": {"type": "string", "nullable": True}
                },
                "required": ["transfer_id", "status"]
            }
        ),
        Tool(
            name="update_app_status",
            description="Update app migration status",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name": {"type": "string"},
                    "package_name": {"type": "string"},
                    "status": {"type": "string"},
                    "configuration": {"type": "object", "nullable": True}
                },
                "required": ["app_name", "package_name", "status"]
            }
        ),
        Tool(
            name="get_migration_status",
            description="Get current migration status and all details",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "nullable": True}
                }
            }
        ),
        Tool(
            name="log_event",
            description="Log a migration event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "component": {"type": "string"},
                    "description": {"type": "string"},
                    "metadata": {"type": "object", "nullable": True}
                },
                "required": ["event_type", "component", "description"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute database operations and return raw JSON"""
    
    try:
        if name == "initialize_migration":
            migration_id = await db.create_migration(
                user_email=arguments["user_email"],
                user_name=arguments["user_name"],
                source_device=arguments["source_device"],
                target_device=arguments["target_device"],
                family_id=arguments.get("family_id")
            )
            result = {"migration_id": migration_id, "status": "created"}
            
        elif name == "update_photo_progress":
            await db.update_photo_transfer(
                transfer_id=arguments["transfer_id"],
                status=arguments["status"],
                photos_count=arguments.get("photos_count"),
                videos_count=arguments.get("videos_count"),
                total_size_gb=arguments.get("total_size_gb"),
                apple_status=arguments.get("apple_status"),
                google_status=arguments.get("google_status")
            )
            result = {"transfer_id": arguments["transfer_id"], "status": "updated"}
            
        elif name == "update_app_status":
            await db.update_app_migration(
                app_name=arguments["app_name"],
                package_name=arguments["package_name"],
                status=arguments["status"],
                configuration=arguments.get("configuration")
            )
            result = {"app": arguments["app_name"], "status": "updated"}
            
        elif name == "get_migration_status":
            migration_id = arguments.get("migration_id")
            if migration_id:
                result = await db.get_migration_status(migration_id)
            else:
                result = await db.get_active_migration()
            
            # Convert datetime objects to strings for JSON serialization
            if result:
                for key, value in result.items():
                    if isinstance(value, datetime):
                        result[key] = value.isoformat()
                        
        elif name == "log_event":
            await db.log_event(
                event_type=arguments["event_type"],
                component=arguments["component"],
                description=arguments["description"],
                metadata=arguments.get("metadata")
            )
            result = {"event": arguments["event_type"], "status": "logged"}
            
        else:
            result = {"error": f"Unknown tool: {name}"}
            
        # Return raw JSON for Claude to visualize
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2)
        )]
        
    except Exception as e:
        error_result = {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }
        return [TextContent(
            type="text",
            text=json.dumps(error_result, indent=2)
        )]

async def main():
    """Run the MCP server"""
    # Initialize database schemas on startup
    await db.initialize_schemas()
    
    # Run the stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())