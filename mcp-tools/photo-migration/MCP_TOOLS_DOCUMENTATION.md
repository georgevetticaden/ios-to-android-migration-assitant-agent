# Photo Migration MCP Tools Documentation

## Overview
This document describes the 5 MCP tools exposed by the photo-migration server for iOS to Android photo migration. All credentials are managed internally via environment variables and are NEVER passed as parameters.

**Implementation Status:**
- ✅ Tool 1: `check_icloud_status` - Fully tested standalone
- 🚧 Tool 2: `start_photo_transfer` - Standalone tested, MCP integration pending
- 🚧 Tool 3: `check_photo_transfer_progress` - Standalone tested, MCP integration pending
- 🚧 Tool 4: `verify_photo_transfer_complete` - Standalone tested, MCP integration pending 
- 🚧 Tool 5: `check_photo_transfer_email` - Gmail OAuth tested, MCP integration pending

---

## Tool 1: `check_icloud_status` ✅
**Purpose**: Get current photo/video counts from iCloud and check for existing transfers
**Testing Status**: Fully tested with standalone and MCP

### Parameters
- `reuse_session` (boolean, optional): Whether to reuse saved browser session. Default: `true`

### Returns
```json
{
  "status": "success",
  "photos": 60238,
  "videos": 2418,
  "total_items": 62656,
  "storage_gb": 383,
  "transfer_history": [
    {
      "status": "Cancelled",
      "date": "Aug 10, 2025"
    }
  ],
  "session_used": true
}
```

### When to Use
- Initial assessment of migration scope
- Checking if previous transfers exist
- Verifying source counts before starting transfer

### Example Claude Usage
```
"I need to check how many photos are in the user's iCloud account"
→ Calls check_icloud_status(reuse_session=true)
```

---

## Tool 2: `start_photo_transfer` 🚧
**Purpose**: Initiate the iCloud to Google Photos transfer process
**Testing Status**: Standalone implementation tested, MCP wrapper pending verification

### Parameters
- `reuse_session` (boolean, optional): Whether to reuse saved browser session. Default: `true`

### Internal Process
1. Establishes Google Photos baseline (current count)
2. Gets iCloud photo/video counts
3. Navigates Apple transfer workflow
4. Creates transfer record in database

### Returns
```json
{
  "status": "initiated",
  "transfer_id": "TRF-20250820-143022",
  "started_at": "2025-08-20T14:30:22Z",
  "source_counts": {
    "photos": 60238,
    "videos": 2418,
    "total": 62656,
    "size_gb": 383
  },
  "destination": {
    "service": "Google Photos",
    "account": "REDACTED"
  },
  "baseline_established": {
    "pre_transfer_count": 42,
    "baseline_timestamp": "2025-08-20T14:30:00Z"
  },
  "estimated_completion_days": "3-7"
}
```

### When to Use
- User says "Start the photo transfer"
- After confirming user is ready to begin migration
- Only after checking iCloud status

### Example Claude Usage
```
User: "I'm ready to start transferring my photos to Google"
→ Calls start_photo_transfer()
→ Returns transfer_id for tracking
```

---

## Tool 3: `check_photo_transfer_progress` 🚧
**Purpose**: Monitor ongoing transfer progress
**Testing Status**: Core functionality tested, MCP integration needs verification

### Parameters
- `transfer_id` (string, required): The transfer ID from start_photo_transfer

### Returns
```json
{
  "transfer_id": "TRF-20250820-143022",
  "status": "in_progress",
  "timeline": {
    "started_at": "2025-08-20T14:30:22Z",
    "checked_at": "2025-08-22T10:15:00Z",
    "days_elapsed": 1.8,
    "estimated_completion": "2025-08-24T16:00:00Z"
  },
  "counts": {
    "source_total": 62656,
    "baseline_google": 42,
    "current_google": 28500,
    "transferred_items": 28458,
    "remaining_items": 34198
  },
  "progress": {
    "percent_complete": 45.4,
    "transfer_rate_per_day": 15810,
    "transfer_rate_per_hour": 659
  }
}
```

### When to Use
- User asks "How's my transfer going?"
- Daily status checks
- Before verification

### Example Claude Usage
```
User: "What's the status of my photo transfer?"
→ Calls check_photo_transfer_progress(transfer_id="TRF-20250820-143022")
→ Reports: "Your transfer is 45% complete, about 2 days remaining"
```

---

## Tool 4: `verify_photo_transfer_complete` 🚧
**Purpose**: Final verification that all photos transferred successfully
**Testing Status**: Logic implemented, MCP protocol testing required

