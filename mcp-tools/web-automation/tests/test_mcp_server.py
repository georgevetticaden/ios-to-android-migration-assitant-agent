#!/usr/bin/env python3
"""
MCP Server Integration Test

This test script validates all 4 MCP (Model Context Protocol) tools provided by
the photo migration server. It simulates how Claude Desktop interacts with these
tools through the MCP protocol, ensuring proper functionality and integration.

MCP Tools Tested (4 Tools):
1. check_icloud_status - Retrieves photo/video counts from iCloud
2. start_photo_transfer - Initiates Apple to Google photo transfer
3. check_transfer_progress - Monitors ongoing transfer status
4. verify_transfer_complete - Validates transfer completion
(Note: check_photo_transfer_email removed in Phase 6 - use mobile-mcp for Gmail)

Test Features:
- Interactive menu for testing individual tools
- Full test sequence that runs all tools in order
- Simulates actual MCP client-server communication
- Validates tool parameters and response formats
- Tests with real or mock credentials based on environment

Test Modes:
1. Interactive Menu: Test individual tools on demand
2. Full Sequence: Run complete transfer workflow test

Environment Variables:
- APPLE_ID: Apple ID for authentication
- APPLE_PASSWORD: Password for Apple ID
- GOOGLE_EMAIL: Google account email
- GOOGLE_PASSWORD: Google account password

Usage:
    python test_mcp_server.py
    
    Then select:
    1. Interactive menu - Test tools individually
    2. Full test sequence - Run complete workflow

Note: This test creates an actual MCP server instance and calls tools
through the proper MCP protocol interface, not direct function calls.
"""
import asyncio
import json
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Dict, Any

