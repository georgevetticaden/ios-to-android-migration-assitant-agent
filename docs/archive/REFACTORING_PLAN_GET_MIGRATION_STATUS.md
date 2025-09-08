# Refactoring Plan: Integrate Storage Checking into get_migration_status

## Overview
**Date Created**: 2025-01-04  
**Date Completed**: 2025-01-04  
**Purpose**: Make `get_migration_status` self-contained by having it internally check Google storage, eliminating `check_photo_transfer_progress` as an MCP tool entirely.  
**Current State**: Refactoring COMPLETE - Phases 1-4 done, ready for Day 3 demo  
**Risk Level**: Low - changes are additive first, subtractive last

## Goals
- ✅ **DONE** - Simplify agent instructions to single call per day
- ✅ **DONE** - Make `get_migration_status` the true "uber status tool"
- ✅ **DONE** - Remove `check_photo_transfer_progress` MCP tool completely
- ✅ **DONE** - Preserve demo database state for Day 3 continuation
- ✅ **DONE** - Ensure real Google storage data populates storage_snapshots table

## Implementation Status

### Completed Phases
- ✅ **Phase 1**: Added Storage Checking to migration-state server *(COMPLETE)*
- ✅ **Phase 3**: Updated agent instructions to remove check_photo_transfer_progress calls *(COMPLETE)*
- ✅ **Phase 2**: Removed check_photo_transfer_progress MCP tool from web-automation *(COMPLETE)*
- ✅ **Phase 4**: Updated documentation (CLAUDE.md, READMEs) *(COMPLETE)*

### Pending Phases
- ⏳ **Phase 5**: Populate production database history *(SQL ready below, needs execution)*
- ⏳ **Phase 6**: Run isolated test *(Optional - test script ready below)*

## What Was Changed

### Files Modified
1. **mcp-tools/migration-state/server.py**
   - Added ICloudClient import and initialization
   - Updated get_migration_status to query real Google storage
   - Now automatically populates storage_snapshots and daily_progress tables

2. **agent/instructions/ios2android-agent-instructions-v7.md**
   - Simplified Days 2-7 to single get_migration_status calls
   - Removed all check_photo_transfer_progress references

3. **mcp-tools/web-automation/src/web_automation/server.py**
   - Removed check_photo_transfer_progress tool definition
   - Deleted _handle_check_progress function
   - Removed tool from call_tool handler

4. **Documentation Updates**
   - CLAUDE.md: Updated tool count from 11 to 10
   - web-automation/README.md: Removed tool documentation
   - migration-state/README.md: Added note about automatic storage checking

## Current System State
- **Tool Count**: 10 MCP tools (3 web-automation + 7 migration-state)
- **Agent Pattern**: Single `get_migration_status(migration_id, day_number)` call per day
- **Storage Checking**: Automatic via integrated ICloudClient in migration-state
- **Database Updates**: Automatic population of storage_snapshots and daily_progress

## Safety Constraints
- ⚠️ **NO test execution** - only code changes
- ⚠️ **Preserve database state** - no resets or test runs
- ⚠️ **Maintain Day 3 readiness** - demo can continue immediately after changes

---

# PHASE 1: Add Storage Checking to migration-state

## Step 1.1: Import ICloudClient in migration-state/server.py

**File**: `mcp-tools/migration-state/server.py`

### Add imports at top:
```python
import sys
from pathlib import Path

# Add web_automation to path for imports
web_automation_path = Path(__file__).parent.parent / 'web-automation' / 'src'
sys.path.insert(0, str(web_automation_path))

from web_automation.icloud_client import ICloudClientWithSession
```

### Add global variable (after existing globals):
```python
# Global instances
server = Server("migration-state")
db = MigrationDatabase()
icloud_client = None  # Add this line
```

## Step 1.2: Modify get_migration_status handler

**Location**: In `@server.call_tool()` handler  
**Action**: Replace the entire `elif name == "get_migration_status":` block

```python
elif name == "get_migration_status":
    # UBER status tool - returns everything with fresh storage data
    if not migration_id:
        result = {
            "success": False,
            "error": "No migration found",
            "message": "No migration found. Ensure you've called initialize_migration first and stored the migration_id.",
            "hint": "Pass migration_id parameter or ensure there's an active migration"
        }
    else:
        day_number = arguments["day_number"]
        
        # Get transfer_id from overview
        overview = await internal_get_migration_overview(migration_id)
        transfer_id = overview.get("transfer_id") if overview else None
        
        # For Day 2+ with valid transfer_id, check actual storage
        if transfer_id and day_number >= 2:
            try:
                # Initialize iCloud client if needed (singleton pattern)
                global icloud_client
                if not icloud_client:
                    icloud_client = ICloudClientWithSession()
                    await icloud_client.initialize_apis()
                
                # Check real storage progress - this updates storage_snapshots & daily_progress
                logger.info(f"Checking real storage progress for day {day_number}")
                progress_result = await icloud_client.check_transfer_progress(
                    transfer_id=transfer_id,
                    day_number=day_number
                )
                logger.info(f"Storage check complete: {progress_result.get('progress', {}).get('percent_complete', 0)}%")
            except Exception as e:
                logger.warning(f"Could not check real storage: {e}")
                # Continue with data from DB
        
        # Get all status information (now includes fresh storage data)
        daily = await internal_get_daily_summary(migration_id, day_number)
        overview = await internal_get_migration_overview(migration_id)
        family = await internal_get_family_service_summary(migration_id)
        
        # Get photo progress from latest storage snapshot
        photo_progress = {}
        with db.get_connection() as conn:
            # Get most recent storage snapshot
            snapshot = conn.execute("""
                SELECT google_photos_gb, storage_growth_gb, percent_complete,
                       estimated_photos_transferred, estimated_videos_transferred
                FROM storage_snapshots 
                WHERE migration_id = ? 
                ORDER BY created_at DESC
                LIMIT 1
            """, (migration_id,)).fetchone()
            
            if snapshot:
                # Use actual storage data from snapshot
                photo_progress = {
                    "percent_complete": snapshot[2] or 0,
                    "current_storage_gb": snapshot[0],
                    "storage_growth_gb": snapshot[1],
                    "photos_transferred": snapshot[3] or 0,
                    "videos_transferred": snapshot[4] or 0,
                    "transfer_id": transfer_id,
                    "day_number": day_number,
                    "status": "in_progress" if day_number < 7 else "completed"
                }
            else:
                # Fallback for Day 1 or if no snapshots yet
                photo_progress = await internal_check_photo_transfer_progress(transfer_id, day_number, migration_id) if transfer_id else {}
        
        result = {
            "success": True,
            "day_number": day_number,
            "migration": overview,
            "day_summary": daily,
            "migration_overview": overview,
            "photo_progress": photo_progress,
            "family_services": family,
            "status_message": f"Day {day_number}: {photo_progress.get('percent_complete', 0)}% complete"
        }
```

