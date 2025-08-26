-- iOS to Android Migration Database Schema
-- Single unified schema optimized for 7-day demo flow
-- Created: 2025-08-25

-- Drop existing tables if they exist (for clean start)
DROP TABLE IF EXISTS venmo_setup;
DROP TABLE IF EXISTS daily_progress;
DROP TABLE IF EXISTS family_app_adoption;
DROP TABLE IF EXISTS app_setup;
DROP TABLE IF EXISTS photo_transfer;
DROP TABLE IF EXISTS family_members;
DROP TABLE IF EXISTS migration_status;

DROP VIEW IF EXISTS active_migration;
DROP VIEW IF EXISTS family_app_status;
DROP VIEW IF EXISTS migration_summary;

-- 1. Core migration tracking table
CREATE TABLE migration_status (
    id TEXT PRIMARY KEY DEFAULT ('MIG-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S')),
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
CREATE TABLE family_members (
    id INTEGER PRIMARY KEY,
    migration_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT, -- 'spouse', 'child'
    age INTEGER,
    email TEXT NOT NULL, -- Required for sending invites
    staying_on_ios BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('spouse', 'child'))
);

-- 3. Photo transfer tracking
CREATE TABLE photo_transfer (
    transfer_id TEXT PRIMARY KEY DEFAULT ('TRF-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S')),
    migration_id TEXT NOT NULL,
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
CREATE TABLE app_setup (
    id INTEGER PRIMARY KEY,
    migration_id TEXT NOT NULL,
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
CREATE TABLE family_app_adoption (
    id INTEGER PRIMARY KEY,
    family_member_id INTEGER NOT NULL,
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
CREATE TABLE daily_progress (
    id INTEGER PRIMARY KEY,
    migration_id TEXT NOT NULL,
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
CREATE TABLE venmo_setup (
    id INTEGER PRIMARY KEY,
    migration_id TEXT NOT NULL,
    family_member_id INTEGER NOT NULL,
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
CREATE INDEX idx_migration_status_phase ON migration_status(current_phase);
CREATE INDEX idx_family_members_migration ON family_members(migration_id);
CREATE INDEX idx_photo_transfer_migration ON photo_transfer(migration_id);
CREATE INDEX idx_app_setup_migration ON app_setup(migration_id);
CREATE INDEX idx_family_adoption_member ON family_app_adoption(family_member_id);
CREATE INDEX idx_daily_progress_migration ON daily_progress(migration_id, day_number);
CREATE INDEX idx_venmo_setup_migration ON venmo_setup(migration_id);

-- Create useful views for easy querying

-- Overall migration status view
CREATE VIEW migration_summary AS
SELECT 
    m.id,
    m.user_name,
    m.current_phase,
    m.overall_progress,
    pt.status as photo_status,
    CASE 
        WHEN pt.total_photos > 0 
        THEN pt.transferred_photos || '/' || pt.total_photos 
        ELSE '0/0' 
    END as photo_progress,
    COUNT(DISTINCT fm.id) as family_members,
    COUNT(DISTINCT CASE WHEN faa.status = 'configured' THEN faa.family_member_id END) as members_configured
FROM migration.migration_status m
LEFT JOIN migration.photo_transfer pt ON m.id = pt.migration_id
LEFT JOIN migration.family_members fm ON m.id = fm.migration_id
LEFT JOIN migration.family_app_adoption faa ON fm.id = faa.family_member_id
GROUP BY m.id, m.user_name, m.current_phase, m.overall_progress, pt.status, pt.transferred_photos, pt.total_photos;

-- Family member app status view
CREATE VIEW family_app_status AS
SELECT 
    fm.name,
    fm.email,
    MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.status END) as whatsapp,
    MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.status END) as maps,
    MAX(CASE WHEN faa.app_name = 'Venmo' THEN faa.status END) as venmo
FROM migration.family_members fm
LEFT JOIN migration.family_app_adoption faa ON fm.id = faa.family_member_id
GROUP BY fm.id, fm.name, fm.email;

-- Active migration view
CREATE VIEW active_migration AS
SELECT 
    m.*,
    pt.status as photo_transfer_status,
    pt.transferred_photos,
    pt.total_photos,
    COUNT(DISTINCT fm.id) as total_family_members
FROM migration.migration_status m
LEFT JOIN migration.photo_transfer pt ON m.id = pt.migration_id
LEFT JOIN migration.family_members fm ON m.id = fm.migration_id
WHERE m.completed_at IS NULL
GROUP BY m.id, m.user_name, m.source_device, m.target_device, m.years_on_ios, 
         m.photo_count, m.video_count, m.storage_gb, m.family_size, m.started_at,
         m.current_phase, m.overall_progress, m.completed_at,
         pt.status, pt.transferred_photos, pt.total_photos
ORDER BY m.started_at DESC
LIMIT 1;