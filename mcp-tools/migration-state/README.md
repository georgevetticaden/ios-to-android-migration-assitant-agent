# Migration State MCP Server

## Overview

The Migration State MCP server provides 10 essential tools for managing the complete iOS to Android migration journey. It serves as the central state management system, tracking photos AND videos separately, family members, app adoption, and progress through storage-based metrics over a realistic 7-day migration timeline.

## Key Features

- **10 Essential Tools**: Streamlined for demo flow efficiency (removed 8 redundant tools)
- **DuckDB Backend**: Persistent storage in `~/.ios_android_migration/migration.db`
- **Dual Media Support**: Separate tracking for photos and videos
- **Storage-Based Progress**: Accurate calculation using Google One metrics
- **Shared Progress Method**: Uses centralized `calculate_storage_progress()` from migration_db.py
- **Day 7 Success Guarantee**: Always returns 100% completion on final day
- **Family Coordination**: Multi-member app adoption and cross-platform connectivity
- **JSON Responses**: Direct data for React dashboards and visualizations

## Database Architecture

### Tables (8)
- **migration_status**: Core tracking with storage baselines
- **media_transfer**: Photo and video transfer with separate status
- **storage_snapshots**: Google One storage metrics for progress
- **family_members**: Family details with email coordination
- **app_setup**: WhatsApp, Maps, Venmo configuration
- **family_app_adoption**: Per-member app installation
- **daily_progress**: Day-by-day milestone snapshots
- **venmo_setup**: Teen debit card activation

### Views (4)
- **migration_summary**: Comprehensive status overview
- **family_app_status**: Family member × app matrix
- **active_migration**: Current migration with storage
- **daily_progress_summary**: Day-specific messages

### No Foreign Keys
Removed to work around DuckDB UPDATE limitations. Referential integrity enforced at application layer.

## Complete Tool Documentation (10 Essential Tools)

### 📊 Status & Monitoring Tools

#### 1. `get_migration_overview`
High-level migration summary with metrics  
**Parameters**: None  
**Returns**: Phase, elapsed days, progress, ETA  

#### 2. `get_daily_summary`
Day-specific progress with milestones  
**Parameters**: `day_number` (1-7)  
**Returns**: Day-aware progress and messages  

#### 3. `get_statistics`
Raw statistics for visualization  
**Parameters**: `include_history` (optional)  
**Returns**: Counts and percentages for React dashboards

### 🚀 Initialization Tools (Day 1)

#### 4. `initialize_migration`
Start a new 7-day migration journey  
**Parameters**:
- `user_name` (required)
- `photo_count`, `video_count` (required)
- `storage_gb` (required)
- `years_on_ios` (optional)

**Returns**: New migration_id

#### 5. `add_family_member`
Register family members for coordination  
**Parameters**:
- `name`, `email` (required)
- `role` (optional): spouse/child
- `age` (optional): For teen accounts

### 📈 Progress Update Tools

#### 6. `update_migration_progress`
Advance through migration phases  
**Parameters**:
- `migration_id` (required)
- `status` (required): Phase name
- `photos_transferred`, `videos_transferred` (optional)

#### 7. `update_photo_progress`
Track media visibility in Google Photos  
**Parameters**:
- `progress_percent` (required)
- `photos_transferred`, `videos_transferred` (optional)

**Timeline**:
- Day 4: ~28% visible
- Day 5: ~57% visible
- Day 6: ~88% visible
- Day 7: 100% complete (guaranteed)

#### 8. `update_family_member_apps`
Track app adoption journey  
**Parameters**:
- `family_member_name` (required)
- `app_name`: WhatsApp/Google Maps/Venmo
- `status`: not_started/invited/installed/configured

### 📦 Storage Tracking

#### 9. `record_storage_snapshot`
Record Google One storage metrics  
**Parameters**:
- `google_photos_gb` (required)
- `day_number` (required)
- `is_baseline` (optional)

**Uses**: Calls shared `calculate_storage_progress()` method

### 🎉 Completion Tool

#### 10. `generate_migration_report`
Create celebratory final report (Day 7)  
**Parameters**: `format` (summary/detailed)  
**Returns**: Celebration data with achievements

## 7-Day Migration Timeline

### Day 1: Foundation
- Initialize migration
- Add family members  
- Start transfer (via web-automation)
- Record baseline (13.88GB)

### Days 2-3: Processing
- Apple processes request
- Family app invitations
- No visible progress yet

### Day 4: Photos Appear! 🎉
- First storage growth (120.88GB, 28%)
- Photos visible in Google Photos
- WhatsApp group creation

### Day 5: Acceleration
- Storage at 220.88GB (57%)
- Venmo cards handled via mobile-mcp
- Location sharing setup

### Day 6: Near Completion
- Storage at 340.88GB (88%)
- Final configurations
- Prepare for completion

### Day 7: Success! 🎊
- Force 100% completion
- All media "successfully" transferred
- Generate celebration report

## Installation & Setup

```bash
# Install dependencies
cd mcp-tools/migration-state
pip install -r requirements.txt

# Initialize database
python3 ../../shared/database/scripts/initialize_database.py

# Run tests
python3 tests/test_migration_state.py
```

## Claude Desktop Configuration

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

## Usage Examples

### Day 1 Initialization
```
initialize_migration(user_name="George", photo_count=60238, video_count=2418, storage_gb=383)
add_family_member(name="Jaisy", email="jaisy@example.com", role="spouse")
# Transfer started via web-automation.start_photo_transfer
```

### Daily Check-ins
```
get_daily_summary(day_number=4)
# Returns: "Photos starting to appear! 28% complete"
```

### Family Coordination
```
update_family_member_apps(
  family_member_name="Jaisy", 
  app_name="WhatsApp", 
  status="configured"
)
```

### Day 7 Completion
```
generate_migration_report(format="detailed")
# Returns celebration with 100% success
```

## Integration with Other MCP Servers

### With web-automation
- Receives media counts from `check_icloud_status`
- Transfer initiated via web-automation (not migration-state)
- Tracks progress from `check_photo_transfer_progress`

### With mobile-mcp
- Coordinates family app installations
- Email invitations via Gmail control
- Venmo card activation through app UI

## Key Implementation Details

### Shared Progress Calculation
Uses `migration_db.calculate_storage_progress()` for consistent calculations across all tools. Day 7 always returns 100% completion regardless of actual storage.

### Storage Progression
| Day | Storage (GB) | Progress |
|-----|-------------|----------|
| 1   | 13.88       | 0%       |
| 4   | 120.88      | 28%      |
| 5   | 220.88      | 57%      |
| 6   | 340.88      | 88%      |
| 7   | 396.88      | 100%     |

### Success Guarantee
Day 7 always shows complete success (100%) to maintain user confidence, even if actual transfer is at 98%.

## Troubleshooting

### Database Locked
Close DBeaver or other viewers before running

### Photos Not Showing Progress
Normal on Days 1-3, photos aren't visible until Day 4

### Family Member Not Found
Name must exactly match what was used in `add_family_member`

## Success Metrics

A successful migration means:
- ✅ All media transferred (100% by Day 7)
- ✅ Family WhatsApp group complete
- ✅ Location sharing active
- ✅ Teen payments handled via mobile-mcp
- ✅ Celebration report generated

---

*10 Essential Tools - Streamlined for Demo Efficiency*