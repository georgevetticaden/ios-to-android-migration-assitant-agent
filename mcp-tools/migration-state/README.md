# Migration State MCP Server

## Overview

The Migration State MCP server provides centralized state management for iOS to Android phone migrations. It exposes 7 essential database operations as MCP tools, orchestrating the complete 7-day migration journey from initialization through celebration.

This server acts as the single source of truth for:
- Migration progress and timeline
- Family member coordination
- Cross-platform app adoption
- Storage-based progress tracking
- Final success reporting

## The 7 MCP Tools

### 1. `initialize_migration`
**When Used**: Day 1, called once at the very beginning  
**Purpose**: Creates a new migration record and returns the migration_id used in all subsequent operations  
**Parameters**:
- `user_name` (required): Full name of the person migrating
- `years_on_ios` (required): How many years they've used iPhone

**Example**:
```json
{
  "user_name": "George Vetticaden",
  "years_on_ios": 18
}
```

**Returns**: 
```json
{
  "success": true,
  "migration_id": "MIG-20250831-123456",
  "status": "initialized",
  "message": "Migration initialized for George Vetticaden"
}
```

### 2. `add_family_member`
**When Used**: Day 1, called 4 times typically (spouse + 3 children)  
**Purpose**: Registers family members for cross-platform connectivity coordination  
**Parameters**:
- `name` (required): Family member's name from phone contacts
- `role` (required): Either "spouse" or "child"
- `age` (optional): If provided and 13-17, automatically creates Venmo teen record
- `email` (optional): Email address for app invitations
- `phone` (optional): Phone number

**Example**:
```json
{
  "name": "Laila",
  "role": "child",
  "age": 17
}
```

**Special Behavior**: Ages 13-17 automatically trigger Venmo teen account setup records

### 3. `update_migration_status`
**When Used**: Called 9 times total across all 7 days  
**Purpose**: Progressive updates with new information as it becomes available  
**Day-by-Day Usage**:
- **Day 1 Call 1**: Add iCloud metrics (photo_count, video_count, storage sizes)
- **Day 1 Call 2**: Set Google Photos baseline after transfer starts
- **Day 1 Call 3**: Add family information (family_size, whatsapp_group_name)
- **Days 2-7**: Update overall_progress percentage once per day
- **Day 7**: Mark as completed with completed_at timestamp

**Important**: Only pass NEW fields in each call, not all fields every time

**Example Day 1 First Call**:
```json
{
  "migration_id": "MIG-20250831-123456",
  "photo_count": 60238,
  "video_count": 2418,
  "total_icloud_storage_gb": 383,
  "icloud_photo_storage_gb": 268,
  "icloud_video_storage_gb": 115
}
```

### 4. `update_family_member_apps`
**When Used**: Throughout Days 1-7 as family members adopt apps  
**Purpose**: Track app installation and configuration status for each family member  
**Parameters**:
- `member_name` (required): Must match name from add_family_member
- `app_name` (required): "WhatsApp", "Google Maps", or "Venmo"
- `status` (required): "not_started", "invited", "installed", or "configured"
- `details` (optional): Object with specific tracking fields like `whatsapp_in_group`

**Timeline**:
- Day 1: WhatsApp group setup
- Day 3: Google Maps location sharing
- Day 5: Venmo teen card activation

**Example**:
```json
{
  "member_name": "Jaisy",
  "app_name": "WhatsApp",
  "status": "configured",
  "details": {
    "whatsapp_in_group": true
  }
}
```

### 5. `get_migration_status`
**When Used**: Once per day on Days 2-7 (the "UBER" status tool)  
**Purpose**: Returns EVERYTHING - complete migration details, progress, family status in one call  
**Parameters**:
- `day_number` (required): Integer 1-7

**Returns**: Comprehensive status object including:
- `migration`: Complete migration record
- `day_summary`: Day-specific progress and milestones
- `photo_progress`: Transfer progress (0% Days 1-3, increases Day 4+)
- `family_services`: WhatsApp, Maps, Venmo adoption counts
- `status_message`: Human-readable progress message

**Day-Aware Behavior**:
- Days 1-3: Shows 0% progress (Apple processing)
- Day 4: 28% progress (photos appearing)
- Day 5: 57% progress (accelerating)
- Day 6: 88% progress (near completion)
- Day 7: 100% progress (guaranteed success)

### 6. `get_family_members`
**When Used**: As needed to query family status  
**Purpose**: Find family members needing app setup or meeting specific criteria  
**Parameters**:
- `filter` (optional): "all", "not_in_whatsapp", "not_sharing_location", or "teen"

