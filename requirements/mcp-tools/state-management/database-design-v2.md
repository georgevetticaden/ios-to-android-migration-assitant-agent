# Database Design V2 - Simplified Schema

## Overview

This document defines the new simplified database schema for the iOS to Android Migration Assistant, replacing the current over-engineered 4-schema design with a single unified schema optimized for the demo flow.

## Current Problems with Existing Schema

The current implementation has significant issues:

- **Over-engineered**: 4 separate schemas (family_services, migration_core, photo_migration, whatsapp_migration) with 17 tables
- **Unnecessary complexity**: Tables like parental_controls, life360_migration, family_calendars that aren't used in the demo
- **Cross-schema limitations**: DuckDB has issues with foreign keys across schemas
- **Not aligned with demo**: Many tables don't map to actual demo requirements
- **Redundant tracking**: Multiple tables tracking similar information

## New Design: Single Unified Schema

### Design Principles

1. **Single schema**: All tables under `migration` schema
2. **Demo-focused**: Only tables that directly support the 7-day demo flow
3. **Simplified relationships**: Clear foreign keys within single schema
4. **Progressive data capture**: Data populated as demo progresses
5. **Natural language aligned**: Structure supports MCP tool interactions

### Complete Schema SQL

```sql
-- Drop all existing schemas and start fresh
DROP SCHEMA IF EXISTS photo_migration CASCADE;
DROP SCHEMA IF EXISTS family_services CASCADE;
DROP SCHEMA IF EXISTS migration_core CASCADE;
DROP SCHEMA IF EXISTS whatsapp_migration CASCADE;
DROP SCHEMA IF EXISTS migration CASCADE;

-- Create single unified schema
CREATE SCHEMA IF NOT EXISTS migration;

-- 1. Core migration tracking table
CREATE TABLE migration.migration_status (
    id TEXT PRIMARY KEY DEFAULT ('MIG-' || strftime('%Y%m%d-%H%M%S', 'now')),
    user_name TEXT NOT NULL,
    source_device TEXT DEFAULT 'iPhone',
    target_device TEXT DEFAULT 'Galaxy Z Fold 7',
    years_on_ios INTEGER,
    photo_count INTEGER,
    video_count INTEGER,
    storage_gb DECIMAL(10,2),
    family_size INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_phase TEXT DEFAULT 'initialization',
    overall_progress INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    CONSTRAINT valid_progress CHECK (overall_progress BETWEEN 0 AND 100),
    CONSTRAINT valid_phase CHECK (current_phase IN ('initialization', 'photo_transfer', 'family_setup', 'validation', 'completed'))
);

-- 2. Family members table
CREATE TABLE migration.family_members (
    id INTEGER PRIMARY KEY,
    migration_id TEXT REFERENCES migration.migration_status(id),
    name TEXT NOT NULL,
    role TEXT, -- 'spouse', 'child'
    age INTEGER,
    email TEXT NOT NULL, -- Required for sending invites
    staying_on_ios BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('spouse', 'child'))
);

-- 3. Photo transfer tracking
CREATE TABLE migration.photo_transfer (
    transfer_id TEXT PRIMARY KEY DEFAULT ('TRF-' || strftime('%Y%m%d-%H%M%S', 'now')),
    migration_id TEXT REFERENCES migration.migration_status(id),
    total_photos INTEGER,
    total_videos INTEGER,
    total_size_gb DECIMAL(10,2),
    transferred_photos INTEGER DEFAULT 0,
    transferred_videos INTEGER DEFAULT 0,
    transferred_size_gb DECIMAL(10,2) DEFAULT 0,
    status TEXT DEFAULT 'pending',
    apple_transfer_initiated TIMESTAMP,
    apple_confirmation_email_received TIMESTAMP,
    photos_visible_day INTEGER, -- Day when photos start appearing (typically 3-4)
    estimated_completion_day INTEGER DEFAULT 7,
    daily_transfer_rate INTEGER,
    last_checked_at TIMESTAMP,
    CONSTRAINT valid_status CHECK (status IN ('pending', 'initiated', 'in_progress', 'completed'))
);

-- 4. App setup tracking (WhatsApp, Google Maps, Venmo)
CREATE TABLE migration.app_setup (
    id INTEGER PRIMARY KEY,
    migration_id TEXT REFERENCES migration.migration_status(id),
    app_name TEXT NOT NULL,
    category TEXT, -- 'messaging', 'location', 'payment'
    setup_status TEXT DEFAULT 'pending',
    group_created BOOLEAN DEFAULT false, -- For WhatsApp
    invitations_sent INTEGER DEFAULT 0,
    family_members_connected INTEGER DEFAULT 0,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    notes TEXT,
    UNIQUE(migration_id, app_name),
    CONSTRAINT valid_app CHECK (app_name IN ('WhatsApp', 'Google Maps', 'Venmo')),
    CONSTRAINT valid_category CHECK (category IN ('messaging', 'location', 'payment')),
    CONSTRAINT valid_status CHECK (setup_status IN ('pending', 'in_progress', 'completed'))
);

-- 5. Family member app adoption
CREATE TABLE migration.family_app_adoption (
    id INTEGER PRIMARY KEY,
    family_member_id INTEGER REFERENCES migration.family_members(id),
    app_name TEXT,
    status TEXT DEFAULT 'not_started',
    invitation_sent_at TIMESTAMP,
    invitation_method TEXT DEFAULT 'email',
    installed_at TIMESTAMP,
    configured_at TIMESTAMP,
    UNIQUE(family_member_id, app_name),
    CONSTRAINT valid_app CHECK (app_name IN ('WhatsApp', 'Google Maps', 'Venmo')),
    CONSTRAINT valid_status CHECK (status IN ('not_started', 'invited', 'installed', 'configured'))
);

-- 6. Daily progress snapshots for demo timeline
CREATE TABLE migration.daily_progress (
    id INTEGER PRIMARY KEY,
    migration_id TEXT REFERENCES migration.migration_status(id),
    day_number INTEGER NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    photos_transferred INTEGER,
    videos_transferred INTEGER,
    size_transferred_gb DECIMAL(10,2),
    whatsapp_members_connected INTEGER,
    maps_members_sharing INTEGER,
    venmo_members_active INTEGER,
    key_milestone TEXT, -- Description of main achievement
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(migration_id, day_number)
);

-- 7. Venmo teen account setup (specific to demo)
CREATE TABLE migration.venmo_setup (
    id INTEGER PRIMARY KEY,
    migration_id TEXT REFERENCES migration.migration_status(id),
    family_member_id INTEGER REFERENCES migration.family_members(id),
    needs_teen_account BOOLEAN DEFAULT false,
    account_created_at TIMESTAMP,
    card_ordered_at TIMESTAMP,
    card_arrived_at TIMESTAMP,
    card_activated_at TIMESTAMP,
    card_last_four TEXT,
    setup_complete BOOLEAN DEFAULT false,
    UNIQUE(family_member_id)
);

-- Create indexes for performance
CREATE INDEX idx_migration_status_phase ON migration.migration_status(current_phase);
CREATE INDEX idx_family_members_migration ON migration.family_members(migration_id);
CREATE INDEX idx_photo_transfer_migration ON migration.photo_transfer(migration_id);
CREATE INDEX idx_app_setup_migration ON migration.app_setup(migration_id);
CREATE INDEX idx_family_adoption_member ON migration.family_app_adoption(family_member_id);
CREATE INDEX idx_daily_progress_migration ON migration.daily_progress(migration_id, day_number);
CREATE INDEX idx_venmo_setup_migration ON migration.venmo_setup(migration_id);
```