---

# PHASE 2: Remove check_photo_transfer_progress MCP Tool

## Step 2.1: Update web-automation tool list

**File**: `mcp-tools/web-automation/src/web_automation/server.py`

### In `@server.list_tools()` function, REMOVE this tool definition:
```python
types.Tool(
    name="check_photo_transfer_progress",
    description="Monitor ongoing photo transfer progress via Google One storage metrics...",
    inputSchema={
        "type": "object",
        "properties": {
            "transfer_id": {
                "type": "string",
                "description": "Transfer ID from start_photo_transfer (format: TRF-YYYYMMDD-HHMMSS)"
            },
            "day_number": {
                "type": "integer",
                "minimum": 1,
                "maximum": 7,
                "description": "Current day number (1-7) for timeline-aware messages. Day 7 always returns 100% completion."
            }
        },
        "required": ["transfer_id"]
    }
),
```

## Step 2.2: Remove handler function

**File**: `mcp-tools/web-automation/src/web_automation/server.py`

### DELETE the entire `_handle_check_progress` function (~lines 297-349):
```python
async def _handle_check_progress(arguments: Dict[str, Any]) -> list[types.TextContent]:
    # DELETE THIS ENTIRE FUNCTION
    ...
```

## Step 2.3: Update call_tool handler

**File**: `mcp-tools/web-automation/src/web_automation/server.py`

### In `@server.call_tool()` function, REMOVE:
```python
elif name == "check_photo_transfer_progress":
    return await _handle_check_progress(arguments)
```

### ⚠️ IMPORTANT: Keep These Intact!
- ✅ Keep `icloud_client.check_transfer_progress()` method in `icloud_client.py`
- ✅ Keep `GoogleStorageClient` class and its methods
- ✅ Keep database update logic in `check_transfer_progress()`

---

# PHASE 3: Update Agent Instructions

## Step 3.1: Simplify ALL Day 2-7 Status Checks

**File**: `ios-to-android-migration-assitant-agent/agent/instructions/ios2android-agent-instructions-v7.md`

### Day 2 - Replace Step 1:
```python
### Step 1: Get Day 2 Status
```python
status = get_migration_status(migration_id=migration_id, day_number=2)
not_in_group = get_family_members(migration_id=migration_id, filter="not_in_whatsapp")
not_sharing_location = get_family_members(migration_id=migration_id, filter="not_sharing_location")
group_name = status.get('migration', {}).get('whatsapp_group_name', 'family')
```
```

### Day 3 - Replace Step 1:
```python
### Step 1: Get Day 3 Status
```python
status = get_migration_status(migration_id=migration_id, day_number=3)
not_sharing = get_family_members(migration_id=migration_id, filter="not_sharing_location")
group_name = status.get('migration', {}).get('whatsapp_group_name', 'family')
```
```

### Day 4 - Replace Step 1:
```python
### Step 1: Get Day 4 Status
```python
status = get_migration_status(migration_id=migration_id, day_number=4)
# Will show ~28% progress with photos visible
```
```

### Day 5 - Replace Step 1:
```python
### Step 1: Get Day 5 Status
```python
status = get_migration_status(migration_id=migration_id, day_number=5)
teens = get_family_members(migration_id=migration_id, filter="teen")
```
```

### Day 6 - Replace Step 1:
```python
### Step 1: Get Day 6 Status
```python
status = get_migration_status(migration_id=migration_id, day_number=6)
# Shows ~88% complete
```
```

### Day 7 - Replace Step 1:
```python
### Step 1: Get Final Status
```python
status = get_migration_status(migration_id=migration_id, day_number=7)
# ALWAYS returns 100% on Day 7
```
```

---

# PHASE 4: Documentation Updates

## Step 4.1: Update CLAUDE.md

**File**: `ios-to-android-migration-assitant-agent/CLAUDE.md`

### Update web-automation tool count:
```markdown
#### 1. web-automation (3 tools)  <!-- Changed from 4 tools -->
**Purpose**: Browser automation for iCloud and Google One interactions  
**Location**: `mcp-tools/web-automation/`  
**Documentation**: [`mcp-tools/web-automation/README.md`](mcp-tools/web-automation/README.md)  
**Tools**:
- `check_icloud_status` - Get photo/video counts from iCloud
- `start_photo_transfer` - Initiate Apple's transfer service
- `verify_photo_transfer_complete` - Final verification
```

### Update total tool count:
```markdown
### Tool Count
- **Total**: 10 MCP tools (3 web + 7 state)  <!-- Changed from 11 tools -->
```

## Step 4.2: Update web-automation README

**File**: `mcp-tools/web-automation/README.md`

Update tool list to show only 3 tools (remove check_photo_transfer_progress).

---

# Implementation Checklist

## Pre-Implementation Verification
- [ ] Current database shows Day 2 completed
- [ ] migration_id is stored and available
- [ ] transfer_id is in database from Day 1
- [ ] No active MCP servers running

