#!/usr/bin/env python3
"""
Quick script to check transfer progress for existing transfer
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.photo_migration.icloud_client import ICloudClientWithSession
from src.photo_migration.logging_config import setup_logging
from dotenv import load_dotenv

# Setup logging
logger = setup_logging(__name__)

# Load environment
project_root = Path(__file__).parent.parent.parent.parent
env_path = project_root / '.env'
load_dotenv(env_path)

async def check_progress():
    """Check progress of existing transfer"""
    
    print("\n" + "="*60)
    print("TRANSFER PROGRESS CHECK")
    print("="*60)
    
    # Initialize client
    client = ICloudClientWithSession()
    await client.initialize()
    await client.initialize_apis()
    print("✅ Client initialized\n")
    
    # The transfer ID from your latest run
    transfer_id = "TRF-20250820-180056"
    
    print(f"Checking progress for transfer: {transfer_id}\n")
    
    # Check progress
    progress = await client.check_transfer_progress(transfer_id)
    
    if progress.get('status') == 'in_progress':
        print(f"📊 Transfer Progress:")
        print(f"   Status: {progress['status']}")
        print(f"   Progress: {progress['progress']['percent_complete']:.1f}%")
        print(f"   Transferred: {progress['counts']['transferred_items']:,} items")
        print(f"   Remaining: {progress['counts']['remaining_items']:,} items")
        print(f"   Days elapsed: {progress['timeline']['days_elapsed']:.1f}")
        
        if progress['progress']['percent_complete'] < 100:
            print(f"   Estimated completion: {progress['timeline']['estimated_completion']}")
    elif progress.get('status') == 'error':
        print(f"❌ Error checking progress: {progress.get('error')}")
    else:
        print(f"Status: {progress}")
    
    # Check for completion email
    print("\n" + "="*60)
    print("CHECKING FOR COMPLETION EMAIL")
    print("="*60)
    
    email_result = await client.check_completion_email(transfer_id)
    
    if email_result.get('email_found'):
        print("✅ Completion email found!")
        print(f"   Subject: {email_result['email_details']['subject']}")
        print(f"   Received: {email_result['email_details']['received_at']}")
    else:
        print("📧 No completion email yet (transfer may still be in progress)")
    
    # Cleanup
    await client.cleanup()
    print("\n✅ Done")

async def main():
    try:
        await check_progress()
    except Exception as e:
        logger.error(f"Failed: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(main())