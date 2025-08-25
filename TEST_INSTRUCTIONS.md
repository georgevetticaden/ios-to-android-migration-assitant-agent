# Test Instructions for iOS to Android Migration Assistant (V2)

## Test Organization

All tests are organized in `tests/` subdirectories within their respective modules:

```
├── shared/database/tests/          # Database tests (V2 schema)
├── mcp-tools/migration-state/tests/  # Migration state server tests  
├── mcp-tools/web-automation/tests/   # Web automation tests
```

## Complete Test Sequence (V2)

### Phase 1: Database Tests

#### Step 1: Reset Database
```bash
python3 shared/database/scripts/reset_database.py
```
Expected: Database backed up and reset

#### Step 2: Initialize Database
```bash
python3 shared/database/scripts/initialize_database.py
```
Expected: 
- 7 tables created
- 3 views created
- All indexes created

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
python3 mcp-tools/migration-state/tests/test_server.py
```
Expected: All 10 tests should pass
- Schema initialization
- Migration creation
- Status queries
- Progress updates
- Statistics retrieval
- Event logging

#### Step 5: Test Web Automation Database Compatibility
```bash
python3 mcp-tools/web-automation/tests/test_icloud_db.py
```
Expected: 
- Old tables should NOT exist (pass)
- New tables should work (pass)
- Old queries should fail (pass)
- New queries should work (pass)

## Quick Test Command

Run all tests in sequence:
```bash
# Reset and initialize
python3 shared/database/scripts/reset_database.py && \
python3 shared/database/scripts/initialize_database.py && \
# Run all tests
python3 shared/database/tests/test_database.py && \
python3 mcp-tools/migration-state/tests/test_server.py && \
python3 mcp-tools/web-automation/tests/test_icloud_db.py
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