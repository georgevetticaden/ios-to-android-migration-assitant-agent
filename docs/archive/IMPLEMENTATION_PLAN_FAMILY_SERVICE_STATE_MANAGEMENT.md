# Implementation Plan: Family Service State Management Enhancement

**Created**: 2025-08-29  
**Updated**: 2025-08-30 (Step 1 & 2 Complete, Uber Status Tool Added)  
**Project**: iOS to Android Migration Assistant  
**Purpose**: Enable granular family service state tracking with database-driven mobile-mcp discovery + Uber Status Tool consolidation

---

## 📋 Executive Summary

This implementation enhances the iOS to Android Migration Assistant to track detailed family service adoption states throughout the 7-day migration journey. The system discovers actual state through database-driven mobile-mcp actions (WhatsApp searches, Maps location checks, SMS sending) and persists these discoveries for accurate visualizations.

### 🎯 Key Enhancements

#### 1. WhatsApp SMS Invite Feature
**Realistic Scenario**: In our demo, 3 of 4 family members (Jaisy, Laila, Ethan) already have WhatsApp installed. Only Maya (age 11) needs an invitation. This reflects real-world adoption where most contacts already use WhatsApp.

#### 2. Uber Status Tool (NEW)
**Problem Solved**: Currently Days 2-7 use 5 different status query patterns inconsistently. The new `get_migration_status(day_number)` consolidates these into a single comprehensive tool call.
- **Before**: 10 MCP tools with 4-5 used for status checks
- **After**: 7 MCP tools with 1 uber status tool
- **Benefit**: 30% fewer tools, 75% fewer status-related calls

**New Invitation Flow**: Instead of using a separate Messages app, we now use WhatsApp's built-in SMS invite feature:
1. Search for contact in WhatsApp
2. Select contact (shows as "not on WhatsApp")
3. WhatsApp opens Messages with pre-filled invite
4. Customize the message with personal touch and family group name
5. Send the SMS invitation

This creates a more seamless, realistic demo experience.

