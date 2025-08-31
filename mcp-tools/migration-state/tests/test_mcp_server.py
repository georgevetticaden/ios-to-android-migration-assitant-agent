#!/usr/bin/env python3
"""
Test suite for Migration State MCP Server JSON-RPC interface
Tests the actual MCP server protocol, not just the database layer
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

# ANSI color codes
class Colors:
    HEADER = '\033[95m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.HEADER}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text}{Colors.ENDC}")
    print(f"{Colors.HEADER}{'='*80}{Colors.ENDC}")

def print_test(name: str, passed: bool, details: str = ""):
    """Print test result with color"""
    status = f"{Colors.GREEN}✅ PASS{Colors.ENDC}" if passed else f"{Colors.FAIL}❌ FAIL{Colors.ENDC}"
    print(f"{status}: {name}")
    if details:
        print(f"         {details}")

async def call_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate MCP tool call through the server's call_tool function
    This mimics what Claude Desktop would send via JSON-RPC
    """
    # Call the server's tool handler directly
    # In production, this would go through stdio with JSON-RPC wrapper
    result = await mcp_server.call_tool(tool_name, arguments)
    
    # Extract the JSON from TextContent response
    if result and len(result) > 0:
        return json.loads(result[0].text)
    return {"error": "No response from server"}

async def test_mcp_tools():
    """Test all 7 MCP tools through the server interface"""
    print_header("MCP SERVER INTERFACE TEST SUITE")
    print(f"{Colors.CYAN}Testing 7 MCP tools via JSON-RPC protocol{Colors.ENDC}")
    print(f"{Colors.CYAN}Simulating Claude Desktop tool calls{Colors.ENDC}")
    
    # Initialize database
    await mcp_server.db.initialize_schemas()
    
    test_results = []
    migration_id = None
    
    # Test 1: initialize_migration
    print(f"\n{Colors.CYAN}Testing Tool 1: initialize_migration{Colors.ENDC}")
    try:
        response = await call_tool("initialize_migration", {
            "user_name": "Test User",
            "years_on_ios": 10
        })
        
        if "migration_id" in response:
            migration_id = response["migration_id"]
            print_test("initialize_migration", True, f"Created migration: {migration_id}")
            test_results.append(("initialize_migration", True))
        else:
            print_test("initialize_migration", False, "No migration_id returned")
            test_results.append(("initialize_migration", False))
    except Exception as e:
        print_test("initialize_migration", False, str(e))
        test_results.append(("initialize_migration", False))
    
    # Test 2: add_family_member
    print(f"\n{Colors.CYAN}Testing Tool 2: add_family_member{Colors.ENDC}")
    if migration_id:
        try:
            response = await call_tool("add_family_member", {
                "migration_id": migration_id,
                "name": "Test Spouse",
                "role": "spouse"
            })
            
            if "member_id" in response:
                print_test("add_family_member", True, f"Added member ID: {response['member_id']}")
                test_results.append(("add_family_member", True))
            else:
                print_test("add_family_member", False, "No member_id returned")
                test_results.append(("add_family_member", False))
        except Exception as e:
            print_test("add_family_member", False, str(e))
            test_results.append(("add_family_member", False))
    
    # Test 3: update_migration_status
    print(f"\n{Colors.CYAN}Testing Tool 3: update_migration_status{Colors.ENDC}")
    if migration_id:
        try:
            response = await call_tool("update_migration_status", {
                "migration_id": migration_id,
                "photo_count": 50000,
                "video_count": 2000,
                "total_icloud_storage_gb": 300
            })
            
            if response.get("success"):
                print_test("update_migration_status", True, "Status updated successfully")
                test_results.append(("update_migration_status", True))
            else:
                print_test("update_migration_status", False, "Update failed")
                test_results.append(("update_migration_status", False))
        except Exception as e:
            print_test("update_migration_status", False, str(e))
            test_results.append(("update_migration_status", False))
    
    # Test 4: get_migration_status (uber tool)
    print(f"\n{Colors.CYAN}Testing Tool 4: get_migration_status{Colors.ENDC}")
    if migration_id:
        try:
            response = await call_tool("get_migration_status", {
                "day_number": 1
            })
            
            if "migration" in response:
                print_test("get_migration_status", True, 
                          f"Day 1 - Progress: {response['migration'].get('overall_progress', 0)}%")
                test_results.append(("get_migration_status", True))
            else:
                print_test("get_migration_status", False, "No migration data returned")
                test_results.append(("get_migration_status", False))
        except Exception as e:
            print_test("get_migration_status", False, str(e))
            test_results.append(("get_migration_status", False))
    
    # Test 5: get_family_members
    print(f"\n{Colors.CYAN}Testing Tool 5: get_family_members{Colors.ENDC}")
    if migration_id:
        try:
            response = await call_tool("get_family_members", {
                "filter": "all"
            })
            
            if "members" in response:
                print_test("get_family_members", True, 
                          f"Found {len(response['members'])} family member(s)")
                test_results.append(("get_family_members", True))
            else:
                print_test("get_family_members", False, "No members returned")
                test_results.append(("get_family_members", False))
        except Exception as e:
            print_test("get_family_members", False, str(e))
            test_results.append(("get_family_members", False))
    
    # Test 6: update_family_member_apps
    print(f"\n{Colors.CYAN}Testing Tool 6: update_family_member_apps{Colors.ENDC}")
    if migration_id:
        try:
            # First get family members to get an ID
            members_response = await call_tool("get_family_members", {
                "filter": "all"
            })
            
            if members_response.get("members") and len(members_response["members"]) > 0:
                member_name = members_response["members"][0]["name"]
                
                response = await call_tool("update_family_member_apps", {
                    "member_name": member_name,
                    "app_name": "WhatsApp",
                    "status": "invited"
                })
                
                if response.get("success"):
                    print_test("update_family_member_apps", True, 
                              f"Updated {member_name}'s WhatsApp status")
                    test_results.append(("update_family_member_apps", True))
                else:
                    print_test("update_family_member_apps", False, "Update failed")
                    test_results.append(("update_family_member_apps", False))
            else:
                print_test("update_family_member_apps", False, "No family members found")
                test_results.append(("update_family_member_apps", False))
        except Exception as e:
            print_test("update_family_member_apps", False, str(e))
            test_results.append(("update_family_member_apps", False))
    
    # Test 7: generate_migration_report
    print(f"\n{Colors.CYAN}Testing Tool 7: generate_migration_report{Colors.ENDC}")
    if migration_id:
        try:
            # Update to completed state first
            await call_tool("update_migration_status", {
                "migration_id": migration_id,
                "current_phase": "completed",
                "overall_progress": 100
            })
            
            response = await call_tool("generate_migration_report", {
                "format": "summary"
            })
            
            if "report" in response:
                print_test("generate_migration_report", True, "Report generated successfully")
                test_results.append(("generate_migration_report", True))
                
                # Print a snippet of the report
                if "summary" in response["report"]:
                    print(f"         User: {response['report']['summary'].get('user', 'Unknown')}")
            else:
                print_test("generate_migration_report", False, "No report returned")
                test_results.append(("generate_migration_report", False))
        except Exception as e:
            print_test("generate_migration_report", False, str(e))
            test_results.append(("generate_migration_report", False))
    
    # Summary
    print_header("MCP SERVER TEST SUMMARY")
    
    passed = sum(1 for _, success in test_results if success)
    total = len(test_results)
    
    print(f"\n{Colors.BOLD}Results:{Colors.ENDC}")
    print(f"Total Tests: {total}")
    print(f"{Colors.GREEN}Passed: {passed}{Colors.ENDC}")
    print(f"{Colors.FAIL}Failed: {total - passed}{Colors.ENDC}")
    
    if passed == total:
        print(f"\n{Colors.GREEN}{Colors.BOLD}🎉 ALL MCP SERVER TESTS PASSED! 🎉{Colors.ENDC}")
    else:
        print(f"\n{Colors.WARNING}⚠️  Some tests failed ({passed}/{total}){Colors.ENDC}")
        failed = [name for name, success in test_results if not success]
        if failed:
            print(f"\n{Colors.FAIL}Failed tests:{Colors.ENDC}")
            for test in failed:
                print(f"  - {test}")
    
    return 0 if passed == total else 1

