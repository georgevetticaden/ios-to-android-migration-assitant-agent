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
- migration_status: Core migration tracking with storage baselines
- family_members: Family member details
- media_transfer: Photo AND video transfer progress (formerly photo_transfer)
- app_setup: App installation tracking
- family_app_adoption: Per-member app status
- daily_progress: Day-by-day snapshots with video metrics
- venmo_setup: Teen card tracking
- storage_snapshots: Google One storage tracking for progress monitoring

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
                              google_photos_baseline_gb: float = 0.0,
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
                 photo_count, video_count, total_icloud_storage_gb,
                 icloud_photo_storage_gb, icloud_video_storage_gb,
                 google_photos_baseline_gb, years_on_ios, started_at, current_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'initialization')
            """, (migration_id, user_name, source_device, target_device,
                  photo_count, video_count, storage_gb,
                  storage_gb * 0.7,  # Estimate 70% for photos
                  storage_gb * 0.3,  # Estimate 30% for videos
                  google_photos_baseline_gb,  # Google Photos baseline storage
                  years_on_ios, datetime.now()))
        
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
                       mt.photo_status,
                       mt.video_status,
                       mt.overall_status,
                       mt.transferred_photos,
                       mt.transferred_videos,
                       mt.total_photos,
                       mt.total_videos,
                       mt.transferred_size_gb,
                       mt.total_size_gb
                FROM migration_status m
                LEFT JOIN media_transfer mt ON m.id = mt.migration_id
                WHERE m.completed_at IS NULL
                ORDER BY m.started_at DESC
                LIMIT 1
            """).fetchone()
            
            if result:
                # Note: migration_status has more columns now with storage baselines
                columns = [
                    'id', 'user_name', 'source_device', 'target_device',
                    'years_on_ios', 'photo_count', 'video_count', 'total_icloud_storage_gb',
                    'icloud_photo_storage_gb', 'icloud_video_storage_gb', 'album_count',
                    'google_storage_total_gb', 'google_photos_baseline_gb', 'google_drive_baseline_gb',
                    'gmail_baseline_gb', 'family_size', 'started_at', 'current_phase', 
                    'overall_progress', 'completed_at',
                    'photo_status', 'video_status', 'overall_status',
                    'transferred_photos', 'transferred_videos',
                    'total_photos', 'total_videos',
                    'transferred_size_gb', 'total_size_gb'
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
    
    # ===== MEDIA TRANSFER OPERATIONS =====
    
    async def create_media_transfer(self, migration_id: str, 
                                   total_photos: int, total_videos: int,
                                   total_size_gb: float) -> str:
        """Create a media transfer record for both photos and videos"""
        transfer_id = f"TRF-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO media_transfer
                (transfer_id, migration_id, total_photos, total_videos, 
                 total_size_gb, photo_status, video_status, overall_status, photos_visible_day)
                VALUES (?, ?, ?, ?, ?, 'pending', 'pending', 'pending', 4)
            """, (transfer_id, migration_id, total_photos, total_videos, total_size_gb))
        
        logger.info(f"Created media transfer: {transfer_id}")
        return transfer_id
    
    # Backward compatibility alias
    async def create_photo_transfer(self, migration_id: str, 
                                   total_photos: int, total_videos: int,
                                   total_size_gb: float) -> str:
        """Backward compatibility wrapper for create_media_transfer"""
        return await self.create_media_transfer(migration_id, total_photos, total_videos, total_size_gb)
    
    async def update_media_progress(self, migration_id: str,
                                   transferred_photos: int = None,
                                   transferred_videos: int = None,
                                   transferred_size_gb: float = None,
                                   photo_status: str = None,
                                   video_status: str = None,
                                   overall_status: str = None):
        """Update media transfer progress for photos and videos separately"""
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
            
            if photo_status:
                updates.append('photo_status = ?')
                values.append(photo_status)
            
            if video_status:
                updates.append('video_status = ?')
                values.append(video_status)
                
            if overall_status:
                updates.append('overall_status = ?')
                values.append(overall_status)
            
            updates.append('last_progress_check = ?')
            values.append(datetime.now())
            
            values.append(migration_id)
            
            if updates:
                conn.execute(f"""
                    UPDATE media_transfer 
                    SET {', '.join(updates)}
                    WHERE migration_id = ?
                """, values)
        
        logger.info(f"Updated media progress for migration: {migration_id}")
    
    # Backward compatibility alias
    async def update_photo_progress(self, migration_id: str,
                                   transferred_photos: int = None,
                                   transferred_videos: int = None,
                                   transferred_size_gb: float = None,
                                   status: str = None):
        """Backward compatibility wrapper for update_media_progress"""
        # Map old status to new separate statuses
        photo_status = status
        video_status = status
        overall_status = status
        return await self.update_media_progress(
            migration_id, transferred_photos, transferred_videos, 
            transferred_size_gb, photo_status, video_status, overall_status
        )
    
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
            # Map migration status to media_transfer statuses
            media_status = None
            if status == 'media_transfer':
                media_status = 'in_progress'
            elif status == 'completed':
                media_status = 'completed'
            elif status in ['initialization', 'family_setup', 'validation']:
                media_status = 'pending'
            else:
                media_status = 'in_progress'
            
            await self.update_media_progress(
                migration_id,
                transferred_photos=photos_transferred,
                transferred_videos=videos_transferred,
                transferred_size_gb=total_size_gb,
                photo_status=media_status,
                video_status=media_status,
                overall_status=media_status
            )
    
    async def get_pending_items(self, category: str) -> List[Dict[str, Any]]:
        """Get pending items to migrate"""
        # Simplified - return basic status
        items = []
        
        if category == 'photos':
            with self.get_connection() as conn:
                result = conn.execute("""
                    SELECT * FROM media_transfer 
                    WHERE overall_status != 'completed'
                """).fetchall()
                
                for row in result:
                    items.append({
                        'type': 'photos',
                        'photo_status': row[7],  # photo_status field
                        'video_status': row[8],  # video_status field
                        'overall_status': row[9],  # overall_status field
                        'total_photos': row[4],   # total_photos
                        'total_videos': row[5],   # total_videos
                        'transferred_photos': row[10],  # transferred_photos
                        'transferred_videos': row[11]   # transferred_videos
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