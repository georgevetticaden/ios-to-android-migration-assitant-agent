#!/usr/bin/env python3
"""
Test script for Gmail API
Verifies OAuth2 setup and email monitoring functionality
"""

import os
import sys
import asyncio
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from root .env
root_dir = Path(__file__).parent.parent
env_file = root_dir / '.env'
print(f"Loading .env from: {env_file}")
load_dotenv(env_file)

# Add photo-migration src to path
photo_migration_src = root_dir / 'mcp-tools' / 'photo-migration' / 'src'
sys.path.insert(0, str(photo_migration_src))

from photo_migration.gmail_monitor import GmailMonitor

async def test_gmail():
    """Test Gmail API for monitoring Apple transfer emails"""
    print("\n" + "="*60)
    print("Testing Gmail API")
    print("="*60)
    
    try:
        monitor = GmailMonitor()
        await monitor.initialize()
        
        # Check for completion emails
        print("\nChecking for Apple transfer emails...")
        result = await monitor.check_for_completion_email(since_hours=720)  # Last 30 days
        
        if result['found']:
            print(f"✅ Found transfer email:")
            print(f"   Subject: {result.get('subject')}")
            print(f"   Date: {result.get('received_at')}")
        else:
            print("ℹ️  No transfer completion emails found (this is normal if no transfer has been done)")
        
        # Get recent Apple emails
        print("\nGetting recent Apple emails...")
        emails = await monitor.get_recent_apple_emails(limit=3)
        
        if emails:
            print(f"✅ Found {len(emails)} recent Apple emails:")
            for email in emails:
                print(f"   - {email['subject'][:50]}...")
        else:
            print("ℹ️  No recent Apple emails found")
        
        await monitor.cleanup()
        return True
        
    except Exception as e:
        print(f"❌ Gmail test failed: {e}")
        return False

async def main():
    """Run Gmail API test"""
    print("\n🚀 Gmail API Test Suite")
    print("For monitoring Apple transfer completion emails")
    print("\nNOTE: You may be prompted to authorize Gmail access")
    
    gmail_ok = await test_gmail()
    
    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"Gmail API: {'✅ PASSED' if gmail_ok else '❌ FAILED'}")
    
    if gmail_ok:
        print("\n✅ Gmail API is ready for use!")
        print("\nNext steps:")
        print("1. Use record_flow.py to record Google Dashboard steps")
        print("2. Implement Playwright-based photo counting")
        print("3. Extend iCloud client with new methods")
    else:
        print("\n⚠️  Gmail test failed. Please check:")
        print("- Gmail API is enabled in Cloud Console")
        print("- OAuth2 credentials are correct")
        print("- GMAIL_CREDENTIALS_PATH is set in .env")

if __name__ == "__main__":
    asyncio.run(main())