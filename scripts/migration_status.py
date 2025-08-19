#!/usr/bin/env python3.11
"""
Check current migration status across all tools
Provides a unified view of the migration progress
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from shared.database.migration_db import get_migration_db
from shared.config.settings import get_settings
from shared.utils.logging_config import setup_logging

async def main(migration_id: str = None):
    """
    Check migration status
    
    Args:
        migration_id: Specific migration ID to check, or None for active migration
    """
    
    # Set up logging
    logger = setup_logging(name='migration_status', file=False)
    
    print("\n" + "="*60)
    print("iOS to Android Migration Status")
    print("="*60)
    
    # Get database
    db = get_migration_db()
    
    try:
        # Get migration to check
        if migration_id:
            migration = await db.get_migration(migration_id)
            if not migration:
                print(f"\n❌ Migration {migration_id} not found")
                return False
        else:
            migration = await db.get_active_migration()
            if not migration:
                print("\n📭 No active migration found")
                print("\nTo start a new migration, use the photo-migration MCP tool")
                return True
        
        # Display migration info
        print(f"\n📋 Migration ID: {migration['migration_id']}")
        print(f"👤 User: {migration['user_name']} ({migration['user_email']})")
        print(f"📱 Devices: {migration['source_device']} → {migration['target_device']}")
        print(f"📅 Started: {migration['started_at']}")
        print(f"🔄 Status: {migration['status'].upper()}")
        
        if migration['completed_at']:
            print(f"✅ Completed: {migration['completed_at']}")
        
        # Get family members
        family_members = await db.get_family_members(migration['migration_id'])
        if family_members:
            print(f"\n👨‍👩‍👧‍👦 Family Members ({len(family_members)}):")
            for member in family_members:
                print(f"  - {member['name']} ({member['role']})")
                if member['apple_id']:
                    print(f"    Apple ID: {member['apple_id']}")
                if member['google_account']:
                    print(f"    Google: {member['google_account']}")
        
        # Get tool status
        tool_status = await db.get_tool_status(migration['migration_id'])
        
        # Photo migration status
        if 'photo_migration' in tool_status:
            photo = tool_status['photo_migration']
            print(f"\n📸 Photo Migration:")
            print(f"  Status: {photo['status']}")
            print(f"  Transfer ID: {photo['transfer_id']}")
            print(f"  Photos: {photo['source_photos']:,}")
            print(f"  Videos: {photo['source_videos']:,}")
            print(f"  Size: {photo['source_size_gb']:.1f} GB")
            
            # Get latest progress
            progress_history = await db.get_photo_progress_history(photo['transfer_id'])
            if progress_history:
                latest = progress_history[-1]
                transferred = latest['transferred_items']
                total = photo['source_photos'] + photo['source_videos']
                percentage = (transferred / total * 100) if total > 0 else 0
                print(f"  Progress: {transferred:,}/{total:,} ({percentage:.1f}%)")
                print(f"  Last checked: {latest['checked_at']}")
        else:
            print(f"\n📸 Photo Migration: Not started")
        
        # Future: WhatsApp status
        if 'whatsapp' in tool_status:
            print(f"\n💬 WhatsApp Migration: {tool_status['whatsapp'].get('status', 'Not started')}")
        else:
            print(f"\n💬 WhatsApp Migration: Not started")
        
        # Future: Family services status
        if 'family_services' in tool_status:
            print(f"\n👨‍👩‍👧‍👦 Family Services: {tool_status['family_services'].get('status', 'Not started')}")
        else:
            print(f"\n👨‍👩‍👧‍👦 Family Services: Not started")
        
        # Get recent events
        print(f"\n📊 Recent Activity:")
        timeline = await db.get_migration_timeline(migration['migration_id'])
        recent_events = timeline[-5:] if len(timeline) > 5 else timeline
        
        for event in recent_events:
            timestamp = event['timestamp'].strftime('%m/%d %H:%M')
            print(f"  [{timestamp}] {event['tool_name']}: {event['event_type']}")
            if event['details']:
                details = json.loads(event['details']) if isinstance(event['details'], str) else event['details']
                for key, value in details.items():
                    if key != 'transfer_id':  # Skip redundant info
                        print(f"    - {key}: {value}")
        
        # Database statistics
        stats = await db.get_database_stats()
        print(f"\n💾 Database Statistics:")
        print(f"  Total migrations: {stats['total_migrations']}")
        print(f"  Active migrations: {stats['active_migrations']}")
        print(f"  Total events: {stats['total_events']}")
        print(f"  Database size: {stats['database_size_mb']} MB")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error checking status: {e}")
        logger.error(f"Status check failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    # Check if migration ID was provided as argument
    migration_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    success = asyncio.run(main(migration_id))
    sys.exit(0 if success else 1)