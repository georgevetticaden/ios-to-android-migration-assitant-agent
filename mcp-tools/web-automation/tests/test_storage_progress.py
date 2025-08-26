#!/usr/bin/env python3
"""
Test script for storage-based progress tracking
Tests the transformed check_transfer_progress functionality
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
import duckdb

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from web_automation.icloud_client import ICloudClientWithSession

# Load environment variables
load_dotenv()

class StorageProgressTester:
    """Test storage-based progress tracking"""
    
    def __init__(self):
        self.client = None
        self.db_path = Path.home() / ".ios_android_migration" / "migration.db"
        
    async def setup(self):
        """Initialize client and APIs"""
        session_dir = os.path.expanduser("~/.icloud_session")
        self.client = ICloudClientWithSession(session_dir=session_dir)
        await self.client.initialize()
        await self.client.initialize_apis()
        print("✅ Client initialized with APIs")
        
    async def get_latest_transfer(self):
        """Get the most recent transfer from database"""
        if not self.db_path.exists():
            print("❌ Database not found")
            return None
            
        conn = duckdb.connect(str(self.db_path))
        result = conn.execute("""
            SELECT transfer_id, migration_id, total_photos, total_videos, 
                   total_size_gb, photo_status, video_status
            FROM media_transfer
            ORDER BY transfer_id DESC
            LIMIT 1
        """).fetchone()
        conn.close()
        
        if result:
            print(f"📋 Found transfer: {result[0]}")
            print(f"   Photos: {result[2]:,}, Videos: {result[3]:,}")
            print(f"   Total size: {result[4]} GB")
            print(f"   Status: Photos={result[5]}, Videos={result[6]}")
            return result[0]
        else:
            print("❌ No transfers found in database")
            return None
    
    async def test_progress_day(self, transfer_id: str, day_number: int):
        """Test progress check for a specific day"""
        print(f"\n{'='*60}")
        print(f"Testing Day {day_number} Progress")
        print('='*60)
        
        result = await self.client.check_transfer_progress(transfer_id, day_number)
        
        if result.get('status') == 'error':
            print(f"❌ Error: {result.get('error')}")
            return None
            
        # Display results
        print(f"\n📊 Day {result['day_number']} Progress Report:")
        print(f"   Status: {result['status']}")
        print(f"   Progress: {result['progress']['percent_complete']:.1f}%")
        
        print(f"\n📦 Storage Metrics:")
        print(f"   Baseline: {result['storage']['baseline_gb']} GB")
        print(f"   Current: {result['storage']['current_gb']} GB")
        print(f"   Growth: {result['storage']['growth_gb']} GB")
        print(f"   Remaining: {result['storage']['remaining_gb']} GB")
        
        print(f"\n📈 Estimated Transfer:")
        print(f"   Photos: {result['estimates']['photos_transferred']:,}")
        print(f"   Videos: {result['estimates']['videos_transferred']:,}")
        print(f"   Total: {result['estimates']['total_items']:,}")
        
        print(f"\n⏱️ Transfer Rate:")
        print(f"   Speed: {result['progress']['transfer_rate_gb_per_day']} GB/day")
        print(f"   Days remaining: {result['progress']['days_remaining']}")
        
        print(f"\n💬 Message: {result['message']}")
        
        if result.get('snapshot_saved'):
            print("✅ Snapshot saved to database")
            
        return result
    
    async def test_simulated_progress(self, transfer_id: str):
        """Test progress with simulated storage values for demo"""
        print(f"\n{'='*60}")
        print("SIMULATED 7-DAY PROGRESS TEST")
        print("This simulates what the progress would look like over 7 days")
        print('='*60)
        
        # Simulated storage values for each day
        simulated_days = [
            {"day": 1, "storage_gb": 1.05, "expected_percent": 0},
            {"day": 4, "storage_gb": 108.05, "expected_percent": 27.9},
            {"day": 5, "storage_gb": 219.05, "expected_percent": 56.9},
            {"day": 6, "storage_gb": 338.05, "expected_percent": 87.8},
            {"day": 7, "storage_gb": 384.05, "expected_percent": 99.7},
        ]
        
        print("\n📅 Simulated Timeline:")
        for sim in simulated_days:
            print(f"   Day {sim['day']}: {sim['storage_gb']} GB → {sim['expected_percent']}%")
        
        print("\n⚠️  Note: Actual test will use CURRENT Google One storage")
        print("The percentages shown will be based on real storage growth")
        
        # Test actual current progress
        actual_result = await self.test_progress_day(transfer_id, 4)
        
        if actual_result:
            print(f"\n📊 Comparison:")
            print(f"   Simulated Day 4: 108.05 GB (27.9%)")
            print(f"   Actual Current: {actual_result['storage']['current_gb']} GB ({actual_result['progress']['percent_complete']}%)")
    
    async def verify_database_updates(self, transfer_id: str):
        """Verify that snapshots and daily_progress were updated"""
        print(f"\n{'='*60}")
        print("Verifying Database Updates")
        print('='*60)
        
        if not self.db_path.exists():
            print("❌ Database not found")
            return
            
        conn = duckdb.connect(str(self.db_path))
        
        # Get migration_id
        migration_id = conn.execute("""
            SELECT migration_id FROM media_transfer 
            WHERE transfer_id = ?
        """, (transfer_id,)).fetchone()
        
        if not migration_id:
            print("❌ Transfer not found")
            conn.close()
            return
            
        migration_id = migration_id[0]
        
        # Check storage_snapshots
        snapshots = conn.execute("""
            SELECT day_number, google_photos_gb, storage_growth_gb, 
                   estimated_photos_transferred, snapshot_time
            FROM storage_snapshots
            WHERE migration_id = ?
            ORDER BY snapshot_time DESC
            LIMIT 5
        """, (migration_id,)).fetchall()
        
        if snapshots:
            print(f"\n📸 Storage Snapshots ({len(snapshots)} found):")
            for snap in snapshots:
                print(f"   Day {snap[0]}: {snap[1]} GB (+{snap[2]} GB) - {snap[3]:,} photos - {snap[4]}")
        else:
            print("❌ No storage snapshots found")
        
        # Check daily_progress
        progress = conn.execute("""
            SELECT day_number, storage_percent_complete, 
                   photos_transferred, videos_transferred, key_milestone
            FROM daily_progress
            WHERE migration_id = ?
            ORDER BY day_number DESC
            LIMIT 5
        """, (migration_id,)).fetchall()
        
        if progress:
            print(f"\n📈 Daily Progress ({len(progress)} records):")
            for prog in progress:
                print(f"   Day {prog[0]}: {prog[1]:.1f}% - {prog[2]:,} photos, {prog[3]:,} videos")
                print(f"      Milestone: {prog[4]}")
        else:
            print("❌ No daily progress records found")
        
        conn.close()
    
    async def cleanup(self):
        """Clean up resources"""
        if self.client:
            await self.client.cleanup()

async def main():
    """Main test runner"""
    print("""
