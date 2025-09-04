#!/usr/bin/env python3.11
"""
Web Automation MCP Server

Provides browser automation tools for iOS to Android migration, handling complete photo transfer
workflow from iCloud to Google Photos. Designed specifically for the iOS2Android Agent to
orchestrate Apple's official data transfer service with session persistence and progress monitoring.

Core Capabilities:
- Apple ID authentication via privacy.apple.com with session reuse
- iCloud photo library status retrieval (counts, storage, history)
- Apple-to-Google photo transfer initiation with baseline establishment  
- Storage-based progress tracking via Google One monitoring
- Transfer completion verification with certificate generation

All operations maintain browser session state across the 7-day migration timeline to minimize
2FA requirements and provide consistent user experience.
"""

import asyncio
import logging
import os
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv
from mcp.server import Server
import mcp.server.stdio
import mcp.types as types

from .icloud_client import ICloudClientWithSession
from .logging_config import setup_logging

# Initialize environment and logging
root_dir = Path(__file__).parent.parent.parent.parent
load_dotenv(root_dir / '.env')
logger = setup_logging(__name__)

# Global server instance
server = Server("web-automation")
icloud_client = None

# ============================================================================
# PUBLIC MCP TOOLS - Exposed to iOS2Android Agent
# ============================================================================