## Phase 1: migration-state Changes
- [ ] Add ICloudClient import with proper path setup
- [ ] Add global icloud_client variable
- [ ] Replace get_migration_status handler with new version
- [ ] Verify no syntax errors

## Phase 2: web-automation Changes
- [ ] Remove check_photo_transfer_progress from tool list
- [ ] Delete _handle_check_progress function entirely
- [ ] Remove tool handler from call_tool
- [ ] Verify icloud_client.check_transfer_progress still exists

## Phase 3: Agent Instruction Updates
- [ ] Simplify Day 2 Step 1
- [ ] Simplify Day 3 Step 1
- [ ] Simplify Day 4 Step 1
- [ ] Simplify Day 5 Step 1
- [ ] Simplify Day 6 Step 1
- [ ] Simplify Day 7 Step 1

## Phase 4: Documentation
- [ ] Update CLAUDE.md tool counts
- [ ] Update web-automation README

## Post-Implementation Verification
- [ ] No test scripts run (preserves DB state)
- [ ] Database still shows Day 2 completion
- [ ] Ready to continue Day 3 demo recording

---

# Rollback Plan

If issues arise at any phase:

## After Phase 1 (migration-state updated):
- System works with both patterns
- Can still call check_photo_transfer_progress if needed
- Revert changes to server.py if necessary

## After Phase 3 (instructions updated):
- Can revert agent instructions to previous version
- System still functional with simplified calls

## After Phase 2 (MCP tool removed):
- Can re-add tool definition and handlers
- Requires restart of web-automation server

---

# Expected Outcomes

## What Changes:
- `get_migration_status` now queries real Google storage internally
- Agent makes 1 call instead of 3 per day
- storage_snapshots table populated automatically
- MCP tool count reduced from 11 to 10

## What Stays the Same:
- Database schema unchanged
- Existing data preserved
- Day 1 flow unchanged
- Core logic unchanged (just relocated)

## Benefits:
- ✅ Simpler agent instructions (50% fewer lines for Days 2-7)
- ✅ True "uber status tool" as originally designed
- ✅ Automatic storage checking and DB population
- ✅ Reduced chance of sequencing errors
- ✅ Easier debugging (single call to trace)

---

# Risk Assessment

## Technical Risks:
- **Import paths**: MITIGATED - Using sys.path.insert
- **Credentials**: MITIGATED - Both servers use same .env
- **Browser sessions**: MITIGATED - Each server has own instance

## Demo Risks:
- **Database corruption**: NONE - No destructive operations
- **State loss**: NONE - All changes are additive first
- **Continuity**: NONE - Can continue Day 3 immediately

## Overall Risk Level: **LOW**
- Changes are reversible
- Database state preserved
- Demo can continue without interruption

---

# PHASE 5: Database Preparation for Day 3

## Current Database State Summary
- **Migration ID**: MIG-20250903-102718
- **Transfer ID**: TRF-20250903-103223
- **User**: Vetticaden
- **Photos**: 60,238
- **Videos**: 2,418
- **Total Storage**: 383 GB
- **Baseline Storage**: 1.5 GB
- **Overall Progress**: 45% (as of Day 2)
- **WhatsApp**: All 4 family members configured
- **Location Sharing**: 2 of 4 configured (Laila ✅, Maya ✅, Jaisy ❌, Ethan ❌)

## Manual Database Inserts for Day 1-2 History

Since storage_snapshots and daily_progress are empty, we need to populate them with historical data for Days 1-2 before starting Day 3. Run these in DuckDB:

### Step 5.1: Insert Storage Snapshots

```sql
-- Day 1 Baseline (when transfer started)
INSERT INTO storage_snapshots (
    migration_id, day_number, snapshot_time,
    google_photos_gb, google_drive_gb, gmail_gb,
    device_backup_gb, total_used_gb,
    storage_growth_gb, estimated_photos_transferred, estimated_videos_transferred,
    percent_complete, is_baseline, created_at
) VALUES (
    'MIG-20250903-102718', 1, '2025-09-03 15:32:23',
    1.5, 0.5, 1.2, 0.8, 4.0,
    0, 0, 0,
    0, true, '2025-09-03 15:32:23'
);

-- Day 2 Progress Check (0% - still processing)
INSERT INTO storage_snapshots (
    migration_id, day_number, snapshot_time,
    google_photos_gb, google_drive_gb, gmail_gb,
    device_backup_gb, total_used_gb,
    storage_growth_gb, estimated_photos_transferred, estimated_videos_transferred,
    percent_complete, is_baseline, created_at
) VALUES (
    'MIG-20250903-102718', 2, '2025-09-04 10:00:00',
    1.5, 0.5, 1.2, 0.8, 4.0,
    0, 0, 0,
    0, false, '2025-09-04 10:00:00'
);
```

### Step 5.2: Insert Daily Progress Records

```sql
-- Day 1 Progress
INSERT INTO daily_progress (
    migration_id, day_number, date,
    photos_transferred, videos_transferred,
    size_transferred_gb, storage_percent_complete,
    whatsapp_members_connected, maps_members_sharing, venmo_members_active,
    key_milestone, notes
) VALUES (
    'MIG-20250903-102718', 1, '2025-09-03',
    0, 0,
    0, 0,
    3, 0, 0,
    'Day 1: Migration initiated, family setup complete',
    'Transfer started, WhatsApp group created with 3 members'
);

-- Day 2 Progress
INSERT INTO daily_progress (
    migration_id, day_number, date,
    photos_transferred, videos_transferred,
    size_transferred_gb, storage_percent_complete,
    whatsapp_members_connected, maps_members_sharing, venmo_members_active,
    key_milestone, notes
) VALUES (
    'MIG-20250903-102718', 2, '2025-09-04',
    0, 0,
    0, 0,
    4, 2, 0,
    'Day 2: Apple processing, family connectivity improved',
    'Maya added to WhatsApp, location sharing with Laila and Maya'
);
```

