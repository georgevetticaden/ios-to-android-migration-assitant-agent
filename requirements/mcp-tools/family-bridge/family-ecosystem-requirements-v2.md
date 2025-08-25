# Family Ecosystem Requirements V2

## Overview

This document defines simplified requirements for family app coordination aligned with the demo reality. The focus is on configuration and coordination of existing apps, not installation automation.

## Changes from V1

### What's Removed
- ❌ **NO app installation automation** - Apps are already installed or we send email instructions
- ❌ **NO Apple Cash detailed migration** - Simplified to Venmo teen accounts only
- ❌ **NO Find My complex replacement** - Simple Google Maps location sharing
- ❌ **NO Music/Calendar/Contacts migration** - Not shown in demo
- ❌ **NO Life360 or parental controls** - Out of scope for demo

### What's Simplified
- ✅ **Email-based coordination** - Send invites via email, not complex automation
- ✅ **Natural language commands** - Everything through English to mobile-mcp
- ✅ **Progressive adoption tracking** - Monitor who has what over multiple days
- ✅ **Focus on 3 apps only** - WhatsApp, Google Maps, Venmo

## WhatsApp Requirements

### Purpose
Replace iMessage for cross-platform family messaging

### Day 1: Initial Setup

**User provides**: Family member names and email addresses
```
"Jaisy is jaisy.vetticaden@gmail.com"
"Laila is laila.vetticaden@gmail.com" 
"Ethan is ethan.vetticaden@gmail.com"
"Maya is maya.vetticaden@gmail.com"
```

**Claude's orchestration**:
1. Store family details via `migration-state.add_family_member()`
2. Create WhatsApp group via mobile-mcp natural language
3. Attempt to add each family member
4. Identify who doesn't have WhatsApp
5. Send email invitations to those without

**Natural Language Commands to mobile-mcp**:
```
"Open WhatsApp"
"Tap the three dots menu in top right"
"Select New group"
"Search for Jaisy"     → Result: Not found
"Search for Laila"     → Result: Found
"Select Laila"
"Search for Ethan"     → Result: Not found
"Search for Maya"      → Result: Found
"Select Maya"
"Tap the green arrow"
"Type 'Vetticaden Family' as group name"
"Tap the green checkmark"
```

**Email Sending** (via mobile-mcp):
```
"Open Gmail"
"Tap compose button"
"Enter recipient: jaisy.vetticaden@gmail.com"
"Enter subject: Join our WhatsApp family group"
"Enter message: Hi Jaisy, I've created our family WhatsApp group. Please install WhatsApp from the App Store to join us. -George"
"Tap send"
```

**Database Updates**:
- `update_family_member_apps()` marks Laila and Maya as 'configured'
- `update_family_member_apps()` marks Jaisy and Ethan as 'invited'
- `app_setup` table shows WhatsApp with 2/4 members connected

### Day 3: Adoption Check

**Claude's orchestration**:
1. Check family adoption status via `get_daily_summary()`
2. Identify Jaisy and Ethan now have WhatsApp
3. Add them to the family group

**Natural Language Commands**:
```
"Open WhatsApp"
"Open Vetticaden Family group"
"Tap the group name at top"
"Tap Add participants"
"Search for Jaisy"     → Result: Now found!
"Select Jaisy"
"Search for Ethan"     → Result: Now found!
"Select Ethan"
"Tap the green checkmark"
```

**Database Updates**:
- `update_family_member_apps()` marks all 4 members as 'configured'
- `app_setup` shows WhatsApp 'completed' with 4/4 connected

### Success Criteria
- ✅ Family group created with correct name
- ✅ All family members eventually added
- ✅ Email invitations sent to those without app
- ✅ Progressive adoption tracked over days

---

## Google Maps Location Sharing

### Purpose
Replace Find My for cross-platform location sharing

### Day 1: Setup Location Sharing

**Claude's orchestration**:
Immediately after WhatsApp setup, configure location sharing

**Natural Language Commands**:
```
"Open Google Maps"
"Tap your profile picture in top right"
"Tap Location sharing"
"Tap New share"
"Select 'Until you turn this off'"
"Search for Jaisy"
"Select Jaisy"
"Tap Share"
```
*Repeat for Laila, Ethan, and Maya*

**What happens**:
- Invitations sent to all family members
- They receive notifications on their iPhones
- Can accept from Google Maps app on iOS

**Database Updates**:
- `update_family_member_apps()` marks all as 'invited' for Google Maps
- Family members accept at their own pace

### Day 3-7: Monitor Acceptance

**Tracking**:
- Check who has accepted location sharing
- Update database as family members accept
- No automation needed - just status tracking

**Natural Language Check** (optional):
```
"Open Google Maps"
"Tap your profile picture"
"Tap Location sharing"
"Take screenshot"  → Shows who's sharing back
```

### Success Criteria
- ✅ Location sharing invitations sent Day 1
- ✅ Family acceptance tracked over time
- ✅ Cross-platform sharing verified
- ✅ No complex automation required

---

## Venmo Teen Accounts

### Purpose
Replace Apple Cash for teen allowances and spending

### Day 1: Manual Account Creation

**User Action** (not automated):
User manually creates teen accounts for Laila (17) and Ethan (15)

