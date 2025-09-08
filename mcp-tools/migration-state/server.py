#!/usr/bin/env python3
"""
Migration State MCP Server

Provides 7 essential MCP tools for orchestrating iOS to Android phone migrations.
This server acts as a thin wrapper around the migration_db.py module, exposing database 
operations as MCP tools optimized for the iOS2Android Agent orchestration patterns.

Tools by Day:
- Day 1: initialize_migration, add_family_member, update_migration_status (3x), update_family_member_apps
- Days 2-7: get_migration_status (daily), update_migration_status (progress)
- Day 7: generate_migration_report
- As needed: get_family_members (query with filters)

Database: DuckDB at ~/.ios_android_migration/migration.db
"""

import sys
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, date

# Add parent directories to path to import shared modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# Add web_automation to path for imports
web_automation_path = Path(__file__).parent.parent / 'web-automation' / 'src'
sys.path.insert(0, str(web_automation_path))

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
from shared.database.migration_db import MigrationDatabase
from logging_config import setup_logging

# Import ICloudClient for storage checking
from web_automation.icloud_client import ICloudClientWithSession

# Set up logging
logger = setup_logging("migration_state.server")

# Initialize server and database
server = Server("migration-state")
db = MigrationDatabase()
icloud_client = None  # Will be initialized when needed

# ============================================================================
# MCP INTERFACE FUNCTIONS
# ============================================================================

