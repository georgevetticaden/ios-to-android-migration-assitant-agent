# iCloud Photo Migration MCP Server

An MCP (Model Context Protocol) server that automates checking iCloud photo library status via privacy.apple.com. This tool extracts real photo/video counts and storage information from your iCloud account with session persistence to avoid repeated 2FA authentication.

## Features

- 🔐 **Session Persistence**: Authenticate once with 2FA, then reuse the session for ~7 days
- 📸 **Real Data Extraction**: Gets actual photo/video counts from privacy.apple.com
- 🎬 **Detailed Metrics**: Reports photos, videos, total items, and storage usage
- 📅 **Transfer History**: Shows previous transfer request statuses
- 🤖 **MCP Integration**: Works as an MCP server for Claude Desktop and other MCP clients

## Current Status

✅ Successfully extracts:
- 60,238 photos
- 2,418 videos  
- 383 GB storage usage
- Previous transfer history

## Prerequisites

- Python 3.11+ (Important: Use Python 3.11, not the system Python 3.9.6)
- macOS, Linux, or Windows
- Apple ID with iCloud Photos enabled
- A device capable of receiving 2FA codes

## Installation

### 1. Clone and Navigate

```bash
cd ios-to-android-migration-assitant-agent/mcp-tools/photo-migration
```

### 2. Create Virtual Environment with Python 3.11

```bash
# Create venv with Python 3.11 explicitly
uv venv --python python3.11

# Activate virtual environment
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Verify Python version
python --version  # Should show Python 3.11.x
```

### 3. Install Dependencies

```bash
# Install the package in development mode
uv pip install -e .

# Install Playwright browsers
playwright install chromium
```

### 4. Set Up Credentials

Create a `.env` file in the photo-migration directory:

```bash
APPLE_ID=your.email@icloud.com
APPLE_PASSWORD=your_password
```

## Usage

### Standalone Testing

The tool supports session persistence to avoid repeated 2FA:

```bash
# First run - will require 2FA authentication
python test_client.py

# Subsequent runs - uses saved session (no 2FA needed)
python test_client.py

# Force fresh login (require 2FA even if session exists)
python test_client.py --fresh

# Clear saved session
python test_client.py --clear
```

### Command Line Options

- **No flags**: Uses saved session if available (< 7 days old)
- **`--fresh`**: Forces new login even if valid session exists
- **`--clear`**: Clears saved session and exits

### Session Persistence

Sessions are saved to `~/.icloud_session/` and include:
- Browser cookies and storage state
- Session metadata (timestamp, URL)
- Valid for approximately 7 days

The tool will automatically:
1. Check for existing valid session
2. Skip authentication if session is valid
3. Save new session after successful 2FA
4. Prompt for 2FA only when necessary

## MCP Server Configuration

### Configure Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "photo-migration": {
      "command": "/absolute/path/to/photo-migration/.venv/bin/python",
      "args": ["-m", "photo_migration.server"],
      "cwd": "/absolute/path/to/photo-migration",
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
cd mcp-tools/photo-migration
pwd  # Copy this path for 'cwd'
echo $VIRTUAL_ENV/bin/python  # Copy this for 'command'
```

### Using with Claude Desktop

1. Restart Claude Desktop after configuration
2. Look for "photo-migration" in available tools
3. Use the tool: "Check my iCloud photo status"
4. First use will require 2FA in the browser window
5. Subsequent uses will reuse the saved session

## How It Works

1. **Authentication Flow**:
   - Navigates to privacy.apple.com
   - Handles Apple's iframe-based authentication
   - Manages 2FA when required
   - Saves session for future use

2. **Data Extraction**:
   - Clicks "Request to transfer a copy of your data"
   - Selects "iCloud photos and videos"
   - Extracts counts from confirmation page
   - Parses storage information

3. **Session Management**:
   - Saves browser state after successful auth
   - Validates session age (< 7 days)
   - Automatically reuses valid sessions
   - Falls back to fresh login when needed

## Troubleshooting

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
- **"JSHandle error"**: Fixed in current version
- **"Could not find transfer button"**: May need to update selectors

## Project Structure

```
photo-migration/
├── src/
│   └── photo_migration/
│       ├── __init__.py
│       ├── icloud_client.py      # Main client with session persistence
│       └── server.py              # MCP server implementation
├── test_client.py                 # Standalone test script
├── record_flow.py                 # Utility to record user interactions
├── pyproject.toml                 # Package configuration
├── .env                          # Credentials (not in git)
└── README.md                     # This file
```

## Security Notes

- Credentials are never logged or stored in plain text
- Session data is stored locally in `~/.icloud_session/`
- Browser runs in non-headless mode for security transparency
- 2FA provides additional security layer
- Sessions expire after ~7 days

## Future Enhancements

- [ ] Add `start_transfer` tool to initiate actual transfer
- [ ] Add `monitor_progress` tool to track transfer status
- [ ] Support for selecting specific date ranges
- [ ] Google Photos integration for verification
- [ ] Automated retry on transient failures

## Development

### Running Tests

```bash
# Test the client directly
python -m pytest tests/

# Test with real credentials
python test_client.py
```

### Debugging

Enable debug logging:
```python
logging.basicConfig(level=logging.DEBUG)
```

View MCP server logs:
```bash
tail -f ~/Library/Logs/Claude/*.log | grep photo-migration
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test thoroughly with `python test_client.py`
4. Submit a pull request

## License

MIT

## Support

For issues or questions:
- Check existing issues in the repository
- Review logs in `mcp-tools/logs/`
- Ensure you're using Python 3.11+
- Verify Playwright installation