# Test Migration Flow - Complete Validation Guide

## 🧹 Pre-Test Cleanup (Start Fresh)

Run these commands to ensure a completely clean test environment:

```bash
cd mcp-tools/photo-migration

# 1. Clear ALL saved browser sessions (will prompt for confirmation)
python utils/clear_sessions.py
# Answer 'y' to delete each session

# 2. Clear Gmail OAuth token (if exists)
rm -f ~/.ios_android_migration/gmail_token.pickle

# 3. Optional: Clear the migration database for fresh transfer IDs
rm -f ~/.ios_android_migration/migration.db

# 4. Clear any old logs
rm -f logs/*.log

# 5. Clear any old screenshots
rm -f screenshots/*.png

# 6. Verify environment variables are set
cat .env
# Should show all 4 required variables:
# APPLE_ID=your.email@icloud.com
# APPLE_PASSWORD=your_password
# GOOGLE_EMAIL=your.email@gmail.com
# GOOGLE_PASSWORD=your_password
```

## 🚀 Running the Test

```bash
# Make sure you're in the tests directory
cd tests

# Activate virtual environment if not already active
source ../.venv/bin/activate

# Run the migration flow test
python test_migration_flow.py
```

## ✅ Step-by-Step Validation Checklist

### Phase 1: iCloud Status Check ✓

**What to Watch For:**
- [ ] Browser window opens to `privacy.apple.com`
- [ ] **If fresh session (first run after cleanup):**
  - [ ] Apple login page appears
  - [ ] Enter Apple ID and password
  - [ ] 2FA code prompt appears
  - [ ] Check Mac notification center or iPhone for code
  - [ ] Enter 2FA code within 60 seconds
- [ ] **If reusing session:**
  - [ ] Should see "Using saved session to avoid 2FA..."
  - [ ] Should see "✅ Already signed in with saved session! No 2FA needed."
- [ ] Navigate to "Request to transfer a copy of your data"
- [ ] Select "iCloud Photos and videos"
- [ ] Console shows photo counts:
  ```
  ✅ iCloud Status Retrieved:
     - Photos: 60,238
     - Videos: 2,418
     - Storage: 383 GB
     - Total items: 62,656
  ```

### Phase 2: API Initialization ✓

**Verify These Initialize:**
- [ ] Google Dashboard client initialized
- [ ] Gmail monitor initialized (if credentials configured)
- [ ] Database initialized at `~/.ios_android_migration/migration.db`
- [ ] Console shows: `✅ APIs initialized (Gmail, Database, Google Dashboard)`

### Phase 3: Database Check ✓

**What You Should See:**
- [ ] Either "No existing transfers found in database" (if fresh)
- [ ] Or list of previous transfers with IDs and timestamps

### Phase 4: Start Transfer (Interactive) ⚠️

**When prompted "Start a new transfer? (yes/no):"**

If you answer **yes**, watch for:

#### 4.1 Google Dashboard Baseline
- [ ] New browser window opens for Google Dashboard
- [ ] URL: `myaccount.google.com/dashboard`
- [ ] **If fresh Google session:**
  - [ ] Google login page appears
  - [ ] Enter Google email and password
  - [ ] May see "Tap Yes on your phone" for 2FA
  - [ ] Wait for phone notification and tap Yes
- [ ] Dashboard loads showing Google services
- [ ] Script extracts Google Photos count
- [ ] Console shows: `Baseline established: X photos`
- [ ] Screenshot saved to `screenshots/dashboard_*.png`

#### 4.2 Apple Transfer Workflow
- [ ] Returns to Apple browser window
- [ ] **Step 1:** Dropdown changes to "Google Photos"
- [ ] **Step 2:** "Photos" checkbox gets checked (NOT Videos!)
- [ ] **Step 3:** Continue button becomes enabled and clicked
- [ ] **Step 4:** "Copy your photos to Google Photos" page appears
- [ ] Another Continue button clicked

#### 4.3 Google OAuth Popup
- [ ] Popup window opens for Google OAuth
- [ ] Google account selection or login
- [ ] Click "Allow" to grant permissions
- [ ] Popup closes automatically (this is normal)
- [ ] Returns to main Apple window

