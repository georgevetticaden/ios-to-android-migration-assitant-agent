#!/usr/bin/env python3
"""
Database initialization for DuckDB
Uses direct DuckDB commands without schema complexity
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
    """Initialize the database with simplified approach"""
    
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
    conn = duckdb.connect(str(db_path))
    
    try:
        print("🔨 Creating database tables...")
        
        # Note: DuckDB doesn't need schemas for our use case
        # We'll use table prefixes instead
        
        # 1. Core migration tracking table
        conn.execute("""
            CREATE TABLE migration_status (
                id TEXT PRIMARY KEY DEFAULT ('MIG-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S')),
                user_name TEXT NOT NULL,
                source_device TEXT DEFAULT 'iPhone',
                target_device TEXT DEFAULT 'Galaxy Z Fold 7',
                years_on_ios INTEGER,
                photo_count INTEGER,
                video_count INTEGER,
                storage_gb DECIMAL(10,2),
                family_size INTEGER,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                current_phase TEXT DEFAULT 'initialization',
                overall_progress INTEGER DEFAULT 0,
                completed_at TIMESTAMP,
                CONSTRAINT valid_progress CHECK (overall_progress BETWEEN 0 AND 100),
                CONSTRAINT valid_phase CHECK (current_phase IN ('initialization', 'photo_transfer', 'family_setup', 'validation', 'completed'))
            )
        """)
        print("  ✅ Created table: migration_status")
        
        # 2. Family members table
        conn.execute("""
            CREATE TABLE family_members (
                id INTEGER PRIMARY KEY,
                migration_id TEXT REFERENCES migration_status(id),
                name TEXT NOT NULL,
                role TEXT,
                age INTEGER,
                email TEXT NOT NULL,
                staying_on_ios BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                CONSTRAINT valid_role CHECK (role IN ('spouse', 'child'))
            )
        """)
        print("  ✅ Created table: family_members")
        
        # 3. Photo transfer tracking
        conn.execute("""
            CREATE TABLE photo_transfer (
                transfer_id TEXT PRIMARY KEY DEFAULT ('TRF-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S')),
                migration_id TEXT REFERENCES migration_status(id),
                total_photos INTEGER,
                total_videos INTEGER,
                total_size_gb DECIMAL(10,2),
                transferred_photos INTEGER DEFAULT 0,
                transferred_videos INTEGER DEFAULT 0,
                transferred_size_gb DECIMAL(10,2) DEFAULT 0,
                status TEXT DEFAULT 'pending',
                apple_transfer_initiated TIMESTAMP,
                apple_confirmation_email_received TIMESTAMP,
                photos_visible_day INTEGER,
                estimated_completion_day INTEGER DEFAULT 7,
                daily_transfer_rate INTEGER,
                last_checked_at TIMESTAMP,
                CONSTRAINT valid_status CHECK (status IN ('pending', 'initiated', 'in_progress', 'completed'))
            )
        """)
        print("  ✅ Created table: photo_transfer")
        
        # 4. App setup tracking
        conn.execute("""
            CREATE TABLE app_setup (
                id INTEGER PRIMARY KEY,
                migration_id TEXT REFERENCES migration_status(id),
                app_name TEXT NOT NULL,
                category TEXT,
                setup_status TEXT DEFAULT 'pending',
                group_created BOOLEAN DEFAULT false,
                invitations_sent INTEGER DEFAULT 0,
                family_members_connected INTEGER DEFAULT 0,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                notes TEXT,
                UNIQUE(migration_id, app_name),
                CONSTRAINT valid_app CHECK (app_name IN ('WhatsApp', 'Google Maps', 'Venmo')),
                CONSTRAINT valid_category CHECK (category IN ('messaging', 'location', 'payment')),
                CONSTRAINT valid_status CHECK (setup_status IN ('pending', 'in_progress', 'completed'))
            )
        """)
        print("  ✅ Created table: app_setup")
        
        # 5. Family member app adoption
        conn.execute("""
            CREATE TABLE family_app_adoption (
                id INTEGER PRIMARY KEY,
                family_member_id INTEGER REFERENCES family_members(id),
                app_name TEXT,
                status TEXT DEFAULT 'not_started',
                invitation_sent_at TIMESTAMP,
                invitation_method TEXT DEFAULT 'email',
                installed_at TIMESTAMP,
                configured_at TIMESTAMP,
                UNIQUE(family_member_id, app_name),
                CONSTRAINT valid_app CHECK (app_name IN ('WhatsApp', 'Google Maps', 'Venmo')),
                CONSTRAINT valid_status CHECK (status IN ('not_started', 'invited', 'installed', 'configured'))
            )
        """)
        print("  ✅ Created table: family_app_adoption")
        
        # 6. Daily progress snapshots
        conn.execute("""
            CREATE TABLE daily_progress (
                id INTEGER PRIMARY KEY,
                migration_id TEXT REFERENCES migration_status(id),
                day_number INTEGER NOT NULL,
                date DATE DEFAULT CURRENT_DATE,
                photos_transferred INTEGER,
                videos_transferred INTEGER,
                size_transferred_gb DECIMAL(10,2),
                whatsapp_members_connected INTEGER,
                maps_members_sharing INTEGER,
                venmo_members_active INTEGER,
                key_milestone TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(migration_id, day_number)
            )
        """)
        print("  ✅ Created table: daily_progress")
        
        # 7. Venmo teen account setup
        conn.execute("""
            CREATE TABLE venmo_setup (
                id INTEGER PRIMARY KEY,
                migration_id TEXT REFERENCES migration_status(id),
                family_member_id INTEGER REFERENCES family_members(id),
                needs_teen_account BOOLEAN DEFAULT false,
                account_created_at TIMESTAMP,
                card_ordered_at TIMESTAMP,
                card_arrived_at TIMESTAMP,
                card_activated_at TIMESTAMP,
                card_last_four TEXT,
                setup_complete BOOLEAN DEFAULT false,
                UNIQUE(family_member_id)
            )
        """)
        print("  ✅ Created table: venmo_setup")
        
        print("\n📊 Creating indexes for performance...")
        
        # Create indexes
        indexes = [
            "CREATE INDEX idx_migration_status_phase ON migration_status(current_phase)",
            "CREATE INDEX idx_family_members_migration ON family_members(migration_id)",
            "CREATE INDEX idx_photo_transfer_migration ON photo_transfer(migration_id)",
            "CREATE INDEX idx_app_setup_migration ON app_setup(migration_id)",
            "CREATE INDEX idx_family_adoption_member ON family_app_adoption(family_member_id)",
            "CREATE INDEX idx_daily_progress_migration ON daily_progress(migration_id, day_number)",
            "CREATE INDEX idx_venmo_setup_migration ON venmo_setup(migration_id)"
        ]
        
        for idx_sql in indexes:
            conn.execute(idx_sql)
        print(f"  ✅ Created {len(indexes)} indexes")
        
        print("\n👁️  Creating views for easy querying...")
        
        # Create views
        conn.execute("""
            CREATE VIEW migration_summary AS
            SELECT 
                m.id,
                m.user_name,
                m.current_phase,
                m.overall_progress,
                pt.status as photo_status,
                CASE 
                    WHEN pt.total_photos > 0 
                    THEN pt.transferred_photos || '/' || pt.total_photos 
                    ELSE '0/0' 
                END as photo_progress,
                COUNT(DISTINCT fm.id) as family_members,
                COUNT(DISTINCT CASE WHEN faa.status = 'configured' THEN faa.family_member_id END) as members_configured
            FROM migration_status m
            LEFT JOIN photo_transfer pt ON m.id = pt.migration_id
            LEFT JOIN family_members fm ON m.id = fm.migration_id
            LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
            GROUP BY m.id, m.user_name, m.current_phase, m.overall_progress, pt.status, pt.transferred_photos, pt.total_photos
        """)
        print("  ✅ Created view: migration_summary")
        
        conn.execute("""
            CREATE VIEW family_app_status AS
            SELECT 
                fm.name,
                fm.email,
                MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.status END) as whatsapp,
                MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.status END) as maps,
                MAX(CASE WHEN faa.app_name = 'Venmo' THEN faa.status END) as venmo
            FROM family_members fm
            LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
            GROUP BY fm.id, fm.name, fm.email
        """)
        print("  ✅ Created view: family_app_status")
        
        conn.execute("""
            CREATE VIEW active_migration AS
            SELECT 
                m.*,
                pt.status as photo_transfer_status,
                pt.transferred_photos,
                pt.total_photos,
                COUNT(DISTINCT fm.id) as total_family_members
            FROM migration_status m
            LEFT JOIN photo_transfer pt ON m.id = pt.migration_id
            LEFT JOIN family_members fm ON m.id = fm.migration_id
            WHERE m.completed_at IS NULL
            GROUP BY m.id, m.user_name, m.source_device, m.target_device, m.years_on_ios, 
                     m.photo_count, m.video_count, m.storage_gb, m.family_size, m.started_at,
                     m.current_phase, m.overall_progress, m.completed_at,
                     pt.status, pt.transferred_photos, pt.total_photos
            ORDER BY m.started_at DESC
            LIMIT 1
        """)
        print("  ✅ Created view: active_migration")
        
        print("\n🔍 Verifying database structure...")
        
        # Verify tables
        tables_result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_type = 'BASE TABLE'
            AND table_schema = 'main'
            ORDER BY table_name
        """).fetchall()
        
        tables = [t[0] for t in tables_result]
        print(f"\n📊 Created {len(tables)} tables:")
        for table in tables:
            print(f"  • {table}")
        
        # Verify views
        views_result = conn.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_type = 'VIEW'
            AND table_schema = 'main'
            ORDER BY table_name
        """).fetchall()
        
        views = [v[0] for v in views_result]
        print(f"\n👁️  Created {len(views)} views:")
        for view in views:
            print(f"  • {view}")
        
        # Verify expected tables exist
        expected_tables = [
            'migration_status',
            'family_members', 
            'photo_transfer',
            'app_setup',
            'family_app_adoption',
            'daily_progress',
            'venmo_setup'
        ]
        
        missing_tables = [t for t in expected_tables if t not in tables]
        
        if missing_tables:
            print(f"\n⚠️  Warning: Missing expected tables: {missing_tables}")
            return False
        
        print("\n✅ All expected tables created successfully!")
        
        # Test with a simple query
        conn.execute("SELECT * FROM migration_status WHERE 1=0")
        print("✅ Database is ready for use!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error initializing database: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 iOS to Android Migration Database Initialization")
    print("=" * 60)
    
    success = initialize_database()
    
    if success:
        print("\n🎉 Database initialization complete!")
        print("\nNext steps:")
        print("1. Run the test script: python3 shared/database/tests/test_database.py")
        print("2. Implement MCP tools: Update mcp-tools/migration-state/server.py")
    else:
        print("\n❌ Database initialization failed!")
        sys.exit(1)