-- iOS to Android Migration Database Schema v2.0
-- Optimized for video support and storage-based tracking
-- Created: 2025-08-26

-- Drop all existing tables for fresh start
DROP TABLE IF EXISTS storage_snapshots;
DROP TABLE IF EXISTS venmo_setup;
DROP TABLE IF EXISTS daily_progress;
DROP TABLE IF EXISTS family_app_adoption;
DROP TABLE IF EXISTS app_setup;
DROP TABLE IF EXISTS media_transfer;
DROP TABLE IF EXISTS photo_transfer;
DROP TABLE IF EXISTS family_members;
DROP TABLE IF EXISTS migration_status;

DROP VIEW IF EXISTS active_migration;
DROP VIEW IF EXISTS family_app_status;
DROP VIEW IF EXISTS migration_summary;
DROP VIEW IF EXISTS daily_progress_summary;

-- 1. Core migration tracking with storage baselines
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
    icloud_photo_storage_gb REAL,  -- Estimated 70% of total
    icloud_video_storage_gb REAL,  -- Estimated 30% of total
    album_count INTEGER,
    
    -- Google baseline metrics (from Google One)
    google_storage_total_gb REAL DEFAULT 2048,  -- 2TB plan
    google_photos_baseline_gb REAL,  -- Before transfer starts
    google_drive_baseline_gb REAL,
    gmail_baseline_gb REAL,
    
    -- Migration tracking
    family_size INTEGER,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    current_phase TEXT DEFAULT 'initialization',
    overall_progress INTEGER DEFAULT 0,
    completed_at TIMESTAMP,
    
    CONSTRAINT valid_progress CHECK (overall_progress BETWEEN 0 AND 100),
    CONSTRAINT valid_phase CHECK (current_phase IN ('initialization', 'media_transfer', 'family_setup', 'validation', 'completed'))
);

-- 2. Media transfer tracking (photos AND videos)
CREATE TABLE media_transfer (
    transfer_id TEXT PRIMARY KEY DEFAULT ('TRF-' || strftime(CURRENT_TIMESTAMP, '%Y%m%d-%H%M%S')),
    migration_id TEXT NOT NULL,
    
    -- Apple transfer IDs
    photo_transfer_id TEXT,  -- Apple's ID for photo transfer
    video_transfer_id TEXT,  -- Apple's ID for video transfer
    
    -- Total counts to transfer
    total_photos INTEGER,
    total_videos INTEGER,
    total_size_gb REAL,
    
    -- Progress tracking (calculated from storage)
    transferred_photos INTEGER DEFAULT 0,
    transferred_videos INTEGER DEFAULT 0,
    transferred_size_gb REAL DEFAULT 0,
    
    -- Status tracking
    photo_status TEXT DEFAULT 'pending',
    video_status TEXT DEFAULT 'pending',
    overall_status TEXT DEFAULT 'pending',
    
    -- Timestamps
    apple_transfer_initiated TIMESTAMP,
    photo_start_email_received TIMESTAMP,
    video_start_email_received TIMESTAMP,
    photo_complete_email_received TIMESTAMP,
    video_complete_email_received TIMESTAMP,
    
    -- Progress milestones
    photos_visible_day INTEGER,  -- Typically day 4
    estimated_completion_day INTEGER DEFAULT 7,
    last_progress_check TIMESTAMP,
    
    CONSTRAINT valid_photo_status CHECK (photo_status IN ('pending', 'initiated', 'in_progress', 'completed', 'failed')),
    CONSTRAINT valid_video_status CHECK (video_status IN ('pending', 'initiated', 'in_progress', 'completed', 'failed')),
    CONSTRAINT valid_overall_status CHECK (overall_status IN ('pending', 'initiated', 'in_progress', 'completed', 'partial_failure'))
);