**Claude's response**:
"I see you have two teens who need Venmo accounts. You'll need to set these up manually through Venmo's website. Once created, Venmo will send you debit cards in 3-5 days and provide invitation links for your teens."

**Database Updates**:
- `venmo_setup` records created for Laila and Ethan
- `needs_teen_account` set to true
- Status tracked but not automated

### Day 2-4: Waiting Period

**Status**: Waiting for cards to arrive
- No automation needed
- Claude can check status via `get_daily_summary()`

### Day 5: Card Activation

**User notification**: "The Venmo teen cards have arrived!"

**Claude's orchestration**:
1. Acknowledge cards arrived
2. Help activate each card via mobile-mcp

**Natural Language Commands** (for Laila's card):
```
"Open Venmo"
"Tap the Cards tab at bottom"
"Tap 'Activate your card'"
"Enter last 4 digits: 1234"
"Enter card expiration: 08/29"
"Enter CVV: 567"
"Tap Activate"
"Set PIN: 4321"
"Confirm PIN: 4321"
"Tap Done"
```

**Database Updates**:
- `activate_venmo_card()` for Laila
- `activate_venmo_card()` for Ethan
- Venmo marked as 'completed' when both activated

### Day 6-7: Verify Setup

**Verification Steps**:
- Check teen accounts are active
- Verify spending controls in place
- Confirm teens can use their cards

**Natural Language Commands**:
```
"Open Venmo"
"Tap the menu icon"
"Tap 'Teen account'"
"Take screenshot"  → Shows active teen accounts
```

### Success Criteria
- ✅ Teen accounts tracked (not automated)
- ✅ Card arrival on realistic timeline (Day 5)
- ✅ Card activation automated via mobile-mcp
- ✅ Teen spending controls verified

---

## Coordination Patterns

### Email-Based Invitations

All app invitations follow the same pattern:
1. Try to add family member to app/service
2. If not found, send email invitation
3. Track invitation sent in database
4. Check back in later days for adoption
5. Complete setup when they join

**Email Template**:
```
To: [family_member_email]
Subject: [App name] family setup
Message: Hi [name], I've set up [app] for our family. 
Please install it from the App Store to stay connected. -George
```

### Status Tracking Flow

```
not_started → invited → installed → configured
     ↓           ↓          ↓           ↓
  Day 1      Email sent  App ready   Fully setup
```

### Natural Language Principles

**Good Commands** (specific, natural):
- "Open WhatsApp"
- "Tap the green button at the bottom"
- "Search for Jaisy"
- "Type 'Vetticaden Family'"

**Bad Commands** (too technical):
- "Click element with id com.whatsapp:id/fab"
- "Execute tap at coordinates 540, 1920"
- "Find TextView containing 'New group'"

---

## Implementation Requirements

### MCP Tool Coordination

1. **migration-state** tools:
   - Store family member details with emails
   - Track app adoption status
   - Generate daily summaries

2. **mobile-mcp** commands:
   - All UI automation via natural language
   - Screenshot capability for verification
   - Email sending through Gmail app

3. **web-automation** tools:
   - No involvement in family ecosystem
   - Handles photo migration separately

### Database Requirements

Tables used (from database-design-v2.md):
- `family_members` - Names and emails
- `family_app_adoption` - Individual app status
- `app_setup` - Overall app configuration
- `venmo_setup` - Teen account tracking

### Error Handling

Common scenarios:
- **Family member not found**: Send email invitation
- **App not installed**: Detected when search fails
- **Network issues**: Retry with variations
- **UI changes**: Flexible natural language handles minor changes

---

## Testing Scenarios

### Day 1 Test
1. Add 4 family members with emails
2. Create WhatsApp group with 2 members
3. Send 2 email invitations
4. Set up location sharing for all
5. Note Venmo teen requirements

### Day 3 Test
1. Check adoption status
2. Add remaining WhatsApp members
3. Verify location sharing acceptance
4. Update database accordingly

### Day 5 Test
1. Acknowledge card arrival
2. Activate both teen cards
3. Verify Venmo setup complete
4. Update all statuses

### Day 7 Test
1. Verify all apps configured
2. All family members connected
3. Generate final report
4. Confirm zero dropoff

---

## Success Metrics

### WhatsApp
- ✅ 4/4 family members in group by Day 3
- ✅ Zero manual intervention after emails sent
- ✅ Group name exactly as specified

### Google Maps
- ✅ 4/4 sharing location by Day 7
- ✅ Works across iOS and Android
- ✅ Persistent sharing ("Until you turn off")

### Venmo
- ✅ 2/2 teen cards activated Day 5
- ✅ Spending controls verified
- ✅ Parents can monitor activity

### Overall
- ✅ No custom code written
- ✅ All automation via natural language
- ✅ Email coordination successful
- ✅ 7-day timeline maintained

---

## Excluded from V2 Scope

These items from V1 are NOT included:

1. **Apple Cash Migration**: No detailed transfer process
2. **Find My Device**: No device tracking setup
3. **Screen Time**: No parental control migration
4. **iCloud Shared Albums**: No photo sharing migration
5. **Apple Music**: No playlist transfer
6. **Calendar Sync**: No calendar migration
7. **Contact Sync**: No contact transfer
8. **App Purchase History**: No app migration

The V2 requirements focus ONLY on what's shown in the demo: WhatsApp messaging, Google Maps location sharing, and Venmo teen accounts for payments.