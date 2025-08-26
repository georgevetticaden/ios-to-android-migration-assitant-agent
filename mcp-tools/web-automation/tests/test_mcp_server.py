#!/usr/bin/env python3
"""
MCP Server Integration Test

This test script validates all 5 MCP (Model Context Protocol) tools provided by
the photo migration server. It simulates how Claude Desktop interacts with these
tools through the MCP protocol, ensuring proper functionality and integration.

MCP Tools Tested:
1. check_icloud_status - Retrieves photo/video counts from iCloud
2. start_photo_transfer - Initiates Apple to Google photo transfer
3. check_transfer_progress - Monitors ongoing transfer status
4. verify_transfer_complete - Validates transfer completion
5. check_completion_email - Checks for Apple confirmation emails

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
        # Add src to path
        sys.path.insert(0, str(Path(__file__).parent / 'src'))
        
        from web_automation.server import PhotoMigrationServer
        
        # Create server instance
        self.server = PhotoMigrationServer()
        await self.server.run()  # This starts the internal client
        
        print("✅ MCP Server initialized")
        print(f"Available tools: {len(self.server.list_tools())}")
        
    def list_tools(self):
        """List all available MCP tools"""
        tools = self.server.list_tools()
        
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
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                data = json.loads(content) if isinstance(content, str) else content
                
                print("\n✅ Tool executed successfully!")
                print(f"Photos: {data.get('photos', 'N/A')}")
                print(f"Videos: {data.get('videos', 'N/A')}")
                print(f"Storage: {data.get('storage_gb', 'N/A')} GB")
                print(f"Status: {data.get('status', 'N/A')}")
                
                return True
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
        
        args = {"reuse_session": True}
        
        print("Calling tool to start transfer...")
        print(f"Parameters: {args}")
        
        try:
            result = await self.server.call_tool("start_photo_transfer", args)
            
            if result and len(result) > 0:
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                data = json.loads(content) if isinstance(content, str) else content
                
                print("\n✅ Transfer initiated!")
                print(f"Transfer ID: {data.get('transfer_id', 'N/A')}")
                print(f"Status: {data.get('status', 'N/A')}")
                
                if 'source_counts' in data:
                    print(f"Source photos: {data['source_counts'].get('photos', 0):,}")
                    print(f"Source videos: {data['source_counts'].get('videos', 0):,}")
                
                return data.get('transfer_id')
            else:
                print("❌ No result returned")
                return None
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return None
    
    async def test_check_progress(self, transfer_id: str):
        """Test check_transfer_progress tool"""
        print("\n" + "="*60)
        print("TEST: check_transfer_progress")
        print("="*60)
        
        args = {"transfer_id": transfer_id}
        
        print(f"Checking progress for transfer: {transfer_id}")
        
        try:
            result = await self.server.call_tool("check_transfer_progress", args)
            
            if result and len(result) > 0:
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                data = json.loads(content) if isinstance(content, str) else content
                
                print("\n✅ Progress retrieved!")
                
                if 'progress' in data:
                    print(f"Progress: {data['progress'].get('percent_complete', 0)}%")
                
                if 'counts' in data:
                    print(f"Transferred: {data['counts'].get('transferred_items', 0):,} items")
                    print(f"Remaining: {data['counts'].get('remaining_items', 0):,} items")
                
                return True
            else:
                print("❌ No result returned")
                return False
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
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
            result = await self.server.call_tool("verify_transfer_complete", args)
            
            if result and len(result) > 0:
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                data = json.loads(content) if isinstance(content, str) else content
                
                print("\n✅ Verification complete!")
                print(f"Status: {data.get('status', 'N/A')}")
                
                if 'verification' in data:
                    print(f"Match rate: {data['verification'].get('match_rate', 0)}%")
                
                if 'certificate' in data:
                    print(f"Grade: {data['certificate'].get('grade', 'N/A')}")
                    print(f"Score: {data['certificate'].get('score', 0)}/100")
                
                return True
            else:
                print("❌ No result returned")
                return False
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return False
    
    async def test_check_email(self, transfer_id: str):
        """Test check_completion_email tool"""
        print("\n" + "="*60)
        print("TEST: check_completion_email")
        print("="*60)
        
        args = {"transfer_id": transfer_id}
        
        print(f"Checking email for transfer: {transfer_id}")
        
        try:
            result = await self.server.call_tool("check_completion_email", args)
            
            if result and len(result) > 0:
                content = result[0].text if hasattr(result[0], 'text') else str(result[0])
                data = json.loads(content) if isinstance(content, str) else content
                
                if data.get('email_found'):
                    print("\n✅ Email found!")
                    if 'email_details' in data:
                        print(f"Subject: {data['email_details'].get('subject', 'N/A')}")
                        print(f"From: {data['email_details'].get('sender', 'N/A')}")
                else:
                    print("\n📧 No email found yet")
                
                return True
            else:
                print("❌ No result returned")
                return False
                
        except Exception as e:
            print(f"❌ Tool execution failed: {e}")
            return False
    
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
                
                # 3. Check progress
                await self.test_check_progress(transfer_id)
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
            print("4. Test check_transfer_progress")
            print("5. Test verify_transfer_complete")
            print("6. Test check_completion_email")
            print("7. Run full test sequence")
            print("0. Exit")
            print("="*60)
            
            if transfer_id:
                print(f"Current transfer ID: {transfer_id}")
            
            choice = input("\nSelect option (0-7): ").strip()
            
            if choice == '1':
                self.list_tools()
            elif choice == '2':
                await self.test_check_status()
            elif choice == '3':
                result = await self.test_start_transfer()
                if result:
                    transfer_id = result
            elif choice == '4':
                if not transfer_id:
                    transfer_id = input("Enter transfer ID: ").strip()
                if transfer_id:
                    await self.test_check_progress(transfer_id)
            elif choice == '5':
                if not transfer_id:
                    transfer_id = input("Enter transfer ID: ").strip()
                if transfer_id:
                    await self.test_verify_complete(transfer_id)
            elif choice == '6':
                if not transfer_id:
                    transfer_id = input("Enter transfer ID: ").strip()
                if transfer_id:
                    await self.test_check_email(transfer_id)
            elif choice == '7':
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