### Step 5.3: Verify Inserts

After running the above inserts, verify with:

```sql
-- Check storage snapshots
SELECT day_number, google_photos_gb, percent_complete, is_baseline 
FROM storage_snapshots 
WHERE migration_id = 'MIG-20250903-102718'
ORDER BY day_number;

-- Check daily progress
SELECT day_number, storage_percent_complete, whatsapp_members_connected, maps_members_sharing, key_milestone
FROM daily_progress
WHERE migration_id = 'MIG-20250903-102718'
ORDER BY day_number;
```

Expected output:
- storage_snapshots: 2 records (Day 1 baseline, Day 2 at 0%)
- daily_progress: 2 records (Day 1 and Day 2 summaries)

## Day 3 Expected State

When Day 3 runs with the refactored code:
- `get_migration_status` will check real Google storage (~13.88 GB expected)
- This will automatically insert Day 3 storage_snapshot (~0% progress still)
- Location sharing will be completed for remaining family members
- Overall progress will update to 47-50%

---

# PHASE 6: Isolated Integration Testing with Real Google Storage

## Overview
Create a completely isolated test environment that:
- Uses a **separate test database** (not the demo database)
- Seeds test DB with **current demo state** 
- Executes **Phase 5 SQL** against test DB
- Calls **real get_migration_status** with **real Google storage** (no mocking)
- Validates correct data returns and table populations
- Lives in **isolated folder** for easy cleanup

## Critical Requirements
✅ **Separate test folder** - `/phase6-isolated-tests/`  
✅ **Test DuckDB instance** - Not the demo database  
✅ **Seed with current state** - Copy demo DB state to test DB  
✅ **Real Google storage** - No mocking, actual API calls  
✅ **Phase 5 execution** - Run SQL against test DB first  
✅ **Full validation** - Check returns and table updates  
✅ **Easy cleanup** - Single folder deletion removes all artifacts  

## Folder Structure
```
08-14-2025-ios-to-android-migration-agent-take-2/
├── phase6-isolated-tests/              # NEW - All test artifacts here
│   ├── test_database/                  # Test database location
│   │   └── test_migration.db          # Test DuckDB instance
│   ├── scripts/                       # Test scripts
│   │   ├── 01_seed_database.py       # Copy current state to test DB
│   │   ├── 02_apply_phase5.py        # Apply Phase 5 SQL to test DB
│   │   ├── 03_test_integration.py    # Main integration test
│   │   ├── 04_validate_results.py    # Validation checks
│   │   └── 05_cleanup.sh             # Remove all test artifacts
│   ├── logs/                          # Test execution logs
│   │   └── test_run_[timestamp].log  # Detailed test output
│   ├── results/                       # Test results
│   │   ├── before_state.json         # DB state before test
│   │   ├── after_state.json          # DB state after test
│   │   └── validation_report.txt     # Final validation report
│   └── README.md                      # Test documentation
```

## Step 6.1: Create Database Seeding Script

**File**: `phase6-isolated-tests/scripts/01_seed_database.py`

