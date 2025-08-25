# Migration State MCP Tools V2

## Overview

This document defines 10 new MCP tools to be added to the existing migration-state server. These tools provide the database operations needed to support the complete 7-day iOS to Android migration demo flow.

## Current State

The migration-state server currently has 6 basic tools. We need to ADD (not replace) 10 more sophisticated tools that align with the demo script and new database schema.

## Design Principles

1. **Raw JSON returns**: All tools return JSON for Claude to visualize
2. **Demo-aligned**: Each tool maps to specific demo script moments
3. **Progressive updates**: Tools build on each other through the 7-day flow
4. **Error resilient**: Graceful handling of missing data
5. **Natural language friendly**: Tool names and descriptions clear for Claude

## New Tools to Add

### 1. initialize_migration

**Purpose**: Start a new migration with user details and photo counts from iCloud check

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "user_name": {"type": "string"},
    "years_on_ios": {"type": "integer", "default": 18},
    "photo_count": {"type": "integer"},
    "video_count": {"type": "integer"},
    "storage_gb": {"type": "number"}
  },
  "required": ["user_name", "photo_count", "storage_gb"]
}
```

**Database Operations**:
```sql
-- Create migration record
INSERT INTO migration.migration_status 
(id, user_name, years_on_ios, photo_count, video_count, storage_gb, family_size, current_phase)
VALUES (?, ?, ?, ?, ?, ?, 0, 'initialization')

-- Initialize photo transfer record
INSERT INTO migration.photo_transfer
(migration_id, total_photos, total_videos, total_size_gb, status)
VALUES (?, ?, ?, ?, 'pending')

-- Initialize app setup records
INSERT INTO migration.app_setup (migration_id, app_name, category)
VALUES 
  (?, 'WhatsApp', 'messaging'),
  (?, 'Google Maps', 'location'),
  (?, 'Venmo', 'payment')
```

**Returns**:
```json
{
  "migration_id": "MIG-20250823-140523",
  "status": "initialized",
  "message": "Migration initialized for George",
  "photo_count": 58460,
  "video_count": 2418,
  "storage_gb": 383
}
```

**Demo Usage**: Day 1 - Called after web-automation.check_icloud_status returns photo counts

---

### 2. add_family_member

**Purpose**: Add a family member with their email for sending app invitations

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "name": {"type": "string"},
    "email": {"type": "string"},
    "role": {"type": "string", "enum": ["spouse", "child"]},
    "age": {"type": "integer", "description": "Optional, used for Venmo teen accounts"}
  },
  "required": ["name", "email"]
}
```

**Database Operations**:
```sql
-- Add family member
INSERT INTO migration.family_members
(migration_id, name, role, age, email)
VALUES (?, ?, ?, ?, ?)

-- Initialize app adoption records for this member
INSERT INTO migration.family_app_adoption
(family_member_id, app_name, status)
VALUES 
  (?, 'WhatsApp', 'not_started'),
  (?, 'Google Maps', 'not_started'),
  (?, 'Venmo', 'not_started')

-- If teen (13-17), create Venmo teen setup record
IF age BETWEEN 13 AND 17 THEN
  INSERT INTO migration.venmo_setup
  (migration_id, family_member_id, needs_teen_account)
  VALUES (?, ?, true)

-- Update family size
UPDATE migration.migration_status
SET family_size = (SELECT COUNT(*) + 1 FROM migration.family_members WHERE migration_id = ?)
WHERE id = ?
```

**Returns**:
```json
{
  "status": "added",
  "family_member": "Laila",
  "email": "laila.vetticaden@gmail.com",
  "role": "child",
  "age": 17,
  "needs_venmo_teen": true
}
```

**Demo Usage**: Day 1 - Called 4 times to add Jaisy, Laila, Ethan, and Maya

---

### 3. start_photo_transfer

