#!/usr/bin/env python3.11
"""
Initialize the migration database
Creates all schemas and tables for the iOS to Android migration system
"""

import asyncio
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

from shared.database.migration_db import get_migration_db
from shared.config.settings import get_settings
from shared.utils.logging_config import setup_logging

async def main():
    """Initialize the migration database with all schemas"""
    
    # Set up logging
    logger = setup_logging(name='setup_database')
    
    print("\n" + "="*60)
    print("iOS to Android Migration Database Setup")
    print("="*60)
    
    # Get settings
    settings = get_settings()
    print(f"\nDatabase location: {settings.MIGRATION_DB_PATH}")
    
    # Initialize database
    print("\nInitializing database...")
    db = get_migration_db()
    
    try:
        # Create all schemas
        await db.initialize_schemas()
        print("✅ Database schemas created successfully")
        
        # Verify schemas were created
        with db.get_connection() as conn:
            # Check for schemas
            schemas = conn.execute("""
                SELECT DISTINCT table_schema 
                FROM information_schema.tables 
                WHERE table_schema LIKE '%migration%' 
                   OR table_schema LIKE '%photo%'
                   OR table_schema LIKE '%whatsapp%'
                   OR table_schema LIKE '%family%'
                ORDER BY table_schema
            """).fetchall()
            
            if schemas:
                print("\n📁 Created schemas:")
                for schema in schemas:
                    print(f"  - {schema[0]}")
                    
                    # List tables in each schema
                    tables = conn.execute("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_schema = ?
                        ORDER BY table_name
                    """, (schema[0],)).fetchall()
                    
                    for table in tables:
                        print(f"      • {table[0]}")
            
            # Get database statistics
            stats = await db.get_database_stats()
            print(f"\n📊 Database Statistics:")
            print(f"  - Database size: {stats['database_size_mb']} MB")
            print(f"  - Total migrations: {stats['total_migrations']}")
            print(f"  - Active migrations: {stats['active_migrations']}")
            print(f"  - Total events: {stats['total_events']}")
        
        print("\n✅ Database setup complete!")
        print(f"   Location: {db.db_path}")
        
        # Provide next steps
        print("\n📝 Next Steps:")
        print("1. Configure your .env file with required credentials")
        print("2. Run test_database.py to verify the setup")
        print("3. Start using MCP tools for migration")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error setting up database: {e}")
        logger.error(f"Database setup failed: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)