## Table Purposes and Demo Alignment

### 1. migration_status
- **Purpose**: Core tracking for entire migration
- **Demo Usage**: Created on Day 1 when user provides initial details
- **Key Fields**: 
  - `current_phase`: Tracks which stage of migration
  - `overall_progress`: 0-100% for visualization
  - `family_size`: Updated as family members added

### 2. family_members
- **Purpose**: Store family member details for coordination
- **Demo Usage**: Populated when user provides names and emails for WhatsApp setup
- **Key Fields**:
  - `email`: REQUIRED for sending app invitations
  - `role`: Determines if teen account needed for Venmo
  - `age`: Used for Venmo teen account logic

### 3. photo_transfer
- **Purpose**: Track Apple to Google Photos migration
- **Demo Usage**: 
  - Day 1: Record initiated
  - Day 3-4: Photos become visible
  - Day 7: Completion confirmed
- **Key Fields**:
  - `photos_visible_day`: Set to 4 (matches reality)
  - `status`: Progressive states through transfer

### 4. app_setup
- **Purpose**: Track setup of each cross-platform app
- **Demo Usage**: One record each for WhatsApp, Google Maps, Venmo
- **Key Fields**:
  - `family_members_connected`: Increments as family joins
  - `group_created`: WhatsApp-specific flag

### 5. family_app_adoption
- **Purpose**: Track individual family member app status
- **Demo Usage**: Shows who has/hasn't installed each app
- **Key Fields**:
  - `status`: Progressive (not_started → invited → installed → configured)
  - Timestamps for each stage

### 6. daily_progress
- **Purpose**: Snapshot for demo day visualization
- **Demo Usage**: Created by get_daily_summary() tool
- **Key Fields**:
  - `key_milestone`: Human-readable achievement
  - Metrics for each app's adoption