╔══════════════════════════════════════════════════════════╗
║        STORAGE-BASED PROGRESS TRACKING TEST             ║
║                                                          ║
║  Tests the new storage-based check_transfer_progress    ║
║  - Captures Google One storage metrics                  ║
║  - Calculates real progress percentage                  ║
║  - Saves snapshots to database                          ║
║  - Returns day-specific messages                        ║
╚══════════════════════════════════════════════════════════╝
""")
    
    tester = StorageProgressTester()
    
    try:
        await tester.setup()
        
        # Get latest transfer or ask for ID
        transfer_id = await tester.get_latest_transfer()
        
        if not transfer_id:
            transfer_id = input("\nEnter transfer ID (or press Enter to skip): ").strip()
            if not transfer_id:
                print("❌ No transfer ID provided")
                return
        
        print("\n" + "="*60)
        print("Select Test Option:")
        print("="*60)
        print("1. Test current progress (actual day)")
        print("2. Test specific day (1-7)")
        print("3. Test simulated 7-day timeline")
        print("4. Verify database updates")
        print("5. Run all tests")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == '1':
            # Test current progress
            await tester.test_progress_day(transfer_id, None)  # Auto-calculate day
            
        elif choice == '2':
            # Test specific day
            day = input("Enter day number (1-7): ").strip()
            if day.isdigit() and 1 <= int(day) <= 7:
                await tester.test_progress_day(transfer_id, int(day))
            else:
                print("❌ Invalid day number")
                
        elif choice == '3':
            # Test simulated timeline
            await tester.test_simulated_progress(transfer_id)
            
        elif choice == '4':
            # Verify database updates
            await tester.verify_database_updates(transfer_id)
            
        elif choice == '5':
            # Run all tests
            print("\n🔄 Running all tests...")
            
            # Test Day 1
            await tester.test_progress_day(transfer_id, 1)
            
            # Test Day 4 (photos visible)
            await tester.test_progress_day(transfer_id, 4)
            
            # Test Day 7 (near complete)
            await tester.test_progress_day(transfer_id, 7)
            
            # Verify database
            await tester.verify_database_updates(transfer_id)
            
        else:
            print("❌ Invalid option")
        
        print("\n" + "="*60)
        print("✅ Test Complete!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        await tester.cleanup()

if __name__ == "__main__":
    asyncio.run(main())