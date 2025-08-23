#!/usr/bin/env python3
"""
Migration State MCP Server
Thin wrapper around the existing migration_db.py to expose database operations as MCP tools
Returns raw JSON for Claude to visualize
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from shared.database.migration_db import MigrationDatabase
from datetime import datetime

# Initialize server and database
server = Server("migration-state")
db = MigrationDatabase()

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available database tools"""
    return [
        Tool(
            name="get_migration_status",
            description="Get current migration status and all details",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Optional specific migration ID"}
                }
            }
        ),
        Tool(
            name="update_migration_progress",
            description="Update migration progress metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string"},
                    "status": {"type": "string", "enum": ["planning", "in_progress", "completed", "failed"]},
                    "photos_transferred": {"type": "integer"},
                    "videos_transferred": {"type": "integer"},
                    "total_size_gb": {"type": "number"}
                },
                "required": ["migration_id", "status"]
            }
        ),
        Tool(
            name="get_pending_items",
            description="Get items still to be migrated",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["photos", "contacts", "apps", "messages", "all"]}
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="mark_item_complete",
            description="Mark individual migration items as complete",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {"type": "string"},
                    "item_id": {"type": "string"},
                    "details": {"type": "object"}
                },
                "required": ["item_type", "item_id"]
            }
        ),
        Tool(
            name="get_statistics",
            description="Get migration statistics as JSON",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_history": {"type": "boolean", "description": "Include historical migrations"}
                }
            }
        ),
        Tool(
            name="log_migration_event",
            description="Log a migration event",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string"},
                    "component": {"type": "string"},
                    "description": {"type": "string"},
                    "metadata": {"type": "object"}
                },
                "required": ["event_type", "component", "description"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Execute database operations and return raw JSON"""
    
    try:
        result = {}
        
        if name == "get_migration_status":
            migration_id = arguments.get("migration_id")
            if migration_id:
                result = await db.get_migration_status(migration_id)
            else:
                result = await db.get_active_migration()
            
            if not result:
                result = {"status": "no_active_migration"}
                
        elif name == "update_migration_progress":
            await db.update_migration_progress(
                migration_id=arguments["migration_id"],
                status=arguments["status"],
                photos_transferred=arguments.get("photos_transferred"),
                videos_transferred=arguments.get("videos_transferred"),
                total_size_gb=arguments.get("total_size_gb")
            )
            result = {
                "migration_id": arguments["migration_id"],
                "status": "updated",
                "new_status": arguments["status"]
            }
            
        elif name == "get_pending_items":
            category = arguments["category"]
            items = await db.get_pending_items(category)
            result = {
                "category": category,
                "pending_count": len(items) if items else 0,
                "items": items
            }
            
        elif name == "mark_item_complete":
            await db.mark_item_complete(
                item_type=arguments["item_type"],
                item_id=arguments["item_id"],
                details=arguments.get("details", {})
            )
            result = {
                "item_type": arguments["item_type"],
                "item_id": arguments["item_id"],
                "status": "marked_complete"
            }
            
        elif name == "get_statistics":
            include_history = arguments.get("include_history", False)
            stats = await db.get_migration_statistics(include_history=include_history)
            result = stats
            
        elif name == "log_migration_event":
            await db.log_event(
                event_type=arguments["event_type"],
                component=arguments["component"],
                description=arguments["description"],
                metadata=arguments.get("metadata", {})
            )
            result = {
                "event": arguments["event_type"],
                "component": arguments["component"],
                "status": "logged"
            }
            
        else:
            result = {"error": f"Unknown tool: {name}"}
        
        # Convert datetime objects to strings for JSON serialization
        def serialize(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            elif isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [serialize(item) for item in obj]
            return obj
            
        result = serialize(result)
        
        # Return raw JSON for Claude to visualize
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, ensure_ascii=False)
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