# Migration State MCP Server

## Overview

The Migration State MCP server provides 18 comprehensive tools for managing the complete iOS to Android migration journey. It serves as the central state management system, tracking photos AND videos separately, family members, app adoption, and progress through storage-based metrics over a realistic 7-day migration timeline. All tools return raw JSON for easy visualization in Claude's React environment.

## Key Features

- **18 MCP Tools**: Complete lifecycle management from initialization to celebration
- **DuckDB Backend**: Persistent storage in `~/.ios_android_migration/migration.db`
- **Video Support**: Separate tracking for photos and videos with independent status
- **Storage-Based Progress**: Accurate progress calculation using Google One metrics
- **7-Day Timeline**: Day-aware logic matching real-world migration timelines
- **Family Coordination**: Track multi-member app adoption and cross-platform connectivity
- **No Foreign Keys**: Optimized for DuckDB's UPDATE operations
- **JSON Responses**: Direct data for React dashboards and visualizations

## Database Architecture (v2.0)

### Tables (8)
- **migration_status**: Core migration tracking with storage baselines for progress
- **family_members**: Family details with email-based coordination
- **media_transfer**: Photo AND video transfer with separate status (formerly photo_transfer)
- **storage_snapshots**: NEW - Google One storage metrics for accurate progress calculation
- **app_setup**: WhatsApp, Maps, Venmo configuration tracking
- **family_app_adoption**: Per-member app installation status
- **daily_progress**: Day-by-day milestone snapshots with video metrics
- **venmo_setup**: Teen debit card activation tracking

### Views (4)
- **migration_summary**: Comprehensive status with video support
- **family_app_status**: Family member × app adoption matrix
- **active_migration**: Current migration with storage tracking
- **daily_progress_summary**: NEW - Day-specific messages with celebrations

### Design Decision: No Foreign Keys
Foreign key constraints were intentionally removed to work around a DuckDB limitation where UPDATE operations fail on tables with foreign key references. Referential integrity is enforced at the application layer through the migration_db.py module.

## Complete Tool Documentation

### 📊 Status & Monitoring Tools

#### 1. `get_migration_status`
**Purpose**: Get comprehensive current migration state  
**When to Use**: Daily check-ins, status updates, progress monitoring  
**Day**: Any day (1-7)  
**Parameters**:
- `migration_id` (optional): Specific migration ID, defaults to active migration

**Returns**: Complete migration details including phase, progress percentages, photo transfer status, family size
**State Impact**: Read-only, no state changes
**Agent Usage**: Start every daily check-in with this tool

---

#### 2. `get_migration_overview`
**Purpose**: High-level migration summary with calculated metrics  
**When to Use**: User asks "how are things going?" or needs dashboard data  
**Day**: Any day (1-7)  
**Parameters**: None

**Returns**: Phase, elapsed days, photo progress, family app adoption counts, ETA
**State Impact**: Read-only
**Agent Usage**: Perfect for React dashboard visualizations

---

#### 3. `get_daily_summary`
**Purpose**: Day-specific progress with appropriate expectations  
**When to Use**: Daily morning check-ins  
**Day**: Specific to requested day (1-7)  
**Parameters**:
- `day_number` (required): Which day (1-7) to summarize

**Returns**: Day-aware progress (photos 0% until Day 4), milestone messages, celebration flags
**State Impact**: Read-only
**Key Logic**:
- Day 1-3: Photos shown as "transfer running, not visible yet"
- Day 4: "Photos appearing!" celebration
- Day 5: Venmo cards arrival noted
- Day 7: Final celebration

---

#### 4. `get_statistics`
**Purpose**: Raw statistics for visualization  
**When to Use**: Creating React charts and progress bars  
**Day**: Any day  
**Parameters**:
- `include_history` (optional): Include previous migrations

**Returns**: Counts, percentages, rates for comprehensive dashboards
**State Impact**: Read-only
**Agent Usage**: Use with React components for visual progress

---

### 🚀 Initialization Tools (Day 1)

#### 5. `initialize_migration`
**Purpose**: Start a new 7-day migration journey  
**When to Use**: After user confirms they want to migrate and web-automation has checked iCloud  
**Day**: Day 1 only  
**Parameters**:
- `user_name` (required): User's name for personalization
- `photo_count` (required): From web-automation.check_icloud_status
- `storage_gb` (required): Total size from iCloud check
- `video_count` (optional): Video count from iCloud
- `years_on_ios` (optional, default: 18): For celebration messaging

**Returns**: New migration_id for all subsequent operations
**State Impact**: 
- Creates migration_status record
- Initializes photo_transfer record
- Creates app_setup entries for WhatsApp, Maps, Venmo
**Agent Usage**: First tool after user commits to migration

---

