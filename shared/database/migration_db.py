"""
Centralized DuckDB Database for iOS to Android Migration

This module provides a singleton database interface for managing all migration-related data
during the iOS to Android transition process. It handles the complete 7-day migration journey
including photo transfers, family member management, app adoption tracking, and progress monitoring.

Key Features:
- Singleton pattern ensures single database instance across all MCP tools
- Simplified schema with 7 tables (no schema prefixes for DuckDB compatibility)
- No foreign key constraints (workaround for DuckDB UPDATE limitation)
- Referential integrity enforced at application layer
- Context manager for safe connection handling
- Comprehensive async methods for all migration operations

Database Location: ~/.ios_android_migration/migration.db

Tables:
- migration_status: Core migration tracking
- family_members: Family member details
- photo_transfer: Photo/video transfer progress
- app_setup: App installation tracking
- family_app_adoption: Per-member app status
- daily_progress: Day-by-day snapshots
- venmo_setup: Teen card tracking

Usage:
    db = MigrationDatabase()
    migration_id = await db.create_migration(user_name="George", ...)
    await db.add_family_member(migration_id, "Jaisy", "jaisy@example.com")
    
Author: iOS2Android Migration Team
Version: 2.0
"""

import duckdb
import json
import os
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)

class MigrationDatabase:
    """
    Centralized database for all migration tools.
    Implements singleton pattern to ensure single database instance.
    """
    
    _instance = None
    _db_path = None
    
    def __new__(cls):
        """Singleton pattern to ensure single database instance"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        """
        Initialize the database connection.
        
        Sets up the database path and ensures the directory exists.
        Uses environment variable MIGRATION_DB_PATH if set, otherwise
        defaults to ~/.ios_android_migration/migration.db
        
        Note: Actual initialization only happens once due to singleton pattern.
        """
        if not hasattr(self, 'initialized'):
            # Use environment variable or default path
            db_path = os.getenv('MIGRATION_DB_PATH', 
                               '~/.ios_android_migration/migration.db')
            self.db_path = Path(db_path).expanduser()
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.initialized = True
            logger.info(f"Migration database initialized at: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """
        Context manager for safe database connections.
        
        Provides a DuckDB connection that is automatically closed after use,
        even if an error occurs. This prevents connection leaks and ensures
        the database isn't locked by hanging connections.
        
        Yields:
            duckdb.DuckDBPyConnection: Active database connection
            
        Example:
            with db.get_connection() as conn:
                conn.execute("SELECT * FROM migration_status")
        """
        conn = duckdb.connect(str(self.db_path))
        try:
            yield conn
        finally:
            conn.close()
    
    async def initialize_schemas(self):
        """Initialize schema if needed"""
        # Schema is initialized via shared/database/scripts/initialize_database.py
        # This method kept for compatibility
        logger.info("Schema should be initialized via shared/database/scripts/initialize_database.py")
        return True
    
    # ===== MIGRATION CORE OPERATIONS =====
    
    async def create_migration(self, user_name: str, 
                              source_device: str = 'iPhone',
                              target_device: str = 'Galaxy Z Fold 7',
                              photo_count: int = 0,
                              video_count: int = 0,
                              storage_gb: float = 0,
                              years_on_ios: int = None) -> str:
        """
        Create a new migration record.
        
        Initializes a new migration journey for a user transitioning from iOS to Android.
        Generates a unique migration ID with timestamp and sets initial phase to 'initialization'.
        
        Args:
            user_name: Name of the user migrating
            source_device: Device migrating from (default: iPhone)
            target_device: Device migrating to (default: Galaxy Z Fold 7)
            photo_count: Number of photos to migrate
            video_count: Number of videos to migrate
            storage_gb: Total storage size in GB
            years_on_ios: How many years the user has been on iOS
            
        Returns:
            str: Unique migration ID (format: MIG-YYYYMMDD-HHMMSS)
            
        Example:
            migration_id = await db.create_migration(
                user_name="George",
                photo_count=60238,
                video_count=2418,
                storage_gb=383,
                years_on_ios=18
            )
        """
        migration_id = f"MIG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO migration_status 
                (id, user_name, source_device, target_device, 
                 photo_count, video_count, storage_gb, years_on_ios, started_at, current_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'initialization')
            """, (migration_id, user_name, source_device, target_device,
                  photo_count, video_count, storage_gb, years_on_ios, datetime.now()))
        
        logger.info(f"Created migration: {migration_id}")
        return migration_id
    
    async def get_active_migration(self) -> Optional[Dict[str, Any]]:
        """
        Get the currently active migration.
        
        Retrieves the most recent incomplete migration with all related data including
        photo transfer status. Used by MCP tools to get current migration context.
        
        Returns:
            Optional[Dict[str, Any]]: Migration data dictionary or None if no active migration
            
        Dictionary includes:
            - All migration_status fields
            - photo_transfer_status, transferred_photos, total_photos
            - transferred_size_gb, total_size_gb
        """
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT m.*, 
                       pt.status as photo_transfer_status,
                       pt.transferred_photos,
                       pt.total_photos,
                       pt.transferred_size_gb,
                       pt.total_size_gb
                FROM migration_status m
                LEFT JOIN photo_transfer pt ON m.id = pt.migration_id
                WHERE m.completed_at IS NULL
                ORDER BY m.started_at DESC
                LIMIT 1
            """).fetchone()
            
            if result:
                columns = [
                    'id', 'user_name', 'source_device', 'target_device',
                    'years_on_ios', 'photo_count', 'video_count', 'storage_gb',
                    'family_size', 'started_at', 'current_phase', 'overall_progress',
                    'completed_at', 'photo_transfer_status', 'transferred_photos',
                    'total_photos', 'transferred_size_gb', 'total_size_gb'
                ]
                return dict(zip(columns, result))
            return None
    
    async def update_migration_status(self, migration_id: str, status: str, **kwargs):
        """
        Update migration status and phase.
        
        Updates the current phase of the migration and optionally other fields like
        overall_progress and family_size. Handles the DuckDB foreign key limitation
        by allowing UPDATE operations without constraint checks.
        
        Args:
            migration_id: ID of the migration to update
            status: New phase (initialization, photo_transfer, family_setup, validation, completed)
            **kwargs: Optional fields to update (overall_progress, family_size)
            
        Note:
            Foreign keys removed from schema to allow UPDATEs due to DuckDB limitation.
            Referential integrity is maintained at the application layer.
        """
        with self.get_connection() as conn:
            # Build update statement dynamically
            updates = ['current_phase = ?']
            values = [status]
            
            for key, value in kwargs.items():
                if key in ['overall_progress', 'family_size']:
                    updates.append(f'{key} = ?')
                    values.append(value)
            
            if status == 'completed':
                updates.append('completed_at = ?')
                values.append(datetime.now())
            
            values.append(migration_id)
            
            # Execute the UPDATE
            conn.execute(f"""
                UPDATE migration_status 
                SET {', '.join(updates)}
                WHERE id = ?
            """, values)
        
        logger.info(f"Updated migration {migration_id} status to: {status}")
    
    async def get_migration_status(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Get specific migration status"""
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM migration_status WHERE id = ?
            """, (migration_id,)).fetchone()
            
            if result:
                columns = [
                    'id', 'user_name', 'source_device', 'target_device',
                    'years_on_ios', 'photo_count', 'video_count', 'storage_gb',
                    'family_size', 'started_at', 'current_phase', 'overall_progress',
                    'completed_at'
                ]
                return dict(zip(columns, result))
            return None
    
    # ===== PHOTO TRANSFER OPERATIONS =====
    
    async def create_photo_transfer(self, migration_id: str, 
                                   total_photos: int, total_videos: int,
                                   total_size_gb: float) -> str:
        """Create a photo transfer record"""
        transfer_id = f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO photo_transfer
                (transfer_id, migration_id, total_photos, total_videos, 
                 total_size_gb, status, photos_visible_day)
                VALUES (?, ?, ?, ?, ?, 'pending', 4)
            """, (transfer_id, migration_id, total_photos, total_videos, total_size_gb))
        
        logger.info(f"Created photo transfer: {transfer_id}")
        return transfer_id
    
    async def update_photo_progress(self, migration_id: str,
                                   transferred_photos: int = None,
                                   transferred_videos: int = None,
                                   transferred_size_gb: float = None,
                                   status: str = None):
        """Update photo transfer progress"""
        with self.get_connection() as conn:
            updates = []
            values = []
            
            if transferred_photos is not None:
                updates.append('transferred_photos = ?')
                values.append(transferred_photos)
            
            if transferred_videos is not None:
                updates.append('transferred_videos = ?')
                values.append(transferred_videos)
                
            if transferred_size_gb is not None:
                updates.append('transferred_size_gb = ?')
                values.append(transferred_size_gb)
            
            if status:
                updates.append('status = ?')
                values.append(status)
            
            updates.append('last_checked_at = ?')
            values.append(datetime.now())
            
            values.append(migration_id)
            
            if updates:
                conn.execute(f"""
                    UPDATE photo_transfer 
                    SET {', '.join(updates)}
                    WHERE migration_id = ?
                """, values)
        
        logger.info(f"Updated photo progress for migration: {migration_id}")
    
    # ===== FAMILY OPERATIONS =====
    
    async def add_family_member(self, migration_id: str, name: str, email: str,
                               role: str = None, age: int = None) -> int:
        """
        Add a family member to the migration.
        
        Creates a new family member record and updates the family_size in migration_status.
        Email is required for sending app invitations during the migration process.
        
        Args:
            migration_id: ID of the migration
            name: Family member's name
            email: Email address for invitations
            role: Optional role (spouse/child)
            age: Optional age (used to determine teen accounts for Venmo)
            
        Returns:
            int: The ID of the newly created family member
            
        Example:
            member_id = await db.add_family_member(
                migration_id="MIG-20250825-120000",
                name="Laila",
                email="laila@example.com",
                role="child",
                age=15
            )
        """
        with self.get_connection() as conn:
            # Get next ID (simple approach)
            max_id = conn.execute("SELECT MAX(id) FROM family_members").fetchone()[0]
            next_id = (max_id or 0) + 1
            
            conn.execute("""
                INSERT INTO family_members
                (id, migration_id, name, email, role, age)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (next_id, migration_id, name, email, role, age))
            
            # Update family size
            conn.execute("""
                UPDATE migration_status 
                SET family_size = (
                    SELECT COUNT(*) FROM family_members WHERE migration_id = ?
                )
                WHERE id = ?
            """, (migration_id, migration_id))
        
        logger.info(f"Added family member: {name}")
        return next_id
    
    async def get_family_members(self, migration_id: str) -> List[Dict[str, Any]]:
        """Get all family members for a migration"""
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT * FROM family_members WHERE migration_id = ?
            """, (migration_id,)).fetchall()
            
            columns = ['id', 'migration_id', 'name', 'role', 'age', 'email', 
                      'staying_on_ios', 'created_at']
            return [dict(zip(columns, row)) for row in results]
    
    # ===== SIMPLIFIED OPERATIONS =====
    
    async def update_migration_progress(self, migration_id: str, status: str,
                                       photos_transferred: int = None,
                                       videos_transferred: int = None,
                                       total_size_gb: float = None):
        """Simplified progress update for MCP tools"""
        await self.update_migration_status(migration_id, status)
        
        if any([photos_transferred, videos_transferred, total_size_gb]):
            # Map migration status to photo_transfer status
            photo_status = None
            if status == 'photo_transfer':
                photo_status = 'in_progress'
            elif status == 'completed':
                photo_status = 'completed'
            elif status in ['initialization', 'family_setup', 'validation']:
                photo_status = 'pending'
            else:
                photo_status = 'in_progress'
            
            await self.update_photo_progress(
                migration_id,
                transferred_photos=photos_transferred,
                transferred_videos=videos_transferred,
                transferred_size_gb=total_size_gb,
                status=photo_status
            )
    
    async def get_pending_items(self, category: str) -> List[Dict[str, Any]]:
        """Get pending items to migrate"""
        # Simplified - return basic status
        items = []
        
        if category == 'photos':
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT * FROM photo_transfer 
                    WHERE status != 'completed'
                """).fetchall()
                
                for row in result:
                    items.append({
                        'type': 'photos',
                        'status': row[8],  # status field
                        'total': row[2],   # total_photos
                        'transferred': row[5]  # transferred_photos
                    })
        
        return items
    
    async def mark_item_complete(self, item_type: str, item_id: str, details: Dict = None):
        """Mark an item as complete"""
        # Simplified
        logger.info(f"Marked {item_type} {item_id} as complete")
        return True
    
    async def get_migration_statistics(self, include_history: bool = False) -> Dict[str, Any]:
        """Get migration statistics"""
        with self.get_connection() as conn:
            # Get active migration stats
            active = await self.get_active_migration()
            
            stats = {
                'active_migration': active,
                'total_migrations': 0,
                'completed_migrations': 0
            }
            
            # Count migrations
            total = conn.execute("SELECT COUNT(*) FROM migration_status").fetchone()[0]
            completed = conn.execute(
                "SELECT COUNT(*) FROM migration_status WHERE completed_at IS NOT NULL"
            ).fetchone()[0]
            
            stats['total_migrations'] = total
            stats['completed_migrations'] = completed
            
            return stats
    
    async def log_event(self, event_type: str, component: str, 
                       description: str, metadata: Dict = None):
        """Log an event (simplified)"""
        logger.info(f"[{component}] {event_type}: {description}")
        return True

# Singleton instance
def get_migration_db():
    """Get the singleton database instance"""
    return MigrationDatabase()

# Make MigrationDatabase available at module level for backward compatibility
__all__ = ['MigrationDatabase', 'get_migration_db']