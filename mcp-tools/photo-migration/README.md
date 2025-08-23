# Photo Migration Tool - iCloud to Google Photos

## Overview
A production-ready tool that automates the complete migration of photos from iCloud to Google Photos. Currently processing 60,238 photos (383GB) with zero manual intervention required after initial setup.

## ✅ Current Status
**COMPLETE & OPERATIONAL** - Transfer TRF-20250820-180056 is actively running

## Features

### Core Capabilities
- **Automated Transfer**: Complete workflow from iCloud to Google Photos
- **Session Persistence**: 7-day validity for both Apple and Google accounts
- **2FA Support**: Handles two-factor authentication for both services
- **Progress Tracking**: Real-time monitoring of transfer status
- **Email Notifications**: Automatic detection of completion emails
- **Database Integration**: Full transfer history and progress tracking
- **Error Recovery**: Robust retry logic and comprehensive error handling

### Technical Features
- Browser automation with Playwright
- DuckDB for local data persistence
- Gmail API for email monitoring
- Centralized logging to `logs/` directory
- Environment-based configuration

## Quick Start

### Prerequisites
- Python 3.11 (required)
- Chrome/Chromium browser
- Apple ID with 2FA enabled
- Google account
- ~200MB free disk space

### Installation

```bash
# Clone the repository
cd mcp-tools/photo-migration

# Create virtual environment with Python 3.11
uv venv --python python3.11
source .venv/bin/activate

# Install dependencies
uv pip install -e .
playwright install chromium
```

### Configuration

Create `.env` file in project root:
```bash
APPLE_ID=your.email@icloud.com
APPLE_PASSWORD=your_password
GOOGLE_EMAIL=your.gmail@gmail.com
GOOGLE_PASSWORD=your_password
```

### Usage

#### Start New Transfer
```bash
python tests/test_migration_flow_simple.py
```

This will:
1. Authenticate with Apple (2FA required first time)
2. Get iCloud photo counts
3. Establish Google Photos baseline
4. Navigate transfer workflow
5. Stop at confirmation page for review
6. Start transfer upon confirmation

#### Check Progress
```bash
python tests/check_progress.py
```

#### Monitor Logs
```bash
tail -f ../../logs/photo_migration_$(date +%Y%m%d).log
```

## Database Queries

Check transfer status:
```sql
SELECT * FROM photo_migration.transfers 
WHERE transfer_id = 'TRF-20250820-180056';
```

View progress history:
```sql
SELECT * FROM photo_migration.progress_history 
WHERE transfer_id = 'TRF-20250820-180056'
ORDER BY checked_at DESC;
```

## Architecture

### Components
- **icloud_client.py**: Main client with transfer management
- **google_dashboard_client.py**: Google Photos monitoring via Dashboard
- **gmail_monitor.py**: Email completion tracking
- **icloud_transfer_workflow.py**: Apple workflow automation
- **logging_config.py**: Centralized logging configuration
- **server.py**: MCP server implementation

### Data Flow
1. **Authentication**: Saved sessions in `~/.icloud_session/` and `~/.google_session/`
2. **Database**: Transfer records in `~/.ios_android_migration/migration.db`
3. **Logs**: All activity in `ios-to-android-migration-assitant-agent/logs/`
4. **Screenshots**: Error screenshots saved to logs directory

## Two-Step Confirmation Process

The tool implements a deliberate two-step confirmation to prevent accidental transfers:

1. **start_transfer()**: Navigates to confirmation page but doesn't click confirm
2. **confirm_transfer_final_step()**: Actually starts the transfer

This design ensures:
- User can review exact photo count (60,238 photos)
- Verify destination account
- Check storage requirements (383GB)
- Make informed decision before 3-7 day process

## Troubleshooting

### Common Issues

#### Database Lock Error
**Problem**: "Could not set lock on file" when DBeaver is open
**Solution**: Close DBeaver or use read-only mode test

#### 2FA Timeout
**Problem**: Code expires before entry
**Solution**: Have device ready, check Notification Center on Mac

#### Session Expired
**Problem**: Sessions older than 7 days
**Solution**: Run with `--fresh` flag or delete session directories

### Clear Sessions
```bash
# Clear iCloud session
rm -rf ~/.icloud_session

# Clear Google session
rm -rf ~/.google_session

# Clear both
python utils/clear_sessions.py
```

## Performance Metrics

- **Authentication**: ~30 seconds (with 2FA)
- **Session Reuse**: < 5 seconds
- **Baseline Check**: ~10 seconds
- **Transfer Start**: ~45 seconds
- **Progress Check**: ~15 seconds
- **Memory Usage**: ~200MB
- **CPU Usage**: < 5% average

## Security

- All credentials in environment variables
- No credentials in logs or database
- Sessions encrypted locally
- Browser runs in visible mode
- Two-step confirmation required
- HTTPS only communication

## Testing

### Run Tests
```bash
# Full migration flow
python tests/test_migration_flow_simple.py

# Check existing transfer
python tests/check_progress.py

# Test with fresh session
python tests/test_basic_auth.py --fresh
```

### Test Coverage
- ✅ Authentication flow
- ✅ Session persistence
- ✅ Transfer initiation
- ✅ Progress tracking
- ✅ Email monitoring
- ✅ Database operations
- ✅ Error recovery

## MCP Integration

The tool exposes these MCP tools:
1. `check_icloud_status` - Get photo counts
2. `start_transfer` - Initiate transfer with baseline
3. `check_transfer_progress` - Monitor progress
4. `check_completion_email` - Check for emails
5. `verify_transfer_complete` - Verify completion

## Known Limitations

1. **Transfer Time**: Apple takes 3-7 days to process
2. **No Cancellation**: Once confirmed, transfer cannot be stopped
3. **Single Transfer**: One transfer at a time per Apple ID
4. **Browser Required**: Cannot run headless due to 2FA

## Support

### Logs Location
- Main logs: `../../logs/photo_migration_YYYYMMDD.log`
- Screenshots: `../../logs/[error_type]_YYYYMMDD_HHMMSS.png`

### Database Location
- Database: `~/.ios_android_migration/migration.db`
- Sessions: `~/.icloud_session/` and `~/.google_session/`

## License
MIT

---

**Current Transfer**: TRF-20250820-180056 (60,238 photos, 383GB)
**Status**: In Progress
**Expected Completion**: August 23-27, 2025