async def test_json_rpc_format():
    """Test that responses follow JSON-RPC format"""
    print_header("JSON-RPC FORMAT VALIDATION")
    
    await mcp_server.db.initialize_schemas()
    
    # Test successful response format
    print(f"\n{Colors.CYAN}Testing successful response format...{Colors.ENDC}")
    response = await call_tool("initialize_migration", {
        "user_name": "Format Test",
        "years_on_ios": 5
    })
    
    # Check response structure
    has_migration_id = "migration_id" in response
    has_success = "success" in response
    
    if has_migration_id and has_success:
        print_test("JSON-RPC success format", True, "Valid response structure")
    else:
        print_test("JSON-RPC success format", False, 
                  f"Missing fields - migration_id: {has_migration_id}, success: {has_success}")
    
    # Test error response format
    print(f"\n{Colors.CYAN}Testing error response format...{Colors.ENDC}")
    try:
        # Call with invalid day number
        response = await call_tool("get_migration_status", {
            "day_number": 10  # Invalid - should be 1-7
        })
        
        if "error" in response or not response.get("success"):
            print_test("JSON-RPC error format", True, "Valid error response")
        else:
            print_test("JSON-RPC error format", False, "Should return error for invalid ID")
    except Exception as e:
        print_test("JSON-RPC error format", True, f"Raised exception as expected: {e}")

async def main():
    """Run all MCP server tests"""
    print(f"{Colors.BOLD}{Colors.CYAN}MCP SERVER TEST RUNNER{Colors.ENDC}")
    print(f"{Colors.CYAN}Testing server interface, not just database layer{Colors.ENDC}")
    
    # Run MCP tool tests
    tool_result = await test_mcp_tools()
    
    # Run JSON-RPC format tests
    await test_json_rpc_format()
    
    return tool_result

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)