#!/usr/bin/env python3
"""
Simplified test for the complete photo migration flow.
This test properly uses the Phase 3 methods without redundant authentication.
"""

import asyncio
import os
import sys
import json
from pathlib import Path
from datetime import datetime
import logging

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from web_automation.icloud_client import ICloudClientWithSession
from web_automation.logging_config import setup_logging

# Setup logging
logger = setup_logging(__name__)

# Load environment variables from project root
from dotenv import load_dotenv
# Path structure: tests/test_migration_flow_simple.py
# Need to go up: tests -> photo-migration -> mcp-tools -> ios-to-android-migration-assitant-agent
# That's 4 levels up (tests -> photo-migration -> mcp-tools -> ios-to-android-migration-assitant-agent)
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / '.env'
if env_path.exists():
    load_dotenv(env_path)
    logger.info(f"Loaded environment from: {env_path}")
else:
    # Try local directory as fallback
    local_env = Path(__file__).parent.parent / '.env'
    if local_env.exists():
        load_dotenv(local_env)
        logger.info(f"Loaded environment from: {local_env}")
    else:
        logger.warning(f"No .env file found at: {env_path} or {local_env}")
        logger.warning(f"Current directory: {Path.cwd()}")
        logger.warning(f"Test file location: {Path(__file__).resolve()}")

