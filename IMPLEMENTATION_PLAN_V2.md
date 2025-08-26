# Implementation Plan v2.0: Storage-Based Transfer Tracking with Video Support

## 🎯 Objective
Implement storage-based progress tracking using Google One metrics for accurate transfer monitoring, with full video support and realistic 7-day demo flow.

## 📅 Created: August 26, 2025
## 🔄 Last Updated: August 26, 2025

---

## ✅ COMPLETED COMPONENTS

### Phase 1: Database Schema v2.0 - ✅ COMPLETE
- **Date Completed**: August 26, 2025
- **Changes**:
  - ✅ Renamed `photo_transfer` → `media_transfer` table
  - ✅ Added separate `photo_status`, `video_status` columns
  - ✅ Created `storage_snapshots` table for Google One tracking
  - ✅ Added `google_photos_baseline_gb` to migration_status
  - ✅ Fixed DuckDB compatibility (sequences, strftime syntax)
  - ✅ Removed foreign keys (DuckDB UPDATE workaround)
- **Files Modified**:
  - `shared/database/schemas/migration_schema.sql`
  - `shared/database/migration_db.py`
  - `shared/database/tests/test_database.py`

### Phase 2: Migration-State MCP Server - ✅ COMPLETE  
- **Date Completed**: August 26, 2025
- **Changes**:
  - ✅ Updated from 6 → 18 tools
  - ✅ Added `record_storage_snapshot` tool
  - ✅ Added `get_storage_progress` tool
  - ✅ Updated all references from photo_transfer to media_transfer
  - ✅ All 17 tests passing
- **Files Modified**:
  - `mcp-tools/migration-state/server.py`
  - `mcp-tools/migration-state/tests/test_migration_state.py`

### Documentation Updates - ✅ COMPLETE
- **Date Completed**: August 26, 2025
- **Files Updated**:
  - `README.md` - Updated to v2.0 status
  - `TEST_INSTRUCTIONS.md` - Complete testing procedures
  - `shared/database/README.md` - 8 tables, 4 views documented
  - `mcp-tools/migration-state/README.md` - 18 tools documented

---

## 🚧 REMAINING IMPLEMENTATION

### Phase 3: Web-Automation Updates - 🔄 IN PROGRESS

#### Task 3.1: Video Checkbox Support ✅ COMPLETE
**File**: `mcp-tools/web-automation/src/web_automation/icloud_client.py`
**Status**: Completed - August 26, 2025
**Changes Made**:
- Updated `icloud_transfer_workflow.py` to check both Photos and Videos checkboxes
- Modified `_check_transfer_checkboxes()` method to select both media types
- Updated docstrings to reflect v2.0 media transfer support
- Test files updated to use `media_transfer` table instead of `photo_transfer`

#### Task 3.2: Google One Storage Extraction ✅ COMPLETE
**New File**: `mcp-tools/web-automation/src/web_automation/google_storage_client.py`
**Status**: Completed - August 26, 2025
**Changes Made**:
- Created `GoogleStorageClient` class with session persistence
- Extracts storage metrics from one.google.com/storage
- Successfully parses total storage (2TB), used storage (86.91GB)
- Correctly extracts service breakdown: Photos (1.05GB), Drive (52.52GB), Gmail (33.26GB)
- Updated `icloud_client.py` to use storage client instead of dashboard
- Modified `_establish_baseline_in_new_context()` to get storage metrics
- Removed deprecated `google_dashboard_client.py`
- Test verified: `test_google_storage.py` working correctly

#### Task 3.3: Update Database Calls ✅ COMPLETE
**Files Updated**: 
- `mcp-tools/web-automation/src/web_automation/icloud_client.py`
- `mcp-tools/web-automation/tests/test_migration_flow.py`
**Status**: Completed - August 26, 2025
**Changes Made**:
- Fixed `photo_transfer` → `media_transfer` table references
- Updated column references to v2.0 schema (photo_status, video_status)
- Fixed `progress_percentage` → `storage_percent_complete`
- Corrected JOIN clause to use proper migration_id
- Updated result indexing for additional video_status column

#### Task 3.4: Transform check_transfer_progress ✅ COMPLETE
**Files Modified**: 
- `mcp-tools/web-automation/src/web_automation/icloud_client.py`
- `mcp-tools/web-automation/src/web_automation/server.py`
**Status**: Completed - August 26, 2025
**Changes Made**:
- Transformed `check_transfer_progress()` from email-based to storage-based
- Now captures Google One storage and calculates real progress
- Saves snapshots to `storage_snapshots` table when checking
- Updates `daily_progress` table with calculated metrics
- Added day-specific milestone messages
- Estimates photos/videos based on storage growth (65%/35% ratio)
- Returns storage metrics, progress percentage, and human-readable messages

---

### Phase 4: Mobile-MCP Integration - 📋 TODO

#### Task 4.1: Gmail Verification Commands
**Type**: Natural Language Commands
**Status**: Not Started
**Commands**:
```
Day 1:
- "Open Gmail app"
- "Search for emails from Apple"
- "Take screenshot of video transfer email"
- "Take screenshot of photo transfer email"
```

#### Task 4.2: Google One App Commands
**Type**: Natural Language Commands
**Status**: Not Started
**Commands**:
```
Day 4+:
- "Open Google One app"
- "Navigate to Storage details"
- "Read the Google Photos storage number"
```

---

### Phase 5: Progress Calculation - 📋 TODO

