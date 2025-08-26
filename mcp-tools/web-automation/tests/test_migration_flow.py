#!/usr/bin/env python3
"""
Phase 3 Integration Test - Complete Photo Migration Flow

This test script validates the entire photo migration workflow from iCloud to 
Google Photos using only the Phase 3 MCP methods. It demonstrates proper API
usage without direct database manipulation, ensuring all state management goes
through the designated MCP interfaces.

Test Workflow:
1. CHECK ICLOUD STATUS - Retrieve photo/video counts from iCloud
2. INITIALIZE APIS - Set up Gmail, Database, and Google Dashboard clients
3. CHECK EXISTING TRANSFERS - Query database for previous transfers
4. START NEW TRANSFER - Initiate Apple to Google migration (interactive)
5. CHECK TRANSFER PROGRESS - Monitor migration status
6. CHECK FOR EMAILS - Look for Apple completion emails
7. VERIFY TRANSFER COMPLETE - Validate final transfer state
8. DATABASE SUMMARY - Review all transfer records

Phase 3 MCP Methods Used:
- check_icloud_status(): Get current photo library counts
- start_transfer(): Initiate transfer with baseline establishment
- check_transfer_progress(): Monitor ongoing transfer
- check_completion_email(): Check for confirmation emails
- verify_transfer_complete(): Validate transfer completion

Key Features:
- No direct database manipulation (all through MCP methods)
- Automatic database integration and state persistence
- Interactive prompts for destructive operations
- Comprehensive error handling and logging
- Browser session reuse for efficiency

Prerequisites:
- Apple ID and password in environment variables
- Google account credentials configured
- Database initialized with V2 schema
- Browser automation dependencies installed

Environment Variables Required:
- APPLE_ID: Apple account email
- APPLE_PASSWORD: Apple account password
- GOOGLE_EMAIL: Google account email
- GOOGLE_PASSWORD: Google account password

Usage:
    python test_migration_flow.py
    
    Follow interactive prompts to:
    - Start new transfer (optional)
    - Check progress (if transfer exists)
    - Verify completion (when ready)

Note: Browser remains open after test for manual inspection.
Press Enter to close browser and exit when done.
"""
import asyncio
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from web_automation.icloud_client import ICloudClientWithSession

# Set up logging
sys.path.insert(0, str(Path(__file__).parent.parent))
from web_automation.logging_config import setup_logging
logger = setup_logging(__name__)

# Load environment variables
load_dotenv()

