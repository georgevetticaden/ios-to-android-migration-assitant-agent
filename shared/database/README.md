# iOS to Android Migration Database Documentation

## Overview

The migration database is a DuckDB-based system that tracks the complete 7-day iOS to Android migration journey. It uses 8 tables and 4 views to manage photo/video transfers, family member coordination, app adoption, and progress monitoring through storage-based metrics.

**Database Location**: `~/.ios_android_migration/migration.db`  
**Schema Version**: 2.0 (Video & Storage Support)  
**Engine**: DuckDB 1.3.2

## Structure

```
database/
├── schemas/           # Database schema definitions
│   └── migration_schema.sql  # v2.0 with media_transfer & storage_snapshots
├── scripts/          # Database management scripts
│   ├── initialize_database.py  # Creates all 8 tables and 4 views
│   └── reset_database.py       # Complete database reset
├── tests/            # Database tests
│   └── test_database.py  # 10 comprehensive tests
└── migration_db.py   # Core database interface with media support
```

## Database Tables (8)

### 1. migration_status
**Purpose**: Core migration tracking with Google One storage baselines  
**Populated By**: `migration-state` MCP server on Day 1  
**Key Fields**:
- `id`: MIG-YYYYMMDD-HHMMSS format
- `photo_count` (60,238), `video_count` (2,418): From iCloud
- `google_photos_baseline_gb` (13.88): Before transfer starts
- `current_phase`: initialization → media_transfer → family_setup → validation → completed

### 2. media_transfer (formerly photo_transfer)
**Purpose**: Track separate photo and video transfer progress  
**Populated By**: `web-automation` when Apple transfer starts (Day 1)  
**Key Fields**:
- `photo_status`, `video_status`: Independent tracking
- `transferred_photos`, `transferred_videos`: Current progress
- `photos_visible_day`: Day 4 (when photos appear)

### 3. storage_snapshots (NEW in v2.0)
**Purpose**: Track Google One storage growth for progress calculation  
**Populated By**: `migration-state` when checking Google One (Days 1,4,5,6,7)  
**Key Fields**:
- `storage_growth_gb`: 0→107→207→327→383GB progression
- `percent_complete`: Calculated from growth
- `estimated_photos_transferred`: Based on percentage

### 4. family_members
**Purpose**: Track family for cross-platform coordination  
**Populated By**: `migration-state` on Day 1  
**Example**: Jaisy (spouse), Laila (17), Ethan (15), Maya (11)

### 5. app_setup
**Purpose**: Track WhatsApp, Maps, Venmo installation  
**Populated By**: `migration-state` during initialization  
**Updates**: Throughout Days 1-6 as apps configured

### 6. family_app_adoption
**Purpose**: Per-member app adoption tracking  
**Populated By**: `migration-state` as members join apps  
**Status Flow**: not_started → invited → installed → configured

### 7. daily_progress
**Purpose**: Day-by-day milestone tracking  
**Populated By**: `migration-state` daily summaries  
**Key Milestones**: Day 4 "Photos appearing!", Day 7 "Complete!"

### 8. venmo_setup
**Purpose**: Teen debit card activation  
**Populated By**: `migration-state` for teens (Day 1), activated Day 5  

## Database Views (4)

### 1. migration_summary
Comprehensive overview joining all tables for dashboard display

### 2. active_migration
Current incomplete migration with all context

### 3. family_app_status
Matrix of family members × app adoption status

### 4. daily_progress_summary
Day-specific messages with celebration milestones

## Data Flow by MCP Server

### web-automation (Mac)
- **Day 1**: Initiates Apple transfer → creates media_transfer record
- **Day 1**: Provides iCloud metrics (photos, videos, storage)
- **Day 7**: Confirms completion via email check

### migration-state (Database)
- **Day 1**: Creates migration_status, family_members, app_setup
- **Days 1-7**: Records storage_snapshots for progress
- **Days 1-6**: Updates family_app_adoption as members join
- **Day 5**: Activates venmo_setup records
- **Daily**: Generates daily_progress summaries

### mobile-mcp (Android)
- **Day 1**: Sends WhatsApp invitations (updates family_app_adoption)
- **Days 4-7**: Checks Google Photos (triggers storage snapshots)
- **Day 5**: Activates Venmo cards through app

## Testing

### Run All Tests
```bash
# Reset and initialize
python3 shared/database/scripts/reset_database.py
python3 shared/database/scripts/initialize_database.py

# Run database tests (10/10 should pass)
python3 shared/database/tests/test_database.py
```

### Expected Results
- ✅ 8 tables created (including media_transfer, storage_snapshots)
- ✅ 4 views functional
- ✅ Storage tracking works
- ✅ Video support operational
- ✅ Foreign keys disabled (DuckDB workaround)

## Key Metrics

### Storage Progression (7-Day Timeline)
- Day 1: 13.88GB baseline
- Day 4: 120.88GB (28% complete) - Photos visible!
- Day 5: 220.88GB (57% complete)
- Day 6: 340.88GB (88% complete)
- Day 7: 396.88GB (100% complete)

### Media Distribution
- Photos: 60,238 items (~268GB, 70%)
- Videos: 2,418 items (~115GB, 30%)
- Total: 383GB over 7 days

## Architecture Decisions

### No Foreign Keys
Removed to work around DuckDB UPDATE limitation. Referential integrity enforced at application layer.

### Separate Photo/Video Tracking
Enables demo scenario where videos complete but photos show 98% with minor failures.

### Storage-Based Progress
More accurate than item counts since compression varies.