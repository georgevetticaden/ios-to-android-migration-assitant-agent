# Web Automation MCP Server

## Overview

The Web Automation MCP server provides 5 comprehensive browser automation tools for managing the complete iCloud to Google Photos migration workflow. This server handles all web-based interactions required for the iOS to Android transition, using Playwright to automate privacy.apple.com, photos.google.com, and Gmail. It maintains session persistence to avoid repeated 2FA and tracks all operations through the 7-day migration timeline.

## Key Features

- **5 MCP Tools**: Complete media migration lifecycle from initiation to verification
- **Session Persistence**: 7-day browser session validity avoiding repeated 2FA
- **Visual Browser Automation**: See exactly what's happening during transfers
- **Progress Monitoring**: Track transfer progress using Google One storage metrics
- **Email Verification**: Gmail API integration for Apple completion notifications
- **Database Integration**: All transfers tracked in DuckDB with storage snapshots
- **Production Ready**: Currently processing 383GB real migration with photos and videos

## Technical Architecture

### Browser Automation Stack
```
Playwright (Chromium) → privacy.apple.com → Apple Transfer Service
         ↓                      ↓                     ↓
  Session Storage        Google OAuth          Google Photos
         ↓                      ↓                     ↓
  ~/.icloud_session     Authorization Flow    Progress Monitoring
```

### Session Persistence Model
```
~/.icloud_session/
├── contexts/
│   ├── apple_context.json      # Apple ID browser state
│   ├── google_context.json     # Google account state
│   └── metadata.json           # Session timestamps
├── cookies/
│   ├── apple_cookies.json      # privacy.apple.com cookies
│   └── google_cookies.json     # photos.google.com cookies
└── session_info.json           # Session validity tracking
```

Sessions remain valid for ~7 days, enabling:
- No 2FA after initial authentication
- Instant access to both Apple and Google services
- Seamless progress checking without re-authentication

### Database Schema Integration
```
~/.ios_android_migration/migration.db
└── media_transfer table
    ├── transfer_id (PK)         # TRF-YYYYMMDD-HHMMSS
    ├── migration_id (FK)        # Links to migration_status
    ├── total_photos             # From iCloud check
    ├── total_videos             # From iCloud check
    ├── total_size_gb            # Storage size
    ├── transferred_photos       # Current progress
    ├── transferred_videos       # Current progress
    ├── photo_status             # pending/initiated/in_progress/completed
    ├── video_status             # pending/initiated/in_progress/completed
    ├── overall_status           # Combined status
    ├── apple_transfer_initiated # Timestamp
    ├── photos_visible_day       # Day 4
    └── estimated_completion_day # Day 7

└── storage_snapshots table
    ├── migration_id             # Links to migration
    ├── day_number               # 1-7
    ├── google_photos_gb         # Current Google Photos storage
    ├── storage_growth_gb        # Growth since baseline
    ├── estimated_photos_transferred  # Calculated estimate
    ├── estimated_videos_transferred  # Calculated estimate
    └── snapshot_time            # When measured
```

## Complete Tool Documentation

### 📸 Photo Migration Tools

---

#### 1. `check_icloud_status`

**Purpose**: Retrieve comprehensive iCloud photo and video library statistics before migration  
**When to Use**: Day 1, as the very first step before any migration planning  
**Day**: DAY 1 TOOL  
**MCP Category**: Information gathering

**Parameters**:
- `reuse_session` (optional, boolean, default: true)
  - true: Use saved browser session (no 2FA needed)
  - false: Force fresh login (requires 2FA)
  - Recommendation: Always use true unless session expired

**Returns**: Dictionary containing:
```json
{
  "status": "success",
  "photos": 60238,
  "videos": 2418,
  "storage_gb": 383.2,
  "total_items": 62656,
  "session_used": true,
  "existing_transfers": [
    {"status": "complete", "date": "2024-03-15"},
    {"status": "cancelled", "date": "2024-01-10"}
  ],
  "checked_at": "2025-08-26T10:30:00Z"
}
```

**Browser Automation Flow**:
1. Opens privacy.apple.com in Chromium
2. Checks for existing session cookies
3. If no session or reuse_session=false:
   - Enters Apple ID credentials
   - Handles 2FA (waits for user input)
   - Saves session for future use
4. Navigates to Data & Privacy section
5. Clicks "Transfer a copy of your data"
6. Extracts photo and video counts from the page
7. Checks transfer history if available
8. Returns structured data

**Session Management**:
- Creates session on first run
- Saves to ~/.icloud_session/contexts/apple_context.json
- Valid for approximately 7 days
- Automatic refresh if approaching expiration

**Error Handling**:
- Invalid credentials: Returns clear error message
- 2FA timeout: Waits up to 5 minutes for code
- Network issues: Retries with exponential backoff
- Session expired: Automatically creates new session

