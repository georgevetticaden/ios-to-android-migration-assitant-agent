#!/usr/bin/env python3
"""
Reset/Clear Database Script
Safely backs up and clears the database for a fresh start
"""

import sys
import os
from pathlib import Path
import shutil
from datetime import datetime
import time

def reset_database(backup=True, force=False):
    """
    Reset the database with optional backup
    
    Args:
        backup: Whether to create a backup before deletion
        force: Skip confirmation prompt
    """
    
    # Database path
    db_path = Path('~/.ios_android_migration/migration.db').expanduser()
    db_dir = db_path.parent
    
    print("🔄 Database Reset Utility")
    print("=" * 50)
    
    # Check if database exists
    if not db_path.exists():
        print("ℹ️  No existing database found at:")
        print(f"   {db_path}")
        print("✅ System is already clean - ready for initialization")
        return True
    
    # Show current database info
    db_size = db_path.stat().st_size / (1024 * 1024)  # Size in MB
    db_modified = datetime.fromtimestamp(db_path.stat().st_mtime)
    
    print(f"📊 Current Database Info:")
    print(f"   Path: {db_path}")
    print(f"   Size: {db_size:.2f} MB")
    print(f"   Last Modified: {db_modified.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check for DBeaver lock
    try:
        # Try to open the file to check if it's locked
        with open(db_path, 'rb'):
            pass
        print("✅ Database is not locked")
    except PermissionError:
        print("⚠️  WARNING: Database appears to be locked!")
        print("   Please close DBeaver or any other database clients")
        response = input("   Continue anyway? (y/n): ").lower()
        if response != 'y':
            print("❌ Reset cancelled")
            return False
    
    # Confirmation prompt (unless forced)
    if not force:
        print("⚠️  This will delete the current database!")
        response = input("   Are you sure you want to continue? (y/n): ").lower()
        if response != 'y':
            print("❌ Reset cancelled")
            return False
    
    # Create backup if requested
    if backup:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_path.with_suffix(f'.backup_{timestamp}.db')
        
        print(f"\n📦 Creating backup...")
        try:
            shutil.copy2(db_path, backup_path)
            backup_size = backup_path.stat().st_size / (1024 * 1024)
            print(f"   ✅ Backup created: {backup_path.name}")
            print(f"   Size: {backup_size:.2f} MB")
            
            # List recent backups
            backups = sorted(db_dir.glob('migration.backup_*.db'))
            if len(backups) > 3:
                print(f"\n   ℹ️  You have {len(backups)} backup files.")
                print("   Recent backups:")
                for backup_file in backups[-3:]:
                    backup_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
                    backup_mb = backup_file.stat().st_size / (1024 * 1024)
                    print(f"     - {backup_file.name} ({backup_mb:.2f} MB, {backup_time.strftime('%Y-%m-%d %H:%M')})")
                    
        except Exception as e:
            print(f"   ❌ Backup failed: {e}")
            response = input("   Continue without backup? (y/n): ").lower()
            if response != 'y':
                print("❌ Reset cancelled")
                return False
    
    # Delete the database
    print(f"\n🗑️  Deleting database...")
    try:
        db_path.unlink()
        print(f"   ✅ Database deleted successfully")
    except Exception as e:
        print(f"   ❌ Failed to delete database: {e}")
        print("   Try closing all database connections and run again")
        return False
    
    # Clean up any temporary files
    print("\n🧹 Cleaning up temporary files...")
    temp_files_deleted = 0
    
    # Remove .wal and .wal-shm files (DuckDB write-ahead log)
    for pattern in ['*.wal', '*.wal-shm', '*.tmp']:
        for temp_file in db_dir.glob(f'migration.db{pattern}'):
            try:
                temp_file.unlink()
                temp_files_deleted += 1
                print(f"   Deleted: {temp_file.name}")
            except:
                pass
    
    if temp_files_deleted > 0:
        print(f"   ✅ Deleted {temp_files_deleted} temporary files")
    else:
        print(f"   ✅ No temporary files found")
    
    # Success message
    print("\n" + "=" * 50)
    print("✅ Database reset complete!")
    print("\nNext steps:")
    print("1. Initialize fresh database:")
    print("   python3 shared/database/scripts/initialize_database.py")
    print("\n2. Run tests:")
    print("   python3 shared/database/tests/test_database.py")
    
    return True

def list_backups():
    """List all existing database backups"""
    db_dir = Path('~/.ios_android_migration').expanduser()
    
    print("\n📋 Database Backups")
    print("=" * 50)
    
    backups = sorted(db_dir.glob('migration.backup_*.db'))
    
    if not backups:
        print("No backups found")
        return
    
    total_size = 0
    print(f"Found {len(backups)} backup(s):\n")
    
    for i, backup_file in enumerate(backups, 1):
        backup_time = datetime.fromtimestamp(backup_file.stat().st_mtime)
        backup_size = backup_file.stat().st_size / (1024 * 1024)
        total_size += backup_size
        
        # Extract timestamp from filename
        timestamp_str = backup_file.stem.split('backup_')[1]
        
        print(f"{i}. {backup_file.name}")
        print(f"   Size: {backup_size:.2f} MB")
        print(f"   Created: {backup_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print()
    
    print(f"Total backup size: {total_size:.2f} MB")
    
    if len(backups) > 5:
        print("\n⚠️  You have many backups. Consider cleaning old ones:")
        print("   rm ~/.ios_android_migration/migration.backup_*.db")

def clean_old_backups(keep_recent=3):
    """Remove old backup files, keeping the most recent ones"""
    db_dir = Path('~/.ios_android_migration').expanduser()
    
    backups = sorted(db_dir.glob('migration.backup_*.db'))
    
    if len(backups) <= keep_recent:
        print(f"Only {len(backups)} backups found, keeping all")
        return
    
    to_delete = backups[:-keep_recent]
    
    print(f"\n🧹 Cleaning old backups (keeping {keep_recent} most recent)")
    for backup_file in to_delete:
        try:
            backup_size = backup_file.stat().st_size / (1024 * 1024)
            backup_file.unlink()
            print(f"   Deleted: {backup_file.name} ({backup_size:.2f} MB)")
        except Exception as e:
            print(f"   Failed to delete {backup_file.name}: {e}")
    
    print(f"✅ Deleted {len(to_delete)} old backups")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Reset the migration database')
    parser.add_argument('--no-backup', action='store_true', 
                       help='Skip creating a backup')
    parser.add_argument('--force', '-f', action='store_true',
                       help='Skip confirmation prompts')
    parser.add_argument('--list-backups', action='store_true',
                       help='List existing backups')
    parser.add_argument('--clean-backups', action='store_true',
                       help='Remove old backups, keeping 3 most recent')
    
    args = parser.parse_args()
    
    if args.list_backups:
        list_backups()
    elif args.clean_backups:
        clean_old_backups()
    else:
        success = reset_database(backup=not args.no_backup, force=args.force)
        sys.exit(0 if success else 1)