**Purpose**: Record that Apple photo transfer has been initiated

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "transfer_initiated": {"type": "boolean", "default": true}
  }
}
```

**Database Operations**:
```sql
-- Update photo transfer status
UPDATE migration.photo_transfer
SET status = 'initiated',
    apple_transfer_initiated = CURRENT_TIMESTAMP,
    photos_visible_day = 4,
    estimated_completion_day = 7
WHERE migration_id = ?

-- Update migration phase
UPDATE migration.migration_status
SET current_phase = 'photo_transfer'
WHERE id = ?
```

**Returns**:
```json
{
  "status": "transfer_initiated",
  "message": "Apple photo transfer started",
  "estimated_completion": "5-7 days",
  "photos_visible": "Day 3-4"
}
```

**Demo Usage**: Day 1 - Called after user confirms transfer initiation

---

### 4. update_family_member_apps

**Purpose**: Update which apps a family member has installed/configured

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "family_member_name": {"type": "string"},
    "app_name": {"type": "string", "enum": ["WhatsApp", "Google Maps", "Venmo"]},
    "status": {"type": "string", "enum": ["not_started", "invited", "installed", "configured"]}
  },
  "required": ["family_member_name", "app_name", "status"]
}
```

**Database Operations**:
```sql
-- Update family member app status
UPDATE migration.family_app_adoption
SET status = ?,
    invitation_sent_at = CASE WHEN ? = 'invited' THEN CURRENT_TIMESTAMP ELSE invitation_sent_at END,
    installed_at = CASE WHEN ? = 'installed' THEN CURRENT_TIMESTAMP ELSE installed_at END,
    configured_at = CASE WHEN ? = 'configured' THEN CURRENT_TIMESTAMP ELSE configured_at END
WHERE family_member_id = (SELECT id FROM migration.family_members WHERE name = ?)
  AND app_name = ?

-- If WhatsApp configured, update app setup connected count
IF app_name = 'WhatsApp' AND status = 'configured' THEN
  UPDATE migration.app_setup
  SET family_members_connected = (
    SELECT COUNT(*) FROM migration.family_app_adoption
    WHERE app_name = 'WhatsApp' AND status = 'configured'
  )
  WHERE app_name = 'WhatsApp'
```

**Returns**:
```json
{
  "family_member": "Jaisy",
  "app": "WhatsApp",
  "previous_status": "invited",
  "new_status": "configured",
  "timestamp": "2025-08-25T10:30:00Z"
}
```

**Demo Usage**: 
- Day 1: Mark members as 'invited' when emails sent
- Day 3: Update to 'configured' when they join WhatsApp group

---

### 5. update_photo_progress

**Purpose**: Update photo transfer progress metrics

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "progress_percent": {"type": "number"},
    "photos_transferred": {"type": "integer"},
    "videos_transferred": {"type": "integer"},
    "size_transferred_gb": {"type": "number"}
  },
  "required": ["progress_percent"]
}
```

**Database Operations**:
```sql
-- Update photo transfer progress
UPDATE migration.photo_transfer
SET transferred_photos = COALESCE(?, transferred_photos),
    transferred_videos = COALESCE(?, transferred_videos),
    transferred_size_gb = COALESCE(?, transferred_size_gb),
    status = CASE 
      WHEN ? >= 100 THEN 'completed'
      WHEN ? > 0 THEN 'in_progress'
      ELSE status
    END,
    daily_transfer_rate = CASE 
      WHEN ? > 0 THEN ? / EXTRACT(DAY FROM (CURRENT_TIMESTAMP - apple_transfer_initiated))
      ELSE daily_transfer_rate
    END,
    last_checked_at = CURRENT_TIMESTAMP
WHERE migration_id = ?

