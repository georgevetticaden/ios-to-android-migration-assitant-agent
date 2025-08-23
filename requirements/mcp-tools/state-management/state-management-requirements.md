# State Management Requirements - Shared State MCP

## Overview

This document defines the state management architecture for the iOS to Android migration assistant. The shared-state-mcp tool provides a centralized state store using DuckDB, accessible by both Claude (the orchestrator) and photo-migration-mcp (which needs to update progress directly).

## Architecture Decision

### Chosen Approach: Shared MCP Service

```
┌─────────────────────────────────────────┐
│         Claude (Orchestrator)           │
│   Calls shared-state-mcp for updates    │
│   after mobile-mcp operations           │
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│         shared-state-mcp                │
│   - MCP wrapper around DuckDB           │
│   - Read/write operations               │
│   - Progress tracking                   │
└────────────────▲────────────────────────┘
                 │
┌────────────────┴────────────────────────┐
│      photo-migration-mcp                │
│   Calls shared-state-mcp directly       │
│   for photo transfer updates            │
└─────────────────────────────────────────┘

Note: mobile-mcp does NOT call shared-state-mcp
(keeps forked code clean)
```

### Why This Architecture

1. **Separation of Concerns** - State management is isolated
2. **Clean Fork** - mobile-mcp remains unmodified 
3. **Direct Updates** - photo-migration-mcp can update without going through Claude
4. **Orchestration Control** - Claude manages state for mobile operations

## Database Schema Updates

### Existing Schemas (Keep As-Is)

#### core_schema.sql
```sql
-- Migration metadata and status
CREATE TABLE IF NOT EXISTS migrations (
    migration_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    source_device TEXT,
    target_device TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    status TEXT CHECK(status IN ('planning', 'in_progress', 'completed', 'failed')),
    total_photos INTEGER,
    total_apps INTEGER,
    family_members INTEGER
);

CREATE TABLE IF NOT EXISTS migration_events (
    event_id TEXT PRIMARY KEY,
    migration_id TEXT,
    timestamp TIMESTAMP,
    event_type TEXT,
    description TEXT,
    metadata JSON,
    FOREIGN KEY (migration_id) REFERENCES migrations(migration_id)
);
```

#### photo_schema.sql
```sql
-- Photo transfer tracking
CREATE TABLE IF NOT EXISTS photo_transfers (
    transfer_id TEXT PRIMARY KEY,
    migration_id TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    source_count INTEGER,
    transferred_count INTEGER,
    status TEXT CHECK(status IN ('pending', 'transferring', 'completed', 'failed')),
    transfer_rate REAL,
    estimated_completion TIMESTAMP,
    FOREIGN KEY (migration_id) REFERENCES migrations(migration_id)
);

CREATE TABLE IF NOT EXISTS photo_progress_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_id TEXT,
    checked_at TIMESTAMP,
    photos_transferred INTEGER,
    transfer_rate REAL,
    FOREIGN KEY (transfer_id) REFERENCES photo_transfers(transfer_id)
);
```

#### family_schema.sql
```sql
-- Family member tracking
CREATE TABLE IF NOT EXISTS family_members (
    member_id TEXT PRIMARY KEY,
    migration_id TEXT,
    name TEXT,
    relationship TEXT,
    phone_number TEXT,
    email TEXT,
    device_type TEXT,
    whatsapp_status TEXT CHECK(whatsapp_status IN ('not_invited', 'invited', 'joined')),
    location_sharing_status TEXT CHECK(location_sharing_status IN ('not_shared', 'pending', 'active')),
    venmo_status TEXT CHECK(venmo_status IN ('not_setup', 'pending', 'active')),
    FOREIGN KEY (migration_id) REFERENCES migrations(migration_id)
);
```

#### whatsapp_schema.sql (Update for Natural Language)
```sql
-- WhatsApp setup tracking
CREATE TABLE IF NOT EXISTS whatsapp_setup (
    setup_id TEXT PRIMARY KEY,
    migration_id TEXT,
    installation_status TEXT CHECK(installation_status IN ('not_started', 'installing', 'installed')),
    group_name TEXT,
    group_created BOOLEAN,
    members_added INTEGER,
    setup_completed_at TIMESTAMP,
    natural_language_commands JSON,  -- NEW: Store commands used
    FOREIGN KEY (migration_id) REFERENCES migrations(migration_id)
);
```

## MCP Service Interface

### Tools Exposed by shared-state-mcp