@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    """
    Define MCP tools available to the iOS2Android Agent.
    
    These 4 tools form the complete photo migration workflow, designed for optimal
    agent orchestration following the DAY 1 → DAYS 3-7 → DAY 7 pattern.
    """
    return [
        types.Tool(
            name="check_icloud_status",
            description=(
                "Retrieve iCloud photo library statistics before migration. Authenticates via "
                "privacy.apple.com, extracts photo/video counts and storage usage, checks for "
                "existing transfer history. Uses persistent browser sessions to avoid repeated 2FA. "
                "Essential first step - call before initialize_migration to get actual counts."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "reuse_session": {
                        "type": "boolean",
                        "description": "Use saved browser session to skip 2FA (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        
        types.Tool(
            name="start_photo_transfer",
            description=(
                "Initiate Apple's official iCloud to Google Photos transfer service. Establishes "
                "Google Photos storage baseline, navigates complete privacy.apple.com workflow, "
                "handles OAuth consent, and optionally confirms transfer. Associates transfer "
                "with the migration for tracking. Photos visible Day 3-4, complete Day 7."
            ),
            inputSchema={
                "type": "object", 
                "properties": {
                    "migration_id": {
                        "type": "string",
                        "description": "Migration ID from initialize_migration (required to link transfer to migration)"
                    },
                    "reuse_session": {
                        "type": "boolean",
                        "description": "Reuse Apple ID session from check_icloud_status (default: true)",
                        "default": True
                    },
                    "confirm_transfer": {
                        "type": "boolean", 
                        "description": "Actually start transfer by clicking 'Confirm' (default: false for safety)",
                        "default": False
                    }
                },
                "required": ["migration_id"]
            }
        ),
        
        types.Tool(
            name="verify_photo_transfer_complete", 
            description=(
                "Comprehensive transfer completion verification with certificate generation. "
                "Performs final Google One storage check, compares against iCloud source counts, "
                "calculates match rates, and generates completion certificate with grade. "
                "Optionally verifies specific important photos. Use on Day 7 for final validation."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {
                        "type": "string",
                        "description": "Transfer ID to verify"
                    },
                    "important_photos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of specific photo filenames to verify"
                    }
                },
                "required": ["transfer_id"]
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """
    Execute MCP tools for the iOS2Android Agent.
    
    Handles all browser automation tasks in the photo migration workflow, maintaining
    session persistence and coordinating with the shared database for progress tracking.
    
    Args:
        name: Tool name to execute
        arguments: Tool-specific parameters
        
    Returns:
        Formatted text response with migration status, progress metrics, and next steps
    """
    global icloud_client
    
    if name == "check_icloud_status":
        return await _handle_check_icloud_status(arguments)
    elif name == "start_photo_transfer":
        return await _handle_start_photo_transfer(arguments)
    elif name == "verify_photo_transfer_complete":
        return await _handle_verify_complete(arguments)
    else:
        return [types.TextContent(type="text", text=f"Unknown tool: {name}")]

# ============================================================================
# INTERNAL TOOL IMPLEMENTATIONS
# ============================================================================

async def _handle_check_icloud_status(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Check iCloud photo library status and transfer history."""
    try:
        await _ensure_client_initialized()
        
        # Validate environment credentials
        apple_id = os.getenv("APPLE_ID") 
        password = os.getenv("APPLE_PASSWORD")
        if not apple_id or not password:
            return [types.TextContent(
                type="text",
                text="Error: Please configure APPLE_ID and APPLE_PASSWORD environment variables"
            )]
        
        # Execute iCloud status check
        reuse_session = arguments.get("reuse_session", True)
        result = await icloud_client.get_photo_status(
            apple_id=apple_id,
            password=password,
            force_fresh_login=not reuse_session
        )
        
        # Format response for agent
        response = f"""iCloud Photo Library Status:
📸 Photos: {result['photos']:,}
🎬 Videos: {result['videos']:,}
💾 Storage: {result['storage_gb']:.1f} GB
📦 Total Items: {result['total_items']:,}

Session: {'Reused saved session (no 2FA)' if result.get('session_used') else 'New session created'}

Transfer History:
"""
        # Add transfer history
        if result.get('existing_transfers'):
            for transfer in result['existing_transfers']:
                status_emoji = {
                    'complete': '✅', 'cancelled': '❌', 
                    'failed': '⚠️', 'in_progress': '🔄'
                }.get(transfer['status'], '❓')
                response += f"{status_emoji} {transfer['status'].title()} - {transfer.get('date', 'Unknown')}\n"
        else:
            response += "No previous transfer requests found\n"
        
        return [types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"iCloud status check failed: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

async def _handle_start_photo_transfer(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Initiate photo transfer with Google Photos baseline establishment."""
    try:
        await _ensure_client_initialized(initialize_apis=True)
        
        # Get required migration_id
        migration_id = arguments.get("migration_id")
        if not migration_id:
            return [types.TextContent(
                type="text", 
                text="Error: migration_id is required. Get it from initialize_migration and pass it to start_photo_transfer."
            )]
        
        # Execute transfer initiation
        reuse_session = arguments.get("reuse_session", True)
        confirm_transfer = arguments.get("confirm_transfer", False) 
        
        result = await icloud_client.start_transfer(
            migration_id=migration_id,
            reuse_session=reuse_session, 
            confirm_transfer=confirm_transfer
        )
        
        # Format success response
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
        logger.error(f"Transfer initiation failed: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]


async def _handle_verify_complete(arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Verify transfer completion with certificate generation."""
    try:
        await _ensure_client_initialized(initialize_apis=True)
        
        # Validate required parameters
        transfer_id = arguments.get("transfer_id")
        if not transfer_id:
            return [types.TextContent(type="text", text="Error: transfer_id is required")]
        
        # Execute completion verification
        important_photos = arguments.get("important_photos")
        result = await icloud_client.verify_transfer_complete(
            transfer_id=transfer_id,
            important_photos=important_photos,
            include_email_check=False  # Email verification handled by mobile-mcp
        )
        
        if result.get('status') != 'error':
            response = f"""🎉 Transfer Verification Report

Transfer ID: {result['transfer_id']}
Status: {result['status'].upper()}

✅ Verification Results:
• Source photos: {result['verification'].get('source_photos', 0):,}
• Source videos: {result['verification'].get('source_videos', 0):,}
• Estimated photos transferred: {result['verification'].get('estimated_photos', 0):,}
• Estimated videos transferred: {result['verification'].get('estimated_videos', 0):,}
• Match rate: {result['verification'].get('match_rate', 0)}%

🏆 Completion Certificate:
• Grade: {result['certificate']['grade']}
• Score: {result['certificate']['score']}/100
• {result['certificate']['message']}

Certified at: {result['certificate']['issued_at']}

Note: Email verification is handled via mobile-mcp Gmail control"""
            
            # Add important photos check if provided
            if important_photos and result.get('important_photos_check'):
                response += "\n\n📸 Important Photos Check:"
                for photo in result['important_photos_check']:
                    response += f"\n• {photo}"
        else:
            response = f"❌ Verification failed: {result.get('error')}"
        
        return [types.TextContent(type="text", text=response)]
        
    except Exception as e:
        logger.error(f"Verification failed: {e}")
        return [types.TextContent(type="text", text=f"Error: {str(e)}")]

# ============================================================================
# PRIVATE UTILITY FUNCTIONS
# ============================================================================

async def _ensure_client_initialized(initialize_apis: bool = False):
    """Ensure iCloud client is initialized with optional API initialization."""
    global icloud_client
    
    if icloud_client is None:
        session_dir = os.path.expanduser("~/.icloud_session")
        icloud_client = ICloudClientWithSession(session_dir=session_dir)
        await icloud_client.initialize()
    
    if initialize_apis:
        await icloud_client.initialize_apis()

# ============================================================================
# SERVER RUNTIME AND TEST COMPATIBILITY
# ============================================================================

async def main():
    """Main MCP server runtime."""
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# Test compatibility exports
async def initialize_server():
    """Initialize server for testing."""
    await _ensure_client_initialized(initialize_apis=True)
    return icloud_client

async def get_tools():
    """Get tools list for testing."""
    return await handle_list_tools()

async def call_tool(name: str, arguments: Dict[str, Any]) -> list[types.TextContent]:
    """Direct tool execution for testing."""
    return await handle_call_tool(name, arguments)

if __name__ == "__main__":
    asyncio.run(main())