#!/usr/bin/env python3
"""Quick test to verify the fixes work"""

import asyncio
import sys
import json
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "shared"))

import server as mcp_server

async def test_fixes():
    print("Testing fixes for the 3 failing tools...")
    
    # Initialize database
    await mcp_server.db.initialize_schemas()
    
    # Get active migration
    active = await mcp_server.db.get_active_migration()
    if active:
        migration_id = active["id"]
        print(f"\n✓ Found migration: {migration_id}")
        
        # Test 1: get_family_members (was failing with GROUP BY error)
        print("\n1. Testing get_family_members...")
        result = await mcp_server.call_tool("get_family_members", {"filter": "all"})
        response = json.loads(result[0].text)
        if "error" in response:
            print(f"   ❌ FAILED: {response['error']}")
        else:
            print(f"   ✅ SUCCESS: Found {response.get('count', 0)} members")
        
        # Test 2: get_migration_status (was failing with dictionary error)
        print("\n2. Testing get_migration_status...")
        result = await mcp_server.call_tool("get_migration_status", {"day_number": 2})
        response = json.loads(result[0].text)
        if "error" in response:
            print(f"   ❌ FAILED: {response['error']}")
        else:
            print(f"   ✅ SUCCESS: Got status for day 2")
        
        # Mark migration as completed for test 3
        with mcp_server.db.get_connection() as conn:
            conn.execute(f"UPDATE migration_status SET completed_at = CURRENT_TIMESTAMP WHERE id = '{migration_id}'")
            conn.commit()
        
        # Test 3: generate_migration_report (was failing with "No active migration")
        print("\n3. Testing generate_migration_report (after marking complete)...")
        result = await mcp_server.call_tool("generate_migration_report", {"format": "summary"})
        response = json.loads(result[0].text)
        if "error" in response or "status" in response and response["status"] == "error":
            print(f"   ❌ FAILED: {response.get('error', response.get('message'))}")
        else:
            print(f"   ✅ SUCCESS: Report generated")
    else:
        print("No active migration found. Run test_mcp_server.py first to create test data.")

if __name__ == "__main__":
    asyncio.run(test_fixes())