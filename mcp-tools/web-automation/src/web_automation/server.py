#!/usr/bin/env python3.11
"""
Web Automation MCP Server

Provides browser automation tools for the iOS to Android migration, specifically handling
all interactions with privacy.apple.com for photo transfers and Google Photos for monitoring.
This server manages the complete photo migration workflow from iCloud to Google Photos,
including authentication, transfer initiation, progress monitoring, and completion verification.

Key Features:
- Session persistence to avoid repeated 2FA (sessions valid ~7 days)
- Automated workflow through Apple's privacy portal
- Google Photos baseline establishment and monitoring
- Gmail integration for completion email verification
- Database tracking of all transfer operations

All operations use Playwright for browser automation with visual debugging support.
"""

import asyncio
import logging
import os
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
import mcp.server.stdio
import mcp.types as types

from .icloud_client import ICloudClientWithSession
from .logging_config import setup_logging

# Load environment variables from project root
# Project root is 4 levels up from this file: src/web_automation/server.py
root_dir = Path(__file__).parent.parent.parent.parent
env_file = root_dir / '.env'
load_dotenv(env_file)

# Use centralized logging
logger = setup_logging(__name__)

server = Server("web-automation")
icloud_client = None

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """List available tools"""
    return [
        types.Tool(
            name="check_icloud_status",
            description="DAY 1 TOOL: Check iCloud photo library status to get photo/video counts before migration. Authenticates with Apple ID via privacy.apple.com, retrieves current library statistics, and checks transfer history. Uses session persistence to avoid repeated 2FA for ~7 days. Essential first step before initialize_migration in migration-state.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reuse_session": {
                        "type": "boolean",
                        "description": "Whether to reuse saved browser session to avoid 2FA (default: true, recommended)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="start_photo_transfer",
            description="DAY 1 TOOL: Initiate Apple's official iCloud to Google Photos transfer service. Establishes Google Photos baseline count, navigates privacy.apple.com workflow, handles Google OAuth consent, and reaches confirmation page. Creates transfer record in database. Photos become visible Day 3-4, complete by Day 7. Use immediately after migration-state.initialize_migration.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reuse_session": {
                        "type": "boolean",
                        "description": "Whether to reuse Apple ID session from check_icloud_status (default: true, saves 2FA)",
                        "default": True
                    },
                    "confirm_transfer": {
                        "type": "boolean",
                        "description": "Whether to click 'Confirm Transfers' button to actually start the transfer (default: false for safety)",
                        "default": False
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="check_photo_transfer_progress",
            description="DAYS 3-7 TOOL: Monitor ongoing photo transfer by checking Google Photos count against baseline. Returns percentage complete, transfer rate, and time estimates. Note: Progress will show 0% until Day 3-4 when photos become visible. Use daily from Day 3 onwards to track progress (28% Day 4, 57% Day 5, 85% Day 6, 100% Day 7).",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {
                        "type": "string",
                        "description": "The transfer ID returned from start_photo_transfer (format: TRF-YYYYMMDD-HHMMSS)"
                    }
                },
                "required": ["transfer_id"]
            }
        ),
        types.Tool(
            name="verify_photo_transfer_complete",
            description="DAY 7 TOOL: Comprehensive verification that photo transfer completed successfully. Compares final Google Photos count with iCloud source, verifies specific important photos if provided, and generates completion certificate with grade. Use on Day 7 to confirm 100% success of the transfer.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {
                        "type": "string",
                        "description": "The transfer ID to verify completion for"
                    },
                    "important_photos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of important photo filenames to specifically check for (e.g., wedding photos, baby photos)"
                    }
                },
                "required": ["transfer_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Handle tool calls from the iOS2Android Agent.
    
    Each tool performs specific browser automation tasks in the photo migration workflow.
    All tools maintain session state to avoid repeated authentication and provide
    consistent user experience across the 7-day migration timeline.
    
    Tools interact with:
    - privacy.apple.com for Apple ID authentication and transfer initiation
    - photos.google.com for baseline establishment and progress monitoring
    - Gmail API for completion email verification
    - DuckDB database for transfer record persistence
    
    Args:
        name: The tool to execute
        arguments: Tool-specific parameters
        
    Returns:
        Formatted text response with status, statistics, and next steps
    """
    global icloud_client
    
    if name == "check_icloud_status":
        try:
            if icloud_client is None:
                # Use session persistence to avoid repeated 2FA
                session_dir = os.path.expanduser("~/.icloud_session")
                icloud_client = ICloudClientWithSession(session_dir=session_dir)
                await icloud_client.initialize()
            
            # Get credentials from environment only
            apple_id = os.getenv("APPLE_ID")
            password = os.getenv("APPLE_PASSWORD")
            
            if not apple_id or not password:
                return [types.TextContent(
                    type="text",
                    text="Error: Please configure APPLE_ID and APPLE_PASSWORD environment variables"
                )]
            
            reuse_session = arguments.get("reuse_session", True)
            
            result = await icloud_client.get_photo_status(
                apple_id=apple_id,
                password=password,
                force_fresh_login=not reuse_session
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
    
    elif name == "start_photo_transfer":
        try:
            if icloud_client is None:
                session_dir = os.path.expanduser("~/.icloud_session")
                icloud_client = ICloudClientWithSession(session_dir=session_dir)
                await icloud_client.initialize()
                await icloud_client.initialize_apis()
            
            reuse_session = arguments.get("reuse_session", True)
            confirm_transfer = arguments.get("confirm_transfer", False)
            
            result = await icloud_client.start_transfer(reuse_session=reuse_session, confirm_transfer=confirm_transfer)
            
            if result.get('status') == 'initiated':
                response = f"""✅ Photo Transfer Initiated Successfully!

Transfer ID: {result['transfer_id']}
Started: {result['started_at']}

📱 Source (iCloud):
• Photos: {result['source_counts']['photos']:,}
• Videos: {result['source_counts']['videos']:,}
• Total: {result['source_counts']['total']:,}
• Size: {result['source_counts']['size_gb']} GB

📊 Baseline Established:
• Google Photos baseline: {result['baseline_established']['google_photos_baseline_gb']:.2f} GB
• Total storage: {result['baseline_established']['total_storage_gb']:.0f} GB
• Available storage: {result['baseline_established']['available_storage_gb']:.2f} GB
• Baseline captured at: {result['baseline_established']['baseline_timestamp']}

⏱️ Estimated Completion: {result['estimated_completion_days']} days

💡 Next Steps:
1. Apple will process your transfer request
2. Check progress daily using transfer ID: {result['transfer_id']}
3. You'll receive an email when complete"""
            else:
                response = f"❌ Transfer initiation failed: {result.get('error', result.get('message'))}"
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Error starting transfer: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "check_photo_transfer_progress":
        try:
            if icloud_client is None:
                session_dir = os.path.expanduser("~/.icloud_session")
                icloud_client = ICloudClientWithSession(session_dir=session_dir)
                await icloud_client.initialize()
                await icloud_client.initialize_apis()
            
            transfer_id = arguments.get("transfer_id")
            if not transfer_id:
                return [types.TextContent(type="text", text="Error: transfer_id is required")]
            
            day_number = arguments.get("day_number")  # Optional parameter
            result = await icloud_client.check_transfer_progress(transfer_id, day_number)
            
            if result.get('status') != 'error':
                progress_bar_length = 20
                filled = int(progress_bar_length * result.get('progress', {}).get('percent_complete', 0) / 100)
                bar = '█' * filled + '░' * (progress_bar_length - filled)
                
                day_num = result.get('day_number', 1)
                percent = result.get('progress', {}).get('percent_complete', 0)
                
                response = f"""📊 Transfer Progress Report - Day {day_num}

Transfer ID: {result['transfer_id']}
Status: {result['status'].upper()}

Progress: [{bar}] {percent}%

📦 Storage Metrics:
• Baseline: {result.get('storage', {}).get('baseline_gb', 0)} GB
• Current: {result.get('storage', {}).get('current_gb', 0)} GB
• Growth: {result.get('storage', {}).get('growth_gb', 0)} GB
• Remaining: {result.get('storage', {}).get('remaining_gb', 0)} GB

📈 Estimated Transfer:
• Photos: {result.get('estimates', {}).get('photos_transferred', 0):,}
• Videos: {result.get('estimates', {}).get('videos_transferred', 0):,}
• Total items: {result.get('estimates', {}).get('total_items', 0):,}

⏱️ Transfer Rate:
• Speed: {result.get('progress', {}).get('transfer_rate_gb_per_day', 0)} GB/day
• Days remaining: {result.get('progress', {}).get('days_remaining', 0)}

💬 {result.get('message', 'Transfer in progress')}"""
                
                if result.get('snapshot_saved'):
                    response += "\n\n✅ Progress snapshot saved to database"
            else:
                response = f"❌ Progress check failed: {result.get('error')}"
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Error checking progress: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    elif name == "verify_photo_transfer_complete":
        try:
            if icloud_client is None:
                session_dir = os.path.expanduser("~/.icloud_session")
                icloud_client = ICloudClientWithSession(session_dir=session_dir)
                await icloud_client.initialize()
                await icloud_client.initialize_apis()
            
            transfer_id = arguments.get("transfer_id")
            if not transfer_id:
                return [types.TextContent(type="text", text="Error: transfer_id is required")]
            
            important_photos = arguments.get("important_photos")
            
            result = await icloud_client.verify_transfer_complete(
                transfer_id=transfer_id,
                important_photos=important_photos,
                include_email_check=False  # Email checking now handled by mobile-mcp
            )
            
            if result.get('status') != 'error':
                response = f"""🎉 Transfer Verification Report

Transfer ID: {result['transfer_id']}
Status: {result['status'].upper()}

✅ Verification Results:
• Source photos: {result['verification']['source_photos']:,}
• Destination photos: {result['verification']['destination_photos']:,}
• Match rate: {result['verification']['match_rate']}%

🏆 Completion Certificate:
• Grade: {result['certificate']['grade']}
• Score: {result['certificate']['score']}/100
• {result['certificate']['message']}

Certified at: {result['certificate']['issued_at']}

Note: Email verification is handled via mobile-mcp Gmail control"""
                
                if important_photos and result.get('important_photos_check'):
                    response += "\n\n📸 Important Photos Check:"
                    for photo in result['important_photos_check']:
                        response += f"\n• {photo}"
            else:
                response = f"❌ Verification failed: {result.get('error')}"
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Error verifying transfer: {e}")
            return [types.TextContent(type="text", text=f"Error: {str(e)}")]
    
    
    return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

# For test compatibility - expose functions directly
async def initialize_server():
    """Initialize the server for testing"""
    global icloud_client
    if not icloud_client:
        session_dir = os.path.expanduser("~/.icloud_session")
        icloud_client = ICloudClientWithSession(session_dir=session_dir)
        await icloud_client.initialize()
        await icloud_client.initialize_apis()
    return icloud_client

# Export the actual tool functions for testing
async def get_tools():
    """Get list of tools for testing"""
    return await handle_list_tools()

# Direct access to tool handler for testing
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Call a tool directly for testing"""
    return await handle_call_tool(name, arguments)

async def main():
    """Main function for the MCP server"""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

if __name__ == "__main__":
    asyncio.run(main())