-- 3. Storage tracking for progress calculation
CREATE SEQUENCE IF NOT EXISTS storage_snapshots_seq;
CREATE TABLE storage_snapshots (
    id INTEGER PRIMARY KEY DEFAULT nextval('storage_snapshots_seq'),
    migration_id TEXT NOT NULL,
    snapshot_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    day_number INTEGER,
    
    -- Google One storage breakdown
    google_photos_gb REAL,
    google_drive_gb REAL,
    gmail_gb REAL,
    device_backup_gb REAL,
    total_used_gb REAL,
    
    -- Calculated metrics
    storage_growth_gb REAL,  -- Growth since baseline
    percent_complete REAL,
    
    -- Estimated transfers based on storage
    estimated_photos_transferred INTEGER,
    estimated_videos_transferred INTEGER,
    
    -- Flags
    is_baseline BOOLEAN DEFAULT FALSE,
    verification_method TEXT DEFAULT 'storage',  -- 'storage', 'ui_check', 'email'
    
    notes TEXT
);

-- 4. Daily progress with enhanced tracking
CREATE SEQUENCE IF NOT EXISTS daily_progress_seq;
CREATE TABLE daily_progress (
    id INTEGER PRIMARY KEY DEFAULT nextval('daily_progress_seq'),
    migration_id TEXT NOT NULL,
    day_number INTEGER NOT NULL,
    date DATE DEFAULT CURRENT_DATE,
    
    -- Media transfer progress
    photos_transferred INTEGER,
    videos_transferred INTEGER,
    size_transferred_gb REAL,
    storage_percent_complete REAL,
    
    -- Family app adoption
    whatsapp_members_connected INTEGER,
    maps_members_sharing INTEGER,
    venmo_members_active INTEGER,
    
    -- Key events
    key_milestone TEXT,
    gmail_checks_performed TEXT,  -- JSON array of email checks
    mobile_actions_performed TEXT,  -- JSON array of mobile actions
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    -- Removed UNIQUE constraint to allow multiple progress updates per day
);

-- 5. Family members (unchanged)
CREATE SEQUENCE IF NOT EXISTS family_members_seq;
CREATE TABLE family_members (
    id INTEGER PRIMARY KEY DEFAULT nextval('family_members_seq'),
    migration_id TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT,
    age INTEGER,
    email TEXT NOT NULL,
    phone TEXT,
    staying_on_ios BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_role CHECK (role IN ('spouse', 'child'))
);