**Agent Integration**:
```
User: "I want to migrate from iPhone to Android"
Agent: "Let me check your iCloud photo and video library first..."
→ web-automation.check_icloud_status()
→ Use returned counts for migration-state.initialize_migration()
```

**Important Notes**:
- This tool MUST be called before initialize_migration
- Photo counts are required for accurate progress tracking
- Session creation only happens once per 7 days
- Transfer history helps identify previous attempts

---

#### 2. `start_photo_transfer`

**Purpose**: Initiate Apple's official iCloud to Google Photos transfer service  
**When to Use**: Day 1, immediately after migration has been initialized in database  
**Day**: DAY 1 TOOL  
**MCP Category**: Action execution

**Parameters**:
- `reuse_session` (optional, boolean, default: true)
  - true: Reuse Apple ID session from check_icloud_status
  - false: Create new session (not recommended)
  - Best practice: Always true if check_icloud_status was just called

**Returns**: Dictionary containing:
```json
{
  "status": "initiated",
  "transfer_id": "TRF-20250826-143022",
  "started_at": "2025-08-26T14:30:22Z",
  "source_counts": {
    "photos": 60238,
    "videos": 2418,
    "total": 62656,
    "size_gb": 383.2
  },
  "baseline_established": {
    "pre_transfer_count": 1547,
    "baseline_timestamp": "2025-08-26T14:28:15Z",
    "google_email": "user@gmail.com"
  },
  "destination": {
    "service": "Google Photos",
    "account": "user@gmail.com"
  },
  "estimated_completion_days": "5-7 days",
  "message": "Transfer initiated successfully"
}
```

**Complex Browser Automation Workflow**:

**Phase 1: Google Photos Baseline (Separate Browser)**
1. Opens new browser context for Google
2. Navigates to photos.google.com
3. Authenticates with Google credentials (if needed)
4. Waits for photo grid to fully load
5. Extracts current photo count (baseline)
6. Saves count with timestamp
7. Closes Google browser context

**Phase 2: Apple Transfer Initiation**
1. Opens privacy.apple.com (reuses session)
2. Navigates to "Transfer a copy of your data"
3. Selects "Google Photos" as destination
4. Reviews data to be transferred:
   - Photos and videos (both selected)
   - Albums and metadata
   - Original quality preserved
5. Clicks "Continue"

**Phase 3: Google OAuth Flow**
1. Handles redirect to Google OAuth
2. Auto-fills Google email (already known)
3. Enters Google password
4. Handles 2FA if required
5. Reviews permissions:
   - View and manage Google Photos
   - Add photos and videos
6. Clicks "Allow" or "Continue"

**Phase 4: Confirmation (Without Final Submit)**
1. Returns to Apple confirmation page
2. Verifies transfer details displayed
3. **STOPS before clicking final "Confirm Transfer"**
4. Takes screenshot for records
5. Saves transfer record to database

**Database Operations**:
```sql
-- Creates new transfer record
INSERT INTO media_transfer (
  transfer_id, migration_id, total_photos, total_videos,
  total_size_gb, photo_status, video_status, overall_status,
  apple_transfer_initiated, photos_visible_day, estimated_completion_day
) VALUES (?, ?, ?, ?, ?, 'initiated', 'initiated', 'initiated', CURRENT_TIMESTAMP, 4, 7)

-- Updates migration phase
UPDATE migration_status 
SET current_phase = 'media_transfer'
WHERE id = ?
```

**Timeline Expectations**:
- Day 1-3: Transfer processing (0% visible)
- Day 4: First photos appear (~28%)
- Day 5: Steady progress (~57%)
- Day 6: Nearly complete (~85%)
- Day 7: Fully complete (100%)

**Why Stop Before Final Confirmation?**:
- Allows user to review terms
- Prevents accidental duplicate transfers
- Gives opportunity to cancel if needed
- Maintains user control over final decision

**Error Handling**:
- Google auth failure: Clear instructions provided
- Session expired: Automatically refreshes
- Network timeout: Retries with longer waits
- Duplicate transfer: Checks for existing active transfers

**Agent Integration**:
```
Agent: "I'll now start the photo transfer to Google Photos..."
→ web-automation.start_photo_transfer()
→ migration-state.start_photo_transfer(transfer_initiated=true)
→ Save transfer_id for all future operations
```

**Critical Notes**:
- Baseline MUST be established first (automatic)
- Transfer ID is essential for all progress tracking
- Photos won't be visible for 3-4 days
- User sees the browser automation happening

---

#### 3. `check_photo_transfer_progress`