#### Task 5.1: Storage-Based Calculation
**File**: `shared/database/migration_db.py`
**Status**: Not Started
**New Method**: `calculate_storage_progress()`
**Formula**:
```python
growth = current_storage - baseline_storage
percent = (growth / total_icloud_storage) * 100
photos_est = growth * 0.7 * 1024 / 6.5  # 70% of storage
videos_est = growth * 0.3 * 1024 / 150  # 30% of storage
```

---

### Phase 6: Demo Script Updates - 📋 TODO

#### Task 6.1: Day 1 Enhanced Flow
**File**: `docs/demo/demo-script-complete-final.md`
**Status**: Not Started
**Updates**:
- Capture Google baseline before transfer
- Show both photo and video checkboxes
- Verify both emails in Gmail

#### Task 6.2: Day 4-7 Progress Updates
**Status**: Not Started
**Updates**:
- Use real storage metrics
- Show storage-based calculations
- Handle 98% photo / 100% video scenario

---

## 📊 Key Metrics & Formulas

### Storage Distribution
- **Total iCloud**: 383GB (60,238 photos + 2,418 videos)
- **Google Baseline**: 13.88GB (before transfer)
- **Expected Final**: 396.88GB (after transfer)

### Progress Calculation
```
Day 1: 0% (13.88GB) - Transfer initiated
Day 4: 28% (120.88GB) - Photos appearing (+107GB)
Day 5: 57% (220.88GB) - Accelerating (+207GB)
Day 6: 88% (340.88GB) - Nearly complete (+327GB)
Day 7: 99.3% (394.88GB) - Complete (+381GB)
```

### Item Estimation
- **Average Photo**: 6.5MB (70% of storage)
- **Average Video**: 150MB (30% of storage)
- **Formula**: `items = (storage_gb * ratio * 1024) / avg_size_mb`

---

## 🧪 Testing Requirements

### Unit Tests Completed
1. ✅ Video checkbox verification - Integrated in `test_migration_flow.py`
2. ✅ `test_google_storage.py` - Test storage extraction (tests directory)
3. 📋 `test_storage_progress.py` - Validate calculations (TODO)

### Integration Tests
1. Day 1 flow with baselines
2. Day 4 storage check
3. Day 7 completion scenario

---

## 📝 Implementation Order

### Session 1 (Current - August 26, 2025)
1. ✅ Create this implementation plan
2. ✅ Update icloud_client.py for video checkbox
3. ✅ Update icloud_transfer_workflow.py for video selection
4. ✅ Update test files to use media_transfer table

### Session 2 (Next)
1. Create google_storage_client.py
2. Add storage MCP tools
3. Implement progress calculation
4. Test storage extraction

### Session 3 (Final)
1. Gmail verification flow
2. Update demo script
3. End-to-end testing
4. Documentation

---

## 🎯 Success Criteria

### Must Have
- [x] Database supports video tracking
- [x] Storage snapshots table works
- [ ] Video checkbox selected during transfer
- [ ] Google One storage extracted
- [ ] Progress based on real storage metrics
- [ ] 98% photo / 100% video scenario works

### Nice to Have
- [ ] Gmail screenshot automation
- [ ] Google Photos item count verification
- [ ] Storage growth visualization
- [ ] Error recovery for partial failures

---

## 🚨 Known Issues & Risks

### Current Issues (Fixed)
1. **Confirm Transfer Button**: Test correctly stops at confirmation page (intentional safety feature) ✅
2. **Google Baseline**: Fixed - Now uses Google One storage page instead of Dashboard ✅
3. **Session Reuse**: Fixed - `start_transfer()` now reuses existing browser session to avoid double login ✅
4. **Google Dashboard Removed**: Deprecated google_dashboard_client.py has been removed ✅
5. **Database References**: Fixed - migration_status.id JOIN and daily_progress.key_milestone column ✅

### Potential Risks
1. **Google One UI Changes**: Selectors may need updates
2. **Apple Checkbox Changes**: Monitor for UI updates
3. **Storage Calculation**: Ratios may vary by user
4. **Demo Timing**: 7-day timeline needs careful orchestration

---

## 📌 Quick Reference

### Key Files
- **Database Schema**: `shared/database/schemas/migration_schema.sql`
- **iCloud Client**: `mcp-tools/web-automation/src/web_automation/icloud_client.py`
- **Migration State**: `mcp-tools/migration-state/server.py`
- **Demo Script**: `docs/demo/demo-script-complete-final.md`

### Test Commands
```bash
# Reset and initialize database
python3 shared/database/scripts/reset_database.py
python3 shared/database/scripts/initialize_database.py

# Test database
python3 shared/database/tests/test_database.py

# Test MCP server
python3 mcp-tools/migration-state/tests/test_migration_state.py

# Test web automation (from web-automation directory)
cd mcp-tools/web-automation
python3 tests/test_basic_auth.py
python3 tests/test_google_storage.py
python3 tests/test_migration_flow.py --phase 1
```

### MCP Tools Count
- **web-automation**: 5 tools (will be 7 after updates)
- **migration-state**: 18 tools ✅
- **mobile-mcp**: Natural language interface

---

## 📞 Session Handoff Notes

**For Next Session**:
1. Start with Task 3.1: Update icloud_client.py for video checkbox
2. Reference this plan for implementation details
3. Use storage formulas provided above
4. Test video checkbox before moving to storage extraction

**Current Branch**: main
**Last Commit**: "adding new requirements docs." (69f5e96)

---

*This plan is the source of truth for v2.0 implementation status. Update after each completed task.*