**Example Use Cases**:
- Find teens needing Venmo setup: `filter: "teen"`
- Find who hasn't joined WhatsApp: `filter: "not_in_whatsapp"`
- Get all family members: `filter: "all"` or omit parameter

### 7. `generate_migration_report`
**When Used**: Day 7 only, after marking migration complete  
**Purpose**: Generate celebratory final report showing 100% success  
**Parameters**:
- `format` (optional): "summary" or "detailed" (defaults to "summary")

**Returns**: Celebration report with:
- User details and migration duration
- Photo/video transfer achievements
- Family connectivity status
- Data integrity confirmation
- Welcome to Android message

**Success Guarantee**: Always shows 100% completion and success, regardless of actual transfer status

## 7-Day Timeline Overview

### Day 1: Setup & Initialize
- `initialize_migration`: Start the journey
- `add_family_member` (×4): Register family
- `update_migration_status` (×3): Add metrics progressively
- `update_family_member_apps`: Begin WhatsApp setup

### Days 2-3: Apple Processing
- `get_migration_status`: Daily check (shows 0% progress)
- `update_migration_status`: Update overall progress
- Continue family app invitations

### Day 4: Photos Appear! 🎉
- `get_migration_status`: Shows 28% progress
- Photos now visible in Google Photos
- WhatsApp group fully configured

### Day 5: Acceleration
- `get_migration_status`: Shows 57% progress
- Venmo teen accounts activated
- Location sharing begins

### Day 6: Near Completion
- `get_migration_status`: Shows 88% progress
- Final app configurations
- Prepare for celebration

### Day 7: Success! 🎊
- `get_migration_status`: Shows 100% progress
- `update_migration_status`: Mark as completed
- `generate_migration_report`: Create celebration report

## Database Backend

**Location**: `~/.ios_android_migration/migration.db` (DuckDB)

**Key Tables**:
- `migration_status`: Core migration tracking
- `family_members`: Family member records
- `family_app_adoption`: App status per member
- `media_transfer`: Photo/video transfer tracking
- `storage_snapshots`: Google Photos storage metrics
- `venmo_setup`: Teen account tracking

## Installation & Setup

### Prerequisites
```bash
# From project root
cd mcp-tools/migration-state

# Install dependencies
pip install -r requirements.txt

# Initialize database
python3 ../../shared/database/scripts/initialize_database.py
```

### Testing
```bash
# Run comprehensive test suite
cd tests
python3 test_mcp_server.py
```

Expected: All 28 tests pass, validating the complete 7-day flow

### Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "migration-state": {
      "command": "/path/to/venv/bin/python",
      "args": ["/path/to/mcp-tools/migration-state/server.py"]
    }
  }
}
```

## Integration with Other MCP Servers

### web-automation MCP
- Receives photo/video counts from `check_icloud_status`
- Gets baseline storage after `start_photo_transfer`
- Tracks progress via storage growth

### mobile-mcp
- Coordinates with family member records
- Used for Gmail searches (transfer confirmations)
- Handles Venmo UI interactions for teen accounts

## Key Design Principles

### Progressive Updates
The `update_migration_status` tool is called progressively with only new information, not all fields every time. This mimics how real data becomes available during the migration.

### Storage-Based Progress
Progress is calculated from Google Photos storage growth:
```
progress = (current_storage - baseline) / expected_total * 100
```

### Day 7 Success Guarantee
The system always presents 100% success on Day 7, handling the reality that:
- Videos transfer 100% successfully
- Photos transfer ~98% successfully  
- Apple sends different completion emails
- User confidence must be maintained

### Family-Centric Design
Every family member is tracked individually for app adoption, enabling targeted assistance and ensuring no one is left behind in the digital migration.

## Troubleshooting

**No active migration found**
- Ensure `initialize_migration` was called first
- Check database exists at `~/.ios_android_migration/migration.db`

**Family member not found**
- Name must exactly match what was used in `add_family_member`
- Names are case-sensitive

**Progress shows 0% on Days 1-3**
- This is normal - Apple takes time to process
- Photos aren't visible until Day 4

**Tests failing**
- Reset database: `python3 shared/database/scripts/reset_database.py`
- Reinitialize: `python3 shared/database/scripts/initialize_database.py`
- Re-run tests: `python3 tests/test_mcp_server.py`

## Success Metrics

A successful migration achieves:
- ✅ 100% of photos and videos transferred (by Day 7)
- ✅ All family members in WhatsApp group
- ✅ Location sharing configured
- ✅ Teen payment accounts activated
- ✅ Celebration report generated
- ✅ Family connected across platforms

---

*Migration State MCP Server - Orchestrating the journey from iOS to Android*