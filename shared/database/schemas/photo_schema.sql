-- Photo migration specific tables
-- Extends core migration with photo transfer tracking

-- Create photo migration schema
CREATE SCHEMA IF NOT EXISTS photo_migration;

-- Photo transfer tracking table
CREATE TABLE IF NOT EXISTS photo_migration.transfers (
    transfer_id VARCHAR PRIMARY KEY,
    migration_id VARCHAR NOT NULL,  -- Links to master migration
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR DEFAULT 'initiated',  -- 'initiated', 'in_progress', 'completed', 'failed'
    source_photos INTEGER,
    source_videos INTEGER,
    source_size_gb FLOAT,
    google_email VARCHAR NOT NULL,
    apple_id VARCHAR NOT NULL,
    baseline_google_count INTEGER,  -- Photos in Google before transfer
    baseline_timestamp TIMESTAMP,   -- When baseline was established
    metadata JSON
    -- Foreign key removed due to DuckDB cross-schema limitation
);

-- Progress history for tracking transfer over time
CREATE SEQUENCE IF NOT EXISTS photo_migration.progress_history_seq;
CREATE TABLE IF NOT EXISTS photo_migration.progress_history (
    id INTEGER PRIMARY KEY DEFAULT nextval('photo_migration.progress_history_seq'),
    transfer_id VARCHAR NOT NULL,
    checked_at TIMESTAMP NOT NULL,
    google_photos_total INTEGER,     -- Current total in Google Photos
    transferred_items INTEGER,       -- New items since baseline
    transfer_rate_per_hour FLOAT,
    notes TEXT
);

-- Quality verification samples
CREATE SEQUENCE IF NOT EXISTS photo_migration.quality_samples_seq;
CREATE TABLE IF NOT EXISTS photo_migration.quality_samples (
    id INTEGER PRIMARY KEY DEFAULT nextval('photo_migration.quality_samples_seq'),
    transfer_id VARCHAR NOT NULL,
    sample_date TIMESTAMP NOT NULL,
    photos_sampled INTEGER,
    metadata_preserved BOOLEAN,
    quality_issues INTEGER,
    sample_details JSON
);

-- Email confirmations from Apple
CREATE SEQUENCE IF NOT EXISTS photo_migration.email_confirmations_seq;
CREATE TABLE IF NOT EXISTS photo_migration.email_confirmations (
    id INTEGER PRIMARY KEY DEFAULT nextval('photo_migration.email_confirmations_seq'),
    transfer_id VARCHAR NOT NULL,
    email_received_at TIMESTAMP,
    email_subject VARCHAR,
    photos_reported INTEGER,
    videos_reported INTEGER,
    email_raw_content TEXT,
    parsed_data JSON
);

-- Important photos tracking for verification
CREATE SEQUENCE IF NOT EXISTS photo_migration.important_photos_seq;
CREATE TABLE IF NOT EXISTS photo_migration.important_photos (
    id INTEGER PRIMARY KEY DEFAULT nextval('photo_migration.important_photos_seq'),
    transfer_id VARCHAR NOT NULL,
    filename VARCHAR NOT NULL,
    original_date TIMESTAMP,
    found_in_destination BOOLEAN DEFAULT FALSE,
    quality_maintained BOOLEAN,
    metadata_intact BOOLEAN,
    verification_date TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_transfers_migration ON photo_migration.transfers(migration_id);
CREATE INDEX IF NOT EXISTS idx_transfers_status ON photo_migration.transfers(status);
CREATE INDEX IF NOT EXISTS idx_progress_transfer ON photo_migration.progress_history(transfer_id);
CREATE INDEX IF NOT EXISTS idx_progress_checked ON photo_migration.progress_history(checked_at);
CREATE INDEX IF NOT EXISTS idx_quality_transfer ON photo_migration.quality_samples(transfer_id);
CREATE INDEX IF NOT EXISTS idx_email_transfer ON photo_migration.email_confirmations(transfer_id);
CREATE INDEX IF NOT EXISTS idx_important_transfer ON photo_migration.important_photos(transfer_id);