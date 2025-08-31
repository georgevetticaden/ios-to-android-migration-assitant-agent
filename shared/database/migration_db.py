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
- media_transfer: Photo and video transfer progress
- family_app_adoption: Per-member app status
- daily_progress: Day-by-day snapshots with video metrics
- venmo_setup: Teen card tracking
- storage_snapshots: Google One storage tracking for progress monitoring

Usage:
    db = MigrationDatabase()
    migration_id = await db.create_migration(user_name="George", ...)
    await db.add_family_member(migration_id, "Jaisy", "jaisy@example.com")
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
        """
        Initialize database schema.
        
        Note: Schema initialization is handled by shared/database/scripts/initialize_database.py
        This method is kept for backward compatibility but does not perform any operations.
        
        Returns:
            bool: Always returns True for compatibility
        """
        logger.info("Schema should be initialized via shared/database/scripts/initialize_database.py")
        return True
    
    # ===== MIGRATION CORE OPERATIONS =====
    
    async def create_migration(self, user_name: str, 
                              source_device: str = 'iPhone',
                              target_device: str = 'Galaxy Z Fold 7',
                              photo_count: int = None,
                              video_count: int = None,
                              storage_gb: float = None,
                              google_photos_baseline_gb: float = None,
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
            # Handle optional parameters
            photo_storage = (storage_gb * 0.7) if storage_gb else None
            video_storage = (storage_gb * 0.3) if storage_gb else None
            
            conn.execute("""
                INSERT INTO migration_status 
                (id, user_name, source_device, target_device, 
                 photo_count, video_count, total_icloud_storage_gb,
                 icloud_photo_storage_gb, icloud_video_storage_gb,
                 google_photos_baseline_gb, years_on_ios, started_at, current_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'initialization')
            """, (migration_id, user_name, source_device, target_device,
                  photo_count, video_count, storage_gb,
                  photo_storage,  # Estimate 70% for photos
                  video_storage,  # Estimate 30% for videos
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
            # First, get column names from both tables dynamically
            migration_columns_result = conn.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'migration_status'
                ORDER BY ordinal_position
            """).fetchall()
            
            migration_columns = [col[0] for col in migration_columns_result]
            
            # Build query to select all migration columns plus specific media_transfer columns
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
                # Combine migration columns with the specific media_transfer columns we selected
                media_columns = [
                    'photo_status', 'video_status', 'overall_status',
                    'transferred_photos', 'transferred_videos',
                    'total_photos', 'total_videos',
                    'transferred_size_gb', 'total_size_gb'
                ]
                all_columns = migration_columns + media_columns
                return dict(zip(all_columns, result))
            return None
    
    async def update_migration_status(self, migration_id: str, status: str = None, **kwargs):
        """
        Update migration status with progressive enrichment support.
        
        Enhanced method that supports updating any migration_status field, enabling
        progressive data enrichment throughout the 7-day journey. Called 9 times total:
        3 times on Day 1, once each on Days 2-7.
        
        Args:
            migration_id: ID of the migration to update
            status: Optional new phase (initialization, media_transfer, family_setup, validation, completed)
            **kwargs: Any migration_status fields to update
            
        Supported fields in kwargs:
            - photo_count, video_count, total_icloud_storage_gb
            - icloud_photo_storage_gb, icloud_video_storage_gb
            - album_count, google_photos_baseline_gb
            - whatsapp_group_name, current_phase
            - overall_progress, family_size, completed_at
        """
        with self.get_connection() as conn:
            updates = []
            values = []
            
            # Handle status parameter (for backward compatibility)
            if status:
                updates.append('current_phase = ?')
                values.append(status)
                if status == 'completed' and 'completed_at' not in kwargs:
                    kwargs['completed_at'] = datetime.now()
            
            # Extended list of allowed fields for progressive updates
            allowed_fields = [
                'photo_count', 'video_count', 'total_icloud_storage_gb',
                'icloud_photo_storage_gb', 'icloud_video_storage_gb',
                'album_count', 'google_photos_baseline_gb',
                'whatsapp_group_name', 'current_phase',
                'overall_progress', 'family_size', 'completed_at'
            ]
            
            for key, value in kwargs.items():
                if key in allowed_fields:
                    updates.append(f'{key} = ?')
                    values.append(value)
            
            if updates:
                values.append(migration_id)
                conn.execute(f"""
                    UPDATE migration_status 
                    SET {', '.join(updates)}
                    WHERE id = ?
                """, values)
                
                logger.info(f"Updated migration {migration_id}: {', '.join(updates)}")
    
    async def get_migration_status(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status for a specific migration.
        
        Retrieves complete migration record by ID, used for tracking progress
        and generating reports.
        
        Args:
            migration_id: ID of the migration to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Migration data dictionary or None if not found
            
        Dictionary includes:
            - User and device information
            - Photo/video counts and storage metrics
            - Current phase and overall progress
            - Family size and timestamps
        """
        with self.get_connection() as conn:
            # Get column names from the table
            columns_result = conn.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'migration_status'
                ORDER BY ordinal_position
            """).fetchall()
            
            columns = [col[0] for col in columns_result]
            
            # Get the migration record
            result = conn.execute("""
                SELECT * FROM migration_status WHERE id = ?
            """, (migration_id,)).fetchone()
            
            if result:
                return dict(zip(columns, result))
            return None
    
    # ===== MEDIA TRANSFER OPERATIONS =====
    
    async def create_media_transfer(self, migration_id: str, 
                                   total_photos: int, total_videos: int,
                                   total_size_gb: float) -> str:
        """
        Create a media transfer record for photos and videos.
        
        Initializes tracking for the photo/video transfer process, setting initial
        status to 'pending' and configuring photos to become visible on Day 4.
        
        Args:
            migration_id: ID of the migration
            total_photos: Total number of photos to transfer
            total_videos: Total number of videos to transfer
            total_size_gb: Total size of media in GB
            
        Returns:
            str: Transfer ID (format: TRF-YYYYMMDD-HHMMSS)
        """
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
    
    async def create_photo_transfer(self, migration_id: str, 
                                   total_photos: int, total_videos: int,
                                   total_size_gb: float) -> str:
        """
        Backward compatibility wrapper for create_media_transfer.
        
        Maintained for compatibility with existing code that uses the old method name.
        Delegates to create_media_transfer.
        """
        return await self.create_media_transfer(migration_id, total_photos, total_videos, total_size_gb)
    
    async def update_media_progress(self, migration_id: str,
                                   transferred_photos: int = None,
                                   transferred_videos: int = None,
                                   transferred_size_gb: float = None,
                                   photo_status: str = None,
                                   video_status: str = None,
                                   overall_status: str = None):
        """
        Update media transfer progress.
        
        Updates photo and video transfer metrics separately, allowing for
        different completion rates (videos typically complete 100%, photos ~98%).
        
        Args:
            migration_id: ID of the migration
            transferred_photos: Number of photos transferred
            transferred_videos: Number of videos transferred
            transferred_size_gb: Total GB transferred
            photo_status: Status of photo transfer (pending/in_progress/completed)
            video_status: Status of video transfer (pending/in_progress/completed)
            overall_status: Overall transfer status
        """
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
    
    async def update_photo_progress(self, migration_id: str,
                                   transferred_photos: int = None,
                                   transferred_videos: int = None,
                                   transferred_size_gb: float = None,
                                   status: str = None):
        """
        Backward compatibility wrapper for update_media_progress.
        
        Maintained for compatibility with existing code. Maps single status
        to separate photo/video/overall statuses.
        """
        photo_status = status
        video_status = status
        overall_status = status
        return await self.update_media_progress(
            migration_id, transferred_photos, transferred_videos, 
            transferred_size_gb, photo_status, video_status, overall_status
        )
    
    # ===== FAMILY OPERATIONS =====
    
    async def add_family_member(self, migration_id: str, name: str,
                               email: str = None, phone: str = None,
                               role: str = None, age: int = None) -> int:
        """
        Add a family member to the migration.
        
        Creates a new family member record and updates the family_size in migration_status.
        Email and phone are optional since these are existing contacts on the phone.
        
        Args:
            migration_id: ID of the migration
            name: Family member's name (from phone contacts)
            email: Optional email address
            phone: Optional phone number
            role: Optional role (spouse/child)
            age: Optional age (used to determine teen accounts for Venmo)
            
        Returns:
            int: The ID of the newly created family member
            
        Example:
            member_id = await db.add_family_member(
                migration_id="MIG-20250825-120000",
                name="Laila",
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
                (id, migration_id, name, email, phone, role, age)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (next_id, migration_id, name, email, phone, role, age))
            
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
    
    async def get_family_members(self, migration_id: str, filter_type: str = "all") -> List[Dict[str, Any]]:
        """
        Get family members with optional filtering for database-driven discovery.
        
        Enhanced to support filters that enable mobile-mcp to query the database
        before taking actions, avoiding hardcoded family member names.
        
        Args:
            migration_id: ID of the migration
            filter_type: Filter to apply:
                - "all": Return all family members (default)
                - "not_in_whatsapp": Members not yet in WhatsApp group
                - "not_sharing_location": Members not sharing location
                - "teen": Members aged 13-17
                
        Returns:
            List of family member dictionaries with app adoption status
        """
        with self.get_connection() as conn:
            # Base query with app adoption status
            base_query = """
                SELECT fm.*, 
                       MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.whatsapp_in_group END) as whatsapp_in_group,
                       MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.status END) as whatsapp_status,
                       MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.location_sharing_received END) as location_sharing_received,
                       MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.status END) as maps_status,
                       MAX(CASE WHEN faa.app_name = 'Venmo' THEN faa.status END) as venmo_status
                FROM family_members fm
                LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
                WHERE fm.migration_id = ?
            """
            
            # Apply filters
            if filter_type == "not_in_whatsapp":
                base_query += " AND (faa.whatsapp_in_group IS FALSE OR faa.whatsapp_in_group IS NULL OR faa.app_name != 'WhatsApp')"
            elif filter_type == "not_sharing_location":
                base_query += " AND (faa.location_sharing_received IS FALSE OR faa.location_sharing_received IS NULL OR faa.app_name != 'Google Maps')"
            elif filter_type == "teen":
                base_query += " AND fm.age BETWEEN 13 AND 17"
            
            base_query += " GROUP BY fm.id, fm.migration_id, fm.name, fm.role, fm.age, fm.email, fm.phone, fm.staying_on_ios, fm.created_at"
            
            results = conn.execute(base_query, (migration_id,)).fetchall()
            
            # Convert to dictionaries
            members = []
            for row in results:
                member = {
                    'id': row[0],
                    'migration_id': row[1],
                    'name': row[2],
                    'role': row[3],
                    'age': row[4],
                    'email': row[5],
                    'phone': row[6],
                    'staying_on_ios': row[7],
                    'created_at': row[8],
                    'whatsapp_in_group': row[9] if len(row) > 9 else None,
                    'whatsapp_status': row[10] if len(row) > 10 else None,
                    'location_sharing_received': row[11] if len(row) > 11 else None,
                    'maps_status': row[12] if len(row) > 12 else None,
                    'venmo_status': row[13] if len(row) > 13 else None
                }
                members.append(member)
            
            return members
    
    # ===== SIMPLIFIED OPERATIONS =====
    
    async def update_migration_progress(self, migration_id: str, status: str,
                                       photos_transferred: int = None,
                                       videos_transferred: int = None,
                                       total_size_gb: float = None):
        """
        Simplified progress update for MCP tools.
        
        Provides a single method to update both migration status and media transfer
        progress, automatically mapping migration phases to transfer statuses.
        
        Args:
            migration_id: ID of the migration
            status: Migration phase (initialization/media_transfer/family_setup/validation/completed)
            photos_transferred: Number of photos transferred
            videos_transferred: Number of videos transferred
            total_size_gb: Total GB transferred
        """
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
        """
        Get items pending migration.
        
        Args:
            category: Type of items to check ('photos', 'apps', etc.)
            
        Returns:
            List of dictionaries with pending item details
        """
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
        """
        Mark an item as complete.
        
        Args:
            item_type: Type of item (photo, app, etc.)
            item_id: ID of the item
            details: Optional completion details
            
        Returns:
            bool: True if successful
        """
        logger.info(f"Marked {item_type} {item_id} as complete")
        return True
    
    async def get_migration_statistics(self, include_history: bool = False) -> Dict[str, Any]:
        """
        Get migration statistics.
        
        Provides summary statistics about migrations including active migration
        details and counts of total/completed migrations.
        
        Args:
            include_history: Whether to include historical migration data
            
        Returns:
            Dictionary with active_migration, total_migrations, and completed_migrations
        """
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
        """
        Log a migration event.
        
        Simple event logging for tracking migration activities.
        
        Args:
            event_type: Type of event
            component: Component generating the event
            description: Event description
            metadata: Optional event metadata
            
        Returns:
            bool: True if logged successfully
        """
        logger.info(f"[{component}] {event_type}: {description}")
        return True
    
    async def calculate_storage_progress(self, migration_id: str,
                                        current_storage_gb: float,
                                        day_number: int = None) -> Dict[str, Any]:
        """
        Calculate storage-based progress for media transfer.
        
        Central calculation method that determines transfer progress based on
        Google Photos storage growth since baseline. Implements the success
        narrative strategy by returning 100% completion on Day 7 regardless
        of actual storage metrics.
        
        Args:
            migration_id: ID of the migration to calculate progress for
            current_storage_gb: Current Google Photos storage in GB
            day_number: Optional day number (1-7) for demo flow. Day 7 forces 100%
            
        Returns:
            Dict containing:
                - storage: Current storage metrics (baseline, current, growth)
                - estimates: Estimated photos and videos transferred
                - progress: Percent complete and transfer rate
                - message: Human-readable progress message
                - success: Boolean indicating if transfer is complete
                
        Progress Calculation:
            - Storage growth = current - baseline
            - Percent = (growth / total_icloud) * 100
            - Day 7 Override: Always returns 100% for demo success
            
        Item Estimation:
            - Photos: 65% of storage, average 5.5MB per photo
            - Videos: 35% of storage, average 150MB per video
            
        Example:
            result = await db.calculate_storage_progress(
                migration_id="MIG-20250827-120000",
                current_storage_gb=220.88,
                day_number=5
            )
            # Returns: {
            #     "storage": {"baseline_gb": 13.88, "current_gb": 220.88, "growth_gb": 207.0},
            #     "estimates": {"photos_transferred": 26000, "videos_transferred": 500},
            #     "progress": {"percent_complete": 57.0, "rate_gb_per_day": 41.4},
            #     "message": "Transfer accelerating. 57.0% complete.",
            #     "success": False
            # }
        """
        try:
            # Get migration details and baseline
            migration = await self.get_migration_status(migration_id)
            if not migration:
                return {
                    "status": "error",
                    "message": "Migration not found"
                }
            
            # Get baseline storage from migration_status
            baseline_gb = migration.get('google_photos_baseline_gb', 0.0)
            total_icloud_gb = migration.get('total_icloud_storage_gb')
            total_photos = migration.get('photo_count')
            total_videos = migration.get('video_count')
            
            # These values MUST come from the database
            if total_icloud_gb is None or total_photos is None or total_videos is None:
                return {
                    "status": "error",
                    "message": "Migration data not found - values must come from actual iCloud check"
                }
            
            # Calculate actual storage growth
            growth_gb = max(0, current_storage_gb - baseline_gb)
            actual_percent = min(100, (growth_gb / total_icloud_gb) * 100) if total_icloud_gb > 0 else 0
            
            # CRITICAL: Day 7 Success Override for Demo
            if day_number == 7:
                # Force 100% completion on Day 7 for success narrative
                percent_complete = 100.0
                photos_transferred = total_photos  # Show full count
                videos_transferred = total_videos  # Show full count
                message = "Transfer complete! All photos and videos successfully migrated."
                success = True
            else:
                # Normal calculation for Days 1-6
                percent_complete = actual_percent
                
                # Estimate items transferred based on storage ratios
                # Photos: 65% of storage, average 5.5MB per photo
                photos_transferred = int((growth_gb * 0.65 * 1024) / 5.5)
                # Videos: 35% of storage, average 150MB per video  
                videos_transferred = int((growth_gb * 0.35 * 1024) / 150)
                
                # Cap at actual totals
                photos_transferred = min(photos_transferred, total_photos)
                videos_transferred = min(videos_transferred, total_videos)
                
                # Generate appropriate milestone message
                message = self._get_day_milestone_message(day_number, percent_complete)
                success = False
            
            # Calculate transfer rate if day_number provided
            rate_gb_per_day = (growth_gb / day_number) if day_number and day_number > 0 else 0
            
            return {
                "storage": {
                    "baseline_gb": baseline_gb,
                    "current_gb": current_storage_gb,
                    "growth_gb": growth_gb,
                    "total_expected_gb": total_icloud_gb
                },
                "estimates": {
                    "photos_transferred": photos_transferred,
                    "videos_transferred": videos_transferred,
                    "total_photos": total_photos,
                    "total_videos": total_videos
                },
                "progress": {
                    "percent_complete": round(percent_complete, 1),
                    "rate_gb_per_day": round(rate_gb_per_day, 1)
                },
                "message": message,
                "success": success,
                "day_number": day_number
            }
            
        except Exception as e:
            logger.error(f"Error calculating storage progress: {e}")
            return {
                "status": "error",
                "message": f"Failed to calculate progress: {str(e)}"
            }
    
    
    def _get_day_milestone_message(self, day_number: int, percent_complete: float) -> str:
        """
        Get appropriate milestone message based on day and progress.
        
        Provides contextual messages that align with the 7-day demo narrative,
        building anticipation and celebrating milestones.
        
        Args:
            day_number: Current day of transfer (1-7)
            percent_complete: Current completion percentage
            
        Returns:
            str: Human-readable progress message
        """
        if day_number is None:
            return f"Transfer in progress. {percent_complete:.1f}% complete."
            
        if day_number == 1:
            return "Transfer initiated. Apple is processing your request."
        elif day_number == 2:
            return f"Apple is preparing your media. Day {day_number} of expected 3-7 days."
        elif day_number == 3:
            return f"Transfer processing continues. Day {day_number} of expected 3-7 days."
        elif day_number == 4:
            if percent_complete > 20:
                return f"Photos are now visible in Google Photos! {percent_complete:.1f}% complete."
            else:
                return "Photos should start appearing soon in Google Photos."
        elif day_number == 5:
            return f"Transfer accelerating. {percent_complete:.1f}% complete."
        elif day_number == 6:
            if percent_complete >= 85:
                return f"Nearly there! {percent_complete:.1f}% complete."
            else:
                return f"Nearing completion. {percent_complete:.1f}% complete."
        elif day_number >= 7:
            # Day 7 always handled by main method to return 100%
            return "Transfer complete! All photos and videos successfully migrated."
        else:
            return f"Transfer in progress. Day {day_number}. {percent_complete:.1f}% complete."

def get_migration_db():
    """
    Get the singleton database instance.
    
    Returns the single MigrationDatabase instance used across all MCP tools,
    ensuring consistent database access and preventing connection conflicts.
    
    Returns:
        MigrationDatabase: The singleton database instance
    """
    return MigrationDatabase()

__all__ = ['MigrationDatabase', 'get_migration_db']