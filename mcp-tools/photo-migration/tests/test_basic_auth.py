#!/usr/bin/env python3.11
"""
Test client with session persistence
First run: Requires 2FA
Subsequent runs: No 2FA needed (for ~7 days)
"""

import asyncio
import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from src.photo_migration.icloud_client import ICloudClientWithSession

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from src.photo_migration.logging_config import setup_logging

# Set up centralized logging
logger = setup_logging(__name__)
logger.info("Starting test_basic_auth")

# Load environment variables from project root
env_file = Path(__file__).parent.parent / '.env'
load_dotenv(env_file)

async def test():
    # Get credentials from environment variables
    apple_id = os.getenv('APPLE_ID')
    apple_password = os.getenv('APPLE_PASSWORD')
    
    if not apple_id or not apple_password:
        print("Error: APPLE_ID and APPLE_PASSWORD must be set in .env file")
        return
    
    # Check for command line arguments
    force_fresh = '--fresh' in sys.argv
    clear_session = '--clear' in sys.argv
    
    print(f"Testing with Apple ID: {apple_id}")
    print("=" * 60)
    print("iCloud Photo Status Checker - WITH SESSION PERSISTENCE")
    print("=" * 60)
    
    # Use a specific session directory
    session_dir = os.path.expanduser("~/.icloud_session")
    client = ICloudClientWithSession(session_dir=session_dir)
    await client.initialize()
    
    try:
        if clear_session:
            print("Clearing saved session...")
            await client.clear_session()
            print("Session cleared. Next run will require 2FA.")
            return
        
        if force_fresh:
            print("Forcing fresh login (will require 2FA)...")
        elif client.is_session_valid():
            print("✅ Found valid saved session - NO 2FA NEEDED!")
        else:
            print("No valid session found - will need 2FA this time")
            print("But session will be saved for future runs!")
        
        print("\nStarting automation...")
        result = await client.get_photo_status(
            apple_id=apple_id,
            password=apple_password,
            force_fresh_login=force_fresh
        )
        
        print("\n=== iCloud Photo Library Status ===")
        print(f"📸 Photos: {result['photos']:,}")
        print(f"🎬 Videos: {result['videos']:,}")
        print(f"📦 Total Items: {result['total_items']:,}")
        print(f"💾 Storage: {result['storage_gb']:.1f} GB")
        print(f"📅 Checked at: {result['checked_at']}")
        
        if result.get('session_used'):
            print("\n✅ Used saved session - No 2FA was needed!")
        else:
            print("\n✅ New session saved - Future runs won't need 2FA!")
        
        if result.get('existing_transfers'):
            print("\n=== Transfer History ===")
            for transfer in result['existing_transfers']:
                print(f"- {transfer['status'].title()}: {transfer.get('date', 'Unknown')}")
                
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.error(f"Test failed: {e}", exc_info=True)
    finally:
        await client.cleanup()

if __name__ == "__main__":
    print("\nUsage:")
    print("  python test_with_session.py         # Use saved session if available")
    print("  python test_with_session.py --fresh  # Force fresh login (require 2FA)")
    print("  python test_with_session.py --clear  # Clear saved session")
    print()
    
    asyncio.run(test())