#### 6. `add_family_member`
**Purpose**: Register family members for cross-platform connectivity  
**When to Use**: After initialization, when user provides family details  
**Day**: Day 1 (can add more later if needed)  
**Parameters**:
- `name` (required): Family member's name
- `email` (required): For sending app invitations
- `role` (optional): "spouse" or "child"
- `age` (optional): Required for teens 13-17 (triggers Venmo teen account)

**Returns**: Confirmation with Venmo teen flag if applicable
**State Impact**:
- Creates family_members record
- Initializes family_app_adoption entries (WhatsApp, Maps, Venmo)
- Creates venmo_setup record if age 13-17
- Updates family_size in migration_status
**Agent Usage**: Loop through all family members on Day 1

---

#### 7. `start_photo_transfer`
**Purpose**: Record that Apple's transfer service has been initiated  
**When to Use**: After web-automation.start_photo_transfer succeeds  
**Day**: Day 1  
**Parameters**:
- `transfer_initiated` (optional, default: true): Confirmation flag

**Returns**: Confirmation with timeline expectations
**State Impact**:
- Updates photo_transfer status to "initiated"
- Sets photos_visible_day = 4
- Sets estimated_completion_day = 7
- Changes migration phase to "photo_transfer"
**Agent Usage**: Call immediately after web-automation initiates transfer

---

### 📈 Progress Update Tools (Days 1-7)

#### 8. `update_migration_progress`
**Purpose**: Advance through migration phases  
**When to Use**: When reaching major milestones  
**Day**: Various (1-7)  
**Parameters**:
- `migration_id` (required): Which migration to update
- `status` (required): New phase (initialization/photo_transfer/family_setup/validation/completed)
- `photos_transferred` (optional): Update photo counts
- `videos_transferred` (optional): Update video counts
- `total_size_gb` (optional): Update size transferred

**Returns**: Confirmation of phase change
**State Impact**:
- Updates migration_status.current_phase
- Can update overall_progress percentage
- Sets completed_at timestamp when status="completed"
**Agent Usage**: 
- Day 1: "photo_transfer" after transfer starts
- Day 3: "family_setup" when working on apps
- Day 7: "completed" when done

---

#### 9. `update_photo_progress`
**Purpose**: Track photo visibility in Google Photos  
**When to Use**: Days 4-7 when checking Google Photos app  
**Day**: Days 4-7 ONLY (photos not visible before Day 4)  
**Parameters**:
- `progress_percent` (required): Percentage complete (0-100)
- `photos_transferred` (optional): Actual count if available
- `videos_transferred` (optional): Video count
- `size_transferred_gb` (optional): Size in GB

**Returns**: Progress with daily transfer rate and ETA
**State Impact**:
- Updates photo_transfer progress fields
- Calculates daily transfer rates
- Updates status to "completed" at 100%
**Timeline**:
- Day 4: ~28% visible
- Day 5: ~57% visible
- Day 6: ~85% visible
- Day 7: 100% complete

---

#### 10. `update_family_member_apps`
**Purpose**: Track each family member's app adoption journey  
**When to Use**: Throughout Days 1-6 as family members progress  
**Day**: Days 1-6  
**Parameters**:
- `family_member_name` (required): Must match name from add_family_member
- `app_name` (required): "WhatsApp", "Google Maps", or "Venmo"
- `status` (required): "not_started", "invited", "installed", or "configured"

**Returns**: Previous and new status with timestamp
**State Impact**:
- Updates family_app_adoption status
- Records invitation_sent_at, installed_at, configured_at timestamps
- Updates app_setup.family_members_connected for WhatsApp
**Status Flow**:
- "not_started" → "invited" (email sent via mobile-mcp)
- "invited" → "installed" (app detected on their device)
- "installed" → "configured" (added to group/sharing)

---

### 👨‍👩‍👧‍👦 Family-Specific Tools (Days 5-6)

#### 11. `activate_venmo_card`
**Purpose**: Record teen debit card activation  
**When to Use**: Day 5 when physical cards arrive  
**Day**: Day 5 (cards take 3-5 days to arrive)  
**Parameters**:
- `family_member_name` (required): Teen's name (must be age 13-17)
- `card_last_four` (optional): Last 4 digits for records
- `card_activated` (optional, default: true): Confirmation

**Returns**: Activation confirmation
**State Impact**:
- Updates venmo_setup with card details and timestamps
- Sets family_app_adoption Venmo status to "configured"
- Updates app_setup if all cards activated
**Agent Usage**: Only for teens 13-17 who need Apple Cash replacement

---

### 📝 Utility Tools

#### 12. `log_migration_event`
**Purpose**: Create audit trail of significant events  
**When to Use**: Major milestones or issues  
**Day**: Any day  
**Parameters**:
- `event_type` (required): Category (milestone/error/user_action)
- `component` (required): System part (photo_transfer/whatsapp/venmo)
- `description` (required): What happened
- `metadata` (optional): Additional data