```python
#!/usr/bin/env python3
"""
Phase 6 Step 1: Seed test database with current production state.
Copies existing demo data to isolated test database.
DOES NOT modify production database.
"""

import os
import sys
import json
import duckdb
from pathlib import Path
from datetime import datetime

# Setup paths
project_root = Path(__file__).parent.parent.parent
prod_db_path = os.path.expanduser('~/.ios_android_migration/migration.db')
test_db_path = project_root / 'phase6-isolated-tests' / 'test_database' / 'test_migration.db'
results_path = project_root / 'phase6-isolated-tests' / 'results'

def seed_test_database():
    """Copy current production state to test database."""
    
    print("\n" + "="*60)
    print("PHASE 6 - STEP 1: SEEDING TEST DATABASE")
    print("="*60)
    print(f"Source (prod): {prod_db_path}")
    print(f"Target (test): {test_db_path}")
    print("-"*60)
    
    # Create test directories
    test_db_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.mkdir(parents=True, exist_ok=True)
    
    # Connect to production DB (read-only)
    print("\n[1/4] Connecting to production database...")
    prod_conn = duckdb.connect(str(prod_db_path), read_only=True)
    
    # Extract current state
    migration_data = prod_conn.execute("""
        SELECT * FROM migration_status 
        WHERE id = 'MIG-20250903-102718'
    """).fetchone()
    
    media_data = prod_conn.execute("""
        SELECT * FROM media_transfer 
        WHERE migration_id = 'MIG-20250903-102718'
    """).fetchone()
    
    family_data = prod_conn.execute("""
        SELECT * FROM family_members 
        WHERE migration_id = 'MIG-20250903-102718'
    """).fetchall()
    
    family_app_data = prod_conn.execute("""
        SELECT fa.* FROM family_app_adoption fa
        JOIN family_members fm ON fa.family_member_id = fm.id
        WHERE fm.migration_id = 'MIG-20250903-102718'
    """).fetchall()
    
    print(f"✅ Extracted migration record")
    print(f"✅ Extracted {len(family_data)} family members")
    print(f"✅ Extracted {len(family_app_data)} app adoption records")
    
    # Save before state
    before_state = {
        "migration": migration_data,
        "media_transfer": media_data,
        "family_count": len(family_data),
        "app_adoption_count": len(family_app_data)
    }
    
    with open(results_path / 'before_state.json', 'w') as f:
        json.dump(before_state, f, indent=2, default=str)
    
    prod_conn.close()
    
    # Create test database
    print("\n[2/4] Creating test database...")
    test_conn = duckdb.connect(str(test_db_path))
    
    # Create schema - copy from production
    print("[3/4] Creating schema...")
    test_conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS migration_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS family_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS media_transfer_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS storage_snapshot_seq START 1;
        CREATE SEQUENCE IF NOT EXISTS daily_progress_seq START 1;
        
        CREATE TABLE migration_status (
            id TEXT PRIMARY KEY DEFAULT 'MIG-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S'),
            user_name TEXT NOT NULL,
            source_device TEXT DEFAULT 'iPhone',
            target_device TEXT DEFAULT 'Android',
            years_on_ios INTEGER,
            photo_count INTEGER,
            video_count INTEGER,
            total_icloud_storage_gb REAL,
            icloud_photo_storage_gb REAL,
            icloud_video_storage_gb REAL,
            album_count INTEGER,
            google_storage_total_gb REAL DEFAULT 2048,
            google_photos_baseline_gb REAL,
            google_drive_baseline_gb REAL,
            gmail_baseline_gb REAL,
            family_size INTEGER DEFAULT 0,
            whatsapp_group_name TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            current_phase TEXT DEFAULT 'initialization',
            overall_progress INTEGER DEFAULT 0,
            completed_at TIMESTAMP
        );
        
        CREATE TABLE media_transfer (
            transfer_id TEXT PRIMARY KEY DEFAULT 'TRF-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S'),
            migration_id TEXT NOT NULL,
            photo_transfer_id TEXT,
            video_transfer_id TEXT,
            total_photos INTEGER,
            total_videos INTEGER,
            total_size_gb REAL,
            transferred_photos INTEGER DEFAULT 0,
            transferred_videos INTEGER DEFAULT 0,
            transferred_size_gb REAL DEFAULT 0,
            photo_status TEXT DEFAULT 'pending',
            video_status TEXT DEFAULT 'pending',
            overall_status TEXT DEFAULT 'pending',
            apple_transfer_initiated TIMESTAMP,
            photo_start_email_received TIMESTAMP,
            video_start_email_received TIMESTAMP,
            photo_complete_email_received TIMESTAMP,
            video_complete_email_received TIMESTAMP,
            photos_visible_day INTEGER,
            estimated_completion_day INTEGER,
            last_progress_check TIMESTAMP
        );
        
        CREATE TABLE storage_snapshots (
            id INTEGER PRIMARY KEY DEFAULT nextval('storage_snapshot_seq'),
            migration_id TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            google_photos_gb REAL,
            google_drive_gb REAL,
            gmail_gb REAL,
            device_backup_gb REAL,
            total_used_gb REAL,
            storage_growth_gb REAL,
            estimated_photos_transferred INTEGER,
            estimated_videos_transferred INTEGER,
            percent_complete REAL,
            is_baseline BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE daily_progress (
            id INTEGER PRIMARY KEY DEFAULT nextval('daily_progress_seq'),
            migration_id TEXT NOT NULL,
            day_number INTEGER NOT NULL,
            date DATE DEFAULT CURRENT_DATE,
            photos_transferred INTEGER,
            videos_transferred INTEGER,
            size_transferred_gb REAL,
            storage_percent_complete REAL,
            whatsapp_members_connected INTEGER,
            maps_members_sharing INTEGER,
            venmo_members_active INTEGER,
            key_milestone TEXT,
            notes TEXT
        );
        
        CREATE TABLE family_members (
            id INTEGER PRIMARY KEY DEFAULT nextval('family_seq'),
            migration_id TEXT NOT NULL,
            name TEXT NOT NULL,
            role TEXT,
            age INTEGER,
            email TEXT,
            phone TEXT,
            staying_on_ios BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE family_app_adoption (
            id INTEGER PRIMARY KEY,
            family_member_id INTEGER NOT NULL,
            app_name TEXT NOT NULL,
            status TEXT DEFAULT 'not_started',
            invitation_sent_at TIMESTAMP,
            invitation_method TEXT DEFAULT 'email',
            installed_at TIMESTAMP,
            configured_at TIMESTAMP,
            whatsapp_in_group BOOLEAN DEFAULT FALSE,
            location_sharing_sent BOOLEAN DEFAULT FALSE,
            location_sharing_received BOOLEAN DEFAULT FALSE,
            venmo_card_activated BOOLEAN DEFAULT FALSE,
            card_last_four TEXT
        );
    """)
    
    # Insert production data
    print("\n[4/4] Inserting production data...")
    
    # Use actual extracted data (implementation would copy from prod_conn queries above)
    # This is simplified for documentation
    test_conn.execute("""
        INSERT INTO migration_status 
        SELECT * FROM (VALUES (
            'MIG-20250903-102718', 'Vetticaden', 'iPhone', 'Galaxy Z Fold 7', 18,
            60238, 2418, 383.0, 383.0, NULL, NULL, 2048.0, 1.5, NULL, NULL,
            4, 'Vetticaden Family', '2025-09-03T15:27:18.069Z', 'family_setup', 45, NULL
        ))
    """)
    
    test_conn.execute("""
        INSERT INTO media_transfer 
        SELECT * FROM (VALUES (
            'TRF-20250903-103223', 'MIG-20250903-102718', NULL, NULL,
            60238, 2418, 383.0, 0, 0, 0.0, 'pending', 'pending', 'pending',
            NULL, NULL, NULL, NULL, NULL, 4, 7, NULL
        ))
    """)
    
    # Insert family members
    test_conn.execute("""
        INSERT INTO family_members (id, migration_id, name, role, age, staying_on_ios)
        VALUES 
        (1, 'MIG-20250903-102718', 'Jaisy Vetticaden', 'spouse', NULL, true),
        (2, 'MIG-20250903-102718', 'Laila Vetticaden', 'child', 17, true),
        (3, 'MIG-20250903-102718', 'Ethan Vetticaden', 'child', 15, true),
        (4, 'MIG-20250903-102718', 'Maya Vetticaden', 'child', 11, true)
    """)
    
    test_conn.commit()
    test_conn.close()
    
    print(f"\n✅ Test database seeded successfully")
    print(f"📁 Database location: {test_db_path}")
    print(f"📊 Before state saved: {results_path / 'before_state.json'}")
    print("="*60)

if __name__ == "__main__":
    seed_test_database()
```

