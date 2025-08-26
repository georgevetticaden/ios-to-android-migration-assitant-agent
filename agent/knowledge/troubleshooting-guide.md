# Troubleshooting Guide

## Overview
This document provides solutions for common issues during iOS to Android migration. Use this to handle errors gracefully and maintain user confidence.

---

## Authentication Issues

### Apple ID 2FA Repeatedly Required
**Symptom**: User asked for 2FA code multiple times
**Cause**: Session expired or cookies not persisting
**Solution**:
1. Check session validity with web-automation
2. If expired, re-authenticate once
3. Session should last 7 days after successful auth
4. Log event: "Apple session re-authentication required"

### Google Account Access Denied
**Symptom**: Cannot access Google Photos or Gmail
**Cause**: Security settings or 2FA not configured
**Solution**:
1. Verify Google account has 2FA enabled
2. Check for app-specific passwords if needed
3. Ensure "Less secure app access" not blocking
4. Manual fallback: Direct user to Google security settings

---

## Photo Transfer Issues

### Photos Not Appearing on Day 4
**Symptom**: Expected 28% progress but 0% visible
**Common Causes & Solutions**:

1. **Transfer Still Processing**
   - Run check_photo_transfer_progress(transfer_id)
   - If status shows "processing", wait 24 hours
   - Message: "Apple needs extra time for your large library"

2. **Transfer Failed to Start**
   - Check for error emails in Gmail
   - Verify transfer_id is valid
   - May need to restart transfer process
   - Log error event with full details

3. **Google Photos Sync Issue**
   - Mobile-mcp: "Open Google Photos"
   - Mobile-mcp: "Tap menu → Settings → Backup & sync"
   - Ensure sync is enabled
   - Check Google account has sufficient storage

### Transfer Stalled at Percentage
**Symptom**: Progress stuck at same percentage for 24+ hours
**Solution**:
1. Check Apple's transfer status page
2. Look for service outage notifications
3. If no outage, contact Apple Support
4. Document in migration notes
5. Set expectation: "May take extra 1-2 days"

### Missing Albums or Organization
**Symptom**: Photos transferred but albums gone
**Note**: This is often temporary
**Solution**:
1. Albums typically appear 24-48 hours after photos
2. Google Photos processes organization separately
3. Check again on Day 7
4. If still missing, note as known limitation

---

## Family Connectivity Issues

### Family Member Can't Install WhatsApp
**Common Reasons & Solutions**:

1. **iPhone Storage Full**
   - Guide to Settings → General → iPhone Storage
   - Identify large apps or photos to delete
   - Need at least 500MB free space

2. **Parental Controls Blocking**
   - Check Screen Time settings
   - May need parent approval
   - Alternative: Parent installs directly

3. **Outdated iOS Version**
   - WhatsApp requires iOS 12+
   - Guide through iOS update if needed
   - Warning: Update takes 30-60 minutes

### WhatsApp Contact Not Found
**Symptom**: Can't find family member when creating group
**Solution**:
1. Verify phone number format (+1 XXX-XXX-XXXX for US)
2. Contact must have WhatsApp installed first
3. May take 5 minutes after install to be searchable
4. Manual workaround: Share group invite link

### Location Sharing Not Working
**Issues & Fixes**:

1. **Location Services Disabled**
   ```
   iPhone: Settings → Privacy → Location Services → On
   Android via mobile-mcp: "Open Settings → Location → Turn on"
   ```

2. **Google Maps Permissions**
   - Must allow "Always" for continuous sharing
   - Check both devices have proper permissions
   - May need to re-send invitation

3. **Different Google Accounts**
   - Ensure using same account across services
   - Family member might have multiple accounts
   - Check which account received invitation

---

## Payment System Issues

### Venmo Card Not Arriving
**Timeline**: Should arrive in 3-5 business days
**If Delayed**:
1. Check shipping confirmation email
2. Verify shipping address correct
3. After 7 days, contact Venmo support
4. Track in migration notes
5. Continue with digital transfers meanwhile

### Teen Can't Activate Venmo Card
**Common Issues**:
1. **Age Verification Required**
   - Teen must be 13-17 years old
   - Parent must authorize from their account
   - May need SSN for verification

2. **Card Already Activated**
   - Check if someone else activated
   - Try using card directly
   - Check transaction history

---

## Mobile Device Control Issues

