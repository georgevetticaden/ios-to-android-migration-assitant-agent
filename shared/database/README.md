# iOS to Android Migration Database

## Overview

The migration database is a DuckDB-based system that tracks the complete 7-day iOS to Android migration journey. It uses 7 tables and 4 views to manage photo/video transfers, family member coordination, app adoption, and progress monitoring through storage-based metrics.

**Database Location**: `~/.ios_android_migration/migration.db`  
**Engine**: DuckDB

## Structure

```
database/
├── schemas/                      # Database schema definitions
│   └── migration_schema.sql     # Complete schema with media & storage support
├── scripts/                     # Database management scripts
│   ├── initialize_database.py   # Creates all 7 tables and 4 views
│   └── reset_database.py        # Complete database reset
├── tests/                       # Database tests
│   └── test_database.py         # Comprehensive test suite
└── migration_db.py              # Core database interface with calculate_storage_progress()
```

## Database Tables (7)

### 1. migration_status
**Purpose**: Core migration tracking with Google One storage baselines  
**Key Fields**:
- `id`: Unique migration identifier (MIG-YYYYMMDD-HHMMSS)
- `photo_count`, `video_count`: Media counts from iCloud
- `total_icloud_storage_gb`: Total storage to transfer (383GB)
- `google_photos_baseline_gb`: Storage before transfer starts
- `current_phase`: Migration workflow stage
- `overall_progress`: 0-100% completion

### 2. media_transfer
**Purpose**: Track photo and video transfer progress separately  
**Key Fields**:
- `transfer_id`: Unique transfer identifier (TRF-YYYYMMDD-HHMMSS)
- `photo_status`, `video_status`: Independent status tracking
- `transferred_photos`, `transferred_videos`: Current progress counts
- `transferred_size_gb`: Storage transferred so far
- `photos_visible_day`: When photos appear in Google Photos (Day 4)

### 3. storage_snapshots
**Purpose**: Time-series Google One storage measurements for progress calculation  
**Key Fields**:
- `google_photos_gb`: Current Google Photos storage
- `storage_growth_gb`: Growth since baseline
- `percent_complete`: Calculated progress percentage
- `estimated_photos_transferred`, `estimated_videos_transferred`: Based on storage
- `is_baseline`: Marks initial measurement

### 4. family_members
**Purpose**: Track family members for cross-platform coordination  
**Key Fields**:
- `name`, `email`: Family member identification
- `role`: spouse/child/parent
- `age`: Used for teen account determination
- `staying_on_ios`: If they're keeping iPhone

### 5. family_app_adoption
**Purpose**: Per-member app adoption tracking  
**Key Fields**:
- `family_member_id`: Links to family_members
- `app_name`: Which app (WhatsApp/Google Maps/Venmo)
- `status`: not_started → invited → installed → configured
- `whatsapp_in_group`: Boolean for WhatsApp group membership
- `location_sharing_received`: Boolean for Maps location sharing
- `configuration_details`: App-specific settings

### 6. daily_progress
**Purpose**: Day-by-day milestone tracking  
**Key Fields**:
- `day_number`: 1-7 of migration journey
- `photos_transferred`, `videos_transferred`: Daily counts
- `storage_percent_complete`: Progress percentage
- `key_milestone`: Human-readable achievement

### 7. venmo_setup
**Purpose**: Teen debit card activation tracking  
**Key Fields**:
- `family_member_id`: Links to teen family member
- `card_ordered_at`, `card_arrived_at`, `card_activated_at`: Timeline
- `card_last_four`: Card identification

## Database Views (4)

### 1. migration_summary
Complete overview joining all tables for comprehensive status display

### 2. active_migration
Current incomplete migration with all related data

### 3. family_app_status
Matrix view showing each family member's app adoption status

### 4. daily_progress_summary
Aggregated daily progress with milestone messages

## MCP Tool Integration

The database is accessed through 7 MCP tools provided by the migration-state server:

| MCP Tool | Database Operations |
|----------|-------------------|
| `initialize_migration` | INSERTS into migration_status, media_transfer |
| `add_family_member` | INSERTS into family_members, venmo_setup, family_app_adoption |
| `update_migration_status` | UPDATES migration_status, INSERTS daily_progress |
| `update_family_member_apps` | SELECTS family_members, UPDATES family_app_adoption, venmo_setup |
| `get_migration_status` | SELECTS from all 7 tables for comprehensive status |
| `get_family_members` | Complex JOINs with family_app_adoption, venmo_setup |

## Key Methods

### calculate_storage_progress()
Central method in `migration_db.py` that calculates transfer progress based on storage growth:

```python
async def calculate_storage_progress(
    migration_id: str,
    current_storage_gb: float,
    day_number: int = None
) -> Dict[str, Any]
```

**Features**:
- Storage-based calculation for accuracy
- Day 7 override (always returns 100%)
- Item estimation based on storage ratios
- Contextual milestone messages

### MigrationDatabase Singleton
The `MigrationDatabase` class uses a singleton pattern to ensure all MCP tools share the same database connection:

```python
db = MigrationDatabase()  # Always returns the same instance
migration_id = await db.create_migration(user_name="George", years_on_ios=18)
```

## Data Flow

### Day 1: Initialization
- `initialize_migration` creates migration_status record
- `add_family_member` adds 4 family members (spouse + 3 children)
- `update_migration_status` called 3 times:
  - First: Add iCloud metrics (photo_count, video_count, storage)
  - Second: Set Google Photos baseline after transfer starts
  - Third: Add family information (family_size, whatsapp_group_name)
- Family app adoption records initialized

### Days 2-3: Processing
- Apple processes transfer request
- `get_migration_status` called daily (shows 0% progress)
- `update_migration_status` updates overall_progress
- Family app invitations tracked via `update_family_member_apps`

### Day 4: Photos Appear
- First storage growth detected (~28% complete)
- Photos become visible in Google Photos
- `storage_snapshots` records growth metrics
- WhatsApp group fully configured

### Days 5-6: Acceleration
- Rapid storage growth (57% → 88%)
- Venmo teen cards activated (Day 5)
- Google Maps location sharing configured
- Daily `get_migration_status` calls show increasing progress

### Day 7: Completion
- `calculate_storage_progress` forces 100% completion
- `update_migration_status` sets phase to "completed"
- `get_migration_status` returns hardcoded 100% for Day 7
- Shows complete success regardless of actual metrics

## Testing

```bash
# Initialize database
python3 shared/database/scripts/initialize_database.py

# Run tests
python3 shared/database/tests/test_database.py

# Reset if needed
python3 shared/database/scripts/reset_database.py
```

## Storage Metrics

### Expected Progression
| Day | Storage (GB) | Progress | Milestone |
|-----|-------------|----------|-----------|
| 1   | 13.88       | 0%       | Transfer initiated |
| 4   | 120.88      | 28%      | Photos visible! |
| 5   | 220.88      | 57%      | Accelerating |
| 6   | 340.88      | 88%      | Nearly complete |
| 7   | 396.88      | 100%     | Success! |

### Media Distribution
- **Photos**: 65% of storage (~5.5MB average)
- **Videos**: 35% of storage (~150MB average)
- **Total**: 383GB over 7 days

## Architecture Decisions

### No Foreign Keys
DuckDB doesn't support foreign keys with UPDATE operations. Referential integrity is enforced at the application layer instead.

### Separate Status Tracking
Photo and video statuses tracked independently to handle the reality where videos transfer 100% but photos may only reach 98%.

### Storage-Based Progress
More accurate than counting items since compression and quality vary. Google One storage metrics provide reliable progress indication.

### Day 7 Success Override
Always returns 100% completion on Day 7 for demo confidence, regardless of actual storage metrics.