#### 4.4 Confirmation Page
- [ ] See "Confirm your Transfer" heading
- [ ] Transfer details displayed
- [ ] Script STOPS here (doesn't click Confirm Transfer)
- [ ] Console shows:
  ```
  ✅ Transfer initiated successfully!
  Transfer ID: TRF-20250820-XXXXXX
  ```

### Phase 5: Check Progress (Interactive) 📊

**When prompted "Check transfer progress? (yes/no):"**

If you answer **yes**:
- [ ] Google Dashboard opens again (or reuses session)
- [ ] Current photo count retrieved
- [ ] Progress calculated and displayed:
  ```
  📊 Transfer Progress:
     - Status: in_progress
     - Progress: 0.0%
     - Transferred: 0 items
     - Current Google count: 42
     - Days elapsed: 0.0
  ```
- [ ] Database updated with progress record

### Phase 6: Email Check 📧

**Automatic check for completion email:**
- [ ] **If Gmail configured:**
  - [ ] First time: Browser may open for Gmail OAuth
  - [ ] Grant permissions if prompted
  - [ ] Searches for Apple completion emails
  - [ ] Shows either "No completion email found yet" or email details
- [ ] **If Gmail not configured:**
  - [ ] Shows "Gmail not configured" message

### Phase 7: Verify Completion (Interactive) ✓

**When prompted "Verify transfer completion? (yes/no):"**

If you answer **yes**:
- [ ] Checks current Google Photos count
- [ ] Calculates match rate
- [ ] Shows completion status:
  ```
  📊 Transfer Verification:
     - Status: incomplete (normal if just started)
     - Match Rate: 0.0%
     - Grade: F (normal if < 80% complete)
  ```

## 📁 Post-Test Validation

### 1. Check Session Files Created
```bash
ls -la ~/.icloud_session/
# Should see:
# - browser_state.json
# - session_info.json

ls -la ~/.google_session/
# Should see:
# - browser_state.json  
# - session_info.json
```

### 2. Check Database Records
```bash
cd ..  # Back to photo-migration directory
python -c "
from shared.database.migration_db import MigrationDatabase
db = MigrationDatabase()
with db.get_connection() as conn:
    # Check transfers table
    transfers = conn.execute('SELECT transfer_id, status, source_photos FROM photo_migration.transfers ORDER BY created_at DESC LIMIT 1').fetchone()
    if transfers:
        print(f'Latest transfer: {transfers[0]}, Status: {transfers[1]}, Photos: {transfers[2]}')
    
    # Check progress history
    progress = conn.execute('SELECT COUNT(*) FROM photo_migration.progress_history').fetchone()
    print(f'Progress records: {progress[0]}')
"
```

### 3. Check Screenshots
```bash
ls -la screenshots/
# Should see dashboard_YYYYMMDD_HHMMSS.png files
```

### 4. Check Logs for Errors
```bash
grep -i error logs/photo_migration_$(date +%Y%m%d).log || echo "No errors found"
```

## 🔴 Common Issues & Solutions

### Issue 1: "Element not found" errors
**Cause:** Apple/Google changed their UI
**Solution:** Take screenshot, note which step failed, report the exact error

### Issue 2: OAuth popup doesn't appear
**Cause:** Popup blocker or browser issue
**Solution:** Check browser console, ensure popups allowed for the sites

### Issue 3: 2FA timeout
**Cause:** Didn't enter code within 60 seconds
**Solution:** Run test again, have 2FA device ready

### Issue 4: "Database not available"
**Cause:** Shared module import failed
**Solution:** Check that shared/ directory exists at project root

### Issue 5: Google Dashboard shows 0 photos
**Cause:** Wrong account or no photos in Google Photos
**Solution:** Verify you're using correct Google account

## 🎯 Success Criteria

The test is successful if:
1. ✅ iCloud status retrieved with correct photo counts
2. ✅ Transfer initiated with generated transfer_id
3. ✅ Google baseline established
4. ✅ Transfer workflow reaches confirmation page
5. ✅ Progress can be checked (even if 0%)
6. ✅ Database records created
7. ✅ Sessions saved for reuse

## 💡 Tips for Testing

1. **Keep browsers visible** - Don't minimize windows during automation
2. **Have 2FA devices ready** - Both Apple and Google may require codes
3. **Watch for popups** - OAuth popup may appear on different monitor
4. **Be patient** - Let pages fully load before automation proceeds
5. **Run twice** - Second run should reuse sessions (no 2FA)

## 🔄 Testing Session Reuse

After successful first run, test session persistence:

```bash
# Don't clear sessions!
# Just run the test again
python test_migration_flow.py
```

You should see:
- No Apple login required
- No Google login required  
- "Using saved session" messages
- Much faster execution

## 📝 What to Report

If test fails, provide:
1. The exact step number where it failed
2. The error message from console
3. Screenshot of the browser at failure point
4. Contents of the latest log file
5. Whether it's first run or reusing session