**Returns**: Confirmation of logging
**State Impact**: Creates log entry (implementation simplified)
**Agent Usage**: Log important events for troubleshooting

---

#### 13. `create_action_item`
**Purpose**: Coordinate with mobile-mcp for follow-ups  
**When to Use**: When family members need reminders  
**Day**: Any day  
**Parameters**:
- `action_type` (required): Type of action (email_invite/reminder)
- `description` (required): What needs to be done
- `target_member` (optional): Which family member

**Returns**: Confirmation (actual action handled by mobile-mcp)
**State Impact**: Minimal (placeholder for coordination)
**Agent Usage**: Creates reminder, mobile-mcp does actual email

---

#### 14. `get_pending_items`
**Purpose**: Find incomplete tasks  
**When to Use**: Daily checks to see what needs attention  
**Day**: Days 2-6  
**Parameters**:
- `category` (required): photos/contacts/apps/messages/all

**Returns**: List of pending items with status
**State Impact**: Read-only
**Agent Usage**: Use "apps" category to check family adoption

---

#### 15. `mark_item_complete`
**Purpose**: Mark specific tasks as done  
**When to Use**: When verifying individual completions  
**Day**: Any day  
**Parameters**:
- `item_type` (required): Type of item
- `item_id` (required): Unique identifier
- `details` (optional): Additional info

**Returns**: Completion confirmation
**State Impact**: Updates relevant completion flags
**Agent Usage**: Mark items done as verified

---

### 🎉 Completion Tool (Day 7)

#### 16. `generate_migration_report`
**Purpose**: Create celebratory final report  
**When to Use**: Day 7 after Apple confirmation email  
**Day**: Day 7  
**Parameters**:
- `format` (optional): "summary" or "detailed"

**Returns**: Celebration data with achievements, statistics, and emoji
**State Impact**: Read-only (generates report)
**Agent Usage**: Final celebration visualization

---

### 📊 Storage Tracking Tools (NEW in v2.0)

#### 17. `record_storage_snapshot`
**Purpose**: Record Google One storage metrics for progress tracking  
**When to Use**: When checking Google One storage page (Days 1,4,5,6,7)  
**Day**: Days 1-7 (baseline on Day 1, progress on Days 4-7)  
**Parameters**:
- `google_photos_gb` (required): Current Google Photos storage in GB
- `google_drive_gb` (optional): Current Google Drive storage
- `gmail_gb` (optional): Current Gmail storage  
- `day_number` (required): Which day of migration (1-7)
- `is_baseline` (optional): True if this is the initial baseline

**Returns**: Snapshot recorded with calculated growth and percentage
**State Impact**: Creates storage_snapshots record
**Agent Usage**: Called after checking Google One dashboard

---

#### 18. `get_storage_progress`
**Purpose**: Calculate transfer progress based on storage growth  
**When to Use**: To get accurate progress percentage from storage metrics  
**Day**: Days 4-7 (after photos start appearing)  
**Parameters**: None

**Returns**: Current storage metrics, growth, and calculated progress
**State Impact**: Read-only calculation from latest snapshot
**Agent Usage**: More accurate than Apple's estimates

## 7-Day Migration Timeline

### Day 1: Foundation
- `initialize_migration` - Start the journey
- `add_family_member` - Register all family members
- `start_photo_transfer` - Begin Apple transfer
- `record_storage_snapshot` - Baseline (13.88GB)
- `update_family_member_apps` - Send WhatsApp invitations

### Day 2-3: Family Adoption
- `update_family_member_apps` - Track WhatsApp installations
- `get_daily_summary` - Check Day 2 and 3 progress
- Continue invitations and app setup

### Day 4: Photos Appear! 🎉
- `record_storage_snapshot` - 120.88GB (28% complete)
- `update_photo_progress` - First photo visibility (~16,387 photos)
- `get_daily_summary` - Celebration milestone
- `update_family_member_apps` - Complete WhatsApp group

### Day 5: Venmo Cards
- `activate_venmo_card` - Teen cards arrive
- `record_storage_snapshot` - 220.88GB (57% complete)
- `update_photo_progress` - ~34,356 photos visible
- Location sharing setup via Maps

### Day 6: Near Completion
- `record_storage_snapshot` - 340.88GB (88% complete)
- `update_photo_progress` - ~53,010 photos visible
- Final app configurations
- Prepare for completion

### Day 7: Celebration! 🎊
- `record_storage_snapshot` - 396.88GB (100% complete)
- `update_photo_progress` - 60,238 photos, 2,418 videos complete
- `update_migration_progress` - Set to "completed"
- `generate_migration_report` - Final celebration

