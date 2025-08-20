#!/usr/bin/env python3.11
"""
Photo Migration MCP Server
Connects to privacy.apple.com to get real iCloud photo counts
"""

import asyncio
import logging
import os
from typing import Any, Dict
from pathlib import Path
from dotenv import load_dotenv
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

from .icloud_client import ICloudClientWithSession
from .logging_config import setup_logging

# Load environment variables from project root
# Project root is 4 levels up from this file: src/photo_migration/server.py
root_dir = Path(__file__).parent.parent.parent.parent
env_file = root_dir / '.env'
load_dotenv(env_file)

# Use centralized logging
logger = setup_logging(__name__)

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
                    "reuse_session": {
                        "type": "boolean",
                        "description": "Whether to reuse saved browser session (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="start_photo_transfer",
            description="Start iCloud to Google Photos transfer. Establishes baseline, gets counts, initiates transfer workflow.",
            inputSchema={
                "type": "object",
                "properties": {
                    "reuse_session": {
                        "type": "boolean",
                        "description": "Whether to reuse saved browser session (default: true)",
                        "default": True
                    }
                },
                "required": []
            }
        ),
        types.Tool(
            name="check_photo_transfer_progress",
            description="Monitor ongoing photo transfer progress. Shows percentage complete, transfer rate, and time estimates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {
                        "type": "string",
                        "description": "The transfer ID returned from start_photo_transfer"
                    }
                },
                "required": ["transfer_id"]
            }
        ),
        types.Tool(
            name="verify_photo_transfer_complete",
            description="Verify that photo transfer completed successfully. Checks counts, email confirmation, and generates completion certificate.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {
                        "type": "string",
                        "description": "The transfer ID to verify"
                    },
                    "important_photos": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Optional list of important photo filenames to check"
                    },
                    "include_email_check": {
                        "type": "boolean",
                        "description": "Whether to check for Apple completion email (default: true)",
                        "default": True
                    }
                },
                "required": ["transfer_id"]
            }
        ),
        types.Tool(
            name="check_photo_transfer_email",
            description="Check Gmail for Apple transfer completion email notification.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_id": {
                        "type": "string",
                        "description": "The transfer ID to check emails for"
                    }
                },
                "required": ["transfer_id"]
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
            
            result = await icloud_client.start_transfer(reuse_session=reuse_session)
            
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
• Existing Google Photos: {result['baseline_established']['pre_transfer_count']:,}
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
            
            result = await icloud_client.check_transfer_progress(transfer_id)
            
            if result.get('status') != 'error':
                progress_bar_length = 20
                filled = int(progress_bar_length * result['progress']['percent_complete'] / 100)
                bar = '█' * filled + '░' * (progress_bar_length - filled)
                
                response = f"""📊 Transfer Progress Report

Transfer ID: {result['transfer_id']}
Status: {result['status'].upper()}

Progress: [{bar}] {result['progress']['percent_complete']}%

📈 Statistics:
• Transferred: {result['counts']['transferred_items']:,} items
• Remaining: {result['counts']['remaining_items']:,} items
• Transfer rate: {result['progress']['transfer_rate_per_hour']:,} items/hour

⏱️ Timeline:
• Days elapsed: {result['timeline']['days_elapsed']}
• Estimated completion: {result['timeline']['estimated_completion']}

📷 Counts:
• Source total: {result['counts']['source_total']:,}
• Google baseline: {result['counts']['baseline_google']:,}
• Current Google total: {result['counts']['current_google']:,}"""
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
            include_email_check = arguments.get("include_email_check", True)
            
            result = await icloud_client.verify_transfer_complete(
                transfer_id=transfer_id,
                important_photos=important_photos,
                include_email_check=include_email_check
            )
            
            if result.get('status') != 'error':
                email_status = "✅ Found" if result.get('email_confirmation', {}).get('email_found') else "⏳ Not found yet"
                
                response = f"""🎉 Transfer Verification Report

Transfer ID: {result['transfer_id']}
Status: {result['status'].upper()}

✅ Verification Results:
• Source photos: {result['verification']['source_photos']:,}
• Destination photos: {result['verification']['destination_photos']:,}
• Match rate: {result['verification']['match_rate']}%

📧 Email Confirmation: {email_status}

🏆 Completion Certificate:
• Grade: {result['certificate']['grade']}
• Score: {result['certificate']['score']}/100
• {result['certificate']['message']}

Certified at: {result['certificate']['issued_at']}"""
                
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
    
    elif name == "check_photo_transfer_email":
        try:
            if icloud_client is None:
                session_dir = os.path.expanduser("~/.icloud_session")
                icloud_client = ICloudClientWithSession(session_dir=session_dir)
                await icloud_client.initialize()
                await icloud_client.initialize_apis()
            
            transfer_id = arguments.get("transfer_id")
            if not transfer_id:
                return [types.TextContent(type="text", text="Error: transfer_id is required")]
            
            result = await icloud_client.check_completion_email(transfer_id)
            
            if result.get('email_found'):
                response = f"""✅ Completion Email Found!

Transfer ID: {result['transfer_id']}

📧 Email Details:
• Subject: {result['email_details']['subject']}
• From: {result['email_details']['sender']}
• Received: {result['email_details']['received_at']}

Message: Transfer completion confirmed by Apple"""
            elif result.get('error'):
                if 'not configured' in result['error']:
                    response = "⚠️ Gmail API not configured. Please set GMAIL_CREDENTIALS_PATH in environment variables."
                else:
                    response = f"❌ Email check error: {result['error']}"
            else:
                response = f"""📧 No Completion Email Yet

Transfer ID: {result['transfer_id']}
Status: {result.get('message', 'Email not found')}

Apple typically sends completion emails within 24 hours of transfer completion."""
            
            return [types.TextContent(type="text", text=response)]
            
        except Exception as e:
            logger.error(f"Error checking email: {e}")
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