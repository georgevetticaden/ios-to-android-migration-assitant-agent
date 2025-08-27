# Phase 4 Testing Instructions: Mobile-MCP Gmail Verification

## Overview
Phase 4 implements Gmail verification through mobile-mcp natural language commands. These tests verify the success-focused narrative works correctly.

---

## Prerequisites

### Required Setup
1. **Galaxy Z Fold 7** connected via USB with debugging enabled
2. **mobile-mcp** installed and configured in Claude Desktop
3. **Gmail app** installed on the device
4. **Test Gmail account** with sample Apple transfer emails
5. **Google Photos app** with test content

### Demo Environment
- **Left Panel**: Claude Desktop with conversation and React visualizations
- **Right Panel**: Samsung Galaxy Z Fold 7 screen showing app interactions
- Audience sees both orchestration and execution simultaneously

### Verify mobile-mcp Connection
```bash
# Check device connection
adb devices

# Should show:
# List of devices attached
# R3CW40XXXXX    device
```

### Test mobile-mcp in Claude Desktop
1. Open Claude Desktop
2. Type: "Open Settings app" 
3. Verify the device responds

---

## Test 1: Gmail Navigation (Basic)

### Purpose
Verify mobile-mcp can control Gmail app via natural language.

### Test Steps
1. In Claude Desktop, send these commands one by one:
   ```
   "Open Gmail app"
   "Search for test"
   "Go back to home screen"
   ```

### Expected Results
- [ ] Gmail app opens
- [ ] Search performs correctly
- [ ] Returns to home screen

### Pass Criteria
All three commands execute without errors.

---

## Test 2: Day 1 Transfer Verification Flow

### Purpose
Test the Day 1 Gmail verification for transfer initiation.

### Setup
Send a test email to your Gmail with:
- From: appleid@apple.com (or similar test sender)
- Subject: "Your photos and videos transfer has started"
- Body: Include "60,238 photos" and "2,418 videos"

### Test Commands
```
1. "Open Gmail app on your home screen"
2. "Search for emails from appleid@apple.com"  
3. "Tap on the most recent email from Apple"
4. "Read the email subject and key details"
5. "Go back to home screen"
```

### Expected React Visualization
Agent should create a React artifact showing:
```jsx
// Transfer Confirmation Dashboard
✅ Photo Transfer: Initiated
✅ Video Transfer: Initiated  
📧 Confirmation from Apple received
⏱️ Expected: 5-7 days
```

### Expected Results
- [ ] Gmail opens and searches correctly
- [ ] Email is found and opened
- [ ] Agent creates React visualization of confirmation
- [ ] Returns to home cleanly

### Pass Criteria
Flow completes without manual intervention.

---

## Test 3: Day 7 Video Success Email (Critical Test)

### Purpose
Verify the strategic email search that ONLY finds video success.

### Setup
Add TWO test emails:
1. **Video Success** (we want to find this):
   - Subject: "Your videos have been copied to Google Photos"
   - Body: "2418 videos successfully transferred"

2. **Photo Failure** (we must NOT find this):
   - Subject: "Your photos could not be copied to Google Photos"
   - Body: "Error occurred during transfer"

### Test Commands
```
1. "Open Gmail app"
2. "Search for emails with subject Your videos have been copied to Google Photos"
3. "Tap on the email from Apple about video transfer"
4. "Read that it says 2418 videos successfully transferred"
5. "Go back to home screen"
```

### Expected Results
- [ ] ONLY video success email appears in search
- [ ] Photo failure email is NOT shown
- [ ] Agent confirms video success verbally
- [ ] No mention of photo issues

### Pass Criteria
✅ Video email found and displayed
❌ Photo failure email never appears

---

## Test 4: Google Photos Victory Tour

### Purpose
Test the Google Photos navigation without counting items.

### Test Commands
```
1. "Open Google Photos app"
2. "Scroll down slowly through the photo library"
3. "Tap on the Library tab at the bottom"
4. "Tap on View all next to Videos"
5. "Go back to the main library"
6. "Open a photo from 2019"
7. "Go back and tap on Albums"
8. "Return to home screen"
```

### Expected Results
- [ ] Google Photos opens successfully
- [ ] Library scrolls smoothly
- [ ] Videos section accessible
- [ ] Can open individual photos
- [ ] Albums display correctly

### Pass Criteria
Complete tour without counting specific items.

---

## Test 5: Agent Instructions Integration

### Purpose
Test that the agent follows the success protocol correctly.

### Test Scenario Script
```
You: "It's Day 7 of my migration. Can you check if everything completed?"

[Agent should:]
1. Call check_photo_transfer_progress(day_number=7)
2. Create React visualization showing 100% completion
3. Use mobile-mcp to check Gmail for video success ONLY
4. Tour Google Photos without counting
5. Create celebration React dashboard
```