## Installation & Setup

```bash
# 1. Install dependencies
cd mcp-tools/migration-state
pip install -r requirements.txt

# 2. Initialize database (creates all tables)
python3 ../../shared/database/scripts/initialize_database.py

# 3. Run comprehensive tests (17 tests)
python3 tests/test_migration_state.py
```

## Claude Desktop Configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "migration-state": {
      "command": "/path/to/venv/bin/python",
      "args": [
        "/path/to/mcp-tools/migration-state/server.py"
      ]
    }
  }
}
```

## Usage Examples

### Day 1 Initialization
```
"I want to migrate from iPhone to Android"
→ initialize_migration(user_name="George", photo_count=60238, storage_gb=383)

"Add my family members"
→ add_family_member(name="Jaisy", email="jaisy@example.com", role="spouse")
→ add_family_member(name="Laila", email="laila@example.com", role="child", age=15)

"Start the photo transfer"
→ start_photo_transfer(transfer_initiated=true)
```

### Daily Check-ins
```
"Show me today's progress" (Day 4)
→ get_daily_summary(day_number=4)
Returns: {"photo_status": {"message": "Photos starting to appear!"}}

"How's the migration going?"
→ get_migration_overview()
Returns: Complete status with family adoption metrics
```

### Family Coordination
```
"Jaisy installed WhatsApp"
→ update_family_member_apps(
    family_member_name="Jaisy", 
    app_name="WhatsApp", 
    status="installed"
  )

"Add Jaisy to the family group"
→ update_family_member_apps(
    family_member_name="Jaisy", 
    app_name="WhatsApp", 
    status="configured"
  )
```

### Day 7 Completion
```
"Generate the final report"
→ generate_migration_report(format="detailed")
Returns: {
  "🎉": "MIGRATION COMPLETE!",
  "achievements": {
    "photos": "✅ 60,238 photos transferred",
    "family": "✅ 3 members connected"
  }
}
```

## Troubleshooting

### Common Issues

#### Foreign Key Errors
- **Problem**: UPDATE operations fail with foreign key constraint errors
- **Solution**: Database uses V2 schema without foreign keys. Re-run initialize_database.py

#### Database Locked
- **Problem**: "database is locked" errors
- **Solution**: Close DBeaver or other database viewers before running

#### Photos Not Showing Progress
- **Problem**: Photo progress shows 0% on Days 1-3
- **Solution**: This is correct! Photos aren't visible until Day 4

#### Family Member Not Found
- **Problem**: update_family_member_apps fails
- **Solution**: Name must exactly match what was used in add_family_member

### Debug Commands

```bash
# Check database directly
sqlite3 ~/.ios_android_migration/migration.db
.tables
SELECT * FROM migration_status;
SELECT * FROM family_app_adoption;

# View logs
tail -f ~/Dropbox/.../logs/migration-state.log

# Reset database (WARNING: deletes all data)
python3 ../../shared/database/scripts/reset_database.py
```

## Integration with Other MCP Servers

### With web-automation
- Receives photo counts from `check_icloud_status`
- Records transfer initiation from `start_photo_transfer`
- Tracks progress from `check_transfer_progress`

### With mobile-mcp
- Coordinates family app installations
- Email invitations sent via mobile-mcp Gmail control
- Venmo card activation through mobile app

### Data Flow
```
web-automation (Mac) → migration-state (Database) ← mobile-mcp (Android)
                              ↓
                    iOS2Android Agent (Orchestrator)
```

## Development Notes

### Adding New Tools
1. Add tool definition in `list_tools()`
2. Add handler in `call_tool()`
3. Update migration_db.py if needed
4. Add test in test_migration_state.py
5. Update this README

### Key Files
- `server.py` - MCP server implementation (18 tools)
- `migration_db.py` - Database operations (singleton)
- `initialize_database.py` - Schema creation
- `test_migration_state.py` - Comprehensive tests

### Design Principles
- Tools return raw JSON for visualization
- Day-aware logic for realistic timeline
- Email-based coordination (not phone numbers)
- Application-layer referential integrity
- Singleton database connection

## Success Metrics

A successful migration means:
- ✅ All photos transferred (100% by Day 7)
- ✅ Family WhatsApp group complete (Day 3)
- ✅ Location sharing active (Day 6)
- ✅ Teen Venmo cards working (Day 5)
- ✅ Celebration report generated (Day 7)

## Next Steps

With Phase 2 complete and all 18 tools operational:
1. Use iOS2Android agent instructions for orchestration
2. Test complete 7-day flow with real data
3. Monitor actual photo transfer progress
4. Refine day-specific logic based on results

---

*Version 2.0 - Phase 2 Complete (August 2025)*  
*18 Tools Operational with Video & Storage Support - Ready for iOS2Android Agent Integration*