```python
# shared-state/server.py

@server.tool()
async def initialize_migration(
    user_id: str,
    source_device: str = "iPhone 16 Pro Max",
    target_device: str = "Samsung Galaxy Z Fold 7",
    total_photos: int = None,
    family_members: List[dict] = None
) -> TextContent:
    """Initialize a new migration with metadata"""
    
@server.tool()
async def update_photo_progress(
    transfer_id: str,
    photos_transferred: int,
    transfer_rate: float = None
) -> TextContent:
    """Update photo transfer progress (called by photo-migration-mcp)"""

@server.tool()
async def update_app_status(
    migration_id: str,
    app_name: str,  # 'whatsapp', 'venmo', 'google_maps'
    status: str,
    details: dict = None
) -> TextContent:
    """Update app setup status (called by Claude after mobile-mcp operations)"""

@server.tool()
async def update_family_member_status(
    migration_id: str,
    member_name: str,
    service: str,  # 'whatsapp', 'location_sharing', 'venmo'
    status: str
) -> TextContent:
    """Update individual family member service status"""

@server.tool()
async def get_migration_status(
    migration_id: str
) -> TextContent:
    """Get comprehensive migration status"""

@server.tool()
async def log_event(
    migration_id: str,
    event_type: str,
    description: str,
    metadata: dict = None
) -> TextContent:
    """Log a migration event for audit trail"""
```

## Integration Points

### 1. photo-migration-mcp Integration

The photo-migration-mcp directly calls shared-state-mcp:

```python
# In icloud_transfer_workflow.py
async def update_progress(self, photos_transferred: int):
    """Update progress in shared state"""
    if self.shared_state_client:
        await self.shared_state_client.update_photo_progress(
            transfer_id=self.transfer_id,
            photos_transferred=photos_transferred,
            transfer_rate=self.calculate_rate()
        )
```

### 2. Claude Orchestration Integration

Claude calls shared-state-mcp after mobile-mcp operations:

```markdown
# In agent/instructions.md

After completing WhatsApp setup:
1. Use mobile-mcp: "Create family group"
2. Use shared-state-mcp: update_app_status("whatsapp", "completed", {group_name: "Family"})

After checking Google Photos:
1. Use mobile-mcp: "Read photo count"
2. Use shared-state-mcp: log_event("photo_check", "Photos arriving: 15,387")
```

### 3. Mobile-MCP Non-Integration

Mobile-mcp does NOT directly integrate with shared-state. This keeps the forked code clean. Claude handles all state updates after mobile-mcp operations.

## State Management Flows

### Flow 1: Photo Migration
```
1. Claude → photo-migration-mcp: "Start transfer"
2. photo-migration-mcp → shared-state-mcp: "Initialize transfer"
3. [Every 30 min] photo-migration-mcp → shared-state-mcp: "Update progress"
4. Claude → shared-state-mcp: "Get status" (when user asks)
5. photo-migration-mcp → shared-state-mcp: "Mark complete"
```

### Flow 2: WhatsApp Setup
```
1. Claude → mobile-mcp: "Install WhatsApp" (natural language)
2. Claude → shared-state-mcp: "Update app status: installing"
3. Claude → mobile-mcp: "Create family group" (natural language)
4. Claude → shared-state-mcp: "Update app status: completed"
5. Claude → shared-state-mcp: "Update family members: all joined"
```

### Flow 3: Progress Checking
```
1. User → Claude: "How's my migration going?"
2. Claude → shared-state-mcp: "Get migration status"
3. Claude → mobile-mcp: "Open Google Photos and check count"
4. Claude → shared-state-mcp: "Log event: visual verification"
5. Claude → User: Comprehensive status report
```

## Error Handling

### State Consistency
- All operations are idempotent
- State updates include timestamps
- Failed operations don't corrupt state
- Recovery possible from any point

### Connection Failures
```python
# Graceful degradation if state service unavailable
try:
    await shared_state.update_progress(...)
except ConnectionError:
    # Log locally and continue
    logger.warning("State service unavailable, continuing without state update")
```

## Testing Requirements

### Unit Tests
```python
def test_state_initialization():
    """Test migration initialization"""
    
def test_progress_updates():
    """Test incremental progress updates"""
    
def test_concurrent_updates():
    """Test multiple tools updating simultaneously"""
    
def test_state_recovery():
    """Test recovery after connection loss"""
```

### Integration Tests
```python
def test_photo_migration_integration():
    """Test photo-migration-mcp → shared-state-mcp"""
    
def test_claude_orchestration():
    """Test Claude → shared-state-mcp after mobile operations"""
    
def test_full_migration_flow():
    """Test complete migration with all state updates"""
```

## Implementation Notes

### DuckDB Persistence
- Database file: `~/.ios_android_migration/migration.db`
- Automatic backup every hour
- WAL mode for concurrent access
- Vacuum on completion

### Performance Considerations
- Batch updates when possible
- Async operations throughout
- Connection pooling for DuckDB
- Minimal locking for reads

### Security
- No sensitive data in state (no passwords)
- Phone numbers partially redacted
- Read-only access for status checks
- Write access requires migration_id

## Success Metrics

- State updates < 100ms
- Zero data loss across restarts
- Concurrent access supported
- Complete audit trail maintained
- Recovery from any failure point

## Conclusion

The shared-state-mcp service provides a clean, centralized state management solution that:
1. Keeps mobile-mcp fork unmodified
2. Allows direct updates from photo-migration-mcp
3. Gives Claude full orchestration control
4. Maintains complete migration history
5. Enables recovery and resume capabilities

This architecture supports the Three Amigos pattern by allowing each specialist to focus on their domain while maintaining coordinated state through a shared service.