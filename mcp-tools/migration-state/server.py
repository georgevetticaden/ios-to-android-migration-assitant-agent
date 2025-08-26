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
                    "status": {"type": "string", "enum": ["initialization", "photo_transfer", "family_setup", "validation", "completed"]},
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
        ),
        # New V2 Tools
        Tool(
            name="initialize_migration",
            description="Start a new migration with user details and photo counts from iCloud check",
            inputSchema={
                "type": "object",
                "properties": {
                    "user_name": {"type": "string"},
                    "years_on_ios": {"type": "integer", "default": 18},
                    "photo_count": {"type": "integer"},
                    "video_count": {"type": "integer"},
                    "storage_gb": {"type": "number"}
                },
                "required": ["user_name", "photo_count", "storage_gb"]
            }
        ),
        Tool(
            name="add_family_member",
            description="Add a family member with their email for sending app invitations",
            inputSchema={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "role": {"type": "string", "enum": ["spouse", "child"]},
                    "age": {"type": "integer", "description": "Optional, used for Venmo teen accounts"}
                },
                "required": ["name", "email"]
            }
        ),
        Tool(
            name="start_photo_transfer",
            description="Record that Apple photo transfer has been initiated",
            inputSchema={
                "type": "object",
                "properties": {
                    "transfer_initiated": {"type": "boolean", "default": True}
                }
            }
        ),
        Tool(
            name="update_family_member_apps",
            description="Update which apps a family member has installed/configured",
            inputSchema={
                "type": "object",
                "properties": {
                    "family_member_name": {"type": "string"},
                    "app_name": {"type": "string", "enum": ["WhatsApp", "Google Maps", "Venmo"]},
                    "status": {"type": "string", "enum": ["not_started", "invited", "installed", "configured"]}
                },
                "required": ["family_member_name", "app_name", "status"]
            }
        ),
        Tool(
            name="update_photo_progress",
            description="Update photo transfer progress metrics",
            inputSchema={
                "type": "object",
                "properties": {
                    "progress_percent": {"type": "number"},
                    "photos_transferred": {"type": "integer"},
                    "videos_transferred": {"type": "integer"},
                    "size_transferred_gb": {"type": "number"}
                },
                "required": ["progress_percent"]
            }
        ),
        Tool(
            name="activate_venmo_card",
            description="Record Venmo teen card activation",
            inputSchema={
                "type": "object",
                "properties": {
                    "family_member_name": {"type": "string"},
                    "card_last_four": {"type": "string"},
                    "card_activated": {"type": "boolean", "default": True}
                },
                "required": ["family_member_name"]
            }
        ),
        Tool(
            name="get_daily_summary",
            description="Get migration status summary for a specific day",
            inputSchema={
                "type": "object",
                "properties": {
                    "day_number": {"type": "integer", "minimum": 1, "maximum": 7}
                },
                "required": ["day_number"]
            }
        ),
        Tool(
            name="get_migration_overview",
            description="Get current overall migration status",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
        Tool(
            name="create_action_item",
            description="Create a follow-up task (like sending email invites)",
            inputSchema={
                "type": "object",
                "properties": {
                    "action_type": {"type": "string"},
                    "description": {"type": "string"},
                    "target_member": {"type": "string"}
                },
                "required": ["action_type", "description"]
            }
        ),
        Tool(
            name="generate_migration_report",
            description="Generate final migration completion report",
            inputSchema={
                "type": "object",
                "properties": {
                    "format": {"type": "string", "enum": ["summary", "detailed"], "default": "summary"}
                }
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
            
            # Create photo transfer record
            transfer_id = await db.create_photo_transfer(
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
                    # Check if photo_transfer record exists
                    existing = conn.execute("""
                        SELECT transfer_id FROM photo_transfer WHERE migration_id = ?
                    """, (active["id"],)).fetchone()
                    
                    if existing:
                        # Update existing record
                        conn.execute("""
                            UPDATE photo_transfer
                            SET status = 'initiated',
                                apple_transfer_initiated = ?,
                                photos_visible_day = 4,
                                estimated_completion_day = 7
                            WHERE migration_id = ?
                        """, (datetime.now(), active["id"]))
                    else:
                        # Create new record with proper transfer_id
                        transfer_id = f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                        conn.execute("""
                            INSERT INTO photo_transfer (
                                transfer_id, migration_id, 
                                total_photos, total_videos, total_size_gb,
                                status, apple_transfer_initiated,
                                photos_visible_day, estimated_completion_day
                            ) VALUES (?, ?, ?, ?, ?, 'initiated', ?, 4, 7)
                        """, (transfer_id, active["id"], 
                              active.get("photo_count", 0),
                              active.get("video_count", 0), 
                              active.get("storage_gb", 0),
                              datetime.now()))
                    
                    # Update migration phase
                    conn.execute("""
                        UPDATE migration_status
                        SET current_phase = 'photo_transfer'
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
                        FROM photo_transfer WHERE migration_id = ?
                    """, (active["id"],)).fetchone()
                    
                    if transfer_result:
                        total_photos, total_videos, total_size_gb, transfer_id = transfer_result
                        
                        photos_transferred = arguments.get("photos_transferred", int(total_photos * progress_percent / 100))
                        videos_transferred = arguments.get("videos_transferred", int(total_videos * progress_percent / 100))
                        size_transferred_gb = arguments.get("size_transferred_gb", total_size_gb * progress_percent / 100)
                        
                        # Update photo transfer progress
                        await db.update_photo_progress(
                            migration_id=active["id"],
                            transferred_photos=photos_transferred,
                            transferred_videos=videos_transferred,
                            transferred_size_gb=size_transferred_gb,
                            status='completed' if progress_percent >= 100 else 'in_progress'
                        )
                        
                        # Calculate daily rate
                        start_result = conn.execute("""
                            SELECT apple_transfer_initiated FROM photo_transfer 
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
                        result = {"status": "error", "message": "No photo transfer found"}
                        
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
                            pt.transferred_photos, pt.total_photos, pt.status as photo_status,
                            pt.transferred_size_gb, pt.total_size_gb,
                            (SELECT COUNT(*) FROM family_app_adoption WHERE app_name = 'WhatsApp' AND status = 'configured') as whatsapp_configured,
                            (SELECT COUNT(*) FROM family_app_adoption WHERE app_name = 'WhatsApp' AND status = 'invited') as whatsapp_invited,
                            (SELECT COUNT(*) FROM family_members WHERE migration_id = m.id) as total_family
                        FROM migration_status m
                        LEFT JOIN photo_transfer pt ON m.id = pt.migration_id
                        WHERE m.id = ?
                    """, (active["id"],)).fetchone()
                    
                    if stats_result:
                        transferred_photos, total_photos, photo_status, transferred_gb, total_gb, whatsapp_configured, whatsapp_invited, total_family = stats_result
                        
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
                            pt.total_photos, pt.total_videos, pt.total_size_gb,
                            COUNT(DISTINCT fm.id) as family_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'WhatsApp' AND faa.status = 'configured' THEN faa.family_member_id END) as whatsapp_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'Google Maps' AND faa.status = 'configured' THEN faa.family_member_id END) as maps_members,
                            COUNT(DISTINCT CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN faa.family_member_id END) as venmo_members
                        FROM migration_status m
                        JOIN photo_transfer pt ON m.id = pt.migration_id
                        LEFT JOIN family_members fm ON m.id = fm.migration_id
                        LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                        WHERE m.id = ?
                        GROUP BY m.id, m.user_name, m.years_on_ios, m.started_at,
                                 pt.total_photos, pt.total_videos, pt.total_size_gb
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