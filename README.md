# iOS to Android Migration Assistant Agent

A comprehensive MCP (Model Context Protocol) tool suite for migrating from iOS to Android, handling photos, WhatsApp, and family services with intelligent automation.

## 🎯 Project Overview

This project provides MCP tools that assist with the complete migration journey from iPhone to Android devices, focusing on:
- **Photo Migration**: iCloud Photos → Google Photos (60,000+ photos) with session persistence
- **WhatsApp Migration**: Chat history and group management (Future)
- **Family Services**: Life360, parental controls, shared calendars (Future)

## 🚀 Features

### Photo Migration Tool (Current)
- 🔐 **Session Persistence**: Authenticate once with 2FA, then reuse session for ~7 days
- 📸 **Real Data Extraction**: Gets actual photo/video counts from privacy.apple.com
- 🎬 **Detailed Metrics**: Reports photos, videos, total items, and storage usage
- 📅 **Transfer History**: Shows previous transfer request statuses
- 🤖 **MCP Integration**: 5 tools exposed for Claude Desktop
- 🚀 **Transfer Automation**: Complete iCloud to Google Photos workflow
- 📊 **Progress Tracking**: Real-time monitoring via Google Dashboard
- ✅ **Verification**: Automatic completion checks and email monitoring

### Successfully Extracts
- ✅ 60,238 photos
- ✅ 2,418 videos  
- ✅ 383 GB storage usage
- ✅ Previous transfer history

## 📋 Current Status - V2 Implementation

### ✅ Phase 1: Database V2 Implementation - COMPLETE (Aug 25, 2025)
- **Simplified Schema**: Reduced from 17 to 7 tables
- **No Schema Prefixes**: Direct table names (no migration. prefix)
- **Day-Aware Logic**: Photos visible Day 4, Venmo cards Day 5
- **Email-Based Coordination**: Family members use emails for invitations
- **Full Test Coverage**: All database and compatibility tests passing