-- Update overall progress
UPDATE migration.migration_status
SET overall_progress = (
  SELECT (
    (CASE WHEN pt.status = 'completed' THEN 40 ELSE pt.transferred_photos * 40 / pt.total_photos END) +
    (CASE WHEN ws.setup_status = 'completed' THEN 20 ELSE ws.family_members_connected * 20 / 4 END) +
    (CASE WHEN gm.setup_status = 'completed' THEN 20 ELSE gm.family_members_connected * 20 / 4 END) +
    (CASE WHEN vm.setup_status = 'completed' THEN 20 ELSE 0 END)
  )
  FROM migration.photo_transfer pt, 
       migration.app_setup ws, 
       migration.app_setup gm, 
       migration.app_setup vm
  WHERE pt.migration_id = ? 
    AND ws.migration_id = ? AND ws.app_name = 'WhatsApp'
    AND gm.migration_id = ? AND gm.app_name = 'Google Maps'
    AND vm.migration_id = ? AND vm.app_name = 'Venmo'
)
```

**Returns**:
```json
{
  "transfer_id": "TRF-20250823-180056",
  "progress_percent": 28,
  "photos_transferred": 16387,
  "total_photos": 58460,
  "estimated_completion": "4 more days",
  "daily_rate": 5462
}
```

**Demo Usage**: Day 4 - First update showing 28% progress when photos become visible

---

### 6. activate_venmo_card

**Purpose**: Record Venmo teen card activation

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "family_member_name": {"type": "string"},
    "card_last_four": {"type": "string"},
    "card_activated": {"type": "boolean", "default": true}
  },
  "required": ["family_member_name"]
}
```

**Database Operations**:
```sql
-- Update Venmo setup record
UPDATE migration.venmo_setup
SET card_arrived_at = CURRENT_TIMESTAMP,
    card_activated_at = CASE WHEN ? THEN CURRENT_TIMESTAMP ELSE NULL END,
    card_last_four = ?,
    setup_complete = ?
WHERE family_member_id = (SELECT id FROM migration.family_members WHERE name = ?)

-- Update family member app adoption
UPDATE migration.family_app_adoption
SET status = 'configured',
    configured_at = CURRENT_TIMESTAMP
WHERE family_member_id = (SELECT id FROM migration.family_members WHERE name = ?)
  AND app_name = 'Venmo'

-- Check if all Venmo cards activated
UPDATE migration.app_setup
SET setup_status = CASE 
  WHEN (SELECT COUNT(*) FROM migration.venmo_setup WHERE setup_complete = false) = 0 
  THEN 'completed' 
  ELSE 'in_progress' 
END
WHERE app_name = 'Venmo'
```

**Returns**:
```json
{
  "family_member": "Laila",
  "card_activated": true,
  "card_last_four": "1234",
  "venmo_status": "configured",
  "message": "Teen card activated successfully"
}
```

**Demo Usage**: Day 5 - Called for Laila and Ethan when activating their cards

---

### 7. get_daily_summary

**Purpose**: Get migration status summary for a specific day

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "day_number": {"type": "integer", "minimum": 1, "maximum": 7}
  },
  "required": ["day_number"]
}
```

**Database Operations**:
```sql
-- Get or create daily progress record
INSERT OR REPLACE INTO migration.daily_progress
(migration_id, day_number, date, photos_transferred, videos_transferred, 
 size_transferred_gb, whatsapp_members_connected, maps_members_sharing, 
 venmo_members_active, key_milestone)
SELECT 
  m.id,
  ?,
  CURRENT_DATE,
  pt.transferred_photos,
  pt.transferred_videos,
  pt.transferred_size_gb,
  ws.family_members_connected,
  gm.family_members_connected,
  vm.family_members_connected,
  CASE ?
    WHEN 1 THEN 'Migration initialized, photo transfer started'
    WHEN 3 THEN 'WhatsApp group complete, family connecting'
    WHEN 4 THEN 'Photos appearing in Google Photos!'
    WHEN 5 THEN 'Venmo teen cards activated'
    WHEN 6 THEN 'Near completion, final setup'
    WHEN 7 THEN 'Migration complete!'
  END