async def test_simplified_flow():
    """Test the migration flow the way it should actually work"""
    
    logger.info("="*80)
    logger.info("SIMPLIFIED PHOTO MIGRATION TEST")
    logger.info("="*80)
    logger.info("This test demonstrates the proper flow:")
    logger.info("1. start_transfer() - Handles EVERYTHING including auth")
    logger.info("2. Confirm transfer - Explicit user confirmation")
    logger.info("3. Monitor progress - Check transfer status")
    logger.info("="*80)
    
    # Also print to console for interactive use
    print("\n" + "="*80)
    print("SIMPLIFIED PHOTO MIGRATION TEST")
    print("="*80)
    print("This test demonstrates the proper flow:")
    print("1. start_transfer() - Handles EVERYTHING including auth")
    print("2. Confirm transfer - Explicit user confirmation")
    print("3. Monitor progress - Check transfer status")
    print("="*80)
    
    # Initialize client
    client = ICloudClientWithSession()
    await client.initialize()
    await client.initialize_apis()
    print("✅ Client initialized\n")
    
    # ============================================================
    # STEP 1: START TRANSFER (This does EVERYTHING!)
    # ============================================================
    print("="*60)
    print("STEP 1: START TRANSFER")
    print("="*60)
    print("This will:")
    print("  1. Authenticate with Apple (if needed)")
    print("  2. Get iCloud photo counts")
    print("  3. Establish Google baseline")
    print("  4. Navigate transfer workflow")
    print("  5. Stop at confirmation page")
    
    proceed = input("\nStart transfer process? (yes/no): ").strip().lower()
    
    if proceed != 'yes':
        print("❌ Test cancelled")
        return
    
    print("\n🚀 Starting transfer process...")
    print("(This handles all authentication automatically)\n")
    
    # Start the transfer - this does EVERYTHING
    transfer_result = await client.start_transfer(reuse_session=True)
    
    if transfer_result.get('status') != 'initiated':
        logger.error(f"Transfer failed with status: {transfer_result.get('status')}")
        logger.error(f"Error: {transfer_result.get('error', transfer_result.get('message', 'No error message'))}")
        logger.error(f"Full result: {transfer_result}")
        print(f"❌ Transfer failed with status: {transfer_result.get('status')}")
        print(f"   Error: {transfer_result.get('error', transfer_result.get('message', 'No error message'))}")
        print(f"   Full result: {transfer_result}")
        return
    
    transfer_id = transfer_result['transfer_id']
    
    logger.info(f"Transfer prepared successfully!")
    logger.info(f"Transfer Details:")
    print(f"\n✅ Transfer prepared successfully!")
    print(f"\n📋 Transfer Details:")
    print(f"   Transfer ID: {transfer_id}")
    print(f"   Photos: {transfer_result['source_counts']['photos']:,}")
    print(f"   Videos: {transfer_result['source_counts']['videos']:,}")
    print(f"   Total Size: {transfer_result['source_counts']['size_gb']} GB")
    print(f"   Destination: {transfer_result['destination']['service']}")
    print(f"   Account: {transfer_result['destination']['account']}")
    print(f"   Baseline: {transfer_result['baseline_established']['pre_transfer_count']} photos already in Google")
    
    # ============================================================
    # STEP 2: CONFIRM TRANSFER (User must explicitly confirm)
    # ============================================================
    print("\n" + "="*60)
    print("STEP 2: CONFIRM TRANSFER")
    print("="*60)
    print("\n⚠️  IMPORTANT: Review the confirmation page in the browser")
    print(f"   - {transfer_result['source_counts']['photos']:,} photos will be transferred")
    print(f"   - Destination: {transfer_result['destination']['account']}")
    print(f"   - Required storage: {transfer_result['source_counts']['size_gb']}GB")
    print("   - Estimated time: 3-7 days")
    
    confirm = input("\n🔴 Ready to start the actual transfer? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        print("\n📤 Confirming transfer...")
        confirm_result = await client.confirm_transfer_final_step()
        
        if confirm_result.get('status') == 'confirmed':
            print("✅ Transfer confirmed and started!")
            print(f"   {confirm_result['message']}")
            print("\n📝 Next steps:")
            for step in confirm_result.get('next_steps', []):
                print(f"   - {step}")
        else:
            print(f"❌ Confirmation failed: {confirm_result.get('message')}")
    else:
        print("\n⏸️  Transfer NOT confirmed - remains at confirmation page")
        print("   (You can manually click 'Confirm Transfer' in the browser)")
    
    # ============================================================
    # STEP 3: CHECK PROGRESS (Optional)
    # ============================================================
    print("\n" + "="*60)
    print("STEP 3: CHECK TRANSFER PROGRESS")
    print("="*60)
    
    check = input("\nCheck transfer progress? (yes/no): ").strip().lower()
    
    if check == 'yes':
        progress = await client.check_transfer_progress(transfer_id)
        
        if progress.get('status') == 'in_progress':
            print(f"\n📊 Transfer Progress:")
            print(f"   Status: {progress['status']}")
            print(f"   Progress: {progress['progress']['percent_complete']:.1f}%")
            print(f"   Transferred: {progress['counts']['transferred_items']:,} items")
            print(f"   Remaining: {progress['counts']['remaining_items']:,} items")
            print(f"   Days elapsed: {progress['timeline']['days_elapsed']:.1f}")
            
            if progress['progress']['percent_complete'] < 100:
                print(f"   Estimated completion: {progress['timeline']['estimated_completion']}")
        else:
            print(f"Progress check result: {progress}")
    
    # ============================================================
    # STEP 4: CHECK EMAIL (Optional)
    # ============================================================
    print("\n" + "="*60)
    print("STEP 4: CHECK FOR COMPLETION EMAIL")
    print("="*60)
    
    check_email = input("\nCheck for completion email? (yes/no): ").strip().lower()
    
    if check_email == 'yes':
        email_result = await client.check_completion_email(transfer_id)
        
        if email_result.get('email_found'):
            print("✅ Completion email found!")
            print(f"   Subject: {email_result['email_details']['subject']}")
            print(f"   Received: {email_result['email_details']['received_at']}")
        else:
            print("📧 No completion email yet (transfer may still be in progress)")
    
    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)
    
    # Check database
    if client.db:
        try:
            with client.db.get_connection() as conn:
                result = conn.execute("""
                    SELECT transfer_id, status, source_photos, baseline_google_count
                    FROM photo_migration.transfers 
                    WHERE transfer_id = ?
                """, (transfer_id,)).fetchone()
                
                if result:
                    print(f"\n💾 Database Record:")
                    print(f"   Transfer ID: {result[0]}")
                    print(f"   Status: {result[1]}")
                    print(f"   Source Photos: {result[2]:,}")
                    print(f"   Baseline: {result[3]}")
        except Exception as e:
            print(f"Could not query database: {e}")
    
    print("\n✅ Test completed successfully!")
    print("\n💡 Browser remains open for inspection")
    input("Press Enter to close browser and exit...")
    
    # Cleanup
    await client.cleanup()

async def main():
    """Main entry point"""
    try:
        await test_simplified_flow()
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}", exc_info=True)
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Cleanup completed")
        print("\n✅ Cleanup completed")

if __name__ == "__main__":
    # Environment variables are already loaded at module level
    # Run the test
    asyncio.run(main())