### 7. venmo_setup
- **Purpose**: Track Venmo teen card process
- **Demo Usage**:
  - Day 1: Records created for teens
  - Day 5: Cards arrive
  - Day 5: Activation tracked

## Data Flow by Demo Day

### Day 1: Initialization
```sql
-- Created by initialize_migration()
INSERT INTO migration.migration_status (user_name, years_on_ios, photo_count, storage_gb)
INSERT INTO migration.photo_transfer (migration_id, total_photos, total_videos, total_size_gb)
INSERT INTO migration.app_setup (migration_id, app_name, category) -- 3 records

-- Created by add_family_member() x4
INSERT INTO migration.family_members (migration_id, name, email, role, age)
INSERT INTO migration.family_app_adoption (family_member_id, app_name) -- 3 apps per member

-- Created by start_photo_transfer()
UPDATE migration.photo_transfer SET status = 'initiated', apple_transfer_initiated = NOW()
```

### Day 3: WhatsApp Adoption
```sql
-- Updated by update_family_member_apps()
UPDATE migration.family_app_adoption 
SET status = 'configured', configured_at = NOW()
WHERE app_name = 'WhatsApp'

-- Updated app setup status
UPDATE migration.app_setup 
SET family_members_connected = 4, setup_status = 'completed'
WHERE app_name = 'WhatsApp'
```

### Day 4: Photos Appear
```sql
-- Updated by update_photo_progress()
UPDATE migration.photo_transfer 
SET transferred_photos = 16000, transferred_size_gb = 100, status = 'in_progress'

-- Daily snapshot created
INSERT INTO migration.daily_progress (migration_id, day_number, photos_transferred, key_milestone)
VALUES (?, 4, 16000, 'Photos starting to appear in Google Photos')
```

### Day 5: Venmo Cards
```sql
-- Updated by activate_venmo_card()
UPDATE migration.venmo_setup 
SET card_arrived_at = NOW(), card_activated_at = NOW(), card_last_four = '1234'
WHERE family_member_id = ?
```

### Day 7: Completion
```sql
-- Final updates
UPDATE migration.photo_transfer 
SET status = 'completed', apple_confirmation_email_received = NOW()

UPDATE migration.migration_status 
SET current_phase = 'completed', overall_progress = 100, completed_at = NOW()
```

## Views for Easy Querying

```sql
-- Overall migration status view
CREATE VIEW migration.migration_summary AS
SELECT 
    m.id,
    m.user_name,
    m.current_phase,
    m.overall_progress,
    pt.status as photo_status,
    pt.transferred_photos || '/' || pt.total_photos as photo_progress,
    COUNT(DISTINCT fm.id) as family_members,
    COUNT(DISTINCT CASE WHEN faa.status = 'configured' THEN faa.family_member_id END) as members_configured
FROM migration.migration_status m
LEFT JOIN migration.photo_transfer pt ON m.id = pt.migration_id
LEFT JOIN migration.family_members fm ON m.id = fm.migration_id
LEFT JOIN migration.family_app_adoption faa ON fm.id = faa.family_member_id
GROUP BY m.id, m.user_name, m.current_phase, m.overall_progress, pt.status, pt.transferred_photos, pt.total_photos;

-- Family member app status view
CREATE VIEW migration.family_app_status AS
SELECT 
    fm.name,
    fm.email,
    MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.status END) as whatsapp,
    MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.status END) as maps,
    MAX(CASE WHEN faa.app_name = 'Venmo' THEN faa.status END) as venmo
FROM migration.family_members fm
LEFT JOIN migration.family_app_adoption faa ON fm.id = faa.family_member_id
GROUP BY fm.id, fm.name, fm.email;
```

## Migration from Current Schema

Since this is a new implementation with no production data to preserve (except the active photo transfer), the migration is straightforward:

1. **Backup current database** (if needed)
2. **Run the schema creation SQL** above
3. **No data migration needed** - the demo flow will populate all data through MCP tools

## Key Improvements Over Current Design

1. **Simplicity**: 7 tables vs 17 tables
2. **Single schema**: No cross-schema foreign key issues
3. **Demo-aligned**: Every table has a clear purpose in the demo
4. **Progressive population**: Data added naturally as demo progresses
5. **Clean relationships**: All foreign keys work within single schema
6. **Focused scope**: Only tracks what's shown in demo (no Life360, no parental controls)
7. **Email-centric**: Family coordination via email, not phone numbers

## Success Criteria

- ✅ Database supports complete 7-day demo flow
- ✅ All MCP tools can read/write successfully
- ✅ Foreign keys maintain referential integrity
- ✅ Views provide easy status summaries
- ✅ No unused or over-engineered tables
- ✅ Natural progression through demo days