async def test_phase3_flow():
    """Test Phase 3 methods in proper sequence"""
    client = ICloudClientWithSession()
    
    try:
        print("\n" + "="*80)
        print("PHASE 3 INTEGRATED TEST - Using MCP Methods Only")
        print("="*80)
        print("This test uses ONLY the Phase 3 MCP methods:")
        print("1. check_icloud_status - Get photo counts")
        print("2. start_transfer - Start transfer with baseline")
        print("3. check_transfer_progress - Monitor progress")
        print("4. check_completion_email - Check for emails")
        print("5. verify_transfer_complete - Verify completion")
        print("="*80)
        
        # Initialize client
        await client.initialize()
        print("✅ Client initialized")
        
        # ============================================================
        # STEP 1: CHECK ICLOUD STATUS
        # ============================================================
        print("\n" + "="*60)
        print("STEP 1: CHECK ICLOUD STATUS")
        print("="*60)
        
        status_result = await client.get_photo_status(
            apple_id=os.getenv('APPLE_ID'),
            password=os.getenv('APPLE_PASSWORD'),
            force_fresh_login=False
        )
        
        if status_result.get('status') != 'success':
            print(f"❌ Failed to get iCloud status: {status_result}")
            return
        
        print(f"✅ iCloud Status Retrieved:")
        print(f"   - Photos: {status_result['photos']:,}")
        print(f"   - Videos: {status_result['videos']:,}")
        print(f"   - Storage: {status_result.get('storage_gb', 0)} GB")
        print(f"   - Total items: {status_result.get('total_items', 0):,}")
        
        # ============================================================
        # STEP 2: INITIALIZE APIS (Required for transfer)
        # ============================================================
        print("\n" + "="*60)
        print("STEP 2: INITIALIZE APIS")
        print("="*60)
        
        await client.initialize_apis()
        print("✅ APIs initialized (Gmail, Database, Google Dashboard)")
        
        # ============================================================
        # STEP 3: CHECK FOR EXISTING TRANSFERS (Optional)
        # ============================================================
        print("\n" + "="*60)
        print("STEP 3: CHECK EXISTING TRANSFERS (from database)")
        print("="*60)
        
        # Check if there are any existing transfers in the database
        if client.db:
            try:
                with client.db.get_connection() as conn:
                    result = conn.execute("""
                        SELECT transfer_id, status, started_at 
                        FROM photo_migration.transfers 
                        ORDER BY started_at DESC 
                        LIMIT 5
                    """).fetchall()
                    
                    if result:
                        print(f"Found {len(result)} existing transfers:")
                        for row in result:
                            print(f"   - {row[0]}: {row[1]} (created {row[2]})")
                    else:
                        print("No existing transfers found in database")
            except Exception as e:
                print(f"Could not check existing transfers: {e}")
                print("No existing transfers found")
        else:
            print("Database not available - skipping existing transfer check")
        
        # ============================================================
        # STEP 4: START NEW TRANSFER (Interactive)
        # ============================================================
        print("\n" + "="*60)
        print("STEP 4: START NEW TRANSFER")
        print("="*60)
        print("⚠️  This will:")
        print("   1. Establish Google Photos baseline (separate browser)")
        print("   2. Navigate through Apple transfer workflow")
        print("   3. Handle Google OAuth")
        print("   4. Stop at confirmation page")
        print("   5. Save transfer to database")
        
        start_transfer = input("\nStart a new transfer? (yes/no): ").strip().lower()
        
        if start_transfer == 'yes':
            print("\n🚀 Starting transfer...")
            
            # Call start_transfer - this does EVERYTHING
            transfer_result = await client.start_transfer(reuse_session=True)
            
            print(f"\nTransfer Result: {json.dumps(transfer_result, indent=2)}")
            
            if transfer_result.get('status') == 'initiated':
                transfer_id = transfer_result['transfer_id']
                print(f"\n✅ Transfer initiated successfully!")
                print(f"Transfer ID: {transfer_id}")
                print(f"Started at: {transfer_result['started_at']}")
                print(f"\n📊 Source Counts:")
                for key, value in transfer_result['source_counts'].items():
                    print(f"   - {key}: {value}")
                print(f"\n📍 Destination:")
                for key, value in transfer_result['destination'].items():
                    print(f"   - {key}: {value}")
                print(f"\n📈 Baseline:")
                for key, value in transfer_result['baseline_established'].items():
                    print(f"   - {key}: {value}")
                
                # The transfer is now saved in the database automatically!
                print("\n💾 Transfer saved to database automatically")
                
                # ========================================================
                # STEP 5: CHECK TRANSFER PROGRESS
                # ========================================================
                print("\n" + "="*60)
                print("STEP 5: CHECK TRANSFER PROGRESS")
                print("="*60)
                
                check_progress = input("\nCheck transfer progress? (yes/no): ").strip().lower()
                
                if check_progress == 'yes':
                    progress = await client.check_transfer_progress(transfer_id)
                    
                    if progress.get('status') == 'success':
                        print(f"\n📊 Transfer Progress:")
                        print(f"   - Status: {progress.get('transfer_status')}")
                        print(f"   - Progress: {progress.get('percent_complete', 0):.1f}%")
                        print(f"   - Transferred: {progress.get('transferred_items', 0):,} items")
                        print(f"   - Current Google count: {progress.get('current_google_count', 0):,}")
                        print(f"   - Days elapsed: {progress.get('days_elapsed', 0):.1f}")
                        
                        # Progress is automatically saved to database!
                        print("\n💾 Progress saved to database automatically")
                    else:
                        print(f"❌ Failed to check progress: {progress}")
                
                # ========================================================
                # STEP 6: CHECK FOR EMAILS
                # ========================================================
                print("\n" + "="*60)
                print("STEP 6: CHECK FOR TRANSFER EMAILS")
                print("="*60)
                
                email_result = await client.check_completion_email(transfer_id)
                
                if email_result.get('status') == 'success':
                    if email_result.get('has_completion_email'):
                        print(f"✅ Found completion email!")
                        email = email_result['email']
                        print(f"   - Subject: {email['subject']}")
                        print(f"   - From: {email['from']}")
                        print(f"   - Date: {email['date']}")
                        
                        # Email is automatically saved to database!
                        print("\n💾 Email confirmation saved to database automatically")
                    else:
                        print("No completion email found yet (transfer may still be in progress)")
                else:
                    print(f"Failed to check emails: {email_result}")
                
                # ========================================================
                # STEP 7: VERIFY TRANSFER COMPLETE
                # ========================================================
                print("\n" + "="*60)
                print("STEP 7: VERIFY TRANSFER COMPLETE")
                print("="*60)
                
                verify_transfer = input("\nVerify transfer completion? (yes/no): ").strip().lower()
                
                if verify_transfer == 'yes':
                    verify_result = await client.verify_transfer_complete(transfer_id)
                    
                    if verify_result.get('status') == 'success':
                        print(f"\n✅ Transfer Verification:")
                        print(f"   - Transfer status: {verify_result['transfer_status']}")
                        print(f"   - Is complete: {verify_result['is_complete']}")
                        
                        if verify_result['is_complete']:
                            summary = verify_result['summary']
                            print(f"\n📊 Transfer Summary:")
                            print(f"   - Source items: {summary['source_total']:,}")
                            print(f"   - Transferred: {summary['transferred_items']:,}")
                            print(f"   - Success rate: {summary['success_rate']:.1f}%")
                            print(f"   - Duration: {summary['days_taken']:.1f} days")
                        
                        # Verification is automatically saved to database!
                        print("\n💾 Verification saved to database automatically")
                    else:
                        print(f"Failed to verify: {verify_result}")
            else:
                print(f"\n❌ Transfer initiation failed: {transfer_result}")
        else:
            print("\n✋ Transfer start skipped")
        
        # ============================================================
        # STEP 8: DATABASE SUMMARY (Read from database)
        # ============================================================
        print("\n" + "="*60)
        print("STEP 8: DATABASE SUMMARY")
        print("="*60)
        
        if client.db:
            with client.db.get_connection() as conn:
                # Check photo_migration.transfers table
                transfers = conn.execute("""
                    SELECT transfer_id, status, started_at, 
                           source_photos, source_videos, baseline_google_count
                    FROM photo_migration.transfers 
                    ORDER BY started_at DESC 
                    LIMIT 5
                """).fetchall()
                
                print(f"\n📋 Recent Transfers ({len(transfers)} records):")
                for transfer in transfers:
                    print(f"\n   Transfer: {transfer[0]}")
                    print(f"   Status: {transfer[1]}")
                    print(f"   Started: {transfer[2]}")
                    print(f"   Photos: {transfer[3]:,}, Videos: {transfer[4]:,}")
                    print(f"   Baseline: {transfer[5]:,} photos")
                
                # Check progress history
                progress_records = conn.execute("""
                    SELECT transfer_id, checked_at, google_photos_total, transferred_items
                    FROM photo_migration.progress_history
                    ORDER BY checked_at DESC
                    LIMIT 5
                """).fetchall()
                
                if progress_records:
                    print(f"\n📈 Recent Progress Checks ({len(progress_records)} records):")
                    for record in progress_records:
                        print(f"   {record[0]}: {record[3]:,} items transferred (checked {record[1]})")
        else:
            print("Database not available")
        
        # Keep browser open
        print("\n" + "="*80)
        print("⏸️  Test complete. Browser will stay open for inspection.")
        print("Press Enter to close browser and exit...")
        input()
        
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        await client.cleanup()
        print("\n✅ Cleanup completed")

async def main():
    """Main function"""
    print("""
╔══════════════════════════════════════════════════════════╗
║          PHASE 3 INTEGRATED TEST                        ║
║                                                          ║
║  Tests the complete flow using ONLY MCP methods:        ║
║  - No direct database manipulation                      ║
║  - All state management through proper APIs             ║
║  - Automatic database integration                       ║
║  - Proper sequencing of operations                      ║
╚══════════════════════════════════════════════════════════╝
""")
    
    # Check environment
    required = ['APPLE_ID', 'APPLE_PASSWORD', 'GOOGLE_EMAIL', 'GOOGLE_PASSWORD']
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print("\n⚠️  Missing environment variables:")
        for var in missing:
            print(f"  - {var}")
        print("\nPlease set these in your .env file")
        return
    
    await test_phase3_flow()

if __name__ == "__main__":
    asyncio.run(main())