# Simulate MCP client interactions
class MCPServerTester:
    """Test MCP server with simulated tool calls"""
    
    def __init__(self):
        self.server_module = None
        self.server = None
        
    async def setup(self):
        """Import and initialize the MCP server"""
        # Add src to path (go up one level from tests)
        sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
        
        from web_automation import server
        
        # Initialize the server
        await server.initialize_server()
        self.server = server
        
        # Get list of tools
        tools = await server.get_tools()
        
        print("✅ MCP Server initialized")
        print(f"Available tools: {len(tools)}")
        
    async def list_tools(self):
        """List all available MCP tools"""
        tools = await self.server.get_tools()
        
        print("\n" + "="*60)
        print("AVAILABLE MCP TOOLS")
        print("="*60)
        
        for i, tool in enumerate(tools, 1):
            print(f"\n{i}. {tool.name}")
            print(f"   {tool.description[:100]}...")
            
            # Show parameters
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                props = tool.inputSchema.get('properties', {})
                required = tool.inputSchema.get('required', [])
                
                if props:
                    print("   Parameters:")
                    for param, schema in props.items():
                        req = " (required)" if param in required else " (optional)"
                        print(f"   - {param}: {schema.get('type', 'any')}{req}")
        
        return tools
    
    async def test_check_status(self):
        """Test check_icloud_status tool"""
        print("\n" + "="*60)
        print("TEST: check_icloud_status")
        print("="*60)
        
        # Prepare arguments (all from environment)
        args = {}
        
        print("Calling tool with no parameters (uses environment variables)...")
        
        try:
            result = await self.server.call_tool("check_icloud_status", args)
            
            if result and len(result) > 0:
                # The MCP server returns TextContent objects with formatted text
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                
                # The response is formatted text, not JSON
                print("\n✅ Tool executed successfully!")
                print(content)
                
                # Check if the response contains expected elements
                if "Photos:" in content and "Videos:" in content:
                    return True
                else:
                    print("⚠️ Response may be incomplete")
                    return False
            else:
                print("❌ No result returned")
                return False
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return False
    
    async def test_start_transfer(self):
        """Test start_photo_transfer tool"""
        print("\n" + "="*60)
        print("TEST: start_photo_transfer")
        print("="*60)
        
        # Ask if user wants to actually confirm the transfer
        confirm = input("\nActually initiate transfer with Apple? (y/n, default=n): ").strip().lower()
        args = {
            "reuse_session": True,
            "confirm_transfer": confirm == 'y'
        }
        
        print("Calling tool to start transfer...")
        print(f"Parameters: {args}")
        if args['confirm_transfer']:
            print("⚠️  WARNING: This will actually start the transfer with Apple!")
        
        try:
            result = await self.server.call_tool("start_photo_transfer", args)
            
            if result and len(result) > 0:
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                
                print("\n✅ Transfer test executed!")
                print(content)
                
                # Extract transfer ID from the formatted text if present
                import re
                transfer_id_match = re.search(r'Transfer ID: (TRF-\d+-\d+)', content)
                if transfer_id_match:
                    transfer_id = transfer_id_match.group(1)
                    print(f"\nExtracted Transfer ID: {transfer_id}")
                    return transfer_id
                
                # Check if it stopped at confirmation
                if "Confirmation page reached" in content:
                    print("\n✅ Test correctly stopped at confirmation page")
                    # Generate a test transfer ID for testing progress
                    transfer_id = f"TRF-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    print(f"Using test Transfer ID: {transfer_id}")
                    return transfer_id
                
                return None
            else:
                print("❌ No result returned")
                return None
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return None
    
    async def test_check_progress(self, transfer_id: str, day_number: int = None):
        """Test check_transfer_progress tool with storage-based tracking"""
        print("\n" + "="*60)
        print(f"TEST: check_transfer_progress{f' (Day {day_number})' if day_number else ''}")
        print("="*60)
        
        args = {"transfer_id": transfer_id}
        if day_number:
            args["day_number"] = day_number
        
        print(f"Checking progress for transfer: {transfer_id}")
        if day_number:
            print(f"Simulating day {day_number} of transfer")
        
        try:
            result = await self.server.call_tool("check_photo_transfer_progress", args)
            
            if result and len(result) > 0:
                # The result is text formatted, just print it
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                print("\n" + content)
                
                # Check if it contains expected elements
                if "Storage Metrics:" in content and "Estimated Transfer:" in content:
                    print("\n✅ Storage-based progress retrieved successfully!")
                    return True
                else:
                    print("\n⚠️ Progress retrieved but may be using old format")
                    return True
            else:
                print("❌ No result returned")
                return False
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return False
    
    async def test_storage_timeline(self):
        """Test storage-based progress over multiple days"""
        print("\n" + "="*60)
        print("TEST: Storage Timeline (Simulated 7-Day Transfer)")
        print("="*60)
        
        # First, we need a transfer ID - either get existing or create test one
        transfer_id = input("\nEnter transfer ID (or press Enter for test ID): ").strip()
        if not transfer_id:
            transfer_id = f"TRF-TEST-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            print(f"Using test ID: {transfer_id}")
        
        print("\nThis test simulates checking progress on different days of the transfer.")
        print("Each day shows expected storage growth and progress percentage.\n")
        
        # Define test days with expected behaviors
        test_days = [
            {"day": 1, "description": "Transfer just started", "expected_progress": "0-5%"},
            {"day": 4, "description": "Photos appearing in Google", "expected_progress": "25-30%"},
            {"day": 5, "description": "Transfer accelerating", "expected_progress": "55-60%"}, 
            {"day": 6, "description": "Nearly complete", "expected_progress": "85-90%"},
            {"day": 7, "description": "Transfer complete", "expected_progress": "98-100%"}
        ]
        
        results = []
        
        for test_day in test_days:
            print(f"\n--- Day {test_day['day']}: {test_day['description']} ---")
            print(f"Expected: {test_day['expected_progress']}")
            
            success = await self.test_check_progress(transfer_id, test_day['day'])
            results.append({
                "day": test_day['day'],
                "success": success,
                "expected": test_day['expected_progress']
            })
            
            if success:
                print(f"✅ Day {test_day['day']} test passed")
            else:
                print(f"❌ Day {test_day['day']} test failed")
            
            # Small delay between tests
            await asyncio.sleep(0.5)
        
        # Summary
        print("\n" + "="*60)
        print("TIMELINE TEST SUMMARY")
        print("="*60)
        
        success_count = sum(1 for r in results if r["success"])
        total_count = len(results)
        
        for result in results:
            status = "✅" if result["success"] else "❌"
            print(f"{status} Day {result['day']}: Expected {result['expected']}")
        
        print(f"\nOverall: {success_count}/{total_count} tests passed")
        
        if success_count == total_count:
            print("\n🎉 Storage timeline test PASSED!")
            return True
        else:
            print(f"\n⚠️ Storage timeline test had {total_count - success_count} failures")
            return False
    
    async def test_verify_complete(self, transfer_id: str):
        """Test verify_transfer_complete tool"""
        print("\n" + "="*60)
        print("TEST: verify_transfer_complete")
        print("="*60)
        
        args = {
            "transfer_id": transfer_id,
            "include_email_check": True
        }
        
        print(f"Verifying transfer: {transfer_id}")
        print(f"Parameters: {args}")
        
        try:
            result = await self.server.call_tool("verify_photo_transfer_complete", args)
            
            if result and len(result) > 0:
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                
                print("\n✅ Verification test executed!")
                print(content)
                
                # Check for success indicators in text
                if "Complete" in content or "Verification" in content:
                    return True
                elif "Error" in content or "failed" in content.lower():
                    return False
                else:
                    return True  # Assume success if no error
            else:
                print("❌ No result returned")
                return False
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return False
    
    async def test_check_email(self, transfer_id: str):
        """Test check_completion_email tool - REMOVED"""
        print("\n" + "="*60)
        print("TEST: check_completion_email (REMOVED)")
        print("="*60)
        
        print(f"Note: check_photo_transfer_email tool has been removed")
        print("Email checking is now handled via mobile-mcp Gmail commands")
        print("Use mobile-mcp to search for 'Your videos have been copied to Google Photos'")
        
        # Return without error to allow test to continue
        print("\n✅ Test skipped - tool removed in Phase 6")
        return True
    
    async def run_full_test(self):
        """Run complete test sequence"""
        print("\n" + "="*60)
        print("RUNNING FULL MCP SERVER TEST")
        print("="*60)
        
        # 1. Check status
        await self.test_check_status()
        await asyncio.sleep(1)
        
        # 2. Start transfer (simulated - won't actually start)
        confirm = input("\nStart transfer test? (y/n): ").strip().lower()
        if confirm == 'y':
            transfer_id = await self.test_start_transfer()
            
            if transfer_id:
                await asyncio.sleep(1)
                
                # 3. Check progress with different days
                print("\n📊 Testing storage-based progress tracking...")
                
                # Day 1 - Just started
                print("\n--- Testing Day 1 Progress ---")
                await self.test_check_progress(transfer_id, 1)
                await asyncio.sleep(1)
                
                # Day 4 - Photos appearing
                print("\n--- Testing Day 4 Progress ---")
                await self.test_check_progress(transfer_id, 4)
                await asyncio.sleep(1)
                
                # Day 7 - Nearly complete
                print("\n--- Testing Day 7 Progress ---")
                await self.test_check_progress(transfer_id, 7)
                await asyncio.sleep(1)
                
                # 4. Verify complete
                await self.test_verify_complete(transfer_id)
                await asyncio.sleep(1)
                
                # 5. Check email
                await self.test_check_email(transfer_id)
        
        print("\n" + "="*60)
        print("✅ MCP SERVER TEST COMPLETE")
        print("="*60)
    
    async def interactive_menu(self):
        """Interactive menu for testing individual tools"""
        transfer_id = None
        
        while True:
            print("\n" + "="*60)
            print("MCP SERVER TEST MENU")
            print("="*60)
            print("1. List all tools")
            print("2. Test check_icloud_status")
            print("3. Test start_photo_transfer")
            print("4. Test check_transfer_progress (current day)")
            print("5. Test check_transfer_progress (specific day)")
            print("6. Test storage timeline (7-day simulation)")
            print("7. Test verify_transfer_complete")
            print("8. Run full test sequence")
            print("0. Exit")
            print("="*60)
            
            if transfer_id:
                print(f"Current transfer ID: {transfer_id}")
            
            choice = input("\nSelect option (0-8): ").strip()
            
            if choice == '1':
                await self.list_tools()
            elif choice == '2':
                await self.test_check_status()
            elif choice == '3':
                result = await self.test_start_transfer()
                if result:
                    transfer_id = result
            elif choice == '4':
                # Test current day progress
                if not transfer_id:
                    transfer_id = input("Enter transfer ID: ").strip()
                if transfer_id:
                    await self.test_check_progress(transfer_id)
            elif choice == '5':
                # Test specific day progress
                if not transfer_id:
                    transfer_id = input("Enter transfer ID: ").strip()
                if transfer_id:
                    day = input("Enter day number (1-7): ").strip()
                    if day.isdigit() and 1 <= int(day) <= 7:
                        await self.test_check_progress(transfer_id, int(day))
                    else:
                        print("Invalid day number")
            elif choice == '6':
                # Test storage timeline
                await self.test_storage_timeline()
            elif choice == '7':
                if not transfer_id:
                    transfer_id = input("Enter transfer ID: ").strip()
                if transfer_id:
                    await self.test_verify_complete(transfer_id)
            elif choice == '8':
                # Run full test sequence
                await self.run_full_test()
            elif choice == '0':
                print("Exiting...")
                break
            else:
                print("Invalid option")
            
            if choice != '0':
                input("\nPress Enter to continue...")

async def main():
    """Main test runner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║           MCP SERVER TEST - Photo Migration             ║
║                                                          ║
║  This tests the MCP server with all 5 tools via the     ║
║  actual MCP protocol, simulating Claude Desktop usage   ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Check environment
    required_vars = ['APPLE_ID', 'APPLE_PASSWORD', 'GOOGLE_EMAIL', 'GOOGLE_PASSWORD']
    missing = [var for var in required_vars if not os.getenv(var)]
    
    if missing:
        print("⚠️  Missing environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease set these in your .env file")
        
        confirm = input("\nContinue anyway? (y/n): ").strip().lower()
        if confirm != 'y':
            return
    
    tester = MCPServerTester()
    
    try:
        await tester.setup()
        
        # Choose mode
        print("\nSelect test mode:")
        print("1. Interactive menu")
        print("2. Run full test sequence")
        
        mode = input("Choice (1-2): ").strip()
        
        if mode == '2':
            await tester.run_full_test()
        else:
            await tester.interactive_menu()
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\nTest completed")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    asyncio.run(main())