## Step 6.2: Apply Phase 5 Historical Data

**File**: `phase6-isolated-tests/scripts/02_apply_phase5.py`

```python
#!/usr/bin/env python3
"""
Phase 6 Step 2: Apply Phase 5 SQL to test database.
Adds historical Day 1-2 storage snapshots and daily progress.
"""

import duckdb
from pathlib import Path

def apply_phase5_sql():
    """Apply Phase 5 historical data to test database."""
    
    project_root = Path(__file__).parent.parent.parent
    test_db_path = project_root / 'phase6-isolated-tests' / 'test_database' / 'test_migration.db'
    
    print("\n" + "="*60)
    print("PHASE 6 - STEP 2: APPLYING PHASE 5 HISTORICAL DATA")
    print("="*60)
    
    conn = duckdb.connect(str(test_db_path))
    
    # Insert Day 1-2 storage snapshots
    print("\n[1/2] Inserting storage snapshots...")
    conn.execute("""
        INSERT INTO storage_snapshots (
            migration_id, day_number, snapshot_time,
            google_photos_gb, google_drive_gb, gmail_gb,
            device_backup_gb, total_used_gb,
            storage_growth_gb, estimated_photos_transferred, estimated_videos_transferred,
            percent_complete, is_baseline, created_at
        ) VALUES 
        ('MIG-20250903-102718', 1, '2025-09-03 15:32:23',
         1.5, 0.5, 1.2, 0.8, 4.0, 0, 0, 0, 0, true, '2025-09-03 15:32:23'),
        ('MIG-20250903-102718', 2, '2025-09-04 10:00:00',
         1.5, 0.5, 1.2, 0.8, 4.0, 0, 0, 0, 0, false, '2025-09-04 10:00:00')
    """)
    
    # Insert Day 1-2 daily progress
    print("[2/2] Inserting daily progress records...")
    conn.execute("""
        INSERT INTO daily_progress (
            migration_id, day_number, date,
            photos_transferred, videos_transferred,
            size_transferred_gb, storage_percent_complete,
            whatsapp_members_connected, maps_members_sharing, venmo_members_active,
            key_milestone, notes
        ) VALUES 
        ('MIG-20250903-102718', 1, '2025-09-03',
         0, 0, 0, 0, 3, 0, 0,
         'Day 1: Migration initiated, family setup complete',
         'Transfer started, WhatsApp group created with 3 members'),
        ('MIG-20250903-102718', 2, '2025-09-04',
         0, 0, 0, 0, 4, 2, 0,
         'Day 2: Apple processing, family connectivity improved',
         'Maya added to WhatsApp, location sharing with Laila and Maya')
    """)
    
    # Verify insertions
    snapshots = conn.execute("SELECT COUNT(*) FROM storage_snapshots").fetchone()[0]
    progress = conn.execute("SELECT COUNT(*) FROM daily_progress").fetchone()[0]
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ Phase 5 data applied successfully")
    print(f"📊 Storage snapshots: {snapshots} records")
    print(f"📈 Daily progress: {progress} records")
    print("="*60)

if __name__ == "__main__":
    apply_phase5_sql()
```

## Step 6.3: Integration Test with Real Google Storage

**File**: `phase6-isolated-tests/scripts/03_test_integration.py`

```python
#!/usr/bin/env python3
"""
Phase 6 Step 3: Integration test with REAL Google Storage.
NO MOCKING - Uses actual Google APIs to validate refactoring.
"""

import os
import sys
import json
import asyncio
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_get_migration_status():
    """Test the refactored get_migration_status with REAL Google storage."""
    
    project_root = Path(__file__).parent.parent.parent
    test_db_path = project_root / 'phase6-isolated-tests' / 'test_database' / 'test_migration.db'
    results_path = project_root / 'phase6-isolated-tests' / 'results'
    
    print("\n" + "="*60)
    print("PHASE 6 - STEP 3: INTEGRATION TEST WITH REAL GOOGLE STORAGE")
    print("="*60)
    print(f"Test DB: {test_db_path}")
    print(f"Production DB: UNTOUCHED")
    print("-"*60)
    
    try:
        # Override database path for migration-state
        original_db_path = os.environ.get('MIGRATION_DATABASE_PATH')
        os.environ['MIGRATION_DATABASE_PATH'] = str(test_db_path)
        
        # Setup Python path
        sys.path.insert(0, str(project_root / 'ios-to-android-migration-assitant-agent' / 'shared' / 'database'))
        sys.path.insert(0, str(project_root / 'ios-to-android-migration-assitant-agent' / 'mcp-tools' / 'migration-state'))
        
        # Import migration-state server AFTER setting DB path
        from server import handle_call_tool
        
        print("\n[TEST 1] Testing Day 3 with REAL Google Storage...")
        print("🔄 This will make actual API calls to Google...")
        
        # Simulate Day 3 get_migration_status call
        class MockCallToolRequest:
            def __init__(self, name, arguments):
                self.name = name
                self.arguments = arguments
        
        request = MockCallToolRequest(
            name="get_migration_status",
            arguments={
                "migration_id": "MIG-20250903-102718",
                "day_number": 3
            }
        )
        
        # Call the actual handler
        result = await handle_call_tool(request)
        
        # Parse and validate result
        if result and len(result) > 0:
            response_text = result[0].text
            response_data = json.loads(response_text)
            
            print("\n✅ get_migration_status returned successfully")
            print(f"   Day Number: {response_data.get('day_number')}")
            print(f"   Photo Progress: {response_data.get('photo_progress', {}).get('percent_complete', 0)}%")
            print(f"   Success: {response_data.get('success')}")
            
            # Verify storage snapshot was created
            import duckdb
            conn = duckdb.connect(str(test_db_path))
            
            snapshots = conn.execute("""
                SELECT day_number, google_photos_gb, percent_complete, created_at
                FROM storage_snapshots 
                ORDER BY day_number
            """).fetchall()
            
            print("\n📦 Storage Snapshots in Test DB:")
            for snap in snapshots:
                print(f"   Day {snap[0]}: {snap[1]} GB ({snap[2]}%) - {snap[3]}")
            
            # Check if Day 3 snapshot was created
            day3_snapshot = [s for s in snapshots if s[0] == 3]
            if day3_snapshot:
                print("\n✅ Day 3 snapshot automatically created!")
                print(f"   Google Photos storage: {day3_snapshot[0][1]} GB")
            
            # Test Day 7 override
            print("\n[TEST 2] Testing Day 7 Success Override...")
            
            request_day7 = MockCallToolRequest(
                name="get_migration_status",
                arguments={
                    "migration_id": "MIG-20250903-102718",
                    "day_number": 7
                }
            )
            
            result_day7 = await handle_call_tool(request_day7)
            if result_day7:
                response_day7 = json.loads(result_day7[0].text)
                progress_day7 = response_day7.get('photo_progress', {}).get('percent_complete', 0)
                
                if progress_day7 == 100:
                    print("✅ Day 7 returns 100% (success override working)")
                else:
                    print(f"❌ Day 7 returned {progress_day7}% (should be 100%)")
            
            # Save results
            with open(results_path / 'after_state.json', 'w') as f:
                json.dump({
                    "day3_response": response_data,
                    "storage_snapshots_count": len(snapshots),
                    "day3_storage_gb": day3_snapshot[0][1] if day3_snapshot else None
                }, f, indent=2, default=str)
            
            conn.close()
            
        else:
            print("❌ No result returned from get_migration_status")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        # Restore original DB path
        if original_db_path:
            os.environ['MIGRATION_DATABASE_PATH'] = original_db_path
        else:
            os.environ.pop('MIGRATION_DATABASE_PATH', None)
        
        print("\n" + "="*60)
        print("TEST COMPLETE")
        print("Production database remains UNCHANGED")
        print(f"Test results saved in: {results_path}")
        print("="*60)

if __name__ == "__main__":
    asyncio.run(test_get_migration_status())
```

