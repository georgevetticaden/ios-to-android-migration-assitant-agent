-- WhatsApp migration tables (future implementation)
-- Placeholder schema for WhatsApp automation tools

-- Create WhatsApp migration schema
CREATE SCHEMA IF NOT EXISTS whatsapp_migration;

-- WhatsApp chat transfer tracking
CREATE TABLE IF NOT EXISTS whatsapp_migration.chat_transfers (
    chat_transfer_id VARCHAR PRIMARY KEY,
    migration_id VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR DEFAULT 'pending',
    chat_count INTEGER,
    media_count INTEGER,
    total_messages INTEGER,
    transfer_method VARCHAR,  -- 'official_tool', 'third_party', 'manual'
    metadata JSON
    -- Foreign key removed due to DuckDB cross-schema limitation
);

-- WhatsApp automation tasks
CREATE SEQUENCE IF NOT EXISTS whatsapp_migration.automation_tasks_seq;
CREATE TABLE IF NOT EXISTS whatsapp_migration.automation_tasks (
    task_id INTEGER PRIMARY KEY DEFAULT nextval('whatsapp_migration.automation_tasks_seq'),
    migration_id VARCHAR NOT NULL,
    task_type VARCHAR NOT NULL,  -- 'group_creation', 'member_addition', 'notification', 'settings_update'
    scheduled_at TIMESTAMP,
    executed_at TIMESTAMP,
    status VARCHAR DEFAULT 'pending',  -- 'pending', 'in_progress', 'completed', 'failed'
    target_group VARCHAR,
    details JSON,
    error_message TEXT
);

-- WhatsApp group mappings (iOS to Android)
CREATE SEQUENCE IF NOT EXISTS whatsapp_migration.group_mappings_seq;
CREATE TABLE IF NOT EXISTS whatsapp_migration.group_mappings (
    mapping_id INTEGER PRIMARY KEY DEFAULT nextval('whatsapp_migration.group_mappings_seq'),
    migration_id VARCHAR NOT NULL,
    ios_group_name VARCHAR,
    ios_group_id VARCHAR,
    android_group_name VARCHAR,
    android_group_id VARCHAR,
    member_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- WhatsApp contact sync status
CREATE SEQUENCE IF NOT EXISTS whatsapp_migration.contact_sync_seq;
CREATE TABLE IF NOT EXISTS whatsapp_migration.contact_sync (
    sync_id INTEGER PRIMARY KEY DEFAULT nextval('whatsapp_migration.contact_sync_seq'),
    migration_id VARCHAR NOT NULL,
    contact_name VARCHAR,
    phone_number VARCHAR,
    ios_status VARCHAR,
    android_status VARCHAR,
    sync_date TIMESTAMP,
    metadata JSON
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_chat_transfers_migration ON whatsapp_migration.chat_transfers(migration_id);
CREATE INDEX IF NOT EXISTS idx_automation_tasks_migration ON whatsapp_migration.automation_tasks(migration_id);
CREATE INDEX IF NOT EXISTS idx_automation_tasks_status ON whatsapp_migration.automation_tasks(status);
CREATE INDEX IF NOT EXISTS idx_group_mappings_migration ON whatsapp_migration.group_mappings(migration_id);
CREATE INDEX IF NOT EXISTS idx_contact_sync_migration ON whatsapp_migration.contact_sync(migration_id);