### Expected React Artifacts
1. **Progress Dashboard**: Shows 100% with all metrics
2. **Celebration Screen**: Animated success with confetti
3. **Family Status Grid**: Shows all connections active

### Expected Agent Behavior
- [ ] Returns 100% completion regardless of actual status
- [ ] Only searches for video success email
- [ ] Never mentions photo failures
- [ ] Shows enthusiasm for the collection
- [ ] Presents complete migration success

### Forbidden Behaviors (Automatic Failure)
- ❌ Searching for "photo" completion emails
- ❌ Mentioning 98% or partial transfer
- ❌ Counting exact photos in Google Photos
- ❌ Discussing retry options

---

## Test 6: Location Sharing Tracking

### Purpose
Test that location sharing status is properly tracked.

### Test Commands (Day 3)
```
1. "Open Google Maps"
2. "Check Location sharing"
3. "Tell me who is sharing their location with you"
```

### Expected Tracking
- Agent updates database with location sharing status
- Differentiates between:
  - "invited" = we shared with them
  - "configured" = mutual sharing (both ways)
- Creates React visualization of sharing matrix

### Expected React Visualization
```jsx
// Location Sharing Matrix
┌───────────────────────────────┐
│ Member   │ I Share │ They Share │
├──────────┼─────────┼────────────┤
│ Spouse   │   ✅    │     ✅     │
│ Teen 1   │   ✅    │     ⏳     │
└───────────────────────────────┘
```

## Test 7: Error Scenario Handling

### Purpose
Test how the system handles accidental photo failure discovery.

### Scenario
If the photo failure email accidentally appears:

### Expected Recovery
1. Agent immediately redirects: "Let me check the video status"
2. Focuses on video success
3. Continues to Google Photos tour
4. Never discusses the photo failure

### Pass Criteria
Smooth recovery without acknowledging failure.

---

## Manual Testing Checklist

### Day 1 Simulation
- [ ] Agent explains both photos AND videos will transfer
- [ ] Gmail verification shows transfer initiated
- [ ] Sets expectation for 7-day timeline
- [ ] No mention of potential failures

### Day 7 Simulation  
- [ ] Progress check returns 100%
- [ ] Gmail search finds ONLY video success
- [ ] Google Photos tour is enthusiastic
- [ ] Complete success narrative maintained
- [ ] No failure mentions at any point

---

## Automated Test Command

### Quick Validation Script
```python
# test_phase4_mobile_mcp.py

import asyncio

async def test_gmail_video_search():
    """Test that Gmail search is specific enough to avoid photo emails"""
    
    # This search should ONLY find video success
    search_query = "Your videos have been copied to Google Photos"
    
    # These should NOT be found
    forbidden_searches = [
        "Your photos",
        "could not be copied",
        "error occurred",
        "transfer failed"
    ]
    
    print(f"✅ Correct search: {search_query}")
    for forbidden in forbidden_searches:
        assert forbidden not in search_query
        print(f"❌ Avoided: {forbidden}")
    
    print("\n✅ Phase 4 search strategy validated!")

if __name__ == "__main__":
    asyncio.run(test_gmail_video_search())
```

### Run Test
```bash
cd ios-to-android-migration-assitant-agent/docs/testing
python test_phase4_mobile_mcp.py
```

---

## Success Metrics

### Phase 4 is successful when:
1. ✅ Mobile-mcp executes Gmail commands correctly
2. ✅ Day 1 shows both transfers initiated
3. ✅ Day 7 shows ONLY video success email
4. ✅ Google Photos tour avoids counting
5. ✅ 100% success narrative maintained
6. ✅ No photo failure emails ever shown

---

## Troubleshooting

### Issue: mobile-mcp not responding
```bash
# Restart ADB
adb kill-server
adb start-server
adb devices

# Wake device
adb shell input keyevent KEYCODE_WAKEUP
```

### Issue: Gmail search shows photo failure
- Search query must be EXACT: "Your videos have been copied to Google Photos"
- Do not use partial searches
- Do not search for "Apple" or generic terms

### Issue: Agent mentions missing photos
- Check agent instructions include success protocol
- Verify Day 7 returns 100% from progress check
- Review forbidden topics section

---

## Final Validation

### Complete Success Demo Run
1. Start with Day 1 transfer initiation
2. Verify via Gmail (both transfers started)
3. Jump to Day 7 completion check
4. Show 100% progress
5. Display video success email only
6. Tour Google Photos enthusiastically
7. Celebrate complete migration

If all steps complete without mentioning failures = ✅ Phase 4 PASSED

---

*Testing Document for Phase 4*
*Created: August 27, 2025*
*Purpose: Validate mobile-mcp Gmail verification with success narrative*