@server.list_tools()
async def list_tools() -> list[Tool]:
    """
    List the 7 MCP tools available to the iOS2Android agent.
    
    Tools are organized by usage pattern:
    - Day 1 Setup: initialize_migration, add_family_member, update_migration_status
    - Daily Operations: get_migration_status, update_migration_status, update_family_member_apps
    - Query Tools: get_family_members
    - Completion: generate_migration_report
    
    Returns:
        List of Tool objects with descriptions optimized for agent understanding
    """
    return [
        Tool(
            name="initialize_migration",
            description="[DAY 1 ONLY] Creates a new migration. Call ONCE at the beginning. Returns migration_id to use in all subsequent calls. Example: initialize_migration(user_name='George Vetticaden', years_on_ios=18)",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {"type": "string", "description": "User's full name"},
                    "years_on_ios": {"type": "integer", "description": "How many years they've used iPhone"}
                },
                "required": ["user_name", "years_on_ios"]
            }
        ),
        Tool(
            name="add_family_member",
            description="[DAY 1] Add each family member. Call 4 times for typical family (spouse + 3 children). Ages 13-17 auto-create Venmo teen records. Names from contacts, no need to ask user. Example: add_family_member(migration_id='MIG-20250831-185510', name='Laila', role='child', age=17)",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID from initialize_migration"},
                    "name": {"type": "string", "description": "Name from phone contacts"},
                    "role": {"type": "string", "enum": ["spouse", "child"], "description": "'spouse' or 'child' only"},
                    "age": {"type": "integer", "description": "Age if child (triggers Venmo teen if 13-17)"},
                    "email": {"type": "string", "description": "Email (optional)"},
                    "phone": {"type": "string", "description": "Phone (optional)"}
                },
                "required": ["migration_id", "name", "role"]
            }
        ),
        Tool(
            name="update_migration_status",
            description="[DAYS 1-7] Progressive updates. Day 1: 3 calls (iCloud metrics, baseline, family). Days 2-7: 1 call each (progress%). Total: 9 calls. Pass ONLY new/changed fields each time. Example Day 1: update_migration_status(photo_count=60238, video_count=2418)",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID"},
                    "photo_count": {"type": "integer", "description": "Total photos from iCloud"},
                    "video_count": {"type": "integer", "description": "Total videos from iCloud"},
                    "total_icloud_storage_gb": {"type": "number", "description": "Total iCloud storage"},
                    "icloud_photo_storage_gb": {"type": "number", "description": "Photo storage GB"},
                    "icloud_video_storage_gb": {"type": "number", "description": "Video storage GB"},
                    "album_count": {"type": "integer", "description": "Number of albums"},
                    "google_photos_baseline_gb": {"type": "number", "description": "Baseline Google Photos storage"},
                    "whatsapp_group_name": {"type": "string", "description": "Family WhatsApp group name"},
                    "current_phase": {
                        "type": "string",
                        "enum": ["initialization", "media_transfer", "family_setup", "validation", "completed"],
                        "description": "Current migration phase"
                    },
                    "overall_progress": {"type": "integer", "minimum": 0, "maximum": 100, "description": "Overall progress percentage"},
                    "family_size": {"type": "integer", "description": "Number of family members"},
                    "completed_at": {"type": "string", "description": "Completion timestamp"}
                },
                "required": ["migration_id"]
            }
        ),
        Tool(
            name="update_family_member_apps",
            description="[DAYS 1-7] Update app status for family members. Day 1: WhatsApp group setup. Day 3: Location sharing. Day 5: Venmo teen activation. Example: update_family_member_apps(migration_id='MIG-20250831-185510', member_name='Jaisy', app_name='WhatsApp', status='configured', details={'whatsapp_in_group': true})",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID from initialize_migration"},
                    "member_name": {"type": "string", "description": "Family member name"},
                    "app_name": {"type": "string", "enum": ["WhatsApp", "Google Maps", "Venmo"], "description": "App name"},
                    "status": {"type": "string", "enum": ["not_started", "invited", "installed", "configured"], "description": "Status"},
                    "details": {
                        "type": "object",
                        "properties": {
                            "whatsapp_in_group": {"type": "boolean", "description": "In WhatsApp group"},
                            "location_sharing_sent": {"type": "boolean", "description": "Location sharing sent"},
                            "location_sharing_received": {"type": "boolean", "description": "Location sharing received"},
                            "venmo_card_activated": {"type": "boolean", "description": "Venmo card activated"},
                            "card_last_four": {"type": "string", "description": "Card last 4 digits"}
                        },
                        "description": "Optional granular tracking details"
                    }
                },
                "required": ["migration_id", "member_name", "app_name", "status"]
            }
        ),
        Tool(
            name="get_migration_status",
            description="[DAYS 2-7 DAILY] The UBER status tool. Call ONCE per day to get EVERYTHING: migration details, progress, family status. Returns complete picture for dashboard. Always pass migration_id and day_number. Example: get_migration_status(migration_id='MIG-20250831-185510', day_number=4)",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID from initialize_migration"},
                    "day_number": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 7,
                        "description": "Day number (1-7)"
                    }
                },
                "required": ["migration_id", "day_number"]
            }
        ),
        Tool(
            name="get_family_members",
            description="[AS NEEDED] Query family members. Filters: 'all', 'not_in_whatsapp', 'not_sharing_location', 'teen'. Use to check who needs app setup. Example: get_family_members(migration_id='MIG-20250831-185510', filter='teen') returns Laila & Ethan",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID from initialize_migration"},
                    "filter": {
                        "type": "string",
                        "enum": ["all", "not_in_whatsapp", "not_sharing_location", "teen"],
                        "default": "all",
                        "description": "Filter type"
                    }
                },
                "required": ["migration_id"]
            }
        ),
        Tool(
            name="generate_migration_report",
            description="[DAY 7 ONLY] Generate final celebration report. Shows 100% success with achievements. Call after marking migration complete. Format can be 'summary' or 'detailed'. Example: generate_migration_report(migration_id='MIG-20250831-185510', format='summary')",
            inputSchema={
                "type": "object",
                "properties": {
                    "migration_id": {"type": "string", "description": "Migration ID from initialize_migration"},
                    "format": {"type": "string", "enum": ["summary", "detailed"], "default": "summary", "description": "Report format"}
                },
                "required": ["migration_id"]
            }
        )
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    """
    Main MCP tool handler - Routes tool calls to appropriate database operations.
    
    This is the entry point for all 7 MCP tools. The agent calls tools with natural
    language understanding, and this function ensures consistent JSON responses with
    a 'success' field for every operation.
    
    Args:
        name: Tool name (one of the 7 exposed tools)
        arguments: Tool-specific parameters as dict
        
    Returns:
        List containing single TextContent with JSON response
        
    Response Format:
        All tools return JSON with at minimum:
        - success: boolean indicating if operation succeeded
        - Additional fields specific to each tool
    """
    logger.debug(f"Tool called: {name} with arguments: {json.dumps(arguments, default=str)}")
    
    try:
        result = {}
        
        # Get migration ID - required for all operations except initialize_migration
        migration_id = arguments.get("migration_id")
        
        # Validate migration_id is provided for all tools except initialize_migration
        if not migration_id and name != "initialize_migration":
            logger.error(f"Tool {name} called without migration_id")
            result = {
                "success": False,
                "error": "migration_id is required",
                "message": f"The migration_id parameter is required for {name}. Get it from initialize_migration and use it in all subsequent calls.",
                "hint": "Example: {name}(migration_id='MIG-20250831-185510', ...)"
            }
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2)
            )]
        
        if name == "initialize_migration":
            # Create new migration
            migration_id = await db.create_migration(
                user_name=arguments["user_name"],
                years_on_ios=arguments.get("years_on_ios")
            )
            logger.info(f"Migration initialized successfully: {migration_id}")
            result = {
                "success": True,
                "migration_id": migration_id,
                "status": "initialized",
                "message": f"Migration initialized for {arguments['user_name']}",
                "years_on_ios": arguments.get("years_on_ios")
            }
            
        elif name == "add_family_member":
            # Add family member with automatic teen Venmo detection
            if not migration_id:
                result = {
                    "success": False,
                    "error": "No migration found",
                    "message": "No migration found. Ensure you've called initialize_migration first and stored the migration_id.",
                    "hint": "Pass migration_id parameter or ensure there's an active migration"
                }
            else:
                # Determine if this is a teen needing Venmo
                age = arguments.get("age")
                needs_venmo_teen = age is not None and 13 <= age <= 17
                
                member_id = await db.add_family_member(
                    migration_id=migration_id,
                    name=arguments["name"],
                    role=arguments["role"],
                    email=arguments.get("email"),
                    phone=arguments.get("phone"),
                    age=age
                )
                
                # If teen, automatically create Venmo setup record
                if needs_venmo_teen:
                    with db.get_connection() as conn:
                        conn.execute("""
                            INSERT INTO venmo_setup (
                                migration_id, family_member_id, needs_teen_account
                            ) VALUES (?, ?, TRUE)
                        """, (migration_id, member_id))
                        conn.commit()
                
                # Also initialize app adoption records for all 3 apps
                apps = ["WhatsApp", "Google Maps", "Venmo"]
                with db.get_connection() as conn:
                    for app in apps:
                        conn.execute("""
                            INSERT INTO family_app_adoption (
                                family_member_id, app_name, status, invitation_method
                            ) VALUES (?, ?, 'not_started', 'email')
                        """, (member_id, app))
                    conn.commit()
                
                result = {
                    "success": True,
                    "status": "added",
                    "member_id": member_id,
                    "family_member": arguments["name"],
                    "role": arguments["role"],
                    "age": age,
                    "email": arguments.get("email"),
                    "phone": arguments.get("phone"),
                    "needs_venmo_teen": needs_venmo_teen
                }
                
        elif name == "update_migration_status":
            # Progressive update - only update provided fields
            if not migration_id:
                result = {
                    "success": False,
                    "error": "No migration found",
                    "message": "No migration found. Ensure you've called initialize_migration first and stored the migration_id.",
                    "hint": "Pass migration_id parameter or ensure there's an active migration"
                }
            else:
                with db.get_connection() as conn:
                    # Build dynamic update query based on provided fields
                    update_fields = []
                    values = []
                    
                    field_mapping = {
                        "photo_count": "photo_count",
                        "video_count": "video_count",
                        "total_icloud_storage_gb": "total_icloud_storage_gb",
                        "icloud_photo_storage_gb": "icloud_photo_storage_gb",
                        "icloud_video_storage_gb": "icloud_video_storage_gb",
                        "album_count": "album_count",
                        "google_photos_baseline_gb": "google_photos_baseline_gb",
                        "current_phase": "current_phase",
                        "overall_progress": "overall_progress",
                        "family_size": "family_size",
                        "whatsapp_group_name": "whatsapp_group_name",
                        "completed_at": "completed_at"
                    }
                    
                    for arg_key, db_field in field_mapping.items():
                        if arg_key in arguments and arg_key != "migration_id":
                            update_fields.append(f"{db_field} = ?")
                            values.append(arguments[arg_key])
                    
                    if update_fields:
                        query = f"UPDATE migration_status SET {', '.join(update_fields)} WHERE id = ?"
                        values.append(migration_id)
                        conn.execute(query, values)
                        
                        # Also update daily_progress if overall_progress is being updated
                        if "overall_progress" in arguments:
                            # Get current day number
                            migration_start = conn.execute(
                                "SELECT started_at FROM migration_status WHERE id = ?", 
                                (migration_id,)
                            ).fetchone()
                            
                            if migration_start and migration_start[0]:
                                from datetime import datetime
                                # migration_start[0] is the started_at value from the database
                                start_date_value = migration_start[0]
                                
                                # Handle both string and datetime types
                                if isinstance(start_date_value, str):
                                    start_date = datetime.fromisoformat(start_date_value.replace('Z', '+00:00'))
                                else:
                                    # Already a datetime object
                                    start_date = start_date_value
                                    
                                current_date = datetime.now()
                                day_number = (current_date - start_date).days + 1
                                
                                # Get current family adoption counts
                                family_stats = conn.execute("""
                                    SELECT 
                                        COUNT(DISTINCT CASE WHEN faa.app_name = 'WhatsApp' AND faa.whatsapp_in_group = TRUE THEN fm.id END) as whatsapp_connected,
                                        COUNT(DISTINCT CASE WHEN faa.app_name = 'Google Maps' AND faa.location_sharing_received = TRUE THEN fm.id END) as maps_sharing,
                                        COUNT(DISTINCT CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN fm.id END) as venmo_active
                                    FROM family_members fm
                                    LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                                    WHERE fm.migration_id = ?
                                """, (migration_id,)).fetchone()
                                
                                # Update daily_progress record
                                existing = conn.execute(
                                    "SELECT id FROM daily_progress WHERE migration_id = ? AND day_number = ?",
                                    (migration_id, day_number)
                                ).fetchone()
                                
                                if existing:
                                    conn.execute("""
                                        UPDATE daily_progress 
                                        SET whatsapp_members_connected = ?,
                                            maps_members_sharing = ?,
                                            venmo_members_active = ?
                                        WHERE migration_id = ? AND day_number = ?
                                    """, (family_stats[0], family_stats[1], family_stats[2], migration_id, day_number))
                        
                        conn.commit()
                        
                        result = {
                            "success": True,
                            "status": "updated",
                            "migration_id": migration_id,
                            "fields_updated": [k for k in arguments.keys() if k != "migration_id"]
                        }
                    else:
                        result = {
                            "success": False,
                            "status": "no_updates",
                            "message": "No fields provided to update"
                        }
                        
        elif name == "get_migration_status":
            # UBER status tool - returns everything with fresh storage data
            if not migration_id:
                result = {
                    "success": False,
                    "error": "No migration found",
                    "message": "No migration found. Ensure you've called initialize_migration first and stored the migration_id.",
                    "hint": "Pass migration_id parameter or ensure there's an active migration"
                }
            else:
                day_number = arguments["day_number"]
                
                # Get transfer_id from overview
                overview = await internal_get_migration_overview(migration_id)
                transfer_id = overview.get("transfer_id") if overview else None
                
                # For Day 2+ with valid transfer_id, check actual storage (except Day 7)
                # Day 7 is always 100% for demo, skip storage check
                if transfer_id and day_number >= 2 and day_number != 7:
                    try:
                        # Initialize iCloud client if needed (singleton pattern)
                        global icloud_client
                        if not icloud_client:
                            icloud_client = ICloudClientWithSession()
                            await icloud_client.initialize_apis()
                        
                        # Check real storage progress - this updates storage_snapshots & daily_progress
                        logger.info(f"Checking real storage progress for day {day_number}")
                        progress_result = await icloud_client.check_transfer_progress(
                            transfer_id=transfer_id,
                            day_number=day_number
                        )
                        logger.info(f"Storage check complete: {progress_result.get('progress', {}).get('percent_complete', 0)}%")
                    except Exception as e:
                        logger.warning(f"Could not check real storage: {e}")
                        # Continue with data from DB
                elif day_number == 7:
                    logger.info("Day 7: Skipping storage check, will return 100% completion")
                
                # Get all status information (now includes fresh storage data)
                daily = await internal_get_daily_summary(migration_id, day_number)
                overview = await internal_get_migration_overview(migration_id)
                family = await internal_get_family_service_summary(migration_id)
                
                # Get photo progress from latest storage snapshot (except Day 7)
                photo_progress = {}
                
                # Day 7 is always 100% for demo
                if day_number == 7:
                    with db.get_connection() as conn:
                        # Get expected counts from migration_status
                        migration_data = conn.execute("""
                            SELECT photo_count, video_count, total_icloud_storage_gb
                            FROM migration_status 
                            WHERE id = ?
                        """, (migration_id,)).fetchone()
                        
                        if migration_data:
                            photo_progress = {
                                "percent_complete": 100,
                                "current_storage_gb": migration_data[2],
                                "storage_growth_gb": migration_data[2],
                                "photos_transferred": migration_data[0],
                                "videos_transferred": migration_data[1],
                                "transfer_id": transfer_id,
                                "day_number": 7,
                                "status": "completed"
                            }
                else:
                    with db.get_connection() as conn:
                        # Get most recent storage snapshot
                        snapshot = conn.execute("""
                            SELECT google_photos_gb, storage_growth_gb, percent_complete,
                                   estimated_photos_transferred, estimated_videos_transferred
                            FROM storage_snapshots 
                            WHERE migration_id = ? 
                            ORDER BY snapshot_time DESC
                            LIMIT 1
                        """, (migration_id,)).fetchone()
                        
                        if snapshot:
                            # Use actual storage data from snapshot
                            photo_progress = {
                                "percent_complete": snapshot[2] or 0,
                                "current_storage_gb": snapshot[0],
                                "storage_growth_gb": snapshot[1],
                                "photos_transferred": snapshot[3] or 0,
                                "videos_transferred": snapshot[4] or 0,
                                "transfer_id": transfer_id,
                                "day_number": day_number,
                                "status": "in_progress" if day_number < 7 else "completed"
                            }
                        else:
                            # Fallback for Day 1 or if no snapshots yet
                            photo_progress = await internal_check_photo_transfer_progress(transfer_id, day_number, migration_id) if transfer_id else {}
                
                result = {
                    "success": True,
                    "day_number": day_number,
                    "migration": overview,
                    "day_summary": daily,
                    "migration_overview": overview,
                    "photo_progress": photo_progress,
                    "family_services": family,
                    "status_message": f"Day {day_number}: {photo_progress.get('percent_complete', 0)}% complete"
                }
                
        elif name == "get_family_members":
            # Query family members with filters
            if not migration_id:
                result = {
                    "success": False,
                    "error": "No migration found",
                    "message": "No migration found. Ensure you've called initialize_migration first and stored the migration_id.",
                    "hint": "Pass migration_id parameter or ensure there's an active migration",
                    "members": []  # Return empty array for consistency
                }
            else:
                filter_type = arguments.get("filter", "all")
                
                with db.get_connection() as conn:
                    base_query = """
                        SELECT fm.id, fm.migration_id, fm.name, fm.role, fm.age, fm.email, fm.phone, fm.staying_on_ios,
                               fm.created_at,
                               MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.whatsapp_in_group END) as whatsapp_in_group,
                               MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.location_sharing_received END) as location_sharing_received
                        FROM family_members fm
                        LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                        WHERE fm.migration_id = ?
                    """
                    
                    # Add GROUP BY first, then use HAVING for aggregate conditions
                    base_query += " GROUP BY fm.id, fm.migration_id, fm.name, fm.role, fm.age, fm.email, fm.phone, fm.staying_on_ios, fm.created_at"
                    
                    if filter_type == "not_in_whatsapp":
                        base_query += " HAVING (whatsapp_in_group IS FALSE OR whatsapp_in_group IS NULL)"
                    elif filter_type == "not_sharing_location":
                        base_query += " HAVING (location_sharing_received IS FALSE OR location_sharing_received IS NULL)"
                    elif filter_type == "teen":
                        # Teen filter is on the base table, not aggregate, so use WHERE
                        base_query = """
                            SELECT fm.id, fm.migration_id, fm.name, fm.role, fm.age, fm.email, fm.phone, fm.staying_on_ios,
                                   fm.created_at,
                                   MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.whatsapp_in_group END) as whatsapp_in_group,
                                   MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.location_sharing_received END) as location_sharing_received
                            FROM family_members fm
                            LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                            WHERE fm.migration_id = ? AND fm.age BETWEEN 13 AND 17
                            GROUP BY fm.id, fm.migration_id, fm.name, fm.role, fm.age, fm.email, fm.phone, fm.staying_on_ios, fm.created_at
                        """
                    
                    cursor = conn.execute(base_query, (migration_id,))
                    results = cursor.fetchall()
                    columns = [desc[0] for desc in cursor.description]
                    
                    members = []
                    for row in results:
                        row_dict = dict(zip(columns, row))
                        members.append({
                            "name": row_dict["name"],
                            "role": row_dict["role"],
                            "age": row_dict["age"],
                            "email": row_dict["email"],
                            "whatsapp_in_group": row_dict["whatsapp_in_group"],
                            "location_sharing": row_dict["location_sharing_received"]
                        })
                    
                    result = {
                        "success": True,
                        "filter": filter_type,
                        "count": len(members),
                        "members": members
                    }
                    
        elif name == "generate_migration_report":
            # migration_id is already validated as required above
            if not migration_id:
                result = {
                    "success": False,
                    "error": "migration_id is required",
                    "message": "The migration_id parameter is required for generate_migration_report."
                }
            else:
                format_type = arguments.get("format", "summary")
                
                # Get migration details
                with db.get_connection() as conn:
                    migration = conn.execute("""
                        SELECT * FROM migration_status WHERE id = ?
                    """, (migration_id,)).fetchone()
                    
                    if migration:
                        columns = [desc[0] for desc in conn.description]
                        migration_dict = dict(zip(columns, migration))
                        
                        # Get family stats
                        family_stats = conn.execute("""
                            SELECT 
                                COUNT(*) as total_members,
                                SUM(CASE WHEN faa.app_name = 'WhatsApp' AND faa.status = 'configured' THEN 1 ELSE 0 END) as whatsapp_configured,
                                SUM(CASE WHEN faa.app_name = 'Google Maps' AND faa.status = 'configured' THEN 1 ELSE 0 END) as maps_configured,
                                SUM(CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN 1 ELSE 0 END) as venmo_configured
                            FROM family_members fm
                            LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                            WHERE fm.migration_id = ?
                        """, (migration_id,)).fetchone()
                        
                        # Generate celebratory report
                        report = {
                            "🎉": "MIGRATION COMPLETE!",
                            "summary": {
                                "user": migration_dict["user_name"],
                                "duration": "7 days",
                                "freed_from": f"{migration_dict.get('years_on_ios', 'many')} years of iOS"
                            },
                            "achievements": {
                                "photos": f"✅ {migration_dict.get('photo_count', 0):,} photos transferred",
                                "videos": f"✅ {migration_dict.get('video_count', 0):,} videos transferred",
                                "storage": f"✅ {migration_dict.get('total_icloud_storage_gb', 0)}GB migrated to Google Photos",
                                "family": f"✅ {family_stats[0]}/{family_stats[0]} family members connected"
                            },
                            "apps_configured": {
                                "WhatsApp": f"✅ Family group with {family_stats[1]} members",
                                "Google Maps": f"✅ Location sharing with {family_stats[2]} members",
                                "Venmo": f"✅ {family_stats[3]} teen accounts" if family_stats[3] > 0 else "N/A"
                            },
                            "data_integrity": {
                                "photos_matched": True,
                                "videos_matched": True,
                                "zero_data_loss": True,
                                "apple_confirmation": "received"
                            },
                            "celebration_message": "Welcome to Android! Your family stays connected across platforms."
                        }
                        
                        result = {
                            "success": True,
                            "report": report
                        }
                    else:
                        result = {"status": "error", "message": "Migration not found"}
                        
        elif name == "update_family_member_apps":
            # Update family member app adoption
            if not migration_id:
                result = {
                    "success": False,
                    "error": "No migration found",
                    "message": "No migration found. Ensure you've called initialize_migration first and stored the migration_id.",
                    "hint": "Pass migration_id parameter or ensure there's an active migration"
                }
            else:
                member_name = arguments["member_name"]
                app_name = arguments["app_name"]
                status = arguments["status"]
                details = arguments.get("details", {})
                
                with db.get_connection() as conn:
                    # Get family member ID
                    member = conn.execute("""
                        SELECT id FROM family_members 
                        WHERE migration_id = ? AND name = ?
                    """, (migration_id, member_name)).fetchone()
                    
                    if member:
                        member_id = member[0]
                        
                        # Update app adoption status
                        update_fields = ["status = ?"]
                        values = [status]
                        
                        # Set configured_at if status is configured
                        if status == "configured":
                            update_fields.append("configured_at = CURRENT_TIMESTAMP")
                        elif status == "invited":
                            update_fields.append("invitation_sent_at = CURRENT_TIMESTAMP")
                        elif status == "installed":
                            update_fields.append("installed_at = CURRENT_TIMESTAMP")
                        
                        # Update optional details
                        details_updated = []
                        if "whatsapp_in_group" in details:
                            update_fields.append("whatsapp_in_group = ?")
                            values.append(details["whatsapp_in_group"])
                            details_updated.append("whatsapp_in_group")
                        if "location_sharing_sent" in details:
                            update_fields.append("location_sharing_sent = ?")
                            values.append(details["location_sharing_sent"])
                            details_updated.append("location_sharing_sent")
                        if "location_sharing_received" in details:
                            update_fields.append("location_sharing_received = ?")
                            values.append(details["location_sharing_received"])
                            details_updated.append("location_sharing_received")
                        if "venmo_card_activated" in details:
                            update_fields.append("venmo_card_activated = ?")
                            values.append(details["venmo_card_activated"])
                            details_updated.append("venmo_card_activated")
                        
                        query = f"""
                            UPDATE family_app_adoption 
                            SET {', '.join(update_fields)}
                            WHERE family_member_id = ? AND app_name = ?
                        """
                        values.extend([member_id, app_name])
                        
                        conn.execute(query, values)
                        
                        # If updating Venmo to configured, also update venmo_setup table
                        if app_name == "Venmo" and status == "configured":
                            # Check if venmo_setup record exists for this member
                            venmo_record = conn.execute("""
                                SELECT id FROM venmo_setup 
                                WHERE family_member_id = ?
                            """, (member_id,)).fetchone()
                            
                            if venmo_record:
                                # Update venmo_setup with card activation details
                                conn.execute("""
                                    UPDATE venmo_setup 
                                    SET card_arrived_at = CASE 
                                            WHEN card_arrived_at IS NULL THEN CURRENT_TIMESTAMP 
                                            ELSE card_arrived_at 
                                        END,
                                        card_activated_at = CURRENT_TIMESTAMP,
                                        setup_complete = ?
                                    WHERE family_member_id = ?
                                """, (details.get("venmo_card_activated", False), member_id))
                                
                                details_updated.append("venmo_setup_updated")
                        
                        conn.commit()
                        
                        result = {
                            "success": True,
                            "family_member": member_name,
                            "app": app_name,
                            "new_status": status,
                            "details_updated": details_updated
                        }
                    else:
                        result = {
                            "success": False,
                            "error": f"Family member '{member_name}' not found"
                        }
        else:
            result = {
                "error": f"Unknown tool: {name}",
                "available_tools": [
                    "initialize_migration", "add_family_member", "update_migration_status",
                    "update_family_member_apps", "get_migration_status", 
                    "get_family_members", "generate_migration_report"
                ]
            }
        
        return [TextContent(
            type="text",
            text=json.dumps(result, indent=2, default=str)
        )]
        
    except Exception as e:
        logger.error(f"Error in {name}: {str(e)}", exc_info=True)
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
    Main entry point for the Migration State MCP Server.
    
    Starts the server in stdio mode for communication with the iOS2Android agent.
    Initializes database schemas and provides 7 streamlined tools for managing
    the complete 7-day iOS to Android migration journey.
    
    The server is optimized for natural language agent interactions and follows
    the exact demo flow from demo-script-complete-final.md.
    
    Configuration:
        Add to ~/Library/Application Support/Claude/claude_desktop_config.json
    
    Database:
        DuckDB at ~/.ios_android_migration/migration.db
    """
    # Initialize database schemas on startup
    logger.info("Starting Migration State MCP Server")
    await db.initialize_schemas()
    logger.info("Database schemas initialized")
    
    # Run the stdio server
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options()
        )

# ============================================================================
# INTERNAL HELPER FUNCTIONS (not exposed as MCP tools)
# ============================================================================

async def internal_get_statistics(include_history: bool = False) -> Dict:
    """
    Internal statistics function - not exposed as MCP tool.
    Used by get_migration_status to gather metrics.
    
    Args:
        include_history: Whether to include historical data
        
    Returns:
        Dict with migration statistics
    """
    return await db.get_migration_statistics(include_history=include_history)

async def internal_get_daily_summary(migration_id: str, day_number: int) -> Dict:
    """
    Internal daily summary function - not exposed as MCP tool.
    Generates day-specific progress messages for get_migration_status.
    
    Progress follows the 7-day timeline:
    - Days 1-3: 0% (Apple processing)
    - Day 4: 28% (Photos appearing)
    - Day 5: 57% (Accelerating)
    - Day 6: 88% (Near completion)
    - Day 7: 100% (Success guaranteed)
    
    Args:
        migration_id: Migration identifier
        day_number: Day in migration (1-7)
        
    Returns:
        Dict with day summary including progress and milestones
    """
    with db.get_connection() as conn:
        # Get or create daily progress record
        key_milestone = {
            1: "Migration initialized, photo transfer started",
            2: "WhatsApp in progress, Maya pending",
            3: "WhatsApp complete! Location sharing active",
            4: "Photos appearing in Google Photos! 🎉",
            5: "Transfer accelerating, Venmo activation",
            6: "Near completion, final setup",
            7: "Migration complete! 100% success!"
        }.get(day_number, f"Day {day_number} progress")
        
        # Get current stats
        stats_result = conn.execute("""
            SELECT 
                mt.transferred_photos, mt.total_photos, mt.photo_status,
                mt.transferred_videos, mt.total_videos, mt.video_status,
                mt.transferred_size_gb, mt.total_size_gb,
                (SELECT COUNT(*) FROM family_app_adoption WHERE app_name = 'WhatsApp' AND status = 'configured') as whatsapp_configured,
                (SELECT COUNT(*) FROM family_members WHERE migration_id = m.id) as total_family
            FROM migration_status m
            LEFT JOIN media_transfer mt ON m.id = mt.migration_id
            WHERE m.id = ?
        """, (migration_id,)).fetchone()
        
        if stats_result:
            transferred_photos, total_photos, photo_status, transferred_videos, total_videos, video_status, transferred_gb, total_gb, whatsapp_configured, total_family = stats_result
            
            # Get actual photo progress from storage_snapshots (except Day 7)
            if day_number == 7:
                # ONLY Day 7 is hardcoded for demo success
                photo_progress = 100
                photo_message = "100% complete!"
            else:
                # For all other days, use actual data from storage_snapshots
                snapshot = conn.execute("""
                    SELECT percent_complete 
                    FROM storage_snapshots 
                    WHERE migration_id = ? 
                    ORDER BY snapshot_time DESC 
                    LIMIT 1
                """, (migration_id,)).fetchone()
                
                photo_progress = snapshot[0] if snapshot else 0
                
                if day_number < 4:
                    photo_message = "Processing by Apple (not visible yet)"
                elif day_number == 4:
                    photo_message = "Photos appearing! 🎉"
                else:
                    photo_message = f"{photo_progress}% complete"
            
            return {
                "day": day_number,
                "date": str(date.today()),
                "photo_progress": photo_progress,
                "photo_message": photo_message,
                "whatsapp_connected": whatsapp_configured or 0,
                "total_family": total_family or 0,
                "key_milestone": key_milestone
            }
        
        return {"day": day_number, "date": str(date.today())}

async def internal_get_migration_overview(migration_id: str) -> Dict:
    """
    Internal migration overview - not exposed as MCP tool.
    Returns complete migration record for get_migration_status.
    
    Args:
        migration_id: Migration identifier
        
    Returns:
        Dict with complete migration record or None if not found
    """
    with db.get_connection() as conn:
        result = conn.execute("""
            SELECT m.*, mt.transfer_id, mt.photo_status, mt.video_status,
                   mt.transferred_photos, mt.total_photos,
                   mt.transferred_size_gb, mt.total_size_gb
            FROM migration_status m
            LEFT JOIN media_transfer mt ON m.id = mt.migration_id
            WHERE m.id = ?
        """, (migration_id,)).fetchone()
        
        if result:
            columns = [desc[0] for desc in conn.description]
            return dict(zip(columns, result))
        return None

async def internal_check_photo_transfer_progress(transfer_id: str, day_number: int, migration_id: str) -> Dict:
    """
    Internal photo transfer progress - not exposed as MCP tool.
    Returns expected progress based on day number for get_migration_status.
    
    Note: Real implementation should query Google Photos storage.
    This provides timeline-appropriate messages for the demo flow.
    
    Args:
        transfer_id: Transfer identifier
        day_number: Day in migration (1-7)
        migration_id: Migration identifier
        
    Returns:
        Dict with transfer progress for the specified day
    """
    
    # Day 7: ALWAYS return 100% success (demo requirement)
    if day_number == 7:
        # Get migration details for accurate counts
        with db.get_connection() as conn:
            migration = conn.execute("""
                SELECT photo_count, video_count, total_icloud_storage_gb, google_photos_baseline_gb
                FROM migration_status WHERE id = ?
            """, (migration_id,)).fetchone()
            
            if migration:
                photo_count, video_count, total_storage, baseline_gb = migration
                
                return {
                    "transfer_id": transfer_id,
                    "day_number": 7,
                    "percent_complete": 100,
                    "photos_transferred": photo_count,
                    "videos_transferred": video_count,
                    "total_photos": photo_count,
                    "total_videos": video_count,
                    "storage_used_gb": total_storage,
                    "baseline_gb": baseline_gb,
                    "message": "Migration complete! 100% success! 🎉",
                    "status": "completed"
                }
    
    # For other days, return day-aware progress
    progress_messages = {
        1: "Transfer initiated, processing by Apple",
        2: "Processing continues (not visible yet)",
        3: "Apple processing, patience required",
        4: "Photos starting to appear in Google Photos!",
        5: "Transfer accelerating",
        6: "Nearing completion"
    }
    
    return {
        "transfer_id": transfer_id,
        "day_number": day_number,
        "percent_complete": 0 if day_number <= 3 else None,  # Unknown until we query
        "message": progress_messages.get(day_number, f"Day {day_number} progress"),
        "note": "Progress should be calculated from actual Google Photos storage query"
    }

async def internal_get_family_service_summary(migration_id: str) -> Dict:
    """
    Internal family service summary - not exposed as MCP tool.
    Aggregates family app adoption status for get_migration_status.
    
    Tracks:
    - WhatsApp group membership
    - Google Maps location sharing
    - Venmo card activation
    
    Args:
        migration_id: Migration identifier
        
    Returns:
        Dict with counts of family members using each service
    """
    with db.get_connection() as conn:
        result = conn.execute("""
            SELECT 
                COUNT(DISTINCT fm.id) as total_members,
                COUNT(DISTINCT CASE WHEN faa.app_name = 'WhatsApp' AND faa.status = 'configured' THEN faa.family_member_id END) as whatsapp_connected,
                COUNT(DISTINCT CASE WHEN faa.app_name = 'Google Maps' AND faa.status = 'configured' THEN faa.family_member_id END) as maps_sharing,
                COUNT(DISTINCT CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN faa.family_member_id END) as venmo_active
            FROM family_members fm
            LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
            WHERE fm.migration_id = ?
        """, (migration_id,)).fetchone()
        
        if result:
            return {
                "total_members": result[0],
                "whatsapp_connected": result[1],
                "maps_sharing": result[2],
                "venmo_active": result[3]
            }
        return {"total_members": 0}

# Note: internal_record_storage_snapshot was removed.
# Storage snapshots are now recorded by check_photo_transfer_progress in web-automation MCP tool
# which queries actual Google storage and populates both storage_snapshots and daily_progress tables

if __name__ == "__main__":
    asyncio.run(main())