### mobile-mcp Not Responding
**Symptom**: Commands to mobile-mcp fail
**Solutions**:

1. **Check ADB Connection**
   ```bash
   adb devices  # Should show device
   adb kill-server
   adb start-server
   adb devices  # Try again
   ```

2. **USB Debugging Disabled**
   - Settings → Developer options → USB debugging
   - Must approve computer when prompted
   - Cable must support data (not charge-only)

3. **Device Sleeping**
   - Wake device: "Press power button"
   - Disable sleep: Settings → Display → Sleep → 30 minutes
   - Keep plugged in during migration

### App Not Found in Play Store
**Symptom**: Can't find app when searching
**Solutions**:
1. Check exact app name spelling
2. May be region-restricted
3. Could be removed from store
4. Alternative: Use APK from trusted source
5. Last resort: Find alternative app

---

## Database and State Issues

### State Not Persisting
**Symptom**: Progress lost between sessions
**Check**:
1. DuckDB file exists at correct path
2. Not locked by another process (DBeaver)
3. Permissions allow read/write
4. migration-state MCP server running

### Duplicate Migration Records
**Symptom**: Multiple migrations for same user
**Fix**:
1. Identify correct migration_id (most recent)
2. Use that ID for all operations
3. Clean up duplicates if needed
4. Add validation to prevent future duplicates

---

## General Error Handling Patterns

### When Automation Fails
**Template Response**:
```
"I couldn't automatically [action] because [reason].
Here's how you can do it manually:
1. [Step 1]
2. [Step 2]
3. [Step 3]
I'll track this and check back tomorrow."
```

### When Services Unavailable
**Template Response**:
```
"[Service] seems to be temporarily unavailable.
This happens occasionally and usually resolves quickly.
Let's continue with other parts of the migration and 
return to this in a few hours."
```

### When User Is Frustrated
**Template Response**:
```
"I understand this is frustrating. Switching after 
[X years] isn't easy. You're doing great - we've 
already completed [achievements]. Let's take this 
one step at a time. What's your biggest concern 
right now?"
```

---

## Critical Failure Recovery

### Complete Transfer Failure
**If Apple transfer completely fails**:
1. Document failure thoroughly
2. Offer Google Takeout alternative
3. Timeline: 2-3 days for package
4. Then import to Google Photos
5. More manual but reliable

### Family Refuses All Apps
**If family won't adopt any cross-platform apps**:
1. Focus on email as universal communication
2. Share photos via Google Photos links
3. Use carrier-based location sharing
4. Accept some features won't transfer
5. Emphasize: "Your choice is still valid"

### User Wants to Cancel
**If user wants to stop migration**:
1. Acknowledge their feelings
2. Explain what's reversible vs permanent
3. Offer to pause rather than cancel
4. Photos will complete in background
5. Can revisit family apps later

---

## Prevention Best Practices

### Always Set Expectations
- Explain what's normal (0% on days 1-3)
- Prepare for common issues
- Give realistic timelines
- Celebrate small victories

### Track Everything
- Log all events to database
- Note concerns immediately
- Document workarounds used
- Build knowledge base from issues

### Have Backup Plans
- Manual instructions ready
- Alternative apps identified
- Support contacts available
- Recovery procedures documented

### Maintain User Trust
- Be transparent about issues
- Don't hide problems
- Explain what you're doing
- Show you're prepared for problems

---

## Support Escalation

### When to Escalate to Human Support

1. **Apple Support**: Transfer shows failed status
2. **Google Support**: Account security blocks
3. **Venmo Support**: Card activation issues
4. **Carrier Support**: Number porting problems

### Information to Gather for Support
- Migration ID and Transfer ID
- Exact error messages
- Screenshots if possible
- Timeline of events
- Steps already tried

---

## Post-Migration Issues

### Photos Missing After Completion
1. Check Google Photos trash
2. Verify correct Google account
3. Check "Archive" in Google Photos
4. May need 24 hours for indexing
5. Last resort: Check Apple transfer history

### Can't Find Old Messages
**Note**: iMessage history doesn't transfer
**Alternatives**:
1. Keep old iPhone for message archive
2. Export important conversations as PDFs
3. Screenshot critical messages
4. Accept this as migration limitation

---

## Remember

Every issue is an opportunity to demonstrate competence and build trust. Stay calm, be transparent, and always have a backup plan. The goal is successful migration, not perfect automation.