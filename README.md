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
- 🤖 **MCP Integration**: Works as an MCP server for Claude Desktop

### Successfully Extracts
- ✅ 60,238 photos
- ✅ 2,418 videos  
- ✅ 383 GB storage usage
- ✅ Previous transfer history

## 📋 Current Status

### ✅ Phase 1: Infrastructure (COMPLETED)
- Shared database architecture (DuckDB)
- Centralized configuration management
- Photo-migration tool with session persistence
- Comprehensive testing framework

### 🚧 Phase 2: Google APIs (NEXT)
- Adding Google Photos API integration
- Gmail monitoring for completion emails
- Progress tracking with baseline establishment

### 📅 Upcoming Phases
- Phase 3-5: Extended photo-migration features
- Phase 6+: WhatsApp automation tools
- Phase 7+: Family services coordination

## 🔧 Prerequisites

- Python 3.11+ (Important: Use Python 3.11, not system Python)
- macOS (for iCloud integration)
- Apple ID with iCloud Photos enabled
- Device capable of receiving 2FA codes
- Google Cloud account (for Phase 2+)

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

# Install photo-migration package in development mode
pip install -e mcp-tools/photo-migration/

# Install Playwright browsers for automation
playwright install chromium
```

### 4. Configure Environment Variables
```bash
# Copy template and edit with your credentials
cp .env.template .env

# Edit .env to include:
# APPLE_ID=your.email@icloud.com
# APPLE_PASSWORD=your_password
# (Future: Google API credentials paths)
```

### 5. Initialize the Database
```bash
# Set up the shared database for all tools
python scripts/setup_database.py
```

### 6. Verify Installation
```bash
# Test infrastructure
python scripts/test_shared_infrastructure.py

# Test photo-migration config
python scripts/test_photo_migration_env.py

# Check migration status
python scripts/migration_status.py
```

## 💻 Usage

### Photo Migration Tool

#### Standalone Testing
The tool supports session persistence to avoid repeated 2FA:

```bash
cd mcp-tools/photo-migration

# First run - will require 2FA authentication
python test_client.py

# Subsequent runs - uses saved session (no 2FA needed)
python test_client.py

# Force fresh login (require 2FA even if session exists)
python test_client.py --fresh

# Clear saved session
python test_client.py --clear
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
    "photo-migration": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": ["-m", "photo_migration.server"],
      "cwd": "/absolute/path/to/mcp-tools/photo-migration",
      "env": {
        "APPLE_ID": "your.email@icloud.com",
        "APPLE_PASSWORD": "your_password"
      }
    }
  }
}
```

To find your absolute paths:
```bash
pwd  # Copy this path for 'cwd'
echo $VIRTUAL_ENV/bin/python  # Copy this for 'command'
```

### Using with Claude Desktop

1. Restart Claude Desktop after configuration
2. Look for "photo-migration" in available tools
3. Use the tool: "Check my iCloud photo status"
4. First use will require 2FA in the browser window
5. Subsequent uses will reuse the saved session

## 📁 Project Structure

```
ios-to-android-migration-assistant-agent/
├── shared/                   # Shared infrastructure (Phase 1)
│   ├── database/            # Centralized DuckDB
│   │   ├── migration_db.py  # Database singleton
│   │   └── schemas/         # SQL schemas for all tools
│   ├── config/              # Configuration management
│   └── utils/               # Shared utilities
├── mcp-tools/               # MCP tool implementations
│   ├── photo-migration/     # iCloud → Google Photos
│   │   ├── src/
│   │   │   └── photo_migration/
│   │   │       ├── icloud_client.py  # Client with session persistence
│   │   │       └── server.py         # MCP server implementation
│   │   ├── test_client.py           # Standalone test script
│   │   └── pyproject.toml           # Package configuration
│   ├── whatsapp/           # (Future) WhatsApp tools
│   └── family-services/    # (Future) Family coordination
├── scripts/                 # Utility scripts
│   ├── setup_database.py   # Initialize database
│   ├── migration_status.py # Check migration progress
│   └── test_*.py           # Test scripts
├── requirements/            # Tool specifications
├── .venv/                  # Virtual environment (create this)
├── .env                    # Your credentials (create this)
├── .env.template           # Environment template
└── requirements.txt        # Python dependencies
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

## 🚀 Future Enhancements

### Phase 2 (In Progress)
- [ ] Add `start_transfer` tool to initiate actual transfer
- [ ] Add `check_transfer_progress` tool with Google Photos API
- [ ] Add `verify_transfer_complete` with quality checks
- [ ] Add `check_completion_email` with Gmail integration

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