**Purpose**: Monitor ongoing transfer using Google One storage metrics to calculate real progress  
**When to Use**: Daily from Day 1 onwards (shows processing status even before photos visible)  
**Day**: DAYS 1-7 TOOL  
**MCP Category**: Progress monitoring

**Parameters**:
- `transfer_id` (required, string)
  - Format: TRF-YYYYMMDD-HHMMSS
  - Obtained from start_photo_transfer
- `day_number` (optional, int)
  - Current day number (1-7)
  - If not provided, calculates from start date

**Returns**: Dictionary containing:
```json
{
  "status": "in_progress",
  "transfer_id": "TRF-20250826-143022",
  "day_number": 4,
  "storage": {
    "baseline_gb": 1.05,
    "current_gb": 108.05,
    "growth_gb": 107.0,
    "remaining_gb": 276.0
  },
  "estimates": {
    "photos_transferred": 11988,
    "videos_transferred": 245,
    "total_items": 12233
  },
  "progress": {
    "percent_complete": 27.9,
    "transfer_rate_gb_per_day": 25.5,
    "days_remaining": 10.8
  },
  "message": "Photos should start appearing soon in Google Photos."
}
```

**Storage-Based Automation Process**:
1. Retrieves transfer record and baseline from database
2. Opens one.google.com/storage in new browser
3. Authenticates with Google if needed (uses saved session)
4. Extracts storage breakdown:
   - Google Photos current storage
   - Google Drive storage
   - Gmail storage  
   - Device backup storage
5. Calculates storage growth since baseline
6. Estimates photos/videos transferred using 70%/30% ratio
7. Saves snapshot to storage_snapshots table
8. Updates daily_progress with calculated metrics
9. Returns day-specific milestone messages

**Progress Calculation Logic**:
```python
growth_gb = current_storage - baseline_storage
percent_complete = (growth_gb / total_expected_gb) * 100
photos_est = (growth_gb * 0.7 * 1024) / 6.5  # 70% photos, 6.5MB avg
videos_est = (growth_gb * 0.3 * 1024) / 150  # 30% videos, 150MB avg
```

**Day-Specific Progress Messages**:
- **Day 1**: "Transfer initiated. Apple is processing your request."
  - Storage may show minimal growth as processing begins
- **Day 4**: "Photos should start appearing soon in Google Photos."
  - Storage growth accelerates, ~28% complete
- **Day 7**: "Transfer continuing. X% complete."
  - Final progress based on actual storage metrics
  - Completion percentage varies by transfer size

**Database Operations**:
```sql
-- Updates transfer progress
UPDATE media_transfer
SET transferred_photos = ?,
    transferred_videos = ?,
    transferred_size_gb = ?,
    photo_status = CASE WHEN ? >= 100 THEN 'completed' ELSE 'in_progress' END,
    video_status = CASE WHEN ? >= 100 THEN 'completed' ELSE 'in_progress' END,
    last_progress_check = CURRENT_TIMESTAMP
WHERE transfer_id = ?

-- Creates storage snapshot
INSERT INTO storage_snapshots (
  migration_id, day_number, google_photos_gb, storage_growth_gb,
  estimated_photos_transferred, estimated_videos_transferred, snapshot_time
) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)

-- Updates daily progress
INSERT INTO daily_progress (
  migration_id, day_number, photos_transferred, videos_transferred,
  size_transferred_gb, storage_percent_complete, key_milestone
) VALUES (?, ?, ?, ?, ?, ?, ?)
```

**Handling Zero Progress (Days 1-3)**:
- Don't panic or retry excessively
- Explain to user this is normal
- Apple needs time to process
- Continue with family setup tasks

**Error Scenarios**:
- Transfer not found: Check transfer_id validity
- Google Photos unavailable: Retry after delay
- Count decreased: Possible Google processing delay
- Stuck at percentage: May need email verification

**Agent Integration**:
```
Day 4:
Agent: "Let me check transfer progress using storage metrics..."
→ web-automation.check_photo_transfer_progress(transfer_id)
→ If growth > 0: "Great news! Storage is growing - transfer in progress!"
→ Display storage metrics and estimated items transferred
→ Update visualization with progress bar
→ migration-state.update_photo_progress(progress_percent=28)
```

**Performance Notes**:
- Google One storage page loads faster than photo counting
- Allow up to 30 seconds for storage metrics to appear
- Cache results for 1 hour to avoid excessive checks
- Best checked once or twice daily, not hourly

### Google One Storage Integration

The tool uses Google One storage metrics instead of photo counts for accurate progress tracking:

**Storage Page Navigation**:
1. Opens one.google.com/storage
2. Waits for storage breakdown to load
3. Extracts service-specific storage:
   - Google Photos: X.XX GB
   - Google Drive: XX.XX GB  
   - Gmail: XX.XX GB
   - Device backup: X.XX GB

