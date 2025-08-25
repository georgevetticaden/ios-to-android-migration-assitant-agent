"""
Centralized DuckDB database for iOS to Android migration
Shared across all MCP tools for unified state management
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
        """Create all schemas if they don't exist"""
        schema_dir = Path(__file__).parent / 'schemas'
        
        with self.get_connection() as conn:
            # Load and execute each schema file
            for schema_file in sorted(schema_dir.glob('*.sql')):
                logger.info(f"Loading schema: {schema_file.name}")
                with open(schema_file, 'r') as f:
                    schema_sql = f.read()
                    # Execute each statement separately
                    for statement in schema_sql.split(';'):
                        statement = statement.strip()
                        if statement:
                            try:
                                conn.execute(statement)
                            except Exception as e:
                                logger.error(f"Error executing statement in {schema_file.name}: {e}")
                                logger.error(f"Statement: {statement[:100]}...")
                    logger.info(f"Initialized schema: {schema_file.name}")
    
    # ===== MIGRATION CORE OPERATIONS =====
    
    async def create_migration(self, user_email: str, user_name: str, 
                             source_device: str, target_device: str,
                             family_id: Optional[str] = None) -> str:
        """Create a new master migration record"""
        migration_id = f"MIG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO migration_core.migrations 
                (migration_id, family_id, started_at, user_email, user_name, 
                 source_device, target_device, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'planning')
            """, (migration_id, family_id, datetime.now(), user_email, user_name, 
                  source_device, target_device))
        
        logger.info(f"Created migration: {migration_id}")
        return migration_id
    
    async def get_active_migration(self) -> Optional[Dict[str, Any]]:
        """Get the currently active migration"""
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM migration_core.migrations 
                WHERE status IN ('planning', 'in_progress')
                ORDER BY started_at DESC
                LIMIT 1
            """).fetchone()
            
            if result:
                cols = [desc[0] for desc in conn.description]
                return dict(zip(cols, result))
        return None
    
    async def get_migration(self, migration_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific migration by ID"""
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM migration_core.migrations 
                WHERE migration_id = ?
            """, (migration_id,)).fetchone()
            
            if result:
                cols = [desc[0] for desc in conn.description]
                return dict(zip(cols, result))
        return None
    
    async def update_migration_status(self, migration_id: str, status: str):
        """Update migration status"""
        with self.get_connection() as conn:
            if status == 'completed':
                conn.execute("""
                    UPDATE migration_core.migrations 
                    SET status = ?, completed_at = ?
                    WHERE migration_id = ?
                """, (status, datetime.now(), migration_id))
            else:
                conn.execute("""
                    UPDATE migration_core.migrations 
                    SET status = ?
                    WHERE migration_id = ?
                """, (status, migration_id))
    
    async def log_event(self, migration_id: str, tool_name: str, 
                       event_type: str, details: Dict[str, Any]):
        """Log an event from any tool"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO migration_core.event_log
                (migration_id, timestamp, tool_name, event_type, details)
                VALUES (?, ?, ?, ?, ?)
            """, (migration_id, datetime.now(), tool_name, event_type, 
                  json.dumps(details)))
    
    # ===== FAMILY MEMBER OPERATIONS =====
    
    async def add_family_member(self, migration_id: str, name: str, role: str,
                               apple_id: Optional[str] = None,
                               google_account: Optional[str] = None,
                               phone_number: Optional[str] = None) -> str:
        """Add a family member to the migration"""
        member_id = f"MEM-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO migration_core.family_members
                (member_id, migration_id, name, role, apple_id, 
                 google_account, phone_number, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (member_id, migration_id, name, role, apple_id,
                  google_account, phone_number, datetime.now()))
        
        return member_id
    
    async def get_family_members(self, migration_id: str) -> List[Dict[str, Any]]:
        """Get all family members for a migration"""
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT * FROM migration_core.family_members
                WHERE migration_id = ?
                ORDER BY created_at
            """, (migration_id,)).fetchall()
            
            if results:
                cols = [desc[0] for desc in conn.description]
                return [dict(zip(cols, row)) for row in results]
        return []
    
    # ===== PHOTO MIGRATION OPERATIONS =====
    
    async def create_photo_transfer(self, transfer_data: Dict[str, Any]) -> str:
        """Create a photo transfer linked to active migration"""
        # Get or create active migration
        active_migration = await self.get_active_migration()
        if not active_migration:
            # Auto-create migration if none exists
            migration_id = await self.create_migration(
                transfer_data.get('google_email', 'unknown@gmail.com'),
                transfer_data.get('user_name', 'User'),
                'iPhone',
                'Android'
            )
            active_migration = {'migration_id': migration_id}
        
        transfer_data['migration_id'] = active_migration['migration_id']
        
        with self.get_connection() as conn:
            # Insert photo transfer
            conn.execute("""
                INSERT INTO photo_migration.transfers
                (transfer_id, migration_id, started_at, status, 
                 source_photos, source_videos, source_size_gb,
                 google_email, apple_id, baseline_google_count,
                 baseline_timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                transfer_data['transfer_id'],
                transfer_data['migration_id'],
                datetime.now(),
                'initiated',
                transfer_data.get('source_photos', 0),
                transfer_data.get('source_videos', 0),
                transfer_data.get('source_size_gb', 0.0),
                transfer_data['google_email'],
                transfer_data['apple_id'],
                transfer_data.get('baseline_count', 0),
                transfer_data.get('baseline_timestamp'),
                json.dumps(transfer_data.get('metadata', {}))
            ))
        
        # Log event
        await self.log_event(
            transfer_data['migration_id'],
            'web-automation',
            'transfer_started',
            {
                'transfer_id': transfer_data['transfer_id'],
                'total_items': transfer_data.get('source_photos', 0) + transfer_data.get('source_videos', 0)
            }
        )
        
        # Update migration status to in_progress
        await self.update_migration_status(transfer_data['migration_id'], 'in_progress')
        
        return transfer_data['transfer_id']
    
    async def get_photo_transfer(self, transfer_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific photo transfer"""
        with self.get_connection() as conn:
            result = conn.execute("""
                SELECT * FROM photo_migration.transfers
                WHERE transfer_id = ?
            """, (transfer_id,)).fetchone()
            
            if result:
                cols = [desc[0] for desc in conn.description]
                return dict(zip(cols, result))
        return None
    
    async def update_photo_progress(self, transfer_id: str, progress_data: Dict[str, Any]):
        """Add progress check record"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO photo_migration.progress_history
                (transfer_id, checked_at, google_photos_total, 
                 transferred_items, transfer_rate_per_hour, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transfer_id,
                datetime.now(),
                progress_data.get('google_total', 0),
                progress_data.get('transferred_items', 0),
                progress_data.get('rate_per_hour', 0.0),
                progress_data.get('notes')
            ))
    
    async def get_photo_progress_history(self, transfer_id: str) -> List[Dict[str, Any]]:
        """Get complete history for transfer"""
        with self.get_connection() as conn:
            results = conn.execute("""
                SELECT * FROM photo_migration.progress_history 
                WHERE transfer_id = ? 
                ORDER BY checked_at
            """, (transfer_id,)).fetchall()
            
            if results:
                cols = [desc[0] for desc in conn.description]
                return [dict(zip(cols, row)) for row in results]
        return []
    
    async def calculate_transfer_rate(self, transfer_id: str) -> float:
        """Calculate current transfer rate based on recent progress"""
        with self.get_connection() as conn:
            # Get last two progress entries
            results = conn.execute("""
                SELECT 
                    transferred_items,
                    checked_at
                FROM photo_migration.progress_history 
                WHERE transfer_id = ?
                ORDER BY checked_at DESC
                LIMIT 2
            """, (transfer_id,)).fetchall()
            
            if len(results) >= 2:
                current = results[0]
                previous = results[1]
                
                items_diff = current[0] - previous[0]
                time_diff_hours = (current[1] - previous[1]).total_seconds() / 3600
                
                if time_diff_hours > 0:
                    return items_diff / time_diff_hours
        
        return 0.0
    
    async def mark_photo_transfer_complete(self, transfer_id: str):
        """Mark a photo transfer as complete"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE photo_migration.transfers
                SET status = 'completed', completed_at = ?
                WHERE transfer_id = ?
            """, (datetime.now(), transfer_id))
    
    # ===== CROSS-TOOL QUERIES =====
    
    async def get_migration_timeline(self, migration_id: str) -> List[Dict]:
        """Get complete timeline across all tools"""
        with self.get_connection() as conn:
            events = conn.execute("""
                SELECT * FROM migration_core.event_log
                WHERE migration_id = ?
                ORDER BY timestamp
            """, (migration_id,)).fetchall()
            
            if events:
                cols = [desc[0] for desc in conn.description]
                return [dict(zip(cols, event)) for event in events]
        return []
    
    async def get_tool_status(self, migration_id: str) -> Dict[str, Any]:
        """Get status of all tools for a migration"""
        status = {}
        
        with self.get_connection() as conn:
            # Photo migration status
            photo_transfer = conn.execute("""
                SELECT * FROM photo_migration.transfers
                WHERE migration_id = ?
                ORDER BY started_at DESC
                LIMIT 1
            """, (migration_id,)).fetchone()
            
            if photo_transfer:
                cols = [desc[0] for desc in conn.description]
                status['photo_migration'] = dict(zip(cols, photo_transfer))
            
            # Future: Add WhatsApp status
            # whatsapp_status = conn.execute(...)
            # if whatsapp_status:
            #     status['whatsapp'] = ...
            
            # Future: Add family services status
            # family_status = conn.execute(...)
            # if family_status:
            #     status['family_services'] = ...
            
        return status
    
    # ===== COORDINATION METHODS =====
    
    async def set_tool_dependency(self, migration_id: str, tool_name: str,
                                 depends_on: str):
        """Set tool dependencies for coordination"""
        with self.get_connection() as conn:
            conn.execute("""
                INSERT INTO migration_core.tool_coordination
                (migration_id, tool_name, depends_on_tool, dependency_status)
                VALUES (?, ?, ?, 'waiting')
            """, (migration_id, tool_name, depends_on))
    
    async def update_tool_dependency_status(self, migration_id: str, 
                                           tool_name: str, status: str):
        """Update dependency status when prerequisite completes"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE migration_core.tool_coordination
                SET dependency_status = ?
                WHERE migration_id = ? AND depends_on_tool = ?
            """, (status, migration_id, tool_name))
    
    async def check_dependencies_ready(self, migration_id: str, tool_name: str) -> bool:
        """Check if all dependencies for a tool are ready"""
        with self.get_connection() as conn:
            waiting = conn.execute("""
                SELECT COUNT(*) FROM migration_core.tool_coordination
                WHERE migration_id = ? AND tool_name = ? 
                AND dependency_status != 'completed'
            """, (migration_id, tool_name)).fetchone()[0]
            
            return waiting == 0
    
    # ===== UTILITY METHODS =====
    
    async def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        stats = {}
        
        with self.get_connection() as conn:
            # Count migrations
            stats['total_migrations'] = conn.execute(
                "SELECT COUNT(*) FROM migration_core.migrations"
            ).fetchone()[0]
            
            # Count active migrations
            stats['active_migrations'] = conn.execute("""
                SELECT COUNT(*) FROM migration_core.migrations 
                WHERE status IN ('planning', 'in_progress')
            """).fetchone()[0]
            
            # Count events
            stats['total_events'] = conn.execute(
                "SELECT COUNT(*) FROM migration_core.event_log"
            ).fetchone()[0]
            
            # Database size
            db_size = Path(self.db_path).stat().st_size if Path(self.db_path).exists() else 0
            stats['database_size_mb'] = round(db_size / 1024 / 1024, 2)
        
        return stats

# Global instance getter
def get_migration_db() -> MigrationDatabase:
    """Get the singleton database instance"""
    return MigrationDatabase()