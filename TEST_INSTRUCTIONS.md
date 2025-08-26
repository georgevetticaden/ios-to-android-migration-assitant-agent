# Test Instructions for iOS to Android Migration Assistant (V2)

## Overview
This document provides comprehensive testing instructions for validating the Phase 2 implementation of 10 new MCP tools for the iOS to Android migration assistant.

## Prerequisites
- Python 3.11+ installed
- Virtual environment activated
- DuckDB installed (comes with pip install)

## Test Organization

All tests are organized in `tests/` subdirectories within their respective modules:

```
├── shared/database/tests/          # Database tests (V2 schema)
├── mcp-tools/migration-state/tests/  # Migration state server tests  
├── mcp-tools/web-automation/tests/   # Web automation tests
```

## Complete Test Sequence (V2)

### Phase 1: Database Tests

#### Step 1: Reinitialize Database (IMPORTANT - Updated Schema)
```bash
# From project root
cd /Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent

# Reinitialize with updated schema (no foreign keys)
python3 shared/database/scripts/initialize_database.py
```
Expected: 
- Database backed up (if exists)
- 7 tables created (WITHOUT foreign key constraints)
- 7 indexes created
- 3 views created
- All expected tables verified

#### Step 3: Run Database Tests
```bash
python3 shared/database/tests/test_database.py
```
Expected: All 9 tests should pass
- Table existence tests
- Migration operations
- Family member management
- Photo transfer tracking
- App setup tracking
- View functionality
- Constraint enforcement

### Phase 2: MCP Tools Compatibility Tests

#### Step 4: Test Migration State Server
```bash
python3 mcp-tools/migration-state/tests/test_migration_state.py
```
Expected: All 17 tests should pass
- Original 6 tools (status, progress, statistics, etc.)
- New 10 tools (initialize, family, photos, apps, etc.)
- Complete 7-day demo flow simulation

#### Step 5: Test Web Automation Database Compatibility
```bash
python3 mcp-tools/web-automation/tests/test_icloud_db.py
```
Expected: 
- Old tables should NOT exist (pass)
- New tables should work (pass)
- Old queries should fail (pass)
- New queries should work (pass)

## Database Validation with DuckDB

### Connect to Database
```bash
# Use DuckDB CLI (NOT sqlite3!)
duckdb ~/.ios_android_migration/migration.db
```

### Validation Queries
```sql
-- 1. Check tables exist (should show 7 tables)
SELECT table_name FROM information_schema.tables 
WHERE table_type = 'BASE TABLE' 
ORDER BY table_name;

-- 2. Verify NO foreign key constraints (should return 0)
SELECT COUNT(*) as foreign_key_count
FROM duckdb_constraints()
WHERE constraint_type = 'FOREIGN KEY';

-- 3. Check views exist (should show 3 views)
SELECT table_name FROM information_schema.tables 
WHERE table_type = 'VIEW'
ORDER BY table_name;

-- 4. Test UPDATE works on migration_status
-- (This would fail with foreign keys, should work now)
INSERT INTO migration_status (id, user_name) VALUES ('TEST-1', 'Test User');
INSERT INTO family_members (id, migration_id, name, email) 
VALUES (1, 'TEST-1', 'Member', 'test@test.com');
UPDATE migration_status SET current_phase = 'photo_transfer' WHERE id = 'TEST-1';
-- Should succeed!

-- 5. Clean up test data
DELETE FROM family_members WHERE migration_id = 'TEST-1';
DELETE FROM migration_status WHERE id = 'TEST-1';

-- Exit DuckDB
.quit
```

## Quick Test Command

Run all tests in sequence:
```bash
# From project root
cd /Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent

# Reinitialize and run all tests
python3 shared/database/scripts/initialize_database.py && \
python3 shared/database/tests/test_database.py && \
python3 mcp-tools/migration-state/tests/test_migration_state.py
```

## Test Results Interpretation

### Success Indicators
- ✅ Green checkmarks for passed tests
- "ALL TESTS PASSED" message
- Exit code 0

### Failure Indicators  
- ❌ Red X marks for failed tests
- Specific error messages
- Exit code 1

## Validation Checklist

After running all tests, verify:

1. **Database Structure** ✓
   - [ ] 7 tables exist (not 17)
   - [ ] No schema prefixes (no `migration.` prefix)
   - [ ] Views work correctly

2. **Migration State Server** ✓
   - [ ] Can create migrations
   - [ ] Can update progress
   - [ ] Can query status
   - [ ] Returns JSON properly

3. **Web Automation** ✓
   - [ ] Uses new `photo_transfer` table
   - [ ] No references to old schemas
   - [ ] Methods use migration_db helpers

## Troubleshooting

### Database Lock Errors
If you see "database is locked":
1. Close DBeaver or any database viewers
2. Kill any hanging Python processes
3. Re-run the test

### Import Errors
If you see "ModuleNotFoundError":
1. Ensure you're in the project root
2. Check Python path includes parent directories
3. Verify shared modules exist

### Schema Errors
If you see "table does not exist":
1. Run reset_database.py
2. Run initialize_database.py
3. Verify tables with DBeaver

## Next Steps After Testing

Once all tests pass:
1. Proceed to Phase 2: Implement MCP tools
2. Create demo flow test script
3. Update documentation