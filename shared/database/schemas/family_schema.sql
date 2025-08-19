-- Family services migration tables (future implementation)
-- Placeholder schema for family coordination tools

-- Create family services schema
CREATE SCHEMA IF NOT EXISTS family_services;

-- Service migration tracking
CREATE SEQUENCE IF NOT EXISTS family_services.service_migrations_seq;
CREATE TABLE IF NOT EXISTS family_services.service_migrations (
    service_id INTEGER PRIMARY KEY DEFAULT nextval('family_services.service_migrations_seq'),
    migration_id VARCHAR NOT NULL,
    service_name VARCHAR NOT NULL,  -- 'Life360', 'Venmo Teen', 'Gmail filters', 'Screen Time', 'Find My'
    ios_status VARCHAR,
    android_status VARCHAR,
    migration_notes TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    metadata JSON
);

-- Gmail filter management for family
CREATE SEQUENCE IF NOT EXISTS family_services.email_filters_seq;
CREATE TABLE IF NOT EXISTS family_services.email_filters (
    filter_id INTEGER PRIMARY KEY DEFAULT nextval('family_services.email_filters_seq'),
    migration_id VARCHAR NOT NULL,
    member_id VARCHAR,
    filter_type VARCHAR,  -- 'school', 'medical', 'sports', 'financial'
    gmail_filter_id VARCHAR,
    filter_criteria JSON,
    label_name VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    active BOOLEAN DEFAULT TRUE
);

-- Life360 migration tracking
CREATE SEQUENCE IF NOT EXISTS family_services.life360_migration_seq;
CREATE TABLE IF NOT EXISTS family_services.life360_migration (
    id INTEGER PRIMARY KEY DEFAULT nextval('family_services.life360_migration_seq'),
    migration_id VARCHAR NOT NULL,
    member_id VARCHAR NOT NULL,
    ios_circle_id VARCHAR,
    android_circle_id VARCHAR,
    location_sharing_enabled BOOLEAN,
    driving_alerts_enabled BOOLEAN,
    place_alerts_configured BOOLEAN,
    migration_date TIMESTAMP
);

-- Venmo Teen account tracking
CREATE SEQUENCE IF NOT EXISTS family_services.venmo_teen_accounts_seq;
CREATE TABLE IF NOT EXISTS family_services.venmo_teen_accounts (
    id INTEGER PRIMARY KEY DEFAULT nextval('family_services.venmo_teen_accounts_seq'),
    migration_id VARCHAR NOT NULL,
    member_id VARCHAR NOT NULL,
    venmo_username VARCHAR,
    parent_connected BOOLEAN,
    spending_limit DECIMAL(10,2),
    auto_transfer_enabled BOOLEAN,
    setup_date TIMESTAMP,
    metadata JSON
);

-- Screen time / parental control mappings
CREATE SEQUENCE IF NOT EXISTS family_services.parental_controls_seq;
CREATE TABLE IF NOT EXISTS family_services.parental_controls (
    id INTEGER PRIMARY KEY DEFAULT nextval('family_services.parental_controls_seq'),
    migration_id VARCHAR NOT NULL,
    member_id VARCHAR NOT NULL,
    ios_screen_time_enabled BOOLEAN,
    android_family_link_enabled BOOLEAN,
    daily_limit_hours FLOAT,
    app_restrictions JSON,
    content_restrictions JSON,
    bedtime_schedule JSON,
    migration_date TIMESTAMP
);

-- Shared family calendars
CREATE SEQUENCE IF NOT EXISTS family_services.family_calendars_seq;
CREATE TABLE IF NOT EXISTS family_services.family_calendars (
    calendar_id INTEGER PRIMARY KEY DEFAULT nextval('family_services.family_calendars_seq'),
    migration_id VARCHAR NOT NULL,
    calendar_name VARCHAR NOT NULL,
    ios_calendar_id VARCHAR,
    google_calendar_id VARCHAR,
    shared_with JSON,  -- Array of member_ids
    events_migrated INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_service_migrations_migration ON family_services.service_migrations(migration_id);
CREATE INDEX IF NOT EXISTS idx_email_filters_migration ON family_services.email_filters(migration_id);
CREATE INDEX IF NOT EXISTS idx_email_filters_member ON family_services.email_filters(member_id);
CREATE INDEX IF NOT EXISTS idx_life360_migration ON family_services.life360_migration(migration_id);
CREATE INDEX IF NOT EXISTS idx_venmo_teen_migration ON family_services.venmo_teen_accounts(migration_id);
CREATE INDEX IF NOT EXISTS idx_parental_controls_migration ON family_services.parental_controls(migration_id);
CREATE INDEX IF NOT EXISTS idx_family_calendars_migration ON family_services.family_calendars(migration_id);