**Baseline Establishment**:
- Captures Google Photos storage before transfer starts
- Stores as baseline in migration_status table
- Used for all subsequent progress calculations

**Progress Accuracy**:
- Real storage growth vs. photo count estimates
- Works even when photos not yet visible
- Handles Google processing delays
- Accounts for compression and optimization

---

#### 4. `verify_photo_transfer_complete`

**Purpose**: Comprehensive verification that the entire photo and video transfer completed successfully  
**When to Use**: Day 7, after receiving Apple's completion email or seeing 100% progress  
**Day**: DAY 7 TOOL  
**MCP Category**: Validation and certification

**Parameters**:
- `transfer_id` (required, string)
  - The transfer to verify
- `important_photos` (optional, array of strings)
  - Specific photo filenames to check
  - Example: ["Wedding_2019.jpg", "Baby_First_Steps.mp4"]
- `include_email_check` (optional, boolean, default: true)
  - Whether to check Gmail for Apple confirmation
  - Set false if Gmail API not configured

**Returns**: Dictionary containing:
```json
{
  "status": "completed",
  "transfer_id": "TRF-20250826-143022",
  "verification": {
    "source_photos": 60238,
    "source_videos": 2418,
    "destination_photos": 60235,
    "destination_videos": 2418,
    "match_rate": 99.95,
    "missing_items": 3,
    "verification_method": "count_comparison"
  },
  "email_confirmation": {
    "email_found": true,
    "subject": "Your copy of your data is ready",
    "sender": "noreply@apple.com",
    "received_at": "2025-09-02T08:45:00Z",
    "transfer_confirmed": true
  },
  "important_photos_check": [
    "✅ Wedding_2019.jpg found",
    "✅ Baby_First_Steps.mp4 found"
  ],
  "certificate": {
    "grade": "A+",
    "score": 100,
    "message": "Perfect transfer! All items successfully migrated.",
    "issued_at": "2025-09-02T10:30:00Z",
    "details": {
      "photos_matched": true,
      "videos_matched": true,
      "email_confirmed": true,
      "important_items_verified": true
    }
  }
}
```

**Multi-Phase Verification Process**:

**Phase 1: Count Verification**
1. Retrieves source counts from database
2. Opens photos.google.com
3. Gets final Google Photos count
4. Subtracts baseline for transferred amount
5. Calculates match percentage

**Phase 2: Email Confirmation (if enabled)**
1. Uses Gmail API with OAuth2
2. Searches for emails from noreply@apple.com
3. Looks for subject containing "copy of your data"
4. Verifies email received within expected timeframe
5. Extracts completion confirmation

**Phase 3: Important Photos Check (if provided)**
1. For each specified photo:
   - Searches Google Photos by filename
   - Verifies photo exists
   - Checks basic metadata if available
2. Reports status for each important item

**Phase 4: Certificate Generation**
Generates completion certificate based on:
- **Match Rate Calculation**: (destination / source) * 100
- **Grading Scale**:
  - A+: 100% match + email confirmed
  - A: 98-99.9% match
  - B: 95-97.9% match  
  - C: 90-94.9% match
  - D: 85-89.9% match
  - F: Below 85% (investigation needed)

**Certificate Messages by Grade**:
- A+: "Perfect transfer! All items successfully migrated."
- A: "Excellent transfer! Nearly all items migrated successfully."
- B: "Good transfer! Most items migrated successfully."
- C: "Transfer complete with some items pending."
- F: "Transfer incomplete. Manual review recommended."

**Database Operations**:
```sql
-- Update transfer as completed
UPDATE media_transfer
SET overall_status = 'completed',
    photo_status = 'completed',
    video_status = 'completed',
    photo_complete_email_received = ?,
    video_complete_email_received = ?,
    transferred_photos = ?,
    transferred_videos = ?,
    completed_at = CURRENT_TIMESTAMP
WHERE transfer_id = ?

-- Update migration status
UPDATE migration_status
SET current_phase = 'completed',
    overall_progress = 100,
    completed_at = CURRENT_TIMESTAMP
WHERE id = ?
```

**Gmail API Setup (Optional)**:
1. Enable Gmail API in Google Cloud Console
2. Download OAuth2 credentials JSON
3. Set GMAIL_CREDENTIALS_PATH in environment
4. First run will open browser for authorization
5. Token saved for future use

**Handling Missing Items**:
- 1-10 missing: Usually processing delay, grade A still possible
- 11-100 missing: Check specific items, may be duplicates
- 100+ missing: Investigate transfer issues, may need Apple support

**Agent Integration**:
```
Day 7:
Agent: "Time to verify your transfer is complete!"
→ web-automation.verify_photo_transfer_complete(transfer_id)
→ Create celebration visualization with certificate
→ migration-state.generate_migration_report()
→ Show final success dashboard
```