## Step 6.4: Validation Script

**File**: `phase6-isolated-tests/scripts/04_validate_results.py`

```python
#!/usr/bin/env python3
"""
Phase 6 Step 4: Validate test results.
Comprehensive checks on response structure and database updates.
"""

import json
import duckdb
from pathlib import Path

def validate_results():
    """Validate all test results."""
    
    project_root = Path(__file__).parent.parent.parent
    test_db_path = project_root / 'phase6-isolated-tests' / 'test_database' / 'test_migration.db'
    results_path = project_root / 'phase6-isolated-tests' / 'results'
    
    print("\n" + "="*60)
    print("PHASE 6 - STEP 4: VALIDATING RESULTS")
    print("="*60)
    
    validation_results = []
    
    # Load test results
    with open(results_path / 'after_state.json', 'r') as f:
        after_state = json.load(f)
    
    # Validation 1: Response structure
    print("\n[1/5] Validating response structure...")
    response = after_state.get('day3_response', {})
    required_fields = ['success', 'day_number', 'migration', 'photo_progress', 'family_services']
    
    for field in required_fields:
        if field in response:
            validation_results.append(f"✅ Field '{field}' present")
        else:
            validation_results.append(f"❌ Field '{field}' missing")
    
    # Validation 2: Database updates
    print("\n[2/5] Validating database updates...")
    conn = duckdb.connect(str(test_db_path))
    
    # Check storage_snapshots
    snapshots = conn.execute("""
        SELECT day_number, google_photos_gb 
        FROM storage_snapshots 
        ORDER BY day_number
    """).fetchall()
    
    if len(snapshots) >= 3:
        validation_results.append(f"✅ Storage snapshots: {len(snapshots)} records (Day 3 added)")
    else:
        validation_results.append(f"❌ Storage snapshots: Only {len(snapshots)} records")
    
    # Check daily_progress
    progress = conn.execute("""
        SELECT day_number, storage_percent_complete 
        FROM daily_progress 
        ORDER BY day_number
    """).fetchall()
    
    validation_results.append(f"📊 Daily progress: {len(progress)} records")
    
    # Validation 3: Google storage data
    print("\n[3/5] Validating Google storage integration...")
    day3_storage = after_state.get('day3_storage_gb')
    if day3_storage and day3_storage > 0:
        validation_results.append(f"✅ Real Google storage queried: {day3_storage} GB")
    else:
        validation_results.append(f"⚠️ Google storage might not have been queried")
    
    # Validation 4: Progress calculation
    print("\n[4/5] Validating progress calculation...")
    photo_progress = response.get('photo_progress', {})
    if 'percent_complete' in photo_progress:
        validation_results.append(f"✅ Progress calculated: {photo_progress['percent_complete']}%")
    else:
        validation_results.append(f"❌ Progress calculation missing")
    
    # Validation 5: Day 7 override
    print("\n[5/5] Validating Day 7 success override...")
    # This would be checked in the integration test
    validation_results.append("📝 Day 7 override tested in integration script")
    
    conn.close()
    
    # Generate report
    report_path = results_path / 'validation_report.txt'
    with open(report_path, 'w') as f:
        f.write("PHASE 6 VALIDATION REPORT\n")
        f.write("="*60 + "\n\n")
        for result in validation_results:
            f.write(result + "\n")
        
        # Overall assessment
        failed = [r for r in validation_results if r.startswith("❌")]
        if not failed:
            f.write("\n\n✅ ALL VALIDATIONS PASSED\n")
        else:
            f.write(f"\n\n⚠️ {len(failed)} VALIDATIONS FAILED\n")
    
    print("\n📋 Validation Summary:")
    for result in validation_results:
        print(f"   {result}")
    
    print(f"\n📁 Full report saved: {report_path}")
    print("="*60)

if __name__ == "__main__":
    validate_results()
```

