# MCP Tools Reference Guide

## Overview
This document provides detailed reference information for all MCP tools available to the iOS2Android Migration Agent. Use this as a technical reference when orchestrating the migration process.

## web-automation Tools (5 tools)

### 1. check_icloud_status
**When to use**: Day 1, before starting any migration
**Purpose**: Retrieve photo/video counts and storage size from iCloud
**Returns**: Dictionary with photo_count, video_count, storage_gb, album_count
**Important**: Must be called before initialize_migration to get accurate counts

### 2. start_photo_transfer
**When to use**: Day 1, after initializing migration
**Purpose**: Initiate Apple's official photo transfer service
**Returns**: transfer_id (critical - store for all future operations)
**Notes**: Transfer takes 5-7 days for large libraries

### 3. check_photo_transfer_progress
**When to use**: Days 4-6 for progress updates
**Purpose**: Monitor transfer status via Google Dashboard
**Parameters**: transfer_id from start_photo_transfer
**Returns**: Progress percentage, items transferred, estimated completion

### 4. check_photo_transfer_email
**When to use**: Days 6-7 when expecting completion
**Purpose**: Check Gmail for Apple's completion notification
**Parameters**: transfer_id
**Returns**: Email found status and completion confirmation

### 5. verify_photo_transfer_complete
**When to use**: Day 7 after receiving completion email
**Purpose**: Final verification of successful transfer
**Parameters**: transfer_id
**Returns**: Detailed transfer statistics and success confirmation

## migration-state Tools (16 tools)

### Core Migration Tools

#### initialize_migration
**When to use**: Day 1, after check_icloud_status
**Purpose**: Create new migration record in database
**Parameters**: user_name, photo_count, video_count, storage_gb
**Creates**: Main migration record with unique migration_id

#### update_migration_progress
**When to use**: Days 4-7 as photos transfer
**Purpose**: Update transfer percentages
**Parameters**: photos_transferred, videos_transferred, storage_transferred_gb
**Updates**: Progress metrics and last_updated timestamp

#### complete_migration
**When to use**: Day 7 after verification
**Purpose**: Mark migration as successfully completed
**Effect**: Sets status to 'completed', end_date to current time

### Family Management Tools

#### add_family_member
**When to use**: Day 1 during family setup
**Purpose**: Register family member in system
**Parameters**: name, email, phone (optional), device_type
**Returns**: family_member_id for tracking

#### update_family_member_apps
**When to use**: Days 1-3 as apps are installed
**Purpose**: Track app adoption per family member
**Parameters**: family_member_name, app_name, status (invited/installed/configured)
**Statuses**: 
- invited: Installation request sent
- installed: App downloaded
- configured: Fully set up

#### get_family_status
**When to use**: Daily to check adoption progress
**Purpose**: Overview of all family members and their app status
**Returns**: Table of family members with app installation status

### App Tracking Tools

#### track_app_installation
**When to use**: As each app is installed on Android
**Purpose**: Record app installations
**Parameters**: app_name, package_name, category
**Categories**: messaging, location, payment, photos, productivity

#### update_app_configuration
**When to use**: After app setup/login
**Purpose**: Track configuration status
**Parameters**: app_name, configuration_details, is_configured
**Example details**: "Logged in with Google account"

### Event Logging Tools

#### log_migration_event
**When to use**: For any significant event
**Purpose**: Create audit trail of migration process
**Parameters**: event_type, description, metadata
**Event types**: info, warning, error, success

#### add_migration_note
**When to use**: For important observations
**Purpose**: Add human-readable notes
**Parameters**: note_content
**Example**: "User concerned about WhatsApp adoption"

### Status and Reporting Tools

#### get_migration_status
**When to use**: For current state check
**Purpose**: Get current migration snapshot
**Returns**: Status, progress percentages, timeline

#### get_daily_summary
**When to use**: Each day for updates
**Purpose**: Day-specific progress report
**Parameters**: day_number (1-7)
**Returns**: Formatted summary for that day

#### get_pending_items
**When to use**: To identify remaining tasks
**Purpose**: List incomplete migration items
**Returns**: Apps to install, family members to onboard

#### get_migration_statistics
**When to use**: For detailed metrics
**Purpose**: Comprehensive statistics
**Returns**: JSON with all migration metrics

#### get_migration_overview
**When to use**: Day 6-7 for final summary
**Purpose**: High-level migration overview
**Returns**: Overall progress and status

#### generate_migration_report
**When to use**: Day 7 for celebration
**Purpose**: Create final success report
**Returns**: Formatted celebration message with emojis

## mobile-mcp Tools (Natural Language)

### Important: No Direct Tool Calls
mobile-mcp operates entirely through natural language commands. Never call specific functions. Instead, describe what you want to do in plain English.

### Common Commands

#### App Installation
```
"Open Play Store"
"Search for [app name]"
"Click on the first search result"
"Tap the Install button"
"Wait for installation to complete"
```

#### App Configuration
```
"Open [app name]"
"Tap Continue"
"Enter phone number: [number]"
"Tap Next"
"Enter verification code"
```

#### WhatsApp Group Creation
```
"Open WhatsApp"
"Tap the three dots menu"
"Select New group"
"Search for [contact name]"
"Select [contact name]"
"Tap the green arrow"
"Type '[group name]' as the group name"
"Tap the green checkmark"
```

#### Location Sharing Setup
```
"Open Google Maps"
"Tap your profile picture"
"Select Location sharing"
"Tap Share location"
"Choose Until you turn this off"
"Search for [contact]"
"Select [contact]"
"Tap Share"
```

#### Venmo Configuration
```
"Open Venmo"
"Tap the menu icon"
"Select Teen accounts"
"Tap on [teen name]'s account"
"Tap Activate card"
"Enter the last 4 digits of the card"
```

## Tool Coordination Patterns

### Sequential Operations
Some operations must happen in order:
1. check_icloud_status → initialize_migration → start_photo_transfer
2. check_photo_transfer_email → verify_photo_transfer_complete → complete_migration
3. add_family_member → update_family_member_apps → get_family_status

### Parallel Operations
Some operations can happen simultaneously:
- Photo transfer while setting up family apps
- Multiple family member invitations
- App installations while photos transfer

### State Dependencies
- Must have migration_id before any updates
- Must have family_member_id before tracking their apps
- Must have transfer_id before checking progress

## Error Handling

### Tool Failures
- All tools return structured errors
- Log errors with log_migration_event
- Provide manual fallback instructions
- Track issues for follow-up

### State Consistency
- Database maintains ACID properties
- All updates are atomic
- State persists across sessions
- Recovery possible from any point

## Best Practices

1. **Always Initialize First**: Run initialize_migration before any other state updates
2. **Store IDs**: Keep migration_id, transfer_id, family_member_ids for reference
3. **Regular Progress Updates**: Update progress on days 4, 5, 6, 7
4. **Log Significant Events**: Use log_migration_event for important milestones
5. **Natural Language for Mobile**: Never expose technical commands to user
6. **Progressive Disclosure**: Only ask for information when needed
7. **Verify Before Completing**: Always verify_photo_transfer_complete before complete_migration