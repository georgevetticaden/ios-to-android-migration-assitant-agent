# Test Instructions for iOS to Android Migration Assistant

## Overview
This document provides step-by-step testing instructions for the iOS to Android migration assistant. Follow these steps after cloning the repository to verify everything works correctly.

## Prerequisites

Before running tests, ensure you have:
- Python 3.11+ installed (required for MCP support)
- Virtual environment set up and activated
- Required packages installed: `pip install -r requirements.txt`
- Environment variables configured in `.env` file:
  - `APPLE_ID` and `APPLE_PASSWORD` 
  - `GOOGLE_EMAIL` and `GOOGLE_PASSWORD`

## Quick Start for New Users

If you just cloned the repository, follow these steps in order:

### 1. Initial Setup
```bash
# Navigate to project root
cd ios-to-android-migration-assitant-agent

# Create and activate virtual environment with Python 3.11
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.11.x

# Install dependencies
pip install -r requirements.txt

# Install web-automation package in editable mode
pip install -e mcp-tools/web-automation/

# Install Playwright browsers (required for web automation)
playwright install chromium
```

### 2. Initialize Database
```bash
# Optional: Reset database if it already exists (start completely fresh)
python shared/database/scripts/reset_database.py

# Create the database with all required tables and views
python shared/database/scripts/initialize_database.py
```

Expected output:
- Database created at `~/.ios_android_migration/migration.db`
- 7 tables created (migration_status, media_transfer, family_members, etc.)
- 4 views created for reporting
- Success message: "Database initialization complete!"

Note: The `reset_database.py` script removes any existing database and starts fresh. Use this if you need to clean up from previous test runs or start over.

### 3. Test Shared Infrastructure (Optional)
```bash
# Test that all shared modules are working correctly
python scripts/test_shared_infrastructure.py
```

Expected: 
- All modules import successfully
- Settings are configured correctly
- Database connection works

### 4. Verify Database Setup
```bash
# Run database tests to ensure everything is working
python shared/database/tests/test_database.py
```

Expected: All tests should pass (typically 10 tests)

### 5. Test Migration State MCP Server
```bash
# Test the main migration orchestration server
python mcp-tools/migration-state/tests/test_mcp_server.py
```

Expected: All 28 tests should pass, validating the complete 7-day migration flow

### 6. Setup Google Session (Required for Web Automation)
```bash
# Optional: Clear any existing sessions if switching accounts or having issues
python scripts/clear_sessions.py

# Authenticate with Google (required before web automation tests)
python scripts/setup_google_session.py
```

Expected:
- Browser opens for Google authentication
- Session saved to `~/.google_session/`
- Success message: "Google session established"

### 7. Test Web Automation MCP Server
```bash
# For DEMO MODE only: Launch browser with CDP (optional)
# ./scripts/launch_demo_browser.sh
# export DEMO_MODE=true

# Test browser automation tools (launches its own browser by default)
python mcp-tools/web-automation/tests/test_mcp_server.py
```

Expected: All 4 web automation tools should pass

Note: The test normally launches its own browser. Only use `launch_demo_browser.sh` if you want to run in demo mode with a pre-launched browser for visibility.

## Complete Test Suite

Run all tests in sequence with this single command:

```bash
# From project root
python shared/database/scripts/initialize_database.py && \
python scripts/test_shared_infrastructure.py && \
python shared/database/tests/test_database.py && \
cd mcp-tools/migration-state/tests && python test_mcp_server.py && cd ../../.. && \
python scripts/setup_google_session.py && \
python mcp-tools/web-automation/tests/test_mcp_server.py
```

Or run without the optional shared infrastructure test:

```bash
# From project root (minimal test suite)
python shared/database/scripts/initialize_database.py && \
python shared/database/tests/test_database.py && \
cd mcp-tools/migration-state/tests && python test_mcp_server.py && cd ../../.. && \
python scripts/setup_google_session.py && \
python mcp-tools/web-automation/tests/test_mcp_server.py
```

## Test Organization

Tests are organized by component:

```
├── shared/database/tests/          # Database structure and operations
├── mcp-tools/migration-state/tests/  # Migration orchestration tools
└── mcp-tools/web-automation/tests/   # Browser automation tools
```