-- 6. App setup tracking (unchanged)
CREATE SEQUENCE IF NOT EXISTS app_setup_seq;
CREATE TABLE app_setup (
    id INTEGER PRIMARY KEY DEFAULT nextval('app_setup_seq'),
    migration_id TEXT NOT NULL,
    app_name TEXT NOT NULL,
    category TEXT,
    setup_status TEXT DEFAULT 'pending',
    group_created BOOLEAN DEFAULT false,
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

-- 7. Family app adoption (unchanged)
CREATE SEQUENCE IF NOT EXISTS family_app_adoption_seq;
CREATE TABLE family_app_adoption (
    id INTEGER PRIMARY KEY DEFAULT nextval('family_app_adoption_seq'),
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

-- 8. Venmo setup (unchanged)
CREATE SEQUENCE IF NOT EXISTS venmo_setup_seq;
CREATE TABLE venmo_setup (
    id INTEGER PRIMARY KEY DEFAULT nextval('venmo_setup_seq'),
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
CREATE INDEX idx_media_transfer_migration ON media_transfer(migration_id);
CREATE INDEX idx_storage_snapshots_migration ON storage_snapshots(migration_id, day_number);
CREATE INDEX idx_daily_progress_migration ON daily_progress(migration_id, day_number);
CREATE INDEX idx_family_members_migration ON family_members(migration_id);
CREATE INDEX idx_app_setup_migration ON app_setup(migration_id);
CREATE INDEX idx_family_adoption_member ON family_app_adoption(family_member_id);
CREATE INDEX idx_venmo_setup_migration ON venmo_setup(migration_id);

-- Enhanced Views

-- Overall migration summary with video support
CREATE VIEW migration_summary AS
SELECT 
    m.id,
    m.user_name,
    m.current_phase,
    m.overall_progress,
    
    -- Media transfer details
    mt.photo_status,
    mt.video_status,
    mt.overall_status as transfer_status,
    
    -- Progress metrics
    mt.transferred_photos || '/' || mt.total_photos as photo_progress,
    mt.transferred_videos || '/' || mt.total_videos as video_progress,
    ROUND(mt.transferred_size_gb, 1) || '/' || ROUND(mt.total_size_gb, 1) || ' GB' as storage_progress,
    
    -- Storage-based calculation
    COALESCE(
        (SELECT MAX(percent_complete) 
         FROM storage_snapshots 
         WHERE migration_id = m.id), 0
    ) as storage_percent_complete,
    
    -- Family status
    COUNT(DISTINCT fm.id) as family_members,
    COUNT(DISTINCT CASE WHEN faa.status = 'configured' THEN faa.family_member_id END) as members_configured
    
FROM migration_status m
LEFT JOIN media_transfer mt ON m.id = mt.migration_id
LEFT JOIN family_members fm ON m.id = fm.migration_id
LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
GROUP BY m.id, m.user_name, m.current_phase, m.overall_progress,
         mt.photo_status, mt.video_status, mt.overall_status,
         mt.transferred_photos, mt.total_photos, mt.transferred_videos,
         mt.total_videos, mt.transferred_size_gb, mt.total_size_gb;

-- Family app status (unchanged)
CREATE VIEW family_app_status AS
SELECT 
    fm.name,
    fm.email,
    MAX(CASE WHEN faa.app_name = 'WhatsApp' THEN faa.status END) as whatsapp,
    MAX(CASE WHEN faa.app_name = 'Google Maps' THEN faa.status END) as maps,
    MAX(CASE WHEN faa.app_name = 'Venmo' THEN faa.status END) as venmo
FROM family_members fm
LEFT JOIN family_app_adoption faa ON fm.id = faa.family_member_id
GROUP BY fm.id, fm.name, fm.email;

-- Active migration with storage tracking
CREATE VIEW active_migration AS
SELECT 
    m.*,
    mt.photo_status,
    mt.video_status,
    mt.overall_status as transfer_status,
    mt.transferred_photos,
    mt.transferred_videos,
    mt.total_photos,
    mt.total_videos,
    mt.transferred_size_gb,
    
    -- Latest storage snapshot
    (SELECT google_photos_gb - m.google_photos_baseline_gb 
     FROM storage_snapshots 
     WHERE migration_id = m.id 
     ORDER BY snapshot_time DESC 
     LIMIT 1) as storage_growth_gb,
     
    COUNT(DISTINCT fm.id) as total_family_members
    
FROM migration_status m
LEFT JOIN media_transfer mt ON m.id = mt.migration_id
LEFT JOIN family_members fm ON m.id = fm.migration_id
WHERE m.completed_at IS NULL
GROUP BY m.id, m.user_name, m.source_device, m.target_device, m.years_on_ios,
         m.photo_count, m.video_count, m.total_icloud_storage_gb,
         m.icloud_photo_storage_gb, m.icloud_video_storage_gb, m.album_count,
         m.google_storage_total_gb, m.google_photos_baseline_gb, m.google_drive_baseline_gb,
         m.gmail_baseline_gb, m.family_size, m.started_at, m.current_phase,
         m.overall_progress, m.completed_at,
         mt.photo_status, mt.video_status, mt.overall_status,
         mt.transferred_photos, mt.transferred_videos, mt.total_photos, 
         mt.total_videos, mt.transferred_size_gb
ORDER BY m.started_at DESC
LIMIT 1;

-- Daily progress view for demo
CREATE VIEW daily_progress_summary AS
SELECT 
    dp.*,
    CASE 
        WHEN dp.day_number <= 3 THEN 'Photos processing (not visible yet)'
        WHEN dp.day_number = 4 THEN 'Photos appearing! 🎉'
        WHEN dp.day_number = 5 THEN 'Transfer accelerating'
        WHEN dp.day_number = 6 THEN 'Nearly complete'
        WHEN dp.day_number = 7 THEN 'Migration complete! 🎊'
        ELSE 'In progress'
    END as day_status
FROM daily_progress dp;