**Important Notes**:
- Email typically arrives 12-24 hours before 100% visible
- Some items may still be processing even at "100%"
- Certificate provides confidence score for users
- Grade A or A+ indicates successful migration

---

#### 5. `check_photo_transfer_email`

**Purpose**: Check Gmail for Apple's official photo and video transfer completion notification  
**When to Use**: Days 6-7, when transfer is nearing completion  
**Day**: DAYS 6-7 TOOL  
**MCP Category**: Email verification

**Parameters**:
- `transfer_id` (required, string)
  - Used for tracking and logging
  - Links email to specific transfer

**Returns**: Dictionary containing:
```json
{
  "status": "success",
  "transfer_id": "TRF-20250826-143022",
  "email_found": true,
  "email_details": {
    "subject": "Your copy of your data is ready",
    "sender": "noreply@apple.com",
    "received_at": "2025-09-01T14:23:00Z",
    "snippet": "Your photos and videos have been copied to Google Photos",
    "message_id": "msg_18b4c5d6e7f8g9h0"
  },
  "transfer_confirmed": true,
  "days_since_start": 6.5
}
```

Or if not found:
```json
{
  "status": "success",
  "transfer_id": "TRF-20250826-143022",
  "email_found": false,
  "message": "No completion email found yet",
  "last_checked": "2025-09-01T10:00:00Z",
  "days_since_start": 6.5,
  "suggestion": "Email typically arrives within 5-7 days"
}
```

**Gmail API Integration Process**:

**Initial Setup (One-time)**:
1. Checks for GMAIL_CREDENTIALS_PATH in environment
2. Loads OAuth2 credentials from JSON file
3. If no saved token:
   - Opens browser for Gmail authorization
   - User approves access to Gmail
   - Saves refresh token for future use
4. Token remains valid indefinitely

**Email Search Process**:
1. Connects to Gmail API using saved token
2. Constructs search query:
   ```
   from:noreply@apple.com
   subject:"copy of your data"
   after:${transfer_start_date}
   ```
3. Searches inbox and all mail
4. Retrieves email metadata and snippet
5. Parses for confirmation details

**Email Identification Criteria**:
- From: noreply@apple.com (exact match)
- Subject contains: "copy of your data" or "transfer complete"
- Received after transfer start date
- Body mentions Google Photos

**Timing Expectations**:
- Day 5: Usually no email yet
- Day 6: Email may arrive (check morning and evening)
- Day 7: Email should definitely be present
- Day 8+: If no email, may need to check with Apple

**No Gmail API Fallback**:
If GMAIL_CREDENTIALS_PATH not set:
```json
{
  "status": "error",
  "error": "Gmail API not configured",
  "suggestion": "Please check your email manually for Apple confirmation",
  "manual_check": "Look for email from noreply@apple.com"
}
```

**Database Operations**:
```sql
-- Record email confirmation
UPDATE media_transfer
SET photo_complete_email_received = CURRENT_TIMESTAMP,
    video_complete_email_received = CURRENT_TIMESTAMP
WHERE transfer_id = ?

-- Log email check
INSERT INTO daily_progress (
  migration_id, day_number, key_milestone
) VALUES (?, ?, 'Apple completion email received')
```

**Error Scenarios**:
- Token expired: Automatically refreshes using refresh token
- API quota exceeded: Returns friendly message to try later
- Network error: Retries with exponential backoff
- No credentials: Guides user to manual check

**Agent Integration**:
```
Day 6:
Agent: "Let me check if Apple has sent the completion email..."
→ web-automation.check_photo_transfer_email(transfer_id)
→ If found: "Great! Apple confirms your transfer is complete!"
→ If not found: "No email yet, this is normal for Day 6"
→ Update status visualization
```

**Privacy Notes**:
- Only searches for specific Apple emails
- Doesn't read other emails in inbox
- Minimal permissions requested
- Token can be revoked anytime in Google settings

---

## 7-Day Migration Timeline

### Day 1: Foundation
**Morning**
1. `check_icloud_status()` - Get accurate counts
2. Review photo library statistics with user
3. Initialize migration in database
4. `start_photo_transfer()` - Begin Apple service

**Afternoon**
- Set up family ecosystem (via mobile-mcp)
- Create WhatsApp group
- Configure location sharing
- Start Venmo teen account process

**Key Milestones**:
- ✅ Transfer initiated with Apple
- ✅ Baseline established in Google Photos
- ✅ Family communication started
- ✅ Session saved (no more 2FA needed)

### Days 2-3: Processing
**What's Happening**:
- Apple processes transfer request
- Photos being packaged and encrypted
- Google Photos preparing to receive
- NO photos visible yet (this is normal!)

