# Migration State MCP Server

## Overview

The Migration State MCP server provides 16 tools for managing iOS to Android migration state in a centralized DuckDB database. It tracks the complete 7-day migration journey including photos, family members, app adoption, and progress milestones.

## Features

- **16 MCP Tools**: Complete state management for migration flow
- **DuckDB Backend**: Persistent state in `~/.ios_android_migration/migration.db`
- **7-Day Demo Flow**: Day-aware logic for realistic migration timeline
- **JSON Responses**: All tools return JSON for easy visualization
- **No Foreign Keys**: Workaround for DuckDB UPDATE limitation

## Available Tools

### Original 6 Tools

1. **get_migration_status**
   - Get current migration state
   - Returns active migration or empty

2. **update_migration_progress**
   - Update migration progress metrics
   - Parameters: migration_id, status, photos_transferred, videos_transferred, total_size_gb

3. **initialize_migration** (enhanced in Phase 2)
   - Start new migration with full details
   - Parameters: user_name, years_on_ios, photo_count, video_count, storage_gb

4. **get_pending_items**
   - List items pending migration
   - Parameters: category (photos, apps, etc.)

5. **mark_item_complete**
   - Mark migration items as complete
   - Parameters: item_type, item_id, details

6. **get_migration_statistics**
   - Get overall migration statistics
   - Parameters: include_history (optional)

### New Phase 2 Tools (10 Additional)

7. **add_family_member**
   - Add family member to migration
   - Parameters: name, email, role (spouse/child), age

8. **start_photo_transfer**
   - Record Apple photo transfer initiation
   - Parameters: transfer_initiated (boolean)

9. **update_family_member_apps**
   - Track app adoption per family member
   - Parameters: family_member_name, app_name (WhatsApp/Google Maps/Venmo), status

10. **update_photo_progress**
    - Update photo transfer percentage
    - Parameters: transferred_percentage

11. **activate_venmo_card**
    - Track teen Venmo card activation
    - Parameters: family_member_name

12. **get_daily_summary**
    - Get progress snapshot for specific day
    - Parameters: day_number (1-7)

13. **get_migration_overview**
    - Get complete migration status overview
    - No parameters required

14. **create_action_item**
    - Placeholder for mobile-mcp coordination
    - Parameters: action_type, description

15. **generate_migration_report**
    - Generate final migration completion report
    - No parameters required

16. **log_migration_event**
    - Log migration events
    - Parameters: event_type, component, description, metadata

## Database Structure

### Tables (7)
- `migration_status` - Core migration tracking
- `family_members` - Family member details
- `photo_transfer` - Photo/video transfer progress
- `app_setup` - App installation tracking
- `family_app_adoption` - Per-member app status
- `daily_progress` - Day-by-day snapshots
- `venmo_setup` - Teen card tracking

### Views (3)
- `migration_summary` - Overall migration status
- `family_app_status` - Family app adoption matrix
- `active_migration` - Current active migration

### Important: No Foreign Keys
Foreign key constraints have been removed to work around a DuckDB limitation where UPDATE operations fail on tables with foreign key references. Referential integrity is enforced at the application layer instead.

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 ../../shared/database/scripts/initialize_database.py

# Run tests
python3 tests/test_migration_state.py
```

## Testing

The test suite (`tests/test_migration_state.py`) validates all 16 tools through a complete 7-day demo flow:

```bash
cd mcp-tools/migration-state
python3 tests/test_migration_state.py
```

Expected: 17 tests pass (all tools + cleanup)

## Configuration for Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "migration-state": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": [
        "/absolute/path/to/mcp-tools/migration-state/server.py"
      ]
    }
  }
}
```

## Usage Example

```python
# In Claude Desktop, the tools are available automatically
# Example prompts:

"Check the current migration status"
# Uses: get_migration_status

"Initialize a migration for George with 60,000 photos"
# Uses: initialize_migration

"Add Jaisy as a family member"
# Uses: add_family_member

"Show me the Day 4 summary"
# Uses: get_daily_summary

"Generate the final migration report"
# Uses: generate_migration_report
```

## 7-Day Demo Timeline

- **Day 1**: Initialize migration, add family, start photo transfer
- **Day 2-3**: Family adopts WhatsApp
- **Day 4**: Photos become visible (28% transferred)
- **Day 5**: Venmo teen cards activated
- **Day 6**: Location sharing setup
- **Day 7**: Migration complete, final report

## Troubleshooting

### Foreign Key Errors
If you see foreign key constraint errors during UPDATE operations, ensure you're using the latest schema without foreign keys. Re-run `initialize_database.py`.

### Database Locked
Close any database viewers (DBeaver) before running tests.

### Import Errors
Ensure you're in the virtual environment and have installed all requirements.

## Development

The server implements the MCP protocol with:
- Tool discovery via `tools/list`
- Tool execution via `tools/call`
- JSON serialization for all responses
- Comprehensive error handling

All database operations go through `shared/database/migration_db.py` for consistency.

## Next Steps

After Phase 2 completion, the next phase involves:
1. Creating the iOS2Android agent using `agent/instructions/ios2android-agent-instructions.md`
2. Testing natural language orchestration across all MCP servers
3. Validating the complete 7-day demo flow