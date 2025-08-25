"""
Centralized DuckDB database for iOS to Android migration
Works with simplified schema (no schema prefixes)
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
        """Initialize database connection"""
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
        """Context manager for database connections"""
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
                              storage_gb: float = 0) -> str:
        """Create a new migration record"""
        migration_id = f"MIG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO migration_status 
                (id, user_name, source_device, target_device, 
                 photo_count, video_count, storage_gb, started_at, current_phase)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'initialization')
            """, (migration_id, user_name, source_device, target_device,
                  photo_count, video_count, storage_gb, datetime.now()))
        
        logger.info(f"Created migration: {migration_id}")
        return migration_id
    
    async def get_active_migration(self) -> Optional[Dict[str, Any]]:
        """Get the currently active migration"""
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
        """Update migration status"""
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
        """Add a family member"""
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
            await self.update_photo_progress(
                migration_id,
                transferred_photos=photos_transferred,
                transferred_videos=videos_transferred,
                transferred_size_gb=total_size_gb,
                status='in_progress' if status == 'in_progress' else status
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