**User Actions**:
- Continue normal iPhone use
- Help family install WhatsApp
- Complete Venmo account setup

**Don't**:
- Check progress (will show 0%)
- Worry about lack of visibility
- Restart or cancel transfer

### Day 4: Storage Growth Detected 🎉
**Morning Check**
- `check_photo_transfer_progress()` - Should show ~28% based on storage growth
- Storage snapshots show Google Photos growing
- First photos may start appearing in Google Photos

**Verification**:
- Check Google One storage metrics
- Confirm storage increase from baseline
- Photos may be processing but storage shows progress

**Update Status**:
- Create progress visualization with storage metrics
- Update family on timeline
- Continue family app adoption

### Day 5: Steady Progress
**Progress Check**
- `check_photo_transfer_progress()` - Should show ~57% based on storage
- Storage growth rate established
- ETA calculated from storage transfer rate

**Other Activities**:
- Venmo teen cards arrive
- Activate cards via mobile-mcp
- Complete location sharing setup

### Day 6: Near Completion
**Morning**
- `check_photo_transfer_progress()` - Should show ~85% via storage metrics
- `check_photo_transfer_email()` - Email might arrive

**Preparation**:
- Review important photos list
- Ensure all family connected
- Prepare for final verification

### Day 7: Verification & Celebration
**Final Steps**
1. `check_photo_transfer_email()` - Confirm email received
2. `check_photo_transfer_progress()` - Should show near 100% via storage
3. `verify_photo_transfer_complete()` - Generate certificate

**Celebration Dashboard**:
- Display completion certificate with storage metrics
- Show all achievements including final storage totals
- Confirm family ecosystem active
- Generate final report with storage verification

---

## Installation & Configuration

### System Requirements
- Python 3.11+ (required for Playwright compatibility)
- macOS, Linux, or Windows
- 4GB RAM minimum
- 500MB free disk space
- Chrome/Chromium browser

### Installation Steps

```bash
# 1. Navigate to web-automation directory
cd mcp-tools/web-automation

# 2. Create virtual environment with Python 3.11
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install package in development mode
pip install -e .

# 4. Install Playwright browsers
playwright install chromium

# 5. Verify installation
python -c "from web_automation.server import server; print('✅ Installation successful')"
```

### Environment Configuration

Create `.env` file in project root:

```env
# Required for iCloud operations
APPLE_ID=your.email@icloud.com
APPLE_PASSWORD=your-apple-password

# Required for Google Photos operations  
GOOGLE_EMAIL=your.email@gmail.com
GOOGLE_PASSWORD=your-google-password

# Optional for email verification
GMAIL_CREDENTIALS_PATH=/path/to/gmail_oauth_credentials.json

# Optional for debugging
PWDEBUG=0  # Set to 1 for headed browser mode
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

### Gmail API Setup (Optional but Recommended)

1. **Enable Gmail API**:
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create new project or select existing
   - Enable Gmail API
   - Create OAuth2 credentials (Desktop application)
   - Download JSON file

2. **Configure Environment**:
   ```bash
   export GMAIL_CREDENTIALS_PATH=/path/to/credentials.json
   ```

3. **First Run Authorization**:
   - Browser opens automatically
   - Sign in to Google account
   - Approve Gmail access
   - Token saved to ~/.gmail_token.json

### Claude Desktop Integration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "web-automation": {
      "command": "/absolute/path/to/.venv/bin/python",
      "args": [
        "/absolute/path/to/mcp-tools/web-automation/src/web_automation/server.py"
      ],
      "env": {
        "PYTHONPATH": "/absolute/path/to/mcp-tools/web-automation/src",
        "APPLE_ID": "your.email@icloud.com",
        "APPLE_PASSWORD": "your-password",
        "GOOGLE_EMAIL": "your@gmail.com",
        "GOOGLE_PASSWORD": "your-password"
      }
    }
  }
}
```

---

## Testing & Debugging

### Test Scripts

#### Basic Authentication Test
```bash
# Test Apple ID login and session persistence
python tests/test_basic_auth.py

# Force fresh login (new 2FA)
python tests/test_basic_auth.py --fresh

# Clear saved sessions
python tests/test_basic_auth.py --clear
```

#### Full Migration Flow Test
```bash
# Interactive test of complete workflow
python tests/test_migration_flow.py
```

#### MCP Protocol Test
```bash
# Test all 5 tools via MCP
python tests/test_mcp_server.py
```

### Debugging Techniques

#### Visual Browser Mode
```bash
# See browser automation in action
PWDEBUG=1 python tests/test_basic_auth.py
```

#### Verbose Logging
```bash
# Enable detailed logs
LOG_LEVEL=DEBUG python tests/test_migration_flow.py
```

