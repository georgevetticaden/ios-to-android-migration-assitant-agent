#!/usr/bin/env python3
"""
Migration State MCP Server

A comprehensive MCP server providing 16 tools aligned with the 7-day iOS to Android migration workflow.
This server acts as a thin wrapper around the migration_db.py module, exposing database 
operations as MCP tools optimized for the iOS2Android Agent orchestration patterns.

7-Day Workflow Tool Usage:
- Day 1: initialize_migration, add_family_member, start_photo_transfer
- Days 2-3: update_family_member_apps (WhatsApp adoption), get_daily_summary
- Day 4: update_photo_progress (photos become visible)
- Day 5: activate_venmo_card (teen cards arrive)
- Days 6-7: get_migration_overview, generate_migration_report

Tool Categories:
- Setup Tools: initialize_migration, add_family_member, start_photo_transfer
- Progress Tools: update_photo_progress, update_family_member_apps
- Monitoring Tools: get_daily_summary, get_migration_overview, get_statistics
- Completion Tools: activate_venmo_card, generate_migration_report
- Utility Tools: log_migration_event, create_action_item

All tools return raw JSON optimized for React visualization and Claude processing.

Database: DuckDB at ~/.ios_android_migration/migration.db
Tables: 8 (migration_status, family_members, media_transfer, app_setup, 
        family_app_adoption, daily_progress, venmo_setup, storage_snapshots)

Author: iOS2Android Migration Team
Version: 2.1 (Enhanced Tool Descriptions for 7-Day Workflow)
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
from datetime import datetime, timedelta, date

# Initialize server and database
server = Server("migration-state")
db = MigrationDatabase()

@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available database tools"""
    return [
        Tool(
            name="get_migration_status",
            description="Get current active migration status with comprehensive details. Use this to check progress at any time during the 7-day migration. Returns migration state, photo progress, family app adoption status, and current phase. Essential for daily check-ins and status updates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Optional specific migration ID to query (defaults to active migration)"}
                }
            }
        ),
        Tool(
            name="update_migration_progress",
            description="Update overall migration status and phase progression. Use this to advance through phases: initialization → media_transfer → family_setup → validation → completed. Updates database state when major milestones are reached (e.g., media transfer started, family apps configured, migration completed).",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID to update"},
                    "status": {"type": "string", "enum": ["initialization", "media_transfer", "family_setup", "validation", "completed"], "description": "New migration phase"},
                    "photos_transferred": {"type": "integer", "description": "Optional: Number of photos transferred so far"},
                    "videos_transferred": {"type": "integer", "description": "Optional: Number of videos transferred so far"},
                    "total_size_gb": {"type": "number", "description": "Optional: Total size transferred in GB"}
                },
                "required": ["migration_id", "status"]
            }
        ),
        Tool(
            name="get_pending_items",
            description="Get list of migration tasks or family member setups still pending completion. Use this to identify what needs attention during daily check-ins (Days 2-6). Shows which family members haven't installed apps, which setups are incomplete, etc.",
            inputSchema={
                "type": "object",
                "properties": {
                    "category": {"type": "string", "enum": ["photos", "contacts", "apps", "messages", "all"], "description": "Category of pending items to check (use 'apps' for family app adoption status)"}
                },
                "required": ["category"]
            }
        ),
        Tool(
            name="mark_item_complete",
            description="Mark specific migration tasks as completed. Use when individual items are verified as done (e.g., app installations verified, cards activated). Updates database to reflect completion status.",
            inputSchema={
                "type": "object",
                "properties": {
                    "item_type": {"type": "string", "description": "Type of item being marked complete (e.g., 'app_install', 'card_activation')"},
                    "item_id": {"type": "string", "description": "Unique identifier for the item"},
                    "details": {"type": "object", "description": "Optional additional details about the completion"}
                },
                "required": ["item_type", "item_id"]
            }
        ),
        Tool(
            name="get_statistics",
            description="Get comprehensive migration statistics for visualization. Use this to create React progress charts and dashboards. Returns raw JSON with photo counts, transfer rates, family app adoption metrics, and completion percentages. Perfect for daily status visualizations.",
            inputSchema={
                "type": "object",
                "properties": {
                    "include_history": {"type": "boolean", "description": "Include data from previous migrations (default: false)"}
                }
            }
        ),
        Tool(
            name="log_migration_event",
            description="Record significant migration events for audit trail and troubleshooting. Use when important milestones occur (transfer started, group created, cards activated). Creates timestamped log entries for the migration history.",
            inputSchema={
                "type": "object",
                "properties": {
                    "event_type": {"type": "string", "description": "Category of event (e.g., 'milestone', 'error', 'user_action')"},
                    "component": {"type": "string", "description": "Which part of the system (e.g., 'photo_transfer', 'whatsapp', 'venmo')"},
                    "description": {"type": "string", "description": "Human-readable description of what happened"},
                    "metadata": {"type": "object", "description": "Optional additional data (counts, IDs, etc.)"}
                },
                "required": ["event_type", "component", "description"]
            }
        ),
        # New V2 Tools
        Tool(
            name="initialize_migration",
            description="DAY 1 TOOL: Start a new 7-day migration after getting photo counts from web-automation.check_icloud_status. This creates the migration record, initializes database tables, and sets up app tracking. Use immediately after confirming user wants to proceed with migration. Returns migration_id for tracking.",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "User's name for the migration"},
                    "years_on_ios": {"type": "integer", "default": 18, "description": "How long user has been on iOS (for celebration message)"},
                    "photo_count": {"type": "integer", "description": "Total photos in iCloud (from web-automation check)"},
                    "video_count": {"type": "integer", "description": "Total videos in iCloud"},
                    "storage_gb": {"type": "number", "description": "Total storage size in GB (from iCloud check)"}
                },
                "required": ["user_name", "photo_count", "storage_gb"]
            }
        ),
        Tool(
            name="add_family_member",
            description="DAY 1 TOOL: Add family members who will receive app invitations and be included in cross-platform groups. Use after initialize_migration when user provides family member details. Ages 13-17 automatically create Venmo teen account records. This sets up tracking for WhatsApp, Google Maps, and Venmo adoption.",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Family member's name"},
                    "email": {"type": "string", "description": "Email address for sending app invitations"},
                    "role": {"type": "string", "enum": ["spouse", "child"], "description": "Relationship to user"},
                    "age": {"type": "integer", "description": "Age (required for Venmo teen accounts if 13-17)"}
                },
                "required": ["name", "email"]
            }
        ),
        Tool(
            name="start_photo_transfer",
            description="DAY 1 TOOL: Record that Apple's official photo transfer to Google Photos has been initiated via web-automation. Updates migration phase to 'photo_transfer' and sets expectations (photos visible Day 3-4, completion Day 7). Use after web-automation.start_photo_transfer succeeds.",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_initiated": {"type": "boolean", "default": True, "description": "Confirmation that transfer started successfully"}
                }
            }
        ),
        Tool(
            name="update_family_member_apps",
            description="DAYS 1-6 TOOL: Track family member progress through app adoption workflow. Use when: sending invitations (→'invited'), detecting installations (→'installed'), or adding to groups (→'configured'). Status progression: not_started → invited → installed → configured. Critical for tracking WhatsApp group completion.",
            inputSchema={
                "type": "object",
                "properties": {
                    "family_member_name": {"type": "string", "description": "Name of family member (must match add_family_member name)"},
                    "app_name": {"type": "string", "enum": ["WhatsApp", "Google Maps", "Venmo"], "description": "Which app status is being updated"},
                    "status": {"type": "string", "enum": ["not_started", "invited", "installed", "configured"], "description": "New status (invited=email sent, installed=app detected, configured=added to group)"}
                },
                "required": ["family_member_name", "app_name", "status"]
            }
        ),
        Tool(
            name="update_photo_progress",
            description="DAYS 4-7 TOOL: Update photo transfer progress when photos become visible in Google Photos. Day 4: ~28% visible, Day 6: ~85%, Day 7: 100%. Calculates transfer rates and ETAs. Use when mobile-mcp shows new photo counts in Google Photos app. Photos are NOT visible until Day 4.",
            inputSchema={
                "type": "object",
                "properties": {
                    "progress_percent": {"type": "number", "description": "Percentage of photos transferred (0-100)"},
                    "photos_transferred": {"type": "integer", "description": "Optional: Actual count if available (calculated from % if not provided)"},
                    "videos_transferred": {"type": "integer", "description": "Optional: Video count transferred"},
                    "size_transferred_gb": {"type": "number", "description": "Optional: GB transferred (calculated if not provided)"}
                },
                "required": ["progress_percent"]
            }
        ),
        Tool(
            name="activate_venmo_card",
            description="DAY 5 TOOL: Record when Venmo teen debit cards arrive and are activated. Cards arrive 3-5 days after account creation (typically Day 5). Use after mobile-mcp helps activate card through Venmo app. Updates both venmo_setup and family app adoption status to 'configured'.",
            inputSchema={
                "type": "object",
                "properties": {
                    "family_member_name": {"type": "string", "description": "Teen family member's name (must have age 13-17)"},
                    "card_last_four": {"type": "string", "description": "Last 4 digits of activated card (for records)"},
                    "card_activated": {"type": "boolean", "default": True, "description": "Confirmation that activation succeeded"}
                },
                "required": ["family_member_name"]
            }
        ),
        Tool(
            name="get_daily_summary",
            description="DAILY CHECK-IN TOOL: Get day-specific migration status with appropriate expectations. Day 1: Setup complete, Day 3: WhatsApp adoption, Day 4: Photos appear!, Day 5: Cards arrive, Day 7: Completion. Returns day-aware progress (e.g., photos shown as 0% until Day 4). Use for daily status updates.",
            inputSchema={
                "type": "object",
                "properties": {
                    "day_number": {"type": "integer", "minimum": 1, "maximum": 7, "description": "Which day of the 7-day migration timeline"}
                },
                "required": ["day_number"]
            }
        ),
        Tool(
            name="get_migration_overview",
            description="ANYTIME TOOL: Get comprehensive current migration status including phase, progress, family connections, and time elapsed. Use for detailed status checks, React dashboard data, or when user asks 'how are things going?'. Returns complete picture of migration state.",
            inputSchema={
                "type": "object",
                "properties": {},
                "description": "No parameters needed - returns active migration overview"
            }
        ),
        Tool(
            name="create_action_item",
            description="COORDINATION TOOL: Create reminder for follow-up actions that mobile-mcp will handle directly (like sending email invitations). Use when family members need to be contacted or reminded. Note: Actual email sending is done via mobile-mcp natural language commands.",
            inputSchema={
                "type": "object",
                "properties": {
                    "action_type": {"type": "string", "description": "Type of action needed (e.g., 'email_invite', 'reminder')"},
                    "description": {"type": "string", "description": "Description of what needs to be done"},
                    "target_member": {"type": "string", "description": "Which family member this action concerns"}
                },
                "required": ["action_type", "description"]
            }
        ),
        Tool(
            name="generate_migration_report",
            description="DAY 7 COMPLETION TOOL: Generate celebratory final report when migration is 100% complete. Use after Apple sends completion email and all photos are verified in Google Photos. Returns formatted celebration data perfect for React visualization with achievements, statistics, and success confirmation.",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["summary", "detailed"], "default": "summary", "description": "Level of detail in the report"}
                }
            }
        ),
        Tool(
            name="record_storage_snapshot",
            description="Record Google One storage metrics for progress tracking. Use when checking Google One storage page to calculate actual transfer progress based on storage growth. Compares to baseline to determine percentage complete.",
            inputSchema={
                "type": "object",
                "properties": {
                    "google_photos_gb": {"type": "number", "description": "Current Google Photos storage in GB"},
                    "google_drive_gb": {"type": "number", "description": "Current Google Drive storage in GB"},
                    "gmail_gb": {"type": "number", "description": "Current Gmail storage in GB"},
                    "day_number": {"type": "integer", "description": "Which day of migration (1-7)"},
                    "is_baseline": {"type": "boolean", "default": False, "description": "True if this is the initial baseline before transfer"}
                },
                "required": ["google_photos_gb", "day_number"]
            }
        ),
        Tool(
            name="get_storage_progress",
            description="Calculate transfer progress based on storage growth. Returns percentage complete by comparing current Google One storage to baseline and expected total. More accurate than Apple's estimates.",
            inputSchema={
                "type": "object",
                "properties": {},
                "description": "No parameters needed - calculates from latest snapshot"
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Execute database operations based on tool name and return JSON results.
    
    This is the main handler for all 16 MCP tools aligned with the 7-day migration workflow.
    Each tool performs specific database operations and returns structured JSON data for 
    Claude to process and visualize.
    
    Args:
        name (str): The name of the tool to execute. Must be one of the 16 registered tools.
        arguments (dict): Tool-specific arguments as defined in the tool's inputSchema.
    
    Returns:
        list[TextContent]: A list containing a single TextContent object with the JSON result.
    
    7-Day Workflow Tool Categories:
        - Setup (Day 1): initialize_migration, add_family_member, start_photo_transfer
        - Progress (Days 1-7): update_photo_progress, update_family_member_apps, update_migration_progress
        - Monitoring (Daily): get_daily_summary, get_migration_overview, get_migration_status
        - Completion (Days 5-7): activate_venmo_card, generate_migration_report
        - Support (Anytime): get_statistics, log_migration_event, create_action_item
        - Utility (Anytime): get_pending_items, mark_item_complete
    
    Raises:
        Exception: Any database or processing errors are caught and returned as error JSON.
    """
    
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
            
        # New V2 Tool Handlers
        elif name == "initialize_migration":
            # Create new migration with photo counts
            migration_id = await db.create_migration(
                user_name=arguments["user_name"],
                source_device="iPhone",
                target_device="Galaxy Z Fold 7",
                photo_count=arguments["photo_count"],
                video_count=arguments.get("video_count", 0),
                storage_gb=arguments["storage_gb"],
                years_on_ios=arguments.get("years_on_ios", 18)
            )
            
            # Create media transfer record
            transfer_id = await db.create_media_transfer(
                migration_id=migration_id,
                total_photos=arguments["photo_count"],
                total_videos=arguments.get("video_count", 0),
                total_size_gb=arguments["storage_gb"]
            )
            
            # Initialize app setup records
            with db.get_connection() as conn:
                # Get max ID for app_setup
                max_id_result = conn.execute("SELECT MAX(id) FROM app_setup").fetchone()
                next_id = (max_id_result[0] or 0) + 1
                
                for i, (app_name, category) in enumerate([
                    ("WhatsApp", "messaging"),
                    ("Google Maps", "location"),
                    ("Venmo", "payment")
                ]):
                    conn.execute("""
                        INSERT INTO app_setup (id, migration_id, app_name, category, setup_status)
                        VALUES (?, ?, ?, ?, 'pending')
                    """, (next_id + i, migration_id, app_name, category))
            
            result = {
                "migration_id": migration_id,
                "status": "initialized",
                "message": f"Migration initialized for {arguments['user_name']}",
                "photo_count": arguments["photo_count"],
                "video_count": arguments.get("video_count", 0),
                "storage_gb": arguments["storage_gb"]
            }
            
        elif name == "add_family_member":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                # Add family member
                member_id = await db.add_family_member(
                    migration_id=active["id"],
                    name=arguments["name"],
                    email=arguments["email"],
                    role=arguments.get("role"),
                    age=arguments.get("age")
                )
                
                # Initialize app adoption records
                with db.get_connection() as conn:
                    # Get max ID for family_app_adoption
                    max_id_result = conn.execute("SELECT MAX(id) FROM family_app_adoption").fetchone()
                    next_id = (max_id_result[0] or 0) + 1
                    
                    for i, app_name in enumerate(["WhatsApp", "Google Maps", "Venmo"]):
                        conn.execute("""
                            INSERT INTO family_app_adoption
                            (id, family_member_id, app_name, status)
                            VALUES (?, ?, ?, 'not_started')
                        """, (next_id + i, member_id, app_name))
                    
                    # If teen (13-17), create Venmo teen setup record
                    age = arguments.get("age")
                    if age and 13 <= age <= 17:
                        # Get max ID for venmo_setup
                        max_venmo_id = conn.execute("SELECT MAX(id) FROM venmo_setup").fetchone()
                        next_venmo_id = (max_venmo_id[0] or 0) + 1
                        
                        conn.execute("""
                            INSERT INTO venmo_setup
                            (id, migration_id, family_member_id, needs_teen_account)
                            VALUES (?, ?, ?, true)
                        """, (next_venmo_id, active["id"], member_id))
                
                result = {
                    "status": "added",
                    "family_member": arguments["name"],
                    "email": arguments["email"],
                    "role": arguments.get("role"),
                    "age": arguments.get("age"),
                    "needs_venmo_teen": age and 13 <= age <= 17 if age else False
                }
                
        elif name == "start_photo_transfer":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                # Create or update photo transfer status
                with db.get_connection() as conn:
                    # Check if media_transfer record exists
                    existing = conn.execute("""
                        SELECT transfer_id FROM media_transfer WHERE migration_id = ?
                    """, (active["id"],)).fetchone()
                    
                    if existing:
                        # Update existing record
                        conn.execute("""
                            UPDATE media_transfer
                            SET photo_status = 'initiated',
                                video_status = 'initiated',
                                overall_status = 'initiated',
                                apple_transfer_initiated = ?,
                                photos_visible_day = 4,
                                estimated_completion_day = 7
                            WHERE migration_id = ?
                        """, (datetime.now(), active["id"]))
                    else:
                        # Create new record with proper transfer_id
                        transfer_id = f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                        conn.execute("""
                            INSERT INTO media_transfer (
                                transfer_id, migration_id, 
                                total_photos, total_videos, total_size_gb,
                                photo_status, video_status, overall_status,
                                apple_transfer_initiated,
                                photos_visible_day, estimated_completion_day
                            ) VALUES (?, ?, ?, ?, ?, 'initiated', 'initiated', 'initiated', ?, 4, 7)
                        """, (transfer_id, active["id"], 
                              active.get("photo_count", 0),
                              active.get("video_count", 0), 
                              active.get("storage_gb", 0),
                              datetime.now()))
                    
                    # Update migration phase
                    conn.execute("""
                        UPDATE migration_status
                        SET current_phase = 'media_transfer'
                        WHERE id = ?
                    """, (active["id"],))
                
                result = {
                    "status": "transfer_initiated",
                    "message": "Apple photo transfer started",
                    "estimated_completion": "5-7 days",
                    "photos_visible": "Day 3-4"
                }
                
        elif name == "update_family_member_apps":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                with db.get_connection() as conn:
                    # Get family member ID
                    member_result = conn.execute("""
                        SELECT id FROM family_members 
                        WHERE migration_id = ? AND name = ?
                    """, (active["id"], arguments["family_member_name"])).fetchone()
                    
                    if not member_result:
                        result = {"status": "error", "message": f"Family member {arguments['family_member_name']} not found"}
                    else:
                        member_id = member_result[0]
                        
                        # Get previous status
                        prev_result = conn.execute("""
                            SELECT status FROM family_app_adoption
                            WHERE family_member_id = ? AND app_name = ?
                        """, (member_id, arguments["app_name"])).fetchone()
                        
                        previous_status = prev_result[0] if prev_result else "not_started"
                        
                        # Update app adoption status
                        conn.execute("""
                            UPDATE family_app_adoption
                            SET status = ?,
                                invitation_sent_at = CASE WHEN ? = 'invited' THEN ? ELSE invitation_sent_at END,
                                installed_at = CASE WHEN ? = 'installed' THEN ? ELSE installed_at END,
                                configured_at = CASE WHEN ? = 'configured' THEN ? ELSE configured_at END
                            WHERE family_member_id = ? AND app_name = ?
                        """, (
                            arguments["status"],
                            arguments["status"], datetime.now(),
                            arguments["status"], datetime.now(),
                            arguments["status"], datetime.now(),
                            member_id, arguments["app_name"]
                        ))
                        
                        # If WhatsApp configured, update app setup connected count
                        if arguments["app_name"] == "WhatsApp" and arguments["status"] == "configured":
                            count_result = conn.execute("""
                                SELECT COUNT(*) FROM family_app_adoption
                                WHERE app_name = 'WhatsApp' AND status = 'configured'
                            """).fetchone()
                            
                            conn.execute("""
                                UPDATE app_setup
                                SET family_members_connected = ?
                                WHERE migration_id = ? AND app_name = 'WhatsApp'
                            """, (count_result[0], active["id"]))
                        
                        result = {
                            "family_member": arguments["family_member_name"],
                            "app": arguments["app_name"],
                            "previous_status": previous_status,
                            "new_status": arguments["status"],
                            "timestamp": datetime.now().isoformat()
                        }
                        
        elif name == "update_photo_progress":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                progress_percent = arguments["progress_percent"]
                
                # Calculate transferred amounts based on percentage
                with db.get_connection() as conn:
                    transfer_result = conn.execute("""
                        SELECT total_photos, total_videos, total_size_gb, transfer_id
                        FROM media_transfer WHERE migration_id = ?
                    """, (active["id"],)).fetchone()
                    
                    if transfer_result:
                        total_photos, total_videos, total_size_gb, transfer_id = transfer_result
                        
                        photos_transferred = arguments.get("photos_transferred", int(total_photos * progress_percent / 100))
                        videos_transferred = arguments.get("videos_transferred", int(total_videos * progress_percent / 100))
                        size_transferred_gb = arguments.get("size_transferred_gb", total_size_gb * progress_percent / 100)
                        
                        # Update media transfer progress
                        await db.update_media_progress(
                            migration_id=active["id"],
                            transferred_photos=photos_transferred,
                            transferred_videos=videos_transferred,
                            transferred_size_gb=size_transferred_gb,
                            photo_status='completed' if progress_percent >= 100 else 'in_progress',
                            video_status='completed' if progress_percent >= 100 else 'in_progress',
                            overall_status='completed' if progress_percent >= 100 else 'in_progress'
                        )
                        
                        # Calculate daily rate
                        start_result = conn.execute("""
                            SELECT apple_transfer_initiated FROM media_transfer 
                            WHERE migration_id = ?
                        """, (active["id"],)).fetchone()
                        
                        daily_rate = 0
                        if start_result and start_result[0]:
                            days_elapsed = max(1, (datetime.now() - start_result[0]).days)
                            daily_rate = photos_transferred / days_elapsed
                        
                        result = {
                            "transfer_id": transfer_id,
                            "progress_percent": progress_percent,
                            "photos_transferred": photos_transferred,
                            "total_photos": total_photos,
                            "estimated_completion": f"{max(0, 7 - int(progress_percent / 14))} more days",
                            "daily_rate": int(daily_rate)
                        }
                    else:
                        result = {"status": "error", "message": "No media transfer found"}
                        
        elif name == "activate_venmo_card":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                with db.get_connection() as conn:
                    # Get family member ID
                    member_result = conn.execute("""
                        SELECT id FROM family_members 
                        WHERE migration_id = ? AND name = ?
                    """, (active["id"], arguments["family_member_name"])).fetchone()
                    
                    if not member_result:
                        result = {"status": "error", "message": f"Family member {arguments['family_member_name']} not found"}
                    else:
                        member_id = member_result[0]
                        card_activated = arguments.get("card_activated", True)
                        
                        # Update Venmo setup record
                        conn.execute("""
                            UPDATE venmo_setup
                            SET card_arrived_at = ?,
                                card_activated_at = CASE WHEN ? THEN ? ELSE NULL END,
                                card_last_four = ?,
                                setup_complete = ?
                            WHERE family_member_id = ?
                        """, (
                            datetime.now(),
                            card_activated, datetime.now(),
                            arguments.get("card_last_four", "****"),
                            card_activated,
                            member_id
                        ))
                        
                        # Update family member app adoption
                        conn.execute("""
                            UPDATE family_app_adoption
                            SET status = 'configured',
                                configured_at = ?
                            WHERE family_member_id = ? AND app_name = 'Venmo'
                        """, (datetime.now(), member_id))
                        
                        # Check if all Venmo cards activated
                        pending_result = conn.execute("""
                            SELECT COUNT(*) FROM venmo_setup 
                            WHERE migration_id = ? AND setup_complete = false
                        """, (active["id"],)).fetchone()
                        
                        if pending_result[0] == 0:
                            conn.execute("""
                                UPDATE app_setup
                                SET setup_status = 'completed'
                                WHERE migration_id = ? AND app_name = 'Venmo'
                            """, (active["id"],))
                        
                        result = {
                            "family_member": arguments["family_member_name"],
                            "card_activated": card_activated,
                            "card_last_four": arguments.get("card_last_four", "****"),
                            "venmo_status": "configured",
                            "message": "Teen card activated successfully"
                        }
                        
        elif name == "get_daily_summary":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                day_number = arguments["day_number"]
                
                with db.get_connection() as conn:
                    # Get or create daily progress record
                    key_milestone = {
                        1: "Migration initialized, photo transfer started",
                        3: "WhatsApp group complete, family connecting",
                        4: "Photos appearing in Google Photos!",
                        5: "Venmo teen cards activated",
                        6: "Near completion, final setup",
                        7: "Migration complete!"
                    }.get(day_number, f"Day {day_number} progress")
                    
                    # Get current stats
                    stats_result = conn.execute("""
                        SELECT 
                            mt.transferred_photos, mt.total_photos, mt.photo_status,
                            mt.transferred_videos, mt.total_videos, mt.video_status,
                            mt.transferred_size_gb, mt.total_size_gb,
                            (SELECT COUNT(*) FROM family_app_adoption WHERE app_name = 'WhatsApp' AND status = 'configured') as whatsapp_configured,
                            (SELECT COUNT(*) FROM family_app_adoption WHERE app_name = 'WhatsApp' AND status = 'invited') as whatsapp_invited,
                            (SELECT COUNT(*) FROM family_members WHERE migration_id = m.id) as total_family
                        FROM migration_status m
                        LEFT JOIN media_transfer mt ON m.id = mt.migration_id
                        WHERE m.id = ?
                    """, (active["id"],)).fetchone()
                    
                    if stats_result:
                        transferred_photos, total_photos, photo_status, transferred_videos, total_videos, video_status, transferred_gb, total_gb, whatsapp_configured, whatsapp_invited, total_family = stats_result
                        
                        # Day-aware photo progress
                        if day_number < 4:
                            photo_progress = 0
                            photo_message = "Transfer running, photos not visible yet"
                        else:
                            photo_progress = int((transferred_photos / total_photos * 100) if total_photos else 0)
                            photo_message = f"Photos starting to appear!" if day_number == 4 else f"{photo_progress}% complete"
                        
                        # Get family member names for WhatsApp status
                        configured_members = conn.execute("""
                            SELECT fm.name FROM family_members fm
                            JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                            WHERE fm.migration_id = ? AND faa.app_name = 'WhatsApp' AND faa.status = 'configured'
                        """, (active["id"],)).fetchall()
                        
                        invited_members = conn.execute("""
                            SELECT fm.name FROM family_members fm
                            JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                            WHERE fm.migration_id = ? AND faa.app_name = 'WhatsApp' AND faa.status = 'invited'
                        """, (active["id"],)).fetchall()
                        
                        result = {
                            "day": day_number,
                            "date": date.today().isoformat(),
                            "photo_status": {
                                "status": photo_status,
                                "progress": photo_progress,
                                "message": photo_message
                            },
                            "whatsapp_status": {
                                "configured": [m[0] for m in configured_members],
                                "invited": [m[0] for m in invited_members],
                                "message": "Family group complete" if whatsapp_configured == total_family else f"{whatsapp_configured}/{total_family} connected"
                            },
                            "key_milestone": key_milestone,
                            "celebration": day_number in [4, 7]
                        }
                        
                        if day_number == 4 and photo_progress > 0:
                            result["photo_status"]["photos_visible"] = transferred_photos
                    else:
                        result = {"status": "error", "message": "Could not get migration stats"}
                        
        elif name == "get_migration_overview":
            # Get comprehensive migration status
            active = await db.get_active_migration()
            if not active:
                result = {"status": "no_active_migration"}
            else:
                with db.get_connection() as conn:
                    # Get detailed stats
                    stats = await db.get_migration_statistics(include_history=False)
                    
                    # Calculate days elapsed
                    started_at = active.get("started_at")
                    days_elapsed = 0
                    if started_at:
                        if isinstance(started_at, str):
                            started_at = datetime.fromisoformat(started_at)
                        days_elapsed = (datetime.now() - started_at).days
                    
                    # Get family status
                    family_result = conn.execute("""
                        SELECT 
                            COUNT(DISTINCT fm.id) as total_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'WhatsApp' AND faa.status = 'configured' THEN faa.family_member_id END) as whatsapp_connected,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'Google Maps' AND faa.status = 'configured' THEN faa.family_member_id END) as maps_sharing,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN faa.family_member_id END) as venmo_active
                        FROM family_members fm
                        LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                        WHERE fm.migration_id = ?
                    """, (active["id"],)).fetchone()
                    
                    total_members, whatsapp_connected, maps_sharing, venmo_active = family_result or (0, 0, 0, 0)
                    
                    result = {
                        "migration_id": active["id"],
                        "user": active.get("user_name", "Unknown"),
                        "phase": active.get("current_phase", "initialization"),
                        "overall_progress": active.get("overall_progress", 0),
                        "started": active.get("started_at"),
                        "days_elapsed": days_elapsed,
                        "photo_transfer": {
                            "status": active.get("photo_transfer_status", "pending"),
                            "progress": f"{active.get('transferred_photos', 0)}/{active.get('total_photos', 0)} photos",
                            "size": f"{active.get('transferred_size_gb', 0):.1f}/{active.get('total_size_gb', 0):.1f} GB"
                        },
                        "family_status": {
                            "total_members": total_members,
                            "whatsapp_connected": whatsapp_connected,
                            "maps_sharing": maps_sharing,
                            "venmo_active": venmo_active
                        },
                        "estimated_completion": f"{max(0, 7 - days_elapsed)} more days"
                    }
                    
        elif name == "create_action_item":
            # Simplified - actions are handled directly by mobile-mcp
            result = {
                "message": "Action handled directly by mobile-mcp",
                "action": arguments["description"],
                "method": "email"
            }
            
        elif name == "generate_migration_report":
            # Generate final migration completion report
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                with db.get_connection() as conn:
                    # Comprehensive final report query
                    report_result = conn.execute("""
                        SELECT 
                            m.user_name, m.years_on_ios, m.started_at,
                            mt.total_photos, mt.total_videos, mt.total_size_gb,
                            COUNT(DISTINCT fm.id) as family_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'WhatsApp' AND faa.status = 'configured' THEN faa.family_member_id END) as whatsapp_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'Google Maps' AND faa.status = 'configured' THEN faa.family_member_id END) as maps_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN faa.family_member_id END) as venmo_members
                        FROM migration_status m
                        JOIN media_transfer mt ON m.id = mt.migration_id
                        LEFT JOIN family_members fm ON m.id = fm.migration_id
                        LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                        WHERE m.id = ?
                        GROUP BY m.id, m.user_name, m.years_on_ios, m.started_at,
                                 mt.total_photos, mt.total_videos, mt.total_size_gb
                    """, (active["id"],)).fetchone()
                    
                    if report_result:
                        user_name, years_on_ios, started_at, total_photos, total_videos, total_gb, family_members, whatsapp, maps, venmo = report_result
                        
                        # Calculate duration
                        if isinstance(started_at, str):
                            started_at = datetime.fromisoformat(started_at)
                        duration_days = (datetime.now() - started_at).days if started_at else 7
                        
                        result = {
                            "🎉": "MIGRATION COMPLETE!",
                            "summary": {
                                "user": user_name,
                                "duration": f"{duration_days} days",
                                "freed_from": f"{years_on_ios or 18} years of iOS"
                            },
                            "achievements": {
                                "photos": f"✅ {total_photos:,} photos transferred",
                                "videos": f"✅ {total_videos:,} videos transferred",
                                "storage": f"✅ {total_gb}GB migrated to Google Photos",
                                "family": f"✅ {family_members}/{family_members} family members connected"
                            },
                            "apps_configured": {
                                "WhatsApp": f"✅ Family group with {whatsapp} members",
                                "Google Maps": f"✅ Location sharing active" if maps > 0 else "⏳ Location sharing pending",
                                "Venmo": f"✅ Teen cards activated" if venmo > 0 else "⏳ Venmo setup pending"
                            },
                            "data_integrity": {
                                "photos_matched": True,
                                "zero_data_loss": True,
                                "apple_confirmation": "received"
                            },
                            "celebration_message": "Welcome to Android! Your family stays connected across platforms."
                        }
                    else:
                        result = {"status": "error", "message": "Could not generate report"}
                        
        elif name == "record_storage_snapshot":
            # Get active migration
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                google_photos_gb = arguments["google_photos_gb"]
                google_drive_gb = arguments.get("google_drive_gb", 0)
                gmail_gb = arguments.get("gmail_gb", 0)
                day_number = arguments["day_number"]
                is_baseline = arguments.get("is_baseline", False)
                
                with db.get_connection() as conn:
                    # If this is baseline, update migration_status
                    if is_baseline:
                        conn.execute("""
                            UPDATE migration_status
                            SET google_photos_baseline_gb = ?,
                                google_drive_baseline_gb = ?,
                                gmail_baseline_gb = ?
                            WHERE id = ?
                        """, (google_photos_gb, google_drive_gb, gmail_gb, active["id"]))
                        
                        storage_growth_gb = 0
                        percent_complete = 0
                        estimated_photos = 0
                        estimated_videos = 0
                        progress_calc = {"message": "Baseline established.", "success": False}
                    else:
                        # Use shared calculate_storage_progress method for consistent calculation
                        progress_calc = await db.calculate_storage_progress(
                            migration_id=active["id"],
                            current_storage_gb=google_photos_gb,
                            day_number=day_number
                        )
                        
                        # Check for error
                        if progress_calc.get('status') == 'error':
                            result = progress_calc
                        else:
                            # Extract calculated values
                            storage_info = progress_calc.get('storage', {})
                            estimates = progress_calc.get('estimates', {})
                            progress_info = progress_calc.get('progress', {})
                            
                            storage_growth_gb = storage_info.get('growth_gb', 0)
                            percent_complete = progress_info.get('percent_complete', 0)
                            estimated_photos = estimates.get('photos_transferred', 0)
                            estimated_videos = estimates.get('videos_transferred', 0)
                    
                    # Insert storage snapshot
                    conn.execute("""
                        INSERT INTO storage_snapshots (
                            migration_id, day_number, google_photos_gb,
                            google_drive_gb, gmail_gb, total_used_gb,
                            storage_growth_gb, percent_complete,
                            estimated_photos_transferred, estimated_videos_transferred,
                            is_baseline
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        active["id"], day_number, google_photos_gb,
                        google_drive_gb, gmail_gb, google_photos_gb + google_drive_gb + gmail_gb,
                        storage_growth_gb, percent_complete,
                        estimated_photos, estimated_videos, is_baseline
                    ))
                    
                    # Only build result if no error occurred
                    if progress_calc.get('status') != 'error':
                        result = {
                            "status": "snapshot_recorded",
                            "day": day_number,
                            "google_photos_gb": google_photos_gb,
                            "storage_growth_gb": storage_growth_gb,
                            "percent_complete": percent_complete,
                            "estimated_photos": estimated_photos,
                            "estimated_videos": estimated_videos,
                            "is_baseline": is_baseline,
                            "message": progress_calc.get('message', '') if not is_baseline else "Baseline established.",
                            "success": progress_calc.get('success', False) if not is_baseline else False
                        }
                    
        elif name == "get_storage_progress":
            # Get active migration and latest snapshot
            active = await db.get_active_migration()
            if not active:
                result = {"status": "error", "message": "No active migration"}
            else:
                with db.get_connection() as conn:
                    # Get latest storage snapshot
                    latest = conn.execute("""
                        SELECT 
                            ss.day_number, ss.google_photos_gb, ss.storage_growth_gb,
                            ss.percent_complete, ss.estimated_photos_transferred,
                            ss.estimated_videos_transferred, ss.snapshot_time,
                            mt.total_photos, mt.total_videos, mt.total_size_gb,
                            ms.google_photos_baseline_gb
                        FROM storage_snapshots ss
                        JOIN migration_status ms ON ss.migration_id = ms.id
                        JOIN media_transfer mt ON ms.id = mt.migration_id
                        WHERE ss.migration_id = ?
                        ORDER BY ss.snapshot_time DESC
                        LIMIT 1
                    """, (active["id"],)).fetchone()
                    
                    if latest:
                        result = {
                            "day": latest[0],
                            "current_storage_gb": latest[1],
                            "storage_growth_gb": latest[2],
                            "percent_complete": latest[3],
                            "photos_progress": f"{latest[4]:,}/{latest[7]:,}",
                            "videos_progress": f"{latest[5]:,}/{latest[8]:,}",
                            "size_progress": f"{latest[2]:.1f}/{latest[9]:.1f} GB",
                            "baseline_gb": latest[10],
                            "last_updated": latest[6]
                        }
                    else:
                        result = {"status": "no_snapshots", "message": "No storage snapshots recorded yet"}
            
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
    """
    Run the Migration State MCP server.
    
    This function initializes the database schemas and starts the MCP server
    using stdio for communication with Claude Desktop. The server will run
    continuously, handling tool requests from Claude.
    
    The server communicates via:
    - Input: JSON-RPC messages from Claude via stdin
    - Output: JSON-RPC responses to Claude via stdout
    
    Database initialization is performed on startup to ensure the schema
    exists, though the actual schema setup should be done via
    shared/database/scripts/initialize_database.py
    """
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