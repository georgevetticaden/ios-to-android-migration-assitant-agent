-- Core migration tracking tables for iOS to Android migration
-- Shared across all MCP tools

-- Create core schema
CREATE SCHEMA IF NOT EXISTS migration_core;

-- Master migration tracking table
CREATE TABLE IF NOT EXISTS migration_core.migrations (
    migration_id VARCHAR PRIMARY KEY,
    family_id VARCHAR,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    source_device VARCHAR,
    target_device VARCHAR,
    user_name VARCHAR,
    user_email VARCHAR NOT NULL,
    status VARCHAR DEFAULT 'planning',
    metadata JSON
);

-- Family members involved in migration
CREATE TABLE IF NOT EXISTS migration_core.family_members (
    member_id VARCHAR PRIMARY KEY,
    migration_id VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    role VARCHAR,  -- 'primary', 'spouse', 'teen', 'child'
    apple_id VARCHAR,
    google_account VARCHAR,
    phone_number VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (migration_id) REFERENCES migration_core.migrations(migration_id)
);

-- Cross-tool event log for complete timeline
CREATE SEQUENCE IF NOT EXISTS migration_core.event_log_seq;
CREATE TABLE IF NOT EXISTS migration_core.event_log (
    event_id INTEGER PRIMARY KEY DEFAULT nextval('migration_core.event_log_seq'),
    migration_id VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    tool_name VARCHAR NOT NULL,  -- 'photo-migration', 'whatsapp', 'family-services'
    event_type VARCHAR NOT NULL,  -- 'transfer_started', 'progress_update', 'error', etc.
    details JSON,
    FOREIGN KEY (migration_id) REFERENCES migration_core.migrations(migration_id)
);

-- Tool coordination and dependencies
CREATE SEQUENCE IF NOT EXISTS migration_core.tool_coordination_seq;
CREATE TABLE IF NOT EXISTS migration_core.tool_coordination (
    coordination_id INTEGER PRIMARY KEY DEFAULT nextval('migration_core.tool_coordination_seq'),
    migration_id VARCHAR NOT NULL,
    tool_name VARCHAR NOT NULL,
    depends_on_tool VARCHAR,
    dependency_status VARCHAR DEFAULT 'waiting',  -- 'waiting', 'ready', 'completed'
    metadata JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (migration_id) REFERENCES migration_core.migrations(migration_id)
);

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_migrations_status ON migration_core.migrations(status);
CREATE INDEX IF NOT EXISTS idx_migrations_user ON migration_core.migrations(user_email);
CREATE INDEX IF NOT EXISTS idx_family_members_migration ON migration_core.family_members(migration_id);
CREATE INDEX IF NOT EXISTS idx_event_log_migration ON migration_core.event_log(migration_id);
CREATE INDEX IF NOT EXISTS idx_event_log_timestamp ON migration_core.event_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_event_log_tool ON migration_core.event_log(tool_name);
CREATE INDEX IF NOT EXISTS idx_coordination_migration ON migration_core.tool_coordination(migration_id);
CREATE INDEX IF NOT EXISTS idx_coordination_tool ON migration_core.tool_coordination(tool_name);