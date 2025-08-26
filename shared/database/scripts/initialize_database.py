#!/usr/bin/env python3
"""
Database Initialization Script for iOS to Android Migration v2.0

This script initializes the DuckDB database with the enhanced schema supporting
video transfers and storage-based progress tracking for the 7-day migration demo.

Key Features:
- Creates 8 tables including new storage_snapshots for Google One tracking
- Enhanced media_transfer table (formerly photo_transfer) with video support
- Storage baseline tracking in migration_status
- Creates 8 performance indexes
- Creates 4 views including daily_progress_summary
- Backs up existing database before recreation
- Validates schema after creation

Schema Changes in v2.0:
- photo_transfer → media_transfer with separate photo/video tracking
- Added storage_snapshots table for Google One progress monitoring
- Enhanced migration_status with iCloud and Google storage baselines
- Added video-specific fields throughout

Database Location: ~/.ios_android_migration/migration.db

Usage:
    python3 initialize_database.py
    
This should be run once during initial setup or when resetting the database.
The migration-state MCP server will use this database for all operations.

Author: iOS2Android Migration Team
Version: 2.0 (Video & Storage Support)
"""

import sys
import os
from pathlib import Path
import duckdb
from datetime import datetime
import shutil

# Add project root to path if needed
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def initialize_database():
    """
    Initialize the DuckDB database with v2.0 schema from migration_schema.sql.
    
    This function performs the following operations:
    1. Creates database directory if it doesn't exist
    2. Backs up existing database (if present) with timestamp
    3. Removes old database file
    4. Applies the complete schema from migration_schema.sql
    5. Validates the schema was created correctly
    
    Tables Created (8):
    - migration_status: Core migration tracking with storage baselines
    - family_members: Family member details
    - media_transfer: Photo AND video transfer progress (was photo_transfer)
    - app_setup: App installation tracking
    - family_app_adoption: Per-member app status
    - daily_progress: Day-by-day snapshots with video metrics
    - venmo_setup: Teen card tracking
    - storage_snapshots: NEW - Google One storage tracking
    
    Indexes Created (8):
    - One index per table on the most commonly queried fields
    
    Views Created (4):
    - migration_summary: Overall migration status with video support
    - family_app_status: Family app adoption matrix
    - active_migration: Current active migration with storage tracking
    - daily_progress_summary: NEW - Day-specific status messages
    
    Returns:
        bool: True if initialization successful, False otherwise
    """
    
    # Database path
    db_path = Path('~/.ios_android_migration/migration.db').expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Backup existing database if it exists
    if db_path.exists():
        backup_path = db_path.with_suffix(f'.backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db')
        print(f"📦 Backing up existing database to: {backup_path}")
        shutil.copy2(db_path, backup_path)
        print(f"🗑️  Removing old database: {db_path}")
        db_path.unlink()
    
    print(f"🔗 Creating fresh database: {db_path}")
    
    # Read the schema file
    schema_file = Path(__file__).parent.parent / 'schemas' / 'migration_schema.sql'
    if not schema_file.exists():
        print(f"❌ Schema file not found: {schema_file}")
        return False
        
    print(f"📄 Reading schema from: {schema_file}")
    with open(schema_file, 'r') as f:
        schema_sql = f.read()
    
    # Connect to database
    conn = duckdb.connect(str(db_path))
    
    try:
        print("🔨 Applying migration_schema.sql v2.0...")
        
        # Split the schema into individual statements
        # DuckDB can handle multiple statements but let's be explicit
        statements = []
        current_statement = []
        
        for line in schema_sql.split('\n'):
            # Skip comments and empty lines
            if line.strip().startswith('--') or not line.strip():
                continue
            
            current_statement.append(line)
            
            # If line ends with semicolon, we have a complete statement
            if line.strip().endswith(';'):
                statement = '\n'.join(current_statement)
                if statement.strip():
                    statements.append(statement)
                current_statement = []
        
        # Execute each statement
        tables_created = 0
        indexes_created = 0
        views_created = 0
        
        for statement in statements:
            try:
                conn.execute(statement)
                
                # Track what was created
                statement_upper = statement.upper()
                if 'CREATE TABLE' in statement_upper:
                    # Extract table name
                    if 'migration_status' in statement:
                        print("  ✅ Created table: migration_status (with storage baselines)")
                    elif 'media_transfer' in statement:
                        print("  ✅ Created table: media_transfer (with video support)")
                    elif 'storage_snapshots' in statement:
                        print("  ✅ Created table: storage_snapshots (NEW)")
                    elif 'daily_progress' in statement:
                        print("  ✅ Created table: daily_progress (enhanced)")
                    elif 'family_members' in statement:
                        print("  ✅ Created table: family_members")
                    elif 'app_setup' in statement:
                        print("  ✅ Created table: app_setup")
                    elif 'family_app_adoption' in statement:
                        print("  ✅ Created table: family_app_adoption")
                    elif 'venmo_setup' in statement:
                        print("  ✅ Created table: venmo_setup")
                    tables_created += 1
                elif 'CREATE INDEX' in statement_upper:
                    indexes_created += 1
                elif 'CREATE VIEW' in statement_upper:
                    if 'daily_progress_summary' in statement:
                        print("  ✅ Created view: daily_progress_summary (NEW)")
                    elif 'migration_summary' in statement:
                        print("  ✅ Created view: migration_summary (video support)")
                    elif 'active_migration' in statement:
                        print("  ✅ Created view: active_migration (storage tracking)")
                    elif 'family_app_status' in statement:
                        print("  ✅ Created view: family_app_status")
                    views_created += 1
            except Exception as e:
                # Ignore DROP statements that might fail
                if not statement.upper().startswith('DROP'):
                    print(f"  ⚠️ Warning executing statement: {e}")
        
        print(f"\n📊 Created {tables_created} tables")
        print(f"📈 Created {indexes_created} indexes")
        print(f"👁️  Created {views_created} views")
        
        # Verify the schema
        print("\n🔍 Verifying database structure...")
        
        # Check tables
        tables = conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'main' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """).fetchall()
        
        expected_tables = [
            'app_setup', 'daily_progress', 'family_app_adoption', 
            'family_members', 'media_transfer', 'migration_status', 
            'storage_snapshots', 'venmo_setup'
        ]
        
        actual_tables = [t[0] for t in tables]
        
        print(f"\n📊 Created {len(actual_tables)} tables:")
        for table in actual_tables:
            marker = "✅" if table in expected_tables else "❓"
            special = ""
            if table == 'media_transfer':
                special = " (formerly photo_transfer)"
            elif table == 'storage_snapshots':
                special = " (NEW in v2.0)"
            print(f"  {marker} {table}{special}")
        
        # Check views
        views = conn.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'main' AND table_type = 'VIEW'
            ORDER BY table_name
        """).fetchall()
        
        print(f"\n👁️  Created {len(views)} views:")
        for view in views:
            special = ""
            if view[0] == 'daily_progress_summary':
                special = " (NEW in v2.0)"
            print(f"  • {view[0]}{special}")
        
        # Check if all expected tables exist
        missing = [t for t in expected_tables if t not in actual_tables]
        if missing:
            print(f"\n❌ Missing tables: {missing}")
            return False
        
        print("\n✅ All expected tables created successfully!")
        print("✅ Database is ready for video and storage tracking!")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        conn.close()
        return False

def main():
    """Main entry point for the script"""
    print("🚀 iOS to Android Migration Database Initialization v2.0")
    print("=" * 60)
    
    success = initialize_database()
    
    if success:
        print("\n🎉 Database initialization complete!")
        print("\nNext steps:")
        print("1. Run the test script: python3 shared/database/tests/test_database.py")
        print("2. The database now supports:")
        print("   • Separate photo and video transfer tracking")
        print("   • Google One storage-based progress monitoring")
        print("   • Enhanced daily progress with video metrics")
        print("   • Storage baselines for accurate calculations")
    else:
        print("\n❌ Database initialization failed!")
        print("Please check the error messages above and try again.")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())