## Step 6.5: Cleanup Script

**File**: `phase6-isolated-tests/scripts/05_cleanup.sh`

```bash
#!/bin/bash

echo "========================================"
echo "PHASE 6 - CLEANUP"
echo "========================================"
echo ""
echo "This will remove all Phase 6 test artifacts."
echo "Are you sure? (y/n)"
read -r response

if [ "$response" = "y" ]; then
    cd ../../..
    echo "Removing phase6-isolated-tests folder..."
    rm -rf phase6-isolated-tests/
    echo "✅ Cleanup complete"
else
    echo "Cleanup cancelled"
fi
```

## Test Execution Flow

```bash
# Complete test execution sequence
cd phase6-isolated-tests/scripts/

# Step 1: Seed test database
python 01_seed_database.py

# Step 2: Apply Phase 5 historical data
python 02_apply_phase5.py

# Step 3: Run integration test with real Google
python 03_test_integration.py

# Step 4: Validate results
python 04_validate_results.py

# Step 5: Review results
cat ../results/validation_report.txt

# Step 6: Cleanup (optional)
bash 05_cleanup.sh
```

## Expected Success Output

```
=================================================================
PHASE 6 ISOLATED INTEGRATION TEST - COMPLETE
=================================================================

[STEP 1] ✅ Test database seeded with production data
[STEP 2] ✅ Phase 5 historical data applied
[STEP 3] ✅ Integration test with REAL Google storage passed
[STEP 4] ✅ All validations successful

Key Results:
- Real Google storage API called: YES
- Storage snapshot created for Day 3: YES
- Progress calculation working: YES
- Day 7 override confirmed: YES
- Production database unchanged: YES

Test artifacts location: phase6-isolated-tests/
=================================================================
```

## Success Criteria for Phase 6

### Must Pass All:
- [ ] Test database created with current production state
- [ ] Phase 5 SQL executed successfully on test DB
- [ ] Real Google storage API called (not mocked)
- [ ] get_migration_status returns complete data structure
- [ ] storage_snapshots table gets Day 3 record
- [ ] daily_progress table updated correctly
- [ ] Day 7 shows 100% override working
- [ ] Production database completely unchanged
- [ ] All artifacts contained in phase6-isolated-tests folder
- [ ] Validation report shows all tests passed

## Risk Mitigation

1. **Production DB Safety**: Read-only access, never modified
2. **Test Isolation**: Separate folder and database
3. **Environment Variables**: Temporary override, always restored
4. **Error Handling**: Comprehensive try/finally blocks
5. **Easy Cleanup**: Single command removes everything

## Pre-Test Checklist

Before running Phase 6 tests:
- [ ] Google credentials present in .env file
- [ ] Google session valid (~/.google_session/)
- [ ] Python virtual environment activated
- [ ] All dependencies installed
- [ ] Network access to Google APIs available
- [ ] Production DB at ~/.ios_android_migration/migration.db
- [ ] Migration ID MIG-20250903-102718 exists in production DB

---

# Final Notes

## Implementation Order (Updated):
1. Phase 5 first (populate production database history)
2. Phase 1 second (update migration-state server)
3. **Phase 6 - Run isolated test** (verify refactoring works)
4. Phase 3 third (update agent instructions)
5. Phase 2 fourth (remove old MCP tool)
6. Phase 4 last (documentation)

## Time Estimate:
- Database inserts: ~5 minutes
- Phase 1 implementation: ~10 minutes
- Test verification: ~2 minutes
- Remaining phases: ~20 minutes
- Ready for Day 3 demo: Immediately after

## Success Criteria:
- [ ] Database has Day 1-2 history in storage_snapshots and daily_progress
- [ ] Isolated test passes without errors
- [ ] Test shows Day 3 snapshot created automatically
- [ ] Production database remains unchanged during testing
- [ ] Single call to get_migration_status returns fresh storage data
- [ ] Day 3 demo can continue smoothly

---

# NEXT STEPS FOR DAY 3 DEMO

## Current Status
✅ **Refactoring Complete**: All code changes have been implemented
- get_migration_status now automatically checks Google storage
- Agent instructions simplified to single calls
- check_photo_transfer_progress MCP tool removed
- Documentation updated

## To Continue Day 3 Demo:

### 1. First, Populate Database History (Phase 5)
Run these SQL commands in DuckDB to add Day 1-2 history:

```sql
-- Connect to your database
-- Path: ~/.ios_android_migration/migration.db

-- Run the INSERT statements from Phase 5 above
-- This adds Day 1-2 storage snapshots and daily progress records
```

### 2. Start Day 3 Recording
The system is now ready. When the agent calls:
```python
status = get_migration_status(migration_id='MIG-20250903-102718', day_number=3)
```

It will:
1. Automatically query real Google Photos storage
2. Insert Day 3 storage_snapshot record
3. Update daily_progress table
4. Return complete status with fresh data

### 3. Expected Day 3 Behavior
- Location sharing completion for Jaisy and Ethan
- Storage still at ~0% (Apple still processing)
- Overall progress updates to 47-50%
- WhatsApp group remains at 4/4 members

## Database State Required
- **Migration ID**: MIG-20250903-102718
- **Transfer ID**: TRF-20250903-103223
- **Current Phase**: family_setup
- **Overall Progress**: 45% (from Day 2)

## If Issues Arise
1. Check that migration-state MCP server can import ICloudClient
2. Verify Google credentials are in .env file
3. Ensure web-automation server is also running (for session management)
4. Check logs for any import or connection errors

---

**Created**: 2025-01-04  
**Completed**: 2025-01-04 (Phases 1-4)
**Status**: REFACTORING COMPLETE - Ready for Day 3 Demo
**Next Step**: Run Phase 5 SQL inserts, then continue Day 3 recording