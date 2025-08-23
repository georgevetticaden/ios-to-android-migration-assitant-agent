# Migration State MCP Tool

DuckDB-based state management for tracking migration progress across all tools.

## Overview

This is a thin MCP wrapper around the existing migration database (`shared/database/migration_db.py`). It exposes database operations as MCP tools that return raw JSON for Claude to visualize and process.

## Features

- **Track Migration Progress**: Monitor overall migration status
- **Store Metadata**: Persist migration details and configuration
- **Query Migration Status**: Get current and historical migration data
- **Coordinate Tools**: Share state between web-automation and mobile-mcp
- **Event Logging**: Track all migration events and milestones

## Architecture

```
migration-state/
├── server.py          # Thin MCP wrapper
├── requirements.txt   # Dependencies (mcp, duckdb)
└── README.md         # This file

Imports from:
../../shared/database/migration_db.py  # Core database logic
```

The actual database logic remains in `shared/database/` to maintain separation between:
- **Core Logic**: Database operations, schemas, business logic
- **MCP Interface**: Protocol handling, JSON serialization

## Available Tools

### get_migration_status
Query current migration state or specific migration by ID.

### update_migration_progress
Update progress metrics for photos, videos, and total size.

### get_pending_items
Get items still to be migrated by category (photos, contacts, apps, messages).

### mark_item_complete
Mark individual migration items as complete.

### get_statistics
Return migration statistics as JSON, optionally including history.

### log_migration_event
Log migration events with metadata.

## Setup

### Prerequisites

- Python 3.11+
- DuckDB installed
- MCP package

### Installation

```bash
# From the migration-state directory
pip install -r requirements.txt
```

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "migration-state": {
      "command": "/path/to/.venv/bin/python",
      "args": [
        "/path/to/mcp-tools/migration-state/server.py"
      ]
    }
  }
}
```

## Usage

### With Claude Desktop

After configuration and restart:
- "Get current migration status"
- "Show migration statistics"
- "Update photo transfer progress"
- "Mark WhatsApp migration complete"

### Standalone Testing

```python
# Test the database directly
from shared.database.migration_db import MigrationDatabase

db = MigrationDatabase()
status = await db.get_active_migration()
print(status)
```

## Database Schema

The database uses DuckDB with schemas defined in `shared/database/schemas/`:
- Migration master records
- Photo transfer details
- App migration status
- Event logs
- Progress metrics

## Integration with Other Tools

### web-automation
Tracks iCloud photo extraction and transfer initiation.

### mobile-mcp
Records Android app installations and configurations.

### Coordination
All tools update the same database, enabling:
- Unified progress tracking
- Cross-tool dependencies
- Complete migration history

## Troubleshooting

### Database Locked
If DuckDB is locked by another process:
```bash
# Check what's using the database
lsof | grep migration.db

# Kill the process if needed
kill -9 [PID]
```

### Permission Issues
Ensure the database directory exists and is writable:
```bash
mkdir -p ~/.ios_android_migration
chmod 755 ~/.ios_android_migration
```

### MCP Connection Issues
Check server is running:
```bash
python server.py
```

Test with simple JSON-RPC:
```bash
echo '{"jsonrpc":"2.0","method":"list_tools","id":1}' | python server.py
```