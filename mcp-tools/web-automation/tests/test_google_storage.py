#!/usr/bin/env python3
"""
Test script for Google One storage client
Verifies storage extraction from one.google.com/storage
"""

import asyncio
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from web_automation.google_storage_client import GoogleStorageClient

# Load environment variables
load_dotenv()

async def test_google_storage():
    """Test Google One storage extraction"""
    print("=" * 60)
    print("Google One Storage Test")
    print("=" * 60)
    
    client = GoogleStorageClient()
    
    try:
        # Get credentials from environment
        google_email = os.getenv('GOOGLE_EMAIL')
        google_password = os.getenv('GOOGLE_PASSWORD')
        
        if not google_email or not google_password:
            print("❌ Please set GOOGLE_EMAIL and GOOGLE_PASSWORD in .env file")
            return
        
        print(f"📊 Getting storage metrics for {google_email}...")
        print("   This will open one.google.com/storage")
        print()
        
        # Check for --fresh flag
        force_fresh = "--fresh" in sys.argv
        
        # Get storage metrics
        result = await client.get_storage_metrics(
            google_email=google_email,
            google_password=google_password,
            force_fresh_login=force_fresh
        )
        
        if result['status'] == 'success':
            print("✅ Storage metrics retrieved successfully!\n")
            print("📊 Storage Summary:")
            print(f"   Total Storage: {result.get('total_storage_gb', 0):.2f} GB")
            print(f"   Used Storage: {result.get('used_storage_gb', 0):.2f} GB")
            print(f"   Available: {result.get('available_storage_gb', 0):.2f} GB")
            print()
            print("📦 Service Breakdown:")
            print(f"   Google Photos: {result.get('google_photos_gb', 0):.2f} GB")
            print(f"   Google Drive: {result.get('google_drive_gb', 0):.2f} GB")
            print(f"   Gmail: {result.get('gmail_gb', 0):.2f} GB")
            print(f"   Device Backup: {result.get('device_backup_gb', 0):.2f} GB")
            print()
            print(f"🕒 Timestamp: {result.get('timestamp', 'N/A')}")
            print(f"🔑 Session Used: {result.get('session_used', False)}")
            
            # Calculate how much space is available for transfer
            available = result.get('available_storage_gb', 0)
            if available > 0:
                print()
                print(f"💡 You have {available:.2f} GB available for the transfer")
                print(f"   (383 GB needed for complete iCloud transfer)")
                
                if available >= 383:
                    print("   ✅ Sufficient space for complete transfer")
                else:
                    print(f"   ⚠️  You may need {383 - available:.2f} GB more space")
        else:
            print(f"❌ Failed to get storage metrics: {result.get('error', 'Unknown error')}")
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("Starting Google One storage test...")
    print("Options:")
    print("  --fresh : Force fresh login even if session exists")
    print()
    asyncio.run(test_google_storage())