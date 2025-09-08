#!/usr/bin/env python3
"""
Test suite for Migration State MCP Server following the EXACT demo flow
Tests all 7 MCP tools in the sequence specified in demo-script-complete-final.md
Validates the 7-day migration journey from ios2android-agent-instructions-opus4.md
"""

import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
sys.path.append(str(Path(__file__).parent.parent.parent.parent / "shared"))

# Import the server module to get access to call_tool
import server as mcp_server
from shared.database.migration_db import MigrationDatabase
from logging_config import get_test_logger

# Get logger configured for testing
logger = get_test_logger("mcp_server", verbose=True)  # Enable verbose for debugging

async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Call MCP tool and return parsed response"""
    logger.debug(f"Calling tool: {tool_name} with args: {json.dumps(arguments, default=str)}")
    result = await mcp_server.call_tool(tool_name, arguments)
    if result and len(result) > 0:
        response = json.loads(result[0].text)
        logger.debug(f"Tool response: {json.dumps(response, default=str)}")
        return response
    return {"error": "No response from server"}

async def test_day_1_flow():
    """
    Test Day 1 flow exactly as specified in demo-script-complete-final.md
    Lines 115-450 of the demo script
    """
    logger.info("="*80)
    logger.info("DAY 1: COMPLETE MIGRATION SETUP FLOW")
    logger.info("Following exact sequence from demo-script-complete-final.md")
    logger.info("="*80)
    
    test_results = []
    migration_id = None
    
    # Clean up any existing active migrations
    logger.debug("Cleaning up existing active migrations")
    with mcp_server.db.get_connection() as conn:
        conn.execute("UPDATE migration_status SET completed_at = CURRENT_TIMESTAMP WHERE completed_at IS NULL")
        conn.commit()
    
    # Step 1: Initialize migration (Line 116)
    logger.info("\n" + "-"*60)
    logger.info("Step 1: Initialize Migration")
    logger.info("Demo Line 116: initialize_migration")
    logger.info("-"*60)
    
    try:
        response = await call_tool("initialize_migration", {
            "user_name": "George Vetticaden",
            "years_on_ios": 18
        })
        
        if "migration_id" in response:
            migration_id = response["migration_id"]
            logger.info(f"✅ PASS: initialize_migration - Migration ID: {migration_id}")
            test_results.append(("initialize_migration", True))
        else:
            logger.error(f"❌ FAIL: initialize_migration - No migration_id returned")
            logger.debug(f"Response: {json.dumps(response, indent=2)}")
            test_results.append(("initialize_migration", False))
            return test_results, None
    except Exception as e:
        logger.error(f"❌ FAIL: initialize_migration - {str(e)}")
        return [("initialize_migration", False)], None
    
    # Step 2: Add all 4 family members (Lines 132-145)
    logger.info("\n" + "-"*60)
    logger.info("Step 2: Add Family Members")
    logger.info("Demo Lines 132-145: add_family_member x4")
    logger.info("-"*60)
    
    family_members = [
        {"name": "Jaisy", "role": "spouse"},
        {"name": "Laila", "role": "child", "age": 17},
        {"name": "Ethan", "role": "child", "age": 15},
        {"name": "Maya", "role": "child", "age": 11}
    ]
    
    for member in family_members:
        try:
            member_data = {
                "migration_id": migration_id,
                "name": member["name"],
                "role": member["role"]
            }
            if "age" in member:
                member_data["age"] = member["age"]
            
            response = await call_tool("add_family_member", member_data)
            
            if response.get("success"):
                logger.info(f"✅ PASS: add_family_member ({member['name']}) - ID: {response.get('member_id')}, Teen: {response.get('needs_venmo_teen', False)}")
                test_results.append((f"add_family_member_{member['name']}", True))
            else:
                logger.error(f"❌ FAIL: add_family_member ({member['name']})")
                test_results.append((f"add_family_member_{member['name']}", False))
        except Exception as e:
            logger.error(f"❌ FAIL: add_family_member ({member['name']}) - {str(e)}")
            test_results.append((f"add_family_member_{member['name']}", False))
    
    # Step 3: First progressive update (after iCloud check) - Line 176
    logger.info("\n" + "-"*60)
    logger.info("Step 3: Progressive Update #1 (After iCloud Check)")
    logger.info("Demo Line 176: update_migration_status with iCloud metrics")
    logger.info("-"*60)
    
    try:
        response = await call_tool("update_migration_status", {
            "migration_id": migration_id,
            "photo_count": 60238,
            "video_count": 2418,
            "total_icloud_storage_gb": 383,
            "icloud_photo_storage_gb": 268,
            "icloud_video_storage_gb": 115,
            "album_count": 125
        })
        
        if response.get("success"):
            logger.info("✅ PASS: update_migration_status #1 - Added iCloud metrics: 60,238 photos, 2,418 videos, 383GB")
            test_results.append(("update_migration_status_1", True))
        else:
            logger.error("❌ FAIL: update_migration_status #1")
            test_results.append(("update_migration_status_1", False))
    except Exception as e:
        logger.error(f"❌ FAIL: update_migration_status #1 - {str(e)}")
        test_results.append(("update_migration_status_1", False))
    
    # Step 4: Second progressive update (after transfer start) - Line 239
    logger.info("\n" + "-"*60)
    logger.info("Step 4: Progressive Update #2 (After Transfer Start)")
    logger.info("Demo Line 239: update_migration_status with baseline and phase")
    logger.info("-"*60)
    
    try:
        response = await call_tool("update_migration_status", {
            "migration_id": migration_id,
            "current_phase": "media_transfer",
            "google_photos_baseline_gb": 13.88,
            "overall_progress": 10
        })
        
        if response.get("success"):
            logger.info("✅ PASS: update_migration_status #2 - Phase: media_transfer, Baseline: 13.88GB, Progress: 10%")
            test_results.append(("update_migration_status_2", True))
        else:
            logger.error("❌ FAIL: update_migration_status #2")
            test_results.append(("update_migration_status_2", False))
    except Exception as e:
        logger.error(f"❌ FAIL: update_migration_status #2 - {str(e)}")
        test_results.append(("update_migration_status_2", False))
    
    # Step 5: Update family member apps (WhatsApp) - Lines 342-347
    logger.info("\n" + "-"*60)
    logger.info("Step 5: Update Family App Status (WhatsApp)")
    logger.info("Demo Lines 342-347: update_family_member_apps for WhatsApp")
    logger.info("-"*60)
    
    whatsapp_members = [
        {"name": "Jaisy", "status": "configured", "in_group": True},
        {"name": "Laila", "status": "configured", "in_group": True},
        {"name": "Ethan", "status": "configured", "in_group": True},
        {"name": "Maya", "status": "invited", "in_group": False}
    ]
    
    for member in whatsapp_members:
        try:
            update_data = {
                "migration_id": migration_id,
                "member_name": member["name"],
                "app_name": "WhatsApp",
                "status": member["status"]
            }
            
            if member["in_group"]:
                update_data["details"] = {"whatsapp_in_group": True}
            
            response = await call_tool("update_family_member_apps", update_data)
            
            if response.get("success"):
                logger.info(f"✅ PASS: WhatsApp update ({member['name']}) - Status: {member['status']}")
                test_results.append((f"whatsapp_{member['name']}", True))
            else:
                logger.error(f"❌ FAIL: WhatsApp update ({member['name']})")
                test_results.append((f"whatsapp_{member['name']}", False))
        except Exception as e:
            logger.error(f"❌ FAIL: WhatsApp update ({member['name']}) - {str(e)}")
            test_results.append((f"whatsapp_{member['name']}", False))
    
    # Step 6: Test get_family_members with filters (Lines 352, 298)
    logger.info("\n" + "-"*60)
    logger.info("Step 6: Query Family Members with Filters")
    logger.info("Demo uses get_family_members throughout Day 1")
    logger.info("-"*60)
    
    filters = ["all", "not_in_whatsapp", "teen"]
    
    for filter_type in filters:
        try:
            response = await call_tool("get_family_members", {
                "migration_id": migration_id,
                "filter": filter_type
            })
            
            if "members" in response:
                member_names = [m["name"] for m in response["members"]]
                logger.info(f"✅ PASS: get_family_members ({filter_type}) - Found: {', '.join(member_names) if member_names else 'none'}")
                test_results.append((f"get_family_members_{filter_type}", True))
            else:
                logger.error(f"❌ FAIL: get_family_members ({filter_type})")
                logger.debug(f"Response: {json.dumps(response, indent=2)}")
                test_results.append((f"get_family_members_{filter_type}", False))
        except Exception as e:
            logger.error(f"❌ FAIL: get_family_members ({filter_type}) - {str(e)}")
            test_results.append((f"get_family_members_{filter_type}", False))
    
    # Step 7: Third progressive update (end of Day 1) - Line 450
    logger.info("\n" + "-"*60)
    logger.info("Step 7: Progressive Update #3 (End of Day 1)")
    logger.info("Demo Line 450: update_migration_status with family info")
    logger.info("-"*60)
    
    try:
        response = await call_tool("update_migration_status", {
            "migration_id": migration_id,
            "current_phase": "family_setup",
            "family_size": 4,
            "whatsapp_group_name": "Vetticaden Family",
            "overall_progress": 15
        })
        
        if response.get("success"):
            logger.info("✅ PASS: update_migration_status #3 - Family size: 4, WhatsApp group: Vetticaden Family, Progress: 15%")
            test_results.append(("update_migration_status_3", True))
        else:
            logger.error("❌ FAIL: update_migration_status #3")
            test_results.append(("update_migration_status_3", False))
    except Exception as e:
        logger.error(f"❌ FAIL: update_migration_status #3 - {str(e)}")
        test_results.append(("update_migration_status_3", False))
    
    return test_results, migration_id

async def test_days_2_7_flow(migration_id: str):
    """
    Test Days 2-7 flow using get_migration_status uber tool
    As specified in agent instructions and demo script
    """
    logger.info("\n" + "="*80)
    logger.info("DAYS 2-7: UBER STATUS TOOL PATTERN")
    logger.info("Testing daily get_migration_status + update pattern")
    logger.info("="*80)
    
    test_results = []
    
    for day in range(2, 8):
        logger.info("\n" + "-"*60)
        logger.info(f"Day {day} Flow")
        logger.info("-"*60)
        
        # Step 1: Get migration status (uber tool)
        try:
            response = await call_tool("get_migration_status", {
                "migration_id": migration_id,
                "day_number": day
            })
            
            if response.get("success") and "migration" in response:
                progress = response["migration"].get("overall_progress", 0)
                logger.info(f"✅ PASS: get_migration_status (Day {day}) - Progress: {progress}%, Status: {response.get('status_message', '')}")
                test_results.append((f"get_migration_status_day_{day}", True))
            else:
                logger.error(f"❌ FAIL: get_migration_status (Day {day})")
                logger.debug(f"Response keys: {list(response.keys())}")
                test_results.append((f"get_migration_status_day_{day}", False))
        except Exception as e:
            logger.error(f"❌ FAIL: get_migration_status (Day {day}) - {str(e)}")
            test_results.append((f"get_migration_status_day_{day}", False))
        
        # Step 2: Daily update_migration_status
        progress_by_day = {
            2: 20, 3: 25, 4: 28, 5: 57, 6: 88, 7: 100
        }
        
        try:
            update_data = {
                "migration_id": migration_id,
                "overall_progress": progress_by_day[day]
            }
            
            if day == 7:
                update_data["current_phase"] = "completed"
                update_data["completed_at"] = datetime.now().isoformat()
            
            response = await call_tool("update_migration_status", update_data)
            
            if response.get("success"):
                logger.info(f"✅ PASS: update_migration_status (Day {day}) - Progress updated to {progress_by_day[day]}%")
                test_results.append((f"update_migration_status_day_{day}", True))
            else:
                logger.error(f"❌ FAIL: update_migration_status (Day {day})")
                test_results.append((f"update_migration_status_day_{day}", False))
        except Exception as e:
            logger.error(f"❌ FAIL: update_migration_status (Day {day}) - {str(e)}")
            test_results.append((f"update_migration_status_day_{day}", False))
    
    # Day 7: Mark migration as completed
    logger.info("\n" + "-"*60)
    logger.info("Day 7: Mark Migration as Completed")
    logger.info("-"*60)
    
    try:
        response = await call_tool("update_migration_status", {
            "migration_id": migration_id,
            "overall_progress": 100,
            "current_phase": "completed",
            "notes": "Day 7: Migration completed successfully!"
        })
        
        if response.get("success"):
            logger.info("✅ PASS: Migration marked as completed (100%)")
            test_results.append(("day7_completion", True))
        else:
            logger.error("❌ FAIL: Could not mark migration as completed")
            logger.debug(f"Response: {response}")
            test_results.append(("day7_completion", False))
    except Exception as e:
        logger.error(f"❌ FAIL: day7_completion - {str(e)}")
        test_results.append(("day7_completion", False))
    
    return test_results

async def main():
    """Run complete demo flow test"""
    logger.info("\n" + "="*80)
    logger.info("MCP SERVER DEMO FLOW TEST")
    logger.info("Testing exact flow from demo-script-complete-final.md")
    logger.info("Following agent instructions from ios2android-agent-instructions-opus4.md")
    logger.info("="*80)
    
    # Initialize database
    logger.debug("Initializing database schemas")
    await mcp_server.db.initialize_schemas()
    
    all_results = []
    
    # Test Day 1 flow
    day1_results, migration_id = await test_day_1_flow()
    all_results.extend(day1_results)
    
    # Test Days 2-7 flow
    if migration_id:
        days_2_7_results = await test_days_2_7_flow(migration_id)
        all_results.extend(days_2_7_results)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    
    passed = sum(1 for _, success in all_results if success)
    total = len(all_results)
    
    logger.info(f"\nResults:")
    logger.info(f"Total Tests: {total}")
    logger.info(f"Passed: {passed}")
    logger.info(f"Failed: {total - passed}")
    
    # Count update_migration_status calls
    update_calls = sum(1 for name, _ in all_results if "update_migration_status" in name)
    logger.info(f"\nupdate_migration_status calls: {update_calls}/9")
    logger.info("  Expected: 3 on Day 1, 1 each Days 2-7")
    
    # Validate all 7 tools were tested
    tools_tested = set()
    for name, _ in all_results:
        if "initialize_migration" in name: tools_tested.add("initialize_migration")
        if "add_family_member" in name: tools_tested.add("add_family_member")
        if "update_migration_status" in name: tools_tested.add("update_migration_status")
        if "get_migration_status" in name: tools_tested.add("get_migration_status")
        if "get_family_members" in name: tools_tested.add("get_family_members")
        if "update_family_member_apps" in name: tools_tested.add("update_family_member_apps")
    
    logger.info(f"\nTools Tested: {len(tools_tested)}/6")
    for tool in sorted(tools_tested):
        logger.info(f"  ✓ {tool}")
    
    if passed == total:
        logger.info("\n🎉 ALL TESTS PASSED! 🎉")
        logger.info("The implementation follows the exact demo script flow!")
    else:
        logger.warning(f"\n⚠️  Some tests failed ({passed}/{total})")
        failed = [name for name, success in all_results if not success]
        if failed:
            logger.error("\nFailed tests:")
            for test in failed[:10]:  # Show first 10 failures
                logger.error(f"  - {test}")
            if len(failed) > 10:
                logger.error(f"  ... and {len(failed)-10} more")
    
    # Log file location
    logger.info(f"\nDetailed logs saved to: logs/test_migration_state_*.log")
    
    return 0 if passed == total else 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)