### Parameters
- `transfer_id` (string, required): The transfer ID to verify
- `important_photos` (array, optional): List of specific photo filenames to check
- `include_email_check` (boolean, optional): Check for Apple completion email. Default: `true`

### Returns
```json
{
  "transfer_id": "TRF-20250820-143022",
  "status": "complete",
  "completed_at": "2025-08-24T16:45:00Z",
  "verification": {
    "source_photos": 60238,
    "destination_photos": 60238,
    "match_rate": 100.0
  },
  "email_confirmation": {
    "email_found": true,
    "email_received_at": "2025-08-24T16:30:00Z"
  },
  "certificate": {
    "grade": "A+",
    "score": 100,
    "message": "Perfect Migration - Zero Data Loss"
  }
}
```

### When to Use
- User asks "Is my transfer complete?"
- After progress shows 99%+
- Final migration validation

### Example Claude Usage
```
User: "Can you verify all my photos transferred?"
→ Calls verify_photo_transfer_complete(transfer_id="TRF-20250820-143022")
→ Reports: "Perfect! All 60,238 photos and 2,418 videos transferred successfully"
```

---

## Tool 5: `check_photo_transfer_email` 🚧
**Purpose**: Check for Apple's transfer completion email
**Testing Status**: Gmail OAuth flow working, MCP wrapper needs testing

### Parameters
- `transfer_id` (string, required): The transfer ID to check emails for

### Returns
```json
{
  "transfer_id": "TRF-20250820-143022",
  "email_found": true,
  "email_details": {
    "subject": "Your transfer to Google Photos is complete",
    "sender": "appleid@apple.com",
    "received_at": "2025-08-24T16:30:00Z",
    "content_summary": {
      "message": "Transfer completion confirmed"
    }
  }
}
```

### When to Use
- User asks "Did I get the completion email?"
- Part of final verification
- Troubleshooting transfer status

### Example Claude Usage
```
User: "Have I received any emails from Apple about the transfer?"
→ Calls check_photo_transfer_email(transfer_id="TRF-20250820-143022")
→ Reports: "Yes, Apple sent a completion email at 4:30 PM today"
```

---

## Environment Variables Required

All tools require these environment variables to be configured:

```bash
# Apple Account (Source)
APPLE_ID=user@icloud.com
APPLE_PASSWORD=apple_password

# Google Account (Destination)
GOOGLE_EMAIL=user@gmail.com
GOOGLE_PASSWORD=google_password

# Gmail API (for email checking)
GMAIL_CREDENTIALS_PATH=/path/to/gmail_oauth2_credentials.json

# Database (optional, falls back to local JSON)
MIGRATION_DB_PATH=~/.ios_android_migration/migration.db

# Session directories (auto-created)
ICLOUD_SESSION_DIR=~/.icloud_session
GOOGLE_SESSION_DIR=~/.google_session
```

---

## Important Notes for Claude Agent

1. **NEVER ask users for credentials** - All authentication is handled internally
2. **Save transfer_id** - Store the transfer_id from start_photo_transfer for all subsequent operations
3. **Check status before verification** - Always check progress before running verification
4. **Session persistence** - Tools reuse browser sessions for 7 days to avoid repeated 2FA
5. **Error handling** - If a tool returns an error about missing credentials, inform the user to configure environment variables

---

## Testing Instructions

### Current Test Method (Standalone)
```bash
cd mcp-tools/photo-migration
source .venv/bin/activate

# Test complete flow
python test_migration_flow.py

# Test individual components
python test_basic_auth.py      # Test authentication only
python utils/clear_sessions.py # Clear saved sessions
```

### Pending MCP Server Testing
```bash
# Test MCP protocol (needs verification)
python test_mcp_server.py

# Configure Claude Desktop (pending)
# Add to claude_desktop_config.json and test each tool
```

## Typical Migration Flow

1. **Day 1 - Start Migration**
   ```
   → check_icloud_status()
   → start_photo_transfer()
   Save transfer_id: TRF-20250820-143022
   ```

2. **Day 2-4 - Monitor Progress**
   ```
   → check_photo_transfer_progress(transfer_id)
   Report progress percentage
   ```

3. **Day 5 - Verify Completion**
   ```
   → check_photo_transfer_progress(transfer_id)
   If near 100%:
   → verify_photo_transfer_complete(transfer_id)
   → check_photo_transfer_email(transfer_id)
   ```

---

## Error Responses

All tools return consistent error format:
```json
{
  "status": "error",
  "error": "Descriptive error message",
  "details": "Additional context if available"
}
```

Common errors:
- Missing environment variables
- Session expired (request reuse_session=false)
- Transfer not found (invalid transfer_id)
- Network issues
- Gmail API not configured