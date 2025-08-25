#!/usr/bin/env python3
"""
Test script for migration-state MCP server
Tests compatibility with the new database schema
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared.database.migration_db import MigrationDatabase

async def test_server_compatibility():
    """Test that server.py methods work with new database"""
    
    print("=" * 60)
    print("Testing migration-state server compatibility")
    print("=" * 60)
    
    db = MigrationDatabase()
    test_results = []
    
    # Test 1: Initialize schemas
    print("\nTest 1: Initialize schemas...")
    try:
        await db.initialize_schemas()
        print("✅ PASS: Schema initialization")
        test_results.append(("initialize_schemas", True))
    except Exception as e:
        print(f"❌ FAIL: Schema initialization - {e}")
        test_results.append(("initialize_schemas", False))
    
    # Test 2: Create a test migration
    print("\nTest 2: Create migration...")
    try:
        migration_id = await db.create_migration(
            user_name="Test User",
            source_device="iPhone 15",
            target_device="Galaxy Z Fold 7",
            photo_count=5000,
            video_count=200,
            storage_gb=50.5
        )
        print(f"✅ PASS: Created migration {migration_id}")
        test_results.append(("create_migration", True))
    except Exception as e:
        print(f"❌ FAIL: Create migration - {e}")
        test_results.append(("create_migration", False))
        migration_id = None
    
    # Test 3: Get active migration (method used by server.py)
    print("\nTest 3: Get active migration...")
    try:
        active = await db.get_active_migration()
        if active:
            print(f"✅ PASS: Got active migration: {active['id']}")
            # Verify structure matches what server.py expects
            required_fields = ['id', 'user_name', 'current_phase', 'overall_progress']
            missing = [f for f in required_fields if f not in active]
            if missing:
                print(f"  ⚠️  Warning: Missing fields: {missing}")
        else:
            print("✅ PASS: No active migration (expected)")
        test_results.append(("get_active_migration", True))
    except Exception as e:
        print(f"❌ FAIL: Get active migration - {e}")
        test_results.append(("get_active_migration", False))
    
    # Test 4: Get migration status (method used by server.py)
    if migration_id:
        print("\nTest 4: Get migration status...")
        try:
            status = await db.get_migration_status(migration_id)
            if status:
                print(f"✅ PASS: Got migration status")
                print(f"  - ID: {status['id']}")
                print(f"  - Phase: {status['current_phase']}")
                print(f"  - Progress: {status['overall_progress']}%")
            test_results.append(("get_migration_status", True))
        except Exception as e:
            print(f"❌ FAIL: Get migration status - {e}")
            test_results.append(("get_migration_status", False))
    
    # Test 5: Update migration progress (method used by server.py)
    if migration_id:
        print("\nTest 5: Update migration progress...")
        try:
            await db.update_migration_progress(
                migration_id=migration_id,
                status="photo_transfer",  # Changed from "in_progress" to valid phase
                photos_transferred=1000,
                videos_transferred=50,
                total_size_gb=10.0
            )
            print("✅ PASS: Updated migration progress")
            test_results.append(("update_migration_progress", True))
        except Exception as e:
            print(f"❌ FAIL: Update migration progress - {e}")
            test_results.append(("update_migration_progress", False))
    
    # Test 6: Get pending items (method used by server.py)
    print("\nTest 6: Get pending items...")
    try:
        items = await db.get_pending_items("photos")
        print(f"✅ PASS: Got pending items: {len(items)} items")
        if items:
            print(f"  - First item: {items[0]}")
        test_results.append(("get_pending_items", True))
    except Exception as e:
        print(f"❌ FAIL: Get pending items - {e}")
        test_results.append(("get_pending_items", False))
    
    # Test 7: Mark item complete (method used by server.py)
    print("\nTest 7: Mark item complete...")
    try:
        result = await db.mark_item_complete(
            item_type="photos",
            item_id="test-item-001",
            details={"test": "data"}
        )
        print(f"✅ PASS: Marked item complete: {result}")
        test_results.append(("mark_item_complete", True))
    except Exception as e:
        print(f"❌ FAIL: Mark item complete - {e}")
        test_results.append(("mark_item_complete", False))
    
    # Test 8: Get statistics (method used by server.py)
    print("\nTest 8: Get migration statistics...")
    try:
        stats = await db.get_migration_statistics(include_history=False)
        print(f"✅ PASS: Got statistics")
        print(f"  - Total migrations: {stats['total_migrations']}")
        print(f"  - Completed: {stats['completed_migrations']}")
        if stats['active_migration']:
            print(f"  - Active: {stats['active_migration']['id']}")
        test_results.append(("get_migration_statistics", True))
    except Exception as e:
        print(f"❌ FAIL: Get migration statistics - {e}")
        test_results.append(("get_migration_statistics", False))
    
    # Test 9: Log event (method used by server.py)
    print("\nTest 9: Log migration event...")
    try:
        result = await db.log_event(
            event_type="test_event",
            component="test_server",
            description="Testing server compatibility",
            metadata={"test": "data"}
        )
        print(f"✅ PASS: Logged event: {result}")
        test_results.append(("log_event", True))
    except Exception as e:
        print(f"❌ FAIL: Log event - {e}")
        test_results.append(("log_event", False))
    
    # Test 10: Add family members
    if migration_id:
        print("\nTest 10: Add family members...")
        try:
            member_id = await db.add_family_member(
                migration_id=migration_id,
                name="Test Spouse",
                email="spouse@test.com",
                role="spouse",
                age=35
            )
            print(f"✅ PASS: Added family member with ID: {member_id}")
            test_results.append(("add_family_member", True))
        except Exception as e:
            print(f"❌ FAIL: Add family member - {e}")
            test_results.append(("add_family_member", False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in test_results if result)
    failed = sum(1 for _, result in test_results if not result)
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n✅ ALL TESTS PASSED - Server is compatible with new database!")
    else:
        print("\n❌ Some tests failed - Review the errors above")
        print("\nFailed tests:")
        for test_name, result in test_results:
            if not result:
                print(f"  - {test_name}")
    
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(test_server_compatibility())
    sys.exit(0 if success else 1)