## Understanding Test Results

### Migration State Server Tests (28 tests)

The `test_mcp_server.py` validates the complete migration flow:

**Day 1 Setup (11 tests):**
- Initialize migration for user
- Add 4 family members (Jaisy, Laila, Ethan, Maya)
- Update migration status with iCloud metrics
- Configure WhatsApp group membership
- Query family members with filters

**Days 2-7 Daily Flow (16 tests):**
- Daily status checks with `get_migration_status`
- Progress updates showing gradual completion
- Day 4: Photos become visible (28% progress)
- Day 7: Migration completes (100% success)

**Completion (1 test):**
- Generate final celebration report

### What the Tests Validate

1. **Database Operations:**
   - Tables and views exist and work correctly
   - Data relationships are maintained
   - Queries return expected results

2. **MCP Tool Integration:**
   - All 7 migration state tools function properly
   - All 4 web automation tools work correctly
   - Tools return consistent JSON responses

3. **Migration Flow:**
   - Follows the exact 7-day timeline
   - Progressive updates work correctly
   - Family member management functions
   - App adoption tracking works

## Troubleshooting

### Common Issues and Solutions

**ModuleNotFoundError: No module named 'web_automation'**
- Install the web-automation package in editable mode: `pip install -e mcp-tools/web-automation/`
- This is required for the MCP server to find the web_automation module when running with `-m web_automation.server`

**ModuleNotFoundError: No module named 'mcp'**
- Make sure you've installed all requirements: `pip install -r requirements.txt`
- The MCP package is available on PyPI and should install correctly
- If you still see this error, try: `pip install mcp>=1.0.0`

**Database is locked:**
- Close any database viewers (DBeaver, etc.)
- Ensure no other Python processes are running
- Re-run the test

**Google session expired:**
- Re-run `python scripts/setup_google_session.py`
- Complete the authentication in the browser
- Sessions are valid for approximately 7 days
- If issues persist, clear all sessions with `python scripts/clear_sessions.py`

**Test failures:**
- Check the error message for specific tool that failed
- Try resetting and reinitializing the database:
  ```bash
  python shared/database/scripts/reset_database.py
  python shared/database/scripts/initialize_database.py
  ```
- Verify environment variables are set in `.env` file

## Success Criteria

All tests pass when you see:
- ✅ Green checkmarks for individual tests
- "ALL TESTS PASSED" message
- Test summary showing 100% success rate

For the migration state server specifically:
- "🎉 ALL TESTS PASSED!" 
- "Results: Total Tests: 28, Passed: 28, Failed: 0"

## Next Steps

After all tests pass:
1. Configure MCP servers in Claude Desktop (`claude_desktop_config.json`)
2. Test the complete system with Claude
3. Run through the demo flow in `docs/demo/demo-script-complete-final.md`

## Utility Scripts

### Clear Sessions
```bash
# Clear all saved authentication sessions
python scripts/clear_sessions.py
```
Removes stored sessions for iCloud, Google, and Gmail. Use this when:
- Testing fresh authentication flows
- Sessions have expired
- Switching between different accounts
- Troubleshooting authentication issues

### Check Migration Status
```bash
# View current migration status from the database
python scripts/migration_status.py
```
Shows comprehensive migration status including family members, app adoption, and transfer progress.

### Launch Demo Browser
```bash
# Launch Chromium/Chrome with CDP enabled for demo mode
./scripts/launch_demo_browser.sh
```
Use this when you want to run web automation tools with a fresh browser instance that has remote debugging enabled on port 9222.

### Test Shared Infrastructure
```bash
# Verify all shared modules are working
python scripts/test_shared_infrastructure.py
```
Quick test to ensure database, config, and utils modules are properly configured.

## Additional Resources

- **Database Schema:** `shared/database/schemas/migration_schema.sql`
- **Demo Script:** `docs/demo/demo-script-complete-final.md`
- **Agent Instructions:** `agent/instructions/ios2android-agent-instructions.md`
- **MCP Server Documentation:** Individual README files in each `mcp-tools/` subdirectory