# Claude Desktop Configuration Guide

## Overview

This guide documents the Claude Desktop configuration for the iOS to Android Migration Assistant project. All three MCP servers are configured and operational.

## Configuration File Location

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`

## Complete Configuration

```json
{
  "mcpServers": {
    "web-automation": {
      "command": "/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/.venv/bin/python",
      "args": [
        "-m",
        "web_automation.server"
      ],
      "cwd": "/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/mcp-tools/web-automation"
    },
    "mobile-mcp-local": {
      "command": "node",
      "args": [
        "/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/mcp-tools/mobile-mcp/lib/index.js",
        "--stdio"
      ],
      "env": {
        "NODE_ENV": "production"
      }
    },
    "migration-state": {
      "command": "/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/.venv/bin/python",
      "args": [
        "/Users/aju/Dropbox/Development/Git/08-14-2025-ios-to-android-migration-agent-take-2/ios-to-android-migration-assitant-agent/mcp-tools/migration-state/server.py"
      ]
    }
  }
}
```

## Server Details

### 1. web-automation (Browser Automation)

**Purpose**: Handles web-based automation tasks, primarily iCloud photo migration

**Key Configuration**:
- Runs as a Python module (`-m web_automation.server`)
- Requires `cwd` to be set to the web-automation directory
- Reads Apple credentials from `.env` file in project root

**Available Tools** (5 total):
- `check_icloud_status` - Check iCloud photo library status
- `start_photo_transfer` - Initiate iCloud to Google Photos transfer
- `check_photo_transfer_progress` - Monitor transfer progress
- `verify_photo_transfer_complete` - Verify transfer completion
- `check_photo_transfer_email` - Check for Apple completion email

### 2. mobile-mcp-local (Android Control)

**Purpose**: Control Android devices via ADB using natural language commands

**Key Configuration**:
- Runs as a Node.js application
- Uses `--stdio` for MCP protocol communication
- Requires Android device connected via USB with debugging enabled

**Requirements**:
- Android device (Galaxy Z Fold 7) connected via USB
- USB debugging enabled on device
- ADB installed and accessible

### 3. migration-state (Database Operations)

**Purpose**: Manage migration state in DuckDB database

**Key Configuration**:
- Runs as a standalone Python script
- No `cwd` needed as full path is provided

**Available Tools** (6 total):
- `get_migration_status` - Get current migration state
- `update_migration_progress` - Update progress metrics
- `initialize_migration` - Start a new migration
- `get_pending_items` - Get list of items to migrate
- `mark_item_complete` - Mark items as completed
- `get_migration_statistics` - Get migration statistics as JSON

## Environment Variables

The project uses a `.env` file in the root directory for sensitive configuration:

```bash
# Apple credentials for web-automation
APPLE_ID=your.email@icloud.com
APPLE_PASSWORD=your_password

# Gmail API (optional, for email monitoring)
GMAIL_CREDENTIALS_PATH=/path/to/gmail_credentials.json
```

## Applying Configuration Changes

1. **Save the configuration file**
2. **Completely quit Claude Desktop** (Cmd+Q on macOS)
3. **Restart Claude Desktop**
4. **Verify servers are loaded** - Check the tool menu or ask "What MCP tools are available?"

## Troubleshooting

### Servers Not Appearing

1. Check configuration file syntax (valid JSON)
2. Verify all paths are absolute and correct
3. Check logs: `tail -f ~/Library/Logs/Claude/mcp*.log`

### Python Module Import Errors

Ensure virtual environment packages are installed:
```bash
cd /path/to/project
source .venv/bin/activate
pip install -e mcp-tools/web-automation/
pip install -r mcp-tools/migration-state/requirements.txt
```

### Node.js Errors

Ensure mobile-mcp is built:
```bash
cd mcp-tools/mobile-mcp
npm install
npm run build
```

### Database Lock Issues

If migration-state reports database lock:
- Close DBeaver or other database viewers
- Check for other processes accessing the database

## Testing Configuration

In Claude Desktop, test each server:

```
# Test web-automation
"Check my iCloud photo status"

# Test mobile-mcp-local
"Take a screenshot of my Android device"

# Test migration-state
"Get the current migration status from the database"
```

## Notes

- **Path Flexibility**: All paths must be absolute. Update them based on where you clone the repository.
- **Credentials**: The web-automation server reads credentials from the `.env` file, not from Claude Desktop config.
- **Server Names**: The names (web-automation, mobile-mcp-local, migration-state) are what appear in Claude Desktop.

---

*Last Updated: August 23, 2025*