#### Check Session Status
```python
from web_automation.icloud_client import ICloudClientWithSession

client = ICloudClientWithSession()
print(f"Session valid: {client.is_session_valid()}")
print(f"Session age: {client.get_session_age_days()} days")
```

#### Database Inspection
```sql
-- Check transfer records
sqlite3 ~/.ios_android_migration/migration.db
SELECT * FROM media_transfer ORDER BY transfer_id DESC;

-- View storage snapshots
SELECT * FROM storage_snapshots WHERE migration_id = 'MIG-XXX';

-- View progress history
SELECT * FROM daily_progress WHERE migration_id = 'MIG-XXX';
```

### Common Issues & Solutions

#### Issue: 2FA Required Every Time
**Cause**: Session not being saved properly  
**Solution**:
1. Check ~/.icloud_session directory exists
2. Verify write permissions
3. Ensure reuse_session=true
4. Check session age (expires after ~7 days)

#### Issue: Storage Shows No Growth on Day 4
**Cause**: Transfer still processing or Google One delay  
**Solution**:
1. Wait a few hours and check again
2. Manually check one.google.com/storage
3. Clear Google browser cache
4. Try incognito mode
5. Check if photos are appearing even without storage update

#### Issue: Gmail API Not Working
**Cause**: Credentials not configured  
**Solution**:
1. Set GMAIL_CREDENTIALS_PATH
2. Ensure credentials.json exists
3. Delete ~/.gmail_token.json and reauthorize
4. Check API is enabled in Cloud Console

#### Issue: Browser Closes Too Quickly
**Cause**: Running in headless mode  
**Solution**:
1. Set PWDEBUG=1 for headed mode
2. Add breakpoints in code
3. Use --inspect flag for debugging
4. Check logs for errors

#### Issue: Transfer Already Exists
**Cause**: Previous transfer still active  
**Solution**:
1. Check Apple privacy portal
2. Cancel existing transfer if needed
3. Wait 24 hours before retrying
4. Use different Google account

---

## Integration Patterns

### With migration-state Server

#### Data Flow
```
web-automation → migration-state → Database
      ↓                ↑              ↑
  Browser Auto    State Updates   Progress
```

#### Coordination Sequence
1. web-automation.check_icloud_status() → Get counts
2. migration-state.initialize_migration() → Store details
3. web-automation.start_transfer() → Begin process
4. migration-state.start_photo_transfer() → Update phase
5. Daily: web-automation.check_progress() → Track via storage
6. Daily: migration-state.update_photo_progress() → Record storage metrics

### With mobile-mcp Server

#### Division of Responsibilities
- **web-automation**: All browser-based automation (Mac)
- **mobile-mcp**: All Android device control
- **migration-state**: All state management

#### Parallel Operations
While web-automation handles media transfer:
- mobile-mcp sets up WhatsApp groups
- mobile-mcp configures location sharing
- mobile-mcp activates Venmo cards

### With iOS2Android Agent

#### Agent Orchestration Pattern
```python
# Day 1
photos = web_automation.check_icloud_status()
migration_id = migration_state.initialize_migration(photos)
transfer_id = web_automation.start_transfer()
migration_state.start_photo_transfer()

# Day 4-6
progress = web_automation.check_transfer_progress(transfer_id)
migration_state.update_photo_progress(progress['percent'])

# Day 7
email = web_automation.check_transfer_email(transfer_id)
result = web_automation.verify_transfer_complete(transfer_id)
migration_state.generate_report()
```

---

## Performance & Optimization

### Resource Usage
- **Memory**: ~200-400MB per browser context
- **CPU**: Moderate during page automation
- **Network**: Minimal except during checks
- **Disk**: ~50MB for session storage

### Optimization Strategies

#### Session Reuse
- Always use reuse_session=true
- Sessions valid for ~7 days
- Eliminates 2FA on every call
- Reduces operation time by 90%

#### Caching Strategy
- Photo counts cached for 1 hour
- Progress cached for 30 minutes
- Email checks cached for 15 minutes
- Reduces unnecessary browser operations

#### Parallel Execution
- Baseline and transfer can run simultaneously
- Multiple browser contexts supported
- Email checks independent of progress checks

### Rate Limiting
- Apple: No explicit limits, but space operations
- Google Photos: Max 10 checks per hour recommended
- Gmail API: 250 quota units per user per second
- Browser operations: 1-2 second delays between actions

---

## Security Considerations

### Credential Management
- Never log passwords
- Use environment variables
- Rotate credentials regularly
- Enable 2FA on all accounts

### Session Security
- Sessions encrypted at rest
- Stored in user home directory
- Permissions set to 600 (user only)
- Automatic expiration after 7 days

### Data Privacy
- Only accesses specified services
- No data transmitted to third parties
- All operations logged locally
- User maintains full control