### ✅ Photo Migration Tool: COMPLETE & OPERATIONAL
**Active Transfer**: Currently processing 60,238 photos (383 GB) from iCloud to Google Photos
- **Transfer ID**: TRF-20250820-180056
- **Started**: August 20, 2025
- **Expected Completion**: 3-7 days (Apple's processing time)

### ✅ Completed Features
- **V2 Database**: Simplified 7-table schema with constraints
- **Full Authentication**: Apple ID and Google account with 2FA support
- **Session Persistence**: 7-day session validity for both services
- **Transfer Automation**: Complete 8-step workflow through Apple's portal
- **Progress Monitoring**: Real-time tracking via Google Dashboard
- **Database Integration**: All transfers tracked in DuckDB
- **Gmail Monitoring**: Automatic detection of completion emails
- **Centralized Logging**: All activity logged to `logs/` directory
- **Error Recovery**: Robust retry logic and error handling
- **MCP Servers**: 3 operational servers (web-automation, mobile-mcp, migration-state)

### 🔧 Phase 2: MCP Tools Implementation - READY TO START
**10 New Tools to Implement**:
1. `initialize_migration` - Start new migration with user details
2. `add_family_member` - Add family member with email
3. `setup_whatsapp_group` - Track WhatsApp group creation
4. `track_app_installation` - Monitor app setup progress
5. `update_daily_progress` - Record daily milestones
6. `setup_venmo_teen` - Track teen card ordering/arrival
7. `get_family_app_status` - Query family app adoption
8. `get_migration_summary` - Get complete migration overview
9. `mark_phase_complete` - Update migration phase
10. `generate_completion_report` - Final migration report

### 📅 Upcoming Phases
- Phase 2: Implement 10 new MCP tools
- Phase 3: Demo flow testing
- Phase 4: WhatsApp automation
- Phase 5: Family services coordination

## 🔧 Prerequisites

- Python 3.11 (Required - exactly 3.11, not 3.12+)
- DuckDB (Installed automatically with pip)
- macOS (for iCloud integration)
- Apple ID with iCloud Photos enabled
- Device capable of receiving 2FA codes
- Google account (for Google Photos)
- Android device with USB debugging enabled (for mobile-mcp)
- Node.js 18+ (for mobile-mcp)

## 📦 Installation

### 1. Clone the Repository
```bash
git clone [repository-url]
cd ios-to-android-migration-assistant-agent
```

### 2. Set Up Python Virtual Environment
```bash
# Create venv with Python 3.11 explicitly
python3.11 -m venv .venv

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.11.x
```

### 3. Install Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install all dependencies
pip install -r requirements.txt

# Install web-automation package in development mode
pip install -e mcp-tools/web-automation/

# Install Playwright browsers for automation
playwright install chromium
```

### 4. Set Up Mobile-MCP (Android Device Control)
```bash
# Navigate to mobile-mcp directory
cd mcp-tools/mobile-mcp

# Install Node.js dependencies
npm install

# Build the TypeScript project
npm run build

# Verify ADB connection to your Android device
adb devices  # Should show your device ID

# Test mobile-mcp functionality
npm test  # Runs tests with connected Android device
```

### 5. Configure Environment Variables
```bash
# Copy template and edit with your credentials
cp .env.template .env

# Edit .env to include:
# APPLE_ID=your.email@icloud.com
# APPLE_PASSWORD=your_password
# (Future: Google API credentials paths)
```

### 6. Initialize the Database (V2 Schema)
```bash
# Initialize the V2 database with simplified schema
python3 shared/database/scripts/initialize_database.py

# Verify database setup (should show 9 tests passing)
python3 shared/database/tests/test_database.py
```

**Database Details:**
- Location: `~/.ios_android_migration/migration.db`
- Tables: 7 (migration_status, family_members, photo_transfer, app_setup, family_app_adoption, daily_progress, venmo_setup)
- Views: 3 (migration_summary, family_app_status, active_migration)

### 7. Verify Installation
```bash
# Run all tests to verify setup
python3 shared/database/tests/test_database.py
python3 mcp-tools/migration-state/tests/test_server.py
python3 mcp-tools/web-automation/tests/test_icloud_db.py

# Check migration status
python3 scripts/migration_status.py
```

For detailed test instructions, see [TEST_INSTRUCTIONS.md](TEST_INSTRUCTIONS.md)

## 💻 Usage

### Photo Migration Tool

#### Standalone Testing

##### Basic Authentication Test
```bash
cd mcp-tools/web-automation

# Test authentication and status checking
python test_basic_auth.py         # Uses saved session if available
python test_basic_auth.py --fresh # Force new login
python test_basic_auth.py --clear # Clear saved session
```

##### Complete Migration Flow Test
```bash
# Test all Phase 3 methods
python test_migration_flow.py

# This tests:
# 1. Authentication
# 2. Start transfer
# 3. Check progress
# 4. Verify completion
# 5. Check email
```

##### Clear Sessions
```bash
# Clear all saved sessions
python utils/clear_sessions.py
```

#### Command Line Options
- **No flags**: Uses saved session if available (< 7 days old)
- **`--fresh`**: Forces new login even if valid session exists
- **`--clear`**: Clears saved session and exits

### Check Migration Status
```bash
# From project root
python scripts/migration_status.py
```

## 🔌 MCP Server Configuration

### Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "web-automation": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "web_automation.server"],
      "cwd": "/absolute/path/to/mcp-tools/web-automation"
    },
    "mobile-mcp-local": {
      "command": "node",
      "args": [
        "/absolute/path/to/mcp-tools/mobile-mcp/lib/index.js",
        "--stdio"
      ],
      "env": {
        "NODE_ENV": "production"
      }
    },
    "migration-state": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": [
        "/absolute/path/to/mcp-tools/migration-state/server.py"
      ]
    }
  }
}
```

**Note**: The `web-automation` server reads Apple credentials from the `.env` file in the project root, so you don't need to add them to the Claude Desktop config.

To find your absolute paths:
```bash
pwd  # Copy this path for 'cwd'
echo $VIRTUAL_ENV/bin/python  # Copy this for 'command'
```

### Using with Claude Desktop

#### Web Automation (iCloud Migration)
1. Restart Claude Desktop after configuration
2. Look for "web-automation" in available tools
3. Use the tool: "Check my iCloud photo status"
4. First use will require 2FA in the browser window
5. Subsequent uses will reuse the saved session

#### Mobile-MCP (Android Control)
1. Connect your Android device via USB
2. Enable USB debugging on the device
3. Restart Claude Desktop after configuration
4. Mobile-mcp tools will be available for:
   - Taking screenshots
   - Installing apps
   - Automating UI interactions
   - Natural language commands (e.g., "Open WhatsApp and create a new group")

#### Migration State (Database)
1. Restart Claude Desktop after configuration
2. Migration-state tools will be available for:
   - Checking overall migration status
   - Tracking progress across all tools
   - Querying pending items
   - Viewing migration statistics

## 📁 Project Structure

```
ios-to-android-migration-assistant-agent/
├── mcp-tools/                    # MCP tool implementations
│   ├── web-automation/          # Browser automation (formerly photo-migration)
│   │   ├── src/
│   │   │   └── web_automation/  # Python module
│   │   │       ├── icloud_client.py      # iCloud automation
│   │   │       ├── google_dashboard_client.py  # Google Photos
│   │   │       ├── gmail_monitor.py      # Gmail integration
│   │   │       ├── icloud_transfer_workflow.py # Transfer logic
│   │   │       ├── logging_config.py     # Logging setup
│   │   │       └── server.py             # MCP server (5 tools)
│   │   ├── tests/              # Test scripts
│   │   └── pyproject.toml      # Package configuration
│   ├── mobile-mcp/             # Android device control (external)
│   │   ├── lib/                # Compiled TypeScript
│   │   ├── src/                # Source TypeScript
│   │   ├── SETUP.md           # Setup instructions
│   │   └── package.json        # Node.js configuration
│   └── migration-state/        # Database state management
│       ├── server.py           # MCP wrapper for DuckDB (6 tools)
│       ├── README.md          # Documentation
│       └── requirements.txt    # Dependencies
├── shared/                     # Shared infrastructure
│   ├── database/              # Core database logic
│   │   ├── migration_db.py   # Database operations
│   │   └── schemas/          # Table schemas
│   └── config/               # Configuration management
├── requirements/              # Requirements documentation
│   └── mcp-tools/            # MCP-specific requirements
├── docs/                     # Documentation
│   ├── blog/                # Blog posts
│   └── demo/               # Demo scripts
├── logs/                    # Centralized logging
├── scripts/                 # Utility scripts
├── .venv/                  # Virtual environment (create this)
├── .env                    # Your credentials (create this)
├── .env.template           # Environment template
├── requirements.txt        # Python dependencies
├── CLAUDE.md              # Project instructions
├── README.md              # This file
└── IMPLEMENTATION_STATUS.md # Current status
```

## 🗄️ Database Architecture

The project uses a centralized DuckDB database (`~/.ios_android_migration/migration.db`) with schemas:

- **migration_core**: Master migration tracking, family members, event log
- **photo_migration**: Transfer progress, quality samples, email confirmations
- **whatsapp_migration**: (Future) Chat transfers, automation tasks
- **family_services**: (Future) Service migrations, parental controls

## 🔐 Security

- Credentials stored in `.env` (never committed to git)
- Session persistence in `~/.icloud_session/` (7-day validity)
- Browser runs in non-headless mode for transparency
- 2FA provides additional security layer
- OAuth2 for Google APIs (Phase 2+)
- No credentials passed through MCP parameters

## 🧪 Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run infrastructure tests
python scripts/test_shared_infrastructure.py

# Test photo-migration
cd mcp-tools/photo-migration
python test_client.py

# Check database status
python scripts/migration_status.py
```

## 🐛 Troubleshooting

### 2FA Code Issues on Mac
If the 2FA code disappears quickly:
- Click the date/time in the top-right corner
- Check Notification Center
- Or check your iPhone/iPad

### Session Not Persisting
If you're asked for 2FA every time:
- Check `~/.icloud_session/` exists and is writable
- Verify session files are being created
- Try `python test_client.py --clear` then run again
- Apple may require re-authentication for security

### Tool Not Showing in Claude Desktop
1. Check logs: `tail -f ~/Library/Logs/Claude/*.log`
2. Verify paths in config are absolute paths
3. Ensure virtual environment is activated
4. Restart Claude Desktop

### Common Errors
- **"No email field found"**: Apple changed their login page structure
- **"Could not find transfer button"**: May need to update selectors
- **Import errors**: Ensure you're using Python 3.11 and virtual environment

## 📊 How It Works

### Authentication Flow
1. Navigates to privacy.apple.com
2. Handles Apple's iframe-based authentication
3. Manages 2FA when required
4. Saves session for future use

### Data Extraction
1. Clicks "Request to transfer a copy of your data"
2. Selects "iCloud photos and videos"
3. Extracts counts from confirmation page
4. Parses storage information

### Session Management
- Saves browser state after successful auth
- Validates session age (< 7 days)
- Automatically reuses valid sessions
- Falls back to fresh login when needed

## 🚀 Current Development

### Phase 3-4 Features (Implemented, Testing Pending)
- [x] `start_transfer` - Initiates actual transfer workflow
- [x] `check_transfer_progress` - Monitors via Google Dashboard
- [x] `verify_transfer_complete` - Quality checks and match rate
- [x] `check_completion_email` - Gmail integration with OAuth
- [🚧] MCP server integration testing
- [🚧] Claude Desktop end-to-end validation

### Future Phases
- [ ] WhatsApp chat migration automation
- [ ] Family services coordination (Life360, Venmo Teen)
- [ ] Parental controls migration
- [ ] Shared calendar transfers

## 📝 Documentation

- `IMPLEMENTATION_STATUS.md` - Detailed implementation progress and context
- `TESTING_GUIDE.md` - Comprehensive testing instructions
- `requirements/` - Tool specifications and requirements
- `CLAUDE.md` - Project context for Claude

## 🤝 Contributing

This project is actively being developed. Key areas:
1. Google Photos API integration (Phase 2)
2. WhatsApp automation tools
3. Family services coordination

### Development Setup
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# View MCP server logs
tail -f ~/Library/Logs/Claude/*.log | grep photo-migration

# Run with debug output
python test_client.py
```

## 📄 License

MIT

## 🙏 Acknowledgments

Built with:
- MCP (Model Context Protocol) by Anthropic
- DuckDB for state management
- Playwright for browser automation
- Google APIs for cloud services

## 💬 Support

For issues or questions:
- Check existing issues in the repository
- Review logs in `logs/` directory
- Ensure you're using Python 3.11+
- Verify all dependencies are installed

---

For detailed implementation status, see `IMPLEMENTATION_STATUS.md`
For testing instructions, see `TESTING_GUIDE.md`
For project context, see `CLAUDE.md`