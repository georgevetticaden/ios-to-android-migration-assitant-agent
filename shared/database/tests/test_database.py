#!/usr/bin/env python3
"""
Test script for iOS to Android Migration Database Schema v2.0
Validates video support, storage tracking, and all new features
"""

import sys
import os
from pathlib import Path
import duckdb
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

class DatabaseTester:
    def __init__(self):
        self.db_path = Path('~/.ios_android_migration/migration.db').expanduser()
        self.conn = None
        self.tests_passed = 0
        self.tests_failed = 0
        
    def connect(self):
        """Connect to the database"""
        if not self.db_path.exists():
            print(f"❌ Database not found at: {self.db_path}")
            print("   Run: python3 shared/database/scripts/initialize_v2_database.py")
            return False
        
        try:
            self.conn = duckdb.connect(str(self.db_path))
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def test(self, name, test_func):
        """Run a test and track results"""
        try:
            print(f"\n🧪 Testing: {name}")
            result = test_func()
            if result:
                print(f"  ✅ PASSED")
                self.tests_passed += 1
            else:
                print(f"  ❌ FAILED")
                self.tests_failed += 1
            return result
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            self.tests_failed += 1
            return False
    
    def test_all_tables_exist(self):
        """Test that all 8 tables exist (including new storage_snapshots)"""
        expected = [
            'migration_status', 'family_members', 'media_transfer',
            'app_setup', 'family_app_adoption', 'daily_progress', 'venmo_setup',
            'storage_snapshots'
        ]
        
        tables = self.conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
        """).fetchall()
        
        actual = [t[0] for t in tables]
        missing = [t for t in expected if t not in actual]
        
        if missing:
            print(f"    Missing tables: {missing}")
            return False
        
        print(f"    Found all {len(expected)} tables")
        return True
    
    def test_migration_initialization(self):
        """Test creating a new migration with video and storage support"""
        try:
            # Create a migration with all new fields
            self.conn.execute("""
                INSERT INTO migration_status 
                (user_name, years_on_ios, photo_count, video_count, 
                 total_icloud_storage_gb, icloud_photo_storage_gb, icloud_video_storage_gb,
                 google_photos_baseline_gb, family_size)
                VALUES ('George', 18, 60238, 2418, 383.0, 268.1, 114.9, 13.88, 5)
            """)
            
            # Get the created migration
            result = self.conn.execute("""
                SELECT id, user_name, photo_count 
                FROM migration_status 
                WHERE user_name = 'George'
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            
            if not result:
                return False
            
            migration_id = result[0]
            print(f"    Created migration: {migration_id}")
            
            # Clean up
            self.conn.execute(f"DELETE FROM migration_status WHERE id = '{migration_id}'")
            
            return True
        except Exception as e:
            print(f"    Error: {e}")
            return False
    
    def test_family_members(self):
        """Test adding family members with email"""
        try:
            # Create a migration first
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name, family_size)
                VALUES ('TEST-MIG-001', 'TestUser', 0)
            """)
            
            # Add family members
            family = [
                (1001, 'Jaisy', 'jaisy.vetticaden@gmail.com', 'spouse', None),
                (1002, 'Laila', 'laila.vetticaden@gmail.com', 'child', 17),
                (1003, 'Ethan', 'ethan.vetticaden@gmail.com', 'child', 15),
                (1004, 'Maya', 'maya.vetticaden@gmail.com', 'child', 11)
            ]
            
            for id, name, email, role, age in family:
                self.conn.execute(f"""
                    INSERT INTO family_members 
                    (id, migration_id, name, email, role, age)
                    VALUES ({id}, 'TEST-MIG-001', '{name}', '{email}', '{role}', {age if age else 'NULL'})
                """)
            
            # Verify
            count = self.conn.execute("""
                SELECT COUNT(*) FROM family_members 
                WHERE migration_id = 'TEST-MIG-001'
            """).fetchone()[0]
            
            # Clean up
            self.conn.execute("DELETE FROM family_members WHERE migration_id = 'TEST-MIG-001'")
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-001'")
            
            print(f"    Added {count} family members")
            return count == 4
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup anyway
            try:
                self.conn.execute("DELETE FROM family_members WHERE migration_id = 'TEST-MIG-001'")
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-001'")
            except:
                pass
            return False
    
    def test_media_transfer(self):
        """Test media transfer tracking with separate photo/video support"""
        try:
            # Create migration
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name, photo_count, video_count)
                VALUES ('TEST-MIG-002', 'TestUser', 60238, 2418)
            """)
            
            # Create media transfer with separate IDs
            self.conn.execute("""
                INSERT INTO media_transfer 
                (migration_id, photo_transfer_id, video_transfer_id,
                 total_photos, total_videos, total_size_gb, 
                 photo_status, video_status, overall_status, photos_visible_day)
                VALUES ('TEST-MIG-002', 'APL-PHOTO-123', 'APL-VIDEO-456',
                        60238, 2418, 383.0, 
                        'initiated', 'initiated', 'initiated', 4)
            """)
            
            # Update progress with videos
            self.conn.execute("""
                UPDATE media_transfer 
                SET transferred_photos = 16369,
                    transferred_videos = 847,
                    transferred_size_gb = 107.0,
                    photo_status = 'in_progress',
                    video_status = 'in_progress',
                    overall_status = 'in_progress'
                WHERE migration_id = 'TEST-MIG-002'
            """)
            
            # Verify both photos and videos
            result = self.conn.execute("""
                SELECT transferred_photos, transferred_videos, 
                       photo_status, video_status 
                FROM media_transfer 
                WHERE migration_id = 'TEST-MIG-002'
            """).fetchone()
            
            # Clean up
            self.conn.execute("DELETE FROM media_transfer WHERE migration_id = 'TEST-MIG-002'")
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-002'")
            
            success = (result[0] == 16369 and result[1] == 847 and 
                      result[2] == 'in_progress' and result[3] == 'in_progress')
            if success:
                print(f"    Media progress: {result[0]} photos, {result[1]} videos")
            return success
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup anyway
            try:
                self.conn.execute("DELETE FROM media_transfer WHERE migration_id = 'TEST-MIG-002'")
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-002'")
            except:
                pass
            return False
    
    def test_app_setup(self):
        """Test app setup tracking"""
        try:
            # Create migration
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name)
                VALUES ('TEST-MIG-003', 'TestUser')
            """)
            
            # Initialize apps
            apps = [
                (3001, 'WhatsApp', 'messaging'),
                (3002, 'Google Maps', 'location'),
                (3003, 'Venmo', 'payment')
            ]
            
            for id, app, category in apps:
                self.conn.execute(f"""
                    INSERT INTO app_setup 
                    (id, migration_id, app_name, category, setup_status)
                    VALUES ({id}, 'TEST-MIG-003', '{app}', '{category}', 'pending')
                """)
            
            # Update WhatsApp as in progress
            self.conn.execute("""
                UPDATE app_setup 
                SET setup_status = 'in_progress',
                    group_created = true,
                    family_members_connected = 2
                WHERE migration_id = 'TEST-MIG-003' AND app_name = 'WhatsApp'
            """)
            
            # Verify
            count = self.conn.execute("""
                SELECT COUNT(*) FROM app_setup 
                WHERE migration_id = 'TEST-MIG-003'
            """).fetchone()[0]
            
            # Clean up
            self.conn.execute("DELETE FROM app_setup WHERE migration_id = 'TEST-MIG-003'")
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-003'")
            
            print(f"    Initialized {count} apps")
            return count == 3
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup anyway
            try:
                self.conn.execute("DELETE FROM app_setup WHERE migration_id = 'TEST-MIG-003'")
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-003'")
            except:
                pass
            return False
    
    def test_family_app_adoption(self):
        """Test family member app adoption tracking"""
        try:
            # Create migration and family member
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name)
                VALUES ('TEST-MIG-004', 'TestUser')
            """)
            
            self.conn.execute("""
                INSERT INTO family_members (id, migration_id, name, email)
                VALUES (9999, 'TEST-MIG-004', 'TestMember', 'test@example.com')
            """)
            
            # Track app adoption
            adoption_id = 4001
            for app in ['WhatsApp', 'Google Maps', 'Venmo']:
                self.conn.execute(f"""
                    INSERT INTO family_app_adoption 
                    (id, family_member_id, app_name, status)
                    VALUES ({adoption_id}, 9999, '{app}', 'not_started')
                """)
                adoption_id += 1
            
            # Update WhatsApp to configured
            self.conn.execute("""
                UPDATE family_app_adoption 
                SET status = 'configured',
                    configured_at = CURRENT_TIMESTAMP
                WHERE family_member_id = 9999 AND app_name = 'WhatsApp'
            """)
            
            # Verify
            result = self.conn.execute("""
                SELECT status FROM family_app_adoption 
                WHERE family_member_id = 9999 AND app_name = 'WhatsApp'
            """).fetchone()
            
            # Clean up
            self.conn.execute("DELETE FROM family_app_adoption WHERE family_member_id = 9999")
            self.conn.execute("DELETE FROM family_members WHERE id = 9999")
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-004'")
            
            success = result[0] == 'configured'
            if success:
                print(f"    App adoption tracked: WhatsApp = {result[0]}")
            return success
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup anyway
            try:
                self.conn.execute("DELETE FROM family_app_adoption WHERE family_member_id = 9999")
                self.conn.execute("DELETE FROM family_members WHERE id = 9999")
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-004'")
            except:
                pass
            return False
    
    def test_storage_snapshots(self):
        """Test storage snapshots for progress tracking"""
        try:
            # Create migration with baseline
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name, google_photos_baseline_gb)
                VALUES ('TEST-MIG-STORAGE', 'TestUser', 13.88)
            """)
            
            # Add baseline snapshot
            self.conn.execute("""
                INSERT INTO storage_snapshots 
                (migration_id, day_number, google_photos_gb, google_drive_gb, gmail_gb,
                 total_used_gb, storage_growth_gb, percent_complete, is_baseline)
                VALUES ('TEST-MIG-STORAGE', 1, 13.88, 52.52, 33.26, 
                        99.75, 0.0, 0.0, true)
            """)
            
            # Add Day 4 progress snapshot
            self.conn.execute("""
                INSERT INTO storage_snapshots 
                (migration_id, day_number, google_photos_gb, storage_growth_gb, 
                 percent_complete, estimated_photos_transferred, estimated_videos_transferred)
                VALUES ('TEST-MIG-STORAGE', 4, 120.88, 107.0, 
                        28.0, 16369, 847)
            """)
            
            # Verify progress
            result = self.conn.execute("""
                SELECT google_photos_gb, storage_growth_gb, estimated_photos_transferred 
                FROM storage_snapshots 
                WHERE migration_id = 'TEST-MIG-STORAGE' AND day_number = 4
            """).fetchone()
            
            # Clean up
            self.conn.execute("DELETE FROM storage_snapshots WHERE migration_id = 'TEST-MIG-STORAGE'")
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-STORAGE'")
            
            success = (abs(result[0] - 120.88) < 0.01 and abs(result[1] - 107.0) < 0.01 and result[2] == 16369)
            if success:
                print(f"    Storage tracking: {result[1]}GB growth, {result[2]} photos estimated")
            return success
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup
            try:
                self.conn.execute("DELETE FROM storage_snapshots WHERE migration_id = 'TEST-MIG-STORAGE'")
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-STORAGE'")
            except:
                pass
            return False
    
    def test_venmo_teen_setup(self):
        """Test Venmo teen account tracking"""
        try:
            # Create migration and teen family member
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name)
                VALUES ('TEST-MIG-005', 'TestUser')
            """)
            
            self.conn.execute("""
                INSERT INTO family_members (id, migration_id, name, email, age)
                VALUES (8888, 'TEST-MIG-005', 'TeenMember', 'teen@example.com', 15)
            """)
            
            # Create Venmo teen setup
            self.conn.execute("""
                INSERT INTO venmo_setup 
                (id, migration_id, family_member_id, needs_teen_account)
                VALUES (5001, 'TEST-MIG-005', 8888, true)
            """)
            
            # Simulate card activation
            self.conn.execute("""
                UPDATE venmo_setup 
                SET card_arrived_at = CURRENT_TIMESTAMP,
                    card_activated_at = CURRENT_TIMESTAMP,
                    card_last_four = '1234',
                    setup_complete = true
                WHERE family_member_id = 8888
            """)
            
            # Verify
            result = self.conn.execute("""
                SELECT setup_complete, card_last_four 
                FROM venmo_setup 
                WHERE family_member_id = 8888
            """).fetchone()
            
            # Clean up
            self.conn.execute("DELETE FROM venmo_setup WHERE family_member_id = 8888")
            self.conn.execute("DELETE FROM family_members WHERE id = 8888")
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-005'")
            
            success = result[0] == True and result[1] == '1234'
            if success:
                print(f"    Teen card activated: ****{result[1]}")
            return success
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup anyway
            try:
                self.conn.execute("DELETE FROM venmo_setup WHERE family_member_id = 8888")
                self.conn.execute("DELETE FROM family_members WHERE id = 8888")
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-005'")
            except:
                pass
            return False
    
    def test_views(self):
        """Test that views work correctly"""
        try:
            # Create test data
            self.conn.execute("""
                INSERT INTO migration_status (id, user_name, current_phase, overall_progress)
                VALUES ('TEST-MIG-006', 'TestUser', 'family_setup', 45)
            """)
            
            # Test migration_summary view
            result = self.conn.execute("""
                SELECT user_name, current_phase 
                FROM migration_summary 
                WHERE id = 'TEST-MIG-006'
            """).fetchone()
            
            # Clean up
            self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-006'")
            
            success = result and result[0] == 'TestUser'
            if success:
                print(f"    Views working: migration_summary returned data")
            return success
            
        except Exception as e:
            print(f"    Error: {e}")
            # Try cleanup anyway
            try:
                self.conn.execute("DELETE FROM migration_status WHERE id = 'TEST-MIG-006'")
            except:
                pass
            return False
    
    def test_constraints(self):
        """Test database constraints"""
        try:
            # Test CHECK constraint on progress
            try:
                self.conn.execute("""
                    INSERT INTO migration_status (id, user_name, overall_progress)
                    VALUES ('TEST-FAIL', 'TestUser', 150)
                """)
                print("    ❌ CHECK constraint not working (progress > 100 allowed)")
                return False
            except:
                print("    ✓ CHECK constraint working (progress > 100 rejected)")
            
            # Test CHECK constraint on phase
            try:
                self.conn.execute("""
                    INSERT INTO migration_status (id, user_name, current_phase)
                    VALUES ('TEST-FAIL', 'TestUser', 'invalid_phase')
                """)
                print("    ❌ CHECK constraint not working (invalid phase allowed)")
                return False
            except:
                print("    ✓ CHECK constraint working (invalid phase rejected)")
            
            # Test foreign key constraint (intentionally disabled for DuckDB)
            # Foreign keys are removed from schema to allow UPDATE operations
            # due to DuckDB limitation. This is expected behavior.
            try:
                # Create a family member with non-existent migration_id
                self.conn.execute("""
                    INSERT INTO family_members (id, migration_id, name, email)
                    VALUES (99999, 'NONEXISTENT', 'Test', 'test@test.com')
                """)
                # This SHOULD succeed since we removed foreign keys
                self.conn.execute("DELETE FROM family_members WHERE id = 99999")
                print("    ✓ Foreign keys disabled (expected for DuckDB compatibility)")
            except Exception as e:
                print(f"    ❌ Unexpected behavior with foreign keys: {e}")
                return False
            
            return True
            
        except Exception as e:
            print(f"    Unexpected error: {e}")
            return False
    
    def run_all_tests(self):
        """Run all database tests"""
        print("=" * 60)
        print("🧪 Database Test Suite")
        print("=" * 60)
        
        if not self.connect():
            return False
        
        # Run tests in order
        self.test("All tables exist", self.test_all_tables_exist)
        self.test("Migration initialization", self.test_migration_initialization)
        self.test("Family members with emails", self.test_family_members)
        self.test("Media transfer tracking (photos + videos)", self.test_media_transfer)
        self.test("Storage snapshots tracking", self.test_storage_snapshots)
        self.test("App setup tracking", self.test_app_setup)
        self.test("Family app adoption", self.test_family_app_adoption)
        self.test("Venmo teen setup", self.test_venmo_teen_setup)
        self.test("Views functionality", self.test_views)
        self.test("Constraints enforcement", self.test_constraints)
        
        # Summary
        print("\n" + "=" * 60)
        print(f"📊 Test Results Summary")
        print(f"   ✅ Passed: {self.tests_passed}")
        print(f"   ❌ Failed: {self.tests_failed}")
        print(f"   Total: {self.tests_passed + self.tests_failed}")
        
        if self.tests_failed == 0:
            print("\n🎉 All tests passed! Database is ready for use.")
            return True
        else:
            print(f"\n⚠️  {self.tests_failed} test(s) failed. Please review.")
            return False
    
    def __del__(self):
        """Clean up connection"""
        if self.conn:
            self.conn.close()

if __name__ == "__main__":
    tester = DatabaseTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n✅ Database validation complete!")
        print("\nNext steps:")
        print("1. Review test results above")
        print("2. If all tests pass, proceed to implement MCP tools")
        print("3. Run: Update mcp-tools/migration-state/server.py")
    else:
        print("\n❌ Some tests failed. Please review and fix issues.")
        print("   You may need to reinitialize the database:")
        print("   python3 shared/database/scripts/initialize_v2_database.py")
    
    sys.exit(0 if success else 1)