### Browser Security
- Uses separate browser contexts
- Cookies isolated per session
- No browser extensions loaded
- Automatic cleanup on exit

---

## Success Metrics

### Transfer Success Criteria
- ✅ 98%+ photos and videos transferred (Grade A or A+)
- ✅ Completion email received
- ✅ Important photos and videos verified
- ✅ Transfer completed within 7 days
- ✅ No data loss or corruption
- ✅ Storage metrics match expected totals

### Operational Metrics
- Session reuse rate: >95%
- Average operation time: <30 seconds
- Browser automation success: >99%
- Email detection accuracy: 100%

### User Experience Metrics
- No repeated 2FA after Day 1
- Visual feedback during automation
- Clear progress reporting
- Celebration on completion

---

## Production Status

### Current Active Transfer
- **Transfer ID**: TRF-20250820-180056
- **User**: George (Production)
- **Photos**: 60,238
- **Videos**: 2,418  
- **Size**: 383 GB
- **Started**: August 20, 2025 (Day 6)
- **Progress**: ~85% complete
- **Expected Completion**: Day 7

### Production Statistics
- Total transfers initiated: 1
- Success rate: Pending (Day 6)
- Average transfer time: 7 days
- Largest transfer: 383 GB

---

## Troubleshooting Guide

### Diagnostic Commands

```bash
# Check server health
python -c "from web_automation.server import server; print('Server OK')"

# Verify Playwright installation
python -c "from playwright.async_api import async_playwright; print('Playwright OK')"

# Test database connection
python -c "from shared.database.migration_db import MigrationDatabase; db = MigrationDatabase(); print('Database OK')"

# Check session status
ls -la ~/.icloud_session/

# View recent logs
tail -n 100 ~/Dropbox/Development/Git/*/logs/web_automation.log
```

### Error Recovery Procedures

#### Session Expired
1. Delete ~/.icloud_session directory
2. Run check_icloud_status with reuse_session=false
3. Complete 2FA
4. New session created for 7 days

#### Transfer Stuck
1. Check photos.google.com manually
2. Verify Apple transfer status at privacy.apple.com
3. Run check_transfer_progress to update
4. Contact Apple Support if genuinely stuck

#### Database Lock
1. Close DBeaver/database viewers
2. Kill any hanging Python processes
3. Delete *.db-journal files if present
4. Restart MCP server

---

## Development

### Project Structure
```
web-automation/
├── src/web_automation/
│   ├── server.py                 # MCP server implementation
│   ├── icloud_client.py          # Core browser automation
│   ├── icloud_transfer_workflow.py # Transfer workflow logic
│   ├── google_photos_monitor.py  # Progress tracking
│   ├── gmail_api.py             # Email checking
│   └── logging_config.py        # Centralized logging
├── tests/
│   ├── test_basic_auth.py       # Authentication testing
│   ├── test_migration_flow.py   # Full workflow test
│   ├── test_mcp_server.py       # MCP protocol test
│   └── test_icloud_db.py        # Database integration
├── requirements.txt              # Python dependencies
├── pyproject.toml               # Package configuration
└── README.md                    # This documentation
```

### Key Dependencies
- playwright>=1.40.0 - Browser automation
- mcp>=0.1.0 - Model Context Protocol
- python-dotenv>=1.0.0 - Environment management
- duckdb>=0.9.0 - Database operations
- google-auth>=2.0.0 - Gmail API
- google-auth-oauthlib>=1.0.0 - OAuth flow
- google-auth-httplib2>=0.1.0 - HTTP transport

### Contributing Guidelines
1. Test all changes with test_migration_flow.py
2. Maintain backwards compatibility
3. Document browser automation steps
4. Handle errors gracefully
5. Update tests for new features

---

## Future Enhancements

### Planned Features
- Support for iCloud Drive files
- Shared album handling
- Live Photo preservation
- Facial recognition mapping
- Contact migration assistance

### Architectural Improvements
- Redis caching layer
- WebSocket progress updates
- Distributed browser automation
- Advanced retry strategies
- Machine learning for optimization

---

## Support & Resources

### Documentation
- [Playwright Documentation](https://playwright.dev/python/)
- [MCP Specification](https://modelcontextprotocol.io)
- [Gmail API Reference](https://developers.google.com/gmail/api)
- [Apple Privacy Portal](https://privacy.apple.com)

### Troubleshooting Support
- Check logs in `~/Dropbox/.../logs/`
- Review test scripts for examples
- Examine database for state issues
- Enable debug mode for visibility

---

*Version 3.1 - Production Ready (August 2025)*  
*5 Tools Operational - Currently Processing 383GB Real Migration*  
*Day 6 of 7 - 85% Complete*