FROM migration.migration_status m
LEFT JOIN migration.photo_transfer pt ON m.id = pt.migration_id
LEFT JOIN migration.app_setup ws ON m.id = ws.migration_id AND ws.app_name = 'WhatsApp'
LEFT JOIN migration.app_setup gm ON m.id = gm.migration_id AND gm.app_name = 'Google Maps'
LEFT JOIN migration.app_setup vm ON m.id = vm.migration_id AND vm.app_name = 'Venmo'
WHERE m.id = (SELECT id FROM migration.migration_status ORDER BY started_at DESC LIMIT 1)
```

**Returns** (Day-specific):

Day 3 Example:
```json
{
  "day": 3,
  "date": "2025-08-25",
  "photo_status": {
    "status": "in_progress",
    "progress": 0,
    "message": "Transfer running, photos not visible yet"
  },
  "whatsapp_status": {
    "invited": ["Jaisy", "Ethan"],
    "configured": ["Laila", "Maya"],
    "action_needed": "Waiting for Jaisy and Ethan to install"
  },
  "location_sharing": {
    "sharing_active": 1,
    "pending": 3
  },
  "key_milestone": "WhatsApp group partially complete",
  "next_steps": ["Check if Jaisy and Ethan installed WhatsApp", "Add them to family group"]
}
```

Day 4 Example:
```json
{
  "day": 4,
  "date": "2025-08-26",
  "photo_status": {
    "status": "in_progress",
    "progress": 28,
    "photos_visible": 16387,
    "message": "Photos starting to appear!"
  },
  "whatsapp_status": {
    "configured": ["Jaisy", "Laila", "Ethan", "Maya"],
    "message": "Family group complete"
  },
  "key_milestone": "Photos appearing in Google Photos!",
  "celebration": true
}
```

**Demo Usage**: Called on Days 2, 3, 4, 5, 6, 7 to show progress

---

### 8. get_migration_status

**Purpose**: Get current overall migration status

**Input Schema**:
```json
{
  "type": "object",
  "properties": {}
}
```

**Database Operations**:
```sql
-- Comprehensive status query
SELECT 
  m.*,
  pt.status as photo_status,
  pt.transferred_photos,
  pt.total_photos,
  pt.transferred_size_gb,
  pt.total_size_gb,
  (SELECT COUNT(*) FROM migration.family_members WHERE migration_id = m.id) as family_count,
  (SELECT COUNT(*) FROM migration.family_app_adoption WHERE status = 'configured') as apps_configured,
  (SELECT COUNT(*) FROM migration.venmo_setup WHERE setup_complete = true) as venmo_cards_active
FROM migration.migration_status m
LEFT JOIN migration.photo_transfer pt ON m.id = pt.migration_id
WHERE m.id = (SELECT id FROM migration.migration_status ORDER BY started_at DESC LIMIT 1)
```

**Returns**:
```json
{
  "migration_id": "MIG-20250823-140523",
  "user": "George",
  "phase": "family_setup",
  "overall_progress": 65,
  "started": "2025-08-23T14:05:23Z",
  "days_elapsed": 4,
  "photo_transfer": {
    "status": "in_progress",
    "progress": "16387/58460 photos",
    "size": "100/383 GB"
  },
  "family_status": {
    "total_members": 4,
    "whatsapp_connected": 4,
    "maps_sharing": 2,
    "venmo_active": 0
  },
  "estimated_completion": "3 more days"
}
```

**Demo Usage**: Can be called anytime to get overall status

---

### 9. create_action_item

**Purpose**: Create a follow-up task (like sending email invites)

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "action_type": {"type": "string"},
    "description": {"type": "string"},
    "target_member": {"type": "string"}
  },
  "required": ["action_type", "description"]
}
```

**Database Operations**:
```sql
-- This tool is simplified - action items are handled directly by other tools
-- Kept for compatibility but most actions are now automatic
-- Example: Email invites are sent via mobile-mcp, not queued here
```

**Returns**:
```json
{
  "message": "Action handled directly by mobile-mcp",
  "action": "Send WhatsApp invite to Jaisy",
  "method": "email"
}
```

