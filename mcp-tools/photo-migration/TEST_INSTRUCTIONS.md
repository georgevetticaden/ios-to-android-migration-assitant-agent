# Standalone Testing Instructions - Phase 3

## Prerequisites

### 1. Environment Setup
Create a `.env` file in the `mcp-tools/photo-migration/` directory:

```bash
# Required credentials
APPLE_ID=your.email@icloud.com
APPLE_PASSWORD=your_apple_password
GOOGLE_EMAIL=your.email@gmail.com
GOOGLE_PASSWORD=your_google_password

# Optional - for Gmail monitoring
GMAIL_CREDENTIALS_PATH=/Users/aju/Dropbox/Development/oauth2-credentials/client_secret_758745150294-c5b7od52l1q8orcvvgdj5vj6grtoqerc.apps.googleusercontent.com-v2.json
```

### 2. Python Environment
```bash
cd mcp-tools/photo-migration

# Activate virtual environment
source .venv/bin/activate

# Verify Python version (should be 3.11+)
python --version

# Install dependencies if needed
uv pip install -e .
```

## 🧹 Step 1: Clear All Tokens and Sessions

```bash
# Clear ALL stored sessions and tokens
python clear_sessions.py
```

This will:
- ✅ Clear iCloud browser session (~/.icloud_session/)
- ✅ Clear Gmail OAuth token (~/.ios_android_migration/gmail_token.pickle)
- ✅ Clear any saved transfer IDs (.last_transfer_id)

You should see:
```
Clearing all sessions and tokens...
✅ Cleared iCloud session
✅ Cleared Gmail token
✅ Cleared last transfer ID
All sessions cleared! Next login will require fresh authentication.
```

## 🧪 Step 2: Run Standalone Test

```bash
python test_phase3_final.py
```

## 📋 Step 3: Test Sequence

Follow this exact sequence for a complete test:

### A. First Authentication (Required)
```
Select option: 1
```
- This establishes the browser session
- You'll need to complete 2FA if prompted
- Browser will show privacy.apple.com
- Wait for it to load your photo counts
- Should show: "✅ Authentication successful!"

### B. Start Transfer Test
```
Select option: 2
```
- This will automate the entire 8-step transfer flow
- Browser will navigate through:
  1. Transfer page selection
  2. Google Photos destination
  3. Multiple confirmation pages
  4. Google account login (if needed)
  5. Permission grants
  6. Final confirmation

**IMPORTANT**: When you see "Proceed with transfer? (y/n):", type `y` and press Enter

The automation will:
- Click through all pages automatically
- Fill in Google credentials if needed
- Handle permission prompts
- Stop at the final "Confirm Transfer" button

**DO NOT** click "Confirm Transfer" unless you want to actually start a real transfer!

### C. Check Progress
```
Select option: 3
```
- Uses the transfer ID from step B
- Scrapes Google Dashboard for photo counts
- Shows progress percentage and estimates

### D. Verify Completion
```
Select option: 4
```
- Compares source and destination counts
- Generates completion certificate
- Shows match rate and grade

### E. Gmail Setup (One-Time)
```
Select option: 5
```
- Opens browser for Gmail OAuth
- Authorizes access to read emails
- Saves token for 7-day reuse
- **This is required before checking emails**

### F. Check Completion Email
```
Select option: 6
```
- Searches Gmail for Apple completion emails
- Shows email details if found
- Works with the transfer ID

## 🔍 What to Expect

### Fresh Login Flow:
1. **iCloud Authentication**
   - Browser opens to privacy.apple.com
   - Auto-fills Apple ID and password
   - You complete 2FA manually
   - Session saved for 7 days

2. **Transfer Initiation**
   - Browser navigates to transfer page
   - Automates entire 8-step flow
   - Stops before final confirmation
   - Returns transfer ID and details

3. **Gmail OAuth**
   - Browser opens to Google OAuth
   - Auto-fills Google credentials
   - You approve permissions
   - Token saved for reuse

### Success Indicators:
- ✅ Photo counts loaded (60,238 photos, 2,418 videos)
- ✅ Transfer ID generated (format: TRF_20250120_XXXXXX)
- ✅ Progress shows percentage and estimates
- ✅ Gmail authorization completes

### Common Issues:

**Issue**: "Missing APPLE_ID or APPLE_PASSWORD"
**Fix**: Check your `.env` file has all required variables

**Issue**: Browser closes too quickly
**Fix**: The browser should stay open during transfer workflow

**Issue**: Gmail OAuth fails
**Fix**: Ensure GMAIL_CREDENTIALS_PATH points to valid OAuth client file

**Issue**: "No module named 'photo_migration'"
**Fix**: Run `uv pip install -e .` to install the package

## 📊 Validation

After testing, check:

1. **Session Files**:
```bash
ls -la ~/.icloud_session/
# Should see: browser_state.json, cookies.json
```

2. **Gmail Token**:
```bash
ls -la ~/.ios_android_migration/
# Should see: gmail_token.pickle (after Gmail setup)
```

3. **Transfer ID**:
```bash
cat .last_transfer_id
# Should see: TRF_20250120_XXXXXX
```

4. **Logs**:
```bash
ls -la mcp-tools/logs/
# Should see: photo_migration_YYYYMMDD.log
```

## 🚨 Important Notes

1. **DO NOT** click "Confirm Transfer" in the browser unless you want to start a REAL transfer
2. **Gmail Setup** is required only once - token persists for 7 days
3. **iCloud Session** persists for 7 days - no 2FA needed after first login
4. Use **option 8** (Clear Sessions) to force fresh authentication
5. The test is **non-destructive** - it doesn't actually transfer photos

## 🎯 Quick Test Command Sequence

For a rapid test after clearing tokens:
```bash
# Terminal 1
python clear_sessions.py
python test_phase3_final.py

# In the test menu
1 [Enter]  # Authenticate
y [Enter]  # Don't force fresh (or 'n' for reuse)
[Complete 2FA if prompted]
[Wait for success]

2 [Enter]  # Start Transfer  
y [Enter]  # Proceed
[Watch automation - DO NOT click final confirm]

3 [Enter]  # Check Progress
[See progress stats]

5 [Enter]  # Gmail Setup
y [Enter]  # Proceed
[Complete OAuth in browser]

6 [Enter]  # Check Email
[See email search results]

0 [Enter]  # Exit
```

## ✅ Test Complete!

If all steps work, Phase 3 is fully functional and ready for MCP integration!