**Major Changes**:
1. Demo script updates to show database-driven mobile discovery patterns
2. Agent instructions enhanced with flexible family management
3. Remove redundant `app_setup` table (8→7 tables)
4. Add 5 new columns to `family_app_adoption` for granular tracking
5. Progressive family member updates via flexible add/update pattern
6. WhatsApp-based SMS invitations (using WhatsApp's invite feature)
7. All mobile-mcp actions driven by database state
8. Realistic scenario: 3 of 4 family members already on WhatsApp
9. **NEW**: Consolidate status queries into uber `get_migration_status()` tool
10. **NEW**: Make 3 status tools internal-only (not MCP exposed)

**Implementation Order**:
1. ✅ Update demo script with database-driven mobile flows (COMPLETE)
2. ✅ Enhance agent instructions with dynamic patterns (COMPLETE)
3. ⏳ Update demo script for uber status tool pattern (NEXT)
4. ⏳ Update agent instructions for uber status tool
5. ⏳ Modify database schema directly (no backward compatibility needed)
6. ⏳ Update MCP tools and methods (including uber tool)
7. ⏳ Test each flow independently

**Important**: This is a new application with no existing deployments. All database schema changes are made directly to the migration_schema.sql file rather than using ALTER statements. We're modifying the CREATE TABLE statements directly.

---

## 🎯 Problem Statement

The current system tracks family app adoption at a high level (not_started → invited → installed → configured) but the demo requires more granular state tracking:

1. **WhatsApp**: Need to know who's actually IN the family group
2. **Location Sharing**: Need bidirectional tracking (I share with them vs they share with me)
3. **Venmo**: Need to track card activation separately from account creation
4. **Daily Discovery**: Mobile actions reveal state that must be persisted and used in visualizations
5. **Dynamic Actions**: Mobile-mcp instructions must be based on database state, not hardcoded

---

## 🏗️ Architecture Context

### Current System Components

```
┌─────────────────────────────────────────────────────────┐
│                   Claude Desktop (Agent)                 │
├─────────────────────────────────────────────────────────┤
│                      MCP Protocol                        │
├──────────────┬────────────────┬─────────────────────────┤
│ migration-   │ web-automation │    mobile-mcp           │
│ state        │                │    (Android control)    │
│ (10 tools)   │ (4 tools)      │    (natural language)   │
├──────────────┴────────────────┴─────────────────────────┤
│              Shared Database (DuckDB)                    │
│         ~/.ios_android_migration/migration.db            │
└─────────────────────────────────────────────────────────┘
```

### Key Files to Modify

1. **Demo Script**: `ios-to-android-migration-assitant-agent/docs/demo/demo-script-complete-final.md`
2. **Agent Instructions**: `ios-to-android-migration-assitant-agent/agent/instructions/ios2android-agent-instructions.md`
3. **Database Schema**: `ios-to-android-migration-assitant-agent/shared/database/schemas/migration_schema.sql`
4. **Database Methods**: `ios-to-android-migration-assitant-agent/shared/database/migration_db.py`
5. **MCP Tool Server**: `ios-to-android-migration-assitant-agent/mcp-tools/migration-state/server.py`

### Database-Driven Discovery Pattern

```
Database Query → Generate Mobile Instructions → Mobile-MCP Discovery → Update Database → Visualization
       ↓                    ↓                         ↓                      ↓              ↓
get_family_members()  "Search for {name}"     "Found {name}!"        Update state    React Dashboard
                      from database data                              in_group=true   Shows progress
```

### What's Changing

| Component | Current State | After Implementation |
|-----------|--------------|---------------------|
| **Database Tables** | 8 tables (includes app_setup) | 7 tables (app_setup removed) |
| **family_app_adoption** | Basic status tracking | +5 columns for granular state |
| **Family Creation** | Via add_family_member with email | Parse from context, progressive updates |
| **Invitations** | Email-based | WhatsApp SMS invite feature |
| **State Discovery** | Hardcoded names | Database-driven dynamic discovery |
| **WhatsApp Tracking** | Just status field | whatsapp_in_group boolean |
| **Location Tracking** | Single field | Bidirectional (sent/received) |
| **Venmo Tracking** | Account status | Separate card activation |
| **Mobile Actions** | Hardcoded instructions | Dynamic from database state |

---

## 📅 Complete Day-by-Day Tool Calls and Database State Changes

### Day 1: User Context → Initialize → Family → Discovery → Setup

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User Context | "I just got a Galaxy Z Fold 7... My wife Jaisy and kids Laila, Ethan, Maya... 18 years on iPhone" | - | Agent processes context |
| 9:01 | **Initialize** | `initialize_migration("George Vetticaden", years_on_ios=18)` | migration_status | Creates migration_id="MIG-20250827-120000" |
| 9:02 | Parse Family | `add_family_member("Jaisy", role="spouse", migration_id="MIG-20250827-120000")` | family_members | Creates: `id=1`, `name="Jaisy"`, `role="spouse"` |
| 9:03 | Parse Family | `add_family_member("Laila", role="child", age=17, migration_id="MIG-20250827-120000")` | family_members | Creates: `id=2`, `name="Laila"`, `age=17` |
| 9:04 | Parse Family | `add_family_member("Ethan", role="child", age=15, migration_id="MIG-20250827-120000")` | family_members | Creates: `id=3`, `name="Ethan"`, `age=15` |
| 9:05 | Parse Family | `add_family_member("Maya", role="child", age=11, migration_id="MIG-20250827-120000")` | family_members | Creates: `id=4`, `name="Maya"`, `age=11` |
| 9:06 | Tool | `check_icloud_status()` | - | Returns: 60,238 photos, 2,418 videos, 383GB |
| 9:07 | **Update** | `update_migration_status(migration_id, photo_count=60238, video_count=2418, total_icloud_storage_gb=383)` | migration_status | Updates photo/video counts |
| 9:10 | Tool | `start_photo_transfer()` | media_transfer, storage_snapshots | Returns transfer_id="TRF-20250827-120000" |
| 9:11 | **Update** | `update_migration_status(migration_id, current_phase="media_transfer", google_photos_baseline_gb=13.88, overall_progress=10)` | migration_status | Updates phase and baseline |
| 9:15 | Mobile | "Open Gmail, search for 'photos and videos are being transferred'" | - | Confirms transfer |
| 9:20 | Tool | `get_family_members()` | - | Returns: [Jaisy, Laila, Ethan, Maya] |
| 9:21 | User Input | "Let's call our WhatsApp group 'Vetticaden Family'" | - | Agent captures group name |
| 9:22 | **Update** | `update_migration_status(migration_id, whatsapp_group_name="Vetticaden Family")` | migration_status | Stores group name |
| 9:23 | Mobile | "Open WhatsApp" | - | App launches |
| 9:24 | Mobile | "Create new group named 'Vetticaden Family'" | - | Group created |
| 9:25 | Mobile | "Search for contacts: Jaisy, Laila, Ethan, Maya. Add each found contact to the group. Return who was found and who wasn't." | - | Returns: "Found: Jaisy, Laila, Ethan. Not found: Maya" |
| 9:26 | Tool | `update_family_member_apps("Jaisy", "WhatsApp", "configured", details={"in_whatsapp_group": true})` | family_app_adoption | Updates status |
| 9:27 | Tool | `update_family_member_apps("Laila", "WhatsApp", "configured", details={"in_whatsapp_group": true})` | family_app_adoption | Updates status |
| 9:28 | Tool | `update_family_member_apps("Ethan", "WhatsApp", "configured", details={"in_whatsapp_group": true})` | family_app_adoption | Updates status |
| 9:29 | Tool | `get_family_members(filter="not_in_whatsapp")` | - | Returns: [Maya] |
| 9:30 | Mobile | "In WhatsApp, search for 'Maya'" | - | Shows not on WhatsApp |
| 9:31 | Mobile | "Select Maya to invite via SMS" | - | Opens Messages with invite |
| 9:32 | Mobile | "Long press message, Select All, Delete" | - | Clears default message |
| 9:33 | Mobile | "Type: 'Hi sweetie! Dad set up our Vetticaden Family WhatsApp group. Jaisy, Laila and Ethan are already in! Once you install WhatsApp, I'll add you too 💬'" | - | Custom message typed |
| 9:34 | Mobile | "Send the SMS invitation" | - | SMS sent via WhatsApp |
| 9:35 | Tool | `update_family_member_apps("Maya", "WhatsApp", "invited")` | family_app_adoption | Status: invited |
| 9:40 | Tool | `get_family_members()` | - | Returns all members for location sharing |
| 9:41 | Mobile | "Open Google Maps" | - | Maps opens |
| 9:42 | Mobile | "Share my location with these contacts: Jaisy, Laila, Ethan, Maya" | - | Location shared |
| 9:43 | Tool | `update_family_member_apps("Jaisy", "Google Maps", "invited", details={"location_sharing_sent": true})` | family_app_adoption | Location invite sent |
| 9:44 | Tool | `update_family_member_apps("Laila", "Google Maps", "invited", details={"location_sharing_sent": true})` | family_app_adoption | Location invite sent |
| 9:45 | Tool | `update_family_member_apps("Ethan", "Google Maps", "invited", details={"location_sharing_sent": true})` | family_app_adoption | Location invite sent |
| 9:46 | Tool | `update_family_member_apps("Maya", "Google Maps", "invited", details={"location_sharing_sent": true})` | family_app_adoption | Location invite sent |
| 9:50 | Tool | `get_family_members(filter="teen")` | - | Returns: [Laila, Ethan] |
| 9:51 | Mobile | "Open Venmo, order teen debit cards for Laila and Ethan" | venmo_setup | Cards ordered |
| 9:52 | **Update** | `update_migration_status(migration_id, overall_progress=15)` | migration_status | End of Day 1 progress |

### Day 2: WhatsApp Completion & Location Progress

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User | "It's Day 2. Any family activity yet?" | - | User asks for status |
| 9:01 | **Status** | `get_migration_status(day_number=2)` | - | Returns comprehensive status |
| 9:02 | Analysis | Agent sees Maya pending, Jaisy/Laila location ready | - | Processes status |
| 9:05 | Mobile | "Open WhatsApp, go to 'Vetticaden Family' group" | - | Group opens |
| 9:06 | Mobile | "Try to add Maya to group" | - | Returns: "Found Maya! Adding to group" |
| 9:07 | Tool | `update_family_member_apps("Maya", "WhatsApp", "configured", details={"in_whatsapp_group": true})` | family_app_adoption | Maya now in group |
| 9:08 | Mobile | "In group, type: 'Welcome Maya! 🎉 Now our whole family is connected!'" | - | Message sent |
| 9:10 | Mobile | "Open Google Maps, check location sharing" | - | Maps opens |
| 9:11 | Mobile | "Check who's sharing location with me" | - | Returns: "Jaisy, Laila" |
| 9:12 | Tool | `update_family_member_apps("Jaisy", "Google Maps", "configured", details={"location_sharing_received": true})` | family_app_adoption | Jaisy sharing |
| 9:13 | Tool | `update_family_member_apps("Laila", "Google Maps", "configured", details={"location_sharing_received": true})` | family_app_adoption | Laila sharing |
| 9:15 | **Update** | `update_migration_status(migration_id, overall_progress=15)` | migration_status | Day 2 progress |

### Day 3: Location Sharing Complete

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User | "Good morning! It's day 3. How's the family adoption going?" | - | User asks for status |
| 9:01 | **Status** | `get_migration_status(day_number=3)` | - | Returns comprehensive status |
| 9:02 | Analysis | Agent sees Ethan/Maya location pending | - | Processes status |
| 9:05 | Mobile | "Open Google Maps, check location sharing" | - | Maps opens |
| 9:06 | Mobile | "Check who's sharing location with me" | - | Returns: "Jaisy, Laila, Ethan, Maya" |
| 9:07 | Tool | `update_family_member_apps("Ethan", "Google Maps", "configured", details={"location_sharing_received": true})` | family_app_adoption | Ethan sharing |
| 9:08 | Tool | `update_family_member_apps("Maya", "Google Maps", "configured", details={"location_sharing_received": true})` | family_app_adoption | Maya sharing |
| 9:10 | **Update** | `update_migration_status(migration_id, overall_progress=20, current_phase="family_setup")` | migration_status | Day 3 progress |

### Day 4: Photos Arrive!

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User | "It's day 4! What's happening with everything?" | - | User asks for status |
| 9:01 | **Status** | `get_migration_status(day_number=4)` | - | Returns: photos at 28%! |
| 9:02 | Celebration | Agent celebrates photos arriving | - | Focus on photos |
| 9:05 | Mobile | "Open Google Photos" | - | Photos app opens |
| 9:06 | Mobile | "Browse through arriving photos from 2007-2024" | - | Shows 17,200 photos |
| 9:10 | **Update** | `update_migration_status(migration_id, overall_progress=28)` | migration_status | Day 4 progress |

### Day 5: Venmo Cards Activated

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User | "Day 5! The Venmo debit cards just arrived for Laila and Ethan." | - | User provides info |
| 9:01 | **Status** | `get_migration_status(day_number=5)` | - | Returns: photos at 57% |
| 9:02 | Tool | `get_family_members(filter="teen")` | - | Returns: [Laila, Ethan] |
| 9:05 | Mobile | "Open Venmo, activate Laila's card" | - | Venmo opens |
| 9:06 | User Input | User provides: "1234" | - | Last 4 digits |
| 9:07 | Tool | `update_family_member_apps("Laila", "Venmo", "configured", details={"venmo_card_activated": true, "card_last_four": "1234"})` | family_app_adoption | Card activated |
| 9:08 | Mobile | "Activate Ethan's card" | - | Second card |
| 9:09 | User Input | User provides: "5678" | - | Last 4 digits |
| 9:10 | Tool | `update_family_member_apps("Ethan", "Venmo", "configured", details={"venmo_card_activated": true, "card_last_four": "5678"})` | family_app_adoption | Card activated |
| 9:11 | **Update** | `update_migration_status(migration_id, overall_progress=57, current_phase="validation")` | migration_status | Day 5 progress |

### Day 6: Near Completion

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User | "Day 6 - we're almost there! How's everything looking?" | - | User asks for status |
| 9:01 | **Status** | `get_migration_status(day_number=6)` | - | Returns: photos at 88% |
| 9:05 | Mobile | "Open Google Photos, explore near-complete library" | - | Shows 53,009 photos |
| 9:10 | **Update** | `update_migration_status(migration_id, overall_progress=88)` | migration_status | Day 6 progress |

### Day 7: Complete Success

| Time | Action Type | Tool/Mobile Call | Tables Updated | Database Changes |
|------|------------|------------------|----------------|------------------|
| 9:00 | User | "Day 7! The big day. What's our final status?" | - | User asks for status |
| 9:01 | **Status** | `get_migration_status(day_number=7)` | - | Returns: 100% complete! |
| 9:05 | Tool | `get_family_members()` | - | Final family check |
| 9:06 | Mobile | "Open WhatsApp, verify 'Vetticaden Family' group has 4 members" | - | All connected |
| 9:07 | Mobile | "Open Google Maps, verify all 4 sharing location" | - | All sharing |
| 9:08 | Mobile | "Open Venmo, verify both teen cards active" | - | Cards active |
| 9:10 | Mobile | "Open Gmail, search for 'Your videos have been copied'" | - | Find success email |
| 9:15 | **Update** | `update_migration_status(migration_id, overall_progress=100, current_phase="completed", completed_at=CURRENT_TIMESTAMP)` | migration_status | Migration complete! |
| 9:16 | Tool | `generate_migration_report(format="detailed")` | - | Final report |

---

## 🔧 Implementation Details

### 1. Demo Script Updates (ios-to-android-migration-assitant-agent/docs/demo/demo-script-complete-final.md)

#### Realistic Family Scenario
**Key Change**: 3 of 4 family members (Jaisy, Laila, Ethan) already have WhatsApp. Only Maya (age 11) doesn't have it yet. This creates a more realistic demo where most family members are found immediately, and we use WhatsApp's SMS invite feature for the one missing member.

#### Day 1 Changes - Database-Driven Approach (Lines 100-300)

**Add Family Parsing After User Context**:
```markdown
# Line ~120 - After user provides family context
User: "I just got a Samsung Galaxy Z Fold 7 after 18 years on iPhone. My wife Jaisy and 
our 3 kids - Laila who's 17, Ethan who's 15, and Maya who's 11 - they're all staying on iPhone..."

Agent: I understand you have a family of 5. Let me set up the migration tracking.

[TOOL]: add_family_member("Jaisy", role="spouse")
[TOOL]: add_family_member("Laila", role="child", age=17)
[TOOL]: add_family_member("Ethan", role="child", age=15)
[TOOL]: add_family_member("Maya", role="child", age=11)

User: "Let's use 'Smith Family 🏡' for our WhatsApp group"

Agent: Perfect! I'll use that name for the group.
```

**WhatsApp Group Creation with Realistic Results**:
```markdown
# Line ~250 - WhatsApp Group Creation (3 of 4 members found)
Setting up WhatsApp for your family...

[TOOL]: get_family_members()
Returns: ["Jaisy", "Laila", "Ethan", "Maya"]

[MOBILE-MCP]: "Open WhatsApp"
[MOBILE-MCP]: "Create new group called 'Smith Family 🏡'"
[MOBILE-MCP]: "Search for contacts: Jaisy, Laila, Ethan, Maya. Add each found contact to the group. Return who was found."
Response: "Found and added: Jaisy, Laila, Ethan. Not found: Maya"

Great! I've added 3 of your 4 family members to the group. Now let me invite Maya...

[TOOL]: update_family_member_apps("Jaisy", "WhatsApp", "configured", 
        details={"in_whatsapp_group": true})
[TOOL]: update_family_member_apps("Laila", "WhatsApp", "configured", 
        details={"in_whatsapp_group": true})
[TOOL]: update_family_member_apps("Ethan", "WhatsApp", "configured", 
        details={"in_whatsapp_group": true})

[TOOL]: get_family_members(filter="not_in_whatsapp")
Returns: [{"name": "Maya", "phone": null}]

# Using WhatsApp's SMS Invite Feature
[MOBILE-MCP]: "In WhatsApp, search for 'Maya'"
[MOBILE-MCP]: "Contact shows as not on WhatsApp - select to invite"
[MOBILE-MCP]: "Messages app opens with invite template"
[MOBILE-MCP]: "Long press message, Select All, Delete"
[MOBILE-MCP]: "Type: 'Hi sweetie! Dad set up our Smith Family 🏡 WhatsApp group. 
              Jaisy, Laila and Ethan are already in! Once you install WhatsApp, 
              I'll add you too 💬 Download here: [link]'"
[MOBILE-MCP]: "Send SMS"

# Phone capture not needed - using WhatsApp's SMS feature
[TOOL]: update_family_member_apps("Maya", "WhatsApp", "invited")
```

#### Day 2-5 Changes - Dynamic Discovery (Lines 450-800)

**Day 2 Check - Maya Joins**:
```markdown
# Day 2 - Line ~450
User: "Good morning! Let's check if Maya joined WhatsApp yet"

Agent: I'll check the family group status.

[TOOL]: get_family_members(filter="not_in_whatsapp")
Returns: ["Maya"]

[TOOL]: get_migration_overview()  # Gets group name
Returns: {..., "whatsapp_group_name": "Smith Family 🏡"}

[MOBILE-MCP]: "Open WhatsApp"
[MOBILE-MCP]: "Go to 'Smith Family 🏡' group"
[MOBILE-MCP]: "Try to add Maya to the group"
Response: "Found Maya! Adding to group."

Excellent! Maya has joined WhatsApp overnight. Adding her to the family group now.

[TOOL]: update_family_member_apps("Maya", "WhatsApp", "configured", 
        details={"in_whatsapp_group": true})

[MOBILE-MCP]: "In the group, type: 'Welcome Maya! 🎉 Now our whole family is connected!'"
[MOBILE-MCP]: "Send message"

Perfect! All 4 family members are now in the WhatsApp group.

[MOBILE-MCP]: "Open Google Maps"
[MOBILE-MCP]: "Check who's sharing location with me. Return list of names."
Response: "Sharing with you: Jaisy (2 mins ago), Laila (1 hour ago), Maya (just now)"

[TOOL]: update_family_member_apps("Maya", "Google Maps", "configured",
        details={"location_sharing_received": true})
[TOOL]: update_family_member_apps("Laila", "Google Maps", "configured",
        details={"location_sharing_received": true})

[TOOL]: get_family_service_summary()

Fantastic progress! All family members are now in WhatsApp, and 3 of 4 are sharing location.
```

### 2. Agent Instructions Updates (DETAILED PLAN)

**File**: `ios-to-android-migration-assitant-agent/agent/instructions/ios2android-agent-instructions.md`  
**Current**: 1,194 lines  
**Target**: ~1,350 lines with new patterns

#### Section 1: Add Database-Driven Family Management (After Line ~200)

```markdown
### Database-Driven Family Discovery Pattern

ALWAYS query the database before any mobile-mcp family actions:

1. **Before WhatsApp Group Creation**:
   ```python
   family = get_family_members()
   group_name = get_migration_overview()["whatsapp_group_name"]
   # Generate: "Search for: {', '.join(names)}"
   ```

2. **Before Location Sharing**:
   ```python
   family = get_family_members()
   # Generate: "Share location with: {', '.join(names)}"
   ```

3. **Before Status Checks**:
   ```python
   not_connected = get_family_members(filter="not_in_whatsapp")
   not_sharing = get_family_members(filter="not_sharing_location")
   ```

NEVER hardcode family names in mobile-mcp instructions.
```

#### Section 2: WhatsApp SMS Invite Pattern (New Section after Line ~350)

```markdown
### WhatsApp SMS Invite Feature (Preferred Method)

When family members are not on WhatsApp, use WhatsApp's built-in invite feature instead of separate SMS app:

**Discovery Pattern**:
```python
# First check who's not on WhatsApp
not_on_whatsapp = get_family_members(filter="not_in_whatsapp")

for member in not_on_whatsapp:
    [MOBILE-MCP]: "In WhatsApp, search for '{member['name']}'"
    [MOBILE-MCP]: "Select contact showing as not on WhatsApp"
    [MOBILE-MCP]: "This opens Messages app with invite template"
    [MOBILE-MCP]: "Long press message, Select All, Delete"
    [MOBILE-MCP]: "Type personalized message including family group name"
    [MOBILE-MCP]: "Send SMS"
    
    # Update database
    update_family_member(member["name"], phone=captured_number)
    update_family_member_apps(member["name"], "WhatsApp", "invited")
```

**Key Advantages**:
- Uses WhatsApp's official invite flow
- Automatically includes download link
- Keeps everything within WhatsApp context
- More natural user experience
```

#### Section 3: Update Day-by-Day Patterns (Line ~600)

```markdown
### Day 1 Pattern - Initial Setup with Discovery

**Morning: Family Context Processing**
```python
# Parse family from natural language
for member in parsed_family:
    add_family_member(name, role, age)

if whatsapp_group_name:
    update_migration_status(migration_id, whatsapp_group_name=group_name)
```

**WhatsApp Group Creation**:
```python
family = get_family_members()
[MOBILE-MCP]: f"Search for contacts: {', '.join([m['name'] for m in family])}"
# Response indicates who was found
# Update states for found members
# Use SMS invite for not found
```

### Day 2 Pattern - WhatsApp Completion

**Check Status First**:
```python
summary = get_family_service_summary()
# Shows Maya pending, 0/4 sharing location

[MOBILE-MCP]: "Check if Maya can be added to group"
# If found, add and update state

[MOBILE-MCP]: "Check location sharing status"
# Update states for those now sharing
```

### Day 3 Pattern - Location Completion

**Final Connections**:
```python
[MOBILE-MCP]: "Check all location sharing"
# Should find Ethan and Maya now sharing
# Update states to complete

summary = get_family_service_summary()
# Shows all services complete except Venmo
```

### Day 4 Pattern - Photos Focus

**Celebrate Connectivity**:
```python
progress = check_photo_transfer_progress()
# Photos at 28%

[MOBILE-MCP]: "Explore arriving photos in Google Photos"
# Focus on photos, family already connected
```

### Day 5 Pattern - Venmo Activation

**Teen Card Activation**:
```python
teens = get_family_members(filter="teen")
for teen in teens:
    [MOBILE-MCP]: f"Activate card for {teen['name']}"
    # User provides last 4 digits
    update_family_member_apps(teen['name'], "Venmo", "configured",
        details={"venmo_card_activated": true})
```

Pattern:
```python
# ALWAYS fetch current state before mobile actions
family = get_family_members()
not_connected = get_family_members(filter="not_in_whatsapp")
group_name = get_migration_overview()["whatsapp_group_name"]

# Generate dynamic mobile instructions
mobile_instruction = f"Search for contacts: {', '.join([m['name'] for m in not_connected])}"
```

**Key Principle**: Never hardcode names - always query database first
```

#### Section 4: Update Visualization Patterns (Line ~800)

```markdown
### React Dashboard Data Generation

Use get_family_service_summary() to generate comprehensive status:

**Day 2 Dashboard**:
```javascript
{
  "whatsapp": {
    "total": 4,
    "connected": 4,  // Maya joined!
    "status": "✅ COMPLETE"
  },
  "location": {
    "total": 4,
    "sharing": 2,  // Jaisy & Laila
    "status": "50% sharing"
  }
}
```

**Day 3 Dashboard**:
```javascript
{
  "whatsapp": {"status": "✅ COMPLETE (Day 2)"},
  "location": {"status": "✅ COMPLETE (Day 3)"},
  "venmo": {"status": "📦 Cards in transit"}
}
```

**Day 5 Dashboard**:
```javascript
{
  "family_ecosystem": "100% COMPLETE",
  "all_services": {
    "whatsapp": "✅ 4/4 members",
    "location": "✅ 4/4 bidirectional",
    "venmo": "✅ 2/2 cards active"
  }
}
```
3. Create group with dynamic name
4. Search for ALL family members at once
5. Update database based on who was found

#### Dynamic Discovery Pattern
```python
# NEVER hardcode family names
family = get_family_members()
names = [m["name"] for m in family]

[MOBILE-MCP]: "Open WhatsApp"
[MOBILE-MCP]: f"Create new group called '{group_name}'"
[MOBILE-MCP]: f"Search for contacts: {', '.join(names)}. Add found contacts. Return results."

# Parse response to update each member's status
for name in found_members:
    update_family_member_apps(name, "WhatsApp", "configured", 
                             details={"in_whatsapp_group": true})
```

#### SMS Invitation Pattern - Dynamic
```python
# Get members not in WhatsApp
not_connected = get_family_members(filter="not_in_whatsapp")

for member in not_connected:
    # Generate personalized message based on role/age
    if member["role"] == "spouse":
        msg = f"Hi honey! Setting up WhatsApp for our {group_name}..."
    elif member["age"] < 13:
        msg = "Hi sweetie! Can you get WhatsApp?..."
    else:
        msg = "Hey! Download WhatsApp so we can stay connected..."
    
    [MOBILE-MCP]: f"Send text to {member['name']}: '{msg}'"
    update_family_member(member["name"], phone=captured_number)
```
```

#### Update Phase 4: Daily Discovery - Always Database First (Line ~850)

```markdown
### Phase 4: Daily Family Service Discovery

#### Critical Pattern: Database Before Discovery
```python
# Days 2-5: ALWAYS start with database query
not_in_group = get_family_members(filter="not_in_whatsapp")
group_name = get_migration_overview()["whatsapp_group_name"]

if not_in_group:
    [MOBILE-MCP]: "Open WhatsApp"
    [MOBILE-MCP]: f"Go to '{group_name}' group"
    
    # Check all at once, not one by one
    names = [m["name"] for m in not_in_group]
    [MOBILE-MCP]: f"Search contacts for: {', '.join(names)}. Add found to group. Return results."
    
    # Update based on actual results
    for name in parse_found_members(response):
        update_family_member_apps(name, "WhatsApp", "configured",
                                 details={"in_whatsapp_group": true})
    
    # Send reminders to those still not found
    still_missing = [m for m in not_in_group if m["name"] not in found_members]
    for member in still_missing:
        [MOBILE-MCP]: f"Send reminder text to {member['name']}"
```

#### Location Sharing Discovery - Dynamic
```python
# Get all family members for checking
family = get_family_members()

[MOBILE-MCP]: "Open Google Maps"
[MOBILE-MCP]: "Check who's sharing location with me. Return list of names and times."

# Parse response and update only those sharing
for name in parse_location_sharers(response):
    if name in [m["name"] for m in family]:
        update_family_member_apps(name, "Google Maps", "configured",
                                 details={"location_sharing_received": true})
```

#### Venmo Card Activation - Database-Driven
```python
# Day 5: Get teens who need cards
teens = get_family_members(filter="teen")

if user_says("cards arrived"):
    for teen in teens:
        [MOBILE-MCP]: f"Open Venmo, activate {teen['name']}'s card"
        update_family_member_apps(teen["name"], "Venmo", "configured",
                                 details={"venmo_card_activated": true})
```

#### Rules for Database-Driven Discovery
1. **Always Query First**: Never assume family composition
2. **Batch Operations**: Check multiple people at once
3. **Dynamic Instructions**: Build mobile commands from database state
4. **Parse Responses**: Update only based on actual findings
5. **Track Everything**: Persist all discoveries immediately
```

### 3. Database Schema Changes (Direct Modifications)

#### File: shared/database/schemas/migration_schema.sql

**Remove app_setup Table (Delete Lines 168-186)**:
```sql
-- Lines 168-186: DELETE ENTIRE app_setup TABLE DEFINITION
-- Remove: CREATE TABLE app_setup (...)
-- Remove: All related indexes for app_setup
```

**Modify migration_status Table (Lines 22-52)**:
```sql
CREATE TABLE migration_status (
    id TEXT PRIMARY KEY DEFAULT ('MIG-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S')),
    user_name TEXT NOT NULL,
    source_device TEXT DEFAULT 'iPhone',
    target_device TEXT DEFAULT 'Galaxy Z Fold 7',
    years_on_ios INTEGER,
    
    -- iCloud metrics (from check_icloud_status)
    photo_count INTEGER,
    video_count INTEGER,
    total_icloud_storage_gb REAL,
    icloud_photo_storage_gb REAL,
    icloud_video_storage_gb REAL,
    album_count INTEGER,
    
    -- Google baseline metrics (from Google One)
    google_storage_total_gb REAL DEFAULT 2048,
    google_photos_baseline_gb REAL,
    google_drive_baseline_gb REAL,
    gmail_baseline_gb REAL,
    
    -- Migration tracking
    family_size INTEGER,
    whatsapp_group_name TEXT,  -- NEW: Store family group name
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_phase TEXT DEFAULT 'initialization',
    overall_progress INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    
    CONSTRAINT valid_progress CHECK (overall_progress BETWEEN 0 AND 100),
    CONSTRAINT valid_phase CHECK (current_phase IN ('initialization', 'media_transfer', 'family_setup', 'validation', 'completed'))
);
```

**Enhance family_app_adoption Table (Lines 188-202)**:
```sql
CREATE TABLE family_app_adoption (
    id INTEGER PRIMARY KEY DEFAULT nextval('family_app_adoption_seq'),
    family_member_id INTEGER NOT NULL,
    app_name TEXT,
    status TEXT DEFAULT 'not_started',
    invitation_sent_at TIMESTAMP,
    invitation_method TEXT DEFAULT 'sms',  -- Changed from 'email' to 'sms'
    installed_at TIMESTAMP,
    configured_at TIMESTAMP,
    
    -- NEW COLUMNS FOR GRANULAR STATE TRACKING
    whatsapp_in_group BOOLEAN DEFAULT false,
    location_sharing_sent BOOLEAN DEFAULT false,
    location_sharing_received BOOLEAN DEFAULT false,
    venmo_card_activated BOOLEAN DEFAULT false,
    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    UNIQUE(family_member_id, app_name),
    CONSTRAINT valid_app CHECK (app_name IN ('WhatsApp', 'Google Maps', 'Venmo')),
    CONSTRAINT valid_status CHECK (status IN ('not_started', 'invited', 'installed', 'configured'))
);
```

**Update Indexes (Lines 220-228)**:
```sql
-- Remove this line:
-- CREATE INDEX idx_app_setup_migration ON app_setup(migration_id);

-- Keep all other indexes as-is
```

**Update Views to Reference New Columns (Lines 233-332)**:
```sql
-- Update migration_summary view to include whatsapp_group_name
-- Update family_app_status view to show granular states
-- Example snippet for migration_summary:
CREATE VIEW migration_summary AS
SELECT 
    m.id,
    m.user_name,
    m.whatsapp_group_name,  -- Include group name
    m.current_phase,
    -- ... rest of view definition
```

### 4. MCP Tool Changes

#### File: mcp-tools/migration-state/server.py

**Add Filter Support to get_family_members**:
```python
Tool(
    name="get_family_members",
    description="Get family members with optional filtering",
    inputSchema={
        "type": "object",
        "properties": {
            "filter": {
                "type": "string",
                "enum": ["all", "not_in_whatsapp", "not_sharing_location", "teen", "no_phone"],
                "description": "Filter family members by status"
            }
        }
    }
)

# In handler:
elif name == "get_family_members":
    filter_type = arguments.get("filter", "all")
    result = await db.get_family_members(filter_type)
    return [TextContent(text=json.dumps(result, indent=2))]
```

**Enhance get_migration_overview to include group name**:
```python
# In get_migration_overview handler, add:
result["whatsapp_group_name"] = migration.get("whatsapp_group_name", "Family Group")
```

### 5. Database Method Updates

#### File: shared/database/migration_db.py

**Enhanced get_family_members with Filtering**:
```python
async def get_family_members(self, filter_type: str = "all") -> List[Dict[str, Any]]:
    """
    Get family members with optional filtering.
    
    Filters:
    - all: All family members
    - not_in_whatsapp: Members not in WhatsApp group
    - not_sharing_location: Members not sharing location
    - teen: Members age 13-18
    - no_phone: Members without phone numbers
    """
    with self.get_connection() as conn:
        base_query = """
            SELECT fm.*, 
                   faa_wa.whatsapp_in_group,
                   faa_maps.location_sharing_received,
                   faa_wa.status as whatsapp_status
            FROM family_members fm
            LEFT JOIN family_app_adoption faa_wa 
                ON fm.id = faa_wa.family_member_id AND faa_wa.app_name = 'WhatsApp'
            LEFT JOIN family_app_adoption faa_maps 
                ON fm.id = faa_maps.family_member_id AND faa_maps.app_name = 'Google Maps'
            WHERE fm.migration_id = ?
        """
        
        if filter_type == "not_in_whatsapp":
            base_query += " AND (faa_wa.whatsapp_in_group IS FALSE OR faa_wa.whatsapp_in_group IS NULL)"
        elif filter_type == "not_sharing_location":
            base_query += " AND (faa_maps.location_sharing_received IS FALSE OR faa_maps.location_sharing_received IS NULL)"
        elif filter_type == "teen":
            base_query += " AND fm.age BETWEEN 13 AND 18"
        elif filter_type == "no_phone":
            base_query += " AND fm.phone IS NULL"
        
        results = conn.execute(base_query, (self.current_migration_id,)).fetchall()
        
        return [dict(row) for row in results]
```

**Store WhatsApp Group Name**:
```python
async def set_whatsapp_group_name(self, group_name: str) -> Dict[str, Any]:
    """Store the WhatsApp group name at migration level."""
    with self.get_connection() as conn:
        conn.execute(
            "UPDATE migration_status SET whatsapp_group_name = ? WHERE id = ?",
            (group_name, self.current_migration_id)
        )
        return {"status": "success", "group_name": group_name}
```

---

## 🧪 Mobile-MCP Test Flows (Database-Driven Natural Language)

### Flow 1: Gmail - Confirm Apple Transfer

**Purpose**: Verify transfer initiation email from Apple  
**Day**: 1  
**Pre-requisites**: None (no database needed)

**Mobile-MCP Natural Language Instructions**:
```
Step 1: Open Gmail
- Launch Gmail app
- Wait for inbox to load

Step 2: Search for Transfer Email
- Tap the search bar
- Type "photos and videos are being transferred"
- Tap search

Step 3: Verify Email
- Look for email from appleid@apple.com
- Open the most recent transfer confirmation
- Take screenshot of the email
- Return confirmation that transfer has been initiated
```

### Flow 2: WhatsApp - Create Family Group (Fully Dynamic)

**Purpose**: Set up family communication group  
**Day**: 1  
**Pre-requisites**:
```
[TOOL]: get_family_members()  # Returns variable family list
[TOOL]: get_migration_overview()  # Gets group name from database
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Connect to Samsung Galaxy Fold device
- Create WhatsApp family group with members from database

Step 1: Open WhatsApp
- Launch WhatsApp app
- Wait for app to fully load in two-panel view
- Verify you see "No chat selected" in the right panel

Step 2: Access Group Creation Menu
- Click the three dots (⋮) at top of LEFT panel
- Click coordinates: 768, 89
- This opens the dropdown menu

Step 3: Select "New group"
- Click "New group" from the dropdown menu
- Click coordinates: 390, 281
- This opens the member selection screen

Step 4: Add Group Members
- Click the Search icon
- The search field should be auto-focused
- For each family member returned from the database:
    - Type the member's name
    - If contact is found, select to add to group
    - Note whether found or not found
    - Field auto-clears after each selection
- After searching all members, return complete results
- Example format: "Found and added: [list of found names]. Not found: [list of not found names]"

Step 5: Proceed to Group Details
- Click the "Next" button (green arrow icon)

Step 6: Name the Group
- Group name field will be auto-focused
- Type the group name from database (whatsapp_group_name field)

Step 7: Create the Group
- Click the "Create" button (checkmark icon)
- Return confirmation of group creation with final member count
```

**Post-processing Database Updates**:
```
Parse response to identify who was found/not found
Update each member's status in family_app_adoption table accordingly
```

### Flow 3: WhatsApp SMS Invite (Dynamic)

**Purpose**: Use WhatsApp's built-in SMS invite feature for family members not on WhatsApp  
**Day**: 1  
**Pre-requisites**:
```
[TOOL]: get_family_members(filter="not_in_whatsapp")
[TOOL]: get_migration_overview()  # For group name
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Use WhatsApp's invite feature to send SMS to family members not on WhatsApp
- Customize the auto-generated message with personal touch

For each family member not on WhatsApp (from database):

Step 1: Open WhatsApp
- Launch WhatsApp app if not already open
- Ensure you're at the main chat list

Step 2: Search for Contact
- Find the 'Ask Meta AI or Search' text box at top
- Click on it to activate search
- The search field should be auto-focused
- Type the family member's name (from database)
- Look for the contact in results

Step 3: Select Invite Option
- If contact shows as not on WhatsApp, select it
- This opens the invite to WhatsApp option
- WhatsApp will prepare to open Messages app

Step 4: Customize Invitation Message
- Google Messages app will open with pre-filled invite
- The default message will be visible
- Long press on the message text area
- Click "Select All" to select the default message
- Delete the selected text

Step 5: Type Personalized Message
- Type a new personalized message based on member's role:
    - For spouse: "Hi honey! I'm setting up WhatsApp for our [group_name]. Once you install it, I'll add you to our family chat group ❤️"
    - For teen (13-18): "Hey! Download WhatsApp so we can stay connected. Once you install it, I'll add you to our family group. Dad's on Android now! 🤖"
    - For child (<13): "Hi sweetie! Can you install WhatsApp? Once you have it, I'll add you to our family chat group! 💬"
- Include the WhatsApp download link (auto-added)

Step 6: Send Invitation
- Review the personalized message
- Tap send button
- Return confirmation that SMS was sent
- Note the phone number for database update

Step 7: Return to WhatsApp
- Navigate back to WhatsApp
- Ready for next family member invitation

Repeat for each family member not on WhatsApp
```

**Post-processing**:
```
For each invitation sent:
- Update family_members table with phone number if captured
- Update family_app_adoption status to "invited"
- Set invitation_sent_at timestamp
```

### Flow 4: WhatsApp - Daily Discovery Check (Dynamic)

**Purpose**: Check for new WhatsApp installations and add members to group  
**Days**: 2-5  
**Pre-requisites**:
```
[TOOL]: get_family_members(filter="not_in_whatsapp")
[TOOL]: get_migration_overview()  # For group name
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Check which family members have installed WhatsApp
- Add any new members to the family group

Step 1: Open WhatsApp
- Launch WhatsApp app
- Wait for chat list to load

Step 2: Navigate to Family Group
- Find and tap on the group from database (group name)
- Verify group opens in right panel

Step 3: Access Add Participants
- Tap the group name at top to open info
- Scroll to participants section
- Tap "Add participant"

Step 4: Search for Missing Members
- For each family member not yet in group (from database):
    - Type member's name in search field
    - If contact appears, select to add
    - Note if contact not found
    - Search field clears after each selection
- Return complete results of who was found and added

Step 5: Complete Addition
- If any members were found, tap the checkmark to add them
- Return to group chat
- Report final group member count
```

**Post-processing**:
```
Update family_app_adoption for newly found members
Set whatsapp_in_group = true for added members
```

### Flow 5: Google Maps - Check Location Sharing Status (Dynamic)

**Purpose**: Discover which family members are sharing location  
**Days**: 1-6  
**Pre-requisites**:
```
[TOOL]: get_family_members()  # To validate names against database
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Check current location sharing status
- Identify which family members are sharing with you

Step 1: Open Google Maps
- Launch Google Maps app
- Wait for map to fully load

Step 2: Access Location Sharing
- Tap your profile picture in top right
- Select "Location sharing" from menu

Step 3: Check Sharing Status
- View list of people sharing with you
- Note each person's name and last update time
- Check if you're sharing with them (bidirectional)
- Return complete list with details:
    - Who's sharing with you
    - When they last updated
    - Whether sharing is bidirectional

Step 4: Match Against Family
- Compare returned names with family members from database
- Identify which family members are/aren't sharing
- Return matched results
```

**Post-processing**:
```
For each family member found sharing:
- Update location_sharing_received = true
- Update location_sharing_sent = true (if bidirectional)
- Update last_checked_at timestamp
```

### Flow 6: Google Maps - Share Your Location (Dynamic)

**Purpose**: Share location with all family members  
**Day**: 1  
**Pre-requisites**:
```
[TOOL]: get_family_members()  # Get all family names
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Share your location with all family members
- Set sharing duration to permanent

Step 1: Open Google Maps
- Launch Google Maps app
- Wait for map to load

Step 2: Access Location Sharing
- Tap your profile picture in top right
- Select "Location sharing"

Step 3: Start New Share
- Tap "Share location" or "New share" button
- Select duration: "Until you turn this off"

Step 4: Select Recipients
- In the contact selection screen:
- For each family member from database:
    - Search for member's name
    - If found, select the contact
    - Note if contact not found
- After selecting all available family members, proceed

Step 5: Confirm Sharing
- Review selected recipients
- Tap "Share" to confirm
- Return list of who location was shared with
- Note any family members not found in contacts
```

**Post-processing**:
```
For each family member location was shared with:
- Update location_sharing_sent = true
- Update status to "invited" or "configured" based on result
```

### Flow 7: Venmo - Order Teen Cards (Dynamic)

**Purpose**: Order Venmo Teen Debit Cards for eligible family members  
**Day**: 1  
**Pre-requisites**:
```
[TOOL]: get_family_members(filter="teen")  # Ages 13-18
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Order Venmo Teen Debit Cards for teenage family members
- Process each teen account individually

For each teen family member from database:

Step 1: Open Venmo
- Launch Venmo app
- Wait for home screen to load

Step 2: Access Teen Accounts
- Tap the menu icon (☰)
- Select "Teen accounts"
- Find the teen's account (by name from database)

Step 3: Navigate to Card Section
- Tap on teen's account to open
- Look for "Venmo Teen Debit Card" section
- Tap "Order card" or "Get started"

Step 4: Confirm Details
- Verify teen's name is correct
- Confirm shipping address
- Review card details

Step 5: Complete Order
- Tap "Order card" to confirm
- Note the estimated delivery (3-7 business days)
- Take screenshot of confirmation
- Return confirmation with card order details

Repeat for each teen in family
```

**Post-processing**:
```
For each teen with card ordered:
- Update venmo_setup table with card_ordered_at timestamp
- Update family_app_adoption status to "invited"
```

### Flow 8: Venmo - Activate Teen Cards (Dynamic)

**Purpose**: Activate Venmo Teen Debit Cards when they arrive  
**Day**: 5  
**Pre-requisites**:
```
[TOOL]: get_family_members(filter="teen")
User confirms: "The Venmo cards arrived!"
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Activate physical Venmo Teen Debit Cards
- Set up PIN for each card

For each teen with arrived card (from database):

Step 1: Open Venmo
- Launch Venmo app
- Wait for home screen

Step 2: Access Teen Account
- Tap menu icon (☰)
- Select "Teen accounts"
- Tap on teen's account (name from database)

Step 3: Start Card Activation
- Find "Venmo Teen Debit Card" section
- Tap "Activate card"

Step 4: Enter Card Details
- When prompted, enter last 4 digits of physical card
- User provides these digits
- Enter the digits in the field

Step 5: Set PIN
- Create a 4-digit PIN for the card
- Confirm the PIN
- Complete activation

Step 6: Verify Activation
- Confirm card shows as "Active"
- Return confirmation of activation
- Note card last 4 digits for records

Repeat for each teen's card
```

**Post-processing**:
```
For each activated card:
- Update venmo_card_activated = true
- Update card_activated_at timestamp
- Store card_last_four if captured
- Update status to "configured"
```

### Flow 9: Messages - Send Progress Reminders (Dynamic)

**Purpose**: Send friendly reminders to family members not yet connected  
**Days**: 2-6  
**Pre-requisites**:
```
[TOOL]: get_family_members(filter="not_in_whatsapp")
[TOOL]: get_daily_summary(day_number)  # For context
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Send personalized reminder messages
- Adjust tone based on day and previous attempts

Step 1: Open Messages
- Launch Messages app
- Wait for conversations to load

Step 2: Send Reminders to Each Unconnected Member
For each family member not yet in WhatsApp (from database):
- Open existing conversation or create new message
- Enter recipient name or phone number
- Type day-appropriate reminder:
    Day 2: "Hi [name]! Just checking - did you get my WhatsApp invite? [spouse/sibling] already joined!"
    Day 3: "Hey [name], we're at [X] people in our WhatsApp group now. Join us when you can!"
    Day 4: "Photos are starting to appear! 📸 Don't forget to join our WhatsApp group"
    Day 5: "[name], almost everyone's connected now. Here's the WhatsApp link again: [link]"
    Day 6: "Last reminder about WhatsApp! We'd love to have you in the group 💙"
- Send message
- Note confirmation of delivery

Step 3: Return Summary
- Report number of reminders sent
- List recipients
- Note any delivery failures
```

**Post-processing**:
```
Update last_checked_at for each member contacted
Log reminder sent in daily_progress if tracking
```

### Flow 10: Complete Family Service Status Check (Dynamic)

**Purpose**: Comprehensive check of all family services  
**Days**: 3, 5, 7  
**Pre-requisites**:
```
[TOOL]: get_family_members()
[TOOL]: get_migration_overview()  # For group name
[TOOL]: get_family_members(filter="teen")  # For Venmo checks
```

**Mobile-MCP Natural Language Instructions**:
```
Setup
- Perform complete status check across all family services
- Update database with current state

Part 1: WhatsApp Status
- Open WhatsApp
- Navigate to family group (name from database)
- Tap group name to see members
- Return complete list of current group members
- Note total member count

Part 2: Location Sharing Status
- Open Google Maps
- Tap profile picture → Location sharing
- Check "Sharing with you" section
- Return list of all people sharing location
- Check "You're sharing with" section
- Return list of who you're sharing with
- Note last update times

Part 3: Venmo Status (if teens exist)
- Open Venmo
- Go to Teen accounts section
- For each teen account (from database):
    - Check account status
    - Check if card is ordered/activated
    - Note card status (pending/active)
- Return status for each teen account

Part 4: Summary
- Compile results from all three services
- Return comprehensive status report:
    - WhatsApp: X of Y family members in group
    - Location: X sharing with you, you sharing with Y
    - Venmo: X cards ordered, Y cards activated
```

**Post-processing**:
```
[TOOL]: get_family_service_summary()  # Generate final report
Update all discovered states in family_app_adoption table
Create React visualization with current status
```

---

## 📅 Complete Tool Call Flow with update_migration_status

### Day 1: Initialize → Family → Check → Update → Transfer
```python
# Phase 1: Initial Setup (from user conversation)
[TOOL]: initialize_migration("George", years_on_ios=18)
Returns: migration_id = "MIG-20250827-120000"

[TOOL]: add_family_member("Jaisy", "spouse", migration_id=migration_id)
[TOOL]: add_family_member("Laila", "child", 17, migration_id=migration_id)
[TOOL]: add_family_member("Ethan", "child", 15, migration_id=migration_id)
[TOOL]: add_family_member("Maya", "child", 11, migration_id=migration_id)

# Phase 2: Photo Migration
[TOOL]: check_icloud_status()
Returns: {photos: 60238, videos: 2418, storage_gb: 383}

[TOOL]: update_migration_status(
    migration_id,
    photo_count=60238,
    video_count=2418,
    total_icloud_storage_gb=383,
    icloud_photo_storage_gb=268,
    icloud_video_storage_gb=115
)

[TOOL]: start_photo_transfer()
Returns: {transfer_id: "TRF-20250827", google_photos_baseline_gb: 13.88}

[TOOL]: update_migration_status(
    migration_id,
    current_phase='media_transfer',
    photo_transfer_id="TRF-20250827",
    google_photos_baseline_gb=13.88,
    overall_progress=5
)

# Phase 3: Family Apps
[MOBILE-MCP]: WhatsApp group creation...
[TOOL]: update_family_member_apps(...)

# End of Day 1
[TOOL]: update_migration_status(
    migration_id,
    family_size=4,
    overall_progress=10,
    notes='WhatsApp 3/4, Location 0/4'
)
```

### Days 2-7: Progressive Updates
Each day follows the pattern:
1. Check progress/status
2. Update migration_status with new metrics
3. Update family_member_apps as services connect
4. Final update_migration_status at day end

Total update_migration_status calls: 14 across 7 days

## 📅 Complete Day-by-Day Flow (Updated Demo Script)

Based on our updated demo script, here's the complete day-by-day flow with all tool calls and state changes:

### Day 1: Initial Setup
**Key Events**: Parse family, create WhatsApp group (3 of 4 found), invite Maya, setup location sharing

```markdown
# Family Registration
[TOOL]: add_family_member("Jaisy", role="spouse")
[TOOL]: add_family_member("Laila", role="child", age=17)
[TOOL]: add_family_member("Ethan", role="child", age=15)
[TOOL]: add_family_member("Maya", role="child", age=11)
[TOOL]: set_whatsapp_group_name("Vetticaden Family")

# WhatsApp Group Creation - Database Driven
[TOOL]: get_family_members()
Returns: ["Jaisy", "Laila", "Ethan", "Maya"]

[MOBILE-MCP]: "Create WhatsApp group 'Vetticaden Family'"
[MOBILE-MCP]: "Search for contacts: Jaisy, Laila, Ethan, Maya. Add found contacts."
Response: "Found and added: Jaisy, Laila, Ethan. Not found: Maya"

# Update discovered states
[TOOL]: update_family_member_apps("Jaisy", "WhatsApp", "configured", 
        details={"in_whatsapp_group": true})
[TOOL]: update_family_member_apps("Laila", "WhatsApp", "configured",
        details={"in_whatsapp_group": true})
[TOOL]: update_family_member_apps("Ethan", "WhatsApp", "configured",
        details={"in_whatsapp_group": true})

# WhatsApp SMS Invite for Maya
[TOOL]: get_family_members(filter="not_in_whatsapp")
Returns: [{"name": "Maya", "phone": null}]

[MOBILE-MCP]: "In WhatsApp, search for 'Maya'"
[MOBILE-MCP]: "Select to invite via SMS"
[MOBILE-MCP]: "Customize message with family group name"
[MOBILE-MCP]: "Send SMS, return phone number"
Response: "SMS sent to +1-555-0103"

[TOOL]: update_family_member("Maya", phone="+1-555-0103")
[TOOL]: update_family_member_apps("Maya", "WhatsApp", "invited")

# Location Sharing Setup
[TOOL]: get_family_members()
[MOBILE-MCP]: "Setup location sharing with: Jaisy, Laila, Ethan, Maya"
[TOOL]: update_family_member_apps(each, "Google Maps", "invited",
        details={"location_sharing_sent": true})
```

### Day 2: WhatsApp Complete
**Key Events**: Maya joins WhatsApp, Jaisy & Laila accept location sharing

```markdown
# Check Family Status
[TOOL]: get_family_service_summary()
Returns: {
  "whatsapp": {"connected": 3, "pending": ["Maya"]},
  "location": {"sharing": 0, "invitations_sent": 4}
}

# Maya Joins WhatsApp
[MOBILE-MCP]: "Check if Maya can be added to group"
Response: "Found Maya! Adding to group."

[TOOL]: update_family_member_apps("Maya", "WhatsApp", "configured",
        details={"in_whatsapp_group": true})

# Location Sharing Updates
[MOBILE-MCP]: "Check who's sharing location"
Response: "Sharing: Jaisy, Laila"

[TOOL]: update_family_member_apps("Jaisy", "Google Maps", "configured",
        details={"location_sharing_received": true})
[TOOL]: update_family_member_apps("Laila", "Google Maps", "configured",
        details={"location_sharing_received": true})

Status: WhatsApp 4/4 ✅, Location 2/4
```

### Day 3: Location Complete
**Key Events**: Ethan & Maya accept location sharing, family ecosystem complete

```markdown
# Check Location Status
[MOBILE-MCP]: "Check location sharing status"
Response: "All 4 family members now sharing"

[TOOL]: update_family_member_apps("Ethan", "Google Maps", "configured",
        details={"location_sharing_received": true})
[TOOL]: update_family_member_apps("Maya", "Google Maps", "configured",
        details={"location_sharing_received": true})

[TOOL]: get_family_service_summary()
Returns: {
  "whatsapp": {"status": "complete", "connected": 4},
  "location": {"status": "complete", "sharing": 4},
  "venmo": {"status": "cards_ordered"}
}

Status: WhatsApp 4/4 ✅, Location 4/4 ✅
```

### Day 4: Photos Arrive
**Key Events**: Photos start appearing (28%), explore Google Photos

```markdown
[TOOL]: check_photo_transfer_progress()
Returns: {"progress": 28, "photos_visible": 17200}

[MOBILE-MCP]: "Open Google Photos"
[MOBILE-MCP]: "Browse arriving photos from 2007-2024"
[MOBILE-MCP]: "Show AI organization, face groups, albums"

[TOOL]: get_family_service_summary()
# All family services already complete

Status: Family ecosystem complete, photos arriving
```

### Day 5: Venmo Cards Activated
**Key Events**: Venmo cards arrive and get activated

```markdown
[TOOL]: get_family_members(filter="teen")
Returns: [{"name": "Laila", "age": 17}, {"name": "Ethan", "age": 15}]

[MOBILE-MCP]: "Activate Venmo card for Laila"
User provides: "1234"
[MOBILE-MCP]: "Activate Venmo card for Ethan"  
User provides: "5678"

[TOOL]: update_family_member_apps("Laila", "Venmo", "configured",
        details={"venmo_card_activated": true, "card_last_four": "1234"})
[TOOL]: update_family_member_apps("Ethan", "Venmo", "configured",
        details={"venmo_card_activated": true, "card_last_four": "5678"})

Status: All family services 100% complete ✅
```

### Day 6: Near Completion
**Key Events**: Photos at 88%, explore near-complete library

```markdown
[TOOL]: check_photo_transfer_progress()
Returns: {"progress": 88, "photos_visible": 53009}

[MOBILE-MCP]: "Explore Google Photos library"
[MOBILE-MCP]: "Show Years view, People & Pets, smart albums"

Status: Migration 88% complete, all services operational
```

### Day 7: Complete Success
**Key Events**: 100% completion, final verification

```markdown
[TOOL]: check_photo_transfer_progress()
Returns: {"progress": 100, "photos_visible": 60238}

[TOOL]: get_family_service_summary()
[MOBILE-MCP]: "Verify all family services"
Response: "WhatsApp: 4/4, Location: 4/4, Venmo: 2/2 active"

[TOOL]: generate_migration_report(format="detailed")

Status: MIGRATION COMPLETE 🎉
```

---

## ✅ Success Criteria

1. **Database-Driven**: All mobile actions based on current database state
2. **No Hardcoding**: Family names, group names, phone numbers from database
3. **Dynamic Discovery**: Mobile instructions generated from queries
4. **Batch Operations**: Check multiple family members at once
5. **Progressive Updates**: Enrich data as discovered
6. **Smart Filtering**: Query only relevant family members
7. **State Persistence**: All discoveries saved immediately
8. **Flexible Patterns**: Works for any family size/composition

---

## 💡 Key Design Decisions

### Database-First Approach
- Always query before mobile actions
- Generate instructions dynamically
- Never assume family composition

### Batch Discovery
- Check all missing members at once
- More efficient than individual searches
- Single mobile action returns multiple results

### Progressive Data Enhancement
- Start with names from context
- Add phones during SMS
- Add service states during discovery

### Filter-Based Queries
- get_family_members(filter="not_in_whatsapp")
- Reduces unnecessary checking
- Optimizes mobile actions

---

## 📊 Implementation Status Summary

### ✅ Completed
1. **Demo Script**: Database-driven mobile flows with WhatsApp SMS invite
2. **Agent Instructions**: Progressive update patterns with update_migration_status
3. **Implementation Plan**: Updated with uber status tool architecture

### ⏳ Pending (Priority Order)
1. **Demo Script**: Update Days 2-7 to use `get_migration_status()` consistently
2. **Agent Instructions**: Add uber status tool pattern, remove parallel calls
3. **Database Schema**: Remove app_setup table, add 5 columns to family_app_adoption
4. **MCP Tools**: Implement uber status tool, update_migration_status, filters
5. **Testing**: Validate complete 7-day flow with all changes

### 🎯 Key Metrics
- **Tool Reduction**: 10 → 7 MCP tools (30% reduction)
- **Status Calls**: 4-5 → 1 per day (75% reduction)
- **Timeline**: ~10-12 hours remaining

### 📊 Tool Usage Pattern Summary

#### Day 1 Tools (Setup Phase)
1. `initialize_migration(user_name, years_on_ios)` - FIRST, creates migration_id
2. `add_family_member(name, role, age, migration_id)` - 4 calls for family
3. `check_icloud_status()` - Get photo/video counts (web-automation tool)
4. `update_migration_status(...)` - After iCloud check
5. `start_photo_transfer()` - Initiate transfer (web-automation tool)
6. `update_migration_status(...)` - After transfer start
7. `get_family_members()` - Query for WhatsApp/Maps setup
8. `update_family_member_apps(...)` - Multiple calls for app status
9. `update_migration_status(...)` - End of day progress

#### Days 2-7 Tools (Progress Phase)
1. `get_migration_status(day_number)` - UBER TOOL for all status (replaces 4 tools)
2. `update_family_member_apps(...)` - As family members connect
3. `update_migration_status(...)` - End of each day
4. Special cases:
   - Day 5: `get_family_members(filter="teen")` for Venmo
   - Day 7: `generate_migration_report()` for final summary

---

## 📅 Detailed Implementation Steps

### ✅ Step 1: Demo Script Updates (COMPLETE - Database-Driven)
- Updated all 7 days with database-driven flows
- Implemented realistic WhatsApp scenario (3 of 4 have it)
- Added WhatsApp SMS invite feature for Maya
- All mobile-mcp actions now query database first
- Timeline: Day 2 WhatsApp complete, Day 3 Location complete

### ✅ Step 2: Agent Instructions (COMPLETE - Progressive Updates)
**Sections Added**:
1. ✅ Database-Driven Family Discovery Pattern (Lines 184-228)
2. ✅ WhatsApp SMS Invite Feature (Lines 261-289)
3. ✅ Day-by-Day Patterns Update (Lines 479-592)
4. ✅ Visualization Pattern Updates (Lines 1015-1262)
5. ✅ Complete Migration Status Update Patterns (Lines 634-762)

**Key Changes Implemented**:
- Initialize migration FIRST with minimal data (user_name, years_on_ios)
- Add family members using migration_id
- Progressive updates via update_migration_status throughout 7 days
- Correct tool sequence: init → family → check_icloud → update → start_transfer
- Day-by-day update patterns with 14 total update_migration_status calls
- Phase transitions and completion tracking

### ⏳ Step 3: Uber Status Tool - Demo Script Updates

**Purpose**: Update demo script to use consistent `get_migration_status()` pattern for Days 2-7

#### Previous Inconsistent Status Patterns (TO BE FIXED)

**Day 2**: Used `get_family_service_summary()`
**Day 3**: Used `get_daily_summary()` and `get_migration_overview()`  
**Day 4**: Used `check_photo_transfer_progress()` and `get_family_service_summary()`
**Day 5**: Used `get_family_members(filter="teen")` and `check_photo_transfer_progress()`
**Day 6**: Used `get_migration_overview()` and `check_photo_transfer_progress()`
**Day 7**: Used 4 different tools in parallel

These inconsistent patterns are being replaced with a single `get_migration_status(day_number)` call.

#### New Consistent Pattern for ALL Days 2-7

```markdown
**Me**: "[User's status question for the day]"

**Claude**: "Let me check your complete migration status for Day [N]..."

[TOOL CALL]: migration-state.get_migration_status(day_number=[N])

[TOOL RETURNS]: {
  "day_number": N,
  "day_summary": {
    "expected_milestones": [...],
    "key_events": [...]
  },
  "migration_overview": {
    "user_name": "George Vetticaden",
    "current_phase": "...",
    "overall_progress": N,
    "whatsapp_group_name": "Vetticaden Family"
  },
  "photo_progress": {
    "status": "in_progress",
    "percent_complete": N,
    "photos_visible": N,
    "storage_growth_gb": N
  },
  "family_services": {
    "whatsapp": {"total": 4, "connected": N, "pending": [...]},
    "location": {"total": 4, "sharing": N, "pending": [...]},
    "venmo": {"cards_ordered": N, "cards_activated": N}
  },
  "recommended_actions": [...]
}
```

#### Special Cases That Still Need Individual Calls
- **Day 1**: `check_icloud_status()` and `start_photo_transfer()`
- **Day 5**: `get_family_members(filter="teen")` for Venmo activation
- **Day 7**: `generate_migration_report()` for final report
- **All Days**: `update_migration_status()` and `update_family_member_apps()`

### ⏳ Step 4: Uber Status Tool - Agent Instructions Updates

**Purpose**: Simplify agent instructions to use single status tool

#### Add New Section: Universal Status Check Pattern

```markdown
### Universal Status Check Pattern (Days 2-7)

When user asks for status on Days 2-7, ALWAYS use:

get_migration_status(day_number=current_day)

DO NOT make separate calls to:
- get_daily_summary()
- get_migration_overview()  
- check_photo_transfer_progress()
- get_family_service_summary()

These are now internal functions called by get_migration_status().
```

#### Update Tool Selection Guidelines
- Remove references to parallel status calls
- Emphasize single uber tool for all status checks
- Keep special cases for Day 1 tools and updates

### ⏳ Step 5: Database Schema Updates

#### Tables to Modify
- **Remove**: app_setup table (redundant with family_app_adoption)
- **Enhance**: family_app_adoption table - Add 5 columns:
  - whatsapp_in_group (boolean)
  - location_sharing_sent (boolean)
  - location_sharing_received (boolean)
  - venmo_card_activated (boolean)
  - card_last_four (text)
- Modify initialize_migration to accept MINIMAL parameters:
  - REQUIRED: user_name, years_on_ios
  - OPTIONAL: All other fields (NULLable initially)
- Ensure migration_status columns support NULL for progressive updates

#### Note on Storage Tracking
The `storage_snapshots` table exists in the schema to track Google Photos storage growth over time, which is how we calculate photo transfer progress (since Apple doesn't provide real-time updates). However:
- This tracking happens **internally** when `get_migration_status()` is called
- There is **no** separate `record_storage_snapshot()` MCP tool
- Storage metrics are calculated automatically based on day number and expected growth curve
- The uber tool handles all storage calculations internally

### ⏳ Step 6: MCP Tools Updates

**File**: `mcp-tools/migration-state/server.py`

#### A. Tools Being REMOVED from MCP (Convert to Internal Functions)

These tools will be removed from the `server.py` tools list but their functions kept as internal:

1. **REMOVE**: `get_daily_summary` tool definition
   ```python
   # DELETE this Tool() definition from server.py
   Tool(name="get_daily_summary", ...)
   # KEEP the function as internal: async def get_daily_summary(day_number)
   ```

2. **REMOVE**: `get_migration_overview` tool definition
   ```python
   # DELETE this Tool() definition from server.py
   Tool(name="get_migration_overview", ...)
   # KEEP the function as internal: async def get_migration_overview()
   ```

3. **REMOVE**: `get_family_service_summary` tool definition
   ```python
   # DELETE this Tool() definition from server.py
   Tool(name="get_family_service_summary", ...)
   # KEEP the function as internal: async def get_family_service_summary()
   ```

#### B. Tools Being ADDED to MCP

1. **ADD**: `get_migration_status` (UBER TOOL)
   ```python
   Tool(
       name="get_migration_status",
       description="Get comprehensive migration status for a specific day. Replaces all separate status queries.",
       inputSchema={
           "type": "object",
           "properties": {
               "day_number": {
                   "type": "integer",
                   "minimum": 1,
                   "maximum": 7,
                   "description": "The day number (1-7) to get status for"
               }
           },
           "required": ["day_number"]
       }
   )
   ```

2. **ADD**: `update_migration_status`
   ```python
   Tool(
       name="update_migration_status",
       description="Update migration record with progressive information. All fields optional except migration_id.",
       inputSchema={
           "type": "object",
           "properties": {
               "migration_id": {"type": "string", "description": "Migration ID to update"},
               "photo_count": {"type": "integer"},
               "video_count": {"type": "integer"},
               "total_icloud_storage_gb": {"type": "number"},
               "icloud_photo_storage_gb": {"type": "number"},
               "icloud_video_storage_gb": {"type": "number"},
               "album_count": {"type": "integer"},
               "google_photos_baseline_gb": {"type": "number"},
               "whatsapp_group_name": {"type": "string"},
               "current_phase": {
                   "type": "string",
                   "enum": ["initialization", "media_transfer", "family_setup", "validation", "completed"]
               },
               "overall_progress": {"type": "integer", "minimum": 0, "maximum": 100},
               "family_size": {"type": "integer"},
               "completed_at": {"type": "string", "format": "date-time"}
           },
           "required": ["migration_id"]
       }
   )
   ```

#### C. Tools Being MODIFIED

1. **MODIFY**: `initialize_migration` - Simplify parameters
   ```python
   Tool(
       name="initialize_migration",
       description="Initialize a new migration. Only requires user_name and years_on_ios.",
       inputSchema={
           "type": "object",
           "properties": {
               "user_name": {"type": "string", "description": "User's full name"},
               "years_on_ios": {"type": "integer", "description": "Years using iPhone"}
           },
           "required": ["user_name", "years_on_ios"]  # Only these 2 required
       }
   )
   ```

2. **MODIFY**: `get_family_members` - Add filter parameter
   ```python
   Tool(
       name="get_family_members",
       description="Get family members with optional filtering",
       inputSchema={
           "type": "object",
           "properties": {
               "filter": {
                   "type": "string",
                   "enum": ["all", "not_in_whatsapp", "not_sharing_location", "teen", "no_phone"],
                   "description": "Optional filter for family members",
                   "default": "all"
               }
           }
       }
   )
   ```

3. **MODIFY**: `update_family_member_apps` - Add details parameter
   ```python
   Tool(
       name="update_family_member_apps",
       description="Update family member app adoption status with granular details",
       inputSchema={
           "type": "object",
           "properties": {
               "member_name": {"type": "string"},
               "app_name": {"type": "string", "enum": ["WhatsApp", "Google Maps", "Venmo"]},
               "status": {"type": "string", "enum": ["not_started", "invited", "installed", "configured"]},
               "details": {
                   "type": "object",
                   "properties": {
                       "whatsapp_in_group": {"type": "boolean"},
                       "location_sharing_sent": {"type": "boolean"},
                       "location_sharing_received": {"type": "boolean"},
                       "venmo_card_activated": {"type": "boolean"},
                       "card_last_four": {"type": "string"}
                   }
               }
           },
           "required": ["member_name", "app_name", "status"]
       }
   )
   ```

#### D. FINAL MCP Tool List (7 tools total)

After all changes, `server.py` will expose exactly these 7 tools:

```python
# Final tool list in server.py
tools = [
    # 1. Day 1 setup
    Tool(name="initialize_migration", ...),     # Minimal params
    Tool(name="add_family_member", ...),        # Unchanged
    
    # 2. Progressive updates
    Tool(name="update_migration_status", ...),  # NEW
    Tool(name="update_family_member_apps", ...), # Enhanced with details
    
    # 3. Status queries  
    Tool(name="get_migration_status", ...),     # NEW UBER TOOL
    Tool(name="get_family_members", ...),       # Enhanced with filters
    
    # 4. Final report
    Tool(name="generate_migration_report", ...) # Unchanged
]
```

#### E. Handler Implementation for New Tools

```python
# In server.py handler section

elif name == "get_migration_status":
    day_number = arguments["day_number"]
    
    # Call all internal functions
    daily = await db.get_daily_summary(day_number)
    overview = await db.get_migration_overview()
    
    # Get transfer_id from overview for photo progress
    transfer_id = overview.get("transfer_id")
    photo_progress = await db.check_photo_transfer_progress(transfer_id, day_number)
    
    family = await db.get_family_service_summary()
    
    # Combine into unified response
    return {
        "day_number": day_number,
        "day_summary": daily,
        "migration_overview": overview,
        "photo_progress": photo_progress,
        "family_services": family,
        "status_message": f"Day {day_number}: {photo_progress['percent_complete']}% complete",
        "recommended_actions": _get_day_actions(day_number, family)
    }

elif name == "update_migration_status":
    migration_id = arguments.pop("migration_id")
    # Update only provided fields
    result = await db.update_migration_status(migration_id, **arguments)
    return result
```

### ⏳ Step 7: Database Method Updates

**File**: `shared/database/migration_db.py`

#### A. New Methods to Add

1. **ADD**: `update_migration_status()` method
   ```python
   async def update_migration_status(self, migration_id: str, **kwargs) -> Dict[str, Any]:
       """
       Update migration record with only provided fields.
       All fields optional except migration_id.
       """
       with self.get_connection() as conn:
           # Build UPDATE statement dynamically
           update_fields = []
           values = []
           
           for field, value in kwargs.items():
               if field in ['photo_count', 'video_count', 'total_icloud_storage_gb',
                           'icloud_photo_storage_gb', 'icloud_video_storage_gb', 
                           'album_count', 'google_photos_baseline_gb',
                           'whatsapp_group_name', 'current_phase', 
                           'overall_progress', 'family_size', 'completed_at']:
                   update_fields.append(f"{field} = ?")
                   values.append(value)
           
           if not update_fields:
               return {"status": "error", "message": "No fields to update"}
           
           values.append(migration_id)
           query = f"UPDATE migration_status SET {', '.join(update_fields)} WHERE id = ?"
           
           conn.execute(query, values)
           return {"status": "success", "migration_id": migration_id, "updated_fields": list(kwargs.keys())}
   ```

2. **ADD**: `check_photo_transfer_progress()` method (move from web-automation)
   ```python
   async def check_photo_transfer_progress(self, transfer_id: str, day_number: int) -> Dict[str, Any]:
       """
       Calculate photo transfer progress based on storage growth.
       This is now an internal method, not exposed via MCP.
       """
       # Storage growth curve by day
       expected_storage = {
           1: 13.88,   # Baseline
           2: 13.88,   # Still processing
           3: 13.88,   # Still processing
           4: 120.88,  # 28% complete
           5: 220.88,  # 57% complete
           6: 340.88,  # 88% complete
           7: 396.88   # 100% complete
       }
       
       current_gb = expected_storage.get(day_number, 13.88)
       baseline_gb = 13.88
       total_gb = 383.0
       
       if day_number <= 3:
           percent = 0
           photos_visible = 0
       else:
           percent = min(100, ((current_gb - baseline_gb) / total_gb) * 100)
           photos_visible = int(60238 * (percent / 100))
       
       return {
           "transfer_id": transfer_id,
           "day_number": day_number,
           "percent_complete": round(percent, 1),
           "photos_visible": photos_visible,
           "storage_growth_gb": current_gb - baseline_gb,
           "status": "completed" if percent >= 100 else "in_progress"
       }
   ```

#### B. Methods to Modify

1. **MODIFY**: `initialize_migration()` - Accept minimal parameters
   ```python
   async def initialize_migration(
       self, 
       user_name: str, 
       years_on_ios: int,
       **optional_fields
   ) -> Dict[str, Any]:
       """
       Initialize migration with minimal required fields.
       Everything else can be added via update_migration_status.
       """
       with self.get_connection() as conn:
           migration_id = f"MIG-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
           
           # Start with minimal data
           conn.execute("""
               INSERT INTO migration_status (id, user_name, years_on_ios, started_at)
               VALUES (?, ?, ?, CURRENT_TIMESTAMP)
           """, (migration_id, user_name, years_on_ios))
           
           self.current_migration_id = migration_id
           return {"migration_id": migration_id, "status": "initialized"}
   ```

2. **MODIFY**: `get_family_members()` - Add filter support
   ```python
   async def get_family_members(self, filter_type: str = "all") -> List[Dict[str, Any]]:
       """
       Get family members with optional filtering.
       Filters: all, not_in_whatsapp, not_sharing_location, teen, no_phone
       """
       with self.get_connection() as conn:
           base_query = """
               SELECT fm.*, 
                      faa_wa.whatsapp_in_group,
                      faa_wa.status as whatsapp_status,
                      faa_maps.location_sharing_received
               FROM family_members fm
               LEFT JOIN family_app_adoption faa_wa 
                   ON fm.id = faa_wa.family_member_id 
                   AND faa_wa.app_name = 'WhatsApp'
               LEFT JOIN family_app_adoption faa_maps 
                   ON fm.id = faa_maps.family_member_id 
                   AND faa_maps.app_name = 'Google Maps'
               WHERE fm.migration_id = ?
           """
           
           # Add filter conditions
           if filter_type == "not_in_whatsapp":
               base_query += " AND (faa_wa.whatsapp_in_group IS FALSE OR faa_wa.whatsapp_in_group IS NULL)"
           elif filter_type == "not_sharing_location":
               base_query += " AND (faa_maps.location_sharing_received IS FALSE OR faa_maps.location_sharing_received IS NULL)"
           elif filter_type == "teen":
               base_query += " AND fm.age BETWEEN 13 AND 18"
           elif filter_type == "no_phone":
               base_query += " AND fm.phone IS NULL"
           
           results = conn.execute(base_query, (self.current_migration_id,)).fetchall()
           return [dict(row) for row in results]
   ```

3. **MODIFY**: `update_family_member_apps()` - Add details parameter
   ```python
   async def update_family_member_apps(
       self,
       member_name: str,
       app_name: str,
       status: str,
       details: Optional[Dict[str, Any]] = None
   ) -> Dict[str, Any]:
       """
       Update app adoption status with optional granular details.
       """
       with self.get_connection() as conn:
           # Get family member ID
           member = conn.execute(
               "SELECT id FROM family_members WHERE name = ? AND migration_id = ?",
               (member_name, self.current_migration_id)
           ).fetchone()
           
           if not member:
               return {"status": "error", "message": f"Family member {member_name} not found"}
           
           # Update basic status
           conn.execute("""
               INSERT OR REPLACE INTO family_app_adoption 
               (family_member_id, app_name, status, configured_at)
               VALUES (?, ?, ?, CASE WHEN ? = 'configured' THEN CURRENT_TIMESTAMP ELSE NULL END)
           """, (member['id'], app_name, status, status))
           
           # Update granular details if provided
           if details:
               update_fields = []
               values = []
               
               for field in ['whatsapp_in_group', 'location_sharing_sent', 
                           'location_sharing_received', 'venmo_card_activated', 'card_last_four']:
                   if field in details:
                       update_fields.append(f"{field} = ?")
                       values.append(details[field])
               
               if update_fields:
                   values.extend([member['id'], app_name])
                   conn.execute(
                       f"UPDATE family_app_adoption SET {', '.join(update_fields)} WHERE family_member_id = ? AND app_name = ?",
                       values
                   )
           
           return {"status": "success", "member": member_name, "app": app_name}
   ```

#### C. Methods to Convert to Internal (Remove from MCP exposure)

These methods remain in `migration_db.py` but are no longer exposed as MCP tools:

1. **INTERNAL**: `get_daily_summary(day_number)`
2. **INTERNAL**: `get_migration_overview()` - Modified to include whatsapp_group_name
   ```python
   async def get_migration_overview(self) -> Dict[str, Any]:
       """Internal method - includes whatsapp_group_name in response"""
       with self.get_connection() as conn:
           result = conn.execute(
               "SELECT * FROM migration_status WHERE id = ?",
               (self.current_migration_id,)
           ).fetchone()
           
           # Ensure whatsapp_group_name is included
           overview = dict(result) if result else {}
           overview["whatsapp_group_name"] = overview.get("whatsapp_group_name", "Family Group")
           return overview
   ```

3. **INTERNAL**: `get_family_service_summary()`

They are now called internally by `get_migration_status()`.

#### D. Additional Method Updates

1. **Note about set_whatsapp_group_name**: This is NOT a separate method. The whatsapp_group_name is now set via `update_migration_status()`:
   ```python
   # Instead of a separate set_whatsapp_group_name method, use:
   await db.update_migration_status(
       migration_id,
       whatsapp_group_name="Vetticaden Family"
   )
   ```

2. **Handler Update for get_family_members** (in server.py):
   ```python
   elif name == "get_family_members":
       filter_type = arguments.get("filter", "all")
       result = await db.get_family_members(filter_type)
       return [TextContent(text=json.dumps(result, indent=2))]
   ```

### ⏳ Step 8: Testing
- Test each day's flow independently
- Verify database state changes
- Confirm mobile-mcp instructions are dynamic
- Validate uber status tool returns complete data
- Ensure all 10 mobile-mcp flows work with database
- Test all 7 MCP tools work correctly
- Verify internal functions are not exposed

---

## 🎯 Final Summary: What Changes Where

### Files to Modify

1. **`mcp-tools/migration-state/server.py`**
   - REMOVE: 3 tool definitions (keep functions as internal)
   - ADD: 2 new tools (get_migration_status, update_migration_status)
   - MODIFY: 3 existing tools (initialize_migration, get_family_members, update_family_member_apps)
   - Result: 7 MCP tools total

2. **`shared/database/migration_db.py`**
   - ADD: 2 new methods (update_migration_status, check_photo_transfer_progress)
   - MODIFY: 3 existing methods (initialize_migration, get_family_members, update_family_member_apps)
   - INTERNAL: 3 methods no longer exposed via MCP

3. **`shared/database/schemas/migration_schema.sql`**
   - REMOVE: app_setup table (lines 168-186)
   - ADD: 5 columns to family_app_adoption
   - ADD: whatsapp_group_name to migration_status

4. **`docs/demo/demo-script-complete-final.md`**
   - UPDATE: Days 2-7 to use get_migration_status(day_number)
   - REMOVE: All references to internal-only tools
   - UPDATE: 8 update_migration_status calls

5. **`agent/instructions/ios2android-agent-instructions.md`**
   - ADD: Universal Status Check Pattern section
   - REMOVE: Parallel status call references
   - UPDATE: Tool selection guidelines

### Key Metrics
- **MCP Tools**: 10 → 7 (30% reduction)
- **Status Calls**: 4-5 → 1 per day (75% reduction)
- **update_migration_status calls**: 8 across 7 days
- **Mobile-MCP flows**: 10 database-driven patterns
- **Timeline**: ~10-12 hours remaining

---

**End of Implementation Plan**

This comprehensive plan ensures complete consistency, correct tool architecture, and full database-driven discovery patterns.