**Demo Usage**: Referenced but not heavily used - actions are direct

---

### 10. generate_migration_report

**Purpose**: Generate final migration completion report

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "format": {"type": "string", "enum": ["summary", "detailed"], "default": "summary"}
  }
}
```

**Database Operations**:
```sql
-- Comprehensive final report query
SELECT 
  m.user_name,
  m.years_on_ios,
  m.started_at,
  m.completed_at,
  EXTRACT(DAY FROM (m.completed_at - m.started_at)) as total_days,
  pt.total_photos,
  pt.total_videos,
  pt.total_size_gb,
  COUNT(DISTINCT fm.id) as family_members,
  COUNT(DISTINCT CASE WHEN faa.app_name = 'WhatsApp' AND faa.status = 'configured' THEN faa.family_member_id END) as whatsapp_members,
  COUNT(DISTINCT CASE WHEN faa.app_name = 'Google Maps' AND faa.status = 'configured' THEN faa.family_member_id END) as maps_members,
  COUNT(DISTINCT CASE WHEN faa.app_name = 'Venmo' AND faa.status = 'configured' THEN faa.family_member_id END) as venmo_members
FROM migration.migration_status m
JOIN migration.photo_transfer pt ON m.id = pt.migration_id
JOIN migration.family_members fm ON m.id = fm.migration_id
LEFT JOIN migration.family_app_adoption faa ON fm.id = faa.family_member_id
WHERE m.id = ?
GROUP BY m.id
```

**Returns**:
```json
{
  "🎉": "MIGRATION COMPLETE!",
  "summary": {
    "user": "George",
    "duration": "7 days",
    "freed_from": "18 years of iOS"
  },
  "achievements": {
    "photos": "✅ 58,460 photos transferred",
    "videos": "✅ 2,418 videos transferred",
    "storage": "✅ 383GB migrated to Google Photos",
    "family": "✅ 4/4 family members connected"
  },
  "apps_configured": {
    "WhatsApp": "✅ Family group with 4 members",
    "Google Maps": "✅ Location sharing active",
    "Venmo": "✅ Teen cards activated"
  },
  "data_integrity": {
    "photos_matched": true,
    "zero_data_loss": true,
    "apple_confirmation": "received"
  },
  "celebration_message": "Welcome to Android! Your family stays connected across platforms."
}
```

**Demo Usage**: Day 7 - Final celebration dashboard

## Implementation Notes

### Tool Execution Order

Typical Day 1 sequence:
1. `initialize_migration` - Set up core records
2. `add_family_member` x4 - Add family details
3. `start_photo_transfer` - Begin Apple transfer
4. `update_family_member_apps` - Track WhatsApp invites
5. `get_daily_summary` - End of day status

### Error Handling

All tools should:
- Check for active migration before operations
- Handle missing family members gracefully
- Return meaningful error messages in JSON format
- Never throw exceptions that break MCP communication

### State Management

- Tools read/write to shared DuckDB database
- No direct tool-to-tool communication
- Claude orchestrates all tool calls
- Database is single source of truth

### Demo-Specific Logic

Day-specific behaviors:
- **Day 1-3**: Photos show 0% (not visible yet)
- **Day 4**: Photos suddenly show ~28% progress
- **Day 5**: Venmo cards arrive
- **Day 7**: Apple email confirmation checked

## Testing Requirements

Each tool should be tested for:
1. **Happy path**: Normal demo flow
2. **Missing data**: Graceful handling of nulls
3. **Idempotency**: Multiple calls don't break state
4. **JSON format**: Valid JSON returns
5. **Demo alignment**: Matches expected demo day behavior

## Success Criteria

- ✅ All 10 tools successfully added to migration-state server
- ✅ Tools return valid JSON for Claude visualization
- ✅ Database operations match schema v2
- ✅ Demo flow executes correctly day by day
- ✅ Error handling prevents crashes
- ✅ Natural language descriptions clear for Claude